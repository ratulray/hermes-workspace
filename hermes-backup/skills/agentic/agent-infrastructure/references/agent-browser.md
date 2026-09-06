---
name: agent-browser
description: Browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing web apps, or automating any browser task. Triggers include requests to "open a website", "fill out a form", "click a button", "take a screenshot", "scrape data from a page", "test this web app", "login to a site", "automate browser actions", or any task requiring programmatic web interaction.
allowed-tools: Bash(npx agent-browser:*), Bash(agent-browser:*)
---

# Browser Automation with agent-browser

The CLI uses Chrome/Chromium via CDP directly. Install via `npm i -g agent-browser`, `brew install agent-browser`, or `cargo install agent-browser`. Run `agent-browser install` to download Chrome. Run `agent-browser upgrade` to update to the latest version.

## Core Workflow

Every browser automation follows this pattern:

1. **Navigate**: `agent-browser open <url>`
2. **Snapshot**: `agent-browser snapshot -i` (get element refs like `@e1`, `@e2`)
3. **Interact**: Use refs to click, fill, select
4. **Re-snapshot**: After navigation or DOM changes, get fresh refs

```bash
agent-browser open https://example.com/form
agent-browser snapshot -i
# Output: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Submit"

agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
agent-browser wait --load networkidle
agent-browser snapshot -i  # Check result
```

## Command Chaining

Commands can be chained with `&&` in a single shell invocation. The browser persists between commands via a background daemon, so chaining is safe and more efficient than separate calls.

```bash
# Chain open + wait + snapshot in one call
agent-browser open https://example.com && agent-browser wait --load networkidle && agent-browser snapshot -i

# Chain multiple interactions
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "password123" && agent-browser click @e3

# Navigate and capture
agent-browser open https://example.com && agent-browser wait --load networkidle && agent-browser screenshot page.png
```

**When to chain:** Use `&&` when you don't need to read the output of an intermediate command before proceeding (e.g., open + wait + screenshot). Run commands separately when you need to parse the output first (e.g., snapshot to discover refs, then interact using those refs).

## Handling Authentication

**Option 1: Import auth from the user's browser (fastest for one-off tasks)**

```bash
agent-browser --auto-connect state save ./auth.json
agent-browser --state ./auth.json open https://app.example.com/dashboard
```

State files contain session tokens in plaintext -- add to `.gitignore` and delete when no longer needed. Set `AGENT_BROWSER_ENCRYPTION_KEY` for encryption at rest.

**Option 2: Persistent profile (simplest for recurring tasks)**

```bash
agent-browser --profile ~/.myapp open https://app.example.com/login
# ... fill credentials, submit ...

# All future runs: already authenticated
agent-browser --profile ~/.myapp open https://app.example.com/dashboard
```

**Option 3: Session name (auto-save/restore cookies + localStorage)**

```bash
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close  # State auto-saved

# Next time: state auto-restored
agent-browser --session-name myapp open https://app.example.com/dashboard
```

**Option 4: Auth vault (credentials stored encrypted, login by name)**

```bash
echo "$PASSWORD" | agent-browser auth save myapp --url https://app.example.com/login --username user --password-stdin
agent-browser auth login myapp
```

**Option 5: State file (manual save/load)**

```bash
agent-browser state save ./auth.json
agent-browser state load ./auth.json
agent-browser open https://app.example.com/dashboard
```

## Essential Commands

```bash
# Navigation
agent-browser open <url>              # Navigate (aliases: goto, navigate)
agent-browser close                   # Close browser
agent-browser close --all             # Close all active sessions

# Snapshot
agent-browser snapshot -i             # Interactive elements with refs (recommended)
agent-browser snapshot -s "#selector" # Scope to CSS selector

# Interaction (use @refs from snapshot)
agent-browser click @e1               # Click element
agent-browser click @e1 --new-tab     # Click and open in new tab
agent-browser fill @e2 "text"         # Clear and type text
agent-browser type @e2 "text"         # Type without clearing
agent-browser select @e1 "option"     # Select dropdown option
agent-browser check @e1               # Check checkbox
agent-browser press Enter             # Press key
agent-browser keyboard type "text"    # Type at current focus (no selector)
agent-browser keyboard inserttext "text"  # Insert without key events
agent-browser scroll down 500         # Scroll page

# Get information
agent-browser get text @e1            # Get element text
agent-browser get url                 # Get current URL
agent-browser get title               # Get page title
agent-browser get cdp-url             # Get CDP WebSocket URL

# Wait
agent-browser wait @e1                # Wait for element
agent-browser wait --load networkidle # Wait for network idle
agent-browser wait --url "**/page"    # Wait for URL pattern
agent-browser wait 2000               # Wait milliseconds
agent-browser wait --text "Welcome"    # Wait for text to appear
agent-browser wait --fn "!document.body.innerText.includes('Loading...')"  # Wait for condition

# Downloads
agent-browser download @e1 ./file.pdf
agent-browser wait --download ./output.zip

# Network
agent-browser network requests                 # Inspect tracked requests
agent-browser network requests --type xhr,fetch
agent-browser network requests --status 2xx
agent-browser network har start
agent-browser network har stop ./capture.har

# Viewport & Device Emulation
agent-browser set viewport 1920 1080
agent-browser set device "iPhone 14"

# Capture
agent-browser screenshot              # Screenshot to temp dir
agent-browser screenshot --full     # Full page screenshot
agent-browser screenshot --annotate  # Annotated with numbered element labels
agent-browser pdf output.pdf

# Streaming / Live preview
agent-browser stream enable
agent-browser stream disable

# Clipboard
agent-browser clipboard read
agent-browser clipboard write "Hello, World!"

# Dialogs
agent-browser dialog accept
agent-browser dialog dismiss
agent-browser dialog status

# Diff (compare page states)
agent-browser diff snapshot                          # Compare current vs last snapshot
agent-browser diff screenshot --baseline before.png  # Visual pixel diff
agent-browser diff url https://staging.example.com https://prod.example.com

# Batch execution
echo '[["open","https://example.com"],["snapshot","-i"],["click","@e1"]]' | agent-browser batch --json
```

## Streaming

Every session automatically starts a WebSocket stream server on an OS-assigned port. Use `agent-browser stream status` to see the bound port. Use `stream disable` to tear it down.

## Batch Execution

Execute multiple commands in a single invocation by piping a JSON array of string arrays to `batch`. This avoids per-command process startup overhead.

```bash
echo '[
  ["open", "https://example.com"],
  ["snapshot", "-i"],
  ["click", "@e1"],
  ["screenshot", "result.png"]
]' | agent-browser batch --json
```

Use `batch` when you have a known sequence of commands that don't depend on intermediate output. Use separate commands or `&&` chaining when you need to parse output between steps.

## Common Patterns

### Form Submission

```bash
agent-browser open https://example.com/signup
agent-browser snapshot -i
agent-browser fill @e1 "Jane Doe"
agent-browser fill @e2 "jane@example.com"
agent-browser select @e3 "California"
agent-browser check @e4
agent-browser click @e5
agent-browser wait --load networkidle
```

### Authentication with Auth Vault (Recommended)

```bash
# Save credentials once (encrypted with AGENT_BROWSER_ENCRYPTION_KEY)
echo "pass" | agent-browser auth save github --url https://github.com/login --username user --password-stdin

# Login using saved profile
agent-browser auth login github
```

### Session Persistence

```bash
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close  # State auto-saved to ~/.agent-browser/sessions/

# Next time, state is auto-loaded
agent-browser --session-name myapp open https://app.example.com/dashboard
```

### Working with Iframes

Iframe content is automatically inlined in snapshots. Refs inside iframes carry frame context.

```bash
agent-browser open https://example.com/checkout
agent-browser snapshot -i
# @e2 [Iframe] "payment-frame"
#   @e3 [input] "Card number"
agent-browser fill @e3 "4111111111111111"
```

### Parallel Sessions

```bash
agent-browser --session site1 open https://site-a.com
agent-browser --session site2 open https://site-b.com
agent-browser session list
```

### Connect to Existing Chrome

```bash
agent-browser --auto-connect open https://example.com
agent-browser --cdp 9222 snapshot
```

### iOS Simulator (Mobile Safari)

```bash
agent-browser device list
agent-browser -p ios --device "iPhone 16 Pro" open https://example.com
agent-browser -p ios snapshot -i
agent-browser -p ios tap @e1
agent-browser -p ios screenshot mobile.png
agent-browser -p ios close
```

Requirements: macOS with Xcode, Appium (`npm install -g appium && appium driver install xcuitest`)

## Security

### Content Boundaries (Recommended for AI Agents)

Enable `--content-boundaries` to wrap page-sourced output in markers:

```bash
export AGENT_BROWSER_CONTENT_BOUNDARIES=1
agent-browser snapshot
```

### Domain Allowlist

```bash
export AGENT_BROWSER_ALLOWED_DOMAINS="example.com,*.example.com"
```

### Action Policy

```bash
export AGENT_BROWSER_ACTION_POLICY=./policy.json
```

```json
{ "default": "deny", "allow": ["navigate", "snapshot", "click", "scroll", "wait", "get"] }
```

## Diffing (Verifying Changes)

```bash
agent-browser snapshot -i          # Take baseline snapshot
agent-browser click @e2            # Perform action
agent-browser diff snapshot        # See what changed
```

For visual regression testing:

```bash
agent-browser screenshot baseline.png
# ... changes made ...
agent-browser diff screenshot --baseline baseline.png
```

## Ref Lifecycle (Important)

Refs (`@e1`, `@e2`) are invalidated when the page changes. Always re-snapshot after clicking links, form submissions, or dynamic content loading.

## Annotated Screenshots (Vision Mode)

```bash
agent-browser screenshot --annotate
# Output includes image path and legend: [1] @e1 button "Submit"
```

## JavaScript Evaluation

```bash
# Simple expressions
agent-browser eval 'document.title'

# Complex JS: use --stdin to avoid shell escaping issues
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify(Array.from(document.querySelectorAll("img")).map(i => i.src))
EVALEOF

# Or base64 encoding
agent-browser eval -b "$(echo -n 'expression' | base64)"
```

## Configuration File

Create `agent-browser.json` in the project root:

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data"
}
```

Priority (lowest to highest): `~/.agent-browser/config.json` < `./agent-browser.json` < env vars < CLI flags.

## Deep-Dive Documentation

| Reference | When to Use |
|---|---|
| `references/commands.md` | Full command reference |
| `references/snapshot-refs.md` | Ref lifecycle, invalidation rules |
| `references/session-management.md` | Parallel sessions, state persistence |
| `references/authentication.md` | Login flows, OAuth, 2FA |
| `references/video-recording.md` | Recording workflows |
| `references/profiling.md` | Chrome DevTools profiling |
| `references/proxy-support.md` | Proxy configuration |

## Browser Engine Selection

```bash
# Lightpanda (fast headless, 10x less memory than Chrome)
agent-browser --engine lightpanda open example.com
```

Supported engines: `chrome` (default), `lightpanda` (requires separate install from https://lightpanda.io).

## Observability Dashboard

```bash
agent-browser dashboard install
agent-browser dashboard start   # Background server on port 4848
agent-browser open example.com  # All sessions auto-visible in dashboard
```

## Ready-to-Use Templates

```bash
./templates/form-automation.sh https://example.com/form
./templates/authenticated-session.sh https://app.example.com/login
./templates/capture-workflow.sh https://example.com ./output
```
