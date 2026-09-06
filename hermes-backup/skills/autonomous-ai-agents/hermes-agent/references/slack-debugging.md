# Slack Bot Debugging Reference

Common error patterns from gateway logs and their meanings.

## Missing Scope Error

**Log pattern:**
```
The server responded with: {'ok': False, 'error': 'missing_scope', 'needed': 'groups:read', 'provided': 'app_mentions:read,chat:write,files:write,im:write,assistant:write,commands,channels:history,channels:read,files:read,groups:history,im:history,im:read,users:read'}
```

**Cause:** Slack app is missing the `groups:read` OAuth scope.

**Fix:**
1. Go to https://api.slack.com/apps
2. Select your Hermes app
3. Navigate to **OAuth & Permissions** → **Bot Token Scopes**
4. Add `groups:read` scope
5. Click **Reinstall App** (this updates the token's permissions)
6. Restart gateway: `/restart`

## Channel Directory Errors

**Log pattern:**
```
WARNING gateway.channel_directory: Channel directory: failed to list Slack channels for team T0ANWNYE7L0: The request to the Slack API failed. (url: https://slack.com/api/users.conversations, status: 200)
```

**Cause:** Usually accompanies the missing_scope error above. The gateway can list channels but lacks permissions for private channels (groups).

## Messages Not Reaching Gateway - Deep Debug

When Socket Mode shows "connected" but messages don't arrive:

1. **Verify messages actually reach the gateway:**
   ```bash
   grep "inbound message" ~/.hermes/logs/gateway.log
   ```
   - If you see Telegram messages but NO Slack messages → Slack events aren't reaching Hermes
   - Check the platform field: `platform=slack` vs `platform=telegram`

2. **Check both log files:**
   ```bash
   # Gateway-level logs
   tail -50 ~/.hermes/logs/gateway.log
   
   # Agent-level logs  
   tail -50 ~/.hermes/logs/agent.log
   ```

3. **Socket Mode "connected" ≠ events working:**
   The WebSocket can be connected (handshake successful) but event subscriptions may not be active. This is a common issue when:
   - Event Subscriptions toggle is OFF in Slack app
   - Events aren't verified/enabled after adding them
   - App wasn't reinstalled after changing scopes

4. **Event Subscriptions verification (CRITICAL):**
   - Go to api.slack.com → Your App → **Event Subscriptions**
   - Toggle must be ON (enable)
   - Subscribe to: `app_mention`, `message.channels`, `message.im`
   - Each event should show green "enabled" checkmark

5. **Bot must be in the channel:**
   - For channel messages: invite @hermes to the channel
   - The bot needs to be a member to receive messages

6. **Real-time test:**
   - Send message in Slack
   - Immediately check logs: `tail -20 ~/.hermes/logs/gateway.log`
   - If nothing appears → Slack isn't sending events to the gateway

## Socket Mode Setup - App-Level Token

For Socket Mode to work, you need an App-Level Token (different from Bot Token):

1. **Generate in Slack:**
   - Go to api.slack.com → Your App → **App-Level Tokens**
   - Click "Generate Token and Scopes"
   - Name: "Socket Mode"
   - Add scope: `connections:write`
   - Copy token (starts with `xapp-`)

2. **Enable Socket Mode:**
   - Go to **Socket Mode** in left nav
   - Toggle "Enable Socket Mode"
   - Enter the App-Level Token

3. **Set in .env:**
   ```
   SLACK_APP_TOKEN=xapp-your-token-here
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   ```

## Bot Not Responding - Debug Checklist

1. **Check if gateway is running:**
   ```bash
   ps aux | grep -E "(hermes|openclaw)" | grep -v grep
   curl http://localhost:18789/health
   ```

2. **Check for duplicate gateways (common issue):**
   Multiple gateway processes cause conflicts. Look for:
   - `hermes gateway run` running multiple times
   - Both `openclaw` (node) and `hermes` (python) serving port 18789
   
   **Fix:** Kill duplicates:
   ```bash
   pgrep -f "hermes gateway run" | xargs kill 2>/dev/null
   ```

3. **Check Socket Mode connection state:**
   ```bash
   cat ~/.hermes/gateway_state.json
   ```
   
   Look for `"platforms": {"slack": {"state": "connected"}}`.
   
   Also check logs for reconnection:
   ```bash
   grep -i "\[Slack\].*connect" ~/.hermes/logs/gateway.log | tail -5
   ```

4. **Check gateway logs:**
   ```bash
   grep -i slack ~/.hermes/logs/gateway.error.log | tail -20
   ```

5. **Verify credentials in config:**
   ```bash
   grep -A5 "^slack:" ~/.hermes/config.yaml
   ```
   
   Tokens in `.env` may not be loaded. Ensure `slack.bot_token` is in `config.yaml`:
   ```bash
   hermes config set slack.bot_token xoxb-...
   ```

6. **Check mention requirement:**
   - If `slack.require_mention: true`, user must @mention bot
   - Test with DM first (bypasses channel permissions)

7. **Verify event subscriptions:**
   - Go to api.slack.com → Your App → Event Subscriptions
   - Ensure `message.channels`, `message.im` are enabled

8. **Force reconnection:**
   If Socket Mode appears connected but messages aren't reaching the gateway, restart the gateway:
   ```bash
   hermes gateway stop
   hermes gateway run --replace
   ```
   
   Verify reconnection in logs:
   ```bash
   grep "\[Slack\].*Socket Mode connected" ~/.hermes/logs/gateway.log | tail -3
   ```

## Corrupted App-Level Token

**Symptom:** Socket Mode shows "connected" in logs, but no messages arrive. The gateway appears to work but silently fails to receive events.

**Diagnosis:** Check token length:
```bash
grep "SLACK_APP_TOKEN" ~/.hermes/.env
# Correct token: ~25 chars, e.g. xapp-1-A0A-B3C4D5E6F7
# Corrupted token: 90+ chars (contains extra data or line breaks)
```

**Log hint:** If you see the token truncated in logs (e.g., `xapp-1...cd2a` showing 98 chars when printed), it's malformed.

**Fix:**
1. Go to api.slack.com → Your App → **App-Level Tokens**
2. Click "Generate Token and Scopes" (create a fresh one)
3. Ensure scope `connections:write` is added
4. Copy the new token (should be ~25 chars)
5. Update `.env`: `SLACK_APP_TOKEN=xapp-new-token`
6. Restart gateway: `hermes gateway restart`

**Why this happens:** The token may have been corrupted during copy-paste, or the `.env` file got appended to instead of replaced.

## Slash Commands Not Working in Threads

**Symptom:** Running `/sethome` (or other slash commands) inside a Slack thread returns "not supported in threads" error.

**Cause:** Slack doesn't support all slash commands when used inside threads — this is a platform limitation.

**Workarounds:**
1. **Use in a DM** — Send `/sethome` directly to @hermes in a DM (not in a thread)
2. **Use as regular message** — Send `@hermes /sethome` as a regular message in a channel or DM (not as a thread reply)
3. **Use outside a thread** — Send the command in the main channel, not as a reply

The `/sethome` command sets your "home channel" for the bot — you only need to run it once.

## Config Location

Slack credentials can be in two places:
- `~/.hermes/.env` - SLACK_BOT_TOKEN, SLACK_APP_TOKEN
- `~/.hermes/config.yaml` - slack.bot_token, slack.signing_secret

The gateway reads from config.yaml. If tokens are only in .env, they may not be loaded.