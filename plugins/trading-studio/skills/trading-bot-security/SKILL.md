---
name: trading-bot-security
description: Security and safety review for automated trading bots that connect to exchanges and brokers (Binance, Bybit, Coinbase, Kraken, OKX, Interactive Brokers, Alpaca, OANDA, MetaTrader bridges, Kalshi, Polymarket, TradingView webhooks) - API key storage and permissions, withdrawal rights, IP allow-lists, webhook authentication, idempotent client order IDs, duplicate and runaway orders, rate limits, reconciliation after restarts, kill switches, logging of secrets and dependency risk. Use when reviewing or hardening a trading bot, before running one with real money, or when a bot double-ordered, leaked a key or lost track of positions.
---

# Trading bot security and safety review

A trading bot holds money-moving credentials and acts without a human watching.
Review it for two failure classes: **someone else controls it** (security) and
**it does something you did not intend** (safety). Read the whole code path from
signal to order before reporting.

## Severity

| Level | Examples |
|---|---|
| CRITICAL | Keys in source or logs, withdrawal permission enabled, unauthenticated webhook that places orders, retry loop that can multiply orders, no position or loss limit |
| HIGH | No reconciliation after restart, no idempotency key, rate limits ignored, keys not IP-restricted, secrets in Docker images or CI logs |
| MEDIUM | Weak alerting, no dry-run mode, clock drift unhandled, pinned-but-outdated vulnerable dependency |
| LOW | Hygiene and clarity |

## Security checklist

### Credentials
- [ ] Keys loaded from environment or a secrets manager; never in source,
      config committed to git, notebooks, Docker images, or CI output. Search
      history too (`git log -p | grep -iE "api[_-]?key|secret"`); a key that was
      ever committed must be rotated.
- [ ] `.env`, `*.pem`, `*.key` in `.gitignore`; private keys (Kalshi RSA, wallet
      keys) stored with file permissions 600.
- [ ] Key permissions are the minimum: **trading only, withdrawals disabled**,
      no transfer/sub-account rights unless required.
- [ ] Keys restricted to the server's IP addresses where the venue supports it.
- [ ] Separate keys per bot and per environment (test vs. live).
- [ ] Logs, exceptions and error reports never print headers, signatures,
      keys or full request bodies with secrets.

### Inbound control (webhooks, dashboards, Telegram/Discord bots)
- [ ] TradingView or other webhooks carry a secret that is checked with a
      constant-time compare (`hmac.compare_digest`); the endpoint rejects
      anything else. Optionally allow-list the sender's IP ranges.
- [ ] Webhook payloads are validated (symbol, side, quantity bounds) - never
      pass a quantity from the payload straight to the exchange.
- [ ] Replay protection: timestamp or nonce checked, duplicates ignored.
- [ ] Admin dashboards and chat-bot commands require authentication and an
      allow-list of user IDs; destructive commands need confirmation.
- [ ] Services bind to `127.0.0.1` behind a reverse proxy with TLS, not `0.0.0.0`.

### Dependencies and runtime
- [ ] Dependencies pinned with a lockfile and scanned (`pip-audit`, `npm audit`).
- [ ] Exchange SDKs from the official package names (typosquatting is common
      in crypto).
- [ ] The bot runs as a non-root user with no access to unrelated secrets.

## Safety checklist

### Orders
- [ ] Every order has a **client order ID** generated before sending and
      stored, so a retry after a timeout can check whether the first attempt
      filled instead of sending a duplicate.
- [ ] Timeouts are treated as "unknown", not "failed": query the order by
      client ID before retrying.
- [ ] Retries are bounded, with backoff; HTTP 429 and exchange rate-limit
      headers respected.
- [ ] Quantity, price and notional are bounded by hard limits in code (max
      order size, max position, price within X% of last trade - a fat-finger check).
- [ ] Prices and sizes rounded to the venue's tick size and lot step, using
      the venue's symbol info, not hard-coded values.
- [ ] Stop losses are placed on the exchange (or the bot's absence is handled);
      a bot crash must not leave a position unprotected.

### State
- [ ] On start-up and periodically, positions, open orders and balances are
      **reconciled with the venue**; the exchange is the source of truth, not
      local memory.
- [ ] Partial fills handled; order state machine covers new, partially filled,
      filled, cancelled, rejected, expired.
- [ ] Clock synced (NTP); signed requests tolerate the venue's time window.
- [ ] Single instance guaranteed (a lock), or multiple instances use distinct
      client-ID prefixes and position scopes.

### Limits and kill switch
- [ ] Daily loss limit, max drawdown and max orders per minute stop the bot
      automatically and alert a human.
- [ ] A manual kill switch cancels all orders and optionally flattens positions,
      tested on a test account.
- [ ] Dry-run / paper mode uses the same code path as live except the final send.
- [ ] Alerts (Telegram, email, PagerDuty) on errors, rejections, disconnections
      and limit breaches - without secrets in the message.

## Report format

```markdown
## Summary
<Safe to run with real money? The 1-3 changes that must happen first.>

## Findings
| # | Severity | Where | Issue | Fix |
|---|---|---|---|---|

## Patch
<code for the critical and high fixes>

## Operational steps
<key rotation, permission changes on the exchange, IP allow-list - things the user must do in the venue's UI>
```

Do not test against live accounts. Never print, store or transmit a real key
while reviewing; if you find one, tell the user to rotate it immediately.
