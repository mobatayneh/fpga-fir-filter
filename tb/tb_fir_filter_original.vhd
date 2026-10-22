----------------------------------------------------------------------------------
-- Testbench : tb_fir_filter
-- Purpose   : Drives the fir_filter (Device Under Test) for functional simulation.
--             Generates a 100 MHz clock, applies the active-low reset, and feeds a
--             stream of input samples, so we can watch DataOut / StrobeOut / Busy.
--
-- Check     : with coefficients h = [1,2,2,1] and inputs x = 3,4,5,6, the output
--             after x=6 must be  y = 1*6 + 2*5 + 2*4 + 1*3 = 27  (0x1B in hex).
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
 
entity tb_fir_filter is
    -- a testbench has no ports (it is the top of the simulation)
end tb_fir_filter;
 
architecture sim of tb_fir_filter is
 
    -- signals that connect to the DUT (Device Under Test)
    signal CLK       : std_logic := '0';
    signal Reset     : std_logic := '0';
    signal StrobeIn  : std_logic := '0';
    signal DataIn    : std_logic_vector(7  downto 0) := (others => '0');
    signal DataOut   : std_logic_vector(17 downto 0);
    signal Busy      : std_logic;
    signal StrobeOut : std_logic;
 
    constant CLK_PERIOD : time := 10 ns;   -- 10 ns => 100 MHz
 
begin
 
    ----------------------------------------------------------------------------
    -- Instantiate the FIR filter (the design we are testing)
    ----------------------------------------------------------------------------
    DUT : entity work.fir_filter
        port map (
            CLK       => CLK,
            Reset     => Reset,
            StrobeIn  => StrobeIn,
            DataIn    => DataIn,
            DataOut   => DataOut,
            Busy      => Busy,
            StrobeOut => StrobeOut
        );
 
    ----------------------------------------------------------------------------
    -- Clock generator : toggles every half period forever
    ----------------------------------------------------------------------------
    clk_process : process
    begin
        CLK <= '0';
        wait for CLK_PERIOD/2;
        CLK <= '1';
        wait for CLK_PERIOD/2;
    end process;
 
    ----------------------------------------------------------------------------
    -- Stimulus : reset, then feed samples one at a time
    ----------------------------------------------------------------------------
    stim_process : process
    begin
        -- apply active-LOW reset for a couple of cycles
        Reset <= '0';
        wait for 2*CLK_PERIOD;
        Reset <= '1';
        wait for 2*CLK_PERIOD;
 
        -- sample x = 3
        DataIn <= std_logic_vector(to_unsigned(3, 8));
        StrobeIn <= '1';  wait for CLK_PERIOD;  StrobeIn <= '0';
        wait for 6*CLK_PERIOD;                 -- let the filter finish (S1..S4 + margin)
 
        -- sample x = 4
        DataIn <= std_logic_vector(to_unsigned(4, 8));
        StrobeIn <= '1';  wait for CLK_PERIOD;  StrobeIn <= '0';
        wait for 6*CLK_PERIOD;
 
        -- sample x = 5
        DataIn <= std_logic_vector(to_unsigned(5, 8));
        StrobeIn <= '1';  wait for CLK_PERIOD;  StrobeIn <= '0';
        wait for 6*CLK_PERIOD;
 
        -- sample x = 6   -->  EXPECT DataOut = 27  (delay line now = 6,5,4,3)
        DataIn <= std_logic_vector(to_unsigned(6, 8));
        StrobeIn <= '1';  wait for CLK_PERIOD;  StrobeIn <= '0';
        wait for 6*CLK_PERIOD;
 
        -- two more samples to show continued streaming operation
        DataIn <= std_logic_vector(to_unsigned(10, 8));
        StrobeIn <= '1';  wait for CLK_PERIOD;  StrobeIn <= '0';
        wait for 6*CLK_PERIOD;
 
        DataIn <= std_logic_vector(to_unsigned(0, 8));
        StrobeIn <= '1';  wait for CLK_PERIOD;  StrobeIn <= '0';
        wait for 6*CLK_PERIOD;
 
        report "Simulation finished successfully." severity note;
        wait;   -- stop here
    end process;
 
end sim;
