# Monthly corpus mode

Builds the month's job-description dataset for pattern analysis by the `skillminer` tool (`{data_dir}/tools/skills/`, SKILL.md there). This mode only **collects**. It never ranks for the user and never runs the analysis; the analysis is a separate step the user triggers afterwards.

Trigger: "run the monthly corpus crawl", "build this month's JD corpus", or a scheduled monthly job.

## Settings (read from `{data_dir}/EMPLOYERS.yaml`, key `monthly_corpus`)

- `max_total_jds` (30) — hard cap for the whole run. Stop crawling when reached; this is the cost limit.
- `max_per_employer` (3) — no single employer may supply more than this, so one company's boilerplate cannot dominate the patterns.
- `pool` — employer keys allowed in the corpus. **Tech-industry employers only.** Never add roles from a company outside the pool, and never take a tech role at a bank, pharma, insurer, consultancy or other non-tech firm, even if the posting looks relevant.

## Procedure

1. Month = current `YYYY-MM`. Output folder `{data_dir}/results/<YYYY-MM>/jds/` (create it). If it already has JD files, ask before overwriting; never mix runs.
2. Order the pool deterministically: sort employer keys by `sha1("<YYYY-MM>:<KEY>")`. This rotates which employers are reached first each month while staying reproducible. Process in that order; skip none silently.
3. For each employer, use the single-employer Procedure steps 2, 5 and 7 (find portal, collect IDs via API/curl before browser, open each candidate posting). Entries commented out in `EMPLOYERS.yaml` have unverified URLs: try them, and if blocked or empty, skip the employer and log why.
4. Candidate filter (different from the shortlist hard filters):
   - Keep: AI/ML/agentic-AI leadership roles (Engineering Manager, Senior Manager, Director, Senior Director, Head of, VP) with explicit people-management scope verified in the posting's responsibilities.
   - Do not apply the Bay Area filter. The corpus is for skill patterns, not for applying. Record `work_model` and `location` in each file so the filter can be applied later.
   - Drop IC roles, non-AI roles, and duplicates (same employer, same title and team) before counting toward the caps.
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

## After the crawl (the user's next step)

Run the `skillminer` workflow in `{data_dir}/tools/skills/SKILL.md`: `python -m skillminer run --month <YYYY-MM>`, then classify new companies in `companies.yaml`, then open `results/<YYYY-MM>/skills/<YYYY-MM>-skills-snapshot.html`.
