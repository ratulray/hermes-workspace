# Candidate filter — AI-leadership roles

How to decide which postings count as AI-leadership candidates for the monthly corpus. The goal is a corpus of roles that lead an engineering org doing AI/ML work, so the extracted skill bullets describe AI leadership and nothing else.

## Why a title is not enough

A title is a *candidate generator*, never a decision. Titles that pass a naive leadership regex include a large tail of roles that are not AI leadership at all:

| Title | Why it is not a match |
|---|---|
| PR Director, APAC | Communications, not engineering |
| Head of Corporate Development | Business development |
| VP of Services, Customer Success & Support | Customer-facing org |
| Lifecycle Growth Manager | Growth, not an eng org |
| Customer Advocacy Manager | Marketing |
| Regional Director, AI Deployment | Regional sales over a book of business |
| Head of ASEAN, Applied AI | Regional go-to-market head |
| Technical Program Manager, AI Delivery | Program management, no direct reports |
| Manager, Applied AI Architecture | Solutions architecture / presales |
| Partner Account Manager, AI-Native | Partnerships |

## The four gates

Apply in order. A candidate must clear all four.

### 1. Leadership title

Match: `Head of`, `Director`, `VP`, `Senior Manager`, `Sr. Manager`, `Engineering Manager`, `Eng. Manager`, `Group Manager`, `Manager`, `Tech Lead Manager`, `Head of`.

Reject first if the title contains: `Technical Program Manager`, `Program Manager`, `TPM`, `Product Manager`, `Project Manager`, `Policy Manager`, `Solutions Manager`, `Architect`/`Architecture`, `Outcomes Manager`, `Alliances Manager`, `Strategy & Operations`.

### 2. AI/ML signal

The signal may sit in the title OR in the first ~4000 chars of the posting body. Title signals: `AI`, `ML`, `LLM`, `GenAI`, `Agentic`, `Agent`, `Machine Learning`, `Model`, `Inference`, `Data Science`, `Deep Learning`, `NLP`, `MLOps`, `Applied Science`, `Research Engineer`.

Body-only signal is legitimate and common — a role titled "Engineering Manager, Platform" on an AI platform team qualifies. Body-only signal is NOT legitimate for a generic title like "Director, Corporate Development" whose body merely mentions AI somewhere.

### 3. Not a business-leadership or customer-facing track

Reject titles containing: `Regional Director`, `Success Manager`, `Account Executive`, `Solutions Engineer`, `Solutions Engineering`, `Solution Strategy`, `Professional Services`, `Customer Engineer`, `Customer Advocacy`, `Technical Support`, `Support Engineering`, `Lifecycle Growth`, `Growth Manager`, `Deployment Manager`, `AI Deployment`, `Alliances Manager`, `Marketplace Partner`, `Field Marketing`, `Policy`, `Corporate Development`, `Communications`, `PR Director`, `Talent Acquisition`, `Recruiting`, `Legal`, `Litigation`, `Counsel`, `Chief of Staff`, `Cyber AI Partner`, `Partnerships`, `Product Design`, `Customer Success & Support`, `of Services`.

`Head of X` is only an engineering head when X is an engineering or AI function: `AI`, `Applied`, `Engineering`, `Machine Learning`, `Technical`, `Data`, `Research`, `Product`, `Developer`, `Platform`, `Infrastructure`, `Artificial Intelligence`. `Head of ASEAN` and `Head of Southern Europe` are regional business heads — exclude.

### 4. People-management evidence in the body

A leadership title must be corroborated by the posting. Look for these phrases in the body:

```
direct reports | reports to | manages a team of | managing a team |
managing and leading | leading a team | leads a team of | headcount |
team of N | N+ direct reports | mentors | coaching | performance reviews |
hiring and | build a team | build and grow | growing a team | owns the team |
people manager | group manager | manage the team/group/org | leadership of the team
```

**Do not use the bare token "manager".** It appears in every title and in standard boilerplate, so a regex that matches it accepts every IC role and every non-management posting.

**Do not use a body-wide sweep.** Scan the first ~8000 chars, and check the responsibilities/qualifications sections specifically — a "manager" in an unrelated context is noise.

## Applying it

`${HERMES_SKILL_DIR}/scripts/fetch_jd.py` implements all four gates:

```bash
# List candidates with an eligibility marker ('+' = passes all four gates)
python3 ${HERMES_SKILL_DIR}/scripts/fetch_jd.py --employer OPENAI --list

# Write the top N as JD files
JD_MONTH=2026-11 python3 ${HERMES_SKILL_DIR}/scripts/fetch_jd.py --employer OPENAI --pick 3 --start-row 1
```

The script reads the ATS listing via the employer's `api_endpoint` in `EMPLOYERS.yaml` and falls back to scraping the portal.

## ATS response field names

The description body lives under a different key per ATS. Reading the wrong one yields a zero-length body for every posting, which makes gate 4 reject every candidate — the run then reports "no eligible roles" for an employer that clearly has them.

| ATS | Description key | Other keys |
|---|---|---|
| Ashby | `descriptionHtml`, `descriptionPlain` | `title`, `location` (string), `jobUrl` |
| Greenhouse | `content` | `title`, `location` (object with `.name`), `absolute_url` |

Check `jq 'keys'` on one record before writing field accessors. If every candidate has an empty body, suspect the key name before suspecting the portal.

**Greenhouse `content` is HTML-escaped** — the body arrives as `&lt;h2&gt;...` rather than `<h2>...`. Unescape before looking for tags, or every heading renders as literal text and the section split silently fails.

## Section headings: the posting's own headings win

`fetch_jd.py` splits a posting into responsibilities and qualifications. It first looks for the posting's **own section headings**, because a marker-word scan of flattened text mis-buckets duties. The heading shapes seen in the wild:

| ATS / employer | Responsibilities heading | Qualifications heading |
|---|---|---|
| Ashby (Cohere, Perplexity) | `<p><strong>RESPONSIBILITIES</strong></p>` | `<p><strong>QUALIFICATIONS</strong></p>`, `<h2><strong>Qualifications</strong></h2>` |
| Greenhouse (Stripe) | `<h3>` / `<h4>Responsibilities` | `<h4>Minimum requirements`, `<h4>Preferred qualifications` |
| Airbnb | `<p><strong>A Typical Day:</strong></p>` | `<p><strong>Your Expertise:</strong></p>` |
| Amazon | prose under a `Key job responsibilities` marker | `Basic Qualifications` / `Preferred Qualifications` sections |

Two traps in this area:

- **"Minimum requirements" is not "Minimum qualifications".** A heading matcher keyed on the word "qualifications" alone misses Stripe's wording and drops the whole requirements list.
- **The intro sentence under a qualifications heading is not a requirement.** Stripe writes "We're looking for someone who meets the minimum requirements to be considered for the role" as a lead-in paragraph, and Cohere writes "You may be a good fit if:". Note the curly apostrophe (`’`) in the posting text — a matcher written with a straight `'` does not match it.

A posting with no usable headings (Amazon's prose blobs) must fall back to marker-based splitting rather than being forced into the heading path.

## Splitting a posting's bullets when you write JD files yourself

If you extract bullets directly rather than through `fetch_jd.py`, parse the markup structurally — do not regex the flattened text:

- **Bullets live in `<ul><li>`, and a `<li>` may contain a nested `<ul>`** (Perplexity's Enterprise qualifications nest three domain areas under one bullet). A non-greedy `<li>...</li>` regex truncates the parent bullet at the first nested `</li>`; match `<li>` with nesting depth instead.
- **Headings may be `<h1>`–`<h6>` or a `<p>` whose only child is `<strong>`.** Handle both.
- **A heading ends the previous section.** Cohere's posting runs `You may be a good fit if:` (qualifications) and then a separate perks block; without ending the section at the new heading, the perks land in the qualifications list and are mined as skills.
- **Amazon's requirements are prose paragraphs, not list items**, and the EEO/salary boilerplate trails the qualifications section — cut it, or "Amazon is an equal opportunity employer" becomes a qualification bullet.

## Ranking within one employer

The `max_per_employer` cap keeps only the highest-scored roles, so the ranking decides what survives. Order by:

1. Seniority of the leadership title (`Director`/`Head of`/`VP` above `Manager`)
2. AI/ML signal in the **title** (above signal found only in the body)
3. Platform / infrastructure / inference / applied / agentic focus in the title
4. Engineering or research in the title

## Filenames

`NN-{company-slug}-{title-slug}.md`, `NN` is a two-digit running number.

Slug by lowercasing and replacing non-alphanumerics with `-`, then **cap the length and append a short hash of the full title when you truncate**. Two roles at one employer with long similar titles ("...AI Delivery for Public Sector & Defence, Canada" / "...UK") otherwise reduce to the same slug and the second file silently overwrites the first — losing a JD without any error.
