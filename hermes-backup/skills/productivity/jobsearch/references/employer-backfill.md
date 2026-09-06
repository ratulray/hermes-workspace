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

## How to verify a new employer

1. Try the Ashby API: `curl -s --max-time 10 'https://api.ashbyhq.com/posting-api/job-board/<slug>'`
2. Try the Greenhouse API: `curl -s --max-time 10 'https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true'`
3. If either returns JSON, note the variant (A or B for Ashby) and update this file and `EMPLOYERS.yaml`
4. If neither works, fall back to browser-based collection
