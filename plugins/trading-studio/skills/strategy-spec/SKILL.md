---
name: strategy-spec
description: Turn a vague trading idea into a precise, testable strategy specification - market and timeframe, exact entry and exit rules on closed bars, stops, targets, position sizing, filters, sessions, costs and the backtest plan - so it can be coded the same way in Pine Script, MQL5, Python or any platform without guesswork. Use when someone describes a strategy in words ("buy when RSI is oversold and price is above the 200 EMA"), shares a YouTube or forum strategy, asks to code a strategy but the rules are ambiguous, or wants a spec to hand to a developer.
---

# Strategy spec writer

Ambiguity is where strategies quietly change between the idea, the backtest and
live trading. Your output is a spec so exact that two developers coding it
independently would produce the same trades.

## Interview (only what is missing)

Ask in one message, grouped, skipping anything the user already said:

1. **Market:** symbols, exchange/broker, timeframe, trading hours and timezone.
2. **Direction:** long only, short only, or both; can it flip directly?
3. **Entry:** every condition, with indicator settings and the price source;
   which bar it is checked on (close of the signal bar); the order type (market
   on next open, limit at X, stop at Y) and how long a pending order lives.
4. **Exit:** stop loss (fixed, ATR, structure), take profit, trailing rules,
   time exit, exit on opposite signal, end-of-day/weekend flat.
5. **Sizing:** % of equity at risk per trade, max position, max open trades,
   max exposure per symbol and in total.
6. **Filters:** trend, volatility, spread, session, news, day of week.
7. **Risk limits:** daily loss, weekly loss, max drawdown kill switch.
8. **Costs:** commission, spread, slippage, funding/swap.
9. **Evidence:** where the idea came from and what was already tested.

Where the user does not care, choose a sensible default and **mark it as an
assumption** in the spec.

## Precision rules

- Name every number: "RSI(14) on close < 30", never "RSI oversold".
- Say when each condition is evaluated: "at the close of the signal bar".
- Crossovers: "fast EMA was <= slow EMA on bar N-1 and > slow EMA on bar N".
- Same-bar conflicts: what if stop and target are both touched in one bar
  (assume the stop); what if an entry and exit signal fire together.
- Gaps: what happens when price opens beyond the stop.
- Re-entry: can it re-enter on the next bar after a stop-out?
- Timezones: state the timezone of every session rule.

## Spec template

```markdown
# <Strategy name> - specification v1

## Summary
<2 sentences: the market behaviour it tries to capture>

## Universe and data
- Symbols: ...   Timeframe: ...   Session: ... (timezone)
- Data source and history needed: ...

## Indicators
| Name | Settings | Source |
|---|---|---|

## Entry (evaluated at the close of bar N)
Long when ALL of:
1. ...
Order: market at the open of bar N+1 (or: limit at ..., valid for K bars)

Short when ALL of: ...

## Exit
- Stop: ...   (checked intrabar; if stop and target both hit in a bar, assume stop)
- Target: ...
- Trailing: ...
- Time / session exit: ...
- Opposite signal: close / reverse / ignore

## Position sizing and limits
- Risk per trade: X% of equity; quantity = risk money / (stop distance x value per point), rounded down
- Max open positions: ...   Daily loss limit: ...   Kill switch: ...

## Costs assumed
Commission ..., spread ..., slippage ... ticks, funding/swap ...

## Assumptions (please confirm)
- ...

## Backtest plan
- In-sample: <dates>   Out-of-sample: <dates, untouched until the end>
- Parameters to vary and their ranges (keep it to 2-3)
- Success criteria decided now: e.g. DSR >= 95%, max drawdown < 20%, >= 100 trades
```

Then offer the next step: `pine-script-writer` or `mql5-ea-builder` to code it,
`position-sizing` to check the sizing, and `backtest-auditor` once results exist.
