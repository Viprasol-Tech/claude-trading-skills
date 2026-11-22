---
name: mql5-ea-reviewer
description: Review MQL5 Expert Advisors (MetaTrader 5 robots) for the bugs that lose money or fail broker and MQL5 Market validation - unchecked trade return codes, wrong Bid/Ask side, unnormalised prices and lots, missing stops-level, freeze-level and margin checks, magic-number collisions, hedging-account position bugs, per-tick signal noise, tester-only behaviour and risk sizing errors. Produces ranked findings with line references and fixes. Use when the user shares a .mq5 or .mqh file, asks to audit, debug or harden an EA, or asks why an EA behaves differently live than in the Strategy Tester.
---

# MQL5 EA reviewer

Read the whole EA before reporting. Every finding needs the exact line, what
goes wrong in real trading, and the fix. Facts and return codes are in
[../mql5-ea-builder/reference.md](../mql5-ea-builder/reference.md).

## Severity

| Level | Meaning |
|---|---|
| CRITICAL | Can lose money unintentionally or trade out of control: oversized lots, no stop, retry loops, closes other EAs' positions |
| HIGH | Orders fail or behave differently live vs. tester; fails MQL5 Market validation |
| MEDIUM | Fragile under some brokers, symbols or account types |
| LOW | Clarity, performance, logging |

## Checklist

### Execution
- [ ] `trade.Buy/Sell/PositionModify/...` bool treated as success without
      `ResultRetcode()` (DONE 10009, PLACED 10008, DONE_PARTIAL 10010).
- [ ] Retries without a limit, or `while(!OrderSend(...))` loops (TOO_MANY_REQUESTS
      10024, account bans). One retry for REQUOTE/PRICE_CHANGED is the ceiling.
- [ ] Filling mode hard-coded instead of `SetTypeFillingBySymbol` (INVALID_FILL 10030).
- [ ] Buy priced from Bid or sell from Ask; buy-stop/limit levels judged against
      the wrong side; SL/TP placed on the wrong side of price.
- [ ] Prices not normalised to `SYMBOL_TRADE_TICK_SIZE` (INVALID_PRICE 10015);
      `NormalizeDouble(p, _Digits)` alone on index/futures symbols.
- [ ] SL/TP closer than `SYMBOL_TRADE_STOPS_LEVEL` (INVALID_STOPS 10016);
      modifies inside `SYMBOL_TRADE_FREEZE_LEVEL` (FROZEN 10029); modifies that
      change nothing (NO_CHANGES 10025).
- [ ] No permission checks: `TERMINAL_TRADE_ALLOWED`, `MQL_TRADE_ALLOWED`,
      `ACCOUNT_TRADE_EXPERT`, `ACCOUNT_TRADE_ALLOWED`, `SYMBOL_TRADE_MODE`.

### Risk and sizing
- [ ] Lots not floored to `SYMBOL_VOLUME_STEP` or not clamped to min/max
      (INVALID_VOLUME 10014); rounded **up** to the minimum lot (adds risk).
- [ ] Risk lots from `SYMBOL_TRADE_TICK_VALUE` with point instead of tick size,
      or without `SYMBOL_TRADE_TICK_VALUE_LOSS`; wrong on crosses, metals, indices.
- [ ] No free-margin check (`OrderCalcMargin` vs `ACCOUNT_MARGIN_FREE`) - NO_MONEY 10019.
- [ ] No stop loss at all, or stop added in a second modify call (unprotected window).
- [ ] Martingale/grid without a hard cap on lots, positions and drawdown.
- [ ] No daily loss limit or equity kill switch where the user expects one.

### Position handling
- [ ] `PositionSelect(_Symbol)` on a hedging account (selects the lowest ticket only).
- [ ] Loops over positions/orders that do not filter by **symbol and magic** -
      closes or counts other EAs' or manual trades.
- [ ] Forward loops while closing (`for(i=0; i<PositionsTotal(); i++)` skips
      items); iterate backwards.
- [ ] Same default magic number in several EAs or instances.
- [ ] `OrdersTotal()` not checked against `ACCOUNT_LIMIT_ORDERS`.

### Signals and data
- [ ] Signals read from bar 0 (the forming bar) - repaints within the bar and
      differs between tester modes.
- [ ] No new-bar gate: entry logic runs on every tick (duplicate entries,
      CPU load; ticks arriving during `OnTick` are dropped, not queued).
- [ ] Indicator handles created inside `OnTick`, never checked for
      `INVALID_HANDLE`, or never released.
- [ ] `CopyBuffer` result not checked (returns -1 while the indicator calculates);
      array direction assumed without `ArraySetAsSeries`.
- [ ] Not enough history checked (`Bars()`), array index out of range, division by zero.

### Lifecycle and environment
- [ ] Globals/statics not reset in `OnInit` (stale state after a timeframe or
      inputs change).
- [ ] `EventSetTimer` without `EventKillTimer` in `OnDeinit`.
- [ ] `Sleep()` used for waiting (does nothing useful in the tester, blocks live).
- [ ] Sessions using `TimeLocal()` or a fixed GMT offset; DST not handled.
- [ ] DLL or EX5 imports (blocked in the MQL5 Market).
- [ ] `OnInit` returns `INIT_SUCCEEDED` for impossible inputs instead of
      `INIT_PARAMETERS_INCORRECT`.

### Testing
- [ ] Results only from "Open prices only" or "1 minute OHLC" for an EA that
      uses intrabar stops or ticks. Ask for "Every tick based on real ticks".
- [ ] Optimised with many parameters and no forward period - send the result
      to the `backtest-auditor` skill with the pass count as `--n-trials`.
- [ ] `OnTester` criterion that rewards a handful of lucky trades.

## Report format

```markdown
## Summary
<one paragraph: is it safe to run on a demo? what must change first?>

## Findings
| # | Severity | Line | Issue | Fix |
|---|---|---|---|---|
| 1 | CRITICAL | 142 | Lots rounded up to SYMBOL_VOLUME_MIN | Skip the trade when lots < min |

## Patch
<unified diff or the corrected functions, compilable>

## Re-test
<what to run in the Strategy Tester to confirm the fixes>
```

Offer the corrected code. If MetaEditor is installed, compile with
`metaeditor64.exe /compile:"<file>" /log` and include the log result; otherwise
say the code is uncompiled.
