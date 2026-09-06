# Custom JS Web Component Job Boards

Some employers use a proprietary custom web component for their job board instead of a known ATS. This pattern is distinct from Workday (which uses a recognizable Workday-hosted URL) and from standard JS-rendered SPAs (which at least return a meaningful HTML shell via curl that hints at the JS framework).

## Identifying this pattern

1. `curl -s --max-time 15 <careers-url>` returns minimal/no HTML (no job data in the response body).
2. Browser loads the page and job listings appear after JS executes, but:
   - No `shadow-root` elements with job data (unlike some Web Component frameworks).
   - No `<script type="application/ld+json">` with JobPosting schema.
   - No XHR/fetch calls in the Network tab that return plain JSON.
   - Job links are not `<a href>` elements with recognizable job IDs in the URL — they may be button elements or have click handlers that POST to an ATS.
3. Greenhouse API (`boards-api.greenhouse.io/v1/boards/<slug>`) returns 404.
4. Ashby API (`api.ashbyhq.com/posting-api/job-board/<slug>`) returns "Not Found".
5. Lever API (`api.lever.co/v0/postings/<slug>`) returns "Document not found".

## Moveworks case study (2024–2026)

**Finding:** Moveworks' careers page (`moveworks.com/us/en/company/careers`) uses a custom web component for job listings, but the page **does return extractable structured HTML via `curl`** — no browser automation needed. Job data is embedded server-side in the initial HTML response.

**Confirmed working (2026-08-21):** `curl -s <careers-url>` returns 84 structured job cards in the initial HTML response.

**What was tried and failed (historical):**
- Greenhouse slugs: `moveworks`, `moveworksinc`, `the_moveworks`, `moveworks-careers`, `moveworks-workday` → all 404.
- Ashby slugs: `moveworks`, `moveworks-careers`, `moveworks-jobs` → all "Not Found".
- Lever API: `api.lever.co/v0/postings/moveworks` → "Document not found".
- Browser console JS injection: event handlers not attached in automation context; `querySelectorAll('a')` returned no job links.
- LinkedIn job search → paywalled, requires authentication.
- ServiceNow internal job board (`jobs.servicenow.com`) → DNS resolution failure.

**What works:** Direct `curl` + regex extraction from static HTML.

**Job card structure (confirmed 2026-08-21):**
```html
<div class="... cmp-job-listings__job"
     data-department="Engineering"
     data-location="Mountain view, California, United states">
  <h3 class="cmp-job-listings__job-title">Job Title</h3>
  <p class="cmp-job-listings__job-location">Mountain view, California, United states, Full-time</p>
  <a href="/us/en/company/careers/position?sr_id=744000XXXXXX">Apply for job</a>
</div>
```

Key extraction rules (confirmed working):
- **Title:** extract from `<h3 class="cmp-job-listings__job-title">` — query the `h3` element directly by tag name; class selector on the h3 often resolves empty.
- **Department/location:** extract from `data-department` and `data-location` attributes on the div, not from `<p class="...location">` text.
- **Job ID:** from `sr_id=` query param in the `href` attribute of the apply link.
- **Job URL:** `https://www.moveworks.com` + the href path.

**Known pitfalls:**
- Job links are inside `.cmp-job-listings__job` cards as `a[href]` with `sr_id` query params — not discoverable via top-level `querySelectorAll('a')`.
- The page-level footer contains generic ServiceNow "Work Personas" language ("flexible, remote, or required in office") — **not authoritative for individual roles**. Work model must be verified in the individual JD body.
- For Mountain View roles: the explicit "in-person team culture, collaborating on-site" language appears **only in the JD body** of individual roles that require it. Always open the role URL to confirm onsite requirement.
- When `curl` returns minimal content, fall back to JS injection on the filter `<select>` elements — but try `curl` first.

**`curl` extraction approach (primary — use this first):**
```bash
curl -s --max-time 20 "https://www.moveworks.com/us/en/company/careers" > page.html
# Extract job cards: re.findall('<h3 class="cmp-job-listings__job-title">([^<]+)</h3>', html)
# For each h3, back-extract the enclosing div for data-department, data-location, and sr_id
```

**JS injection fallback (for if curl returns empty/minimal HTML):**
```javascript
const deptSel = document.querySelector('.cmp-job-listings__filter__departments');
if (deptSel) { deptSel.value = 'Engineering'; deptSel.dispatchEvent(new Event('change', { bubbles: true })); }
const cards = document.querySelectorAll('.cmp-job-listings__job');
const jobs = [...cards].map(card => ({
  title: card.querySelector('h3')?.innerText.trim(),
  url: card.querySelector('a')?.href,
  location: card.querySelector('[class*="location"]')?.innerText.trim()
})).filter(j => j.title);
JSON.stringify({ count: jobs.length, jobs });
```

**Results across sessions:**
- 2026-08-21: 84 unique jobs (curl extraction, 1 shortlist pass)
- 2026-08-07: 72 unique after de-duplication
- 2026-07-31: 73–74 engineering roles (JS injection era)
- 2026-07-14: 80 roles (JS injection era)

## Correct fallback sequence

When both Greenhouse and Ashby APIs return 404/Not Found AND the page renders no extractable DOM structure:

1. Check if the company was recently acquired — acquirer's ATS or internal portal may host the roles.
2. Try the employer's careers page directly (not `/careers`, just the root or a general URL) — sometimes the main site has a different rendering path.
3. Try LinkedIn with browser auth (if available) — LinkedIn often has the roles indexed.
4. If all else fails, record the limitation in the shortlist output and state that manual per-posting verification is required.

## Adding a new employer with this pattern to EMPLOYERS.yaml

```yaml
# Custom/proprietary ATS — no API; browser-only, limited automation
MOVEWORKS:
  url: https://www.moveworks.com/us/en/company/careers
  ats_type: custom_web_component   # signals: browser-only, no curl-able API
  note: "Acquired by ServiceNow; no standard ATS API discovered (2026-07-14)"
```

Also add the employer to `references/employer-backfill.md` under a "custom/proprietary ATS" section with the status and date the discovery was made.
