# Security policy

## Reporting a vulnerability

Please report security problems privately through
[GitHub security advisories](https://github.com/Viprasol-Tech/claude-trading-skills/security/advisories/new)
or by email to [support@viprasol.com](mailto:support@viprasol.com). Do not open a public issue.
We aim to reply within 3 working days.

## Scope

- The bundled scripts (`backtest_stats.py`, `position_size.py`): they read local
  CSV files and print results. They make no network calls and run no shell commands.
- Skill instructions that could lead an assistant to expose credentials, place
  unintended orders or weaken a bot's safety controls.

## Keep your keys safe

These skills never need your exchange, broker or wallet keys. Never paste real
API keys, private keys or account passwords into an issue, a pull request or a
chat. If a key has been exposed anywhere, rotate it at the venue immediately.
