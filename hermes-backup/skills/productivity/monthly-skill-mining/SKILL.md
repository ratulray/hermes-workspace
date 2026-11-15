---
name: monthly-skill-mining
description: Mine monthly AI-leadership JDs for skill trends.
version: 1.1.0
author: Ratul Ray
license: MIT
metadata:
  hermes:
    tags: [career, job-search, skills-analysis, productivity]
    related_skills: [jobsearch]
---

# Monthly skill mining

Deterministic Python pipeline over `~/Documents/jobsearch/results/<YYYY-MM>/jds/*.md`. Source of truth for the monthly skill snapshot — supersedes any LLM-based extraction.

**Implementation lives at** `~/Documents/jobsearch/tools/skills/`. **This skill's interface** is `run.sh`, a thin wrapper that always invokes the project's own `.venv/bin/python` regardless of the calling shell. Never call `python -m skillminer` directly — that picks up whatever Python the agent's terminal happens to have activated, which is almost never the right one.

## When to Use

- The user asks to refresh or re-run the monthly skills snapshot, mine this month's JDs for skills, extend the taxonomy, score against the gold file, or compare two months.
- The monthly cron analysis job fires (it loads this skill).
- The January annual trend job fires (it loads this skill).

Do NOT use it to fetch job postings — that is the `jobsearch` skill (monthly corpus mode crawls the JDs this skill then analyses). Do NOT use it to rank a shortlist for applying.

## Commands

```bash
# Analyse a month's JDs and write results/<month>/skills/<month>-*.{md,json,html}
~/Documents/jobsearch/tools/skills/run.sh run  --month 2026-10

# Score the most recent run against the gold file (tests/gold/<month>.json)
~/Documents/jobsearch/tools/skills/run.sh gold --month 2026-10 --detail

# Group unmatched bullets by meaning (one-time install of requirements-suggest.txt)
~/Documents/jobsearch/tools/skills/run.sh suggest --month 2026-10

# Run the test suite (run.sh only wraps the `skillminer` CLI: run/gold/suggest)
~/Documents/jobsearch/tools/skills/.venv/bin/python -m pytest ~/Documents/jobsearch/tools/skills/tests -q
```

`run.sh` exposes no `pytest` subcommand — `run.sh pytest` fails with `invalid choice: 'pytest'`. Run pytest through the venv directly.

`run.sh` is `chmod +x` and exits 127 with a clear error if the venv is missing — in that case run `bootstrap.sh` once (cold-rebuild path; idempotent):

```bash
~/Documents/jobsearch/tools/skills/bootstrap.sh
```

The hermes-workspace backup cron excludes `.venv/`, so a clean restore from backup will lack the venv and need bootstrap. The wrapper is the same every session — no `source .venv/bin/activate`, no `cd` to the project, no PATH gymnastics.

## Monthly workflow

1. **Crawl JDs** into `~/Documents/jobsearch/results/<YYYY-MM>/jds/` using the `jobsearch` skill (monthly corpus mode: tech-only employer pool from `EMPLOYERS.yaml`, max 30 JDs, max 3 per employer, plus a `corpus-manifest.json` for that month). Frontmatter on each JD file must include `company`, `title`, `status`, `responsibilities`, `qualifications`; the loader raises if a JD yields no bullets.
2. **Renumber the JDs.** The analyzer derives a JD's id from the filename prefix, so parallel crawl workers that each start at 01 collide — and `overrides.yaml`, keyed by row-id, then drops the wrong files. Run `python3 ~/Documents/jobsearch/tools/skills/renumber_jds.py --month <YYYY-MM>` after the crawl and before step 3. It renumbers filenames 01..N sequentially and rewrites the `row:` front-matter field.
3. **Run analysis:** `run.sh run --month <YYYY-MM>`. If it warns about *unclassified companies*, add them to `~/Documents/jobsearch/tools/skills/companies.yaml` (tiers: `prominent` / `established` / `emerging`; rubric at the top of that file). Read the "possible duplicate" lines; confirm and list duplicates in `results/<month>/skills/overrides.yaml` under `exclude_jds`.
4. **Review residue:** open `results/<month>/skills/<month>-residue.md`. For each bullet that holds a real skill, add a pattern to the right skill in `taxonomy.yaml` (or a new skill — never rename an `id`); then re-run.
   * Optional: `pip install -r requirements-suggest.txt` once, then `run.sh suggest --month <month>` writes `<month>-suggestions.md`, grouping unmatched bullets by meaning. A group that recurs across JDs is the signal for a new skill or missing pattern. Read the bullets, not the nearest-skill hints.
5. **Spot-check evidence:** `results/<month>/skills/<month>-evidence.json` is the JD bullet behind every hit. For any skill that looks inflated, tighten the regex in `taxonomy.yaml` rather than editing outputs.
6. **Run tests:** `~/Documents/jobsearch/tools/skills/.venv/bin/python -m pytest ~/Documents/jobsearch/tools/skills/tests -q` (`run.sh` has no `pytest` subcommand). Re-running overwrites the outputs in `results/<month>/skills/`. Diff months by comparing `by_bucket.*.jd_pct` in the JSON snapshots.
7. **Excluded companies:** anything tiered `excluded` in `companies.yaml` is dropped automatically.

## Scheduled pipeline

The monthly cycle is automated by three cron jobs. A manual invocation is for ad-hoc reruns and debugging only — when the crons exist, do not re-run the steps by hand and re-deliver the same result.

| Job | Schedule (PT) | Does |
|---|---|---|
| Monthly Job Corpus Crawl (`b72ae4006bc3`) | 2am, 2nd of month | Crawls ≤30 JDs from the `monthly_corpus.pool` into `results/<YYYY-MM>/jds/`; writes `corpus-manifest.json`. Skill: `jobsearch`. |
| Monthly Skill Mining Analysis (`43ae1fd410f5`) | 4am, 6th of month | `run.sh run`, auto-tiers new companies, gold-scores, diffs against the prior month, delivers a narrative. |
| Annual Skill Trend Report (`23722d31b53b`) | 5am, 5 January | Runs `scripts/annual_trends.py` across the year's snapshots; classifies continuous / rising / fading. |

All three deliver to the Telegram "Job Search" group (`telegram:-5179227170`) and carry `catch_up: true`, so a machine that was off still fires on return.

Why crawl on the 2nd and analyse on the 6th: postings are freshest early in the month, and the four-day gap lets the crawl finish before the analysis reads its output.

**Auto-tiering is on for scheduled runs.** When the analysis job reports unclassified companies it adds them to `companies.yaml` itself using the rubric at the top of that file, marking any borderline call `confidence: low`. A tier only drives the `% Prominent` column, so a wrong tier shifts that column without touching the main JD% ranking — but review `confidence: low` entries before trusting the prominent figures.

See `references/scheduled-pipeline.md` for job prompts, the delivery target, and how to change a schedule.

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
- The 2026-10 gold file is a reference, not ground truth; do not tune patterns just to raise its score. Refresh it deliberately when the taxonomy changes. **Note:** the original hand-reviewed 2026-10 reference was overwritten during the v5 taxonomy work and could not be recovered (the tools directory has no git history and no backup copy). It is now a regex snapshot of the current run, so F1 against it reads 1.000 and is not a quality score — it only catches a change that breaks matching entirely. To restore a real quality signal, hand-review a fresh reference over a sample of JDs and write that file instead.

## Pitfalls

- **A JD that matches no skill must still appear in `per_jd`.** That map is the denominator set for month-over-month diffs. If it is built from only the JDs that produced at least one hit, a company whose bullets the taxonomy misses vanishes from the diff and reads as a market shift that never happened. Build `per_jd` from every loaded JD minus the explicit exclusions (`overrides.yaml`, `excluded` tier in `companies.yaml`), never from the matching subset.
- **Fewer than 3 months of snapshots is not a trend.** One month classifies every skill as `emerging`, which means nothing — say so rather than presenting a direction.
- **The snapshot JD count is lower than the JD file count, and that is correct.** `companies.yaml` tiers `excluded` and `overrides.yaml` `exclude_jds` are applied by design. Check those two files before suspecting the loader dropped something.
- **Do not hand-write the snapshot or the HTML.** `run.sh run` emits the JSON, HTML, evidence and residue files together; hand-editing one of them desynchronises it from the others.
- **Test fixtures must not share a temp directory.** If every test writes into one tmp dir, the first test's multi-month fixtures leak into the single-month test and it fails on data it never created — the test blames the code under test instead of the harness. Give each test its own `tempfile.mkdtemp()` and remove it in a `finally` block.
- **A skill that skips early months and appears later is "new", not "emerging".** Classifying on present-count alone reads a skill that skipped the first half of the year as an ordinary newcomer. Compare the first-present month against the months that came before it: if the skill was absent from earlier months, it is new regardless of how many months it appears in.
- **Recruiting boilerplate must be filtered before matching, not after.** A single EEO/accommodation paragraph matched four leadership skills on its own and was the *only* evidence for two of them in the affected JDs — so those skills looked present in postings that required nothing of the sort. Filter boilerplate in the loader (`skillminer/jd.py::_BOILERPLATE`) so every month is protected, and cover it with a test. Be careful not to over-filter: a genuine bullet like "Lead and develop engineers. Hire, coach, and grow a team ... fostering an inclusive culture" must survive, because it *is* real management evidence.
- **A month-over-month diff is only meaningful if the corpus method is identical.** The JD%-difference between two months measures the corpus, not the market, whenever the employer pool, the crawl method, or the per-employer caps changed. Check company overlap between the two snapshots first: if only a handful of companies appear in both, the diff is not a trend. When the corpus method changes, the older month must be re-crawled before the two can be compared — or the newer month becomes the baseline and the older one is discarded as pre-methodology. Also record in the baseline file whether the month is comparable to the previous one, so the next run does not silently diff against a differently-collected corpus.
- **A bare domain noun in a pattern matches every bullet in the domain.** `model_evaluation_and_safety` admits bare `safety`, `validation` and `experimentation`; in the 2026-11 corpus 37 of its 116 evidence bullets matched only those tokens, and 8 of its 34 JDs had no genuine evaluation/safety evidence at all (Stripe "trust and safety", Mistral "provisioning, configuration, validation, burn-in", Perplexity "identity, verification, access control"). Its 56.7% JD% overstated the true figure by ~8–13 JDs. Before trusting a high JD%, classify each skill's evidence bullets into strong (skill-specific vocabulary) and weak (generic noun) and count JDs whose evidence is weak-only — that count is the inflation.
- **A pattern that needs alternation, character-class budgets or negative lookaheads does not belong in `taxonomy.yaml`.** YAML single-quoted strings keep backslashes literal, so a `\b` written through a Python string or an `re.sub` replacement can silently become a backspace byte or a real newline and corrupt the file — the symptom is a `yaml.reader.ReaderError` about "unacceptable character" or a pattern that matches nothing. Put complex patterns in `skillminer/patterns.py` and reference them from the taxonomy as `- '@patterns:<name>'`; the loader resolves the reference before compiling. Verify the file still parses after editing it, and check the pattern against known-good and known-bad strings before trusting a change.
- **Check the function list in a "collaboration" pattern for generic vocabulary.** A list containing `data`, `technical`, `ai` or `model` fires on nearly every bullet in an AI JD and inflates the skill to 100%. The list must name *organisational functions* (product team, engineering, research, design), and the pattern must require a collaboration verb nearby — not just the presence of a function word.
- **The monthly cron job REPORTS; it never fixes.** It runs the analysis, audits the evidence, and posts a short narrative. It must not edit the taxonomy, the patterns module, the gold files or the outputs — findings go to a separate maintenance pass. This is a hard rule, not a style preference: a reporting job that acts on its own findings enters a loop, because each run surfaces one more inflated skill, each fix changes the numbers, and each change justifies another report. On 2026-11-14 this happened four times in 40 minutes (taxonomy v3 → v7), re-firing the cron job after every fix. **The rule for the human/agent side: when a cron report flags a finding, batch it with every other finding, fix once, re-run the pipeline locally, and do NOT re-fire the cron job to verify.** The pipeline plus `pytest` plus the coherence check is the verification; the cron job is the deliverable, not a test.
- **When auditing for pattern inflation, audit every skill in one pass.** Flagging one skill per run guarantees a multi-round loop and leaves the numbers inconsistent between rounds. Work from the evidence file: for each canonical, read the matched bullets and ask whether each bullet actually evidences that skill. Check all skills, list all findings, then fix them in a single taxonomy revision.
- **A skill name is not the same as a skill's scope — check what the bare alternatives admit.** `model_evaluation_and_safety` matched "trust and safety" (a business domain), "validation" of configs and identities, growth "experimentation"/A-B tests, "memory safe" and "safe infrastructure". None of those are model evaluation. Real figure 43%, not the 57% the bare alternatives produced. When a skill's alternative list contains a very common word (`safety`, `validation`, `testing`, `cloud`), write the exclusion list explicitly — a negative lookahead scoped to the whole bullet — and check the surviving evidence bullets by eye. The cron job's spot-check step catches this reliably; do not skip it.
- **The same inflation pattern recurs in every skill whose name contains an adjective.** `observability_and_reliability` matched "reliable software solutions" and "reliable ML models"; `mlops_and_platform_engineering` matched "You have shipped production systems in Go". Bare `reliab` and bare `production systems` are as loose as bare `safety`. The fix is the same shape: keep a STRONG list of terms that count on their own, and admit a weak word only next to precise context ("reliability engineering", "production ML systems"). Check the surviving evidence bullets by eye after every rewrite — a JD can hold several bullets and only one of them needs to be genuine, so the per-JD count is what changes.
- **Rewrite several related skills together rather than one per cron report.** v5→v7 fixed four skills in three passes, and each pass found the same class of defect in a neighbouring skill. When a spot-check flags one, audit the others whose alternatives contain a similarly common word before re-running.
- **Distinguish "boilerplate" kinds.** Recruiting/EEO boilerplate (loader filter), Agile/process boilerplate ("collaborative software development practices"), and culture boilerplate ("A low-ego, team-first mindset") are all different and each needs its own exclusion. A culture line like "team-first" matched `cross_functional_collaboration` because it contains "team" and "engineers".

## Crawl access notes

`references/crawl-lessons.md` records the per-employer portal access patterns (Ashby vs Greenhouse field names, the portals that need API workarounds, which ones returned nothing) and the filter pitfalls found in the 2026-11 crawl. Read it before writing new crawl code — most of the hard-won knowledge there is not in the code.

## Annual trend report

Classifies every canonical skill across a year of monthly snapshots as continuous / rising / steady / emerging / new / one-off / fading. Deterministic script — run it, do not recompute the trend logic:

```bash
python3 ~/.hermes/skills/productivity/monthly-skill-mining/scripts/annual_trends.py --year 2026
python3 ~/.hermes/skills/productivity/monthly-skill-mining/scripts/annual_trends.py --year 2026 --out results/2026/skills/2026-skill-trends.json
python3 ~/.hermes/skills/productivity/monthly-skill-mining/scripts/test_annual_trends.py
```

Thresholds (top of the script): a skill is *continuous* when it appears in every month with data and never drops below `CONTINUOUS_FLOOR_PCT` (25%); *rising*/*fading* need a `CHANGE_THRESHOLD_PCT` (5) move between first and last month; *new* means it skipped early months; *one-off* means a single month. Fewer than 3 months of data is not a trend — say so.

## Outputs in `results/<month>/skills/`

- `<month>-skills-snapshot.html` — interactive report
- `<month>-skills-snapshot.json` — same data, machine-readable; two buckets (`technical`, `leadership_management`); per-skill `JD%`, `company%`, and `% Prominent` (share of prominent-company JDs only), with every matching bullet and its company
- `<month>-evidence.json` — JD bullet behind every hit
- `<month>-residue.md` — bullets that matched nothing
- `overrides.yaml` — manual exclusions (duplicates etc.)
