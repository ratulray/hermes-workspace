---
name: kb-monitor
description: Monitor a directory of files (e.g., AI knowledge base newsletters) and surface new entries to the user via Telegram. When the user approves a deeper dive, run online research and write a deep-dive file to the plans directory. Uses the last30days skill for research.
trigger: "user wants to monitor a knowledge base or file directory and be notified of new content via Telegram"
argument-hint: "<path_to_watch> <telegram_target> <output_dir> — e.g. '/Users/ratul/Documents/agent-roadmap/newsletters/ telegram /Users/ratul/Documents/agent-roadmap/kb-deep-dives'"
allowed-tools: [Bash, Read, Write, List, session_search, skill_view]
---

# KB Monitor — Surface New Content to User via Telegram

## Overview

When the user wants to stay informed about new entries in a knowledge base or file directory without manually checking, set up a KB monitor that:
1. Watches a directory for new files (tracking last-seen)
2. Assesses relevance to the user's interests
3. Sends a Telegram signal with a 2-3 sentence summary
4. If the user approves → runs `last30days` research and writes a deep-dive to `plans/kb-deep-dives/`

## Setup

Create a last-seen tracker at the actual path used by the cron job:
```
/Users/ratul/Documents/agent-roadmap/kb-monitor/last-seen.txt  ← stores the last-processed filename
```

> **Path note:** The skill home (`~/.hermes/`) does NOT expand to `/Users/ratul/` in all contexts. Always use the concrete absolute path for file operations in this workflow.

## Canonical Prompt

Use the prompt from `references/cron-job-prompt.md` as the cron job prompt.

## Relevance Assessment

Assess relevance broadly. Default to surfacing if any plausible connection to the user's interests. Relevant domains include: agent orchestration, LLMs, observability, AI infrastructure, agent evaluation, developer experience, enterprise AI.

## Deep Dive File Format

When the user approves, create:
```
/Users/ratul/Documents/agent-roadmap/kb-deep-dives/{date}-{slug}.md
```

With this structure:

```markdown
# Deep Dive: {Topic Title}

**Source:** {source name} — "{article title}" ({date})
**Research date:** {YYYY-MM-DD}

## Summary

What the research found across sources — synthesize key insights in 2-4 sentences.

## Key Research Findings

### 1. {Finding Name}
{{findings with direct quotes where possible}}

### 2. {Finding Name}
{{findings with direct quotes where possible}}

## Roadmap Ideas

### 1. {Idea Title}
**What:** Concise description of the proposed initiative.

**Implementation considerations:**
- Specific, actionable steps
- Resource implications
- Priority assessment

{{repeat for 3-5 ideas}}

## Resources

- [Primary source](url)
- [Additional resource](url)
```

**Critical**: Ground every finding in what the sources **actually say** — not generic knowledge. Use exact quotes where possible. If the research says "use JSON prompts", the deep dive must say "use JSON prompts", not a paraphrase.

## Telegram Message Format

```
[KB Signal] New entry: {filename}

Topic: {2-3 sentence summary}

Relevance to your team: {why this matters}

Want me to go deeper? (yes/no)
```

## Telegram Delivery

### Finding the right target

First, check which Telegram delivery mechanism is available in the current environment:

```bash
hermes send --list telegram 2>/dev/null && echo "hermes send available" || echo "hermes send not available"
```

Alternative: use the `send_message` function if available (e.g., `send_message(action='list')`).

### Sending the signal

If `hermes send` is available (positional message, NOT `--message` flag):
```bash
hermes send --to "telegram:Ratul Ray" "[KB Signal] New entry: {filename}

Topic: {2-3 sentence summary}

Relevance to your team: {why this matters}

Want me to go deeper? (yes/no)"
```

Note: `hermes send --message` does NOT work — the message is a positional argument, not a `--message` value.

If Telegram is unavailable — **do not abort**. Fall through to creating the deep-dive file and delivering via the cron job's standard output. The report is the delivery mechanism when Telegram is not available.

## Skill Dependencies

- `last30days` skill for research — load via `skill_view(name='last30days')` before invoking

## Pitfalls

- **Workdir responsiveness check BEFORE first run**: Before creating or running a KB monitor cron job, verify the workdir is responsive with `ls<path>` (5-second timeout). A hanging workdir (network drive, deep symlink chain, antivirus scan) causes every terminal command in the cron session to time out silently, making the job appear to fail for reasons unrelated to the skill or prompt. If the directory hangs, set the cron job's workdir to `~` or `/tmp` instead.
- **Failure resilience**: Store last-seen AFTER processing. If the job fails mid-way, don't skip files.
- **Sibling subagent race on last-seen.txt**: If multiple cron job instances of kb-monitor dispatch concurrently (common when a parent job fans out subagents), they will race to write `last-seen.txt`. The write_file tool will emit a conflict warning if a sibling modified the file since this agent's read. **Safe pattern**: read the file first, then write. If the warning fires anyway (sibling wrote between read and write), the write still succeeds — last-seen just reflects whichever agent won the race, which is fine since all agents are processing the same directory and the newest file is the true boundary. Do NOT treat the warning as a failure. Do NOT add sleep/retry loops — they increase the race window without solving it.
- **Deduplication**: Use file modification time, not just name — some files may be rewritten. Also watch for same content filed under different names/dates; check for duplicate content before surfacing.
- **Don't over-filter**: Better to surface a false positive than miss something relevant. The user can say no.
- **Cron job delivery**: Set `deliver: telegram` on the cron job so output goes to Telegram, not just logs.
- **last30days skill scanner risk**: The `last30days` skill contains documentation that may trigger Hermes's `_CRON_THREAT_PATTERNS` scanner (pattern: `cat\s+[^\n]*(\.env|...)`). When creating a KB monitor cron job that loads `last30days`, the assembled prompt (skill body + job prompt) is scanned at runtime. If the skill docs still contain any `cat .env` reference, the job will be silently blocked. See `last30days` skill Pitfalls section for the current safe patterns.
- **Telegram dependency**: `send_message` tool is unreliable in some environments (silently unavailable). Before relying on it, verify availability with `hermes send --list telegram`. If unavailable, fall back to creating the deep-dive file and delivering via cron output. Never let Telegram unavailability block the rest of the workflow.