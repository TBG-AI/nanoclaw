---
name: explain-diagram
description: When explaining knowledge, flows, architectures, lifecycles, or relationships that have structure, render a diagram. Supports ASCII arrow diagrams (inline) and standalone HTML files using Mermaid.js (previewable in a browser). Use for "explain how X works", "show me the flow", "diagram X", "knowledge graph of X", "architecture of X", or whenever an explanation benefits from a visual.
user_invocable: true
---

# Explain-Diagram

A visualization skill for explanations. When the thing being explained has **structure** — a flow, a pipeline, a hierarchy, a lifecycle, a dependency graph, a state machine, a decision tree — render it, don't just describe it.

## When to activate

Activate automatically when the user asks to understand something with structure, e.g.:
- "explain how X works"
- "what's the flow of X"
- "show me the architecture"
- "diagram X" / "draw X" / "visualize X"
- "knowledge graph of X"
- "what are the relationships between X, Y, Z"
- "walk me through the lifecycle"

Also activate on your own judgment — if you notice your answer is going to describe 4+ things with arrows between them, switch to this skill **before** writing the prose version.

## Two output modes

### Mode 1: **ASCII arrow diagram** (default)

Inline in the chat response, in a fenced code block. Good for:
- Quick reference
- Markdown docs
- Anything ≤ ~8 nodes with clean linear/branching flow
- When the user is in a terminal and won't open a browser

**Box-drawing conventions** — use these consistently:

| Purpose | Chars |
|---|---|
| Horizontal line | `─` |
| Vertical line | `│` |
| Down-arrow | `▼` |
| Right-arrow | `→` |
| T-junctions | `┬` `┴` `├` `┤` |
| Corners | `┌` `┐` `└` `┘` |
| Grouping | `( parens )` for annotations, `[brackets]` for node labels optional |

**Layout rules**:
- Top-to-bottom primary flow
- Branches fan out with `┬` / `┴` junctions, not crossing lines
- Annotations in parens on the arrow line: `──(markdown artifacts)──`
- Use blank lines around the diagram so it breathes
- If a node is a skill, write it with the leading slash: `/f1-swe`

Reference example (the TBG feature lifecycle — keep this style):

```
idea
  │
  ▼
/ux-designer   ──(markdown artifacts in Frontend/docs/ux/)──┐
                                                             │
                                                             ▼
                                                         /f1-swe   (frontend)
                                                             │
               needs backend?                                │
                  ┌──────────────┬─────────────┐             │
                  ▼              ▼             ▼             │
             /f2-swe         /f3-swe        (none)           │
           (TBG-only)     (third-party)                      │
                  │              │                           │
                  └──────────────┴───────────────────────────┘
                                 │
                                 ▼
                           /pr-review
                                 │
                                 ▼
                             /deploy
```

### Mode 2: **Standalone HTML** (on request, or when ASCII can't carry it)

Generate a single self-contained HTML file the user can open in a browser. Use **Mermaid.js** via CDN — no build step, no dependencies to install. Good for:
- Dense graphs (> 8 nodes, cycles, many crossings)
- Anything the user will share or keep as a reference
- When the user explicitly says "make it html" / "I want to check it" / "preview"
- When the explanation mixes different relationship types (sequence + ERD + flow)

**File location**: `outputs/YYYY-MM-DD-diagram-<slug>.html` — lands in the audit trail alongside the other dated outputs. Slug = kebab-case of the topic (e.g., `tbg-feature-lifecycle`, `wiki-three-layer-architecture`).

**After writing**, tell the user the exact path and suggest:
```
open outputs/YYYY-MM-DD-diagram-<slug>.html
```

## HTML template

Use this as the starting point. It's a single file, no build, auto-renders Mermaid from a CDN, and works offline once loaded.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{{TITLE}}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    :root { color-scheme: light dark; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      max-width: 1100px;
      margin: 2rem auto;
      padding: 0 1.5rem;
      line-height: 1.55;
    }
    header { border-bottom: 1px solid #8884; padding-bottom: 0.75rem; margin-bottom: 1.5rem; }
    h1 { margin: 0 0 0.25rem; font-size: 1.4rem; }
    .meta { font-size: 0.85rem; opacity: 0.7; }
    .diagram {
      padding: 1.5rem;
      border: 1px solid #8884;
      border-radius: 8px;
      margin: 1.5rem 0;
      overflow-x: auto;
    }
    h2 { font-size: 1.1rem; margin-top: 2rem; }
    footer { font-size: 0.8rem; opacity: 0.6; margin-top: 3rem; border-top: 1px solid #8884; padding-top: 0.75rem; }
    code { background: #8882; padding: 0.1em 0.4em; border-radius: 3px; }
  </style>
</head>
<body>
  <header>
    <h1>{{TITLE}}</h1>
    <div class="meta">Generated {{DATE}} · {{TOPIC}}</div>
  </header>

  <p>{{ONE_PARAGRAPH_SUMMARY}}</p>

  <div class="diagram">
    <pre class="mermaid">
{{MERMAID_SOURCE}}
    </pre>
  </div>

  <h2>Notes</h2>
  <ul>
    {{BULLETED_NOTES_AS_LI}}
  </ul>

  <footer>
    Rendered with Mermaid.js · Part of the <code>outputs/</code> audit trail · See <a href="../CLAUDE.md">CLAUDE.md §9</a>.
  </footer>

  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'default', securityLevel: 'loose' });
  </script>
</body>
</html>
```

## Mermaid diagram-type cheatsheet

Pick the right Mermaid type for the explanation:

| Explaining… | Mermaid type | When |
|---|---|---|
| A pipeline / workflow / decision tree | `flowchart TD` (top-down) or `flowchart LR` (left-right) | Default choice |
| An API call / actor interaction | `sequenceDiagram` | "who calls whom and when" |
| A DB schema / domain model | `erDiagram` | Tables + relationships |
| A state machine | `stateDiagram-v2` | Modes / transitions |
| A dependency tree / org chart | `flowchart TD` with subgraphs | Hierarchy with grouping |
| A Gantt / timeline | `gantt` | Scheduling, phases over time |
| A class hierarchy | `classDiagram` | OOP structure |
| Package / subsystem layout | `flowchart LR` with `subgraph` blocks | Architecture diagrams |

**Flowchart node shape cheatsheet**:
- `A[Rectangle]` — default process
- `A(Rounded)` — start/soft step
- `A((Circle))` — terminal / entry point
- `A{Diamond}` — decision
- `A[/Parallelogram/]` — input/output
- `A[(Cylinder)]` — database

**Edges**:
- `A --> B` — solid arrow
- `A -.-> B` — dotted (weaker / async)
- `A ==> B` — thick (primary path)
- `A -- label --> B` — labeled edge

## Inputs the skill asks for

1. **Topic** — what to diagram (if not obvious from context)
2. **Mode** — `ascii` | `html` | `both`. Default: `ascii` if ≤ 8 nodes, `both` otherwise. Always honor explicit user choice.
3. **Audience** (optional) — if the user is non-technical, prefer simpler shapes and fewer branches; if they're an engineer, dense is fine.

Don't interrogate — infer from context and proceed. Only ask if you truly can't tell.

## Workflow

1. **Extract structure** — what are the nodes? what are the edges? what's the primary flow direction? are there branches, cycles, or grouping?
2. **Pick a form** — tree / DAG / sequence / state / ER / hierarchy. This determines both the ASCII layout and the Mermaid type.
3. **Render ASCII first** — even if you're also generating HTML, do the ASCII pass first. It forces you to simplify and catch missing nodes before they end up in a prettier format.
4. **If HTML requested**:
   a. Compute slug + date: `outputs/$(date +%Y-%m-%d)-diagram-<slug>.html`
   b. Fill the template (title, one-paragraph summary, mermaid source, bullet notes)
   c. Write the file
   d. Tell the user: "Open with `open <path>`"
5. **Explain the diagram in prose** — one short paragraph after the diagram. Not a recap; highlight the *non-obvious* relationship (the thing the diagram makes visible that text wouldn't).

## Hard rules (safety)

- **Don't fabricate nodes.** If you don't know whether two things connect, say so in the prose — don't draw a confident edge.
- **Don't over-draw.** If the explanation is 3 linear steps, use a sentence, not a diagram.
- **Dense ≠ good.** If Mermaid produces a hairball, simplify: group with `subgraph`, or split into multiple diagrams.
- **No external images.** Never embed remote images or iframes in the HTML beyond the Mermaid CDN script. One file, self-contained.
- **Never overwrite an existing dated output** — if `outputs/2026-04-09-diagram-X.html` exists, append a suffix (`-v2`, or a short hash). Audit trail stays append-only.

## Where diagrams live

Generated HTML files go under [`outputs/`](../../../outputs/README.md) and are part of the append-only audit trail (Karpathy LLM Wiki pattern — see [`CLAUDE.md` §9](../../../CLAUDE.md)). ASCII diagrams live wherever they're useful (chat, PR bodies, `TBG-DOCS/plans/*`).

## Reference diagrams to style-match

The repo already has one canonical ASCII flow to match style against — the TBG feature lifecycle shown at the top of this file. Keep other diagrams in the same visual register (same arrow chars, same annotation style, same spacing).
