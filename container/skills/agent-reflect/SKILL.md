---
name: agent-reflect
description: Self-improvement loop for the bug-agents (and other recurring skills). Reviews scan-history.md, fix-history.md, outputs/*.md, and recent issues/PRs to identify what went well, what went poorly, and what should change. Proposes edits to skill definitions, agent CLAUDE.md files, notes/, and the handoff contract based on observed outcomes. Use after N completed cycles or when the user says "reflect", "self-improve", "learn from history", "what should the agents do differently", or "review agent performance".
user_invocable: true
---

# Agent Reflect

Meta-skill that reviews the recent history of agent runs and proposes concrete improvements to skills, prompts, notes, and the handoff contract. Implements the **learning loop** for the Karpathy LLM Wiki pattern: outcomes → dated audit reports → reflection → updated skills/agents → better outcomes.

> **What this skill is NOT**:
> - Not a chat assistant — it produces concrete file edits (or proposals for edits)
> - Not a substitute for human review — it proposes, you approve
> - Not ad-hoc "improvements" — it MUST be grounded in observed evidence from the history files

## The learning loop

```
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │    scheduled run      outcome             reflection     │
  │    ────────────  ───▶  ─────────  ───▶   ────────────    │
  │      /bug-pipeline    outputs/YYYY-     /agent-reflect   │
  │      (or live)        MM-DD-bugrun      reviews N runs   │
  │                       scan-history.md                    │
  │                       fix-history.md                     │
  │                                             │            │
  │                                             ▼            │
  │                                      proposed changes    │
  │                                      to skills/agents/   │
  │                                      notes/              │
  │                                             │            │
  │                                             ▼            │
  │                                      human reviews       │
  │                                      and merges          │
  │                                             │            │
  └─────────────────────────────────────────────┘            │
         ▲                                                   │
         └───────────────── better next run ─────────────────┘
```

## When to run

- **After N completed cycles**: e.g., every 5 BugReporter runs, every 10 PR reviews
- **After an incident**: when a bug escaped the pipeline, run reflect to find why
- **When the user says so**: "reflect", "self-improve", "what's working", "what should we change"
- **As part of `/daily-refactor`**: the daily scheduled cleanup can invoke agent-reflect once per week

## Inputs the skill asks for

1. **Scope** — which agents/skills to reflect on. Options: `bug-agents` (default), `swe-roles`, `all`
2. **Window** — how far back to look. Default: last 10 outputs/ reports OR 30 days, whichever is shorter
3. **Mode** — `analyze-only` (default, writes a report) | `propose-edits` (writes diffs) | `apply-edits` (requires explicit human confirmation at each change)

Don't interrogate. Default to `bug-agents`, 30 days, `analyze-only`.

## The 5 reflection questions

For every run this skill reviews, answer these concretely:

1. **What was the goal?** (from the run's input — scan window, issue N, etc.)
2. **What was the outcome?** (issues created, PRs opened, bugs fixed, errors closed)
3. **What went well?** (specific things that worked — not "it was fine")
4. **What went poorly?** (specific failures, gaps, wrong calls — not "could be better")
5. **What would you do differently next time?** (the proposal — what rule/prompt/tool should change)

The output of these 5 questions gets appended to the agent's notes/ directory as dated reflections, and the "what would you do differently" answers become proposed edits.

## Workflow

### Phase 1 — Gather evidence

```bash
# Read the history files
cat agents/bug-reporter/notes/scan-history.md 2>/dev/null
cat agents/bug-fixer/notes/fix-history.md 2>/dev/null

# Read recent outputs
ls -t outputs/ | head -10
# Focus on: *-bugrun-*.md, *-dryrun-*.md, *-debug-*.md, *-pr-review-*.md

# Read recent closed GitHub issues (BugReporter → BugFixer loop)
gh issue list --repo TBG-AI/Backend-Server --state closed --limit 20 \
    --label bug-fix --json number,title,closedAt,body,comments
gh issue list --repo TBG-AI/Backend-Odds --state closed --limit 20 \
    --label bug-fix --json number,title,closedAt,body,comments

# Read recent merged PRs that came from BugFixer
gh pr list --repo TBG-AI/Backend-Server --state merged --limit 20 \
    --label bug-fix --json number,title,mergedAt,body
```

### Phase 2 — Score each run against the 5 questions

For each run, produce a row:

| run | goal | outcome | went well | went poorly | would do differently |
|---|---|---|---|---|---|
| 2026-04-09-bugrun-48h | find bugs in 48h | 3 real + 3 gaps | trace_id reproduction for #1 worked | Loki label filter broken; 41% entries missing trace_id | propose: trace_id fix in app.py:412 |

### Phase 3 — Aggregate patterns

Look for recurring failures across multiple runs:

- **Same failure mode 2+ times** → propose a skill change to prevent it
- **Same success pattern 3+ times** → codify it as an explicit rule in the skill
- **Evidence of drift** (e.g., "contract §A fields missing from issues" seen twice) → propose a validator

### Phase 4 — Generate proposals

For each pattern found, write a **proposal** with:
- **Observation**: what the evidence shows (with specific file:line citations)
- **Hypothesis**: why this is happening
- **Proposed change**: specific diff to skill/agent/note/contract file
- **Expected outcome**: how this change would prevent/improve the pattern
- **Risk**: what could go wrong with the change

Proposals go to `outputs/YYYY-MM-DD-reflection-<scope>.md`.

### Phase 5 — Apply (only with explicit authorization)

If `mode=apply-edits`, walk the user through each proposal and ask for approval before writing each file. Never batch-apply. Never silently change skill behavior.

### Phase 6 — Update the agent's memory

Append a dated reflection entry to the relevant `notes/`:

- For BugReporter: append to `agents/bug-reporter/notes/scan-history.md` under a `## Reflection` header
- For BugFixer: append to `agents/bug-fixer/notes/fix-history.md`
- For skills: add a commit log entry with `reflection:` prefix

## What to look for (the checklist)

The evidence-based prompts that this skill uses when reading history:

### For BugReporter
- [ ] Are severity classifications matching what a human would call critical/high/medium/low?
- [ ] Are dedup rules producing duplicate issues in practice?
- [ ] Are scan durations growing over time (indicator of slow Grafana queries)?
- [ ] Are any error types consistently being missed by the text-search filter?
- [ ] Is the Slack summary actionable, or is it noise?

### For BugFixer
- [ ] Are fixes being verified post-deploy (§C loop)?
- [ ] Are there issues that get closed but later reopened with `suspected-regression`?
- [ ] Are PRs consistently showing test-first commit order?
- [ ] How often does BugFixer reject an issue as incomplete (§D violation)?
- [ ] What root-cause categories are most common? (informs where to invest prevention effort)

### For SWE skills (f1-swe, f2-swe, f3-swe)
- [ ] Are the instrumentation checklists being caught by `/pr-review` or by post-deploy errors?
- [ ] Are any checklist items being ignored consistently (signal that the rule is wrong or unclear)?
- [ ] Are flow registry drift failures happening in review or at pre-commit?

### For pr-review
- [ ] What percentage of PRs have all §2.5 observability checks satisfied on first submission?
- [ ] What percentage get fixed-by-reviewer vs sent-back-to-author?
- [ ] Are reviewers catching things not in the checklist? (signal to add them)

## Hard rules

1. **Every proposal MUST cite specific evidence.** "Based on the reflection, I propose..." is banned. "Based on outputs/2026-04-09-bugrun-48h.md finding #2 (trace_ids missing on 100% of HTTPException entries), I propose..." is the format.
2. **Never change code in source repos.** This skill only edits `.claude/skills/`, `agents/`, `outputs/`, `TBG-DOCS/plans/`, and `CLAUDE.md`.
3. **Propose, don't apply, without authorization.** `analyze-only` default mode never writes outside `outputs/`.
4. **One reflection run per week per scope.** Avoid over-reflecting — too much change churn is worse than too little. Skip if fewer than N new runs happened since the last reflection.
5. **Flag patterns that call for human intervention**, don't try to fix them with skill edits. E.g., "BugReporter misclassified 3 CRITICAL issues as LOW" is not a skill fix — it's a severity-rubric discussion that needs a human.

## Example output (what the user sees)

```
# Reflection run — bug-agents — 2026-04-15

Reviewed: 7 runs from 2026-04-09 to 2026-04-14
- 4 BugReporter scans
- 3 BugFixer cycles (1 escalated to human, 2 verified post-deploy)

## What's working ✓
- Trace reproduction via /debug-logs trace — 100% success on issues with trace_ids
- Handoff §A frontmatter — no incomplete issues rejected by BugFixer
- Test-first discipline — all 3 PRs had correct commit order

## What's not working ✗
1. **HTTPException-wrapped errors have no trace_id** (seen in 3/4 scans)
   Evidence: outputs/2026-04-09-bugrun-48h.md Gap A, outputs/2026-04-11-bugrun-24h.md Gap A, outputs/2026-04-13-bugrun-24h.md Gap A
   → Proposal: add a pre-flight note to bug-fixer/CLAUDE.md explaining the fallback workflow ('use /debug-logs endpoint "..." instead')

2. **BugReporter severity misclassified /info/get_league_games as MEDIUM, human upgraded to HIGH** (seen 2x)
   Evidence: issue #5342 (manual label change from medium→high), issue #5389 (same)
   → Proposal: add /info/get_league_games to the explicit "known hotspots" list in notes/grafana-queries.md so future scans auto-classify it HIGH

## What should change (proposals)

[Each proposal as a diff block — user can review and apply]

## What should NOT change
- Handoff contract §A: no observed violations, keep as-is
- Scan workflow phases: all 9 phases executed cleanly on every run
```

## Integration with existing skills

- **`/daily-refactor`**: add a weekly "reflect" call as part of its scheduled run
- **`/bug-pipeline`**: at the end of each run, note "see `/agent-reflect` after N more runs to review outcomes"
- **`/pr-review`**: reference reflection output — reviewer can check "what did /agent-reflect flag as common in recent PRs?"

## Related

- [`agents/bug-reporter/notes/scan-history.md`](../../../agents/bug-reporter/notes/scan-history.md) — input source
- [`agents/bug-fixer/notes/fix-history.md`](../../../agents/bug-fixer/notes/fix-history.md) — input source
- [`outputs/`](../../../outputs/README.md) — dated audit reports (primary evidence)
- [`log.md`](../../../log.md) — operation log (secondary evidence)
- [`CLAUDE.md`](../../../CLAUDE.md) §9 "Maintenance workflow" — where this fits in the overall schema
