---
title: Web-sweep mode
---

# Web-sweep mode

Open-web search across many companies for a *title family* the user names (no specific employer), producing a wide-but-shallow list that the user manually trims before any deeper work. This is one of the five modes of the `jobsearch` skill.

## Trigger

The user asks for something like:
- "Search online for job postings for titles like Director of AI Engineering, or Senior Manager of Agentic AI from known companies."
- "Find Senior Manager roles in [domain] across [industry]."
- "List [title family] at FAANG / unicorns / [bucket]."

If the user names a single employer, you are in run mode — go there instead. If the user wants the monthly corpus (JDs from `monthly_corpus.pool`), go there. Web-sweep is for *no specific employer named, but a title family the user is exploring*.

## Output

A markdown table with one row per role and these columns:

| # | Company | Title | Location | Comp (if shown) | Source |
|---|---|---|---|---|---|

Plus:
- A **"Curated highlights"** block (3–8 strong-fit rows) above the table.
- A **"Notes"** block at the bottom describing what was excluded and why (consulting/staffing agencies, generic "Area Director" / non-engineering noise, etc.).

File path: `{data_dir}/results/<YYYY-MM>/<YYYY-MM-DD>-web-sweep-<title-slug>.md`

The "manual review" half of the workflow is the point — the user trims this file, and only the keepers go on to JD fetches. Do not score, do not rank, do not run any of the per-role scoring rubric. Wide then narrow.

## Procedure

1. **Pick 4–6 web search queries that fan out by title family.** The user's phrasing is usually one example title; the fan-out covers synonyms and adjacent families. Example for "Director of AI Engineering, Sr. Manager of Agentic AI":
   - `"Director of AI Engineering" job 2026 site:linkedin.com`
   - `"Senior Manager, Agentic AI" OR "Sr Manager Agentic AI" job 2026`
   - `"Director of Agentic AI" OR "Director, Agentic AI Engineering" job`
   - `"Senior Manager" "AI Engineering" "LLM" OR "agentic" job San Francisco Bay Area`
   - `"Head of AI" OR "Head of Applied AI" job 2026 agentic enterprise`

   Run them in parallel. Pick the queries that return the most distinct known companies, not the highest volume.

2. **Triage: keep, drop.** The 30–50-row output needs cleaning before storage. Drop:
   - **Consulting / staffing / generic postings** (Robert Half, Insight Global, "AI Engineer – Remote – $80/hr").
   - **Cross-industry noise** (Sevita, hospitality, finance, pharma, insurers) — unless the user explicitly widened to those.
   - **Non-engineering functions** even if the title contains "AI" (e.g. "Product Marketing Senior Manager, AI Platform" — drop, the user is looking for engineering leadership).
   - **"Area Director" / "Director of Finance" / etc.** that surfaced from too-loose title matches.

   Keep: roles where the title explicitly says "Engineering", "AI/ML Engineering", "Agentic AI", "LLM Platform", or "Applied AI" AND the company is a known tech employer (FAANG-tier, unicorn, mid-large public tech, well-funded startup).

3. **Dedupe across queries.** A Capital One Sr. Director AI role can surface in 3 different searches. Keep the canonical row once.

4. **Write the file.** Sort by company name (or known-company priority + then alpha). Number rows 1..N. Curated highlights above the table — pick the 3–8 strongest fits to the user's stated focus. Notes block at the bottom.

5. **Tell the user what to do next.** "I'm going to manually review and keep the ones I like" is the user's standing pattern. Do not auto-fetch JDs for all rows. Wait for them to say which to keep.

## Known anti-scrape sources and workarounds

| Source | Behavior | Workaround |
|---|---|---|
| `linkedin.com/jobs/view/...` | 403 from both `curl` and `web_extract`; full anti-bot WAF | Derive the canonical source: company careers site, Greenhouse / Lever / Ashby board at the same job id, or a LinkedIn mirror (`trabajo.org/job-<id>`, `us.trabajo.org/...`). State the redirect in `fetched_url`. |
| `themuse.com/jobs/...` | Returns content for most roles; some are stale (closed) | Acceptable as-is. If the role is stale, web_search for the company's own posting URL. |
| `jobleads.com/...` | Often blocked, sometimes returns a 3-word stub | Try the company's own careers URL first; if that fails, web_search by title. |
| `builtinnyc.com / builtinsf.com / built in boston` | Sometimes the post is already removed (date posted > 30 days) | The JD body is often preserved in the initial web_extract snapshot — write it to the JD file with `status: partial` and a note that the source was removed. |
| `experteer.com/...` | Often returns 404 / dead; the underlying iCIMS requisition is the real source | Search the company careers site for the iCIMS requisition id from the URL. |
| `milwaukeejobs.com / jobleads / similar aggregators` | Low-quality, often stale | Replace with the canonical source URL when possible. |

The high-success pattern: when the source is blocked, **the company's own careers page almost always has the same role**, and the JD id often matches across aggregator and canonical URLs. Search by job id first.

## Post-sweep: the user's edit pass

The user will manually drop rows and ask for further work. The two next steps are:
- **JD fetch** for the keepers — see the SKILL.md main procedure; the 5-subagent fan-out works well for batches of ~25 JDs.
- **Skill extraction** — `monthly-skill-mining` skill, which runs `run.sh` against the JDs the user kept.

Always wait for the user to say which rows to keep. Do not auto-advance.

## Pitfalls

- **Do not score sweep results.** Scoring is for run mode. Sweep = wide filter, run = narrow filter, the two are different shapes.
- **Do not over-prune during triage.** When in doubt, keep the row and let the user decide. Drop only obvious noise (consulting, non-engineering, wrong industry).
- **One row per real role.** Capital One Sr. Director + Capital One Sr. Manager (different titles) is two rows. Capital One Sr. Director surfaced from two queries is one row.
- **The "Source" column is the user's audit trail.** Don't link to a dead URL when a working canonical exists; don't fabricate.
- **The "Curated highlights" block is opinionated, but the labels are the user's standing focus** (Bay Area EM/Director, agentic AI / LLM platform). Don't invent signals not in the row.
