---
name: monthly-skill-mining
description: Run the repeatable monthly analysis that turns crawled AI-leadership JDs into ranked technical and leadership/management skill snapshots. Use when asked to refresh the skills snapshot, mine skills from this month's JDs, extend the skill taxonomy, score against the gold file, or compare two months. Always call run.sh — never `python -m skillminer` directly.
---

# Monthly skill mining

Deterministic Python pipeline over `~/Documents/jobsearch/results/<YYYY-MM>/jds/*.md`. Source of truth for the monthly skill snapshot — supersedes any LLM-based extraction.

**Implementation lives at** `~/Documents/jobsearch/tools/skills/`. **This skill's interface** is `run.sh`, a thin wrapper that always invokes the project's own `.venv/bin/python` regardless of the calling shell. Never call `python -m skillminer` directly — that picks up whatever Python the agent's terminal happens to have activated, which is almost never the right one.

## Commands

```bash
# Analyse a month's JDs and write results/<month>/skills/<month>-*.{md,json,html}
~/Documents/jobsearch/tools/skills/run.sh run  --month 2026-10

# Score the most recent run against the gold file (tests/gold/<month>.json)
~/Documents/jobsearch/tools/skills/run.sh gold --month 2026-10 --detail

# Group unmatched bullets by meaning (one-time install of requirements-suggest.txt)
~/Documents/jobsearch/tools/skills/run.sh suggest --month 2026-10

# Run the test suite
~/Documents/jobsearch/tools/skills/run.sh pytest
```

`run.sh` is `chmod +x` and exits 127 with a clear error if the venv is missing — in that case run `bootstrap.sh` once (cold-rebuild path; idempotent):

```bash
~/Documents/jobsearch/tools/skills/bootstrap.sh
```

The hermes-workspace backup cron excludes `.venv/`, so a clean restore from backup will lack the venv and need bootstrap. The wrapper is the same every session — no `source .venv/bin/activate`, no `cd` to the project, no PATH gymnastics.

## Monthly workflow

1. **Crawl JDs** into `~/Documents/jobsearch/results/<YYYY-MM>/jds/` using the `jobsearch` skill (monthly corpus mode: tech-only employer pool from `EMPLOYERS.yaml`, max 30 JDs, max 3 per employer, plus a `corpus-manifest.json` for that month). Frontmatter on each JD file must include `company`, `title`, `status`, `responsibilities`, `qualifications`; the loader raises if a JD yields no bullets.
2. **Run analysis:** `run.sh run --month <YYYY-MM>`. If it warns about *unclassified companies*, add them to `~/Documents/jobsearch/tools/skills/companies.yaml` (tiers: `prominent` / `established` / `emerging`; rubric at the top of that file). Read the "possible duplicate" lines; confirm and list duplicates in `results/<month>/skills/overrides.yaml` under `exclude_jds`.
3. **Review residue:** open `results/<month>/skills/<month>-residue.md`. For each bullet that holds a real skill, add a pattern to the right skill in `taxonomy.yaml` (or a new skill — never rename an `id`); then re-run.
   * Optional: `pip install -r requirements-suggest.txt` once, then `run.sh suggest --month <month>` writes `<month>-suggestions.md`, grouping unmatched bullets by meaning. A group that recurs across JDs is the signal for a new skill or missing pattern. Read the bullets, not the nearest-skill hints.
4. **Spot-check evidence:** `results/<month>/skills/<month>-evidence.json` is the JD bullet behind every hit. For any skill that looks inflated, tighten the regex in `taxonomy.yaml` rather than editing outputs.
5. **Run tests:** `run.sh pytest`. Re-running overwrites the outputs in `results/<month>/skills/`. Diff months by comparing `by_bucket.*.jd_pct` in the JSON snapshots.
6. **Excluded companies:** anything tiered `excluded` in `companies.yaml` is dropped automatically.

## Why a deterministic pipeline, not LLM extraction

LLM-based skill extraction (extract phrases → cluster into a taxonomy) is a viable fallback when no deterministic tool exists, but it produces unstable outputs: roughly 30% phrase-to-canonical mapping, hundreds of singleton phrases (each in only 1 JD), and a taxonomy that drifts every run because the clustering is non-deterministic. That makes month-over-month diffs noisy.

A deterministic regex-over-bullets extractor with a hand-curated taxonomy solves this: stable skill ids, fixed patterns, a gold file + test suite that gates regressions, and a residue report that surfaces the new-skill signal only when a real pattern recurs. Reach for the deterministic tool first; reserve LLM extraction for corpora that don't have one.

## The run.sh wrapper pattern

Whenever an agent-invoked tool depends on a project-local `.venv`, the skill must wrap it in a `run.sh` that hardcodes the venv path and the project root. Bare `python -m skillminer` calls fail unpredictably — they pick up whatever Python the agent's terminal happens to have activated.

Wrapper template (`run.sh` in the project root):

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/.venv/bin/python"
[[ -x "$VENV_PY" ]] || { echo "error: venv not found. run bootstrap.sh first." >&2; exit 127; }
cd "$SCRIPT_DIR"
exec "$VENV_PY" -m <package> "$@"
```

`set -euo pipefail` surfaces errors immediately. `SCRIPT_DIR` makes the wrapper callable from any cwd. `exec` replaces the shell so the venv is the actual interpreter, not a child. The 127 exit code tells the agent clearly that bootstrap is needed, not that the script is buggy.

Pair with `bootstrap.sh` (idempotent venv creator) because the hermes-workspace backup cron excludes `.venv/` — a clean restore from backup will lack the venv.

## Rules

- Never rename a skill `id`; append only — month-over-month diffs depend on stable ids.
- Patterns are case-insensitive regexes on a raw bullet. One bullet may hit several skills. Keep YAML strings single-quoted. Avoid bare generic words (`ml`, `latency`, `scalab`) — the 2026-10 tuning showed they inflate counts. The test suite rejects patterns that match the empty string.
- `--use-excerpt` also scans `raw_excerpt`; off by default because it adds company boilerplate (e.g. "we can hire people in any country" → hiring).
- The 2026-10 gold file is a reference, not ground truth; do not tune patterns just to raise its score. Refresh it deliberately when the taxonomy changes.

## Outputs in `results/<month>/skills/`

- `<month>-skills-snapshot.html` — interactive report
- `<month>-skills-snapshot.json` — same data, machine-readable; two buckets (`technical`, `leadership_management`); per-skill `JD%`, `company%`, and `% Prominent` (share of prominent-company JDs only), with every matching bullet and its company
- `<month>-evidence.json` — JD bullet behind every hit
- `<month>-residue.md` — bullets that matched nothing
- `overrides.yaml` — manual exclusions (duplicates etc.)
