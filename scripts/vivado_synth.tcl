# Optional, synthesis-only comparison. Run from any directory with Vivado:
# vivado -mode batch -source scripts/vivado_synth.tcl -tclargs results/vivado_run_001
# The output directory must not exist. Existing results are never overwritten.

set fir_script_path [file normalize [info script]]
set fir_root [file dirname [file dirname $fir_script_path]]
set fir_output ""

proc fir_write_text {path contents} {
    set channel [open $path {WRONLY CREAT EXCL}]
    fconfigure $channel -encoding utf-8 -translation lf
    puts $channel $contents
    close $channel
}

proc fir_main {} {
    global argc argv fir_script_path fir_root fir_output
    if {$argc != 1} {
        error "Usage: vivado -mode batch -source scripts/vivado_synth.tcl -tclargs NEW_OUTPUT_DIRECTORY"
    }
    set requested_output [file normalize [lindex $argv 0]]
    if {[file exists $requested_output]} {
        error "Output already exists; choose a new directory: $requested_output"
    }

    set part xc7z020clg484-1
    set tops {fir_filter fir_filter_streaming}
    foreach top $tops {
        set source [file join $fir_root rtl ${top}.vhd]
        if {![file isfile $source]} {
            error "Missing source: $source"
        }
    }
    if {[llength [get_parts -quiet $part]] != 1} {
        error "Target $part is unavailable. Install the Vivado Zynq-7000 device support."
    }

    file mkdir $requested_output
    set fir_output $requested_output
    file copy $fir_script_path [file join $fir_output vivado_synth.tcl]
    set xdc [file join $fir_output clock_only.xdc]
    fir_write_text $xdc {
# Common out-of-context clock target for both architectures.
create_clock -name fir_clk -period 10.000 [get_ports CLK]
# Deliberately no board pins, I/O delays, activity, or timing exceptions.
# External interface and asynchronous-reset timing require integration constraints.
}

    fir_write_text [file join $fir_output environment.txt] "Vivado version: [version -short]\n[version]\nPart: $part\nFlow: out-of-context synthesis only\nClock target: 10.000 ns\nLanguage: VHDL-2008\nFlatten hierarchy: rebuilt\nI/O delays: unspecified; external paths are not timing-closed\nClock uncertainty/activity/board pins: unspecified\nPower: not estimated\nImplementation/bitstream/hardware test: not run\nStarted UTC: [clock format [clock seconds] -gmt true -format {%Y-%m-%dT%H:%M:%SZ}]"

    foreach top $tops {
        set top_output [file join $fir_output $top]
        file mkdir $top_output
        set source_snapshot [file join $top_output ${top}.vhd]
        file copy [file join $fir_root rtl ${top}.vhd] $source_snapshot

        # A fresh in-memory project isolates each top and its constraint state.
        create_project -in_memory -part $part fir_ooc_${top}
        read_vhdl -library work -vhdl2008 $source_snapshot
        read_xdc $xdc
        synth_design -top $top -part $part -mode out_of_context -flatten_hierarchy rebuilt

        if {[llength [get_clocks -quiet fir_clk]] != 1} {
            error "The clock constraint was not applied for $top"
        }
        report_utilization -file [file join $top_output utilization.rpt]
        report_clocks -file [file join $top_output clocks.rpt]
        check_timing -verbose -file [file join $top_output check_timing.rpt]
        report_timing_summary -delay_type min_max -max_paths 10 -report_unconstrained -check_timing_verbose -file [file join $top_output timing_summary.rpt]
        report_drc -file [file join $top_output drc.rpt]
        write_checkpoint [file join $top_output post_synth.dcp]
        fir_write_text [file join $top_output status.txt] "SYNTHESIS_COMPLETED\nInspect warnings, DRC, and unconstrained paths before interpreting timing."
        close_project
    }
    fir_write_text [file join $fir_output status.txt] "SYNTHESIS_COMPARISON_COMPLETED\nThis is not implementation timing closure or a board demonstration."
}

if {[catch {fir_main} fir_error fir_options]} {
    puts stderr "FIR synthesis comparison failed: $fir_error"
    if {$fir_output ne ""} {
        catch {fir_write_text [file join $fir_output failure.txt] [dict get $fir_options -errorinfo]}
    }
    exit 1
}
exit 0
