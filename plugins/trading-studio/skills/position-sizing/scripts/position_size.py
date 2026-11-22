#!/usr/bin/env python3
"""Position sizing calculator for stocks, futures, crypto, forex and binary contracts.

Part of claude-trading-skills by Viprasol Tech Private Limited.

Sizes are always rounded DOWN to the instrument's step, so the money at risk
never exceeds what you asked for. Standard library only.
Run ``python position_size.py --self-test`` to check it.

Examples:
  python position_size.py risk --equity 25000 --risk-pct 1 --entry 182.50 --stop 178.00
  python position_size.py risk --equity 50000 --risk-pct 0.5 --entry 5300 --stop 5285 \
      --multiplier 50 --step 1                          # ES futures, $50 per point
  python position_size.py forex --equity 10000 --risk-pct 1 --stop-pips 25 --pip-value 10
  python position_size.py kelly --win-rate 0.55 --payoff 1.2
  python position_size.py binary --price 0.40 --prob 0.50 --bankroll 2000
  python position_size.py atr-stop --entry 100 --atr 2.5 --mult 2 --side long
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from decimal import ROUND_FLOOR, Decimal


def floor_to_step(qty: float, step: float) -> float:
    """Round qty down to a multiple of step without float drift (0.07 / 0.01 -> 0.07)."""
    if step <= 0:
        raise ValueError("step must be positive")
    q, s = Decimal(str(qty)), Decimal(str(step))
    return float((q / s).to_integral_value(rounding=ROUND_FLOOR) * s)


def risk_size(
    equity: float,
    risk_pct: float,
    entry: float,
    stop: float,
    multiplier: float = 1.0,
    step: float = 1.0,
    min_qty: float = 0.0,
    max_qty: float | None = None,
    fee_per_unit: float = 0.0,
) -> dict[str, float | str]:
    """Fixed-fractional sizing: lose at most risk_pct of equity if the stop is hit."""
    if equity <= 0 or not 0 < risk_pct <= 100:
        raise ValueError("equity must be positive and risk_pct in (0, 100]")
    per_unit = abs(entry - stop) * multiplier + fee_per_unit
    if per_unit <= 0:
        raise ValueError("entry and stop must differ")
    budget = equity * risk_pct / 100.0
    qty = floor_to_step(budget / per_unit, step)
    if max_qty is not None:
        qty = min(qty, floor_to_step(max_qty, step))
    note = "ok"
    if qty < min_qty or qty <= 0:
        qty, note = 0.0, "risk budget is below the minimum tradable size: skip the trade or widen risk"
    return {
        "quantity": qty,
        "risk_per_unit": per_unit,
        "risk_budget": budget,
        "money_at_risk": qty * per_unit,
        "notional": qty * entry * multiplier,
        "note": note,
    }


def forex_lots(
    equity: float,
    risk_pct: float,
    stop_pips: float,
    pip_value: float,
    step: float = 0.01,
    min_lot: float = 0.01,
    max_lot: float = 100.0,
) -> dict[str, float | str]:
    """Lots so that stop_pips * pip_value_per_lot * lots <= risk budget.

    pip_value is the account-currency value of one pip for 1.0 lot
    (about 10 USD for EURUSD on a USD account; it varies for crosses and JPY pairs).
    """
    if stop_pips <= 0 or pip_value <= 0:
        raise ValueError("stop_pips and pip_value must be positive")
    r = risk_size(equity, risk_pct, stop_pips, 0.0, pip_value, step, min_lot, max_lot)
    return {"lots": r["quantity"], "money_at_risk": r["money_at_risk"], "risk_budget": r["risk_budget"], "note": r["note"]}


def kelly(win_rate: float, payoff: float) -> dict[str, float | str]:
    """Kelly fraction for a bet won with probability win_rate that pays `payoff` x the stake lost."""
    if not 0 < win_rate < 1 or payoff <= 0:
        raise ValueError("win_rate must be in (0, 1) and payoff positive")
    f = win_rate - (1 - win_rate) / payoff
    note = "no edge: do not trade" if f <= 0 else "use a fraction (1/4 to 1/2) of full Kelly; estimates are noisy"
    return {"full_kelly": max(0.0, f), "half_kelly": max(0.0, f / 2), "quarter_kelly": max(0.0, f / 4), "note": note}


def binary_kelly(price: float, prob: float, bankroll: float, fee_per_contract: float = 0.0) -> dict[str, float | str]:
    """Kelly stake for buying a binary contract (pays 1.0) at `price` when you believe P(yes) = prob."""
    if not 0 < price < 1 or not 0 <= prob <= 1:
        raise ValueError("price must be in (0, 1) and prob in [0, 1]")
    cost = price + fee_per_contract
    if cost >= 1:
        raise ValueError("price plus fee must be below 1")
    f = (prob - cost) / (1 - cost)
    edge = prob - cost
    if f <= 0:
        return {"fraction": 0.0, "contracts_full": 0.0, "contracts_quarter": 0.0, "edge_per_contract": edge, "note": "no edge at this price"}
    return {
        "fraction": f,
        "contracts_full": math.floor(f * bankroll / cost),
        "contracts_quarter": math.floor(f / 4 * bankroll / cost),
        "edge_per_contract": edge,
        "note": "quarter Kelly is the usual ceiling; your probability is an estimate",
    }


def atr_stop(entry: float, atr: float, mult: float, side: str) -> dict[str, float]:
    if atr <= 0 or mult <= 0:
        raise ValueError("atr and mult must be positive")
    dist = atr * mult
    return {"stop": entry - dist if side == "long" else entry + dist, "distance": dist}


def _self_test() -> None:
    assert floor_to_step(0.07, 0.01) == 0.07 and floor_to_step(1.239, 0.01) == 1.23
    r = risk_size(25_000, 1, 182.50, 178.00)  # 250 / 4.5 = 55.5 -> 55
    assert r["quantity"] == 55 and r["money_at_risk"] <= 250, r
    es = risk_size(50_000, 0.5, 5300, 5285, multiplier=50)  # 250 / 750 -> 0
    assert es["quantity"] == 0 and "minimum" in str(es["note"])
    fx = forex_lots(10_000, 1, 25, 10)  # 100 / 250 = 0.4 lots
    assert fx["lots"] == 0.4 and abs(float(fx["money_at_risk"]) - 100) < 1e-9, fx
    assert forex_lots(1_000, 0.5, 40, 10)["lots"] == 0.01  # 5 / 400 = 0.0125 -> 0.01
    k = kelly(0.55, 1.2)
    assert abs(float(k["full_kelly"]) - (0.55 - 0.45 / 1.2)) < 1e-12
    assert kelly(0.4, 1.0)["full_kelly"] == 0.0
    b = binary_kelly(0.40, 0.50, 2000)  # f = 0.1/0.6
    assert abs(float(b["fraction"]) - 1 / 6) < 1e-12 and b["contracts_full"] == 833
    assert binary_kelly(0.60, 0.55, 2000)["fraction"] == 0.0
    assert atr_stop(100, 2.5, 2, "long")["stop"] == 95 and atr_stop(100, 2.5, 2, "short")["stop"] == 105
    print("position_size self-test passed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Position sizing calculator")
    ap.add_argument("--json", action="store_true", help="Print JSON")
    ap.add_argument("--self-test", action="store_true", help="Run the built-in checks and exit")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("risk", help="Fixed-fractional size from entry and stop")
    p.add_argument("--equity", type=float, required=True)
    p.add_argument("--risk-pct", type=float, required=True, help="Percent of equity to risk, e.g. 1")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--multiplier", type=float, default=1.0, help="Money per 1.0 price move per unit (futures point value)")
    p.add_argument("--step", type=float, default=1.0, help="Quantity step, e.g. 0.001 for BTC")
    p.add_argument("--min-qty", type=float, default=0.0)
    p.add_argument("--max-qty", type=float)
    p.add_argument("--fee-per-unit", type=float, default=0.0, help="Round-trip fees + slippage per unit")

    f = sub.add_parser("forex", help="Lots from stop distance in pips")
    f.add_argument("--equity", type=float, required=True)
    f.add_argument("--risk-pct", type=float, required=True)
    f.add_argument("--stop-pips", type=float, required=True)
    f.add_argument("--pip-value", type=float, required=True, help="Account-currency value of 1 pip for 1.0 lot")
    f.add_argument("--step", type=float, default=0.01)
    f.add_argument("--min-lot", type=float, default=0.01)
    f.add_argument("--max-lot", type=float, default=100.0)

    k = sub.add_parser("kelly", help="Kelly fraction from win rate and payoff ratio")
    k.add_argument("--win-rate", type=float, required=True, help="0-1")
    k.add_argument("--payoff", type=float, required=True, help="Average win / average loss")

    b = sub.add_parser("binary", help="Kelly stake for a binary contract (Kalshi, Polymarket)")
    b.add_argument("--price", type=float, required=True, help="Contract price as a fraction of payout, e.g. 0.40")
    b.add_argument("--prob", type=float, required=True, help="Your probability of YES, 0-1")
    b.add_argument("--bankroll", type=float, required=True)
    b.add_argument("--fee", type=float, default=0.0, help="Fee per contract as a fraction of payout")

    a = sub.add_parser("atr-stop", help="Stop price from ATR")
    a.add_argument("--entry", type=float, required=True)
    a.add_argument("--atr", type=float, required=True)
    a.add_argument("--mult", type=float, default=2.0)
    a.add_argument("--side", choices=["long", "short"], required=True)

    args = ap.parse_args(argv)
    if args.self_test:
        _self_test()
        return 0
    try:
        if args.cmd == "risk":
            out = risk_size(args.equity, args.risk_pct, args.entry, args.stop, args.multiplier, args.step, args.min_qty, args.max_qty, args.fee_per_unit)
        elif args.cmd == "forex":
            out = forex_lots(args.equity, args.risk_pct, args.stop_pips, args.pip_value, args.step, args.min_lot, args.max_lot)
        elif args.cmd == "kelly":
            out = kelly(args.win_rate, args.payoff)
        elif args.cmd == "binary":
            out = binary_kelly(args.price, args.prob, args.bankroll, args.fee)
        elif args.cmd == "atr-stop":
            out = atr_stop(args.entry, args.atr, args.mult, args.side)
        else:
            ap.print_help()
            return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for key, val in out.items():
            print(f"{key:<20}{val:,.4f}" if isinstance(val, float) else f"{key:<20}{val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
