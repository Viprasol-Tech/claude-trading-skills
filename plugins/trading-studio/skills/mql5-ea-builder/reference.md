# MQL5 Expert Advisor reference

Facts checked against the official MQL5 documentation (mql5.com/en/docs) and the
MetaTrader 5 help. Lines marked *(practice)* are established community practice
rather than a documentation quote.

## Event handlers

Source: <https://www.mql5.com/en/docs/basis/function/events>

| Handler | Notes |
|---|---|
| `int OnInit()` | Return `INIT_SUCCEEDED` (0). `INIT_FAILED` unloads the EA (use when an indicator handle fails). `INIT_PARAMETERS_INCORRECT` rejects an input set; in optimisation that pass is skipped. `INIT_AGENT_NOT_SUITABLE` stops that agent getting more tasks. |
| `void OnDeinit(const int reason)` | Runs before unload and before re-init on a symbol/timeframe/inputs change. Release handles, kill timers. Re-init reuses the program, so reset globals and statics in `OnInit` *(practice)*. |
| `void OnTick()` | New ticks that arrive while `OnTick` is still running are **ignored**, not queued (<https://www.mql5.com/en/docs/runtime/event_fire>). Keep it fast. |
| `void OnTimer()` | `EventSetTimer(seconds)` once in `OnInit`, `EventKillTimer()` in `OnDeinit`. |
| `void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& request, const MqlTradeResult& result)` | `request`/`result` are filled only for `TRADE_TRANSACTION_REQUEST`. Arrival order is not guaranteed. |
| `double OnTester()` | Called just before `OnDeinit` in the tester; its value is the "Custom max" optimisation criterion (higher is better). |

## Indicator handles

- `iMA`, `iRSI`, `iATR`, `iCustom`, ... return a **handle**. Create once in
  `OnInit`, check against `INVALID_HANDLE`, return `INIT_FAILED` if invalid.
- Read values with `CopyBuffer(handle, buffer, start_pos, count, array)`.
  `start_pos = 0` is the current (forming) bar. It returns the count copied or
  `-1`, and returns `-1` while the indicator is still calculating
  (`BarsCalculated(handle)`). Source: <https://www.mql5.com/en/docs/series/copybuffer>
- CopyBuffer always writes oldest first. Call `ArraySetAsSeries(arr, true)` so
  `arr[0]` is the newest bar.
- Use the **closed** bar (`[1]`) for signals; `[0]` changes on every tick.
- `IndicatorRelease(handle)` in `OnDeinit` (it is a no-op in the tester).

## Trading with CTrade

`#include <Trade\Trade.mqh>` - <https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade>

- Configure once: `SetExpertMagicNumber(magic)`, `SetDeviationInPoints(n)`,
  `SetTypeFillingBySymbol(_Symbol)`.
- `trade.Buy(...)` returning `true` only means the request passed basic checks;
  the docs say it "does not always mean successful execution". Always check
  `trade.ResultRetcode()` and `trade.ResultDeal()` / `ResultOrder()`.
- Filling modes: `SYMBOL_FILLING_MODE` is a flag set (`SYMBOL_FILLING_FOK` = 1,
  `SYMBOL_FILLING_IOC` = 2, `SYMBOL_FILLING_BOC` = 4). `ORDER_FILLING_RETURN` is
  not allowed in Market Execution. A wrong mode returns `INVALID_FILL` (10030);
  `SetTypeFillingBySymbol` avoids it.

### Trade return codes (prefix `TRADE_RETCODE_`)

Source: <https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes>

| Code | Name | Meaning / action |
|---|---|---|
| 10009 | DONE | success |
| 10008 | PLACED | pending order accepted (success) |
| 10010 | DONE_PARTIAL | partly filled (success, handle the remainder) |
| 10004 | REQUOTE | retry once with a fresh price *(practice)* |
| 10020 | PRICE_CHANGED | retry once with a fresh price *(practice)* |
| 10021 | PRICE_OFF | no quotes; wait for the next tick |
| 10006 | REJECT | rejected |
| 10014 | INVALID_VOLUME | lots not on step / outside min-max |
| 10015 | INVALID_PRICE | price not normalised to tick size |
| 10016 | INVALID_STOPS | SL/TP inside the stops level or wrong side |
| 10017 | TRADE_DISABLED | trading disabled for the symbol |
| 10018 | MARKET_CLOSED | outside session |
| 10019 | NO_MONEY | not enough margin |
| 10024 | TOO_MANY_REQUESTS | back off; do not loop |
| 10025 | NO_CHANGES | modify with the same SL/TP; do not send |
| 10029 | FROZEN | inside the freeze level |
| 10030 | INVALID_FILL | wrong filling mode |
| 10031 | CONNECTION | no connection |
| 10033 / 10034 / 10040 | LIMIT_ORDERS / LIMIT_VOLUME / LIMIT_POSITIONS | broker limits reached |
| 10044 / 10045 / 10046 | CLOSE_ONLY / FIFO_CLOSE / HEDGE_PROHIBITED | account rules (FIFO, no hedging) |

## Checks before every order

From "The checks a trading robot must pass before publication in the Market"
(<https://www.mql5.com/en/articles/2555>), which the MQL5 Market runs on every
submission, plus the trade-permission docs
(<https://www.mql5.com/en/docs/runtime/tradepermission>):

1. **Permissions:** `TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)`,
   `MQLInfoInteger(MQL_TRADE_ALLOWED)`, `AccountInfoInteger(ACCOUNT_TRADE_EXPERT)`,
   `AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)`, `TerminalInfoInteger(TERMINAL_CONNECTED)`,
   and `SYMBOL_TRADE_MODE` (`DISABLED`, `LONGONLY`, `SHORTONLY`, `CLOSEONLY`, `FULL`).
2. **Volume:** within `SYMBOL_VOLUME_MIN` .. `SYMBOL_VOLUME_MAX`, a multiple of
   `SYMBOL_VOLUME_STEP`, and within `SYMBOL_VOLUME_LIMIT` (all positions plus
   pending orders in one direction) when it is non-zero.
3. **Margin:** `OrderCalcMargin()` vs `AccountInfoDouble(ACCOUNT_MARGIN_FREE)`.
   `OrderCheck()` returning true only means the structure is valid; read
   `MqlTradeCheckResult.retcode`.
4. **Stops level:** SL/TP at least `SYMBOL_TRADE_STOPS_LEVEL` points away - for
   a buy position measured from Bid, for a sell from Ask, for pending orders
   from the activation price.
5. **Freeze level:** do not modify or close orders within
   `SYMBOL_TRADE_FREEZE_LEVEL` points of the activation price.
6. **Pending order count:** `OrdersTotal() < AccountInfoInteger(ACCOUNT_LIMIT_ORDERS)`
   (0 means unlimited).
7. **No no-op modifies** (they return 10025), no DLL/EX5 imports, guard every
   division and array access, check that enough history has loaded.

## Prices, lots and risk

- Buy at **Ask**, sell at **Bid**. Charts show Bid, so a long's SL/TP triggers
  when Bid reaches it; a short's when Ask reaches it.
- Round prices to the **tick size**, not just digits:
  `NormalizeDouble(MathRound(p / tick) * tick, _Digits)` with
  `tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE)`. `NormalizeDouble(p, _Digits)`
  alone fails on instruments where tick size is not one point *(practice)*.
- Round lots **down**: `MathFloor(lots / step) * step`, clamp to min/max,
  refuse the trade if below min.
- Risk-based lots: `lots = riskMoney / ((MathAbs(entry - sl) / tickSize) * tickValueLoss)`
  with `tickValueLoss = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS)`
  (the docs define this as the tick price for a losing position; plain
  `SYMBOL_TRADE_TICK_VALUE` is the profit value). Cross-check with
  `OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, 1.0, entry, sl, loss)` on crosses and
  metals *(practice)*.

## New bar, hedging and netting

- New bar: store the last bar time from `iTime(_Symbol, _Period, 0)` (returns 0
  on error) or `SeriesInfoInteger(_Symbol, _Period, SERIES_LASTBAR_DATE)` and
  act when it changes (<https://www.mql5.com/en/articles/159>). Do entries and
  indicator reads once per bar; keep per-tick work to exits and trailing.
- `ACCOUNT_MARGIN_MODE`: on `ACCOUNT_MARGIN_MODE_RETAIL_NETTING` and
  `..._EXCHANGE` there is one position per symbol and `PositionSelect(_Symbol)` works.
  On `..._RETAIL_HEDGING`, `PositionSelect` returns the position with the lowest
  ticket, so loop instead:

```mql5
for(int i = PositionsTotal() - 1; i >= 0; i--)
  {
   ulong ticket = PositionGetTicket(i);
   if(ticket == 0) continue;
   if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
   if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
   // this position belongs to this EA on this symbol
  }
```

## Strategy Tester

Sources: <https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation>,
<https://www.mql5.com/en/docs/runtime/testing>

| Mode | Valid for |
|---|---|
| Every tick based on real ticks | final validation; closest to live (uses the broker's tick history) |
| Every tick | generated from M1; accurate but slow |
| 1 minute OHLC | only if entries and exits do not depend on movement inside a minute |
| Open prices only | only EAs that act strictly on bar open; stops/pendings may fill at other prices |

- Fast modes can look much better than reality. Confirm every result in
  "Every tick based on real ticks" with realistic delays.
- Use the Forward setting (1/2, 1/3, 1/4 or a custom date) to hold back an
  out-of-sample period.
- In the tester: `Sleep()` advances simulated time instead of waiting;
  `TimeLocal()` equals server time and GMT; Print/Comment are skipped during
  optimisation; Alert, SendMail, SendNotification and WebRequest do nothing;
  spread comes from history; multi-symbol bars are not synchronised.

## Command-line compile

Source: <https://www.metatrader5.com/en/metaeditor/help/beginning/integration_ide>

```bat
"C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"C:\...\MQL5\Experts\MyEA.mq5" /log
```

`/log` writes `MyEA.log` next to the source; read its last line for the error
and warning counts. `/s` with `/log` runs a syntax check only. Add include roots
with `/include:"C:\path\to\MQL5"`.
