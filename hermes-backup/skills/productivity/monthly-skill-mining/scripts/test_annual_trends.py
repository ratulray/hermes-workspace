#!/usr/bin/env python3
"""Tests for annual_trends.py classification.

Run: python3 scripts/test_annual_trends.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "annual_trends.py"
spec = importlib.util.spec_from_file_location("annual_trends", SCRIPT)
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)


def mk_snapshot(month: str, tech: list[tuple[str, float]], n_jds: int = 20) -> dict:
    rows = [{"canonical": c, "bucket": "technical", "jds": int(n_jds * p / 100), "jd_pct": p,
             "companies": 8, "company_pct": 80.0, "prominent_jds": 8, "prominent_pct": 70.0,
             "mentions": 10, "jd_ids": [], "evidence": []} for c, p in tech]
    return {"month": month, "n_jds": n_jds, "n_companies": 10,
            "by_bucket": {"technical": rows, "leadership_management": []}}


def write_months(tmp: Path, months: list[tuple[str, list[tuple[str, float]]]]) -> None:
    for month, tech in months:
        d = tmp / month / "skills"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{month}-skills-snapshot.json").write_text(json.dumps(mk_snapshot(month, tech)))


def test_classification(tmp: Path) -> None:
    write_months(tmp, [
        ("2026-08", [("steady", 90.0), ("riser", 20.0), ("fader", 80.0), ("blip", 50.0), ("low", 20.0)]),
        ("2026-09", [("steady", 90.0), ("riser", 40.0), ("fader", 60.0), ("low", 20.0)]),
        ("2026-10", [("steady", 90.0), ("riser", 60.0), ("fader", 40.0), ("newcomer", 50.0), ("low", 20.0)]),
        ("2026-11", [("steady", 90.0), ("riser", 80.0), ("fader", 20.0), ("newcomer", 50.0), ("low", 20.0)]),
    ])
    rep = at.build(tmp, "2026")
    s = rep["summary"]
    assert "steady" in s["continuous"], f"steady should be continuous, got {s}"
    assert "riser" in s["rising"], f"riser should be rising, got {s}"
    assert "fader" in s["fading"], f"fader should be fading, got {s}"
    assert "newcomer" in s["new"], f"newcomer should be new, got {s}"
    assert "blip" in s["one-off"], f"blip (1 month only) should be one-off, got {s}"
    assert "low" in s["steady"], f"low should be steady, got {s}"
    assert rep["n_months"] == 4
    assert rep["jd_counts"]["2026-08"] == 20
    print("  ok: classification over 4 synthetic months")


def test_two_month_blip_is_emerging_not_one_off(tmp: Path) -> None:
    """A skill in 2 of 4 months with no net change is neither one-off nor continuous."""
    write_months(tmp, [
        ("2026-08", [("two_month", 50.0)]),
        ("2026-09", [("two_month", 50.0)]),
        ("2026-10", [("other", 50.0)]),
        ("2026-11", [("other", 50.0)]),
    ])
    rep = at.build(tmp, "2026")
    s = rep["summary"]
    assert "two_month" in s["emerging"], f"2-month flat skill should be emerging, got {s}"
    assert "two_month" not in s["one-off"], f"2-month skill must not be one-off, got {s}"
    print("  ok: 2-month flat skill classifies as emerging, not one-off")


def test_single_month(tmp: Path) -> None:
    d = tmp / "2026-10" / "skills"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-10-skills-snapshot.json").write_text(json.dumps(mk_snapshot("2026-10", [("only", 50.0)])))
    rep = at.build(tmp, "2026")
    assert rep["n_months"] == 1
    assert rep["summary"]["emerging"] == ["only"], rep["summary"]
    print("  ok: single month degrades to 'emerging', no false trend")


def test_no_data(tmp: Path) -> None:
    rep = at.build(tmp, "2026")
    assert rep["n_months"] == 0
    assert rep["n_canonicals"] == 0
    print("  ok: empty year -> zero months, no crash")


def test_zero_jd_months_skipped(tmp: Path) -> None:
    d = tmp / "2026-11" / "skills"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-11-skills-snapshot.json").write_text(json.dumps({"month": "2026-11", "n_jds": 0, "by_bucket": {}}))
    rep = at.build(tmp, "2026")
    assert rep["n_months"] == 0, "a month with n_jds=0 must not count as data"
    print("  ok: months with n_jds=0 are skipped")


def main() -> int:
    # Each test gets its own directory - fixtures from one test must not leak
    # into the next.
    for fn in (test_classification, test_two_month_blip_is_emerging_not_one_off,
               test_single_month, test_no_data, test_zero_jd_months_skipped):
        tmp = Path(tempfile.mkdtemp(prefix="annual_trends_test_"))
        try:
            fn(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("all annual_trends tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
