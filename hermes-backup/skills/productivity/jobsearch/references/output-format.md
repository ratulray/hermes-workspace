# Output Format

Use this structure for every shortlist.

## Header

- Employer name
- Portal URL used
- Date checked
- Number of roles reviewed
- Number of roles shortlisted

## Ranked Shortlist

For each shortlisted role, provide:

**[Rank]. Role Title** — Score: N
- **Department:** X | **Location:** Y | **Work model:** Z | **Comp:** W
- **Hard filters:** ✅/❌ — evidence (quote or paraphrase from posting, or "not confirmed")
- **Why it matches:** 2–4 concise evidence-based bullets
- **Risks or gaps:** 1–2 concise bullets (e.g. management scope unconfirmed, domain mismatch)
- **Source:** direct role URL

**Compensation field:** Use `"$XXX–$YYY"` if publicly listed in the posting. Use `"not publicly listed"` if absent. Do not infer or estimate comp.

## Exclusions Summary

List the main exclusion buckets with counts when practical:
- remote-only / no Bay Area option
- IC-only, no confirmed management scope
- seniority mismatch (too junior or too senior)
- domain mismatch (no AI/agentic/ML component)
- non-technical management role
- duplicate or already applied (cross-checked against APPLICATIONS.yaml when relevant)

## Notes

State any limitations such as:
- search results were incomplete due to [reason]
- the portal required heavy client-side rendering — API fallback used: [endpoint]
- some listings lacked location, work-model, or management-scope detail
- compensation not publicly listed on any shortlisted role
