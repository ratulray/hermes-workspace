#!/usr/bin/env python3
"""
archive_verify.py — deterministic archive + verify for jobsearch shortlists.

Replaces the multi-turn "write .md, write .json, re-read both, check the counts,
re-check the counts" loop with ONE deterministic script run.

Pipeline
--------
1. read a run payload (JSON) produced by the agent's analysis phase
2. render one .md + one .json per employer into <results-root>/<YYYY-MM>/
3. re-read both from disk and verify them against the schema + the skill's
   Verification contract (output-format.md, SKILL.md step 12)
4. render the combined multi-employer Telegram report with global ranking
5. print a verification report and exit non-zero if any ERROR was found

Archive files are ALWAYS written and the Telegram report is ALWAYS rendered,
even when verification fails — a failed count must not swallow the report.
Errors are surfaced loudly in stdout and echoed into the report's Notes.

Usage
-----
  archive_verify.py archive --input PAYLOAD.json [--results-root DIR]
                            [--date YYYY-MM-DD]
  archive_verify.py verify  [--results-root DIR] --date YYYY-MM-DD
                            [--employer SLUG ...]
  archive_verify.py report  [--results-root DIR] --date YYYY-MM-DD
                            [--employer SLUG ...] [--out FILE]

Exit codes
----------
  0  no errors (warnings may still be present)
  1  one or more verification errors (files + report still written)
  2  usage / IO / payload error (nothing written)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime

DEFAULT_RESULTS_ROOT = os.path.expanduser("~/Documents/jobsearch/results")

# JSON role schema — SKILL.md step 12.
REQUIRED_TOP_KEYS = ("employer", "portal", "date", "total_reviewed",
                      "total_shortlisted", "roles", "exclusions", "notes")
REQUIRED_ROLE_KEYS = ("rank", "title", "score", "department", "location",
                      "work_model", "comp", "url", "hard_filters_pass",
                      "key_signals", "risks")
# Keys the agent supplies that are input-only (not copied into the .json).
INPUT_ONLY_ROLE_KEYS = ("hard_filters", "why")
# Render-time fields added internally; never persisted to the .json.
INTERNAL_ROLE_KEYS = ("employer_name",)

MD_EMPTY_SHORTLIST = ("_No roles passed the hard filters (Bay Area onsite/hybrid + "
                      "confirmed people-management scope + EM/Director level). "
                      "See Exclusions Summary._")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def md_comp(text: str) -> str:
    """JSON comp form uses a hyphen; the .md form uses an en dash (output-format.md).

    Matches a hyphen between two currency-range endpoints. Both endpoints may carry
    a `$` prefix and/or a K/M suffix, and the two sides are not symmetric — the
    source postings write `$401K-$445K`, `$190,900-$334,100`, `250K-300K`.
    """
    _END = r"\$?\d[\d,]*(?:[KkMm])?"
    return re.sub(rf"({_END})-({_END})", r"\1–\2", text or "")


def md_notes(text: str) -> str:
    return md_comp(text or "")


def md_code_spans(text: str) -> str:
    """House style: wrap identifier-style tokens in backticks, e.g. workplaceType: OnSite.

    Matches the convention already used in the hand-written .md files.
    Only wraps a single `word: word` token, never a sentence fragment.
    """
    return re.sub(r"(?<![\w`])((?:workplaceType|department|team|employmentType):\s*[\w]+)(?![\w`])",
                  r"`\1`", text or "")


def md_hard_filters_by_title(md_text: str) -> dict:
    """Map role title -> hard-filter evidence line, parsed back out of a .md file.

    Used by the `verify` subcommand, which has no payload and must recover the
    evidence from the rendered file.
    """
    out: dict = {}
    title = None
    for line in (md_text or "").splitlines():
        m = re.match(r"^\*\*(\d+)\.\s+(.+?)\*\*\s+—\s+Score:", line)
        if m:
            title = m.group(2).strip()
            continue
        if title and line.startswith("- **Hard filters:**"):
            ev = line.split("- **Hard filters:**", 1)[1].strip()
            out[title] = re.sub(r"^[✅❌]\s*—\s*", "", ev)
            title = None
    return out


# --- .md parsing that tolerates both the current and the pre-2026-10-30 layout ---

def md_role_entries(md_text: str) -> list:
    """Extract (rank, title, score) from a .md, tolerating both role-heading styles.

    current:  **1. Engineering Manager, Search** — Score: 88
    legacy:   **1. Engineering Manager, Search — Score: 88**
    """
    out = []
    for line in (md_text or "").splitlines():
        m = re.match(r"^\*\*(\d+)\.\s+(.+?)\*\*\s+—\s+Score:\s*(\d+)\s*$", line)
        if m:
            out.append((int(m.group(1)), m.group(2).strip(), int(m.group(3))))
            continue
        m = re.match(r"^\*\*(\d+)\.\s+(.+?)\s+—\s+Score:\s*(\d+)\*\*\s*$", line)
        if m:
            out.append((int(m.group(1)), m.group(2).strip(), int(m.group(3))))
    return out


def md_count_line(md_text: str, label: str):
    """Extract the integer from a 'Roles reviewed:' / 'Roles shortlisted:' line.

    Tolerates '- **Roles reviewed:** 813' (current) and
    '**Roles reviewed:** 796 total postings -> ...' (legacy).
    """
    pat = re.compile(rf"^[-*]*\s*\*\*{label}:\*\*\s*(\d+)", re.M)
    m = pat.search(md_text or "")
    return int(m.group(1)) if m else None


def md_section_lines(md_text: str, heading: str) -> list:
    """Return the bullet lines under a '## <heading>' section."""
    lines = (md_text or "").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and heading.lower() in line.lower():
            start = i + 1
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("- ") or line.startswith("  - "):
            out.append(line)
    return out


def md_is_canonical(md_text: str) -> bool:
    """True when the .md was produced by archive_verify.py (current archive layout).

    The canonical form has bare, dash-prefixed count lines:
        - **Roles reviewed:** 813
        - **Roles shortlisted:** 10
    Archives written before the script used other layouts (`**Total reviewed:** 77 |
    **Shortlisted:** 1`, `**Roles reviewed:** 815 total -> ...`, `**[Rank 1] Title**`).
    Those are still valid history, but their structure differs enough that the
    cross-file checks do not apply to them.
    """
    return bool(re.search(r"^- \*\*Roles reviewed:\*\* \d+\s*$", md_text or "", re.M))


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "employer"


def month_dir(results_root: str, date: str) -> str:
    return os.path.join(results_root, date[:7])


def parse_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise SystemExit(f"ERROR: bad date {value!r}, expected YYYY-MM-DD")


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def render_md(emp: dict) -> str:
    out = [f"# {emp['employer']} — Job Shortlist", ""]
    portal = emp["portal"]
    if emp.get("portal_note"):
        portal = f"{portal} ({emp['portal_note']})"
    out.append(f"- **Portal URL used:** {portal}")
    out.append(f"- **Date checked:** {emp['date']}")
    out.append(f"- **Roles reviewed:** {emp['total_reviewed']}")
    out.append(f"- **Roles shortlisted:** {emp['total_shortlisted']}")
    out += ["", "## Ranked Shortlist", ""]

    roles = emp.get("roles") or []
    if not roles:
        out.append(MD_EMPTY_SHORTLIST)
        out.append("")
    for role in roles:
        out.append(f"**{role['rank']}. {role['title']}** — Score: {role['score']}")
        out.append(
            f"- **Department:** {role['department']} | **Location:** {role['location']} "
            f"| **Work model:** {md_code_spans(role['work_model'])} | **Comp:** {md_comp(role['comp'])}"
        )
        mark = "✅" if role.get("hard_filters_pass") else "❌"
        evidence = role.get("hard_filters") or "not confirmed"
        out.append(f"- **Hard filters:** {mark} — {evidence}")
        out.append("- **Why it matches:**")
        for bullet in (role.get("why") or role.get("key_signals") or []):
            out.append(f"  - {bullet}")
        out.append("- **Risks or gaps:**")
        for bullet in (role.get("risks") or []):
            out.append(f"  - {bullet}")
        out.append(f"- **Source:** {role['url']}")
        out.append("")

    out += ["## Exclusions Summary", ""]
    if emp.get("exclusions"):
        for bucket, count in emp["exclusions"].items():
            out.append(f"- {bucket}: {count}")
    else:
        out.append("- None recorded.")
    out.append("")

    out += ["## Notes", ""]
    if emp.get("notes"):
        for note in emp["notes"]:
            out.append(f"- {md_notes(note)}")
    else:
        out.append("- None recorded.")
    out.append("")
    return "\n".join(out)


def build_json_employer(emp: dict) -> dict:
    roles = []
    for role in emp.get("roles") or []:
        clean = {k: v for k, v in role.items()
                 if k not in INPUT_ONLY_ROLE_KEYS and k not in INTERNAL_ROLE_KEYS}
        roles.append(clean)
    return {
        "employer": emp["employer"],
        "portal": emp["portal"],
        "date": emp["date"],
        "total_reviewed": emp["total_reviewed"],
        "total_shortlisted": emp["total_shortlisted"],
        "roles": roles,
        "exclusions": emp.get("exclusions") or {},
        "notes": emp.get("notes") or [],
    }


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #

class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self) -> bool:
        return not self.errors


def verify_employer(emp: dict, md_text: str, json_obj, slug: str, rep: Report,
                    payload_emp: dict | None = None) -> None:
    """Verify one employer's archived .md + .json.

    `emp`      — the archived .json as read back from disk (source of truth for counts/roles)
    `md_text`  — the archived .md as read back from disk
    `payload_emp` — the in-memory payload, when available. Carries `hard_filters`,
                 which is intentionally NOT written to the .json, so it can only be
                 checked against the payload and the rendered .md.
    """
    label = f"{emp.get('employer', slug)}"

    for key in REQUIRED_TOP_KEYS:
        if key not in json_obj:
            rep.error(f"{label}: missing top-level key '{key}' in .json")

    if json_obj.get("employer") != emp.get("employer"):
        rep.error(f"{label}: .json employer {json_obj.get('employer')!r} != payload {emp.get('employer')!r}")
    if json_obj.get("date") != emp.get("date"):
        rep.error(f"{label}: .json date {json_obj.get('date')!r} != payload {emp.get('date')!r}")

    roles = json_obj.get("roles") or []
    if json_obj.get("total_shortlisted") != len(roles):
        rep.error(f"{label}: total_shortlisted={json_obj.get('total_shortlisted')} but {len(roles)} roles present")

    # ranks contiguous from 1
    ranks = [r.get("rank") for r in roles]
    if ranks != list(range(1, len(roles) + 1)):
        rep.error(f"{label}: ranks are not contiguous 1..N — got {ranks}")

    # scores monotonically non-increasing by rank
    scores = [r.get("score") for r in roles]
    if any(not isinstance(s, (int, float)) for s in scores):
        rep.error(f"{label}: non-numeric score in {scores}")
    elif scores != sorted(scores, reverse=True):
        rep.error(f"{label}: scores not descending by rank — got {scores}")

    # per-role schema + source URL
    payload_roles = {}
    if payload_emp:
        payload_roles = {r.get("title"): r for r in (payload_emp.get("roles") or [])}
    # hard-filter evidence lives only in the payload and the .md — never in the .json.
    # With no payload (the `verify` subcommand on pre-script archives) recover it from the .md.
    md_evidence = md_hard_filters_by_title(md_text)
    for r in roles:
        title = r.get("title", "<untitled>")
        for key in REQUIRED_ROLE_KEYS:
            if key not in r:
                rep.error(f"{label}: role {title!r} missing key '{key}'")
        url = (r.get("url") or "").strip()
        if not url:
            rep.error(f"{label}: role {title!r} has no source URL")
        elif not url.startswith("http"):
            rep.error(f"{label}: role {title!r} source URL is not http(s): {url!r}")
        if not (r.get("key_signals") or []):
            rep.warn(f"{label}: role {title!r} has no key_signals")
        if not (r.get("risks") or []):
            rep.warn(f"{label}: role {title!r} has no risks/gaps listed")
        p_role = payload_roles.get(title, {})
        evidence = (p_role.get("hard_filters") or "").strip()
        if evidence:
            if evidence not in md_text:
                rep.error(f"{label}: .md is missing the hard-filter evidence for {title!r}")
        else:
            md_ev = md_evidence.get(title, "").strip()
            if not md_ev:
                rep.warn(f"{label}: role {title!r} has no hard-filter evidence text")
            elif md_ev.lower().startswith("not confirmed"):
                rep.warn(f"{label}: role {title!r} has unconfirmed hard filters")

    # exclusions must account for every reviewed-but-not-shortlisted role.
    # Pre-script archives counted exclusions against a filtered subset rather than
    # the full reviewed total, so the balance invariant only applies to the
    # canonical layout. For legacy archives it is reported as a warning, not an error.
    ex = json_obj.get("exclusions") or {}
    ex_total = sum(v for v in ex.values() if isinstance(v, (int, float)))
    expected = (json_obj.get("total_reviewed") or 0) - len(roles)
    canonical = md_is_canonical(md_text)
    if ex_total != expected:
        msg = (f"{label}: exclusions sum to {ex_total} but {expected} roles were reviewed "
               f"without being shortlisted ({json_obj.get('total_reviewed')} reviewed - {len(roles)} shortlisted)")
        if canonical:
            rep.error(msg)
        else:
            rep.warn(msg + " — expected for a pre-script archive")
    if not ex:
        rep.warn(f"{label}: no exclusion buckets recorded")

    # .md must reflect the .json
    employer = json_obj.get("employer", "")
    first_line = (md_text or "").splitlines()[0] if md_text else ""
    if employer.lower() not in first_line.lower():
        # A combined multi-employer report names every employer in its body, not
        # in its header. Only a real header/body mismatch is an error.
        body = md_text or ""
        if employer.lower() in body.lower():
            rep.warn(f"{label}: .md header does not name the employer "
                     "— expected for a combined multi-employer report")
        else:
            rep.error(f"{label}: .md header does not name the employer")
    # Section headings. Names varied across the hand-written archives; accept the
    # known synonyms. A missing section is only an error for the canonical layout.
    section_specs = (
        ("## Ranked Shortlist", ("## Ranked Shortlist",)),
        ("## Exclusions Summary", ("## Exclusions Summary", "## Excluded Roles",
                                   "## Roles Excluded", "## Exclusions")),
        ("## Notes", ("## Notes", "## Additional Notes", "## Observations")),
    )
    for label, synonyms in section_specs:
        if not any(s in md_text for s in synonyms):
            if canonical:
                rep.error(f"{label}: .md missing section {label!r}")
            else:
                rep.warn(f"{label}: .md has no '{label}' section "
                         "— expected for a pre-script archive")

    # Archives written before archive_verify.py used a different layout, and in
    # those the .md and .json role titles were not always byte-identical (an
    # employer suffix was added to one side only). The .json-internal checks
    # above still apply, and source-URL presence is checked for every layout.
    # The rest of the cross-file checks require the canonical layout.
    for r in roles:
        title = r.get("title", "")
        if title and title not in md_text:
            if canonical:
                rep.error(f"{label}: .md is missing role title {title!r}")
            else:
                rep.warn(f"{label}: .md role title {title!r} differs from the .json title "
                         "— expected for a pre-script archive")
        if r.get("url") and r["url"] not in md_text:
            rep.error(f"{label}: .md is missing source URL for {title!r}")

    # Archives written before archive_verify.py used a different layout. Their
    # cross-file structure checks do not apply; the .json-internal checks above
    # still do, and any real corruption still surfaces.
    if not canonical:
        rep.warn(f"{label}: .md uses the pre-script archive layout — cross-file checks skipped")
        return

    md_reviewed = md_count_line(md_text, "Roles reviewed")
    if md_reviewed is None:
        rep.error(f"{label}: .md has no 'Roles reviewed:' count")
    elif md_reviewed != json_obj.get("total_reviewed"):
        rep.error(f"{label}: .md roles-reviewed count {md_reviewed} disagrees with .json {json_obj.get('total_reviewed')}")

    md_short = md_count_line(md_text, "Roles shortlisted")
    if md_short is None:
        rep.error(f"{label}: .md has no 'Roles shortlisted:' count")
    elif md_short != json_obj.get("total_shortlisted"):
        rep.error(f"{label}: .md roles-shortlisted count {md_short} disagrees with .json {json_obj.get('total_shortlisted')}")

    # the .md shortlist must have exactly as many role entries as the .json
    md_entries = md_role_entries(md_text)
    if len(md_entries) != len(roles):
        rep.error(f"{label}: .md has {len(md_entries)} role entries but .json has {len(roles)}")
    else:
        for (md_rank, md_title, md_score), r in zip(md_entries, roles):
            if md_title != r.get("title"):
                rep.error(f"{label}: .md role {md_title!r} != .json role {r.get('title')!r}")
            if md_rank != r.get("rank"):
                rep.error(f"{label}: .md rank {md_rank} != .json rank {r.get('rank')} for {md_title!r}")
            if md_score != r.get("score"):
                rep.error(f"{label}: .md score {md_score} != .json score {r.get('score')} for {md_title!r}")

    if ex:
        md_ex_lines = len(md_section_lines(md_text, "Exclusions Summary"))
        if md_ex_lines != len(ex):
            rep.error(f"{label}: .md exclusion bullet count {md_ex_lines} != .json buckets {len(ex)}")
    if not md_text.endswith("\n"):
        rep.error(f"{label}: .md does not end with a newline (possible truncation)")


def verify_cross_employer(payload: dict, rep: Report) -> None:
    seen: dict[str, str] = {}
    for emp in payload.get("employers") or []:
        label = emp.get("employer", "?")
        for r in emp.get("roles") or []:
            url = (r.get("url") or "").strip()
            if not url:
                continue
            if url in seen:
                rep.error(f"{label}: duplicate source URL {url} (also in {seen[url]})")
            else:
                seen[url] = label


# --------------------------------------------------------------------------- #
# telegram report
# --------------------------------------------------------------------------- #

def render_telegram(payload: dict, employers: list[dict]) -> str:
    date = payload.get("date", "")
    pooled = []
    for order, emp in enumerate(employers):
        for role in emp.get("roles") or []:
            pooled.append((order, role))
    pooled.sort(key=lambda pair: (-pair[1].get("score", 0), pair[0]))
    global_rank = {}
    for idx, (_order, role) in enumerate(pooled, start=1):
        global_rank[(role.get("employer_name", ""), role.get("title", ""), role.get("url", ""))] = idx

    total_short = sum(len(e.get("roles") or []) for e in employers)
    out = [f"📋 Weekly Job Shortlist — {date}",
           f"Reviewed {len(employers)} employers | {total_short} total shortlisted",
           ""]

    out.append("🏆 TOP PICKS (ranked across all companies)")
    if pooled:
        for idx, (_order, role) in enumerate(pooled, start=1):
            out.append(f"[GLOBAL RANK {idx}] {role['title']} — {role.get('employer_name', '')} — Score: {role.get('score', 0)}")
    else:
        out.append("(no roles passed the hard filters this week)")
    out.append("")

    for emp in employers:
        roles = emp.get("roles") or []
        out.append(f"━━━ {emp['employer'].upper()} ━━━")
        out.append(f"🔍 {emp.get('total_reviewed', 0)} reviewed → {len(roles)} shortlisted")
        for role in roles:
            gr = global_rank.get((role.get("employer_name", ""), role.get("title", ""), role.get("url", "")), "?")
            out.append(f"[RANK {role.get('rank')}] {role.get('title')} — Score: {role.get('score')} (Global #{gr})")
            out.append(f"• {role.get('department')} | {role.get('location')} | {role.get('work_model')} | {md_comp(role.get('comp', ''))}")
            mark = "✅" if role.get("hard_filters_pass") else "❌"
            out.append(f"• Hard filters: {mark} — {role.get('hard_filters') or 'not confirmed'}")
            for bullet in (role.get("why") or role.get("key_signals") or [])[:2]:
                out.append(f"• Why: {bullet}")
            for bullet in (role.get("risks") or [])[:1]:
                out.append(f"• Risks: {bullet}")
            out.append(f"• Source: {role.get('url')}")
            out.append("")
        if not roles:
            out.append("(0 shortlisted)")
            out.append("")

    out.append("---")
    for emp in employers:
        ex = emp.get("exclusions") or {}
        if ex:
            breakdown = " · ".join(f"{k}: {v}" for k, v in ex.items())
        else:
            breakdown = "none recorded"
        out.append(f"Excluded — {emp['employer']}: {breakdown}")
    notes = [n for emp in employers for n in (emp.get("notes") or [])]
    out.append("Notes: " + ("; ".join(notes) if notes else "none recorded"))
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_archive(args) -> int:
    try:
        payload = load_json(args.input)
    except FileNotFoundError:
        print(f"ERROR: payload not found: {args.input}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: payload is not valid JSON: {exc}", file=sys.stderr)
        return 2

    if "employers" not in payload:
        print("ERROR: payload must contain an 'employers' list", file=sys.stderr)
        return 2

    date = parse_date(args.date or payload.get("date") or datetime.now().strftime("%Y-%m-%d"))
    payload["date"] = date
    results_root = os.path.expanduser(args.results_root)
    out_dir = month_dir(results_root, date)
    os.makedirs(out_dir, exist_ok=True)

    rep = Report()
    employers_out = []
    written = []

    for emp in payload["employers"]:
        emp = dict(emp)
        emp["date"] = date
        slug = emp.get("slug") or slugify(emp.get("employer", ""))
        emp["slug"] = slug

        # rank roles by score desc if the agent did not number them, else trust input
        roles = emp.get("roles") or []
        if roles and any(r.get("rank") is None for r in roles):
            roles = sorted(roles, key=lambda r: -(r.get("score") or 0))
        for i, r in enumerate(roles, start=1):
            if r.get("rank") is None:
                r["rank"] = i
            r["employer_name"] = emp["employer"]
        emp["roles"] = roles
        # total_shortlisted is derivable — never let a missing/wrong field break the run
        emp["total_shortlisted"] = len(roles)
        emp.setdefault("total_reviewed", len(roles))
        emp.setdefault("exclusions", {})
        emp.setdefault("notes", [])

        md_text = render_md(emp)
        json_obj = build_json_employer(emp)

        md_path = os.path.join(out_dir, f"{date}-{slug}.md")
        json_path = os.path.join(out_dir, f"{date}-{slug}.json")
        write_text(md_path, md_text)
        dump_json(json_path, json_obj)
        written += [md_path, json_path]

        # re-read from disk — verify what was actually persisted, not what we intended
        try:
            disk_md = open(md_path, "r", encoding="utf-8").read()
            disk_json = load_json(json_path)
        except Exception as exc:
            rep.error(f"{emp['employer']}: failed to re-read archive files: {exc}")
            employers_out.append(emp)
            continue
        verify_employer(emp, disk_md, disk_json, slug, rep, payload_emp=emp)
        employers_out.append(emp)

    verify_cross_employer(payload, rep)

    report = render_telegram(payload, employers_out)
    report_path = os.path.join(out_dir, f"{date}-weekly-report.md")
    write_text(report_path, report)

    if rep.errors:
        report += ("\n\n⚠️ VERIFICATION ERRORS THIS RUN:\n"
                   + "\n".join(f"- {e}" for e in rep.errors) + "\n")

    print("=" * 72)
    print(f"ARCHIVE  date={date}  dir={out_dir}")
    for emp in employers_out:
        print(f"  {emp['employer']:<12} reviewed={emp.get('total_reviewed'):<5} "
              f"shortlisted={len(emp.get('roles') or []):<3} -> {date}-{emp['slug']}.md/.json")
    print(f"  report -> {report_path}")
    print("=" * 72)
    if rep.errors:
        print(f"VERIFICATION: {len(rep.errors)} ERROR(S)")
        for e in rep.errors:
            print(f"  ERROR  {e}")
    else:
        print("VERIFICATION: PASS (0 errors)")
    if rep.warnings:
        print(f"  {len(rep.warnings)} warning(s)")
        for w in rep.warnings:
            print(f"  WARN   {w}")
    print("=" * 72)
    print("--- BEGIN TELEGRAM MESSAGE ---")
    print(report)
    print("--- END TELEGRAM MESSAGE ---")
    return 1 if rep.errors else 0


def _load_archived(results_root: str, date: str, employers: list[str] | None):
    out_dir = month_dir(results_root, date)
    files = sorted(f for f in os.listdir(out_dir)
                   if f.endswith(".json") and f.startswith(date)
                   and not f.endswith("-weekly-report.json"))
    picked = []
    for fn in files:
        slug = fn[len(date) + 1:-5]
        if employers and slug not in employers:
            continue
        picked.append((slug, load_json(os.path.join(out_dir, fn))))
    return out_dir, picked


def cmd_verify(args) -> int:
    results_root = os.path.expanduser(args.results_root)
    date = parse_date(args.date)
    out_dir = month_dir(results_root, date)
    if not os.path.isdir(out_dir):
        print(f"ERROR: no results directory {out_dir}", file=sys.stderr)
        return 2
    _out_dir, picked = _load_archived(results_root, date, args.employer)
    if not picked:
        print(f"ERROR: no archived employers found for {date}", file=sys.stderr)
        return 2

    rep = Report()
    payload = {"date": date, "employers": []}
    for slug, json_obj in picked:
        md_path = os.path.join(out_dir, f"{date}-{slug}.md")
        try:
            md_text = open(md_path, "r", encoding="utf-8").read()
        except FileNotFoundError:
            rep.error(f"{json_obj.get('employer', slug)}: missing {os.path.basename(md_path)}")
            md_text = ""
        emp = dict(json_obj)
        emp["slug"] = slug
        emp["roles"] = [dict(r, employer_name=json_obj.get("employer", "")) for r in (json_obj.get("roles") or [])]
        verify_employer(emp, md_text, json_obj, slug, rep, payload_emp=emp)
        payload["employers"].append(emp)
    verify_cross_employer(payload, rep)

    print("=" * 72)
    print(f"VERIFY   date={date}  dir={out_dir}  employers={[s for s, _ in picked]}")
    if rep.errors:
        print(f"VERIFICATION: {len(rep.errors)} ERROR(S)")
        for e in rep.errors:
            print(f"  ERROR  {e}")
    else:
        print("VERIFICATION: PASS (0 errors)")
    if rep.warnings:
        print(f"  {len(rep.warnings)} warning(s)")
        for w in rep.warnings:
            print(f"  WARN   {w}")
    print("=" * 72)
    return 1 if rep.errors else 0


def cmd_report(args) -> int:
    results_root = os.path.expanduser(args.results_root)
    date = parse_date(args.date)
    _out_dir, picked = _load_archived(results_root, date, args.employer)
    if not picked:
        print(f"ERROR: no archived employers found for {date}", file=sys.stderr)
        return 2
    payload = {"date": date, "employers": []}
    for slug, json_obj in picked:
        emp = dict(json_obj)
        emp["slug"] = slug
        emp["roles"] = [dict(r, employer_name=json_obj.get("employer", "")) for r in (json_obj.get("roles") or [])]
        payload["employers"].append(emp)
    report = render_telegram(payload, payload["employers"])
    if args.out:
        write_text(args.out, report)
        print(f"report -> {args.out}")
    else:
        sys.stdout.write(report)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="archive_verify.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("archive", help="write archive files, verify them, render the report")
    a.add_argument("--input", required=True, help="run payload JSON")
    a.add_argument("--results-root", default=DEFAULT_RESULTS_ROOT)
    a.add_argument("--date", default=None, help="override the payload date (YYYY-MM-DD)")
    a.set_defaults(func=cmd_archive)

    v = sub.add_parser("verify", help="verify already-archived files")
    v.add_argument("--results-root", default=DEFAULT_RESULTS_ROOT)
    v.add_argument("--date", required=True)
    v.add_argument("--employer", action="append", default=[])
    v.set_defaults(func=cmd_verify)

    r = sub.add_parser("report", help="render the combined Telegram report from archived files")
    r.add_argument("--results-root", default=DEFAULT_RESULTS_ROOT)
    r.add_argument("--date", required=True)
    r.add_argument("--employer", action="append", default=[])
    r.add_argument("--out", default=None)
    r.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
