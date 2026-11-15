#!/usr/bin/env python3
"""Annual skill-trend report across monthly skill snapshots.

Reads every ``results/<YYYY-MM>/skills/<YYYY-MM>-skills-snapshot.json`` and
classifies each canonical skill as continuous / rising / fading / new / one-off.

Usage:
    python annual_trends.py --year 2026          # one calendar year
    python annual_trends.py --year 2026 --all    # every year present
    python annual_trends.py --year 2026 --out /path/to/report.json

Deterministic: same inputs -> same output. No LLM in the loop.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFAULT_RESULTS = Path("/Users/ratul/Documents/jobsearch/results")

# A canonical is "continuous" when it appears in every month that has data and
# never drops below this share of JDs in any month.
CONTINUOUS_FLOOR_PCT = 25.0
# Minimum months present for a skill to count as established rather than a blip.
CONTINUOUS_MIN_MONTHS = 3
# Absolute change in jd_pct between first and last month for rising/fading.
CHANGE_THRESHOLD_PCT = 5.0

BUCKETS = ("technical", "leadership_management")


def load_snapshots(results_dir: Path, year: str | None) -> dict[str, dict]:
    """month -> snapshot json. Sorted by month."""
    out: dict[str, dict] = {}
    for p in sorted(results_dir.glob("*/skills/*-skills-snapshot.json")):
        month = p.parent.parent.name
        if year and not month.startswith(year):
            continue
        try:
            snap = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not snap.get("n_jds"):
            continue
        out[month] = snap
    return out


def series(snapshots: dict[str, dict]) -> dict[str, dict]:
    """canonical -> {bucket, pct_by_month, jds_by_month}"""
    acc: dict[str, dict] = {}
    for month, snap in snapshots.items():
        for bucket in BUCKETS:
            for row in snap.get("by_bucket", {}).get(bucket, []):
                c = row["canonical"]
                e = acc.setdefault(c, {"bucket": bucket, "pct": {}, "jds": {}, "mentions": {}})
                e["pct"][month] = row.get("jd_pct", 0.0)
                e["jds"][month] = row.get("jds", 0)
                e["mentions"][month] = row.get("mentions", 0)
    return acc


def classify(e: dict, months: list[str]) -> tuple[str, float]:
    """Return (label, delta_pct_first_to_last)."""
    pct = e["pct"]
    present = [m for m in months if m in pct]
    if not present:
        return "unknown", 0.0

    first_m, last_m = present[0], present[-1]
    delta = pct[last_m] - pct[first_m]
    # A skill that skips early months and shows up late is "new"; one that
    # appears in a single month and never returns is a "one-off" blip.
    skipped_early = [m for m in months[:months.index(first_m)] if m not in pct]

    if len(present) == 1 and len(months) > 1:
        return ("new" if first_m == months[-1] else "one-off"), delta
    if skipped_early and len(months) > 1:
        return "new", delta

    if len(present) == len(months) and len(months) >= CONTINUOUS_MIN_MONTHS:
        floor = min(pct[m] for m in present)
        if floor >= CONTINUOUS_FLOOR_PCT:
            return "continuous", delta

    if delta >= CHANGE_THRESHOLD_PCT:
        return "rising", delta
    if delta <= -CHANGE_THRESHOLD_PCT:
        return "fading", delta
    if len(present) >= CONTINUOUS_MIN_MONTHS:
        return "steady", delta
    return "emerging", delta


def build(results_dir: Path, year: str | None) -> dict:
    snapshots = load_snapshots(results_dir, year)
    months = sorted(snapshots.keys())
    acc = series(snapshots)
    rows = []
    for canon, e in acc.items():
        label, delta = classify(e, months)
        rows.append({
            "canonical": canon,
            "bucket": e["bucket"],
            "classification": label,
            "delta_pct": round(delta, 1),
            "months_present": len(e["pct"]),
            "months_total": len(months),
            "pct_by_month": e["pct"],
            "jds_by_month": e["jds"],
            "first_month": min(e["pct"]) if e["pct"] else None,
            "last_month": max(e["pct"]) if e["pct"] else None,
        })
    order = {"continuous": 0, "rising": 1, "steady": 2, "emerging": 3, "new": 4, "one-off": 5, "fading": 6}
    rows.sort(key=lambda r: (order.get(r["classification"], 9), -r["delta_pct"], r["canonical"]))
    return {
        "year": year or "all",
        "months_analyzed": months,
        "n_months": len(months),
        "n_canonicals": len(rows),
        "jd_counts": {m: snapshots[m].get("n_jds") for m in months},
        "by_bucket": {
            b: [r for r in rows if r["bucket"] == b] for b in BUCKETS
        },
        "summary": {
            label: sorted(r["canonical"] for r in rows if r["classification"] == label)
            for label in ("continuous", "rising", "steady", "emerging", "new", "one-off", "fading")
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="annual_trends")
    ap.add_argument("--year", required=True, help="calendar year, e.g. 2026")
    ap.add_argument("--all", action="store_true", help="ignore --year, use every month present")
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--out", type=Path, help="write the JSON report here")
    a = ap.parse_args(argv)

    report = build(a.results_dir, None if a.all else a.year)

    if not report["n_months"]:
        print(f"no monthly snapshots found for {report['year']} under {a.results_dir}")
        return 0

    print(f"{report['year']}: {report['n_months']} month(s) - {report['months_analyzed']}")
    print(f"  JDs per month: {report['jd_counts']}")
    print(f"  {report['n_canonicals']} canonical skills")
    for label, names in report["summary"].items():
        if names:
            print(f"  {label:11s} ({len(names):2d}): {', '.join(names)}")
    if report["n_months"] < 2:
        print("  NOTE: only one month of data - no trend is meaningful yet")

    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(f"  wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
