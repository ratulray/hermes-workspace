---
name: agentmail
description: API-first email platform designed for AI agents. Create and manage dedicated email inboxes, send and receive emails programmatically, and handle email-based workflows with webhooks and real-time events. Use when you need to set up agent email identity, send emails from agents, handle incoming email workflows, or replace traditional email providers like Gmail with agent-friendly infrastructure.
---

# agentmail — AI Email Infrastructure

API-first email platform for AI agents. Create/manage dedicated email inboxes, send/receive emails programmatically, handle email-based workflows with webhooks and real-time events.

## Installation

```bash
npm i -g @agent-mail/cli  # or appropriate package name
```

## Core Concepts

- **Inboxes**: Each agent gets a dedicated email inbox with its own address
- **Sending**: Send emails via CLI or API
- **Receiving**: Poll for new emails or use webhooks for real-time delivery
- **Threads**: Conversations are tracked as threads

## Common Workflows

### Send an email

```bash
agent-mail send --to recipient@example.com --subject "Subject" --body "Message body"
```

### Check inbox

```bash
agent-mail inbox list
agent-mail inbox read <email-id>
```

### Create a dedicated agent inbox

```bash
agent-mail inbox create --name "my-agent" --domain "agent.example.com"
```

### Set up webhook for incoming emails

```bash
agent-mail webhook create --url https://your-agent.com/webhook/email --events "email.received"
```

## Error Handling

- HTTP error codes — check response status before proceeding
- API rate limits — implement backoff on 429 responses
- Webhook failures — implement retry logic with exponential backoff
