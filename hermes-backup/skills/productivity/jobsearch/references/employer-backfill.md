# Employer Backfill Tracker

Track which employers in `EMPLOYERS.yaml` still need structured API fields added. Updated whenever a new employer is verified and added.

## Status (as of 2026-07-13)

All frontier_ai employers with known ATS integrations are now fully structured.

### Ashby employers — verified ✅

| Employer | Slug | Variant | Structured in YAML? | Job count |
|---|---|---|---|---|
| OpenAI | `openai` | A (`postings`, `uuid`) | ✅ Yes | 728 |
| ElevenLabs | `elevenlabs` | B (`jobs`, `id`) | ✅ Yes | 183 |
| Cohere | `cohere` | B (`jobs`, `id`) | ✅ Yes | 130 |
| Perplexity | `perplexity` | A (`postings`, `uuid`) | ✅ Yes | 81 |
| Cursor | `cursor` | B (`jobs`, `id`) | ✅ Yes | confirmed |

### Greenhouse employers — verified ✅

| Employer | Slug | Structured in YAML? | Job count |
|---|---|---|---|
| Anthropic | `anthropic` | ✅ Yes | confirmed |
| Glean | `gleanwork` | ✅ Yes | 132 |
| Scale AI | `scaleai` | ✅ Yes | 183 |

### Custom / proprietary web component — confirmed blocked ❌

| Employer | Discovery date | Notes |
|---|---|---|
| Moveworks | 2026-07-14 | Custom JS web component; Greenhouse/Ashby/Lever all 404; acquired by ServiceNow; no API path found |

### Not yet verified

| Employer | ATS | Status |
|---|---|---|
| Intercept | Ashby? | Needs verification |
| Runway | Ashby? | Needs verification |
| Together AI | Greenhouse | Needs verification |

## Verified 2026-11-14 — corpus-crawl employers with no YAML entry

These employers are in `monthly_corpus.pool` but had no `api_endpoint` in
`EMPLOYERS.yaml`, so `fetch_jd.py` could not reach them. All three were
confirmed reachable this crawl and belong in the YAML.

| Employer | Access method | Confirmed |
|---|---|---|
| Stripe | Greenhouse board `stripe` | `https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true` → 786 jobs. `stripe.com/jobs` itself is a Next.js app that renders no job data to `curl`; the board API is the way in. Public posting URL is `https://stripe.com/jobs/search?gh_jid=<greenhouseId>` — note the `gh_jid` query param, not a path. |
| Amazon | Custom JSON search endpoint | `https://www.amazon.jobs/en/search.json?base_query=<terms>&loc_query=&offset=0&result_limit=100&sort=relevant`. `base_query` is the working param — plain `q=` is ignored and silently returns an unfiltered default set, so a filter built on `q` matches nothing. Each job record carries `basic_qualifications`, `preferred_qualifications` and `description` inline, but the posting page (`https://www.amazon.jobs/en/jobs/<id>/<slug>`) is the citable source and holds the base-salary ranges. |
| Airbnb | WordPress + FacetWP | `https://careers.airbnb.com/positions` is the listing; it paginates at `https://careers.airbnb.com/positions/page/<N>/` (10 per page, ~22 pages). `curl` the landing page `https://careers.airbnb.com/` and you get only nav links — no job data. The posting body lives in `<div class="job-detail active">`, the pay range in `<div class="pay-range">`, and section headings are `<p><strong>Heading:</strong></p>` followed by `<ul><li>` bullets. |

Suggested `EMPLOYERS.yaml` entries (these URLs were confirmed working on
2026-11-14):

```yaml
    STRIPE:
      url: https://stripe.com/jobs/search
      api_endpoint: https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true
      job_id_url_pattern: "https://stripe.com/jobs/search?gh_jid={id}"
```

Amazon's `search.json` is not a plain listing endpoint, so it does not fit the
`api_endpoint` contract in `fetch_jd.py` (one JSON body, one job per record).
Either extend the script with an Amazon-specific collector or leave Amazon to
a per-employer scrape.

## Verified 2026-11-14 — employers needing a per-employer collector

Neither has a listing endpoint that fits the `api_endpoint` contract, and each
needed a hand-written collector. Both were confirmed reachable this crawl.

| Employer | Access method | Notes |
|---|---|---|
| Apple | Server-rendered hydration JSON | `POST https://jobs.apple.com/api/v1/search` returns `{"res":{"searchResults":[],"totalRecords":0}}` for every body shape — it needs a live session. `GET https://jobs.apple.com/api/v1/CSRFToken` returns empty and `/api/v1/search` without `Content-Type: application/json` returns HTTP 436 `jobsite.general.serviceError`. **Do not use the JSON API.** The listing works as plain HTML: `GET https://jobs.apple.com/en-us/search?search=<term>&sort=relevance&location=united-states-USA` and read `window.__staticRouterHydrationData = JSON.parse("...")` → `loaderData.search.searchResults[]` (`postingTitle`, `positionId`, `reqId`, `transformedPostingTitle`, `team.teamCode`, `locations`). Two details that matter: **`sort=relevance` is required** (without it the page sorts by newest and the term is ignored), and **quoted phrases work** — `search="machine learning" manager` returns 3 targeted hits while the bare term returns thousands. The posting page `https://jobs.apple.com/en-us/details/<reqId>/<transformedPostingTitle>?team=<teamCode>` embeds the whole JD in the same hydration blob under `loaderData.jobDetails.jobsData` → `description`, `responsibilities`, `minimumQualifications`, `preferredQualifications`, plus `postingFooters` (the base-pay range). `localizations.en_US.posting.*` holds the section bodies; the top-level keys are the same values. There is no `raw_excerpt` to lose — the footer legal text is separate from the JD sections. |
| Cursor | Ashby API + live posting pages | The Ashby board `https://api.ashbyhq.com/posting-api/job-board/cursor` works (99 jobs) but **the `jobUrl` values 404** — `jobs.ashbyhq.com/cursor/<uuid>` returns a 404 shell. The live postings are on `https://cursor.com/careers/<title-slug>` (slug = title lowercased, non-alphanumerics to `-`); the Ashby `descriptionHtml` still carries the full body, and the cursor.com page embeds the same HTML plus the job id. `fetch_jd.py`'s hard filter rejects all 99 Cursor postings — the board's leadership roles sit under customer-facing titles ("Regional Director, AI Deployment", "AI Deployment Manager") that the `NOT_ORG_LEADERSHIP` / `NOT_AI` patterns exclude, even though the postings carry real people-management scope ("hire, lead, and develop a team of AI Deployment", "lead, develop, and scale a team of 6-8 Forward Deployed Engineers"). Cursor needs a hand-written collector that bypasses the title filter for postings whose body has management evidence. |

Note on the Cursor board: as of 2026-11-14 the postings describe SpaceXSI / Grok
work (Grok, Grok Build, Colossus) even though they are hosted on Cursor's board
and its `cursor.com/careers` pages. Write the file with `company: "Cursor"` —
the board, URL and job ids are Cursor's.

## How to verify a new employer

1. Try the Ashby API: `curl -s --max-time 10 'https://api.ashbyhq.com/posting-api/job-board/<slug>'`
2. Try the Greenhouse API: `curl -s --max-time 10 'https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true'`
3. If either returns JSON, note the variant (A or B for Ashby) and update this file and `EMPLOYERS.yaml`
4. If neither works, fall back to browser-based collection
5. If the ATS endpoint works but the public posting URL 404s (Cursor), check whether the company has its own careers site — the posting body may only be reachable there.
