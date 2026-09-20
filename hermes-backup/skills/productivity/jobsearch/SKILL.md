---
name: jobsearch
description: Rank live openings from a named employer's careers portal against Ratul's background and EM/Director-level job search preferences. Use when the user names a single employer and wants current openings scored and returned as a ranked shortlist.
version: 1.1.0
author: Ratul Ray
license: MIT
metadata:
  hermes:
    tags: [career, job-search, productivity]
    requires_toolsets: [browser, terminal]
    config:
      - key: jobsearch.data_dir
        description: Path to the folder containing EMPLOYERS.yaml, PREFERENCES.md, and APPLICATIONS.yaml
        default: "~/Documents/jobsearch"
        prompt: "Path to your jobsearch data directory"
---

# Match Employer Jobs

Rank a named employer's currently live openings against Ratul's background and stated job-search preferences, and return a ranked shortlist with evidence and source links.

## When to Use

This skill handles two distinct modes — **review** and **run** — triggered by different user requests:

### Review mode
The user asks you to check the skill's own configuration or files, e.g. "review the jobsearch skill", "check if the skill is set up correctly", "audit the skill". In review mode: **do not run any job search, do not browse any job postings, do not collect any data.** Only read the skill files and verify structure. Report findings without taking action on any employer.

### Run mode
The user names a single employer and asks for current openings, e.g. "Use jobsearch to check NVIDIA" or "What are the top roles at Anthropic right now?"

This skill targets **Senior Engineering Manager / Director of Engineering** roles in **Bay Area onsite or hybrid** positions — not general job search. See `PREFERENCES.md` for the full policy.

### Multi-employer mode
The user or calling job names **more than one** employer and wants one combined report across all of them, e.g. "compare Moveworks and OpenAI roles" or a scheduled multi-employer digest. This is a distinct mode from run mode — do not just repeat run mode's single-employer output once per employer. Load `references/multi-employer-weekly.md` for the loop, per-employer archiving, cross-employer ranking, and combined-delivery format; the single-employer Procedure below still applies per employer within that loop.

## Quick Reference

| File | Purpose |
|---|---|
| `{data_dir}/EMPLOYERS.yaml` | Employer key → careers portal URL(s). Entries with a known ATS API use a nested `{url, api_endpoint, job_id_url_pattern}` map; entries without one use a plain `url1 \| url2` string. |
| `{data_dir}/PREFERENCES.md` | Ratul's job-search policy and ranking bias (EM/Director, Bay Area) |
| `{data_dir}/RESUME_SUMMARY.md` | Primary background-match input — role history, scope/team-size evidence, domain signals, derived from Ratul's actual resume |
| `~/.hermes/memories/USER.md` | Secondary/general profile context (installation-managed, do not duplicate) |
| `{data_dir}/APPLICATIONS.yaml` | Optional — prior/submitted applications, for duplicate checks only |
| `{data_dir}/results/` | Shortlist archive — `YYYY-MM-DD-{employer-slug}.md` and `.json` from each run |
| `${HERMES_SKILL_DIR}/references/scoring-rubric.md` | Scoring weights and tie-breakers |
| `${HERMES_SKILL_DIR}/references/output-format.md` | Required output structure |
| `references/ats-ashby.md` | Ashby ATS patterns — two API response variants, jq filters for each |
| `references/employer-backfill.md` | Which employers in `EMPLOYERS.yaml` still need structured API fields added |

`{data_dir}` is the configured `jobsearch.data_dir` setting (see `[Skill config]` line injected when this skill loads; default `~/Documents/jobsearch`).

## Procedure

1. Normalize the employer name given by the user.
2. Read `{data_dir}/EMPLOYERS.yaml` and find the matching employer key and portal URL(s).
   - If ambiguous, resolve by exact key match first, then obvious alias match, then ask the user only if multiple plausible employers remain.
   - If the employer isn't in `EMPLOYERS.yaml`, say so and ask whether to add it or search the web for the portal directly.
3. Read `{data_dir}/PREFERENCES.md` and `{data_dir}/RESUME_SUMMARY.md` (and `~/.hermes/memories/USER.md` for any general context not captured in the resume summary).
4. Derive search terms from `PREFERENCES.md`'s "Role Families To Prioritize" and "Skill Signals To Prioritize" sections (e.g. "Engineering Manager", "Director of Engineering", "Agentic AI", "Conversational AI", "ML Platform") and from the domain/title keywords in `RESUME_SUMMARY.md`.
5. **Collect all candidate job IDs** before visiting any posting, using this priority order so the same collection isn't done twice:
   1. If `EMPLOYERS.yaml` has an `api_endpoint` for this employer, fetch it via `curl` — this returns the complete listing in one call, so no further browser-based collection is needed. See `references/ats-*.md` for the response shape and filtering examples.
   2. Otherwise, if `references/ats-*.md` recognizes the employer's ATS from its URL pattern (e.g. `job-boards.greenhouse.io/<token>`, `jobs.ashbyhq.com/<slug>`) but `EMPLOYERS.yaml` has no `api_endpoint` recorded, derive the API endpoint yourself from that ATS's documented pattern and fetch it via `curl`.
   3. Otherwise, use the **browser** tool on the portal. If it has a search or filter box, use the search terms derived in step 4 to narrow results at collection time rather than pulling every listing — search by title terms and by skill/domain terms separately, since portals often only match one field. Merge and de-duplicate the results. If there's no usable search (or it ignores query params), collect the full listing instead.
   - If the portal or API is blocked, JavaScript-heavy, or difficult to reach, state the limitation and fall back to the next option in the list above, or to the best available accessible listing/search page on the same employer's site.
   - Format each collected entry as: `{id, title, department, location, url}`. De-duplicate by ID before proceeding.
6. Filter out roles that clearly conflict with `PREFERENCES.md` (see Hard Filters below).
7. For each remaining role, use the **browser** tool to open the individual posting and check for explicit **Bay Area work model** and **people-management scope** — do not infer either from the title alone. Titles like "Engineering Manager" can still be IC roles (false positives — e.g. OpenAI's "EM, MLE" was an IC MLE role despite the EM title). Verify from the responsibilities section.
8. **Before scoring, read both reference files fully:**
   - `references/scoring-rubric.md` — the 6-category weights and tie-breakers must be applied systematically, not guessed from memory.
   - `references/output-format.md` — the output structure (header, per-role fields, exclusions summary, notes) must be followed exactly.
9. Score the remaining roles using `scoring-rubric.md`, using `RESUME_SUMMARY.md` as the primary source for the background-match and scope/seniority-fit scores.
10. Return the top 10 roles (or fewer) using `output-format.md` — follow the exact field names and bullet structure defined there. Every shortlisted role must have: score, work model, scope, why it matches (bullets), risks or gaps (bullets), source URL.
11. If `{data_dir}/APPLICATIONS.yaml` exists and has entries, flag any shortlisted role that matches a prior application.
12. **Archive the shortlist to disk.** After returning the shortlist, write two files to `{data_dir}/results/`:
    - `{YYYY-MM-DD}-{employer-slug}.md` — the full shortlist in the output-format structure, as returned to the user
    - `{YYYY-MM-DD}-{employer-slug}.json` — a machine-readable summary with these exact top-level fields:
      - `employer`, `portal`, `date`, `total_reviewed`, `total_shortlisted`
      - `roles[].rank`, `title`, `score`, `department`, `location`, `work_model`, `comp`, `url`
      - `roles[].hard_filters_pass`, `key_signals[]`, `risks[]`
      - `exclusions` (breakdown of non-shortlisted roles by reason), `notes[]`
    - Verify the `.json` is not truncated — it must contain the same `total_reviewed`, `total_shortlisted`, and all `exclusions` breakdown fields as the `.md`.
    - If the directory does not exist, create it first.
    - If a file for today's date and employer already exists, overwrite it (treat it as a fresh run, not a duplicate).

Note: search-term narrowing reduces browsing cost but is not a substitute for the hard filters in step 6 — a title match from search terms alone (e.g. "Engineering Manager") does not confirm Bay Area work model or management scope; those are still verified per-posting in step 7.

## Known ATS Patterns

Some applicant tracking systems (ATS) have specific behaviors that override the default browser-first procedure. Check this list before starting a new employer.

| ATS | Employer examples | Behavior | Recommended approach |
|---|---|---|---|
| **Ashby** | OpenAI, Intercept, Runway, and others | Job board renders client-side; direct API endpoint available but CORS-restricted from browser JS | Use `curl` to fetch `https://api.ashbyhq.com/posting-api/job-board/<employer>` for the full listings JSON. Individual job detail pages (URL: `https://jobs.ashbyhq.com/<employer>/<uuid>`) render correctly in browser — use browser for per-posting scope verification. |
| **Green House** | Many mid-size tech companies | Standard job board, usually browsable | Browser-first; no special API known. |
| **Lever** | Many startups | Standard job board; sometimes supports `/api/posts` | Browser-first; check for `/careers` or `/jobs` JSON endpoints if portal is slow. |
| **Workday** | Many enterprises | Heavily JavaScript-rendered; limited URL-based linking | Use browser. If a role detail page returns empty HTML via curl, that confirms JS rendering — do not retry with curl. |
| **Custom web component** | Moveworks (acquired by ServiceNow) | Proprietary JS component embedded in the page; no standard ATS API, no extractable DOM links, no JSON-LD schema | No API path. Check if the company was acquired — acquirer's ATS may host the roles. Otherwise state the limitation and note manual verification required. See `references/ats-custom-web-component.md`. |

If the employer uses an ATS you don't recognize: try `curl -s --max-time 15 <portal-url>` first to check if the page returns meaningful HTML. If it's empty or minimal, fall back to browser-based browsing.

If the portal is blocked, JavaScript-heavy, or difficult to browse, state the limitation and fall back to the best available accessible listing or search page on the same employer's site.

## Hard Filters

Exclude roles that clearly conflict with `PREFERENCES.md`:
- No Bay Area onsite/hybrid option (remote-only, or another region with no relocation/hybrid path)
- Individual-contributor-only roles with no people-management responsibility
- Roles clearly below current scope (first-time manager, small team, no strategic ownership) unless the user frames it as a deliberate pivot

If the portal exposes fewer than 10 roles that pass the hard filters, return the available strong matches and state the shortfall explicitly.

## Evidence Discipline

Base every recommendation on the live posting plus `RESUME_SUMMARY.md` and `PREFERENCES.md`.

Do not invent:
- Bay Area presence, hybrid schedule, or relocation support
- Management scope, team size, or reporting structure
- Compensation
- Seniority calibration beyond what the posting states

When inferring fit, label it as an inference and tie it to concrete signals from the posting and profile.

## Pitfalls

- **"Manager" in the title does not confirm people management** — titles like "Engineering Manager" can still be IC roles at some employers (e.g. OpenAI's "EM, MLE" was an IC MLE role despite the EM title). Always verify from the responsibilities section.
- **Review vs. run mode confusion** — If the user asks to "review", "check", or "audit" the skill itself, do NOT run a job search. Only read the skill files and report on their state. The default trigger ("use jobsearch to check X") is for run mode, not review mode.
- Don't treat "hybrid" as equivalent to Bay Area unless the specific office location is Bay Area.
- Don't score a role high on domain fit alone if it fails the Bay Area or management-scope hard filters.
- Don't duplicate Ratul's profile into this skill's files beyond `RESUME_SUMMARY.md` — that file is already a job-search-specific derivative of his resume; general profile facts still live in `~/.hermes/memories/USER.md`.
- If `RESUME_SUMMARY.md` and `~/.hermes/memories/USER.md` ever conflict on a fact relevant to scoring, treat `RESUME_SUMMARY.md` as authoritative — it's sourced directly from the current resume.
- **Don't score from memory** — the 6-category rubric must be read and applied before scoring begins. Scoring from general impression produces inconsistent results.
- **Don't skip the output format** — the shortlist must follow `output-format.md`'s exact field names and bullet structure. Write to the format, not around it.
- **Don't confuse page-level Work Personas language with role-specific work model requirements.** Some employers (notably ServiceNow/Moveworks) publish generic "Work Personas" boilerplate at the page or footer level listing "flexible, remote, or required in office" as categories that apply across the org. This is NOT authoritative for any individual role. Always open the JD and look for the explicit onsite/hybrid statement in the role's own description body. Conversely, when a role does require onsite work, the explicit language may only appear inside the individual JD (e.g., "in-person team culture, collaborating on-site with colleagues every day") — never project it from page-level context, but do verify it IS there when the role is in Mountain View.
- **Try `curl` before browser on any job board.** Even on sites described as "custom web components" or heavily JS-rendered, a `curl` call often returns full structured HTML. Always attempt `curl -s --max-time 15 <careers-url>` first. If it returns meaningful HTML with job data, use that. Only fall back to browser/JS injection when curl returns minimal content.

## Verification

Before returning the shortlist, confirm:
- Every shortlisted role has a source URL.
- Every shortlisted role's work model and management scope claims are either quoted/paraphrased from the posting or explicitly labeled as unconfirmed.
- The Exclusions Summary accounts for all reviewed roles not shortlisted.
