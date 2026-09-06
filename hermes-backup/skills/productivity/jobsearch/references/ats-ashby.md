# Ashby ATS — Known Patterns

## Quick Reference

Ashby job boards render entirely client-side (SPA). The page HTML returned by `curl` or fetch will be nearly empty — just a root div and JavaScript bundle references. Individual job detail pages also use SPA routing (`/openai/<uuid>`), so curl returns empty HTML too.

## Collections: Use the API endpoint

**Endpoint pattern:** `https://api.ashbyhq.com/posting-api/job-board/<employer-slug>`

**Example (OpenAI):**
```bash
curl -s --max-time 15 'https://api.ashbyhq.com/posting-api/job-board/openai'
```

**Response shape (JSON) — two valid variants exist:**
```json
// Variant A — some employers (e.g. OpenAI):
{
  "postings": [
    {
      "uuid": "cb050c48-2e42-4dc0-8860-e6b3e5e6baff",
      "title": "Online Data Systems",
      "location": { "name": "San Francisco" },
      "department": { "name": "Applied AI" },
      "employmentType": "Full-time",
      "updatedAt": "2026-07-08T..."
    }
  ],
  "meta": { "total": 728 }
}

// Variant B — other employers (e.g. ElevenLabs, Cohere):
{
  "jobs": [
    {
      "id": "02762c18-304f-4759-a34e-a26976567dcc",
      "title": "Forward Deployed Engineer",
      "location": "San Francisco",
      "department": "Engineering & Product",
      "employmentType": "FullTime",
      "updatedAt": "2026-07-09T..."
    }
  ]
}
```

**Both are valid Ashby responses.** Different employers get different root keys (`postings` vs `jobs`) and slightly different internal field names. Always check which variant the API returns before piping to jq — adjust your jq path accordingly (`.postings[]` vs `.jobs[]`). Job ID field also varies: `uuid` (Variant A) or raw `id` string (Variant B). Use `jq 'keys'` on the root object to determine the variant before filtering.

- `uuid` maps to the job detail URL: `https://jobs.ashbyhq.com/<employer>/<uuid>`
- `department.name` is useful for filtering but **do not trust it for hard filters** — some EM/Director roles live in unexpected departments (e.g. Security, Infrastructure)
- `employmentType` is usually "Full-time" for all technical roles — not a discriminator

**CORS:** The API is blocked from browser JavaScript contexts (CORS). Do not attempt `fetch()` from the browser console or browser tool's JS context — it will fail. Use `curl` in terminal instead.

## Individual job detail: Use browser

Job detail pages (`https://jobs.ashbyhq.com/<employer>/<uuid>`) render correctly in a browser — the description content, responsibilities, and team scope are present in the rendered DOM. Use `browser_navigate` + `browser_snapshot` or `browser_console` to read them.

**Tip:** `browser_console(expression="document.querySelector('[data-testid=\"job-description\"]')?.innerText || document.body.innerText")` is a reliable way to extract the full description text from Ashby job pages.

## Filtering strategy

1. Fetch all listings via API (`curl`) — this gives you the complete list with UUIDs, titles, departments, locations.
2. Filter client-side in Python or terminal using the JSON — no need to browse the job board UI.
3. Navigate only the shortlisted UUIDs in the browser for per-posting scope verification (step 7 of the procedure).

### Terminal filtering with jq

**First, detect which response variant you're dealing with:**
```bash
curl -s --max-time 15 'https://api.ashbyhq.com/posting-api/job-board/<slug>' | jq 'keys'
```
- If output includes `"postings"` → Variant A (use `.postings[]`, field `uuid`)
- If output includes `"jobs"` → Variant B (use `.jobs[]`, field `id`)

```bash
# Variant A filters (postings key, uuid field):
curl -s --max-time 15 'https://api.ashbyhq.com/posting-api/job-board/<slug>' \
  | jq '.postings[] | select(.title | test("EM|Manager|Director|Head"; "i"))
         | { id: .uuid, title: .title, dept: .department.name, loc: .location.name }'

# Variant B filters (jobs key, id field):
curl -s --max-time 15 'https://api.ashbyhq.com/posting-api/job-board/<slug>' \
  | jq '.jobs[] | select(.title | test("EM|Manager|Director|Head"; "i"))
         | { id: .id, title: .title, dept: .department, loc: .location }'

# Count total matching roles (adjust key path per variant):
curl -s --max-time 15 'https://api.ashbyhq.com/posting-api/job-board/<slug>' \
  | jq '[.jobs[] | select(.title | test("EM|Manager|Director|Head"; "i"))] | length'
```

### Extracting job descriptions in browser

Ashby job detail pages (e.g. `https://jobs.ashbyhq.com/<employer>/<uuid>`) require JS to render. Use:

```
browser_console(expression="document.querySelector('[data-testid=\"job-description\"]')?.innerText || document.body.innerText")
```

This is more reliable than `browser_snapshot` for long job descriptions on Ashby pages.

## Employer slugs

The employer slug in the Ashby URL is not always the company name verbatim. For example:
- OpenAI → `openai` (direct)
- Anthropic → check the actual URL from `EMPLOYERS.yaml`

If unsure, navigate to `https://jobs.ashbyhq.com/` and look for the employer name in the dropdown or URL.

## False positives to watch for

Ashby titles can be misleading:
- "Engineering Manager, MLE" at OpenAI (Integrity team) → actually an IC MLE role. No management scope in the description.
- "IC Agentic Engineering Manager" → despite "IC" prefix, explicitly says "leading a small team." Treat as management-scoped.

Always verify from the **responsibilities section**, not the title.

## Known Ashby employers

| Employer | Slug | Variant | Confirmation |
|---|---|---|---|
| OpenAI | `openai` | A (`postings`, `uuid`) | Confirmed |
| ElevenLabs | `elevenlabs` | B (`jobs`, `id`) | Confirmed 2026-07-13 — 183 jobs |
| Cohere | `cohere` | B (`jobs`, `id`) | Confirmed 2026-07-13 — 130 jobs |
| Perplexity | `perplexity` | A (`postings`, `uuid`) | Confirmed 2026-07-13 — 81 jobs |
| Cursor | `cursor` | B (`jobs`, `id`) | Confirmed 2026-07-13 — Ashby-hosted board |
| Scale AI | — | Greenhouse | Not Ashby — Greenhouse `boards.greenhouse.io/scaleai` |
| Intercept | `intercept` | ? | Not yet verified |

**To test a new employer:** `curl -s --max-time 10 'https://api.ashbyhq.com/posting-api/job-board/<slug>'` — if it returns JSON with a `postings` or `jobs` array, it's Ashby. Then check `jq 'keys'` on the root to determine the variant.

## Perplexity exception

`perplexity.ai/careers` blocks scripted requests (403). Always use the Ashby-hosted board as the primary URL: `https://jobs.ashbyhq.com/perplexity`
