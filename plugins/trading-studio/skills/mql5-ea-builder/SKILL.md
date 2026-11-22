---
name: mql5-ea-builder
description: Build MetaTrader 5 Expert Advisors (MQL5 trading robots) that survive real brokers - closed-bar signals, risk-based lot sizing, ATR or fixed stops, CTrade execution with return-code checks, hedging and netting safe position handling, spread and daily-loss filters, and the pre-trade checks the MQL5 Market validator requires. Starts from a complete template. Use when the user asks to create, write, convert or extend an MT5 EA, an MQL5 expert, a forex/gold/indices trading robot, or to port a TradingView/Pine strategy or Python strategy to MT5.
---

# MQL5 Expert Advisor builder

Build EAs that compile cleanly, behave the same in the Strategy Tester and on a
live account, and never take more risk than the user asked for.

Read [reference.md](reference.md) before writing code: it holds the event
model, CTrade behaviour, return codes, pre-trade checks and lot formula, with
links to the MQL5 docs. Start from [templates/EA_Template.mq5](templates/EA_Template.mq5),
which already implements everything in the "Non-negotiables" list.

## 1. Pin down the strategy first

Before coding, write the rules back to the user in one short block and get a
yes. If anything is vague, use the `strategy-spec` skill. You need:

- Symbol(s) and timeframe; whether it may run on several charts at once.
- Entry rules evaluated on **closed** bars (state which bar index).
- Exit rules: stop loss, take profit, trailing, time exit, opposite signal.
- Sizing: % of equity at risk per trade (default 1%), or fixed lots.
- Filters: sessions (in **server** time), max spread, news avoidance, days.
- Limits: max open positions, max daily loss, max trades per day.
- Account type: hedging or netting (or support both).

## 2. Non-negotiables in every EA

1. **Closed-bar logic.** Signals read `CopyBuffer(..., start_pos = 1, ...)`;
   gate entries with a new-bar check. Tick-level work only for exits and trailing.
2. **Handles in `OnInit`, released in `OnDeinit`,** checked against
   `INVALID_HANDLE`; return `INIT_FAILED` on failure and
   `INIT_PARAMETERS_INCORRECT` for impossible inputs (fast >= slow period, risk <= 0).
3. **Reset globals in `OnInit`** - a timeframe or inputs change re-initialises
   the same program.
4. **CTrade configured once:** magic number, deviation, `SetTypeFillingBySymbol`.
5. **Check `ResultRetcode()`,** not just the bool. Success = DONE, PLACED,
   DONE_PARTIAL. Log the code and `ResultRetcodeDescription()` otherwise. Retry
   only REQUOTE / PRICE_CHANGED, once, with a fresh price - never in a loop.
6. **Permissions** (terminal, program, account, symbol trade mode) checked
   before sending.
7. **Prices** normalised to tick size; **lots** floored to `SYMBOL_VOLUME_STEP`,
   clamped to min/max, trade skipped if below min (never rounded up into extra risk).
8. **Risk lots** from `SYMBOL_TRADE_TICK_VALUE_LOSS` and tick size.
9. **Stops level** respected; **free margin** checked with `OrderCalcMargin`.
10. **Positions filtered by symbol and magic** with a `PositionGetTicket` loop,
    so the EA is safe on hedging accounts and next to other EAs.
11. **Buy at Ask, sell at Bid;** remember a long's SL triggers on Bid.
12. **Server time** for sessions (`TimeCurrent()`), never `TimeLocal()` or a
    hard-coded GMT offset.
13. **No `Sleep()` loops, no DLLs,** no unbounded arrays, guard every division.
14. An `OnTester()` criterion that rejects tiny samples (the template returns 0
    under 30 trades).

## 3. Build steps

1. Copy the template, rename the file, set `#property` lines and a unique
   default magic number.
2. Replace the signal block in `OnTick` with the user's rules. Keep all reads
   on bar index 1 (last closed) and 2 (the one before).
3. Add exits: trailing in a per-tick section before the new-bar gate if the
   user wants it; modify only when the new stop is better by at least one tick
   and outside the freeze level (avoid `NO_CHANGES` 10025 spam).
4. Add each filter as a small `bool` function, like `TradingAllowed()`.
5. Group inputs with `input group`, give every input a comment (it becomes the
   label in the inputs dialog), and validate them in `OnInit`.
6. Compile. If MetaEditor is available on the machine:

   ```bat
   "C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"<full path>\MyEA.mq5" /log
   ```

   then read `MyEA.log` and fix every error and warning. If you cannot compile,
   say so and list what the user should check.

## 4. Testing plan to hand over

Give the user this plan with the EA:

1. Strategy Tester, **Every tick based on real ticks**, at least 2 years,
   realistic spread, Random delay on.
2. Forward period: 1/3 of the range held out (Settings -> Forward).
3. If optimising: few parameters, wide steps, then check that neighbouring
   values also work (a single sharp peak is overfitting). Run the results
   through the `backtest-auditor` skill with the number of passes as `--n-trials`.
4. Demo account for at least 2-4 weeks before any live money.

## 5. Deliverable

- The `.mq5` file, complete and compilable - no `...` placeholders.
- A table of inputs with defaults and meaning.
- The rules in plain English, and the known limitations.
- The testing plan above.

To review an existing EA instead, use the `mql5-ea-reviewer` skill. For an
on-chart dashboard in the Viprasol style, Viprasol Tech builds these to order:
<https://viprasol.com>.

Trading involves risk. The EA is a tool, not a promise of profit.
