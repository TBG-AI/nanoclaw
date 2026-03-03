---
name: add-slack-swarm
description: Add Agent Swarm (Teams) support to Slack. Multiple independent agents share a channel, each with its own identity, trigger, memory, and session. Requires Slack channel to be set up first (use /add-slack). Triggers on "slack swarm", "slack agents", "slack teams", "multi-agent slack".
---

# Add Agent Swarm to Slack

This skill adds multi-agent swarm support to an existing Slack channel. Each agent gets its own identity (custom username + colored icon), trigger pattern, memory folder, and independent Claude session — all sharing a single Slack channel.

**Prerequisite**: Slack must already be set up via the `/add-slack` skill. If `src/channels/slack.ts` does not exist or Slack tokens are not configured, tell the user to run `/add-slack` first.

## How It Works

Uses **virtual JID aliasing** — each agent registers with a virtual JID that's the real channel JID plus a `::agent-id` suffix:

```
Real channel:  slack:C123456789
Virtual JIDs:  slack:C123456789::bug-reporter    → folder: slack_bug-reporter
               slack:C123456789::senior-dev      → folder: slack_senior-dev
```

- Messages are stored under the **real JID** (normal Slack message flow)
- The message loop fans out to all virtual JIDs matching that channel
- Each agent checks its **own trigger** (e.g., `@BugReporter`)
- Each agent has its **own session, memory, and CLAUDE.md**
- Responses appear with the agent's name and a deterministic colored icon via Slack's `chat.postMessage` username override

```
User: "@BugReporter check the error logs"
  → Message stored under slack:C123456789
  → Fan-out finds slack:C123456789::bug-reporter
  → Trigger "@BugReporter" matches → agent runs
  → Response posted as "Bug Reporter 🔵" via sendMessageAs
```

## No Extra Slack Setup Needed

Unlike Telegram swarm (which needs pool bots), Slack swarm uses the **same bot token** with `chat:write.customize` scope to override the username and icon per message. The bot app must have this scope — check Step 1.

## Implementation Steps

### Step 1: Verify Slack Bot Permissions

The Slack app needs the `chat:write.customize` OAuth scope to post with custom usernames.

Tell the user:

> Your Slack app needs the `chat:write.customize` scope for agent identity overrides.
>
> 1. Go to [api.slack.com/apps](https://api.slack.com/apps) → your app → **OAuth & Permissions**
> 2. Under **Bot Token Scopes**, check if `chat:write.customize` is listed
> 3. If not, add it and **reinstall the app** to your workspace
>
> Do you already have this scope, or did you just add it?

Wait for confirmation.

### Step 2: Identify the Slack Channel

Ask the user which Slack channel to add agents to. They need the channel ID.

Tell the user:

> Which Slack channel should the agents work in?
>
> To find the channel ID:
> 1. Open the channel in Slack
> 2. Click the channel name at the top
> 3. Scroll to the bottom of the "About" panel
> 4. Copy the **Channel ID** (starts with C, e.g., `C07ABC123DE`)

Wait for the channel ID.

### Step 3: Define the Agents

Ask the user what agents they want. For each agent, collect:
- **Name**: Display name in Slack (e.g., "Bug Reporter")
- **Trigger**: The @mention trigger (e.g., `@BugReporter`)
- **Role description**: What this agent does (for its CLAUDE.md)

Example interaction:

> What agents do you want in this channel? For each, I need:
> - A **name** (shown in Slack)
> - A **trigger** (how users invoke it, e.g., `@BugReporter`)
> - A brief **role** description
>
> Example:
> 1. "Bug Reporter" — trigger `@BugReporter` — triages and reports bugs from logs
> 2. "Senior Developer" — trigger `@SeniorDev` — reviews code and suggests improvements

### Step 4: Register Each Agent

For each agent, register it as a group with a virtual JID. Run these steps programmatically:

#### 4a. Create the group folder

```bash
# Convert name to folder-safe format: lowercase, hyphens
# e.g., "Bug Reporter" → "slack_bug-reporter"
FOLDER="slack_$(echo "$AGENT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
mkdir -p "groups/$FOLDER/logs"
```

#### 4b. Write the agent's CLAUDE.md

Create `groups/$FOLDER/CLAUDE.md` with the agent's role instructions. Use this template:

```markdown
# {Agent Name}

You are {Agent Name}, a specialized agent in the {Channel Name} Slack channel.

## Your Role

{Role description from user}

## Communication

- Your messages appear in Slack as "{Agent Name}" with a colored icon
- You have `mcp__nanoclaw__send_message` to send messages while still working
- Keep messages concise — 2-4 sentences max per message
- Use `<internal>` tags for reasoning that shouldn't be sent to the user

## Formatting

Use Slack formatting (similar to markdown):
- *bold* (single asterisks)
- _italic_ (underscores)
- `code` (backticks)
- ```code blocks``` (triple backticks)
- • bullet points

## Memory

Your workspace is isolated — you have your own files, conversation history, and memory. Other agents in the channel cannot see your workspace.
```

#### 4c. Register the virtual JID

Use the SQLite database directly (since we're running from the host, not inside a container):

```bash
# Virtual JID format: slack:{CHANNEL_ID}::{agent-id}
VIRTUAL_JID="slack:${CHANNEL_ID}::${AGENT_ID}"

sqlite3 store/messages.db "INSERT OR REPLACE INTO registered_groups (jid, name, folder, trigger_pattern, added_at, requires_trigger, is_main) VALUES ('$VIRTUAL_JID', '$AGENT_NAME', '$FOLDER', '$TRIGGER', '$(date -u +%Y-%m-%dT%H:%M:%S.000Z)', 1, 0);"
```

Repeat for each agent.

### Step 5: Update the Main Agent's Instructions

Read `groups/main/CLAUDE.md` and add the Slack Agent Swarm section (see below in "Main Agent Instructions"). This tells the main agent how to create new swarm agents dynamically via conversation.

### Step 6: Rebuild and Restart

```bash
npm run build

# macOS:
launchctl kickstart -k gui/$(id -u)/com.nanoclaw

# Linux:
# systemctl --user restart nanoclaw
```

No container rebuild needed — the virtual JID routing is in the host process, not the container.

### Step 7: Test

Tell the user:

> Try it out! Send a message in your Slack channel:
>
> `@BugReporter what's the status?`
>
> You should see a response from "Bug Reporter" with a colored circle icon.
>
> Then try another agent:
>
> `@SeniorDev review the latest PR`
>
> Each agent responds independently with its own identity.
>
> **Dynamic creation**: You can also ask the main agent (via its trigger) to create new agents on the fly:
>
> `@Andy create a new agent called "QA Tester" that responds to @QATester and handles test case writing`

Check logs if something doesn't work:
```bash
tail -f logs/nanoclaw.log | grep -i "virtual\|swarm\|fan-out\|sendMessageAs"
```

## Main Agent Instructions

Add this section to `groups/main/CLAUDE.md`:

```markdown
## Slack Agent Swarm

You can create and manage independent agents that share a Slack channel. Each agent has its own identity, trigger, memory, and session.

### How Virtual JIDs Work

Each agent registers with a virtual JID: `slack:{CHANNEL_ID}::{agent-id}`

Example:
- `slack:C07ABC123DE::bug-reporter` → folder: `slack_bug-reporter`, trigger: `@BugReporter`
- `slack:C07ABC123DE::senior-dev` → folder: `slack_senior-dev`, trigger: `@SeniorDev`

### Creating a New Agent

When a user asks you to create a new agent in a Slack channel:

1. **Determine the channel JID** — check registered_groups for existing agents in the channel, or ask the user for the channel ID

2. **Pick an agent ID** — lowercase, hyphenated (e.g., `bug-reporter`, `qa-tester`)

3. **Register the group** using `mcp__nanoclaw__register_group`:
   ```
   jid: "slack:C07ABC123DE::qa-tester"
   name: "QA Tester"
   folder: "slack_qa-tester"
   trigger: "@QATester"
   ```

4. **Create the agent's CLAUDE.md** — write to `groups/slack_qa-tester/CLAUDE.md` with:
   - Role description
   - Communication guidelines (use send_message, keep messages short)
   - Formatting rules (Slack formatting, not markdown)
   - Any specific instructions from the user

5. **Confirm to the user** — tell them the trigger to use

### Listing Agents

Query the database for virtual JIDs:
```bash
sqlite3 /workspace/project/store/messages.db "
  SELECT jid, name, folder, trigger_pattern
  FROM registered_groups
  WHERE jid LIKE '%::%'
  ORDER BY added_at DESC;
"
```

### Removing an Agent

Delete from the database:
```bash
sqlite3 /workspace/project/store/messages.db "
  DELETE FROM registered_groups WHERE jid = 'slack:C07ABC123DE::agent-id';
"
```

The agent's folder and memory remain in `groups/` but it stops receiving messages.
```

## Architecture Notes

- Virtual JID aliasing is purely a routing/fan-out mechanism — no DB schema changes
- Each agent gets its own queue slot, session, and container — fully independent
- The global `TRIGGER_PATTERN` is NOT used for virtual JID agents — each uses its own trigger
- `sendMessageAs` uses Slack's `chat:write.customize` scope — same bot token, different display name
- Icons are deterministic per sender name (8 colored circles, hash-based assignment)
- Messages stored under the real JID — all agents see the same message history
- Agent cursors are independent — each tracks its own "last seen" position

## Troubleshooting

### Agent not responding to trigger

1. Check registration: `sqlite3 store/messages.db "SELECT * FROM registered_groups WHERE jid LIKE '%::%'"`
2. Verify the trigger pattern matches exactly (case-insensitive, word boundary)
3. Check logs: `grep "fan-out\|virtual\|trigger" logs/nanoclaw.log`

### Messages not being stored

Virtual JID groups need the Slack channel to store messages. Check that the Slack event handler recognizes the channel has virtual groups:
```bash
grep "hasGroup" logs/nanoclaw.log
```

### Agent responding but no custom identity

Verify `chat:write.customize` scope is on the bot token. Check Slack app settings at api.slack.com/apps.

### Multiple agents responding to same message

Each agent has its own trigger. If triggers overlap (e.g., `@Bug` matching `@BugReporter`), make triggers more specific.

## Removal

To remove swarm support for a channel:

1. Delete virtual JID entries: `sqlite3 store/messages.db "DELETE FROM registered_groups WHERE jid LIKE 'slack:CHANNEL_ID::%'"`
2. Agent folders in `groups/` can be kept or removed
3. Rebuild: `npm run build`
4. Restart: `launchctl kickstart -k gui/$(id -u)/com.nanoclaw` (macOS) or `systemctl --user restart nanoclaw` (Linux)

The core virtual JID routing code stays — it has zero impact when no virtual JIDs are registered.
