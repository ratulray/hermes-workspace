# Greenhouse ATS — Known Patterns

## Quick Reference

Greenhouse job boards (URL pattern: `job-boards.greenhouse.io/<boardToken>/jobs/<id>`) render server-side HTML initially, but individual job detail pages are often JavaScript-hydrated. The listing page can be parsed from the static HTML or via browser console.

## Collections: Try API first, fall back to browser

### API
**Endpoint pattern:** `https://boards-api.greenhouse.io/v1/boards/<boardToken>/jobs?content=true`

**Example (Glean):**
```bash
curl -s --max-time 20 'https://boards-api.greenhouse.io/v1/boards/gleanwork/jobs?content=true'
```

**Response shape (JSON):**
```json
{
  "jobs": [
    {
      "id": 4677083005,
      "title": "Tech Lead Manager, Agentic Runtime",
      "location": { "name": "San Francisco, CA" },
      "departments": [{ "name": "Engineering" }],
      "offices": [{ "name": "San Francisco" }],
      "employment_type": "Full-time",
      "updated_at": "2026-07-..."
    }
  ]
}
```

**If API times out or returns empty:** fall back to browser-based console extraction (see below).

### Browser console extraction (when API fails)

Navigate to the company's careers listing page (e.g. `https://www.glean.com/careers`), then run in `browser_console`:

```javascript
(function() {
  const jobs = [];
  document.querySelectorAll('a[href*="greenhouse.io/gleanwork/jobs"]').forEach(a => {
    const href = a.href;
    const parts = href.split('/');
    const id = parts[parts.length - 1];
    const text = a.innerText.replace(/\n+/g, ' ').trim();
    const locMatch = text.match(/(San Francisco|Mountain View|Bangalore|Remote|New York|Seattle)/i);
    const location = locMatch ? locMatch[1] : '';
    jobs.push({ id, title: text.slice(0, 120), location, href });
  });
  const seen = new Set();
  const unique = jobs.filter(j => { if (seen.has(j.id)) return false; seen.add(j.id); return true; });
  return JSON.stringify(unique);
})();
```

**Important:** This only works on the **listing page**, not on individual job detail pages. If you're on a job detail page, navigate back to the listing first.

**Regex filtering** (after extracting IDs/titles to a list):
```python
import re
keywords = ['manager', 'director', 'head', 'lead', 'principal', 'VP', 'chief']
exclude = ['AI Success', 'Solutions Architect', 'Associate', 'Software Engineer',
           'Cloud', 'Application Security', 'SRE', 'Security Engineer',
           'Marketing', 'Sales', 'Finance', 'Recruiter']
for job in jobs:
    t = job['title']
    if any(k in t.lower() for k in keywords) and not any(e in t for e in exclude):
        print(job)
```

## Individual job detail: Use browser

Greenhouse job detail pages (`https://job-boards.greenhouse.io/<boardToken>/jobs/<id>`) render correctly in a browser. Navigate directly to the URL to read responsibilities and confirm management scope.

**Tip:** `browser_console(expression="document.querySelector('[data-testid=\"job-description\"]')?.innerText || document.body.innerText")` reliably extracts the full description text from Greenhouse job pages.

## Hard filter verification

Always verify on the job detail page:
- **Bay Area / hybrid**: Greenhouse locations are often listed as "San Francisco, CA", "Mountain View, CA" etc. — confirm hybrid requirement explicitly in the description ("4 days a week in our SF office").
- **People management**: Greenhouse titles like "Tech Lead Manager" or "Engineering Manager" are usually real management roles but verify — some "Manager" titles at early-stage companies can be player-coach / IC-weighted. Look for "1+ years of engineering management" or "lead and grow the team" language.

## Employer board tokens

Common patterns:
- `https://job-boards.greenhouse.io/<boardToken>/jobs` — the job board URL
- `https://boards-api.greenhouse.io/v1/boards/<boardToken>/jobs?content=true` — the API

To find the board token: look at any job URL on the site — it appears between `/jobs/` and the job ID.

Known tokens (from EMPLOYERS.yaml):
- Glean → `gleanwork`
- Scale AI → `scaleai`
- And others — verify from the actual job board URL on each run

If the employer uses Greenhouse but you don't know the board token: navigate to `https://boards-api.greenhouse.io/v1/boards/<companyname>/jobs?content=true` and try common variants (company name, `work`, `careers`, etc.).
