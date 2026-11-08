# Multi-Employer Weekly Mode

Use this mode when a job (typically a scheduled cron job) asks you to process **more than one whitelisted employer** in a single run and deliver one combined report, instead of the single-employer `run mode` described in `SKILL.md`.

The base `SKILL.md` Procedure (steps 1–12), `PREFERENCES.md`, `RESUME_SUMMARY.md`, `scoring-rubric.md`, and `output-format.md` are still authoritative for hard filters, scoring, and per-role output structure. This file only adds the multi-employer loop, archiving, and combined-delivery layer on top.

## Step 1: Load context

Read `PREFERENCES.md`, `RESUME_SUMMARY.md`, `scoring-rubric.md`, and `output-format.md` in full before doing anything else — same requirement as single-employer run mode.

## Step 2: Whitelisted employers

Process **only** the employers the calling job names — never any other employer found in `EMPLOYERS.yaml`, even if it looks relevant. The calling prompt's whitelist is the boundary, not this file.

The whitelist is the user's explicit statement of scope, so it is never widened on your own initiative. An uncommented `EMPLOYERS.yaml` entry means "if asked, here is how to reach this portal" — it is a lookup table, not a queue of employers to search. Two different knobs, kept separate:

- **Which employers to search** — the calling prompt's whitelist. Changed by editing the prompt.
- **How to reach an employer** — `EMPLOYERS.yaml`. Changed by editing the YAML.

When the calling prompt lists an employer with its own URL or API endpoint, use that. Fall back to `EMPLOYERS.yaml` only for details the prompt omits (ATS type, job-ID URL pattern, known portal quirks).

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

Do this **once at the end of the whole run**, not per employer — build a single payload covering every employer and let the script write all the files.

Build a payload JSON at a scratch path:

```json
{
  "date": "2026-10-30",
  "employers": [
    {
      "employer": "OpenAI",
      "slug": "openai",
      "portal": "https://jobs.ashbyhq.com/openai",
      "portal_note": "Ashby API: https://api.ashbyhq.com/posting-api/job-board/openai",
      "total_reviewed": 813,
      "roles": [
        {
          "rank": 1,
          "title": "Engineering Manager, ChatGPT Search Infrastructure",
          "score": 88,
          "department": "Applied AI",
          "location": "San Francisco",
          "work_model": "On-site (Ashby workplaceType: OnSite)",
          "comp": "$401K-$445K + equity",
          "url": "https://jobs.ashbyhq.com/openai/9d6520c0-...",
          "hard_filters_pass": true,
          "hard_filters": "\"Lead and develop a team of experienced engineers\"; San Francisco",
          "why": ["Direct RAG/retrieval overlap: indexing and retrieval, search orchestration"],
          "key_signals": ["Bay Area onsite (SF)", "People management confirmed"],
          "risks": ["On-site, not hybrid — SF commute from Santa Clara"]
        }
      ],
      "exclusions": {"IC-only, no confirmed management scope": 379},
      "notes": ["Ashby API returned 813 postings."]
    }
  ]
}
```

Then run:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/archive_verify.py archive --input <payload.json>
```

Field notes:
- `hard_filters` is **evidence text only** — do not include the ✅/❌ mark, the script adds it. This field appears in the `.md` only.
- `why` is the "Why it matches" bullet list; `key_signals` is the shorter signal list that goes into the `.json`. If `why` is omitted, `key_signals` is used for both.
- `comp` uses a plain hyphen between range endpoints (`$401K-$445K`); the script renders the en-dash form in the `.md`.
- `exclusions` **must** account for every reviewed-but-not-shortlisted role: `sum(exclusions.values()) + total_shortlisted == total_reviewed`. The verifier rejects the run otherwise.
- `portal_note` is optional and appears in the `.md` portal line only.

The script writes `<YYYY-MM-DD>-<slug>.md` and `.json` per employer plus `<YYYY-MM-DD>-weekly-report.md`, verifies everything by re-reading from disk, and prints the Telegram report between `--- BEGIN TELEGRAM MESSAGE ---` and `--- END TELEGRAM MESSAGE ---`.

### 3f. Track aggregate stats

After each employer, record: employer name, `total_reviewed`, `total_shortlisted`, and its exclusion breakdown by reason (same buckets as `output-format.md`'s Exclusions Summary) — this per-employer breakdown is needed for step 4's delivery format, not just the combined total.

## Step 3g: Global ranking across employers

After all employers have been processed, pool every shortlisted role from every employer into a single list. Sort by score descending, ties broken by employer processing order (i.e. whichever employer was listed first in the calling prompt's whitelist). Assign each role a global rank (1 = highest score across all employers). Each role now carries two ranks: its per-employer rank (from step 3c, shown in the per-company section) and its global rank (shown in the top-picks section).

## Step 4: Deliver combined report

**The script renders this for you.** `archive_verify.py archive` already emits the combined report with the global ranking and per-employer sections. Deliver the text between `--- BEGIN TELEGRAM MESSAGE ---` and `--- END TELEGRAM MESSAGE ---` **verbatim** — do not re-derive or hand-format it.

To re-render the report from files already on disk (no re-search needed):

```bash
python3 ${HERMES_SKILL_DIR}/scripts/archive_verify.py report --date YYYY-MM-DD
```

The format the script produces:

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

If an employer has 0 shortlisted roles, it is still listed with "0 shortlisted" and its own exclusion breakdown — do not fold it silently into a combined total.

## Token discipline

A scheduled multi-employer run is the most expensive job in this skill, and the cost driver is not the work — it is the number of LLM round-trips multiplied by the context size, because every round-trip re-sends the entire accumulated conversation. Minimising turns matters more than minimising bytes.

**Fold the filter/bucket logic into few script passes.** Deriving one bucket per conversational turn multiplies round-trips and grows the context each time; a run that derives every bucket in one script pass does the same work in a fraction of the turns. Write one script that reads the collected listings and emits every bucket at once, then read its output.

**Archive and deliver in one pass each.** The archive-and-verify phase is mechanical file writing — no reasoning required — but spread across per-file write/read turns it becomes the single most expensive phase in the run. One script that writes every employer's `.md` and `.json` and prints a short manifest, then one verification read, beats a write-then-read turn per file.

**Keep bulk data out of the conversation.** Raw ATS payloads run to tens of megabytes. Filter them inside a script and print only the fields the scoring needs — never read a raw payload into context, because everything in context is re-sent on every subsequent turn.

**Report cost honestly.** When reporting what a run consumed, distinguish total prompt tokens from *fresh* (uncached) prompt tokens and completion tokens. Total prompt tokens include the entire conversation re-sent on each turn and overstate the cost of new work by an order of magnitude; state both numbers and the cache hit rate.

## Important

- This is a scheduled automated run — do not ask questions or request clarification.
- If any portal is unreachable, note it in that employer's section and continue — do not abort the whole run.
- Produce both `.md` and `.json` archive files for every employer, every run.
- Always deliver the message, even if every employer yields zero results.
- Never process an employer outside the calling prompt's whitelist.
- Never expand the whitelist to "all employers in `EMPLOYERS.yaml`" — if the user wants a different scope, that is a prompt change, not a judgment call.
