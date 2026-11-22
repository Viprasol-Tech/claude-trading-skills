---
name: trade-journal
description: Analyse a real trade history or broker export (MT4/MT5 account history, TradingView strategy tester list of trades, Binance/Bybit/Coinbase trade CSV, Interactive Brokers flex report, Kalshi fills) to find what actually makes and loses money - R-multiples, expectancy, win rate and payoff by setup, symbol, side, weekday and hour, cost drag, holding time, drawdown and losing streaks, rule breaks, and whether live results match the backtest. Uses the backtest-auditor statistics script. Use when someone shares their trading history, asks why they are losing, wants a trading journal review, or compares live performance with a backtest.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/../backtest-auditor/scripts/backtest_stats.py *)
---

# Trade journal analyst

Turn a raw trade export into a short list of things the trader should keep,
stop and change. Be specific and evidence-based; every claim points to numbers.

## 1. Load and normalise

Find or ask for these columns, whatever the export calls them:

| Field | Typical names |
|---|---|
| open time, close time | `Open Time`, `Time`, `Date/Time`, `Entry time` |
| symbol, side | `Symbol`, `Type` (buy/sell), `Side`, `Direction` |
| quantity | `Volume`, `Lots`, `Qty`, `Contracts` |
| entry, exit price | `Price`, `Open Price`, `Close Price`, `Avg Price` |
| net profit | `Profit` + `Commission` + `Swap` (MT5 keeps them separate), `Realized PnL`, `Net P&L` |
| initial stop (if any) | `S/L`, or from the user's notes |

- Convert all times to one timezone and say which.
- Use **net** PnL (after commission, swap/funding and fees).
- Merge partial closes into one trade where the export splits them.
- Drop deposits, withdrawals, transfers and balance adjustments.

Write a normalised CSV (one row per trade) to a working file before analysing,
and show the user the first rows to confirm the mapping.

## 2. Core statistics

```bash
python ${CLAUDE_SKILL_DIR}/../backtest-auditor/scripts/backtest_stats.py trades.csv \
    --kind pnl --column net_pnl --start-equity <starting balance>
```

This gives win rate, profit factor, expectancy, max drawdown, the longest
losing streak and whether the edge is statistically distinguishable from zero
(PSR). Under 30 trades, say clearly that conclusions are tentative.

## 3. Breakdowns (compute with pandas or plain Python)

For each group show trades, win rate, average win, average loss, expectancy and
total net PnL:

- by **setup / strategy tag** (if the user tags trades) - the most useful split
- by symbol, by side (long vs. short)
- by weekday and by hour of entry (in the trader's timezone)
- by holding time bucket (minutes, hours, days)
- by position size bucket (do bigger trades lose more?)
- R-multiples when stops are known: `R = net PnL / initial risk`. Show the R
  distribution and the average R.

Also compute:

- **Cost drag:** total fees + swap + funding as a % of gross profit.
- **Best and worst 5 trades** and the result *without* the best 5 (is the
  edge carried by a few outliers?).
- **After-loss behaviour:** expectancy of the trade following a loss vs.
  following a win (revenge trading shows up here); trades per day on losing
  days vs. winning days.
- **Equity curve and drawdown periods** with start/end dates.

## 4. Live vs. backtest (if both exist)

Compare win rate, average win/loss, trade frequency and costs. A drop of more
than ~30% in expectancy usually means slippage/fees were under-modelled, the
backtest had lookahead bias, or the trader is not following the rules. Send the
backtest to the `backtest-auditor` skill if it has not been audited.

## 5. Report

```markdown
## Snapshot
<period, trades, net PnL, win rate, profit factor, expectancy, max drawdown, PSR>

## What is working (keep doing)
- <setup / symbol / time with numbers>

## What is costing money (stop or fix)
- <with numbers, e.g. "Trades after 2 losses in a row: 41 trades, -0.6R average, -$2,310">

## Changes to test next
1. <one concrete rule change, how to measure it, for how many trades>

## Caveats
<sample size, missing data, assumptions made in mapping the export>
```

Do not tell the user to trade more, add leverage, or that a pattern will
continue. This is a review of past performance, not financial advice.
