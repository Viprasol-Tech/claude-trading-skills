# Contributing

Thanks for helping make trading code safer and more honest. Fixes, new skills,
better checklists and corrections are all welcome.

## Ways to help

- **Fix a fact.** Pine Script, MQL5 and exchange APIs change. If a rule, limit
  or error message is out of date, open a PR with a link to the official docs.
- **Improve a skill.** Each skill is a folder in `plugins/trading-studio/skills/`
  with a `SKILL.md` (YAML frontmatter `name` + `description`, then instructions).
- **Add a skill.** Same layout. Keep `SKILL.md` under 500 lines; put long
  reference material in a separate file linked from it.
- **Improve the scripts** in `backtest-auditor/scripts` and `position-sizing/scripts`.
  They must stay standard-library only and keep their `--self-test` passing.

## Before you open a PR

```bash
python tests/validate_repo.py
python plugins/trading-studio/skills/backtest-auditor/scripts/backtest_stats.py --self-test
python plugins/trading-studio/skills/position-sizing/scripts/position_size.py --self-test
```

For Pine Script changes, compile the templates in the TradingView Pine Editor
with zero errors and zero warnings. For MQL5 changes, compile with MetaEditor.

## Ground rules

- Accuracy over volume: cite official docs for platform facts.
- No promises of profit, no "guaranteed" or "risk-free" language.
- Never include real API keys, account numbers or personal data.
