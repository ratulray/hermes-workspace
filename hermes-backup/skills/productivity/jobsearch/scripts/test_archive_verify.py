#!/usr/bin/env python3
"""
test_archive_verify.py — self-test for archive_verify.py.

Run:  python3 test_archive_verify.py

Covers both directions:
  * happy path — a valid payload archives, verifies clean, and round-trips
  * fault path — each corruption the verifier claims to catch is actually caught

A verifier that only ever passes is worthless, so every check below asserts that
a deliberately broken input produces a non-zero exit and the expected error.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "archive_verify.py")

PASSED = 0
FAILED = 0


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def run(args, root):
    proc = subprocess.run(
        [sys.executable, SCRIPT] + args + ["--results-root", root],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def good_payload():
    return {
        "date": "2026-11-06",
        "employers": [
            {
                "employer": "OpenAI",
                "slug": "openai",
                "portal": "https://jobs.ashbyhq.com/openai",
                "portal_note": "Ashby API",
                "total_reviewed": 100,
                "roles": [
                    {
                        "rank": 1,
                        "title": "Engineering Manager, Search",
                        "score": 88,
                        "department": "Applied AI",
                        "location": "San Francisco",
                        "work_model": "On-site (Ashby workplaceType: OnSite)",
                        "comp": "$401K-$445K + equity",
                        "url": "https://jobs.ashbyhq.com/openai/aaa",
                        "hard_filters_pass": True,
                        "hard_filters": '"Lead and develop a team of experienced engineers"',
                        "why": ["Direct RAG/retrieval overlap"],
                        "key_signals": ["Bay Area onsite", "People management confirmed"],
                        "risks": ["On-site, not hybrid"],
                    },
                    {
                        "rank": 2,
                        "title": "Engineering Manager, Platform",
                        "score": 72,
                        "department": "Infrastructure",
                        "location": "Mountain View",
                        "work_model": "Hybrid (Ashby workplaceType: Hybrid)",
                        "comp": "$293K-$385K + equity",
                        "url": "https://jobs.ashbyhq.com/openai/bbb",
                        "hard_filters_pass": True,
                        "hard_filters": '"Managing and growing a high-performing team"',
                        "why": ["Platform enablement"],
                        "key_signals": ["Bay Area hybrid"],
                        "risks": ["Backend heavy"],
                    },
                ],
                "exclusions": {"IC-only, no confirmed management scope": 98},
                "notes": ["Ashby API returned 100 postings."],
            },
            {
                "employer": "Moveworks",
                "slug": "moveworks",
                "portal": "https://www.moveworks.com/us/en/company/careers",
                "total_reviewed": 80,
                "roles": [],
                "exclusions": {"IC-only, no confirmed management scope": 80},
                "notes": ["No engineering-management role passed the hard filters."],
            },
        ],
    }


def archive(payload, root):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(payload, fh)
        path = fh.name
    try:
        return run(["archive", "--input", path], root)
    finally:
        os.unlink(path)


def main():
    root = tempfile.mkdtemp(prefix="archive_verify_test_")
    try:
        print("HAPPY PATH")
        payload = good_payload()
        code, out = archive(payload, root)
        check("valid payload exits 0", code == 0, f"exit={code}")
        check("reports PASS", "VERIFICATION: PASS" in out, out[-400:])
        check("reports both employers", "OpenAI" in out and "Moveworks" in out)

        outdir = os.path.join(root, "2026-11")
        for slug in ("openai", "moveworks"):
            md = os.path.join(outdir, f"2026-11-06-{slug}.md")
            js = os.path.join(outdir, f"2026-11-06-{slug}.json")
            check(f"{slug}: .md written", os.path.isfile(md))
            check(f"{slug}: .json written", os.path.isfile(js))
            if os.path.isfile(js):
                d = json.load(open(js))
                check(f"{slug}: .json has all top keys",
                      set(d) == {"employer", "portal", "date", "total_reviewed",
                                 "total_shortlisted", "roles", "exclusions", "notes"},
                      sorted(d))
                check(f"{slug}: .json shortlist matches roles",
                      d["total_shortlisted"] == len(d["roles"]))
                if d["roles"]:
                    r = d["roles"][0]
                    check(f"{slug}: role has no hard_filters leak", "hard_filters" not in r)
                    check(f"{slug}: role has no employer_name leak", "employer_name" not in r)
                    check(f"{slug}: role has all required keys",
                          set(r) == {"rank", "title", "score", "department", "location",
                                     "work_model", "comp", "url", "hard_filters_pass",
                                     "key_signals", "risks"}, sorted(r))
        check("weekly report written",
              os.path.isfile(os.path.join(outdir, "2026-11-06-weekly-report.md")))
        check("telegram block emitted", "--- BEGIN TELEGRAM MESSAGE ---" in out)
        check("global ranking present", "GLOBAL RANK 1" in out)
        check("0-shortlist employer still listed", "MOVEWORKS" in out)

        md_text = open(os.path.join(outdir, "2026-11-06-openai.md"), encoding="utf-8").read()
        check("md uses en dash in comp", "$401K–$445K" in md_text, md_text[:400])
        check("md backticks workplaceType", "`workplaceType: OnSite`" in md_text)
        check("md has portal note", "Ashby API" in md_text)
        check("md shows hard-filter evidence", "Lead and develop a team" in md_text)

        print("\nVERIFY SUBCOMMAND")
        code, out = run(["verify", "--date", "2026-11-06"], root)
        check("verify exits 0 on good files", code == 0, f"exit={code}")
        check("verify reports PASS", "VERIFICATION: PASS" in out)

        print("\nFAULT PATH — verifier must catch each corruption")
        cases = []

        p = copy.deepcopy(payload)
        p["employers"][0]["roles"][1]["rank"] = 7
        cases.append(("non-contiguous ranks", p, "ranks are not contiguous"))

        p = copy.deepcopy(payload)
        p["employers"][0]["roles"][1]["score"] = 99
        cases.append(("scores out of order", p, "scores not descending"))

        p = copy.deepcopy(payload)
        p["employers"][0]["roles"][0]["url"] = ""
        cases.append(("missing source URL", p, "no source URL"))

        p = copy.deepcopy(payload)
        p["employers"][0]["roles"][0]["key_signals"] = []
        p["employers"][0]["roles"][0].pop("key_signals")
        cases.append(("role missing key_signals", p, "missing key 'key_signals'"))

        p = copy.deepcopy(payload)
        p["employers"][0]["exclusions"] = {"IC-only": 50}
        cases.append(("exclusions do not balance", p, "exclusions sum to"))

        p = copy.deepcopy(payload)
        p["employers"][1]["roles"] = [copy.deepcopy(p["employers"][0]["roles"][0])]
        p["employers"][1]["roles"][0]["url"] = p["employers"][0]["roles"][0]["url"]
        p["employers"][1]["roles"][0]["title"] = "Dupe"
        p["employers"][1]["total_reviewed"] = 79
        p["employers"][1]["exclusions"] = {"x": 78}
        cases.append(("duplicate URL across employers", p, "duplicate source URL"))

        for name, bad, expect in cases:
            code, out = archive(bad, root)
            check(f"{name}: exits non-zero", code != 0, f"exit={code}")
            check(f"{name}: reports the error", expect in out,
                  f"expected {expect!r} in output; got tail: {out[-500:]}")

        print("\nFAULT PATH — corrupted .md on disk must be detected")
        md_path = os.path.join(root, "2026-11", "2026-11-06-openai.md")
        good_md = open(md_path, encoding="utf-8").read()
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(good_md.replace("Engineering Manager, Search", "Engineering Manager, Searhc"))
        code, out = run(["verify", "--date", "2026-11-06", "--employer", "openai"], root)
        check("tampered .md: exits non-zero", code != 0, f"exit={code}")
        check("tampered .md: reports mismatch", "missing role title" in out, out[-400:])
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(good_md)

        print("\nREPORT SUBCOMMAND")
        code, out = run(["report", "--date", "2026-11-06"], root)
        check("report exits 0", code == 0, f"exit={code}")
        check("report has top picks", "GLOBAL RANK 1" in out)
        check("report lists exclusions", "Excluded — OpenAI" in out)
        check("report includes notes", "Ashby API returned 100 postings" in out)

        print(f"\n{'=' * 60}")
        print(f"{PASSED} passed, {FAILED} failed")
        print("=" * 60)
        return 1 if FAILED else 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
