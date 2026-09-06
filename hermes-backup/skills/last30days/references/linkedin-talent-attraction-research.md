# LinkedIn Talent Attraction Research — Session Pattern Bank

## Context from this session (2026-06-27)

**User:** Ratul Ray — Senior Engineering Manager, Agentic AI at ServiceNow.
**Task:** Create a LinkedIn recruiting post for a "Staff AI Engineer, Conversational Agentic AI" role.
**Job URL:** `https://careers.servicenow.com/jobs/744000134539069/staff-ai-engineer-conversational-agentic-ai/`

**Research failure:** `last30days` script ran in web-only mode and printed "Web Claude will search the web" — but the agent treated this as the search being done rather than as a handoff signal requiring manual `search_files` calls. Three posts were drafted from training knowledge rather than live competitive research. This reference documents the correct pattern for next time.

---

## What "Top AI Companies" Do in Talent Attraction Posts

These are patterns from training knowledge (not live research this session — see gap below):

1. **Lead with the hard problem, not the company** — "We're trying to make AI that can do X" not "We're a Series D company looking for Y"
2. **Show scale that matters** — "millions of users" or "across 200+ enterprise integrations" makes it real
3. **First-person plural throughout** — "we're building", "our team", never corporate "The Company seeks..."
4. **Specificity over buzzwords** — name the actual technical problems, not "cutting-edge AI"
5. **Honest about what the role isn't** — top candidates are skeptical; addressing tradeoffs builds trust
6. **Clear visual CTA** — job link in first comment + a simple call to share or DM
7. **No "we offer great benefits" list** — save that for the JD; the post's only job is the hook
8. **Hook in the first line** — engineers decide to read or scroll in 3 seconds

## Gap: Live Competitive Research Was Not Done

This session would have benefited from:
- Finding actual ServiceNow AI blog posts or engineering blog to extract specific projects/scale claims
- Searching LinkedIn for examples of similar posts from OpenAI, Anthropic, Google DeepMind hiring for agentic AI roles
- Checking what language/vocabulary is trending in agentic AI hiring right now (e.g., "reasoning", "tool use", "memory", "long-horizon planning")

**Correct approach for next time:** After `last30days.py` exits in web-only mode, immediately run 2–3 `search_files` calls manually before synthesizing. Do not assume the script's "Web Claude will search" message means the search has already happened.

## Draft Outputs from This Session

Three drafts were produced and saved to:
`/Users/ratul/Documents/linkedin_posts/agentic-ai-staff-engineer-draft.md`

- **Draft A (Mission Hook):** Lead with the problem — good for greenfield/high-autonomy candidates
- **Draft B (Engineer-to-Engineer):** Direct, "what it is / what it isn't" — good for skeptical ICs
- **Draft C (Short & Punchy):** One hook, one CTA — assumes brand recognition

All three drafts were based on training knowledge since live research failed.
