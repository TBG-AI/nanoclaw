---
name: f1-swe
description: F-1 SWE role — implement a Frontend feature from UX Designer artifacts. Handles mock API, tests, PostHog events, and PR. Auto-dispatchable. Use after UX Designer phase is complete or when user says "implement design", "F-1 SWE", or "build feature X from the UX doc".
user_invocable: true
---

# F-1 SWE (F-1 Phase 2 — Frontend Engineering) — x Auto

The **frontend engineer role** in an F-1 feature. Takes chosen design artifacts from the UX Designer and ships a working component with mock data, PostHog events, tests, and a PR.

**x Auto**: this skill can be dispatched by Andy automatically once the UX Designer phase is complete.

Plan spec: [../../../TBG-DOCS/plans/03-skills/f1-swe.md](../../../TBG-DOCS/plans/03-skills/f1-swe.md)
Feature type context: [../../../TBG-DOCS/plans/03-skills/feature-impl-types.md](../../../TBG-DOCS/plans/03-skills/feature-impl-types.md)
Upstream designer: [ux-designer](../ux-designer/SKILL.md)
Backend handoff contract: [../../../TBG-DOCS/plans/03-skills/api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md)

---

## Pre-flight: check for UX artifacts

Before doing anything, verify the upstream Phase 1 artifacts exist:

```
Frontend/docs/ux/<feature>/brief.md          ← required
Frontend/docs/ux/<feature>/candidates.md     ← required, must have a CHOSEN marker
Frontend/docs/ux/<feature>/kpi-test-plan.md  ← required
Frontend/docs/ux/<feature>/design.md         ← required
Frontend/docs/ux/<feature>/backend-contract.md  ← optional; presence = mock API needed
```

**If any required file is missing, REFUSE to start.** Respond:

> "No UX Designer artifacts found at `Frontend/docs/ux/<feature>/`. Run the `ux-designer` skill first to produce the brief, candidates, kpi-test-plan, and design. I'll wait."

**If `candidates.md` is missing the `CHOSEN:` marker, REFUSE to start.** Respond:

> "The UX Designer phase paused at human intervention and a candidate was never picked. Re-run the `ux-designer` skill and confirm which candidate to go with."

Read all five files completely before proceeding.

---

## Step 1 — Do you need a mock API?

Decision rule:
- **`backend-contract.md` exists** → **Yes, mock API needed**
- **`backend-contract.md` does NOT exist** → **No, pure UI** → skip to Step 2

### Step 1a — Mock API path (Yes branch)

1. **Open a parallel F-2 task in the relevant backend repo.** Use `wtnew` or the `new-task` skill. The branch name should match this F-1 branch (team convention — see `CLAUDE.md`). Point it at `Frontend/docs/ux/<feature>/backend-contract.md`. The F-2 SWE will produce a proper `AI_DOCS/api-impl/<feature>.md` per the [api-impl-md spec](../../../TBG-DOCS/plans/03-skills/api-impl-md.md).

2. **Define the mock.** The Frontend does **not** use MSW or a mocking library. Instead, follow the existing pattern:
   - **Zod schemas**: `Frontend/packages/shared/src/schemas/api/<domain>/<feature>.schema.ts`
   - **API client function**: `Frontend/packages/shared/src/api/routes/<domain>/<feature>.ts` — mirrors the pattern at `packages/shared/src/api/routes/bets/submission.ts` (axios via `postWithErrorTracking` / `getWithErrorTracking`, zod validate request & response)
   - **Data hook** (if React Query is used): `Frontend/packages/shared/src/hooks/<domain>/use<Feature>.ts`
   - **Mock toggle**: add a module-level `const USE_MOCK = __DEV__ && !process.env.REAL_API;` (or use an existing feature flag) that short-circuits the API call and returns fixture data shaped by the zod schema.
   - **Fixture**: colocate as `Frontend/packages/shared/src/api/routes/<domain>/<feature>.mock.ts` exporting a typed fixture.

3. During F-1 dev the Frontend hits the mock. Cut-over to the real API happens when the F-2 PR merges — remove the `USE_MOCK` branch at that point.

4. Document the swap plan in `Frontend/docs/ux/<feature>/design.md` under a new "Cut-over" heading so the F-2 SWE and reviewer know what to delete.

### Step 1b — Pure UI path (No branch)

Skip straight to Step 2. No backend work, no F-2 task, no mock.

---

## Step 2 — Define the test script (tests BEFORE impl)

**Write the tests first.** Do not jump to Step 3 before the test stubs exist.

> Note on the Frontend test infrastructure: the current Frontend monorepo has no jest / vitest / RTL config (verified — no test files exist in `apps/mobile`, `apps/web`, `packages/shared`, `packages/mobile-core`, `packages/mobile-ui`). The root `package.json` has `test:e2e` scripts pointing at `@tbg/web`, but there is no `playwright.config.*` yet either. **Treat this as a fresh setup:** if you introduce the first test, add the minimum config alongside it (jest + `@testing-library/react-native` for mobile, playwright for web) and mention it explicitly in the PR body so the reviewer can sign off on the choice.

### 2a — Component tests

- **Mobile**: `apps/mobile/src/<feature>/__tests__/<Component>.test.tsx` or colocated `<Component>.test.tsx` using `@testing-library/react-native`
- **Web**: `apps/web/src/components/features/<feature>/__tests__/<Component>.test.tsx` using `@testing-library/react`

Cover:
- Renders in default state
- Renders loading / empty / error states
- Prop variations called out in `design.md`
- Tap/click handlers fire the right callbacks

### 2b — Integration tests (only if Step 1 was "Yes")

- Hit the mock from Step 1a
- Happy path + 1-2 error cases (from `kpi-test-plan.md`)
- Assert zod validation works on the response

### 2c — E2E scenarios

Translate each E2E scenario from `kpi-test-plan.md` into a stub under:
- **Web**: `apps/web/e2e/<feature>.spec.ts` (playwright)
- **Mobile**: leave as a markdown TODO inside `Frontend/docs/ux/<feature>/e2e-todos.md` until mobile E2E infra (Detox/Maestro) is set up — call this out in the PR body.

It's OK to mark E2E tests `.skip` if the real API hasn't landed yet — but the stubs must exist so the F-2 PR knows what to un-skip.

### 2d — Run them

Run whatever test command exists for the package you're in:
```bash
pnpm --filter @tbg/mobile test    # if/when mobile tests exist
pnpm --filter @tbg/web test       # if/when web tests exist
pnpm test:e2e                     # root e2e
```

Every test you wrote must **fail first** (red phase) before Step 3. Record the red output before moving on.

---

## Step 3 — Implement the feature

Now write the component. Work in this order:

### 3a — Read theme tokens

- Import `useTheme` from `@mobile-core/config/ThemeContext` (mobile) or the web equivalent
- Use **only** token names. No raw hex. Reference:
  - `Frontend/packages/mobile-core/src/config/theme.ts` — `ThemeMode` + `ThemeColors` interface
  - `Frontend/packages/mobile-core/src/config/ThemeContext.tsx` — `useTheme()` hook
  - `Frontend/packages/brands/tbg/theme.ts` — brand overrides
  - `Frontend/packages/shared/src/constants/colors.ts` — `GRAYSCALE_PALETTE`

### 3b — Reuse existing components

Search `packages/mobile-ui/src/components/ui/` before writing anything new. Strong candidates to build on:
- `SlideUpSheet.tsx` — bottom sheet with drag-to-dismiss, subpage support, inline mode
- `BaseSlidePanel.tsx` — lower-level slide panel
- `ToggleActionButton.tsx` — toggle CTA
- `GradientText.tsx`, `GradientBorderCard.tsx` — gradient treatments
- `ShimmerSkeleton.tsx` — loading states
- `Text.tsx` — themed text primitive
- `StatusBadge.tsx`, `LiveBadge.tsx`, `StreakBadge.tsx` — badge patterns

### 3c — Wire animations

The Frontend uses **React Native's built-in `Animated` API** (verified: no `react-native-reanimated`, `moti`, or Lottie in `apps/mobile/package.json`). On web, `apps/web` uses **`motion`** (Motion One, package `motion@^12`) and `packages/shared` has `framer-motion@^11` as a peer.

Reuse the existing animation hooks before writing new ones:
- `packages/mobile-ui/src/hooks/useBottomSheetAnimation.ts`
- `packages/mobile-ui/src/hooks/useCenteredModalAnimation.ts`
- `packages/mobile-ui/src/hooks/useModalScaleAnimation.ts`
- `packages/mobile-ui/src/hooks/useModalDragDown.ts`

Every animation specced in `design.md` section "Animations" must map to a concrete `Animated.*` call or `motion` component. If the design wants something the built-in `Animated` API can't easily express, stop and discuss with the UX Designer before reaching for a new dep.

### 3d — Wire data

If Step 1 was "Yes": import the data hook from Step 1a. Keep the mock toggle comment visible so the reviewer can see the cut-over point.

### 3e — Run tests again (green phase)

Tests must now pass. If they don't, fix impl — don't relax the test.

---

## Step 4 — Set up PostHog events + experiments

### 4a — Register events

**Verified events file**: `Frontend/packages/shared/src/posthog/constants/events.ts` — exports `POSTHOG_EVENTS` as an enum. Each entry has an inline `// props: { ... }` comment documenting shape.

For every event in `kpi-test-plan.md`:
1. Check `TBG-DOCS/event-registry.json` — does an event already exist that fits?
2. If not, add a new member to the `POSTHOG_EVENTS` enum in `events.ts`, with a props comment matching the kpi-test-plan table
3. Also add the event to `TBG-DOCS/event-registry.json` per the [TBG-DOCS README](../../../TBG-DOCS/CLAUDE.md) "How to: Add a new PostHog event":
   ```json
   { "name": "FEATURE_X_OPENED", "event": "feature_x_opened", "props": ["source", "entry_point"], "legacy": null }
   ```

### 4b — Fire events

`trackEvent` is exported from `@shared/utils/analytics` (verified path: `Frontend/packages/shared/src/utils/analytics.ts`). Usage:

```tsx
import { trackEvent } from '@shared/utils/analytics';
import { POSTHOG_EVENTS } from '@shared/posthog';

// ...
trackEvent(POSTHOG_EVENTS.FEATURE_X_OPENED, { source: 'pill_tap', entry_point: 'home' });
```

Wire a `trackEvent` call at every interaction point called out in `kpi-test-plan.md`.

### 4c — Feature flag

From `kpi-test-plan.md`: the flag name and default. Register it:
- `Frontend/packages/shared/src/posthog/constants/featureFlags.ts` — add the constant
- Read with `useFeatureFlag(...)` from `@shared/posthog` at the component entry point
- Gate the feature with an early return (don't render stale fallback — that breaks PostHog attribution)

### 4d — Experiments (if A/B called for)

If `kpi-test-plan.md` specifies A/B variants, use `useFeatureFlagVariant` from `@shared/posthog` and register variants in the PostHog dashboard.

---

## Step 5 — Make the PR

### 5a — Checklist before opening

- [ ] Tests written before impl (Step 2 before Step 3) — you have a red-before-green record
- [ ] Tests pass locally
- [ ] No hardcoded colors/spacing — every value goes through `theme.*` tokens
- [ ] PostHog events added to enum + registry + wired with `trackEvent`
- [ ] Feature flag registered and gating the component
- [ ] If mock API was used: `USE_MOCK` toggle clearly marked and "Cut-over" section in `design.md` explains the swap
- [ ] `backend-contract.md` linked to the F-2 task if applicable
- [ ] No changes in files outside the feature scope (use `git status` to check)

### 5b — PR body template

```markdown
**Feature type**: F-1 SWE

**Breaking**: no

**DB migration**: no

**Linked UX docs**:
- `Frontend/docs/ux/<feature>/brief.md`
- `Frontend/docs/ux/<feature>/candidates.md`
- `Frontend/docs/ux/<feature>/design.md`
- `Frontend/docs/ux/<feature>/kpi-test-plan.md`
- `Frontend/docs/ux/<feature>/backend-contract.md` (if mock API)

**Mock API**: yes / no
**Linked F-2 task**: #<number> — <repo>/<branch>  (if mock API)

**PostHog events added**:
- `feature_x_opened` — props: `{ source, entry_point }`
- `feature_x_action_tapped` — props: `{ variant, position }`

**Feature flag**: `feature_x_enabled` (default: off, rollout 10→50→100)

**Test coverage**:
- Component tests: N cases
- Integration tests: N cases (vs mock)
- E2E: stubs present, skipped until F-2 lands

**Theme tokens touched**: `theme.accent`, `theme.ctaButtonDefaultBackground`, ...

**New components**: `<Component>.tsx` at `...`
**Reused components**: `SlideUpSheet`, `ShimmerSkeleton`, ...
**Animation**: `Animated.spring` via `useBottomSheetAnimation` hook

**Manual test notes**:
- Tested on iOS simulator / Android / web (which ones?)
- Screen sizes tested
```

### 5c — Hand off to reviewer

Open the PR, then invoke the [`pr-review`](../pr-review/SKILL.md) skill to kick off the review (or ping a human reviewer).

**Do not merge yourself.** Wait for review.

---

## Cross-references

- [ux-designer](../ux-designer/SKILL.md) — upstream phase (provides inputs)
- [pr-review](../pr-review/SKILL.md) — reviewer skill
- [feature-impl-types.md](../../../TBG-DOCS/plans/03-skills/feature-impl-types.md) — F-1 definition
- [api-impl-md.md](../../../TBG-DOCS/plans/03-skills/api-impl-md.md) — F-2 handoff contract format
- [f1-swe plan spec](../../../TBG-DOCS/plans/03-skills/f1-swe.md) — the plan this skill implements
- [TBG-DOCS CLAUDE.md](../../../TBG-DOCS/CLAUDE.md) — "How to: Add a new PostHog event"

---

## Acceptance criteria (self-check before PR)

- [ ] All five UX artifacts existed and were read before any code was touched
- [ ] Refused to start if artifacts were missing / no CHOSEN marker
- [ ] Step 1 "mock API?" decision was made explicitly (yes → F-2 task opened; no → pure UI)
- [ ] Step 2 tests were written before Step 3 impl (red phase evidence)
- [ ] Step 3 impl uses only theme tokens from `packages/mobile-core/src/config/theme.ts`
- [ ] Step 3 animations use `Animated` (mobile) or `motion` (web) — no new animation library added without discussion
- [ ] Step 4 events added to BOTH `packages/shared/src/posthog/constants/events.ts` AND `TBG-DOCS/event-registry.json`
- [ ] Step 4 events fired via `trackEvent` from `@shared/utils/analytics`
- [ ] Step 4 feature flag registered in `featureFlags.ts` and gating the component
- [ ] Step 5 PR body has every field filled in
- [ ] Handed off to `pr-review` — did not self-merge
- [ ] **Instrumentation**: see checklist below

## Instrumentation checklist (MANDATORY)

The frontend doesn't hit Grafana Loki directly, but it's part of the end-to-end observability story. When a user reports a bug, BugReporter + BugFixer need to correlate the frontend event with backend logs. That only works if F-1 features emit structured events and propagate request IDs.

- [ ] **PostHog events** for every significant user action, with props: `source`, `variant`, `position`, and any domain-specific context. Event names match `TBG-DOCS/event-registry.json`.
- [ ] **Error boundaries** wrap new screens/components. Errors are sent to Sentry (or equivalent) with user_id + feature flag state attached.
- [ ] **Network calls forward correlation headers**: if the feature makes HTTP calls to Backend-Server, the existing `apiClient` wrapper (which adds `X-Request-ID` and related headers) is used — don't `fetch()` directly, don't bypass the wrapper.
- [ ] **Loading + error states are distinguishable**: users can tell the difference between "still loading", "failed to load", and "empty state". Without this, bug reports are ambiguous.
- [ ] **Analytics for the "sad paths"**: emit events for error states too (e.g., `feature_x_error_shown` with props `{ error_code, retry_count }`). These let the team measure what's breaking for real users, not just what's in Sentry.

### Why each rule exists

- **PostHog events** — the primary signal for "is the feature being used" and "where are users dropping off". Without them, you're flying blind on adoption.
- **Error boundaries + Sentry** — catches crashes that happen below the feature-owning component. Without them, a Frontend crash looks like "app frozen" to BugReporter.
- **`apiClient` wrapper** — forwards `X-Request-ID` so backend logs can be correlated to the user's session. Bypassing it means bug reports arrive without a request_id.
- **Distinguishable states** — users who see "nothing happened" when they meant "loading failed" file vague bug reports that take 2x longer to triage.
- **Sad-path events** — Sentry catches exceptions, but NOT "user saw an error message we intentionally showed". Product-level error states need their own events.

See [`.claude/skills/pr-review/SKILL.md` Step 2.5](../pr-review/SKILL.md) for the PR-review side of these checks.
