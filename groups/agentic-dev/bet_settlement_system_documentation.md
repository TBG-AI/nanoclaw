# Bet Settlement System - Complete Flow Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Settlement Architecture](#settlement-architecture)
3. [Leg Evaluation Logic](#leg-evaluation-logic)
4. [Bet Outcome Calculation](#bet-outcome-calculation)
5. [Partial Settlement & Void Handling](#partial-settlement--void-handling)
6. [Payout Calculation Formulas](#payout-calculation-formulas)
7. [Backed Bet Settlement](#backed-bet-settlement)
8. [Scheduled Jobs](#scheduled-jobs)
9. [Edge Cases & Tie-Breaking](#edge-cases--tie-breaking)
10. [Code References](#code-references)

---

## System Overview

The bet settlement system processes sports betting outcomes through a **two-pass verification workflow** followed by settlement:

1. **Draft Pass** - Initial verification immediately after match completion (sets `draft_hit`)
2. **Confirmation Pass** - Final verification after policy window (sets `confirmed_hit`)
3. **Settlement** - Idempotent payout/refund processing (marks `settled_at`)

### Key Design Principles

- **Two-Phase Settlement**: Draft provides quick feedback; confirmation ensures data accuracy
- **Idempotent Operations**: Safe to retry without double-processing
- **Transaction Isolation**: Uses `REPEATABLE READ` for consistent snapshots
- **Domain-Driven Design**: Pure business logic in domain layer, orchestration in application layer

---

## Settlement Architecture

### Service Layers

```
┌─────────────────────────────────────────────────────────┐
│           Scheduled Job (bet_verification.py)           │
│  - Runs every minute                                    │
│  - Transaction coordination                             │
│  - Notification triggering                              │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│    BetVerificationOrchestratorService                   │
│  - Coordinates workflow                                 │
│  - Delegates to specialized services                    │
└──────┬─────────┬─────────────┬──────────────────────────┘
       │         │              │
       ▼         ▼              ▼
┌──────────┐ ┌─────────┐ ┌──────────────┐
│   Leg    │ │   Bet   │ │     Bet      │
│Verifica- │ │Evalua-  │ │   Result     │
│  tion    │ │ tion    │ │   Service    │
└────┬─────┘ └────┬────┘ └──────┬───────┘
     │            │              │
     ▼            ▼              ▼
┌─────────────────────────────────┐
│      Domain Layer               │
│  - LegEvaluator                 │
│  - BetEvaluator                 │
│  - PayoutCalculator             │
│  - VoidPolicy                   │
└─────────────────────────────────┘
```

### File Structure

**Application Services** (`/backend_server/application/services/bets/`)
- `bet_verification_orchestrator_service.py` - Main orchestrator
- `leg_verification_service.py` - Leg evaluation coordination
- `bet_evaluation_service.py` - Bet-level aggregation
- `bet_result_service.py` - Settlement processing (payouts/refunds)
- `bet_backing_service.py` - Backed bet handling

**Domain Services** (`/backend_server/domain/bet/evaluation/`)
- `leg_evaluator.py` - Pure leg evaluation logic
- `bet_evaluator.py` - Pure bet aggregation logic
- `payout_calculator.py` - Pure payout math
- `void_policy.py` - Void rules & timing
- `evaluation_result.py` - Value objects

**Scheduled Jobs** (`/backend_server/schedule/`)
- `bet_verification.py` - Main settlement job
- `tournaments/settle_tournaments.py` - Tournament settlement

---

## Leg Evaluation Logic

### Leg Types & Evaluation Methods

#### 1. Player Props (PlayerPropLeg)
Bets on player performance (e.g., "Player X to score 2+ goals")

**Evaluation Logic** (from `leg_evaluator.py:252-288`):
```python
def _evaluate_player_prop(self, leg, context):
    # Check if player is in starting lineup
    is_starter = context._is_player_starter(leg.player_id)

    if is_starter is None:
        return LegEvaluationResult.voided(VoidReason.PLAYER_NOT_IN_LINEUP)

    if not is_starter:
        return LegEvaluationResult.voided(VoidReason.PLAYER_NOT_STARTER)

    # Count occurrences from match events
    num_occ = context.count_player_actions(
        player_id=leg.player_id,
        action=leg.action,
        zones=leg.zones,
        zone_filter_func=zone_filter_func,
    )

    # Evaluate: over/under threshold
    is_hit = leg.evaluate_occurrence_bet()  # Uses num_occ vs line
    return LegEvaluationResult.from_hit_value(is_hit)
```

**Win Condition**:
- `is_over=True`: `num_occ > line` → HIT
- `is_over=False`: `num_occ < line` → HIT

**Void Conditions**:
- Player not in lineup
- Player not a starter (substitutes void the bet)

#### 2. Team Action Props (ZATLeg)
Team-level zonally-filtered actions (e.g., "Team X to have 5+ shots in attacking third")

**Evaluation Logic** (from `leg_evaluator.py:294-318`):
```python
def _evaluate_zat(self, leg, context):
    # Count team actions (no void based on lineup)
    num_occ = context.count_team_actions(
        team_id=leg.team_id,
        action=leg.action,
        zones=leg.zones,
        zone_filter_func=zone_filter_func,
    )

    is_hit = leg.evaluate_occurrence_bet()
    return LegEvaluationResult.from_hit_value(is_hit)
```

**Win Condition**: Same over/under logic as player props

**Void Conditions**: None (team props never void based on lineup)

#### 3. Team Props (TeamPropLeg)
Traditional betting lines: moneyline, spread, totals

**Evaluation Logic** (from `leg_evaluator.py:324-390`):
```python
def _evaluate_team_prop(self, leg, context):
    home_goals = context.count_team_actions(context.home_team_id, GOALS)
    away_goals = context.count_team_actions(context.away_team_id, GOALS)

    if leg.bet_type == "moneyline":
        # Direct winner comparison
        if home_goals > away_goals: status = "win"
        elif home_goals < away_goals: status = "loss"
        else: status = "draw"
        return leg.line == status  # e.g., line="win"

    elif leg.bet_type == "spread":
        # Add spread to selected team
        if leg.team == "home":
            home_goals += float(leg.line)
        else:
            away_goals += float(leg.line)
        return home_goals > away_goals  # After adjustment

    elif leg.bet_type == "over":
        return (home_goals + away_goals) > float(leg.line)

    elif leg.bet_type == "under":
        return (home_goals + away_goals) < float(leg.line)
```

**Void Conditions**: None (always evaluated)

#### 4. Man of the Match (MomPropLeg)
Bet on highest-rated player

**Evaluation Logic** (from `leg_evaluator.py` - MOM section):
```python
def evaluate_mom(self, leg, home_lineup, away_lineup):
    # Check if player has rating
    player_rating = get_player_rating(leg.player_id, home_lineup, away_lineup)

    if player_rating is None:
        return LegEvaluationResult.voided(VoidReason.PLAYER_NO_RATING)

    # Find highest rated player
    highest_rating = max(all_player_ratings)
    is_hit = (player_rating == highest_rating)

    return LegEvaluationResult.from_hit_value(is_hit)
```

**Void Conditions**:
- Player not in lineup
- Player has no rating (likely didn't play)

#### 5. Zonal Action Occurrence (ZAOPropLeg)
First/most occurrence in specific zones (e.g., "First goal in attacking third")

**Win Conditions**:
- `occurrence="first"`: First event of type in zone → HIT
- `occurrence="most"`: Zone with most events → HIT

**Void Conditions**:
- Tied zones (for "most" bets)

---

## Bet Outcome Calculation

### Aggregation Rules (Parlay Logic)

From `bet_evaluator.py:387-503`:

```python
def evaluate(self, leg_results, is_confirmation=False):
    # Categorize legs
    voided_legs = [leg for leg in leg_results if leg.voided]
    non_voided_legs = [leg for leg in leg_results if not leg.voided]

    # CASE 1: All legs voided → Full void (refund stake)
    if len(voided_legs) == len(leg_results):
        return BetEvaluationResult(
            outcome=BetOutcome.VOIDED,
            hit=None,
            payout_adjustment=PayoutAdjustmentResult(
                final_payout=wager,  # Full refund
                is_full_void=True
            )
        )

    # CASE 2: Some non-voided legs remain
    pending = [leg for leg in non_voided_legs if leg.hit is None]
    hits = [leg for leg in non_voided_legs if leg.hit is True]
    misses = [leg for leg in non_voided_legs if leg.hit is False]

    # Any pending → bet is pending
    if len(pending) > 0:
        return BetEvaluationResult(outcome=BetOutcome.PENDING, hit=None)

    # Any miss → bet misses
    if len(misses) > 0:
        outcome = BetOutcome.LOST if is_confirmation else BetOutcome.DRAFT_LOST
        return BetEvaluationResult(outcome=outcome, hit=False)

    # All non-voided legs hit → bet hits
    outcome = BetOutcome.WON if is_confirmation else BetOutcome.DRAFT_WON

    # Calculate adjusted payout for partial voids
    payout_adjustment = None
    if len(voided_legs) > 0:
        payout_adjustment = payout_calculator.calculate_full_adjustment(
            wager=wager,
            game_multipliers=game_multipliers,
            voided_game_ids=voided_game_ids,
            original_payout=original_payout
        )

    return BetEvaluationResult(
        outcome=outcome,
        hit=True,
        payout_adjustment=payout_adjustment
    )
```

### State Machine

```
PENDING
  │
  ├─ All legs voided ──→ VOIDED (refund)
  │
  ├─ Any leg pending ──→ PENDING (wait)
  │
  ├─ Any leg missed ──→ DRAFT_LOST / LOST
  │
  └─ All legs hit ──────→ DRAFT_WON / WON
                           │
                           └─ Settlement ──→ SETTLED
```

### Database Fields

- `draft_hit` (bool): Preliminary result (draft pass)
- `confirmed_hit` (bool): Final result (confirmation pass)
- `voided` (bool): True if all legs voided
- `payout` (float): Original calculated payout
- `adjusted_payout` (float): Payout after void adjustment (NULL if no voids)
- `settled_at` (timestamp): When settlement completed

---

## Partial Settlement & Void Handling

### Void Policy Rules

From `void_policy.py:156-238`:

#### Game-Level Voids

**Immediate Void** (CANCELLED/ABANDONED):
```python
IMMEDIATE_VOID_STATUSES = (MatchStatus.CANCELLED, MatchStatus.ABANDONED)

# All bets void immediately, no window
if game_status in IMMEDIATE_VOID_STATUSES:
    return VoidDecision.void(
        reason=f"Game {status.value}",
        void_type=GameVoidType.IMMEDIATE
    )
```

**Delayed Void** (POSTPONED):
```python
VOID_WINDOW_HOURS = 48

if game_status == MatchStatus.POSTPONED:
    deadline = original_kickoff + timedelta(hours=48)

    # Within 48h window - don't evaluate yet
    if current_time < deadline:
        return VoidDecision.skip(reason="Postponed, awaiting resolution")

    # Past 48h - void bets placed before original kickoff
    if bet_created_at < original_kickoff:
        return VoidDecision.void(
            reason="Postponed >48h, bet placed before original kickoff",
            void_type=GameVoidType.DELAYED
        )

    # Bets placed after original kickoff → evaluate normally
    return VoidDecision.evaluate()
```

### Partial Void Scenarios

#### Scenario 1: One Leg Voided in 3-Leg Parlay

**Setup**:
- Leg A: 1.5x odds → HIT
- Leg B: 2.0x odds → VOIDED
- Leg C: 1.8x odds → HIT
- Original: 1.5 × 2.0 × 1.8 = 5.4x
- Wager: $10
- Original payout: $54

**Calculation** (from `payout_calculator.py:99-189`):
```python
def recalculate_payout_from_active_games(
    wager=10.00,
    game_multipliers={"A": 1.5, "B": 2.0, "C": 1.8},
    voided_game_ids={"B"}
):
    # Calculate product of non-voided multipliers
    active_multiplier = 1.5 × 1.8 = 2.7

    # New payout = wager × active_multiplier
    final_payout = 10.00 × 2.7 = 27.00

    return PayoutAdjustmentResult(
        final_payout=27.00,
        original_payout=54.00,
        active_games_multiplier=2.7
    )
```

**Result**: User receives $27 instead of $54

#### Scenario 2: All Legs Voided (Full Void)

**Setup**:
- Leg A: VOIDED
- Leg B: VOIDED
- Leg C: VOIDED
- Wager: $10

**Calculation**:
```python
if len(voided_game_ids) >= len(game_multipliers):
    return PayoutAdjustmentResult(
        final_payout=wager,  # Full refund
        is_full_void=True
    )
```

**Result**: User receives $10 refund (original stake)

#### Scenario 3: Voided Leg in Winning Bet

**Setup**:
- Leg A: 1.5x → HIT
- Leg B: 2.0x → VOIDED
- Leg C: 1.8x → HIT
- Wager: $10

**Process**:
1. Leg verification marks Leg B as voided
2. Bet evaluator sees: 2 hits, 1 voided → **bet HITS**
3. Payout calculator: $10 × 1.5 × 1.8 = $27 (not $54)
4. Settlement: Process payout of $27

**Database State**:
```sql
-- userbethistory table
draft_hit: true
confirmed_hit: true
voided: false
payout: 54.00         -- Original
adjusted_payout: 27.00 -- Adjusted for void
settled_at: <timestamp>
```

#### Scenario 4: Voided Leg in Losing Bet

**Setup**:
- Leg A: 1.5x → HIT
- Leg B: 2.0x → VOIDED
- Leg C: 1.8x → MISS
- Wager: $10

**Process**:
1. Leg C evaluation → MISS
2. Bet evaluator sees: 1 hit, 1 voided, 1 miss → **bet MISSES**
3. No payout calculation needed
4. Settlement: Mark as settled (no transaction)

**Result**: User loses original stake, void doesn't help

---

## Payout Calculation Formulas

### Base Payout (No Voids)

From `payout_calculator.py`:

```python
# For regular bets
payout = wager × total_multiplier

# Where total_multiplier is product of all leg odds
total_multiplier = leg1_odds × leg2_odds × ... × legN_odds

# Example: 3-leg parlay with 1.5x, 2.0x, 1.8x
total_multiplier = 1.5 × 2.0 × 1.8 = 5.4
payout = $10 × 5.4 = $54
```

### Partial Void Adjustment (Recalculation Method)

**Preferred Method** - Recalculate from active legs:
```python
def recalculate_payout_from_active_games(wager, game_multipliers, voided_game_ids):
    # Product of non-voided leg multipliers
    active_multiplier = 1
    for game_id, multiplier in game_multipliers.items():
        if game_id not in voided_game_ids:
            active_multiplier *= multiplier

    # New payout = wager × active_multiplier
    final_payout = wager × active_multiplier

    return PayoutAdjustmentResult(
        final_payout=final_payout,
        active_games_multiplier=active_multiplier
    )
```

**Why Recalculation?** The old division method (`original_payout / voided_multiplier`) underestimates when odds are capped.

**Example with Capped Odds**:
```
Games: 1.5x, 2.0x, 1.8x = 5.4x uncapped
Capped at 4.0x max odds
Original payout: $10 × 4.0 = $40

If 2.0x game voided:
❌ Old (division): $40 / 2.0 = $20  (WRONG)
✅ New (recalc):   $10 × 1.5 × 1.8 = $27  (CORRECT)
```

### Bonus Bet Payout

For bonus bets (virtual stake, no cash):
```python
if bonus_amount:
    # Gross payout
    gross = bonus_amount × active_multiplier

    # Net payout (subtract virtual stake)
    final_payout = max(gross - bonus_amount, 0)

    # Example: $20 bonus bet at 2.7x
    gross = $20 × 2.7 = $54
    final_payout = $54 - $20 = $34
```

**Full Void Handling**:
```python
if is_full_void and bonus_amount:
    # Bonus bet full void → no payout, grant restoration handled by ledger
    return PayoutAdjustmentResult(
        final_payout=0,
        is_full_void=True
    )
```

---

## Backed Bet Settlement

### Backing Multiplier System

From `bet_backing_service.py:358-528`:

**Backing Config** (from PostHog or defaults):
```python
max_backers = 5                    # Max users who can back
multiplier_per_backer = 0.05       # +5% profit per backer
min_wager = 5.00                   # Minimum backing wager
```

**Profit Multiplier Formula**:
```python
def calculate_profit_multiplier(backer_count):
    # Linear increase: 1.0 + (count × rate)
    return 1.0 + (backer_count × 0.05)

# Examples:
# 0 backers: 1.0 (no boost)
# 1 backer:  1.05 (+5%)
# 2 backers: 1.10 (+10%)
# 5 backers: 1.25 (+25%)
```

**Boosted Payout Formula**:
```python
def calculate_boosted_payout(base_payout, wager, backer_count):
    profit_multiplier = calculate_profit_multiplier(backer_count)

    # Extract profit
    base_profit = base_payout - wager

    # Apply boost to profit only
    boosted_profit = base_profit × profit_multiplier

    # Reconstitute payout
    boosted_payout = wager + boosted_profit

    return boosted_payout
```

### Backing Example

**Scenario**: Original bettor + 3 backers

**Original Bet**:
- Wager: $10
- Odds: 5.4x (3-leg parlay)
- Base payout: $54

**When Backer 1 Joins** (backer_count=1):
```python
profit_multiplier = 1.0 + (1 × 0.05) = 1.05
base_profit = $54 - $10 = $44
boosted_profit = $44 × 1.05 = $46.20
boosted_payout = $10 + $46.20 = $56.20

# All group members now see $56.20 potential payout
```

**When Backer 2 Joins** (backer_count=2):
```python
profit_multiplier = 1.10
base_profit = $44
boosted_profit = $44 × 1.10 = $48.40
boosted_payout = $10 + $48.40 = $58.40
```

**When Backer 3 Joins** (backer_count=3):
```python
profit_multiplier = 1.15
boosted_payout = $10 + ($44 × 1.15) = $60.60
```

### Backing Settlement Distribution

From `bet_result_service.py:99-122`:

```python
async def _get_effective_payout(user_bet):
    """
    Get final payout at settlement.

    The payout field is kept up-to-date throughout:
    1. Backing boost applied when backers join (batch update)
    2. Void adjustment applied when games voided

    At settlement, just use stored value directly.
    """
    return float(user_bet.payout)
```

**Key Insight**: Each bet in backing group has **same payout value** but **different stakes**:

```sql
-- Backing group example (3 members)
bet_id  | user_id | wager | payout | backing_group_id      | is_backing_original
--------|---------|-------|--------|----------------------|--------------------
bet-1   | alice   | 10.00 | 60.60  | group-123            | true
bet-2   | bob     | 10.00 | 60.60  | group-123            | false
bet-3   | carol   |  5.00 | 30.30  | group-123            | false
```

**Settlement Process**:
1. Bet evaluation marks `draft_hit=true` for all 3 bets
2. Confirmation pass marks `confirmed_hit=true`
3. Settlement processes each independently:
   - Alice wins: Receives $60.60
   - Bob wins: Receives $60.60
   - Carol wins: Receives $30.30 (proportional to $5 wager)

### Batch Payout Updates

When a new backer joins (from `bet_backing_service.py:509-520`):

```python
# Calculate new multiplier
new_backer_count = backer_count + 1
new_multiplier = config.calculate_multiplier(new_backer_count)

# Batch update ALL bets in group
await backing_repo.batch_update_payout_for_group(
    backing_group_id=backing_group_id,
    profit_multiplier=new_multiplier
)
```

**SQL Update**:
```sql
UPDATE userbethistory
SET payout = wager + ((initial_payout - wager) * :profit_multiplier)
WHERE backing_group_id = :group_id
  AND settled_at IS NULL  -- Only update unsettled bets
```

---

## Scheduled Jobs

### Main Settlement Job

**File**: `/backend_server/schedule/bet_verification.py`

**Cron**: Every minute

**Workflow**:

```python
async def verify_bets_job():
    async with get_unit_of_work_context() as uow:
        # Use REPEATABLE READ for consistent snapshot
        await uow.set_repeatable_read()

        factory = ServiceFactory(uow)
        orchestrator = factory.bet_verification_orchestrator

        # PASS 1: Draft - Preliminary verification
        verifiable_matches = await game_repo.get_verifiable_match_ids()
        games_needing_draft = await leg_repo.get_game_ids_needing_draft_hit(
            verifiable_matches
        )

        if games_needing_draft:
            games_info = await game_repo.get_game_info_by_game_ids(
                games_needing_draft
            )
            draft_result = await orchestrator.run_draft_pass(games_info)

        # PASS 2: Confirmation - Final verification after policy window
        games_needing_confirm = await leg_repo.get_game_ids_needing_confirmation(
            verifiable_matches
        )

        if games_needing_confirm:
            games_info = await game_repo.get_game_info_by_game_ids(
                games_needing_confirm
            )
            confirm_result = await orchestrator.run_confirmation_pass(
                games_info, current_time
            )

        # PASS 3: Settlement - Process payouts/refunds
        settlement_result = await orchestrator.settle_bets()

        # PASS 4: Cache flush
        await CacheOperations.flush_all_leaderboard_cache(redis_cache)

    # Separate transaction: Lock verified matches
    if games_ready_to_lock:
        async with get_unit_of_work_context() as lock_uow:
            await lock_matches(
                session=lock_uow.session,
                match_ids=games_ready_to_lock,
                locked_by=DataLockSource.BET_VERIFICATION
            )

    # Separate transaction: Send notifications
    if settlement_result.valid_bets:
        async with get_unit_of_work_context() as notif_uow:
            await notif_service.send_bet_notifications(
                settlement_result.valid_bets
            )
```

**Transaction Isolation**:
- Main transaction: `REPEATABLE READ` (consistent snapshot prevents race conditions)
- Lock transaction: `READ COMMITTED` (separate to avoid serialization errors)
- Notification transaction: `READ COMMITTED` (fire-and-forget, won't roll back settlement)

### Settlement Detail Flow

From `bet_verification_orchestrator_service.py:330-400`:

```python
async def settle_bets(self) -> SettlementResult:
    # Get unsettled bets (hit determined but not settled)
    voided_bets, valid_bets = await eval_service.get_unsettled_bets()

    result = SettlementResult.empty()

    # Settle voided bets (refunds)
    for bet_id, _ in voided_bets:
        await result_service.settle_voided(bet_id)
        result.refunds_processed += 1

    # Settle valid bets
    for bet_id, hit in valid_bets:
        if hit:
            # Process payout
            await result_service.settle_winning(bet_id)
            result.payouts_processed += 1
        else:
            # Just mark settled (no transaction)
            await result_service.settle_loss(bet_id)

    result.bets_settled = result.payouts_processed + result.refunds_processed

    # Finalize: Copy confirmed_hit → hit
    await eval_service.finalize_confirmed_bets(game_ids)

    return result
```

### Tournament Settlement Job

**File**: `/backend_server/schedule/tournaments/settle_tournaments.py`

**Cron**: Every minute

**Workflow**:
```python
async def settle_tournaments_job():
    async with get_unit_of_work_context() as uow:
        factory = ServiceFactory(uow)
        service = factory.social_tournament_service

        # Settle tournaments where all matches have results
        settled_ids = await service.settle_pending_tournaments()

        # Auto-create 1v1 if none open (config from PostHog)
        config_1v1 = load_1v1_config_from_posthog(posthog)
        if config_1v1:
            await service.ensure_open_1v1(
                num_games=config_1v1.num_games,
                buy_in=config_1v1.buy_in,
                # ... other config
            )

        await uow.commit()
```

---

## Edge Cases & Tie-Breaking

### 1. Draw in Moneyline

**Scenario**: Bet on "home wins", game ends 2-2

**Handling**:
```python
if leg.bet_type == "moneyline":
    if home_goals > away_goals:
        status = "win"
    elif home_goals < away_goals:
        status = "loss"
    else:
        status = "draw"

    return leg.line == status
```

**Result**: If `leg.line="win"` → **MISS** (user loses)

**Alternative**: Some sportsbooks void moneyline on draw. This system treats it as a loss.

### 2. Tied Man of the Match

**Scenario**: Multiple players have same highest rating

**Handling** (domain logic):
```python
# Find all players with highest rating
highest_rating = max(all_ratings)
tied_players = [p for p in players if p.rating == highest_rating]

if len(tied_players) > 1:
    # Multiple tied → void
    return LegEvaluationResult.voided(VoidReason.TIED_PLAYERS)
else:
    # Clear winner
    is_hit = (leg.player_id == tied_players[0].id)
    return LegEvaluationResult.from_hit_value(is_hit)
```

**Result**: Bet voids if tie (fair resolution)

### 3. Tied Zones (ZAO "Most" Bets)

**Scenario**: Bet "Most shots in Zone A", but Zone B also has same count

**Handling**:
```python
# Count occurrences in all zones
zone_counts = {zone: count_in_zone(zone) for zone in all_zones}

max_count = max(zone_counts.values())
zones_with_max = [z for z, c in zone_counts.items() if c == max_count]

if len(zones_with_max) > 1:
    # Multiple zones tied for most → void
    return LegEvaluationResult.voided(VoidReason.TIED_ZONES)
else:
    # Clear winner
    is_hit = (leg.zone == zones_with_max[0])
    return LegEvaluationResult.from_hit_value(is_hit)
```

**Result**: Bet voids on tie (can't determine "most")

### 4. Spread Push (Exact Match)

**Scenario**: Home team -1.5 spread, game ends 2-0

**Calculation**:
```python
# Home -1.5 spread
home_score = 2
away_score = 0
adjusted_home = 2 + (-1.5) = 0.5

# Compare
is_hit = (adjusted_home > away_score)
# 0.5 > 0 → True → HIT
```

**Note**: Half-point spreads prevent pushes. Whole number spreads can push:
```python
# Home -2 spread, game ends 2-0
adjusted_home = 2 + (-2) = 0
# 0 > 0 → False → MISS (not a push in this system)
```

**Alternative**: Some books void on exact push. This system counts it as loss.

### 5. Player Substituted Early

**Scenario**: Bet "Player X to score 2+ goals", player substituted after 30 minutes (didn't start)

**Handling**:
```python
is_starter = context._is_player_starter(leg.player_id)

if not is_starter:
    # Not a starter → void
    return LegEvaluationResult.voided(VoidReason.PLAYER_NOT_STARTER)
```

**Result**: Bet voids (player must start)

**Edge Case**: Player starts but injured early (counts as started, bet stands)

### 6. Concurrent Backing Joins

**Scenario**: 2 users try to back simultaneously, would exceed max_backers

**Handling** (from `bet_backing_service.py:399-404`):
```python
# Acquire PostgreSQL advisory lock
await uow.advisory_lock(
    lock_key=f"backing_group:{backing_group_id}",
    enabled=True
)

# Now safe from race conditions
backer_count = await backing_repo.get_backer_count(backing_group_id)
backing_group.validate_can_back(...)  # Checks max_backers
```

**Result**: First user acquires lock and joins; second user waits, then gets error "Max backers reached"

### 7. Void Cascading (Same-Game Parlay)

**Scenario**: 3-leg parlay, 2 legs from Game A (cancelled), 1 leg from Game B

**Handling**:
```python
# VoidPolicy.should_propagate_void_to_same_game_legs() → True

if game_cancelled:
    # Void ALL legs for this game
    for leg in legs:
        if leg.game_id == cancelled_game_id:
            mark_voided(leg)
```

**Result**: Both Game A legs void; Game B leg evaluates normally

**Domain Rule**: "When one leg is voided due to game status, all other legs for that game in the same bet should also be voided."

### 8. Settlement Idempotency

**Scenario**: Job runs twice due to deployment/restart

**Handling**:
```python
async def settle_winning(bet_id):
    user_bet = await bet_repo.get_user_bet(bet_id)

    # Check already settled
    if user_bet.settled_at is not None:
        logger.info(f"Bet {bet_id} already settled, skipping")
        return

    # Process payout
    await ledger.record_bet_winnings(user_id, amount, bet_id)

    # Mark settled (prevents double-processing)
    await bet_repo.mark_bet_settled(bet_id)
```

**Database Constraint**:
```sql
-- Unique constraint on ledger entries
UNIQUE(user_id, transaction_type, bet_id)
```

**Result**: Second run skips already-settled bets; ledger prevents duplicate credits

### 9. Odds Movement During Backing

**Scenario**: Original bet at 5.4x, odds now 3.2x, user tries to back

**Handling** - Odds Alignment Policy (from `bet_backing_service.py:454-461`):
```python
odds_resolution = OddsAlignmentPolicy.resolve(
    original_parlay_odds=5.4,
    market_parlay_odds=3.2,
)

# Policy decision:
# If market odds within threshold → use original odds (aligned=True)
# If too different → use current market odds (aligned=False)

locked_odds = LockedOdds(
    parlay_odds=odds_resolution.effective_parlay_odds
)
```

**Result**: Backer gets fair odds (either original or current, policy decides)

### 10. Postponed Game Resumption

**Scenario**: Game postponed, then resumed 30 hours later

**Timeline**:
- Original kickoff: Monday 3pm
- Game postponed: Monday 2pm
- Resume announced: Tuesday 9am (30h later)
- Void deadline: Wednesday 3pm (48h after original)

**Handling**:
```python
VOID_WINDOW_HOURS = 48

def _check_postponed_void(original_kickoff, current_time, bet_created_at):
    deadline = original_kickoff + timedelta(hours=48)

    # Tuesday 9am: Within window
    if current_time < deadline:
        return VoidDecision.skip(reason="Postponed, awaiting resolution")

    # Wednesday 5pm: Past deadline
    if current_time > deadline:
        # Bet placed before Monday 3pm → void
        if bet_created_at < original_kickoff:
            return VoidDecision.void(reason="Postponed >48h")

        # Bet placed Monday 4pm (after postponement) → evaluate
        else:
            return VoidDecision.evaluate()
```

**Results**:
- Bets placed **before** original kickoff → Void (didn't know about postponement)
- Bets placed **after** postponement announced → Valid (accepted rescheduled odds)

---

## Code References

### Key Files by Responsibility

**Application Orchestration**:
- `/backend_server/application/services/bets/bet_verification_orchestrator_service.py:1-600`
  - Main coordinator for settlement workflow
  - Lines 175-247: Draft pass implementation
  - Lines 249-336: Confirmation pass implementation
  - Lines 338-400: Settlement orchestration

**Leg Evaluation**:
- `/backend_server/application/services/bets/leg_verification_service.py:1-450`
  - Application-level leg verification coordination
  - Lines 97-223: Main verification method
  - Lines 287-348: Game-level void handling
- `/backend_server/domain/bet/evaluation/leg_evaluator.py:1-600`
  - Pure domain leg evaluation logic
  - Lines 252-288: Player prop evaluation
  - Lines 294-318: Team action prop evaluation
  - Lines 324-390: Team prop evaluation (moneyline, spread, totals)

**Bet Aggregation**:
- `/backend_server/application/services/bets/bet_evaluation_service.py:1-613`
  - Application-level bet evaluation coordination
  - Lines 171-236: Game bet evaluation
  - Lines 238-296: Single bet evaluation
  - Lines 337-465: Persistence of results
- `/backend_server/domain/bet/evaluation/bet_evaluator.py:1-654`
  - Pure domain bet aggregation logic
  - Lines 387-503: Main evaluation method with voided leg handling
  - Lines 565-653: Leg aggregation logic

**Settlement Processing**:
- `/backend_server/application/services/bets/bet_result_service.py:1-296`
  - Lines 124-164: Winning bet settlement
  - Lines 171-212: Voided bet settlement (refunds)
  - Lines 219-244: Losing bet settlement
  - Lines 246-295: Batch settlement

**Payout Calculation**:
- `/backend_server/domain/bet/evaluation/payout_calculator.py:1-454`
  - Lines 99-189: Payout recalculation for partial voids
  - Lines 191-235: Voided multiplier calculation
  - Lines 237-298: Adjusted payout formula (deprecated division method)
  - Lines 300-330: Full adjustment wrapper
  - Lines 384-453: Backing boost calculations

**Void Policy**:
- `/backend_server/domain/bet/evaluation/void_policy.py:1-443`
  - Lines 156-194: Game void decision logic
  - Lines 196-238: Postponed game void logic
  - Lines 240-300: Rescheduled game with history
  - Lines 336-414: Leg-level void checks

**Backing System**:
- `/backend_server/application/services/bets/bet_backing_service.py:1-850`
  - Lines 131-213: Enable sharing
  - Lines 258-356: Get backing info with odds alignment
  - Lines 358-528: Back bet flow (including odds alignment)
  - Lines 509-520: Batch payout updates

**Scheduled Jobs**:
- `/backend_server/schedule/bet_verification.py:1-260`
  - Main settlement job (runs every minute)
  - Lines 75-249: Complete workflow with transaction isolation
- `/backend_server/schedule/tournaments/settle_tournaments.py:1-137`
  - Tournament settlement job

**Domain Value Objects**:
- `/backend_server/domain/bet/evaluation/evaluation_result.py:1-310`
  - Lines 15-99: LegEvaluationState enum
  - Lines 101-155: VoidReason enum
  - Lines 157-310: LegEvaluationResult value object

---

## Summary

The bet settlement system is a **robust, domain-driven architecture** with clear separation of concerns:

1. **Domain Layer** - Pure business logic (leg evaluation, bet aggregation, payout math)
2. **Application Layer** - Orchestration and coordination (workflow, persistence, audit)
3. **Infrastructure Layer** - External systems (database, scheduler, notifications)

**Key Strengths**:
- ✅ Idempotent operations (safe to retry)
- ✅ Two-pass verification (draft + confirmation)
- ✅ Transaction isolation (consistent snapshots)
- ✅ Comprehensive void handling (game-level + leg-level)
- ✅ Fair payout recalculation (handles capped odds)
- ✅ Backing support (dynamic multiplier updates)
- ✅ Edge case coverage (ties, pushes, concurrent access)

**Bet Lifecycle**:
```
Place Bet → Pending → Draft Verification → Confirmation → Settlement → Settled
              │              │                    │             │
              └─── Any leg pending               │             │
                             │                    │             │
                             └─── All legs evaluated            │
                                                  │             │
                                                  └─── Hit determined
```

Each stage is **idempotent and audited**, ensuring data integrity and user trust.
