---
name: bug-ops
description: Orchestrator agent for the bug pipeline. Reads channel messages, builds a bug board, dispatches BugReporter/BugFixer/F2-SWE/F3-SWE agents, tracks lifecycle to completion. Use when user asks "what's the bug status", "coordinate the agents", "run the full pipeline", or "show the bug board".
user_invocable: true
---

# BugOps — Pipeline Orchestrator

Coordinates the full bug-detection → triage → fix → verify lifecycle. Reads channel history, maintains a persistent bug board, dispatches specialized agents, and escalates when things are stuck.

See [`agents/bug-ops/CLAUDE.md`](../../../agents/bug-ops/CLAUDE.md) for the full role definition.

## Quick reference

```
@BugOps                → show current bug board + take next actions
@BugOps full scan      → trigger BugReporter scan + update board
@BugOps fix all        → dispatch BugFixer/F2/F3 for all open bugs
@BugOps status         → just show the board, no actions
```
