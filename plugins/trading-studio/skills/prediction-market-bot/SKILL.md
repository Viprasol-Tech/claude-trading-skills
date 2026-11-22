---
name: prediction-market-bot
description: Build, review and size trades for prediction-market bots on Kalshi and Polymarket - binary contract maths (price as implied probability, expected value, fees, Kelly sizing), Kalshi API v2 authentication with RSA-PSS signed requests, fixed-point dollar prices and sub-penny ticks, YES/NO order book symmetry, demo vs. production hosts, order and position handling, settlement risk, and market-making pitfalls. Use when the user wants to build or debug a Kalshi or Polymarket trading bot, price an event contract, decide how many contracts to buy, or review prediction-market strategy code.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/../position-sizing/scripts/position_size.py *)
---

# Prediction-market bot helper

Binary event contracts pay a fixed amount (Kalshi: $1.00) if the event happens
and $0 if not. That makes the maths simple and the mistakes expensive. Get the
probability, fee and sizing right before writing any order code.

## Contract maths

- **Price is the market's implied probability.** YES at 38c means the market
  says about 38%. Your edge per contract is `your_prob - price - fees`.
- **YES/NO symmetry (Kalshi):** buying NO at `n` cents is economically the
  same as selling YES at `100 - n`. A NO bid at 60 is a YES ask at 40. Keep one
  internal representation (for example everything as a YES price in dollars) to avoid
  sign errors.
- **Expected value per contract** = `p * 1.00 - (price + fee)`.
- **Kalshi trading fee** (taker, general formula from Kalshi's fee schedule):
  `fee = ceil_to_cent(0.07 * C * P * (1 - P))` where `C` is contracts and `P`
  the price in dollars. It peaks at 50c: 100 contracts at $0.50 cost $1.75 in
  fees. Maker fees, where charged, use 0.0175 instead of 0.07; some markets
  carry their own multipliers or schedules, and fees apply only to matched
  orders. Always confirm the current schedule at
  <https://kalshi.com/docs/kalshi-fee-schedule.pdf>.
- Near 0c or 100c the fee is small but the payoff is lopsided: buying YES at
  95c risks 95 to make 5, so you need a true probability above ~95% plus fees.

## Sizing (Kelly for binary contracts)

```bash
python ${CLAUDE_SKILL_DIR}/../position-sizing/scripts/position_size.py \
    binary --price 0.40 --prob 0.50 --bankroll 2000 --fee 0.017
```

`--fee` is the per-contract fee as a fraction of the $1 payout (0.07 x P x (1-P)
= 0.0168 at P = 0.40). The full-Kelly fraction is
`f = (p - cost) / (1 - cost)`. Recommend **quarter Kelly or less**: the user's
probability is an estimate, and markets resolving on the same event are
correlated, so size them as one bet.

## Kalshi API essentials

Verified against Viprasol's working client
([kalshi-trading-bot](https://github.com/Viprasol-Tech/kalshi-trading-bot)) and
<https://docs.kalshi.com>:

| Item | Value |
|---|---|
| Production REST | `https://api.elections.kalshi.com/trade-api/v2` |
| Demo REST | `https://demo-api.kalshi.co/trade-api/v2` |
| Production WebSocket | `wss://api.elections.kalshi.com/trade-api/ws/v2` |
| Auth headers | `KALSHI-ACCESS-KEY` (key ID), `KALSHI-ACCESS-TIMESTAMP` (Unix **ms**), `KALSHI-ACCESS-SIGNATURE` |
| Signature | base64 RSA-PSS with SHA-256 (salt length = digest length) over `timestamp + METHOD + path` |
| Signed path | includes `/trade-api/v2`, **excludes** the query string |
| Prices and counts | Kalshi is moving to fixed-point fields: read the `*_dollars` price fields and the `_fp` count fields; the integer-cent fields are legacy and being retired. Some markets trade in sub-penny ticks, so read each market's tick structure (`price_ranges` / `price_level_structure`) instead of assuming 1c steps. See <https://docs.kalshi.com/getting_started/fixed_point_migration> and <https://docs.kalshi.com/getting_started/subpenny_pricing>. |
| Key endpoints | `GET /markets`, `GET /markets/{ticker}`, `GET /markets/{ticker}/orderbook`, `GET /portfolio/balance`, `GET /portfolio/positions`, `POST /portfolio/orders`, `DELETE /portfolio/orders/{order_id}`, `GET /portfolio/orders` |

Python signing, matching the reference client:

```python
import base64, time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def kalshi_headers(key_id, private_key, method, path):
    ts = str(int(time.time() * 1000))
    msg = f"{ts}{method.upper()}{path}".encode()          # path without ?query
    sig = private_key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {"KALSHI-ACCESS-KEY": key_id, "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode()}
```

Common auth failures: signing the URL with the query string, using seconds
instead of milliseconds, PKCS#1 v1.5 instead of PSS, a clock that has drifted,
or signing a path without the `/trade-api/v2` prefix.

## Polymarket notes

Polymarket runs a central limit order book (CLOB) settled on-chain in USDC.
Use the official client libraries and docs (<https://docs.polymarket.com>) for
order signing. Check that it is legal for the user to trade there from their
jurisdiction before building anything. Keep wallet private keys out of code and
logs (see `trading-bot-security`).

## Bot design checklist

- [ ] Develop and test on Kalshi **demo** first; production only with a flag.
- [ ] Every order carries a client order ID; a timeout triggers a lookup, not a resend.
- [ ] Prices parsed from the fixed-point `*_dollars` fields with `Decimal`, kept
      inside the market's valid range and rounded to its tick size; size capped
      per market and per event.
- [ ] Inventory limits for market makers: skew quotes as inventory grows,
      widen or pull quotes before scheduled news and near resolution.
- [ ] Positions and resting orders reconciled from the API on start-up.
- [ ] Settlement risk understood: read the market's rules (resolution source,
      timing, edge cases) - many losses come from misreading the rules, not the price.
- [ ] Fees included in every edge calculation and backtest
      (`backtest-auditor` works on the PnL series).
- [ ] Rate limits respected with backoff.

Event contracts are risky and not available everywhere. This is engineering
guidance, not advice on whether to trade.
