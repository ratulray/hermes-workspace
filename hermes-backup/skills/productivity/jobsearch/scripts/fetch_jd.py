#!/usr/bin/env python3
"""Collect AI-leadership job candidates for the monthly corpus.

Lists an employer's postings, keeps only the ones that pass the four gates
in references/candidate-filter.md (leadership title, AI/ML signal, not a
business-leadership track, people-management evidence in the body), extracts
responsibilities/qualifications bullets, and writes one JD file per role in
the exact front-matter format the skillminer loader parses.

Usage:
    fetch_jd.py --employer OPENAI              # list candidates, '+' = eligible
    fetch_jd.py --employer OPENAI --pick 3     # write the top N as JD files
    fetch_jd.py --employer OPENAI --pick 3 --start-row 7

Environment:
    JD_MONTH      month being crawled (default: current YYYY-MM)
    JD_FETCHED_AT date written into each JD's front matter
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent          # .../jobsearch
DATA_DIR = Path(os.environ.get("JOBSEARCH_DATA_DIR", Path.home() / "Documents/jobsearch"))
EMPLOYERS_YAML = DATA_DIR / "EMPLOYERS.yaml"

# --- Title rules -----------------------------------------------------------

TITLE_KEEP = re.compile(
    r"\b(head of|director|vp|vice president|senior manager|sr\.? manager|"
    r"engineering manager|eng\.? manager|group manager|tech lead manager|manager)\b",
    re.I,
)
AI_HINT = re.compile(
    r"\b(ai|ml|llm|genai|agentic|agent|machine learning|model|inference|"
    r"data science|deep learning|nlp|mlops|applied science|research engineer)\b",
    re.I,
)
# Not engineering tracks at all.
NOT_AI = re.compile(
    r"\b(account executive|sales|recruiter|marketing|finance|legal|hr|people ops|"
    r"security engineer|site reliability|sre)\b",
    re.I,
)
# "Manager" that leads a program, not people.
NOT_LEADERSHIP = re.compile(
    r"\b(technical program manager|program manager|tpm|product manager|"
    r"project manager|partnerships?|policy manager|solutions manager|"
    r"architect(ure)?s?|architect |outcomes manager|alliances manager|"
    r"strategy & operations|strategy and operations)\b",
    re.I,
)
# Business-leadership / customer-facing tracks.
NOT_ORG_LEADERSHIP = re.compile(
    r"\b(regional director|ai success manager|success manager|account executive|"
    r"solutions engineer|solutions engineering|solution strategy|"
    r"professional services|customer engineer|customer advocacy|"
    r"technical support|support engineering|lifecycle growth|growth manager|"
    r"deployment manager|ai deployment|alliances manager|marketplace partner|"
    r"field marketing|global policy|public policy|corporate development|"
    r"communications|pr director|talent acquisition|recruiting|legal|"
    r"litigation|counsel|cyber ai partner|chief of staff|partnerships|"
    r"product design|customer success & support|of services)\b",
    re.I,
)
# "Head of <region-or-function>" is a business head, not an engineering head.
HEAD_OF_NON_ENG = re.compile(
    r"\bhead of (?!ai\b|applied|engineering|eng\b|machine learning|ml\b|"
    r"technical|data|research|product|developer|platform|infrastructure|"
    r"artificial intelligence)\w+",
    re.I,
)
# People-management evidence. The bare token "manager" is deliberately absent:
# it appears in every title and in boilerplate, so it accepts every IC role.
MANAGE_EVIDENCE = re.compile(
    r"\b(direct reports?|reports to|manage(s|d|r)? a team of|managing a team|"
    r"managing and leading|leading a team|leads? a team of|"
    r"headcount|team of \d+|\d+\+ (direct )?reports|"
    r"mentors?|coaching|performance reviews?|hiring and|"
    r"build(ing)? a team|build and grow|grow(ing)? a team|"
    r"owns? the team|people manager|group manager|"
    r"manage the (team|group|org|organization)|"
    r"leadership of (the|a) (team|group|org))\b",
    re.I,
)

# --- Helpers ----------------------------------------------------------------


def slug(s: str, maxlen: int = 44) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    if len(s) <= maxlen:
        return s
    # Truncated names would collide across similar titles - append a short hash.
    digest = hashlib.sha1(s.encode("utf-8")).hexdigest()[:6]
    return s[:maxlen].rstrip("-") + "-" + digest


def strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|li|div|h\d)>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return "\n".join(ln.strip() for ln in s.split("\n")).strip()


def load_employers() -> dict:
    """Parse EMPLOYERS.yaml without needing pyyaml in the ambient interpreter.

    Entries are `KEY: value` (inline) or `KEY:` followed by indented
    `url:` / `api_endpoint:` / `job_id_url_pattern:` lines.
    """
    out: dict[str, dict] = {}
    text = EMPLOYERS_YAML.read_text(encoding="utf-8")
    cur_key = None
    in_categories = False
    for raw in text.split("\n"):
        if raw.startswith("monthly_corpus:"):
            break
        if raw.startswith("categories:"):
            in_categories = True
            continue
        if not in_categories or not raw.strip() or raw.strip().startswith("#"):
            continue
        m = re.match(r"^    ([A-Z_0-9]+):\s*(.*)$", raw)
        if m:
            cur_key = m.group(1)
            val = m.group(2).strip()
            out[cur_key] = {
                "url": val or None,
                "api_endpoint": None,
                "job_id_url_pattern": None,
            }
            continue
        m = re.match(r"^      (url|api_endpoint|job_id_url_pattern|note):\s*(.+)$", raw)
        if m and cur_key:
            out[cur_key][m.group(1)] = m.group(2).strip().strip('"')
    return out


def fetch(url: str) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["curl", "-sL", "--max-time", "40", "-A",
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "Chrome/120 Safari/537.36", url],
            capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def fetch_json(url: str):
    rc, body = fetch(url)
    if rc != 0 or not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def candidates(emp: dict) -> list[dict]:
    """Return [{title, location, url, content_html}] for one employer."""
    out: list[dict] = []
    api = emp.get("api_endpoint")
    if api:
        data = fetch_json(api)
        jobs = []
        if isinstance(data, dict):
            jobs = data.get("jobs") or data.get("postings") or []
        elif isinstance(data, list):
            jobs = data
        for j in jobs:
            title = (j.get("title") or j.get("name") or "").strip()
            loc = j.get("location") or ""
            if isinstance(loc, dict):
                loc = loc.get("name") or ""
            # Ashby uses descriptionHtml/descriptionPlain; Greenhouse uses content.
            content = (j.get("contentHtml") or j.get("descriptionHtml")
                       or j.get("content") or j.get("description")
                       or j.get("descriptionPlain") or "")
            url = j.get("jobUrl") or j.get("absolute_url") or ""
            out.append({"title": title, "location": str(loc), "url": url,
                        "content_html": content})
        if out:
            return out

    url = emp.get("url")
    if not url:
        return out
    rc, body = fetch(url)
    if rc != 0 or not body:
        return out
    m = re.search(r"boards-api\.greenhouse\.io/v1/boards/([a-z0-9]+)/jobs", url)
    if m:
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs?content=true")
        for j in (data or {}).get("jobs", []):
            out.append({
                "title": (j.get("title") or "").strip(),
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "content_html": j.get("content", ""),
            })
        return out
    for m in re.finditer(r'href="([^"]*(?:job|career|position)[^"]*)"[^>]*>([^<]{4,120})<',
                         body, re.I):
        href, anchor = m.group(1), m.group(2).strip()
        if not anchor or anchor.lower() in {"jobs", "careers", "search"}:
            continue
        out.append({"title": anchor, "location": "", "url": href, "content_html": ""})
    return out


def is_eligible(c: dict) -> bool:
    """The four gates from references/candidate-filter.md."""
    t = c.get("title", "")
    if NOT_AI.search(t) or NOT_LEADERSHIP.search(t) or NOT_ORG_LEADERSHIP.search(t):
        return False
    if HEAD_OF_NON_ENG.search(t):
        return False
    if not TITLE_KEEP.search(t):
        return False
    body = c.get("content_html", "") or ""
    if not (AI_HINT.search(t) or AI_HINT.search(body[:4000])):
        return False
    if not MANAGE_EVIDENCE.search(body[:8000]):
        return False
    return True


def rank(c: dict) -> int:
    """Higher = better match. Seniority first, then AI signal, then focus."""
    t = c.get("title", "")
    score = 0
    if re.search(r"\b(head of|director|vp)\b", t, re.I):
        score += 4
    elif re.search(r"\b(senior|sr\.?)\b.*\bmanager|\bmanager\b", t, re.I):
        score += 3
    if AI_HINT.search(t):
        score += 5
    else:
        score += 1          # AI signal came from the body only
    if re.search(r"\b(platform|infrastructure|inference|applied|agentic|llm|ai)\b", t, re.I):
        score += 2
    if re.search(r"\b(engineering|ai|ml|research|applied)\b", t, re.I):
        score += 2
    return score


# --- Heading-aware section split --------------------------------------------
# Most ATS boards mark their own sections. The marker-based split below reads
# the flattened text, so a heading that appears in a different shape than the
# marker list (Ashby puts "RESPONSIBILITIES" in <p><strong>, Greenhouse nests
# it at <h3>/<h4>, Airbnb says "A Typical Day:") puts the duties in the wrong
# bucket. These helpers read the posting's own headings instead.

_RESP_HEAD = re.compile(
    r"^(?:responsibilit|what you(?:['’]ll| will) do|"
    r"what you(?:['’]ll| will) be doing|your role|the role|about the role|"
    r"duties|a typical day|"
    r"as an engineering manager\b.*\byou will\b|key job responsibilities|"
    r"in this role,? you will\b|you will\b|what you will do\b|"
    r"key responsibilities|main responsibilities|job responsibilities)",
    re.I)

_QUAL_HEAD = re.compile(
    r"^(?:qualification|minimum qual|minimum requirement|basic qual|"
    r"preferred qual|preferred requirement|"
    r"who you are|what we(?:['’]re| are) looking for|"
    r"we(?:['’]re| are) looking for|"
    r"you may be a good fit|you(?:['’]ll| might) thrive|about you|you have|"
    r"your expertise|requirements|skills you have)",
    re.I)

# Intro sentences that sit under a qualification heading but are not requirements.
_INTRO_HEAD = re.compile(
    r"^(?:we(?:['’]re| are) looking for someone who|"
    r"we(?:['’]re| are) looking for|"
    r"if you meet these requirements|we are looking for)", re.I)

_TAG = re.compile(r"(?is)<(/?)([a-z0-9]+)((?:\"[^\"]*\"|'[^']*'|[^>])*)>")
_VOID = {"br", "img", "hr", "meta", "link", "input"}


class _Node:
    """DOM node that keeps text and children in document order.

    `parts` is a list of str (text) and _Node (child) entries, so text that
    follows an inline child (e.g. <strong>) stays after it.
    """

    __slots__ = ("tag", "parts", "children")

    def __init__(self, tag):
        self.tag = tag
        self.parts = []
        self.children = []

    def add_text(self, s):
        self.parts.append(s)

    def add_child(self, node):
        self.parts.append(node)
        self.children.append(node)


def _parse_html(html: str) -> _Node:
    """Minimal DOM: enough to find headings, list items and paragraphs."""
    root = _Node("root")
    stack = [root]
    pos = 0
    skip = 0
    for m in _TAG.finditer(html):
        raw = html[pos:m.start()]
        pos = m.end()
        if raw:
            stack[-1].add_text(raw)
        closing, tag = m.group(1), m.group(2).lower()
        if tag in ("script", "style"):
            skip = max(0, skip + (-1 if closing else 1))
            continue
        if skip:
            continue
        if not closing:
            node = _Node(tag)
            stack[-1].add_child(node)
            if tag not in _VOID:
                stack.append(node)
        else:
            for i in range(len(stack) - 1, 0, -1):
                if stack[i].tag == tag:
                    del stack[i:]
                    break
    tail = html[pos:]
    if tail:
        stack[-1].add_text(tail)
    return root


def _node_text(node: _Node) -> str:
    parts = []

    def walk(n):
        for part in n.parts:
            if isinstance(part, str):
                parts.append(part)
                continue
            if part.tag in ("script", "style"):
                continue
            if part.tag == "br":
                parts.append(" ")
                continue
            walk(part)

    walk(node)
    s = html.unescape("".join(parts))
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    return re.sub(r"[\u00a0\s]+", " ", s).strip()


def _is_heading(node: _Node) -> bool:
    if re.fullmatch(r"h[1-6]", node.tag):
        return True
    if node.tag == "p":
        kids = [c for c in node.children if c.tag != "br"]
        return len(kids) == 1 and kids[0].tag == "strong"
    return False


def _heading_text(node: _Node) -> str:
    if re.fullmatch(r"h[1-6]", node.tag):
        return _node_text(node)
    return _node_text(node.children[0])


def _heading_tokens(html: str) -> list[tuple[str, str]]:
    """[('H', heading) | ('B', bullet) | ('P', paragraph)] in document order."""
    root = _parse_html(html)
    out = []

    def emit_list(ul):
        for li in [c for c in ul.children if c.tag == "li"]:
            own = [c for c in li.children if c.tag != "ul"]
            sub = _Node("li")
            sub.parts = [p for p in li.parts
                         if isinstance(p, str) or p.tag != "ul"]
            sub.children = own
            t = _node_text(sub)
            if t:
                out.append(("B", t))
            for c in li.children:
                if c.tag == "ul":
                    emit_list(c)

    def walk(node):
        for child in node.children:
            if child.tag in ("script", "style"):
                continue
            if _is_heading(child):
                t = _heading_text(child)
                if t:
                    out.append(("H", t))
                continue
            if child.tag == "ul":
                emit_list(child)
                continue
            if child.tag == "p":
                t = _node_text(child)
                if t:
                    out.append(("P", t))
                continue
            walk(child)

    walk(root)
    return out


def _heading_split(content: str):
    """(resp, qual, other) from the posting's own headings.

    Returns ([], [], []) when the posting has no usable section headings, so
    the caller keeps its existing marker-based behaviour.
    """
    # Greenhouse stores the body HTML-escaped; unescape before matching tags.
    resp, qual, other = [], [], []
    mode = None
    saw_resp = saw_qual = False
    for kind, val in _heading_tokens(html.unescape(content)):
        if kind == "H":
            bare = re.sub(r"\s+", " ", val.strip().rstrip(":").strip())
            if _RESP_HEAD.match(bare):
                mode, saw_resp = "resp", True
            elif _QUAL_HEAD.match(bare):
                mode, saw_qual = "qual", True
            else:
                mode = "other"
            continue
        if mode == "resp":
            resp.append(val)
        elif mode == "qual":
            qual.append(val)
        else:
            other.append(val)
    if not (saw_resp and saw_qual):
        return [], [], []
    return resp, qual, other


def _heading_bullet_ok(ln: str) -> bool:
    s = ln.strip()
    if len(s) < 12 or len(s) > 400:
        return False
    if s.endswith(":") and len(s) < 60:
        return False
    low = s.lower()
    if low.startswith(("what you", "who you", "we\u2019re looking", "we're looking",
                       "we are looking", "minimum qual", "basic qual", "preferred qual",
                       "responsibilit", "about the role", "the role",
                       "a typical day", "your expertise", "key job")):
        return False
    if _INTRO_HEAD.match(s):
        return False
    return True


def bullets_from(content: str) -> tuple[list[str], list[str], str]:
    """Split posting content into (responsibilities, qualifications, excerpt)."""
    text = strip_html(content)
    if not text:
        return [], [], ""

    # Prefer the posting's own section headings; fall back to marker scanning.
    h_resp, h_qual, _ = _heading_split(content)
    if h_resp or h_qual:
        r = [b for b in h_resp if _heading_bullet_ok(b)]
        q = [b for b in h_qual if _heading_bullet_ok(b)]
        if r and q:
            return r[:12], q[:12], text[:2500]
    low = text.lower()
    resp_markers = ["what you'll do", "what you will do", "what you'll be doing",
                    "responsibilities", "your role", "the role", "you will:",
                    "in this role, you will", "about the role", "role:", "duties"]
    qual_markers = ["who you are", "what we're looking for", "minimum qualifications",
                    "basic qualifications", "preferred qualifications", "qualifications",
                    "you have", "requirements", "skills", "who you are seeking",
                    "we're looking for"]

    def first_index(markers):
        idx = [(low.find(m), m) for m in markers if low.find(m) != -1]
        return sorted(idx)

    r_idx, q_idx = first_index(resp_markers), first_index(qual_markers)
    r_pos = r_idx[0][0] if r_idx else -1
    q_pos = q_idx[0][0] if q_idx else -1
    if r_pos == -1 and q_pos == -1:
        return [ln for ln in text.split("\n") if ln.strip()][:14], [], text[:2500]
    if r_pos == -1:
        r_pos, q_pos = q_pos, -1
    if q_pos != -1 and q_pos < r_pos:
        r_pos, q_pos = q_pos, r_pos
        resp_seg, qual_seg = text[r_pos:], text[:r_pos]
    else:
        resp_seg = text[r_pos:q_pos] if q_pos != -1 else text[r_pos:]
        qual_seg = text[q_pos:] if q_pos != -1 else ""

    def to_bullets(seg: str, cap: int) -> list[str]:
        out = []
        for ln in seg.split("\n"):
            ln = ln.strip()
            if len(ln) < 12 or len(ln) > 400:
                continue
            if ln.lower().startswith(("what you", "who you", "we're looking", "we are looking",
                                      "minimum qual", "basic qual", "preferred qual",
                                      "responsibilit", "about the role", "the role")):
                continue
            if ln.endswith(":") and len(ln) < 60:
                continue
            out.append(ln)
            if len(out) >= cap:
                break
        return out

    return to_bullets(resp_seg, 12), to_bullets(qual_seg, 12), text[:2500]


def yaml_quote(s: str) -> str:
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
    return f'"{s}"'


def write_jd(path: Path, row: int, company: str, title: str, url: str, status: str,
             location: str, comp: str, team_scope: str, resp: list[str],
             qual: list[str], excerpt: str) -> None:
    lines = [
        "---",
        f"row: {row}",
        f"company: {yaml_quote(company)}",
        f"title: {yaml_quote(title)}",
        f"source_url: {yaml_quote(url)}",
        f"fetched_url: {yaml_quote(url)}",
        f"fetched_at: {os.environ.get('JD_FETCHED_AT', '2026-11-14')}",
        f"status: {status}",
        f"work_model: {yaml_quote('unknown')}",
        f"location: {yaml_quote(location or 'unknown')}",
        f"comp: {yaml_quote(comp or 'not stated')}",
        f"team_scope: {yaml_quote(team_scope or 'not stated')}",
        "responsibilities:",
    ]
    for b in (resp or ["Responsibilities not stated in the posting"]):
        lines.append(f"  - {yaml_quote(b)}")
    lines.append("qualifications:")
    for b in (qual or ["Qualifications not stated in the posting"]):
        lines.append(f"  - {yaml_quote(b)}")
    lines.append("raw_excerpt: |")
    for ln in (excerpt or "").split("\n"):
        lines.append(f"  {ln}")
    lines.append("---")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fetch_jd")
    ap.add_argument("--employer", required=True)
    ap.add_argument("--pick", type=int, default=0, help="write top N JDs (0 = list only)")
    ap.add_argument("--start-row", type=int, default=1)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--list", action="store_true", help="print candidates with eligibility")
    a = ap.parse_args(argv)

    emps = load_employers()
    emp = emps.get(a.employer)
    if not emp:
        print(f"ERROR: employer {a.employer} not in EMPLOYERS.yaml", file=sys.stderr)
        return 2

    cands = candidates(emp)
    if not cands:
        print(f"{a.employer}: NO CANDIDATES (portal unreachable or blocked)")
        return 0

    scored = sorted(cands, key=lambda c: -rank(c))
    if a.list:
        for c in scored:
            mark = "+" if is_eligible(c) else " "
            body_len = len(c.get("content_html", "") or "")
            print(f" {mark}[{rank(c):3d}] {c['title'][:64]:64s} | body={body_len:6d} | {str(c['location'])[:24]}")
        n_ok = sum(1 for c in cands if is_eligible(c))
        print(f"  ({n_ok}/{len(cands)} eligible; '+' = passes all four gates)")
        if n_ok == 0:
            print("  NOTE: if body=0 for every row, the ATS description field name is wrong - "
                  "see references/candidate-filter.md")
        return 0

    month = os.environ.get("JD_MONTH", "2026-11")
    out_dir = a.out_dir or (DATA_DIR / "results" / month / "jds")
    out_dir.mkdir(parents=True, exist_ok=True)

    kept, row, seen_titles = 0, a.start_row, set()
    for c in scored:
        if kept >= a.pick:
            break
        if not is_eligible(c):
            continue
        t = c["title"].strip()
        if not t or t.lower() in seen_titles:
            continue
        seen_titles.add(t.lower())
        resp, qual, excerpt = bullets_from(c.get("content_html", ""))
        if not resp and not qual:
            rc, body = fetch(c.get("url", ""))
            if rc == 0 and body:
                resp, qual, excerpt = bullets_from(body)
        if not resp and not qual:
            continue
        company = a.employer.replace("_", " ").title()
        fn = out_dir / f"{row:02d}-{slug(company)}-{slug(t)}.md"
        write_jd(fn, row, company, t, c.get("url", ""), "ok",
                 str(c.get("location", "")), "", "", resp, qual, excerpt)
        print(f"  wrote {fn.name}")
        kept += 1
        row += 1
    print(f"{a.employer}: {len(cands)} candidates -> {kept} kept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
