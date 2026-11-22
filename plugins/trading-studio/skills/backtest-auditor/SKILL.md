---
name: backtest-auditor
description: Audit a trading backtest for the mistakes that make strategies look profitable when they are not - lookahead bias, survivorship bias, overfitting from too many trials, unrealistic fills, missing costs, and too few trades. Computes PSR, Deflated Sharpe Ratio and minimum track record with a bundled script. Use when someone shares backtest results, an equity curve, a trade list, strategy code (Python, Pine Script, MQL5, backtrader, vectorbt, freqtrade, zipline), or asks "is this strategy real", "why does live trading not match my backtest", or "can I trust this Sharpe".
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/backtest_stats.py *)
---

# Backtest auditor

Your job is to find out whether a backtest result is likely to survive live
trading, and to say so plainly. Assume the result is too good until the
evidence says otherwise. A clean "this is probably luck, here is why" is more
useful to the user than a polite summary.

## Workflow

1. **Collect what exists.** Strategy code, data source and date range, the
   instrument list, the trade list or returns series, the cost assumptions, and
   how many variations were tried before this one. If the user has not said how
   many variations they tried, ask: it decides the deflated Sharpe.
2. **Read the code for bias** using the checklist below. Quote the exact line
   for every finding.
3. **Run the numbers** on the returns or trade PnL (see "Statistics").
4. **Report** in the format at the end: verdict first, then findings ranked by
   how much they inflate the result, then concrete fixes.

## Bias checklist

Work through every item. Mark each `OK`, `FOUND` (with the line), or
`CAN'T TELL` (and what you would need to see).

### Lookahead (using information not available at decision time)
- Signals computed on the bar's close but filled at that same bar's open, or
  any fill earlier than the data that produced the signal.
- `shift(-1)`, negative indexing, `df['close'].iloc[i+1]`, centred rolling
  windows (`rolling(..., center=True)`), `bfill()` on features.
- Normalising, scaling, PCA or fitting a model on the full dataset before the
  train/test split (scaler fitted on future data).
- Higher-timeframe data joined without lagging it one completed bar. In Pine
  Script, `request.security()` with `lookahead=barmerge.lookahead_on` and no
  `[1]` offset. In Python, resampled daily data merged onto intraday bars of the
  same day.
- Stops and targets both inside one bar: the code assumes the favourable one
  filled first. On OHLC data you cannot know; assume the worse one.
- Fundamental, earnings or index-membership data used as of its period end
  instead of its publication date.
- Indicators that recalculate history (zigzag, pivots confirmed N bars later,
  repainting Pine indicators).

### Survivorship and selection
- Universe built from today's index members or today's listed coins. Delisted,
  bankrupt and merged symbols must be included for the test period.
- Symbol list hand-picked after looking at charts ("I tested on the 10 coins
  that did well").
- Start and end dates chosen to include or skip a specific crash or rally.

### Overfitting
- Count the free parameters and the variations tried. Many parameters on few
  trades is a red flag (rough rule: fewer than ~10 trades per free parameter).
- Parameters that are oddly specific (RSI 17, MA 83) or a performance surface
  that collapses one step away from the chosen value. Ask for, or run, a sweep
  of the neighbours.
- No out-of-sample period, or an out-of-sample period that was looked at and
  then the strategy was changed (it is now in-sample).
- Walk-forward or cross-validation done with shuffled folds on time series
  (leaks the future). Use purged, embargoed, time-ordered splits.

### Execution realism
- Commission, exchange fees, funding rates (perpetuals), borrow costs (shorts),
  and slippage must all be modelled. Zero cost is never acceptable.
- Fills at the close of the signal bar, at the mid price, or at limit prices
  touched but not traded through are optimistic.
- Position size larger than a small share of average volume, or trading
  illiquid hours, without market-impact assumptions.
- Leverage, margin calls and liquidation not modelled; compounding position
  size without a cap.
- Timezone and session errors: daily bars from different exchanges aligned on
  UTC dates, weekends in crypto vs. traditional markets, daylight-saving shifts.

### Sample size and regime
- Under ~30 trades, no statistic is reliable. Under ~100, treat the Sharpe as
  a rough guess.
- One regime only (for example a single bull market). Check performance by year
  and by volatility regime; one great year carrying the total is fragile.
- Results dominated by a few outlier trades: recompute without the top 5.

## Statistics

Export per-period returns (preferred) or per-trade PnL to a CSV, then run:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/backtest_stats.py returns.csv \
    --periods-per-year 252 --n-trials 50
python ${CLAUDE_SKILL_DIR}/scripts/backtest_stats.py trades.csv \
    --kind pnl --column profit --start-equity 10000 --n-trials 12
```

- `--n-trials` is the number of strategy variations the user tried in total
  (parameter sets, indicator swaps, rule tweaks), not the number kept. When in
  doubt, err high.
- `--sr-variance` is the variance of the Sharpe ratios across those trials. If
  the user has the trial results, compute it; otherwise the default (1/n) is the
  variance expected under pure noise.
- Use `--json` when you need to process the output.

How to read it:

| Metric | Meaning | Rule of thumb |
|---|---|---|
| PSR | P(true Sharpe > 0) from this sample alone | below 95%: not significant |
| DSR | PSR against the best Sharpe expected from N noise trials | the number that matters after a search |
| MinTRL | periods needed for the Sharpe to be credible at 95% | compare with how many you have |
| Skew / kurtosis | fat tails and crash risk | negative skew + high kurtosis = option-seller profile |

The method is from Bailey and Lopez de Prado, *The Sharpe Ratio Efficient
Frontier* (2012, which introduced the PSR) and *The Deflated Sharpe Ratio* (2014). For the full toolkit including
Probability of Backtest Overfitting (CSCV), point users to
[deflated-sharpe](https://github.com/Viprasol-Tech/deflated-sharpe).

## Report format

```markdown
## Verdict: <LIKELY GENUINE | POSSIBLY LUCK | NOT SIGNIFICANT | BROKEN (bias found)>
One or two sentences on why.

## Numbers
<the script's table, plus trades, years covered, costs assumed>

## Findings (most damaging first)
1. **<bias>** - `file:line` - what it does - estimated effect on returns.

## Fixes
- Concrete code or setting changes, in order.

## What would change my mind
- The specific test (out-of-sample period, cost assumption, wider universe)
  that would upgrade the verdict.
```

Never call a strategy profitable, safe or ready for live money. The strongest
honest conclusion is "no bias found and the statistics are significant after
correcting for the trials run". Add that past performance does not predict
future results when the user is about to trade it.
