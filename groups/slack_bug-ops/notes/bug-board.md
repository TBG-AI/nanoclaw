# Bug Board — last updated 2026-04-10 UTC

| # | Severity | Error / Endpoint | Status | Owner | Issue | PR | Last action |
|---|----------|-----------------|--------|-------|-------|----|-------------|
| 1 | CRITICAL | Live status false for live games (Kalshi game_id mapping mismatch) | open-no-fixer | — | Backend-Odds #86 | — | BugOps dispatch x2 04-10, @BugFixer not yet assigned |
| 2 | HIGH | Live override per-pod: PUT/GET can hit different replicas | open-no-fixer | — | Backend-Odds #85 | — | BugOps dispatch x2 04-10, @BugFixer not yet assigned |
| 3 | MEDIUM | 504 timeout /transactions_v1/redeem-daily-bonus (external svc) | open-no-fixer | — | Backend-Server #493 | — | F3-SWE recommended 04-10, not yet picked up |
| 4 | MEDIUM | Kalshi ticker parser Ligue 1 markets → OTHER (hotfix applied) | hotfix-deployed | — | Backend-Odds #87 | — | Regex hotfix committed, long-term refactor open |
| 5 | LOW | OddsMicroservice 422 /odds/get_parlay_odds (schema mismatch) | open-no-fixer | — | Backend-Odds #75 | — | BugOps dispatch x2 04-10, @BugFixer not yet assigned |

## Notes
- Bug #1: Kalshi match resolver writes live_odds to different game_id than UUID mapping reads → live bets broken for affected games. Code-bug → @BugFixer
- Bug #2: LiveBettingPolicy._force_live is in-memory, not shared across ECS replicas; Redis-backed fix recommended. Code-bug → @BugFixer
- Bug #3: Pattern matches #481 (KYC Didit API); external service called without explicit HTTP timeout → F3-SWE investigation needed
- Bug #4: Hotfix (regex KX[A-Z0-9]+) already committed. Issue #87 still open for architectural long-term fix (unified parser)
- Bug #5: 9 occurrences of 422 from Backend-Odds at /odds/get_parlay_odds; schema mismatch between services → @BugFixer
- ⚠ Bugs #1, #2, #5 have been dispatched to @BugFixer twice with no uptake — consider manual assignment or human review
