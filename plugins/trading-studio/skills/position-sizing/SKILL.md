---
name: position-sizing
description: Calculate and review position sizes and portfolio risk for stocks, futures, crypto, forex lots and binary contracts - fixed-fractional risk per trade from entry and stop, ATR stops, futures point values, forex pip values, Kelly and fractional Kelly, prediction-market contract sizing, and checks for correlated exposure, leverage and ruin risk. Includes a tested calculator script. Use when someone asks how much to buy, how many lots or contracts, what risk per trade to use, whether their sizing or leverage is safe, or reviews a bot's sizing code.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/position_size.py *)
---

# Position sizing and risk review

Sizing decides whether a strategy survives its losing streaks. Always compute
with the bundled script rather than mental arithmetic, and always round
quantities **down**.

## Calculator

```bash
S=${CLAUDE_SKILL_DIR}/scripts/position_size.py
python $S risk  --equity 25000 --risk-pct 1 --entry 182.50 --stop 178.00            # shares
python $S risk  --equity 50000 --risk-pct 0.5 --entry 5300 --stop 5285 --multiplier 50  # ES futures
python $S risk  --equity 8000 --risk-pct 1 --entry 64250 --stop 62900 --step 0.001 \
                --fee-per-unit 128                                                  # BTC, fees per 1 BTC
python $S forex --equity 10000 --risk-pct 1 --stop-pips 25 --pip-value 10            # EURUSD, USD account
python $S kelly --win-rate 0.55 --payoff 1.2
python $S binary --price 0.40 --prob 0.50 --bankroll 2000                           # Kalshi / Polymarket
python $S atr-stop --entry 100 --atr 2.5 --mult 2 --side long
```

Add `--json` to any command for machine-readable output. `python $S --self-test`
checks the maths.

Key inputs:

- `--multiplier`: money per 1.0 price move per unit (futures point value,
  contract size). ES = 50, MES = 5, NQ = 20, CL = 1000, gold (GC) = 100 per $1.
- `--pip-value`: account-currency value of 1 pip for 1.0 lot. About 10 for
  XXX/USD pairs on a USD account; for crosses and JPY pairs it depends on the
  current rate. From MT5: `pip value = SYMBOL_TRADE_TICK_VALUE_LOSS x pip size / SYMBOL_TRADE_TICK_SIZE`.
  On 5- and 3-digit quotes one pip is 10 ticks, so the tick value alone is
  10x too small - using it would make the position 10x too big.
- `--step`: the smallest quantity increment the venue accepts.
- `--fee-per-unit`: round-trip commission plus expected slippage per unit, so
  the stop-out loss including costs stays within budget.

If the result is 0, the risk budget is smaller than the minimum tradable size:
recommend skipping the trade or a wider risk budget, never rounding up.

## Defaults to recommend

| Situation | Guideline |
|---|---|
| Risk per trade, discretionary or new system | 0.25% - 1% of equity |
| Risk per trade, proven system with large sample | up to 1% - 2% |
| Kelly | never full Kelly; 1/4 to 1/2 of it, because win rate and payoff are estimates |
| Total open risk | cap at 4% - 6% of equity across all positions |
| Correlated positions | count them as one position (e.g. long EURUSD + long GBPUSD; BTC + ETH) |
| Daily loss limit | 2x - 3x the per-trade risk, then stop for the day |

## Review checklist (for a user's plan or a bot's code)

- [ ] Size computed from the **stop distance**, not a fixed quantity regardless of volatility.
- [ ] Quantity rounded down to the venue step; trade skipped below the minimum.
- [ ] Contract multiplier, pip value and quote currency handled (USD vs. account currency).
- [ ] Fees, spread and slippage included in the per-unit risk.
- [ ] Gap risk acknowledged: a stop is not guaranteed; overnight and weekend gaps can exceed it.
- [ ] Leverage and margin: liquidation price is well beyond the stop (perpetuals and margin accounts).
- [ ] Correlation and total open risk capped.
- [ ] No martingale or averaging down without a hard cap on size and total loss.
- [ ] Equity used is current equity (not starting balance) and updates after losses.

## Losing-streak sanity check

With win rate `w`, the chance of `k` losses in a row at some point over `n`
trades is high even for good systems. Show the user the drawdown from a
plausible streak: at 1% risk, 10 straight losses is about -9.6% (compounded);
at 5% risk it is about -40%. Pick the risk level whose worst plausible streak
the user could sit through without abandoning the system.

This is a calculator and checklist, not personal financial advice.
