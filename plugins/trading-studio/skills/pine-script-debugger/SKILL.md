---
name: pine-script-debugger
description: Fix TradingView Pine Script compile errors, runtime errors, warnings and repainting, and migrate v4/v5 scripts to Pine Script v6 - bool na errors, int-to-bool casts, removed when/transp parameters, short-circuit and/or warnings, plot in local scope, max_bars_back buffer errors, too many tokens or requests, loop time limits, and strategies whose backtest differs from live alerts. Use when the user pastes a Pine error message, a broken or old Pine script, says an indicator repaints or signals disappear, or asks to convert a script to version 6.
---

# Pine Script debugger and v6 migrator

The fix tables and limits are in
[../pine-script-writer/reference.md](../pine-script-writer/reference.md).

## Workflow

1. **Get the exact error text and line number.** If the user only says "it
   doesn't work", ask what they see: compiler error, runtime error (red icon on
   the chart), wrong values, or signals that move or vanish (repainting).
2. **Find the version** on line 1. For v4/v5 code being moved to v6, run the
   migration pass below before chasing individual errors - most errors vanish.
3. **Fix the root cause, not the symptom.** For example, a `na()` error on a
   bool means the bool's logic needs rethinking, not wrapping in `nz()`.
4. **Re-validate.** If a Pine validation tool is available (for example a
   TradingView MCP `validate-pine-script` tool), loop until there are zero
   errors and zero warnings. Otherwise say the fix is unverified.
5. **Explain each change in one line** so the user learns the rule.

## v6 migration pass (in this order)

1. Change `//@version=5` to `//@version=6`. For v4 and older, first use the
   Pine Editor's "Convert code to v5", then come back.
2. Remove `when =` from every `strategy.*` call -> wrap the call in `if`.
3. Remove `transp =` -> `color.new(col, transp)`.
4. Find bools compared to or assigned `na`, and `na()`/`nz()`/`fixnan()` on
   bools -> plain bool logic; `int` for tri-state.
5. Find numbers used as conditions (`if volume`, `x ? :` with an int) ->
   explicit comparisons or `bool(x)`.
6. Move every `ta.*`/history call out of `and`/`or` right-hand sides,
   ternaries, `if` blocks and loops into global variables.
7. Check integer division of constants (`5 / 2` is now 2.5) -> `int()` or `math.floor()`.
8. Check `timeframe.period == "D"` style comparisons -> `"1D"` / `"1W"` / `"1M"`
   or `timeframe.isdaily`.
9. Strategies: note that `margin_long`/`margin_short` now default to 100; set
   them explicitly. Check `strategy.exit()` calls that pass both `limit` and
   `profit` or both `stop` and `loss`.
10. Remove duplicate named arguments, make `linewidth >= 1`, make `offset`
    constant, store `for` loop bounds in a variable.
11. Re-validate.

## Repainting diagnosis

Ask: do signals appear and disappear on the live bar, or do historical signals
look better than what alerts actually delivered? Then check, in order:

- `request.security()` with `lookahead_on` and no `[1]` -> future leak on history.
- `request.security()` without `[1]` on a higher timeframe -> value changes
  until the higher-timeframe bar closes. Use `expr[1]` + `lookahead_on`.
- Signals without `barstate.isconfirmed` on realtime bars.
- `calc_on_every_tick`, `process_orders_on_close`, `calc_on_order_fills` set
  to true in a strategy.
- Indicators that confirm late (pivots, zigzag, `ta.pivothigh` with right bars)
  plotted on the pivot bar instead of the confirmation bar.
- `varip` logic (cannot be reproduced on history).
- Non-standard chart types (Heikin Ashi, Renko) used for backtesting.

For each cause, show the corrected line and say what the user will see
differently (usually: signals one bar later, but they stay put).

## Output

```markdown
**Cause:** <one line>
**Fix:** <corrected code block - the full script if it is under ~150 lines>
**Why:** <the v6 rule or repainting rule in one or two lines>
**Checked:** <validator result, or "not compiled - please paste into the Pine Editor">
```
