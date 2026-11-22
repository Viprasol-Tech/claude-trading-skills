# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-22

### Added
- `trading-studio` Claude Code plugin with 10 skills: `pine-script-writer`,
  `pine-script-debugger`, `mql5-ea-builder`, `mql5-ea-reviewer`,
  `backtest-auditor`, `strategy-spec`, `position-sizing`,
  `trading-bot-security`, `trade-journal`, `prediction-market-bot`.
- Compile-checked Pine Script v6 indicator and strategy templates.
- MQL5 Expert Advisor template with risk-based lots and MQL5 Market pre-trade checks.
- `backtest_stats.py` (Sharpe, Sortino, drawdown, PSR, Deflated Sharpe, MinTRL)
  and `position_size.py` (fixed-fractional, futures, forex, Kelly, binary
  contracts, ATR stops), both standard-library only with self-tests.
- Plugin marketplace manifest, installers for Windows/macOS/Linux, and CI that
  validates every skill and runs the script self-tests.
