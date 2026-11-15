# Scheduled pipeline

Three cron jobs run the monthly AI-leadership skill analysis end to end. This file holds the job-level detail; `SKILL.md` holds the rules.

## The jobs

| Job | id | Schedule (PT) | Skill | Workdir | Delivers to |
|---|---|---|---|---|---|
| Monthly Job Corpus Crawl | `b72ae4006bc3` | `0 2 2 * *` (2am, 2nd) | `jobsearch` | `~/Documents/jobsearch` | `telegram:-5179227170` |
| Monthly Skill Mining Analysis | `43ae1fd410f5` | `0 4 6 * *` (4am, 6th) | `monthly-skill-mining` | `~/Documents/jobsearch/tools/skills` | `telegram:-5179227170` |
| Annual Skill Trend Report | `23722d31b53b` | `0 5 5 1 *` (5am, 5 Jan) | `monthly-skill-mining` | — | `telegram:-5179227170` |

All three set `timezone: America/Los_Angeles` and `catch_up: true` so a machine that was off still fires on return.

`telegram:-5179227170` is the "Job Search" group. The id is stored WITHOUT the `-100` supergroup prefix; a wrong prefix produces "Chat not found".

## Why these schedules

- **Crawl on the 2nd.** Postings are freshest early in the month, so a crawl later in the month sees roles already aged and possibly filled.
- **Analysis on the 6th.** The four-day gap lets the crawl finish before the analysis reads its output. The two jobs are deliberately NOT chained with `context_from`: if the crawl fails, the analysis reports "no corpus for <month>" and waits, instead of analysing a half-written month.
- **Annual on 5 January.** Runs after December's monthly analysis has landed, so the year is complete.

## Writing the prompts

A cron prompt runs in a fresh session with no chat history, so it must be self-contained: state the paths, the commands, the deliverable shape, and the failure behaviour. Every branch the procedure needs must be pre-resolved, because there is nobody present to answer a question.

Each prompt covers, in order:
1. **Setup** — the skill to load, the absolute paths, the wrapper to call, and how the month is derived (never hardcoded).
2. **Steps** — numbered, each with the exact command.
3. **Failure behaviour** — what to report when input is missing, without fabricating a result.
4. **Deliverable** — the exact shape of the Telegram message, with a line cap.

The analysis prompt also carries two reporting rules that keep the output honest:
- Auto-tier unclassified companies into `companies.yaml` using the rubric at the top of that file, with `confidence: low` on borderline calls, then re-run so `% Prominent` reflects them.
- Diff against the prior month's snapshot JSON on `by_bucket.*.jd_pct` and report RISING (≥3 points up), FADING (≥3 points down), and NEW canonicals.

The annual prompt adds two guards: refuse to report a trend on fewer than 3 months of data, and flag any month with under 15 JDs as a low-sample caveat.

## Changing a schedule

```bash
hermes cron list
hermes cron edit <job_id>
```

Edit in place — do not delete and recreate, or the run history is lost. After any change, confirm with `hermes cron list` that `next_run_at` moved to the intended instant.

## Testing a change

`action=run` fires a job immediately in the background; the result re-enters the conversation as a new message when it finishes. Do not poll for it.

Test the analysis job against a month that already has JDs on disk (e.g. `2026-10`) to exercise the run, tier, gold and diff paths without waiting for a fresh crawl. That path is read-mostly apart from writing into `results/<month>/skills/`.

## Known gap

Nine pool employers in `EMPLOYERS.yaml` are commented out with unverified URLs (Amazon, Apple, Meta, Microsoft, NVIDIA, Stripe, Datadog, xAI, Mistral). The crawl tries them and skips any that are blocked, logging why — so early months will likely fall short of the 30-JD cap. Verify those portals and uncomment them to lift the cap.
