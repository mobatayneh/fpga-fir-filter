----------------------------------------------------------------------------------
-- Module Name : fir_filter
-- Project     : EE-8208 Design Project - 8-bit 4-tap FIR Filter
-- Description : Application-Specific Processor (ASP) computing
--               y[n] = h0*x[n] + h1*x[n-1] + h2*x[n-2] + h3*x[n-3]
--
--               Optimal architecture (from the design analysis):
--                 - 2 shared multipliers  (reused across two multiply steps)
--                 - 1 shared adder        (reused across three add steps)
--               Control is done by a small state machine (IDLE -> S1..S4).
--
-- Interface   : DataIn(8-bit) -> DataOut(18-bit),
--               StrobeIn / StrobeOut / Busy handshaking,
--               Reset is active-LOW and asynchronous.
-- Target      : xc7z020clg484-1 (ZedBoard, Zynq-7000). Tool: Vivado 2026.1
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;          -- modern numeric library (unsigned/signed)
 
entity fir_filter is
    Port (
        CLK       : in  STD_LOGIC;                       -- clock
        Reset     : in  STD_LOGIC;                       -- active-LOW asynchronous reset
        StrobeIn  : in  STD_LOGIC;                       -- '1' = a new valid sample is on DataIn
        DataIn    : in  STD_LOGIC_VECTOR(7  downto 0);   -- 8-bit input sample  x[n]
        DataOut   : out STD_LOGIC_VECTOR(17 downto 0);   -- 18-bit output sample y[n]
        Busy      : out STD_LOGIC;                       -- '1' while the filter is computing
        StrobeOut : out STD_LOGIC                        -- '1' for one cycle when DataOut is valid
    );
end fir_filter;
 
architecture Behavioral of fir_filter is
 
    -- Fixed 8-bit FIR coefficients (example low-pass set: 1,2,2,1). Change if needed.
    constant h0 : unsigned(7 downto 0) := to_unsigned(1, 8);
    constant h1 : unsigned(7 downto 0) := to_unsigned(2, 8);
    constant h2 : unsigned(7 downto 0) := to_unsigned(2, 8);
    constant h3 : unsigned(7 downto 0) := to_unsigned(1, 8);
 
    -- Tap delay line : the four most recent input samples
    signal x0, x1, x2, x3 : unsigned(7 downto 0) := (others => '0');
 
    -- Product registers (8-bit x 8-bit = 16-bit)
    signal p1, p2, p3, p4 : unsigned(15 downto 0) := (others => '0');
 
    -- Partial sums / result accumulator (18-bit holds the final answer)
    -- NOTE: named sum1/sum2 (NOT s1/s2) because VHDL is case-insensitive and
    --       s1/s2 would collide with the state names S1/S2 below.
    signal sum1, sum2 : unsigned(17 downto 0) := (others => '0');
 
    -- Control state machine
    type state_t is (IDLE, S1, S2, S3, S4);
    signal state : state_t := IDLE;
 
begin
 
    process(CLK, Reset)
    begin
        if (Reset = '0') then                 -- active-LOW asynchronous reset
            state     <= IDLE;
            x0 <= (others => '0'); x1 <= (others => '0');
            x2 <= (others => '0'); x3 <= (others => '0');
            p1 <= (others => '0'); p2 <= (others => '0');
            p3 <= (others => '0'); p4 <= (others => '0');
            sum1 <= (others => '0'); sum2 <= (others => '0');
            DataOut   <= (others => '0');
            Busy      <= '0';
            StrobeOut <= '0';
 
        elsif rising_edge(CLK) then
            StrobeOut <= '0';                  -- default: StrobeOut is a 1-cycle pulse
 
            case state is
 
                when IDLE =>                   -- wait for a new sample
                    Busy <= '0';
                    if (StrobeIn = '1') then
                        -- shift the tap delay line: newest sample enters x0
                        x0 <= unsigned(DataIn);
                        x1 <= x0;
                        x2 <= x1;
                        x3 <= x2;
                        Busy  <= '1';
                        state <= S1;
                    end if;
 
                when S1 =>                     -- 2 multipliers : Op1, Op2
                    p1 <= h0 * x0;            -- Op1 = h0 * x[n]
                    p2 <= h1 * x1;            -- Op2 = h1 * x[n-1]
                    state <= S2;
 
                when S2 =>                     -- 2 multipliers reused : Op3, Op4 ; adder : Op5
                    p3 <= h2 * x2;            -- Op3 = h2 * x[n-2]
                    p4 <= h3 * x3;            -- Op4 = h3 * x[n-3]
                    sum1 <= resize(p1, 18) + resize(p2, 18);  -- Op5 = p1 + p2
                    state <= S3;
 
                when S3 =>                     -- adder reused : Op6
                    sum2 <= resize(p3, 18) + resize(p4, 18);  -- Op6 = p3 + p4
                    state <= S4;
 
                when S4 =>                     -- adder reused : Op7 (final result)
                    DataOut   <= std_logic_vector(sum1 + sum2); -- Op7 = sum1 + sum2 = y[n]
                    StrobeOut <= '1';         -- result is valid this cycle
                    Busy      <= '0';
                    state     <= IDLE;
 
            end case;
        end if;
    end process;
 
end Behavioral;
