# Cron Job Observability

How to inspect scheduled jobs — their full prompts, run history, and token cost. Use when asked what a cron job does, whether runs were missed, or what a run consumed.

## Reaching the cron tool

`cronjob_manage` is a deferred tool: it is not in the always-loaded tool list. Reach it with `tool_search` → `tool_describe` → `tool_call`, and invoke it through `tool_call` with a non-empty `calls` array of `{name, arguments}` entries. Calling it as a direct function fails with a "does not exist" error listing only the always-loaded tools.

Its `action` values: `list`, `create`, `update`, `pause`, `resume`, `remove`, `run`, `resnap`.

## Reading a job's full prompt

`action=list` returns only a truncated `prompt_preview` (roughly the first 100 characters). To read or edit the complete prompt, parse the jobs file directly:

```python
import json
with open('/Users/ratul/.hermes/cron/jobs.json') as f:
    data = json.load(f)
for job in data['jobs']:
    if job['id'] == '<job_id>':
        print(job['prompt'])
```

`jobs.json` also holds schedule, delivery target, `workdir`, `enabled_toolsets`, `next_run_at`, `last_run_at`, `last_status`, and `last_error`.

## Run history and missed runs

`~/.hermes/cron/usage_audit.jsonl` holds one JSON line per fire with `ts`, `job_id`, `fire_id`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `model`, `duration_ms`, `error`. Timestamps are UTC (`Z`); convert to local time before comparing against a local cron expression.

`~/.hermes/cron/executions.db` (SQLite) has two tables worth querying:

- `executions` — per-fire `status` (`claimed`/`running`/`completed`/`failed`/`unknown`/`cancelled`/`missed`), `claimed_at`, `started_at`, `finished_at`, `scheduled_instant`, `delivery_outcome`, `error`.
- `cron_incidents` — deduplicated recurring error signatures per job with `state`, `failure_type`, and `alerted_at`.

A job that did not fire while the scheduler was down shows as `missed` or has no `executions` row for that `scheduled_instant` — the distinction between "missed" and "ran late" comes from comparing `scheduled_instant` against `started_at`, not from `last_run_at` alone.

## Per-run output archives

`~/.hermes/cron/output/{job_id}/{YYYY-MM-DD_HH-MM-SS}.md` holds the fully assembled prompt plus the final response for each fire — the same content delivered to the target channel.

## Token cost

`usage_audit.jsonl` gives per-fire totals. Note that `prompt_tokens` there is the **sum across every API call in the fire**, not one call's context size.

For a task-level breakdown, parse the agent log. Each API call logs its token counts, and the session id for a cron fire is `cron_{job_id}_{YYYYMMDD}_{HHMMSS}`:

```
agent.conversation_loop: API call #N: model=... in=<prompt> out=<completion> total=<sum> latency=...s cache=<read>/<total> (<pct>%)
```

Filter the log by that session id to recover the full event stream — API calls interleaved with `tool <name> completed (<s>s, <chars> chars)` lines — then segment it into task phases.

**Segmenting by phase:** the agent writes helper scripts to the scratch directory (`~/.hermes/cache/scratch/`) as it works, and each script's mtime marks the start of the phase it belongs to (`parse_mw.py` → parse, `*_bucket*.py` → bucketing, `*_archive*.py` → archiving). File mtimes give phase boundaries without instrumenting the agent.

**Reading the numbers correctly:**

- Total prompt tokens across a run ≈ `calls × average context size`, because each turn re-sends the entire accumulated conversation. A run that feels cheap can post a huge total purely from many turns against a long context.
- The `cache=<read>/<total>` field separates **fresh** (uncached) prompt tokens from cache reads. Report fresh prompt tokens, completion tokens, and the cache hit rate separately — quoting only the total overstates the cost of new work by orders of magnitude.
- Tool output is injected into context in full. Large `chars` counts are the direct driver of context growth and therefore of the next turn's prompt size.

## Reading job output

`action=run` fires a job immediately in the **background** and returns a handle. The result re-enters the conversation as a new message when it finishes — do not poll for it. `action=run` also accepts a transient `prompt` argument that is appended for that one fire only and never persisted, which is the way to ask a job to dump its own state.

## Gotchas

- `action=update` on an existing job is preferred over creating a near-duplicate; always `list` first and copy the real `job_id` — never guess ids.
- Renaming a job is a separate `action=update` call with just `name`.
- A job's final response is what gets delivered. Jobs that need a specific delivery target (a group chat rather than the home channel) need an explicit `platform:chat_id` target; the Telegram group id is stored without the `-100` supergroup prefix.
- Cron runs execute with no user present to approve commands, so dangerous-command approvals and some execution paths behave differently than in an interactive session. Keep cron prompts to read-only or pre-approved operations.
