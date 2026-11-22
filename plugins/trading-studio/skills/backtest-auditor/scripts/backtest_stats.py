#!/usr/bin/env python3
"""Honest performance statistics for a backtest or a live trade log.

Part of claude-trading-skills by Viprasol Tech Private Limited.

Reads one numeric column from a CSV, either per-period fractional returns
(``--kind returns``, e.g. 0.012 for +1.2%) or per-trade profit and loss in
money (``--kind pnl``). Prints the usual metrics plus the ones that tell you
whether the result is likely to be luck:

* PSR: probability the true Sharpe is above zero (Bailey & Lopez de Prado, 2012).
* DSR: PSR against the best Sharpe you would expect from ``--n-trials``
  skill-less variations (Bailey & Lopez de Prado, 2014).
* MinTRL: how many periods you need before the Sharpe is credible at 95%.

Standard library only. Run ``python backtest_stats.py --self-test`` to check it.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from statistics import NormalDist

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()


@dataclass
class Stats:
    kind: str
    n: int
    mean: float
    stdev: float
    sharpe: float
    sharpe_annualized: float | None
    sortino: float | None
    max_drawdown: float
    max_drawdown_note: str
    win_rate: float
    profit_factor: float | None
    avg_win: float
    avg_loss: float
    expectancy: float
    longest_losing_streak: int
    skew: float
    kurtosis: float
    psr: float
    n_trials: int
    dsr: float
    min_track_record: float | None


def _moments(xs: list[float]) -> tuple[float, float, float, float]:
    n = len(xs)
    mean = math.fsum(xs) / n
    dev = [x - mean for x in xs]
    m2 = math.fsum(d * d for d in dev) / n
    if m2 == 0.0:
        return mean, 0.0, 0.0, 3.0
    m3 = math.fsum(d**3 for d in dev) / n
    m4 = math.fsum(d**4 for d in dev) / n
    stdev = math.sqrt(m2 * n / (n - 1))
    return mean, stdev, m3 / m2**1.5, m4 / m2**2


def _sr_std_error(sr: float, skew: float, kurt: float) -> float:
    return math.sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr))


def psr(sr: float, n: int, skew: float, kurt: float, benchmark: float = 0.0) -> float:
    """P(true per-period Sharpe > benchmark)."""
    z = (sr - benchmark) * math.sqrt(n - 1) / _sr_std_error(sr, skew, kurt)
    return _N.cdf(z)


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """Expected best Sharpe among n_trials noise strategies (Gumbel approximation)."""
    if n_trials <= 1:
        return 0.0
    a = _N.inv_cdf(1.0 - 1.0 / n_trials)
    b = _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(sr_variance) * ((1.0 - EULER_GAMMA) * a + EULER_GAMMA * b)


def min_track_record(sr: float, skew: float, kurt: float, prob: float = 0.95) -> float | None:
    """Periods needed for P(true SR > 0) >= prob. None if the Sharpe is not positive."""
    if sr <= 0:
        return None
    return 1.0 + (1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr) * (_N.inv_cdf(prob) / sr) ** 2


def _max_drawdown(xs: list[float], kind: str, start_equity: float | None) -> tuple[float, str]:
    if kind == "returns":
        equity, peak, mdd = 1.0, 1.0, 0.0
        for r in xs:
            equity *= 1.0 + r
            peak = max(peak, equity)
            mdd = max(mdd, 1.0 - equity / peak)
        return mdd, "fraction of peak equity (compounded returns)"
    base = start_equity or 0.0
    equity, peak, mdd = base, base, 0.0
    for p in xs:
        equity += p
        peak = max(peak, equity)
        mdd = max(mdd, peak - equity)
    if start_equity:
        return mdd / start_equity, "fraction of starting equity"
    return mdd, "money, peak-to-trough of cumulative PnL"


def compute(
    xs: list[float],
    kind: str = "returns",
    periods_per_year: float | None = None,
    n_trials: int = 1,
    sr_variance: float | None = None,
    start_equity: float | None = None,
) -> Stats:
    if len(xs) < 3:
        raise ValueError("need at least 3 observations")
    n = len(xs)
    mean, stdev, skew, kurt = _moments(xs)
    sr = mean / stdev if stdev > 0 else 0.0
    downside = math.sqrt(math.fsum(min(0.0, x) ** 2 for x in xs) / n)
    sortino = mean / downside if downside > 0 else None  # None: no losing periods
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x < 0]
    gross_loss = -math.fsum(losses)
    streak = longest = 0
    for x in xs:
        streak = streak + 1 if x < 0 else 0
        longest = max(longest, streak)
    mdd, note = _max_drawdown(xs, kind, start_equity)
    var = sr_variance if sr_variance is not None else 1.0 / n
    sr0 = expected_max_sharpe(n_trials, var)
    return Stats(
        kind=kind,
        n=n,
        mean=mean,
        stdev=stdev,
        sharpe=sr,
        sharpe_annualized=sr * math.sqrt(periods_per_year) if periods_per_year else None,
        sortino=sortino,
        max_drawdown=mdd,
        max_drawdown_note=note,
        win_rate=len(wins) / n,
        profit_factor=math.fsum(wins) / gross_loss if gross_loss > 0 else None,
        avg_win=math.fsum(wins) / len(wins) if wins else 0.0,
        avg_loss=math.fsum(losses) / len(losses) if losses else 0.0,
        expectancy=mean,
        longest_losing_streak=longest,
        skew=skew,
        kurtosis=kurt,
        psr=psr(sr, n, skew, kurt),
        n_trials=n_trials,
        dsr=psr(sr, n, skew, kurt, benchmark=sr0),
        min_track_record=min_track_record(sr, skew, kurt),
    )


def verdict(s: Stats) -> str:
    if s.n < 30:
        return "TOO FEW OBSERVATIONS: under 30 periods/trades, no statistic here is reliable."
    if s.dsr >= 0.95:
        return "LIKELY GENUINE: DSR >= 95% after correcting for the number of trials."
    if s.psr >= 0.95:
        return "POSSIBLY LUCK: significant alone, but not after correcting for the trials you ran."
    return "NOT SIGNIFICANT: the edge is indistinguishable from noise at 95%."


def _is_number(cell: str) -> bool:
    try:
        float(cell.strip().replace(",", "").rstrip("%"))
    except ValueError:
        return False
    return True


def read_column(path: str, column: str | None) -> list[float]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError(f"{path} is empty")
    has_header = not all(_is_number(c) for c in rows[0] if c.strip())
    header, body = (rows[0], rows[1:]) if has_header else ([], rows)
    if column is not None:
        if column not in header:
            raise ValueError(f"column '{column}' not found; columns are: {', '.join(header)}")
        idx = header.index(column)
    else:
        numeric = [i for i, c in enumerate(body[0] if body else []) if _is_number(c)]
        if not numeric:
            raise ValueError("no numeric column found; pass --column")
        if len(numeric) > 1:
            names = ", ".join(header[i] if header else f"#{i + 1}" for i in numeric)
            raise ValueError(f"several numeric columns ({names}); choose one with --column")
        idx = numeric[0]
    out = []
    for row in body:
        cell = row[idx].strip().replace(",", "") if idx < len(row) else ""
        if cell.endswith("%"):
            out.append(float(cell[:-1]) / 100.0)
        elif cell:
            out.append(float(cell))
    return out


def _fmt(s: Stats) -> str:
    pct = (lambda v: f"{v * 100:.2f}%") if s.kind == "returns" else (lambda v: f"{v:,.2f}")
    mdd = f"{s.max_drawdown * 100:.2f}%" if "fraction" in s.max_drawdown_note else f"{s.max_drawdown:,.2f}"
    pf = f"{s.profit_factor:.2f}" if s.profit_factor is not None else "n/a (no losses)"
    ann = f"{s.sharpe_annualized:.2f}" if s.sharpe_annualized is not None else "n/a (pass --periods-per-year)"
    mtrl = f"{s.min_track_record:,.0f}" if s.min_track_record else "n/a (Sharpe <= 0)"
    lines = [
        f"Observations        {s.n} ({s.kind})",
        f"Mean / stdev        {pct(s.mean)} / {pct(s.stdev)}",
        f"Sharpe (per period) {s.sharpe:.4f}   annualized {ann}",
        f"Sortino             {s.sortino:.4f}" if s.sortino is not None else "Sortino             n/a (no losing periods)",
        f"Max drawdown        {mdd}   [{s.max_drawdown_note}]",
        f"Win rate            {s.win_rate * 100:.1f}%   profit factor {pf}",
        f"Avg win / loss      {pct(s.avg_win)} / {pct(s.avg_loss)}   expectancy {pct(s.expectancy)}",
        f"Longest loss streak {s.longest_losing_streak}",
        f"Skew / kurtosis     {s.skew:.3f} / {s.kurtosis:.3f}",
        f"PSR (SR > 0)        {s.psr * 100:.1f}%",
        f"{f'DSR ({s.n_trials} trials)':<20}{s.dsr * 100:.1f}%",
        f"MinTRL (95%)        {mtrl} periods",
        "",
        verdict(s),
    ]
    return "\n".join(lines)


def _self_test() -> None:
    import random

    rng = random.Random(7)
    noise = [rng.gauss(0.0, 0.01) for _ in range(756)]
    s = compute(noise, periods_per_year=252, n_trials=50)
    assert s.n == 756 and 0.0 <= s.psr <= 1.0 and s.dsr <= s.psr, s
    assert s.dsr < 0.95, "noise must not pass the deflated test"
    edge = [rng.gauss(0.002, 0.01) for _ in range(756)]
    e = compute(edge, periods_per_year=252, n_trials=10)
    assert e.psr > 0.999 and e.dsr > 0.95, e
    assert verdict(e).startswith("LIKELY GENUINE")
    # drawdown: +10% then -50% then +10% -> peak 1.1, trough 0.55 -> 50%
    d = compute([0.1, -0.5, 0.1], kind="returns")
    assert abs(d.max_drawdown - 0.5) < 1e-12, d.max_drawdown
    p = compute([100.0, -300.0, 50.0, 200.0], kind="pnl", start_equity=1000.0)
    assert abs(p.max_drawdown - 0.3) < 1e-12 and p.longest_losing_streak == 1
    assert abs(p.profit_factor - 350.0 / 300.0) < 1e-12 and p.win_rate == 0.75
    assert expected_max_sharpe(1, 0.01) == 0.0
    assert min_track_record(-0.1, 0.0, 3.0) is None
    assert verdict(compute([0.01, -0.01, 0.02])).startswith("TOO FEW")
    print("backtest_stats self-test passed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Honest backtest / trade-log statistics (PSR, DSR, MinTRL).")
    ap.add_argument("csv", nargs="?", help="CSV file with one numeric column per row")
    ap.add_argument("--column", help="Column name (default: first numeric column)")
    ap.add_argument("--kind", choices=["returns", "pnl"], default="returns")
    ap.add_argument("--periods-per-year", type=float, help="252 daily, 52 weekly, 12 monthly")
    ap.add_argument("--n-trials", type=int, default=1, help="How many variations you tried in total")
    ap.add_argument("--sr-variance", type=float, help="Variance of Sharpe across trials (default 1/n)")
    ap.add_argument("--start-equity", type=float, help="For --kind pnl: express drawdown as a fraction")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    ap.add_argument("--self-test", action="store_true", help="Run the built-in checks and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        _self_test()
        return 0
    if not args.csv:
        ap.error("csv is required (or use --self-test)")
    if args.n_trials < 1:
        ap.error("--n-trials must be at least 1")
    try:
        xs = read_column(args.csv, args.column)
        s = compute(xs, args.kind, args.periods_per_year, args.n_trials, args.sr_variance, args.start_equity)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({**asdict(s), "verdict": verdict(s)}, indent=2, default=str))
    else:
        print(_fmt(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
