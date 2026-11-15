# Monthly corpus crawl — access patterns and pitfalls

Learned from the 2026-11 crawl. Verify each portal still works before trusting it.

## Employer portal access (2026-11)

| Employer | How to reach postings |
|---|---|
| OPENAI | Ashby: `https://api.ashbyhq.com/posting-api/job-board/openai` — field is `descriptionHtml` |
| ANTHROPIC | Greenhouse: `https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true` |
| CURSOR | Ashby `jobs.ashbyhq.com/cursor` — but `jobUrl` values 404; post at `cursor.com/careers/<slug>` |
| GLEAN | Greenhouse board token is `gleanwork`, not `glean` |
| COHERE | Ashby `posting-api/job-board/cohere` |
| PERPLEXITY | Ashby `posting-api/job-board/perplexity` (perplexity.ai/careers blocks scripts — use the Ashby board) |
| SCALE_AI | Greenhouse `boards/scaleai` |
| ELEVENLABS | Ashby `posting-api/job-board/elevenlabs` |
| STRIPE | Greenhouse `boards/stripe`; post at `stripe.com/jobs/search?gh_jid=<id>` (the /jobs page is a Next.js app with no server-rendered jobs) |
| SNOWFLAKE | Ashby `posting-api/job-board/snowflake` — NOT the Phenom portal at careers.snowflake.com |
| MISTRAL | Ashby `posting-api/job-board/mistral.ai` — note the `.ai` suffix |
| DATADOG | Greenhouse `boards/datadog` |
| DATABRICKS | Greenhouse `boards/databricks` |
| XAI | Greenhouse `boards/xai` |
| NVIDIA | Workday CXS endpoint is decommissioned (303 → community.workday.com/maintenance-page). Now `jobs.nvidia.com` (Eightfold); post bodies are in JSON-LD `JobPosting` schema |
| UBER | `jobs.uber.com` is Oracle HCM, Cloudflare-blocked to curl. Post bodies via the Oracle REST API `recruitingCEJobRequisitionDetails?finder=ById;Id="<id>"` on `iaziqy.fa.ocs.oraclecloud.com` |
| AIRBNB | FacetWP listing at `/positions/page/N/` — 22 pages, ~212 postings. The main careers page renders no job data |
| GOOGLE | `careers.google.com/jobs/sitemap` → 3,276 postings; fetch each leadership posting. The results page only shows EEO boilerplate links |
| META | `metacareers.com/jobsearch` returns HTTP 400 to curl; fetch job-detail pages individually via web_extract |
| APPLE | Hydration JSON on the search page; postings never state a work model (assume hybrid) |
| MICROSOFT | `jobs.careers.microsoft.com/api/apply/v2/jobs` returns the SPA shell — useless. Working path: `https://apply.careers.microsoft.com/careers/sitemap.xml` (2465 job URLs) then `https://apply.careers.microsoft.com/api/apply/v2/jobs/{id}?domain=microsoft.com` for the posting body |
| NETFLIX | `https://explore.jobs.netflix.net/api/apply/v2/jobs?query=...` to search, `.../jobs/{id}` for the body. Both are Eightfold. `location` is "Remote, United States" and `work_model` is `remote` — the posting body says "managing a hybrid team", which describes a geographically split team, NOT the work model |
| PALANTIR | `palantir.com/api/lever/v1/postings` — 302 postings, no AI-leadership roles in 2026-11 |

## Pitfalls

- **Ashby vs Greenhouse field names.** Ashby uses `descriptionHtml` / `descriptionPlain`; Greenhouse uses `content`. Getting this wrong silently yields an empty body for every job, which then fails any content-based filter.
- **Row-prefix collisions.** Parallel crawl workers each start at 01 → the analyzer derives the JD id from the filename prefix, so `04-stripe-*` and `04-scale-ai-*` both become id `04`, and `overrides.yaml` keyed by row-id drops the wrong files. Always run `renumber_jds.py` after the crawl, before analysis.
- **The same posting fetched twice.** Two workers (or one worker retrying after a partial run) can write the same `source_url` into different row blocks. The analyzer counts that as two distinct JDs and double-counts every skill in the posting. `renumber_jds.py` dedupes by `source_url` automatically — run it last, after all workers have finished.
- **Bullet length caps drop real requirements.** A 442-char Microsoft qualification and a 537-char customer-problem bullet were both silently dropped by a 400-char cap. Raise the cap to ~600 and re-check for boilerplate rather than trusting the shorter cap.
- **`work_model` is not the same as the team description.** Netflix postings say "managing a hybrid team" while the role is fully remote. Do not copy "hybrid" from a body phrase — read the posting's own remote/onsite statement.
- **Generous "management" evidence.** Bare `manager` in a posting body matches everything (boilerplate, titles). Require team/report/mentor/hiring language.
- **Title-level false positives.** `NOT_LEADERSHIP` must catch `architect(ure)`, `strategy & operations`, not just `architect`. Sales/customer-success/regional tracks (`ai deployment manager`, `ai success manager`, `regional director`, `head of <region>`) are not org leadership.
- **AI signal must be required**, not a bonus. A bare `Director` title matches PR Director, Head of Corporate Development, Director of Litigation.
- **Greenhouse bodies are HTML-escaped** — unescape before parsing or tags leak into bullets.
- **Section headings vary.** "You will:", "In this role, you will:", "You'll Thrive in This Role If You" all need recognising, or bullets land in the wrong list or become placeholders.

## Employer pool coverage (2026-11)

Yielded 3 eligible JDs each: Airbnb, Anthropic, Apple, Cursor, Glean, Google, Meta, NVIDIA, Perplexity, Scale AI, Snowflake, Stripe, Uber, Amazon, OpenAI.
Yielded fewer: Cohere (1).
Yielded none: Palantir, xAI, ElevenLabs (no AI-leadership postings at all in 2026-11).
