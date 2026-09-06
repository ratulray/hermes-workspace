---
name: agent-infrastructure
description: Reusable agent tooling — browser automation, email, speech-to-text, and social media scraping. Load any of these when building workflows that interact with external services and platforms on behalf of the user.
version: 1.0.0
author: Hermes Agent (consolidated from openclaw-imports)
platforms: [macos, linux]
metadata:
  hermes:
    tags: [agentic, infrastructure, browser, email, speech-to-text, twitter, automation]
    related_skills: [autonomous-ai-agents, hermes-agent]
---

# Agent Infrastructure — External Service Integration for AI Agents

This umbrella skill covers four agent-facing infrastructure tools: browser automation, email, speech-to-text, and social media scraping. Each is loaded independently based on the task at hand.

## Skills in this Umbrella

### [agent-browser](references/agent-browser.md) — Browser Automation
Browser automation CLI for AI agents. Navigate pages, fill forms, click buttons, take screenshots, extract data, test web apps. Triggers: "open a website", "fill out a form", "click a button", "scrape data from a page", "automate browser actions".

**Key reference:** `references/agent-browser.md` — contains the full skill body migrated from `openclaw-imports/agent-browser`.

### [agentmail](references/agentmail.md) — AI Email Infrastructure
API-first email platform for AI agents. Create/manage dedicated email inboxes, send/receive emails, handle email-based workflows with webhooks. Triggers: "set up agent email", "send emails from agent", "handle incoming email workflows".

**Key reference:** `references/agentmail.md` — contains the full skill body migrated from `openclaw-imports/agentmail`.

### [openai-whisper](references/openai-whisper.md) — Local Speech-to-Text
Local speech-to-text with Whisper CLI (no API key required). Triggers: "transcribe audio", "speech to text", "transcribe recording".

**Key reference:** `references/openai-whisper.md` — contains the full skill body migrated from `openclaw-imports/openai-whisper`.

### [twitter-feed](references/twitter-feed.md) — Twitter/X Feed Scraping
Scrape posts from X/Twitter home feed using agent-browser with existing Chrome credentials. Triggers: "check my twitter", "summarize the feed", "what's on my twitter".

**Key reference:** `references/twitter-feed.md` — contains the full skill body migrated from `openclaw-imports/twitter-feed`.

---

## Shared Patterns

All skills in this umbrella share these patterns:

### CLI-first tools
All tools are CLI-based (`agent-browser`, `agent-mail`, `whisper`, `twitter-feed`). Installation and upgrade instructions are in each reference file.

### Session/state persistence
- **agent-browser**: Uses `--profile`, `--session-name`, or `--state` for session persistence. Auth state can be saved/loaded.
- **agentmail**: API-key based; no local session state.
- **openai-whisper**: No session state — stateless binary.
- **twitter-feed**: Relies on Chrome profile for auth; session cookies don't reliably persist via `state save` — use `--profile` instead.

### Error handling
- **agent-browser**: Daemon busy (`os error 35`) — run commands separately, not chained. Element refs invalidated after navigation.
- **agentmail**: HTTP error codes — check response status before proceeding.
- **openai-whisper**: File not found / unsupported format — verify file exists and is a supported audio format.
- **twitter-feed**: Auth failure (login page) — re-authenticate manually. `state save` does not reliably persist Twitter session cookies.

## Common Workflows

### 1. Agentic web research pipeline
```
Load agent-browser → open URL → snapshot → interact → extract data
```

### 2. Asynchronous communication pipeline
```
Load agentmail → create inbox / send message / poll for replies
```

### 3. Audio processing pipeline
```
Load openai-whisper → transcribe audio file → use transcript in downstream task
```

### 4. Social media monitoring pipeline
```
Load twitter-feed → authenticate via Chrome profile → scrape feed → summarize
```

## Tool Discovery

When the user asks to interact with a specific external service:
1. Check if one of the four skills above covers it
2. If not, load the skill and follow its reference documentation
3. If no skill exists, use the generic `browser` tool or direct CLI invocation

## Installation Cheat Sheet

| Tool | Install |
|------|---------|
| agent-browser | `npm i -g agent-browser` or `brew install agent-browser` or `cargo install agent-browser` |
| agent-mail | `npm i -g @agent-mail/cli` (check actual package) |
| whisper | `brew install openai-whisper` |
| twitter-feed | Uses agent-browser with Chrome profile |

---
*Consolidated 2026-07-23 from openclaw-imports/{agent-browser, agentmail, openai-whisper, twitter-feed}*
