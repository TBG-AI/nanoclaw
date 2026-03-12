# Slack Agent Architectures

NanoClaw supports two ways to run multiple agents in Slack. Both use Socket Mode (no public URL needed) and the Claude Agent SDK in containers.

## Architecture Overview

```
Approach A: Virtual JID Swarm            Approach B: Dedicated Agent Bots
(one Slack app, many identities)         (one Slack app per agent)

  Slack Workspace                          Slack Workspace
  +--------------------------+             +---------------------------+
  | #dev-channel             |             | #any-channel / DMs        |
  |                          |             |                           |
  |  User: @BugReporter ...  |             |  User: @BugReporterBot .. |
  |                          |             |                           |
  |  Bug Reporter [icon]:    |             |  BugReporterBot (APP):    |
  |  "Found 3 issues..."     |             |  "Found 3 issues..."     |
  +--------------------------+             +---------------------------+
        |                                        |
        | Single bot token                       | Own bot token
        | chat:write.customize                   | (separate Slack app)
        |                                        |
  +-----|------+                           +-----|------+
  | SlackChannel|                          | SlackAgent |
  | (slack.ts)  |                          | Bot (.ts)  |
  +-----|------+                           +-----|------+
        |                                        |
        | fan-out by                             | single JID
        | virtual JID                            | slackbot:{BOT_USER_ID}
        |                                        |
  +-----|------------------+               +-----|------+
  | slack:C123::bug-reporter|              | Container  |
  | slack:C123::senior-dev  |              | (isolated) |
  | ...each its own session |              +------------+
  +------------------------+
```

## Feature Comparison

| Feature | Virtual JID Swarm | Dedicated Agent Bot |
|---------|-------------------|---------------------|
| Slack apps needed | 1 (shared) | 1 per agent |
| Trigger mechanism | Text pattern (`@BugReporter`) | Real `@mention` or DM |
| DM support | No (channel only) | Yes |
| Identity | Username override (icon + name) | Real bot user (avatar, profile) |
| JID format | `slack:C0AJ2G07YCE::bug-reporter` | `slackbot:{BOT_USER_ID}` |
| Scopes needed | `chat:write.customize` | Standard bot scopes |
| Channel restriction | Tied to one channel | Works in any channel the bot is added to |
| Setup effort | Low (SQL + folder) | Medium (create Slack app + tokens) |
| Appears in member list | No | Yes (real bot user) |

## Message Flow

### Approach A: Virtual JID Swarm

```
1. User types:  "@BugReporter check the error logs"  in #dev-channel
                                    |
2. Slack delivers message event to SlackChannel (slack.ts)
                                    |
3. SlackChannel stores message under real JID:  slack:C0AJ2G07YCE
                                    |
4. Message loop fans out to all virtual JIDs matching that channel:
   - slack:C0AJ2G07YCE::bug-reporter
   - slack:C0AJ2G07YCE::senior-dev
                                    |
5. Each agent checks its own trigger:
   - bug-reporter trigger: /^@BugReporter\b/i  -->  MATCH
   - senior-dev trigger:   /^@SeniorDev\b/i    -->  no match, skip
                                    |
6. bug-reporter's container runs (own session, memory, CLAUDE.md)
                                    |
7. Output routed via channel.sendMessageAs(realJid, text, "Bug Reporter")
                                    |
8. Slack posts as "Bug Reporter" with a deterministic colored circle icon
```

### Approach B: Dedicated Agent Bot

```
1. User types:  "@BugReporterBot check the error logs"  in any channel
   — or sends a DM to BugReporterBot
                                    |
2. Slack delivers app_mention (channel) or message (DM) event
   to SlackAgentBot instance (slack-agent-bot.ts)
                                    |
3. SlackAgentBot translates <@BOT_USER_ID> mention into trigger pattern
   and stores message under JID:  slackbot:U0ABC123DEF
                                    |
4. Message loop picks up the message for this JID
   - trigger matches (prepended by handleIncoming)
                                    |
5. Agent container runs (own session, memory, CLAUDE.md)
                                    |
6. Output routed via channel.sendMessage(jid, text)
   - posts as the bot's own identity (no override needed)
                                    |
7. Reply goes to the channel where the last message was received
   (tracked via lastReplyChannelId)
```

## When to Use Which

| Scenario | Use |
|----------|-----|
| Multiple agents in a single channel, quick setup | Virtual JID Swarm |
| Agent needs its own @mention in Slack's autocomplete | Dedicated Agent Bot |
| Agent needs to receive DMs | Dedicated Agent Bot |
| Agent should work across multiple channels | Dedicated Agent Bot |
| You want to avoid creating multiple Slack apps | Virtual JID Swarm |
| Agent needs a real avatar and profile | Dedicated Agent Bot |
| Rapid prototyping / adding agents dynamically | Virtual JID Swarm |

## Setup: Virtual JID Swarm (Approach A)

Covered by the `/add-slack-swarm` skill. In short:

1. Ensure the main Slack app has `chat:write.customize` scope
2. Get the channel ID from Slack
3. Create the agent folder: `groups/slack_bug-reporter/`
4. Write agent `CLAUDE.md` in that folder
5. Register with a virtual JID:

```sql
INSERT OR REPLACE INTO registered_groups
  (jid, name, folder, trigger_pattern, added_at, requires_trigger, is_main)
VALUES
  ('slack:C0AJ2G07YCE::bug-reporter', 'Bug Reporter', 'slack_bug-reporter',
   '@BugReporter', '2026-01-01T00:00:00.000Z', 1, 0);
```

6. `npm run build` and restart NanoClaw

## Setup: Dedicated Agent Bot (Approach B)

### Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App** > **From scratch**
2. Name it after the agent (e.g., "BugReporter Bot")
3. Select your workspace

### Step 2: Configure Scopes

Under **OAuth & Permissions** > **Bot Token Scopes**, add:

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Receive @mention events |
| `chat:write` | Send messages |
| `im:history` | Read DM messages |
| `im:read` | Access DM conversations |
| `im:write` | Open DMs |
| `users:read` | Resolve user display names |
| `channels:read` | List channels (optional, for metadata) |

### Step 3: Enable Socket Mode

1. Go to **Socket Mode** in the sidebar and enable it
2. Generate an **app-level token** with `connections:write` scope
3. Save the token (starts with `xapp-`)

### Step 4: Enable Events

Under **Event Subscriptions**, enable events and subscribe to:

| Bot Event | Purpose |
|-----------|---------|
| `app_mention` | Triggers on @mentions in channels |
| `message.im` | Triggers on DMs to the bot |

### Step 5: Install the App

Go to **Install App** and install to your workspace. Copy the **Bot User OAuth Token** (starts with `xoxb-`).

### Step 6: Register in NanoClaw

Create the agent folder and CLAUDE.md, then register the group with Slack tokens in `container_config`:

```sql
INSERT OR REPLACE INTO registered_groups
  (jid, name, folder, trigger_pattern, added_at, container_config, requires_trigger, is_main)
VALUES
  ('slackbot:pending', 'Bug Reporter', 'slack_bug-reporter',
   '@BugReporter', '2026-01-01T00:00:00.000Z',
   '{"slackBotToken":"xoxb-YOUR-TOKEN","slackAppToken":"xapp-YOUR-TOKEN"}',
   1, 0);
```

The JID is registered as `slackbot:pending` because the actual bot user ID is unknown until the bot connects. At startup, NanoClaw calls `auth.test()`, discovers the bot user ID, and re-registers the group under `slackbot:{BOT_USER_ID}`.

### Step 7: Build and Restart

```bash
npm run build

# macOS
launchctl kickstart -k gui/$(id -u)/com.nanoclaw

# Linux
systemctl --user restart nanoclaw
```

### Step 8: Test

- **Channel**: Invite the bot to a channel and type `@BugReporterBot check the logs`
- **DM**: Open a DM with the bot and send any message (no trigger needed in DMs -- the trigger is auto-prepended)
- **Verify in logs**: `grep "agent bot" logs/nanoclaw.log`

## JID Format Reference

```
Virtual JID (Approach A):
  slack:{CHANNEL_ID}::{agent-id}
  slack:C0AJ2G07YCE::bug-reporter
       |              |
       real channel   agent identifier (lowercase, hyphenated)

Agent Bot JID (Approach B):
  slackbot:{BOT_USER_ID}
  slackbot:U0ABC123DEF
           |
           Slack bot user ID (resolved at connect time via auth.test)
```

## Key Implementation Files

| File | Role |
|------|------|
| `src/channels/slack.ts` | Main Slack channel: events, sendMessage, sendMessageAs |
| `src/channels/slack-agent-bot.ts` | Dedicated agent bot: own Slack app, @mention + DM handling |
| `src/virtual-jid.ts` | Virtual JID parsing (`realJid`, `isVirtualJid`, `buildTriggerPattern`) |
| `src/index.ts` (lines 585-623) | Startup: scans registered groups for Slack tokens, creates agent bots |
| `src/index.ts` (lines 105-130) | Dynamic registration: creates agent bot when group is registered at runtime |
| `src/types.ts` | `ContainerConfig` type with `slackBotToken` / `slackAppToken` fields |
