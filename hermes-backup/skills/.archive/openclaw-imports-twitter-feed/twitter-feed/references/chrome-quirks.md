# Chrome Quirks When Using agent-browser with Twitter/X

## Problem 1: Chrome for Testing vs Regular Chrome

**Symptom**: Browser opens but Twitter shows the login page even though you're logged in.

**Cause**: agent-browser defaults to its bundled Chrome for Testing binary. This is a bare Chrome with no user data — no cookies, no sessions.

**Fix**: Always pass `--executable-path` pointing at the user's regular Chrome installation:
```bash
agent-browser --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ...
```

Combined with `--profile Default`, this loads the user's real Chrome profile including all stored cookies and sessions.

---

## Problem 2: Gemini in Chrome Side Panel

**Symptom**: After opening x.com or scrolling, `agent-browser snapshot` returns a Gemini UI tree instead of the Twitter page. The output starts with `button "Close Gemini in Chrome"` and contains headings like "Get help with your tabs and tasks with Gemini in Chrome".

**Cause**: Chrome has a built-in "Gemini in Chrome" (internally called GLIC) feature that auto-opens as a side panel on certain pages. When it opens, it takes the accessibility tree focus, causing `snapshot`, `get html`, and `get text` to query Gemini's DOM instead of the underlying page.

This feature is NOT a browser extension — `--disable-extensions` alone does not prevent it. It is a built-in Chrome feature controlled by two separate flags.

**Fix**: Disable both flags at launch:
```bash
--args "--disable-extensions,--disable-features=GLIC,GlicBootstrapping"
```

- `GLIC`: disables the Gemini in Chrome side panel feature itself
- `GlicBootstrapping`: disables the onboarding/auto-open trigger that causes it to pop open during page interactions

Both flags are required. Using only `GLIC` suppresses the panel on initial load but it may reopen on scroll. Using only `GlicBootstrapping` prevents auto-open but the panel can still be triggered.

**Fallback if Gemini still opens mid-session**: Use `agent-browser screenshot` instead of `snapshot`. Screenshots capture the visual page content — Twitter is on the left side of the window and is always visible even when the Gemini panel is open on the right. The panel does not obscure the feed.

---

## Problem 3: Daemon Busy Errors on Rapid Command Chains

**Symptom**: `✗ Failed to read: Resource temporarily unavailable (os error 35) (after 5 retries - daemon may be busy or unresponsive)`

**Cause**: The agent-browser daemon uses a Unix socket for IPC. When commands are sent too quickly back-to-back (e.g., `scroll && screenshot && scroll && screenshot`), the socket can't accept the next command while still processing the previous one, returning `EAGAIN` (error 35).

**Fix**: Run each command as a separate Bash call instead of chaining with `&&`. Each separate call gives the daemon time to finish the previous operation:
```bash
# Bad — causes busy errors:
agent-browser scroll down 800 && agent-browser screenshot /tmp/feed.png

# Good — separate calls:
agent-browser scroll down 800
agent-browser screenshot /tmp/feed.png
```

---

## Problem 4: Twitter Blocks Login with "This browser or app may not be secure"

**Symptom**: When trying to log into Twitter in an agent-browser-launched Chrome, Twitter shows "This browser or app may not be secure" and blocks the login.

**Cause**: agent-browser launches Chrome with Playwright/CDP automation flags. These set `navigator.webdriver = true` and other automation markers that Twitter detects and rejects during login.

**Fix**: Pass `--disable-blink-features=AutomationControlled` in `--args`. This suppresses the automation signals:
```bash
agent-browser --args "--disable-blink-features=AutomationControlled" open https://x.com/login
```

Note: this is only needed when performing a fresh login. For regular scraping where the session already exists in the profile, Twitter does not re-check these signals on session resume.

## Problem 5: Auth State Save Does Not Preserve Twitter Session

**Symptom**: After `agent-browser state save /tmp/auth` and restarting with `--state /tmp/auth`, Twitter shows the logged-out homepage.

**Cause**: Chrome encrypts cookies using a key stored in the macOS Keychain, tied to the profile's user data directory. A saved state file contains the encrypted cookie bytes, but loading them into a different profile (with a different keychain entry) causes decryption to fail silently — cookies are present but invalid.

**Fix**: Use a dedicated persistent profile (`--profile ~/.openclaw/chrome-twitter`). Log in once with `--disable-blink-features=AutomationControlled` and `--headed`. Chrome writes the session to disk on close. All future runs reuse it without re-login.
