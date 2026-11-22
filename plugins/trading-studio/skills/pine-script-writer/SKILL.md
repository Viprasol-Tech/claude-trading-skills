---
name: pine-script-writer
description: Write TradingView Pine Script v6 indicators, strategies and alerts that compile first time and do not repaint - correct v6 types and short-circuit rules, non-repainting request.security() for higher timeframes, confirmed-bar signals, realistic strategy() costs, risk-based position sizing and alertcondition messages. Starts from compile-checked templates. Use when the user asks for a TradingView indicator, strategy, screener-style script, alert, Pine Script code, or to turn trading rules or another language's strategy into Pine.
---

# Pine Script v6 writer

Write Pine Script **v6** unless the user explicitly needs an older version.
Facts, limits and error messages are in [reference.md](reference.md). Start from
[templates/indicator.pine](templates/indicator.pine) or
[templates/strategy.pine](templates/strategy.pine); both compile with no errors
or warnings on TradingView's compiler.

## Before writing

Confirm in one short block: indicator or strategy; overlay or separate pane;
exact entry and exit rules; timeframe(s); inputs the user wants to tune; for
strategies, account size, fees, and sizing (% of equity at risk, default 1%).
If the rules are vague, use the `strategy-spec` skill first.

## Rules for every script

1. First line `//@version=6`. One `indicator()` or `strategy()` call.
2. **Declare types** on variables (`float`, `int`, `bool`, `string`) - it
   catches v6 type errors early and documents intent.
3. **All `ta.*` and other history-dependent calls in global scope,** assigned to
   variables, then combined. Never put them on the right of `and`/`or`, in `?:`
   branches, `if` blocks or loops: v6 short-circuits and the history breaks.
4. **Bools are never `na`.** Use `int` for tri-state. Cast numbers explicitly:
   `volume > 0`, not `volume`.
5. **No repainting.** Signals use `barstate.isconfirmed` (indicators) or
   default bar-close evaluation (strategies). Higher timeframes use only
   `request.security(sym, tf, expr[1], lookahead = barmerge.lookahead_on)`.
   Never `lookahead_on` without `[1]`.
6. **Strategies set real costs:** `commission_type`/`commission_value`,
   `slippage`, `initial_capital`, explicit sizing, `pyramiding`. Keep
   `process_orders_on_close` and `calc_on_every_tick` false.
7. No `when =` and no `transp =` (removed in v6); colours via `color.new()`.
8. `plot()` only in global scope - plot `cond ? value : na` for conditional lines.
9. Inputs: `input.int/float/bool/string/timeframe/source` with `minval`,
   `maxval`, `step` and `group`; titles in plain words.
10. Alerts: `alertcondition()` for indicators (constant message with
    placeholders like `{{ticker}}`, `{{close}}`), or `alert()` with a computed
    message inside `if` for dynamic text. Strategies can use order-fill alerts.
11. Respect limits: 64 plots, 40 unique requests, 500 drawings per type, 500 ms
    per loop. Prefer `var` + incremental updates over loops over history.
12. Add a header comment: what it does, how to use it, and that it is not
    financial advice.

## Validate

If a Pine validation tool is available (for example a TradingView MCP
`validate-pine-script` tool), run the code through it and fix every error **and
warning** before showing it. Otherwise re-read against the rules above and say
the code has not been compiled.

## Deliverable

- The complete script in one code block - no placeholders.
- How to add it: Pine Editor -> paste -> Save -> Add to chart.
- An inputs table and the exact rules in plain English.
- For strategies: the cost assumptions used, and a pointer to run the trade
  list through the `backtest-auditor` skill before trusting the results.

To fix an existing script or migrate v4/v5 code, use `pine-script-debugger`.
