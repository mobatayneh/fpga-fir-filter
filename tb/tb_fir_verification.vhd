-- Self-checking VHDL-2008 verification of the recovered baseline and extension.
-- The reference uses integer convolution, independent of RTL register arithmetic.
-- The cycle counter starts at the first explicitly observed reset edge.
-- Latency counts ELAPSED rising-edge periods.
-- Run from a dedicated results directory; this bench creates two CSV files.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;

entity tb_fir_verification is
end entity;

architecture sim of tb_fir_verification is
    constant PERIOD : time := 10 ns;
    signal clk : std_logic := '0';
    signal reset_n : std_logic := '0';
    signal b_valid, s_valid : std_logic := '0';
    signal b_in, s_in : std_logic_vector(7 downto 0) := (others => '0');
    signal b_out, s_out : std_logic_vector(17 downto 0);
    signal b_busy, s_busy, b_strobe, s_strobe : std_logic;
begin
    clk <= not clk after PERIOD / 2;
    baseline : entity work.fir_filter
        port map(CLK => clk, Reset => reset_n, StrobeIn => b_valid,
                 DataIn => b_in, DataOut => b_out, Busy => b_busy, StrobeOut => b_strobe);
    streaming : entity work.fir_filter_streaming
        port map(CLK => clk, Reset => reset_n, StrobeIn => s_valid,
                 DataIn => s_in, DataOut => s_out, Busy => s_busy, StrobeOut => s_strobe);

    stimulus : process
        file verification : text open write_mode is "verification.csv";
        file benchmark : text open write_mode is "benchmark.csv";
        type history_t is array(0 to 2) of natural range 0 to 255;
        type samples_t is array(natural range <>) of natural range 0 to 255;
        constant report_samples : samples_t := (3, 4, 5, 6, 10, 0);
        variable bh, sh : history_t := (others => 0);
        variable b_remaining : natural range 0 to 4 := 0;
        variable s_pending : boolean := false;
        variable b_expected, s_expected : natural := 0;
        variable b_accepted_cycle, s_accepted_cycle : natural := 0;
        variable b_index, s_index : natural := 0;
        variable b_previous, s_previous : natural := 0;
        variable cycle : natural := 0;
        variable b_checked, s_checked : natural := 0;
        variable b_bench_in, s_bench_in, b_bench_out, s_bench_out : natural := 0;
        variable b_first, s_first, b_last, s_last : natural := 0;
        variable b_last_accept, s_last_accept, b_ii, s_ii : natural := 0;
        variable rng : unsigned(31 downto 0) := x"82080001";
        variable b_drive_valid, s_drive_valid : boolean;
        variable b_drive_data, s_drive_data : natural range 0 to 255;
        variable row : line;

        function logic(value : boolean) return std_logic is
        begin
            if value then return '1'; else return '0'; end if;
        end function;

        procedure write_result(architecture_name, phase : string;
                               index, expected, actual, latency : natural) is
            variable entry : line;
        begin
            write(entry, architecture_name & "," & phase & ",");
            write(entry, cycle); write(entry, string'(","));
            write(entry, index); write(entry, string'(","));
            write(entry, expected); write(entry, string'(","));
            write(entry, actual); write(entry, string'(","));
            write(entry, latency);
            writeline(verification, entry);
        end procedure;

        procedure step(bv, sv : boolean; bd, sd : natural; phase : string) is
            variable b_due, s_due : boolean;
            variable s_due_expected, s_due_cycle, s_due_index : natural;
        begin
            assert bd <= 255 and sd <= 255 report "Invalid test stimulus" severity failure;
            wait until falling_edge(clk);
            b_valid <= logic(bv); s_valid <= logic(sv);
            b_in <= std_logic_vector(to_unsigned(bd, 8));
            s_in <= std_logic_vector(to_unsigned(sd, 8));
            wait until rising_edge(clk);
            cycle := cycle + 1;

            b_due := b_remaining = 1;
            if b_remaining > 0 then
                b_remaining := b_remaining - 1;
            elsif bv then
                b_expected := bd + 2*bh(0) + 2*bh(1) + bh(2);
                bh := (bd, bh(0), bh(1));
                b_remaining := 4;
                b_accepted_cycle := cycle;
                b_index := b_index + 1;
                if phase = "benchmark" then
                    b_bench_in := b_bench_in + 1;
                    if b_bench_in = 1 then b_first := cycle;
                    else
                        b_ii := cycle - b_last_accept;
                        assert b_ii = 5 report "Baseline benchmark II mismatch" severity failure;
                    end if;
                    b_last_accept := cycle;
                end if;
            end if;

            s_due := s_pending;
            s_due_expected := s_expected;
            s_due_cycle := s_accepted_cycle;
            s_due_index := s_index;
            s_pending := sv;
            if sv then
                s_expected := sd + 2*sh(0) + 2*sh(1) + sh(2);
                sh := (sd, sh(0), sh(1));
                s_accepted_cycle := cycle;
                s_index := s_index + 1;
                if phase = "benchmark" then
                    s_bench_in := s_bench_in + 1;
                    if s_bench_in = 1 then s_first := cycle;
                    else
                        s_ii := cycle - s_last_accept;
                        assert s_ii = 1 report "Streaming benchmark II mismatch" severity failure;
                    end if;
                    s_last_accept := cycle;
                end if;
            end if;

            -- Sample after all sequential and concurrent delta-cycle updates.
            wait for 1 ns;
            assert not is_x(b_out) and not is_x(s_out)
                report "Unknown bit in DUT output at cycle " & natural'image(cycle) severity failure;
            assert b_busy = logic(b_remaining > 0)
                report "Baseline Busy mismatch at cycle " & natural'image(cycle) severity failure;
            assert s_busy = '0' report "Streaming Busy must stay low" severity failure;
            assert b_strobe = logic(b_due)
                report "Baseline output validity mismatch at cycle " & natural'image(cycle) severity failure;
            assert s_strobe = logic(s_due)
                report "Streaming output validity mismatch at cycle " & natural'image(cycle) severity failure;

            if b_due then
                assert to_integer(unsigned(b_out)) = b_expected
                    report "Baseline arithmetic mismatch at cycle " & natural'image(cycle) severity failure;
                assert cycle - b_accepted_cycle = 4 report "Baseline latency mismatch" severity failure;
                write_result("baseline", phase, b_index, b_expected,
                             to_integer(unsigned(b_out)), cycle - b_accepted_cycle);
                b_previous := b_expected;
                b_checked := b_checked + 1;
                if phase = "benchmark" then b_bench_out := b_bench_out + 1; b_last := cycle; end if;
            else
                assert to_integer(unsigned(b_out)) = b_previous
                    report "Baseline DataOut changed without valid output" severity failure;
            end if;
            if s_due then
                assert to_integer(unsigned(s_out)) = s_due_expected
                    report "Streaming arithmetic mismatch at cycle " & natural'image(cycle) severity failure;
                assert cycle - s_due_cycle = 1 report "Streaming latency mismatch" severity failure;
                write_result("streaming", phase, s_due_index, s_due_expected,
                             to_integer(unsigned(s_out)), cycle - s_due_cycle);
                s_previous := s_due_expected;
                s_checked := s_checked + 1;
                if phase = "benchmark" then s_bench_out := s_bench_out + 1; s_last := cycle; end if;
            else
                assert to_integer(unsigned(s_out)) = s_previous
                    report "Streaming DataOut changed without valid output" severity failure;
            end if;
        end procedure;

        procedure reset_duts is
        begin
            wait until falling_edge(clk);
            reset_n <= '0'; b_valid <= '0'; s_valid <= '0';
            wait for 1 ns;
            -- These checks occur four ns BEFORE the next rising clock edge.
            assert b_out = (b_out'range => '0') and s_out = (s_out'range => '0')
                report "Asynchronous reset did not clear data" severity failure;
            assert b_busy = '0' and s_busy = '0' and b_strobe = '0' and s_strobe = '0'
                report "Asynchronous reset did not clear handshake" severity failure;
            bh := (others => 0); sh := (others => 0);
            b_remaining := 0; s_pending := false;
            b_expected := 0; s_expected := 0;
            b_previous := 0; s_previous := 0;
            wait until rising_edge(clk);
            cycle := cycle + 1;
            wait for 1 ns;
            reset_n <= '1';
        end procedure;

        procedure paired_sample(value : natural) is
        begin
            step(true, true, value, value, "directed");
            for j in 1 to 4 loop
                step(false, false, 255-j, j, "directed");
            end loop;
        end procedure;

        procedure write_benchmark(name : string; first_cycle, last_cycle, ii : natural) is
            variable entry : line;
        begin
            write(entry, name & ",512,");
            write(entry, first_cycle); write(entry, string'(","));
            write(entry, last_cycle); write(entry, string'(","));
            write(entry, last_cycle-first_cycle); write(entry, string'(","));
            write(entry, ii); writeline(benchmark, entry);
        end procedure;
    begin
        write(row, string'("architecture,phase,cycle,input_index,expected,actual,latency"));
        writeline(verification, row);
        write(row, string'("architecture,samples,first_accept_cycle,last_output_cycle,elapsed_cycles,initiation_interval_cycles"));
        writeline(benchmark, row);
        reset_duts;

        -- Identical 512-value sequence, each design driven at its maximum input rate.
        while b_bench_out < 512 or s_bench_out < 512 loop
            b_drive_valid := b_bench_in < 512 and b_remaining = 0;
            s_drive_valid := s_bench_in < 512;
            b_drive_data := (b_bench_in*73 + 19) mod 256;
            s_drive_data := (s_bench_in*73 + 19) mod 256;
            step(b_drive_valid, s_drive_valid, b_drive_data, s_drive_data, "benchmark");
            assert cycle < 3000 report "Benchmark timeout" severity failure;
        end loop;
        assert b_bench_in = 512 and s_bench_in = 512 severity failure;
        assert b_last-b_first = 2559 and s_last-s_first = 512
            report "Measured block timing mismatch" severity failure;
        write_benchmark("baseline", b_first, b_last, b_ii);
        write_benchmark("streaming", s_first, s_last, s_ii);

        reset_duts;
        for i in report_samples'range loop paired_sample(report_samples(i)); end loop;
        for i in 1 to 16 loop paired_sample(0); end loop;
        paired_sample(255); -- full-amplitude impulse after a zero history
        for i in 1 to 8 loop paired_sample(0); end loop;
        for i in 1 to 32 loop paired_sample(255); end loop; -- step and maximum result
        for i in 1 to 32 loop paired_sample((i mod 2)*255); end loop;

        -- Continuous requests deliberately exercise baseline busy-time rejection.
        for i in 0 to 79 loop step(true, true, (17*i) mod 256, (17*i) mod 256, "directed"); end loop;
        for i in 1 to 5 loop step(false, false, 255, 255, "directed"); end loop;

        -- Abort each baseline processing state; first case also aborts stream pending data.
        for state_offset in 0 to 3 loop
            reset_duts;
            step(true, true, 255, 255, "reset_recovery");
            for i in 1 to state_offset loop step(false, false, 0, 0, "reset_recovery"); end loop;
            reset_duts;
            for i in 1 to 5 loop step(false, false, 0, 0, "reset_recovery"); end loop;
            paired_sample(3);
        end loop;

        -- Reproducible 32-bit LFSR seed 0x82080001; no host random generator.
        -- Gaps, busy requests and data changes are all independent between DUTs.
        for i in 1 to 6000 loop
            rng := rng(30 downto 0) & (rng(31) xor rng(21) xor rng(1) xor rng(0));
            b_drive_valid := rng(8) = '1'; s_drive_valid := rng(17) = '1';
            b_drive_data := to_integer(rng(7 downto 0)); s_drive_data := to_integer(rng(25 downto 18));
            step(b_drive_valid, s_drive_valid, b_drive_data, s_drive_data, "random");
            if i mod 997 = 0 then reset_duts; end if;
        end loop;
        for i in 1 to 5 loop step(false, false, 0, 0, "random"); end loop;
        assert b_remaining = 0 and not s_pending report "Pending results at completion" severity failure;
        assert b_checked > 1500 and s_checked > 3500 report "Insufficient checked outputs" severity failure;
        file_close(verification); file_close(benchmark);
        report "PASSED: baseline_outputs=" & natural'image(b_checked) &
               " streaming_outputs=" & natural'image(s_checked) &
               " cycles=" & natural'image(cycle) & " random_cycles=6000 seed=0x82080001" severity note;
        stop;
        wait;
    end process;
end architecture;
