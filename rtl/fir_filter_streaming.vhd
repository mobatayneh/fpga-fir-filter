-- Fixed-coefficient FIR: y[n] = x[n] + 2*x[n-1] + 2*x[n-2] + x[n-3].
-- Samples are unsigned 8-bit values. Output is an exact unsigned integer.
-- This extension preserves the baseline transfer function and 18-bit port width.
-- It specializes the arithmetic to h=[1,2,2,1]; it is not a generic multiplier.
--
-- Interface contract:
-- * Reset is active LOW and asynchronous; reset clears history and pending data.
-- * Every rising edge with StrobeIn='1' accepts one sample. Busy is always '0'.
-- * An accepted sample produces a valid output at the NEXT rising edge.
-- * Invalid input cycles do not advance sample history.
-- * Consecutive valid outputs keep StrobeOut HIGH on consecutive cycles.
--   Consumers must sample every valid cycle, not only StrobeOut rising edges.
-- * There is no output backpressure. DataOut holds its value on invalid cycles.
--
-- Arithmetic: two symmetric 9-bit pair sums (max 510), then an 11-bit
-- outer + 2*inner (max 1530). Resize BEFORE addition/shift to avoid overflow.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity fir_filter_streaming is
    port (
        CLK       : in  std_logic;
        Reset     : in  std_logic;
        StrobeIn  : in  std_logic;
        DataIn    : in  std_logic_vector(7 downto 0);
        DataOut   : out std_logic_vector(17 downto 0);
        Busy      : out std_logic;
        StrobeOut : out std_logic
    );
end entity;

architecture rtl of fir_filter_streaming is
    signal d1, d2, d3 : unsigned(7 downto 0) := (others => '0');
    signal outer_q, inner_q : unsigned(8 downto 0) := (others => '0');
    signal valid_q : std_logic := '0';
begin
    Busy <= '0';

    process(CLK, Reset)
        variable result : unsigned(10 downto 0);
    begin
        if Reset = '0' then
            d1 <= (others => '0');
            d2 <= (others => '0');
            d3 <= (others => '0');
            outer_q <= (others => '0');
            inner_q <= (others => '0');
            valid_q <= '0';
            DataOut <= (others => '0');
            StrobeOut <= '0';
        elsif rising_edge(CLK) then
            StrobeOut <= valid_q;
            if valid_q = '1' then
                result := resize(outer_q, 11) + shift_left(resize(inner_q, 11), 1);
                DataOut <= std_logic_vector(resize(result, 18));
            end if;

            valid_q <= StrobeIn;
            if StrobeIn = '1' then
                outer_q <= resize(unsigned(DataIn), 9) + resize(d3, 9);
                inner_q <= resize(d1, 9) + resize(d2, 9);
                d1 <= unsigned(DataIn);
                d2 <= d1;
                d3 <= d2;
            end if;
        end if;
    end process;
end architecture;
