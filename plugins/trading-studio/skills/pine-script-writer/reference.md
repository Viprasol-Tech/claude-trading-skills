# Pine Script v6 reference

Checked against the TradingView Pine Script docs (November 2026). Error strings
in quotes are real compiler output. Main pages:

- Migration to v6: <https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/>
- Limitations: <https://www.tradingview.com/pine-script-docs/writing/limitations/>
- Errors: <https://www.tradingview.com/pine-script-docs/errors/overview/>
- Repainting: <https://www.tradingview.com/pine-script-docs/concepts/repainting/>
- Strategies: <https://www.tradingview.com/pine-script-docs/concepts/strategies/>

## v5 -> v6 breaking changes

| Change | What breaks | Fix |
|---|---|---|
| Dynamic requests on by default | Rare: one `request.security()` result used inside another request's expression behaves differently. Code that sets `dynamic_requests = false` and calls `request.*()` in loops/ifs no longer compiles. | Add `dynamic_requests = false`, or remove it when requests are in local scopes. |
| No automatic number -> bool | `bar_index ? a : b`, `if volume`: "An argument of "series int" type was used but a "const bool" is expected." | `bool(x)` or `x != 0`. |
| `bool` can never be `na` | `bool b = na`: "Cannot assign a value of the "simple na" type...". `na(myBool)`: "...An argument of "series bool" type was used but a "simple float" is expected." | Remove `na()/nz()/fixnan()` on bools. Use an `int` (-1/0/1) for three states. An `if`/`switch` with no matching branch now returns `false`; `b[1]` on the first bar is `false`. |
| `and` / `or` short-circuit | The right side may not run, so `ta.*` calls there get inconsistent history (compiler warning about calls "inside the conditional expression"). | Compute every `ta.*` result in global scope first, then combine. |
| Const integer division is float | `5 / 2` is `2.5` (was `2`). | `int(5 / 2)`, `math.floor()`, `math.round()`. |
| `when` removed from `strategy.*` | "The "strategy.entry" function does not have an argument with the name "when"". | Wrap the call in `if cond`. |
| `transp` removed | "The "plot" function does not have an argument with the name "transp"". | `color.new(col, transp)`. |
| `margin_long` / `margin_short` default 100 | Orders bigger than equity are rejected and shorts can be margin-called (v5 default 0 = unlimited). | Size from equity, or set both to 0 deliberately. |
| `timeframe.period` always numeric | `"D"` is now `"1D"`, `"W"` -> `"1W"`, `"M"` -> `"1M"`. String comparisons fail. | Compare against `"1D"` or use `timeframe.isdaily` etc. |
| 9,000-order limit trims oldest | Old trades disappear instead of the script stopping; `strategy.closedtrades.*(i)` returns `na` for them. | Start loops at `strategy.closedtrades.first_index`. |
| `strategy.exit()` price vs. tick params | With both `limit`/`profit` (or `stop`/`loss`) v6 uses whichever is hit first; v5 used the price one. | Pass only one of each pair. |
| Duplicate arguments are errors | "Two or more arguments are passed to the "title" parameter." | Remove the duplicate. |
| `linewidth` must be >= 1 | "The "plot()" function requires a positive "linewidth" value." | Use 1 or more. |
| `offset` no longer accepts series | Dynamic offsets fail. | Use a constant/input offset. |
| `for` re-evaluates `to_num` each iteration | An expression in the bound can change mid-loop or never end. | Store the bound in a variable first. |
| History on literals/fields | `obj.field[10]` is invalid. | `(obj[10]).field`. |
| Negative array indexes work | `array.get(a, -1)` now returns the last element instead of erroring. | Check code that relied on the error. |
| Default colours changed | `color.red` is `#F23645`, `color.teal` `#089981`, `color.yellow` `#FDD835`; `label.new()` text is white. | Set explicit colours if exact shades matter. |

## Repainting rules

- **Higher timeframe without repainting** (the documented idiom):
  `request.security(sym, tf, expr[1], lookahead = barmerge.lookahead_on)`.
  The `[1]` and `lookahead_on` only work together. `lookahead_on` without `[1]`
  reads future data on historical bars and is not allowed in published scripts.
- **Confirmed signals:** `cond and barstate.isconfirmed` - fires once when the
  bar closes; historical bars always count as confirmed.
- Realtime bars change until they close; history only has final OHLC.
  `barstate.isnew` is true at a historical bar's close but at a realtime bar's open.
- `varip` state cannot be reproduced on history, so it cannot be backtested.
- `calc_on_every_tick = true` differs between history and realtime; keep it
  `false` for backtests.
- `process_orders_on_close = true` fills at the signal bar's close - the docs
  call this "typically unrealistic". `calc_on_order_fills = true` can see the
  bar's final OHLC after a fill (lookahead). Trailing stops on history use an
  assumed intrabar path.
- Broker emulator path: open -> high -> low -> close if the open is nearer the
  high, else open -> low -> high -> close. No intrabar gaps.

## `strategy()` settings for realistic backtests

| Parameter | Default | Set it to |
|---|---|---|
| `initial_capital` | 1,000,000 | the user's real account size |
| `default_qty_type` / `default_qty_value` | `strategy.fixed` / 1 | explicit sizing, or compute `qty` per order |
| `commission_type` / `commission_value` | percent / **0** | the broker's real fee (never 0) |
| `slippage` | **0** ticks | at least 1-2 ticks; more for illiquid symbols |
| `pyramiding` | 1 | 0 or 1 unless scaling in is intended |
| `margin_long` / `margin_short` | 100 | 100 for cash accounts; the real leverage otherwise |
| `use_bar_magnifier` | false | true where the plan allows (lower-timeframe fills) |
| `fill_orders_on_standard_ohlc` | false | true if the user insists on Heikin Ashi charts |
| `process_orders_on_close` | false | false |
| `calc_on_every_tick` | false | false |

Heikin Ashi, Renko, Kagi, line break, point & figure and range charts distort
prices or time; backtest on standard candles.

## Hard limits

| Item | Limit |
|---|---|
| Plot count | 64 (one call may use up to 7) |
| Lines / labels / boxes | last 50 kept by default, `max_*_count` up to 500 each |
| Polylines | default 50, max 100 |
| Tables | 9 (one per position) |
| Unique `request.*()` calls | 40 (64 on Ultimate); identical calls are reused; library calls count |
| Tuple elements across requests | 127 |
| Loop time | 500 ms per loop on one bar |
| History buffer | up to 5,000 bars for most series; OHLC/time up to 10,000 (`max_bars_back`) |
| Compiled tokens | 100,256 per script |
| Variables per scope | 1,200 |
| Collections | 100,000 elements (maps 50,000 pairs) |
| Strings | 40,960 characters |
| Orders kept | 9,000 (oldest trimmed) |
| Drawings with `xloc.bar_index` | 10,000 bars back, 500 forward |
| Compile time | 2 minutes |

## Common errors

| Error | Fix |
|---|---|
| "Cannot use "plot" in local scope" | Keep `plot()` global; plot `cond ? v : na` with `plot.style_linebr`. Drawings (`line.new`, `label.new`) are fine locally. |
| CE10101 "The condition of the "X" statement must evaluate to a "bool" value" | Make the condition a real bool (`x != 0`). |
| CW10003 "The function "X" should be called on each calculation for consistency" | Move the `ta.*` call to global scope and use the result. |
| RE10143 "The requested historical offset (X) is beyond the historical buffer's limit (Y)" | `max_bars_back(series, n)` or the `max_bars_back` declaration parameter. |
| CE10117 "Compiled code contains too many tokens" | Remove embedded data, use functions and loops, or split into libraries. |
| RE10139 "Memory limits exceeded" | Fewer or smaller `request.*()` results, smaller arrays. |
| Loop takes longer than 500 ms | Cheaper algorithm, fewer nested loops, compute incrementally with `var`. |
| Too many `request.*()` calls | Reuse identical requests, return tuples, drop symbols. |
| "Cannot use a mutable variable as an argument of the security function" | v3/v4-era error that v6 does not raise: a `var` accumulator passes to `request.security()` without error. |
