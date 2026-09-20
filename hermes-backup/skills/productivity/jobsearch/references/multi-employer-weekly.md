# Multi-Employer Weekly Mode

Use this mode when a job (typically a scheduled cron job) asks you to process **more than one whitelisted employer** in a single run and deliver one combined report, instead of the single-employer `run mode` described in `SKILL.md`.

The base `SKILL.md` Procedure (steps 1–12), `PREFERENCES.md`, `RESUME_SUMMARY.md`, `scoring-rubric.md`, and `output-format.md` are still authoritative for hard filters, scoring, and per-role output structure. This file only adds the multi-employer loop, archiving, and combined-delivery layer on top.

## Step 1: Load context

Read `PREFERENCES.md`, `RESUME_SUMMARY.md`, `scoring-rubric.md`, and `output-format.md` in full before doing anything else — same requirement as single-employer run mode.

## Step 2: Whitelisted employers

Process **only** the employers the calling job names — never any other employer found in `EMPLOYERS.yaml`, even if it looks relevant. The calling prompt's whitelist is the boundary, not this file.

## Step 3: Process each employer

For **each** whitelisted employer, repeat steps 3a–3f below. Process employers one at a time, not interleaved.

### 3a. Collect job listings

Use `EMPLOYERS.yaml` and `SKILL.md`'s "Known ATS Patterns" table to pick the collection method (API endpoint first, then browser). Collect all job IDs before visiting any individual posting. Format each as `{id, title, department, location, url}`.

### 3b. Apply hard filters

Use `PREFERENCES.md`'s hard filters (Bay Area onsite/hybrid, confirmed people-management scope, EM/Director level — no IC-only roles). Exclude any failing role immediately.

### 3c. Score remaining roles

Score 1–100 using `scoring-rubric.md`.

### 3d. Inspect shortlisted candidates

For each role passing hard filters, open its URL and verify people-management scope, location/work model/comp, and domain signals — do not infer any of these from the title or listing alone.

### 3e. Archive per-employer results

Save to `{data_dir}/results/`:
- `YYYY-MM-DD-{employer-slug}.md` — human-readable, using `output-format.md`
- `YYYY-MM-DD-{employer-slug}.json` — machine-readable, same schema as `SKILL.md` step 12

Replace `YYYY-MM-DD` with today's date and `{employer-slug}` with the employer's lowercase slug (e.g. `moveworks`, `openai`). Overwrite existing files for the same date.

### 3f. Track aggregate stats

After each employer, record: employer name, `total_reviewed`, `total_shortlisted`, and its exclusion breakdown by reason (same buckets as `output-format.md`'s Exclusions Summary) — this per-employer breakdown is needed for step 4's delivery format, not just the combined total.

## Step 3g: Global ranking across employers

After all employers have been processed, pool every shortlisted role from every employer into a single list. Sort by score descending, ties broken by employer processing order (i.e. whichever employer was listed first in the calling prompt's whitelist). Assign each role a global rank (1 = highest score across all employers). Each role now carries two ranks: its per-employer rank (from step 3c, shown in the per-company section) and its global rank (shown in the top-picks section).

## Step 4: Deliver combined report

Send **one** message covering all whitelisted employers. Format:

```
📋 Weekly Job Shortlist — [DATE]
Reviewed N employers | [M] total shortlisted

🏆 TOP PICKS (ranked across all companies)
[GLOBAL RANK 1] [TITLE] — [EMPLOYER] — Score: XX
[GLOBAL RANK 2] [TITLE] — [EMPLOYER] — Score: XX
[GLOBAL RANK 3] [TITLE] — [EMPLOYER] — Score: XX
(List every shortlisted role here, ordered by global rank, one line each: rank, title, employer, score)

━━━ [EMPLOYER 1] ━━━
🔍 N reviewed → K shortlisted
[RANK 1] [TITLE] — Score: XX (Global #X)
• Department | Location | Work model | Comp
• Hard filters: ✅/❌ — evidence
• Why: 1-2 bullets
• Risks: 1 bullet
• Source: [URL]
[Additional shortlisted roles in brief format]

━━━ [EMPLOYER 2] ━━━
[... same structure ...]

---
Excluded — [EMPLOYER 1]: [breakdown, e.g. "no BA hybrid: 12 · IC-only: 8 · below scope: 3"]
Excluded — [EMPLOYER 2]: [breakdown]
Notes: [friction points, portal changes, observations]
```

If an employer has 0 shortlisted roles, still list it with "0 shortlisted" and its own exclusion breakdown — do not fold it silently into a combined total.

## Important

- This is a scheduled automated run — do not ask questions or request clarification.
- If any portal is unreachable, note it in that employer's section and continue — do not abort the whole run.
- Produce both `.md` and `.json` archive files for every employer, every run.
- Always deliver the message, even if every employer yields zero results.
- Never process an employer outside the calling prompt's whitelist.
