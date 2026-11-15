# Monthly corpus mode

Builds the month's job-description dataset for pattern analysis by the `skillminer` tool (`{data_dir}/tools/skills/`, SKILL.md there). This mode only **collects**. It never ranks for the user and never runs the analysis; the analysis is a separate step the user triggers afterwards.

Trigger: "run the monthly corpus crawl", "build this month's JD corpus", or a scheduled monthly job.

## Settings (read from `{data_dir}/EMPLOYERS.yaml`, key `monthly_corpus`)

- `max_total_jds` (30) — hard cap for the whole run. Stop crawling when reached; this is the cost limit.
- `max_per_employer` (3) — no single employer may supply more than this, so one company's boilerplate cannot dominate the patterns.
- `pool` — employer keys allowed in the corpus. **Tech-industry employers only.** Never add roles from a company outside the pool, and never take a tech role at a bank, pharma, insurer, consultancy or other non-tech firm, even if the posting looks relevant.

## Procedure

1. Month = current `YYYY-MM`. Output folder `{data_dir}/results/<YYYY-MM>/jds/` (create it). If it already has JD files from an earlier run this month, do not overwrite or mix runs — write to a suffixed folder and name the suffix in the report. (An interactive run may ask the user instead; a scheduled run has nobody to ask, so the suffixed folder is the default.)
2. Order the pool deterministically: sort employer keys by `sha1("<YYYY-MM>:<KEY>")`. This rotates which employers are reached first each month while staying reproducible. Process in that order; skip none silently.
3. For each employer, use the single-employer Procedure steps 2, 5 and 7 (find portal, collect IDs via API/curl before browser, open each candidate posting). Entries commented out in `EMPLOYERS.yaml` have unverified URLs: try them, and if blocked or empty, skip the employer and log why.
4. Candidate filter (different from the shortlist hard filters):
   - Keep: AI/ML/agentic-AI leadership roles (Engineering Manager, Senior Manager, Director, Senior Director, Head of, VP) with explicit people-management scope verified in the posting's responsibilities.
   - **Use the script, not a hand-rolled filter.** `${HERMES_SKILL_DIR}/scripts/fetch_jd.py` implements the four gates (leadership title, AI/ML signal, not a business-leadership track, people-management evidence in the body) and writes the JD file in the exact format below:
     ```bash
     # See what is available (a '+' marks a candidate that passes all four gates)
     python3 ${HERMES_SKILL_DIR}/scripts/fetch_jd.py --employer OPENAI --list

     # Write the top N as JD files
     JD_MONTH=2026-11 python3 ${HERMES_SKILL_DIR}/scripts/fetch_jd.py --employer OPENAI --pick 3 --start-row 1
     ```
     Run one `--pick` per employer, tracking the running `NN` so the numbers stay sequential across employers. `references/candidate-filter.md` holds the gate definitions, the exclusion lists, and the ATS response-field map.
   - Do not apply the Bay Area filter. The corpus is for skill patterns, not for applying. Record `work_model` and `location` in each file so the filter can be applied later.
   - Drop IC roles, non-AI roles, and duplicates (same employer, same title and team) before counting toward the caps.
   - **A leadership title is a candidate, not a match.** "Director" alone admits PR Director, Head of Corporate Development, Customer Advocacy Manager. If every employer reports zero eligible candidates, suspect the filter (a regex that fails to compile makes every lookup look empty) rather than the portals.
5. Per employer keep at most `max_per_employer` roles: take the highest-scoring by `scoring-rubric.md`. Stop the whole crawl at `max_total_jds`.
6. Write one file per kept role (format below). Never write a file from a listing page or from memory; only from the opened posting.
7. Write `{data_dir}/results/<YYYY-MM>/corpus-manifest.json`: `month`, `date`, `max_total_jds`, `max_per_employer`, `employer_order`, and per employer `{attempted, candidates_found, kept, skipped_reason}`, plus `total_kept`. State plainly any shortfall (fewer than 30) and why.
8. Report to the user: counts, employers skipped, and the next step (below). Do not run the analysis yourself.

## JD file format

Path: `results/<YYYY-MM>/jds/NN-{company-slug}-{title-slug}.md`, `NN` = two-digit running number (01, 02, ...). The analyzer parses this by script, so follow the shape exactly:

```
---
row: 1
company: Capital One
title: "Senior Director, AI Engineering — Agentic AI Platform"
source_url: "https://..."
fetched_url: "https://..."
fetched_at: 2026-10-09
status: ok              # "partial" if the full posting could not be read
work_model: hybrid
location: "San Jose, CA"
comp: "..."             # as stated in the posting, or "not stated"
team_scope: "..."
responsibilities:
  - "one bullet per responsibility, verbatim from the posting"
qualifications:
  - "one bullet per qualification, verbatim; keep the 'Preferred:' prefix"
raw_excerpt: |
  ...
---
```

Rules: double-quote every string value and bullet (colons break YAML), indent bullets two spaces, close the front matter with `---`. `company` is the plain employer name (e.g. `Google`, not `Google Cloud — Vertex`). Copy bullets verbatim; the analyzer matches on the exact text and keeps it as evidence. A file with no responsibilities and no qualifications makes the analyzer stop with an error.

**Slug collisions:** truncate the title slug but append a short hash of the full title when you do. Two roles at one employer with long similar titles otherwise reduce to the same slug, and the second file silently overwrites the first — a JD lost with no error anywhere.

**Row numbers must be unique across the whole month, not just within one employer.** The loader derives a JD's id from the filename prefix (`NN`), and the analysis report keys `excluded_jds` and per-skill `jd_ids` on that id. When a month's JDs are produced by several parallel workers that each start numbering at `01`, two different JDs share an id: the exclusion list then drops both, and `jd_ids` in the snapshot points at the wrong file. Give each worker a disjoint row range (e.g. worker A starts at `01`, worker B at `21`, worker C at `41`) or renumber the finished set before analysis. Check with:

```bash
cd results/<month>/jds && for f in *.md; do echo "$(echo "$f" | cut -d- -f1) $f"; done \
  | sort | awk '{c[$1]=c[$1]" "$2} END {for (k in c) {n=split(c[k],a," "); if (n>1) print k":"c[k]}}'
```

**Verify every written JD loads before finishing.** The analyzer raises on a file whose front matter yields no bullets, so a malformed file fails the whole month rather than one row. Load them all with the project's own venv:

```bash
~/Documents/jobsearch/tools/skills/.venv/bin/python -c "
import sys; sys.path.insert(0, '~/Documents/jobsearch/tools/skills')
from pathlib import Path
from skillminer.jd import load_all
print(len(load_all(Path('~/Documents/jobsearch/results/<month>/jds'))), 'JDs loaded')
"
```

## After the crawl (the user's next step)

The analysis belongs to the `monthly-skill-mining` skill. Run it through the project's wrapper so the right interpreter is used — never a bare `python -m skillminer`:

```bash
"{data_dir}/tools/skills/run.sh" run  --month <YYYY-MM>
"{data_dir}/tools/skills/run.sh" gold --month <YYYY-MM> --detail
```

Then classify new companies in `companies.yaml` and open `results/<month>/skills/<month>-skills-snapshot.html`.

Both steps are automated by cron (Monthly Skill Mining Analysis, 4am on the 6th), so a manual crawl is normally just the first half of a cycle that finishes itself.
