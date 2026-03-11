# Complete Database Schema Documentation
## Backend-Server & Backend-Odds Schema Analysis

**Generated:** 2026-03-03
**Systems Analyzed:**
- Backend-Server: `/workspace/extra/programming/Backend-Server`
- Backend-Odds: `/workspace/extra/programming/Backend-Odds`

---

## Table of Contents
1. [Overview](#overview)
2. [Migration Files](#migration-files)
3. [Shared Tables](#shared-tables)
4. [Backend-Server Exclusive Tables](#backend-server-exclusive-tables)
5. [Backend-Odds Exclusive Tables](#backend-odds-exclusive-tables)
6. [Foreign Key Relationships](#foreign-key-relationships)
7. [Indexes and Constraints](#indexes-and-constraints)
8. [Data Types and Defaults](#data-types-and-defaults)
9. [Database Features](#database-features)
10. [ERD Structure](#erd-structure)

---

## 1. Overview

### Architecture
Both Backend-Server and Backend-Odds use:
- **ORM:** SQLAlchemy 2.x with `declarative_base`
- **Database:** PostgreSQL with timezone-aware timestamps
- **Migration Tool:** Alembic
- **Data Format:** JSONB for flexible schema storage

### Database Separation Strategy
- **Shared Schema:** Core sports data (teams, players, matches, events)
- **Backend-Server:** User management, betting, transactions, promotions
- **Backend-Odds:** Odds calculation, historical odds data, market calibration

---

## 2. Migration Files

### Backend-Server Migrations
**Location:** `/workspace/extra/programming/Backend-Server/alembic/versions/`
**Total Files:** 258+ migration files

**Recent Key Migrations:**
- `20260115_ledger_phase2_cleanup.py` - Ledger system cleanup
- `20260114a_add_config_snapshot_to_promo_redemptions.py` - Promo config snapshots
- `20260114_add_migration_adjustment_type.py` - Migration adjustment type
- `20260109_ledger_phase1_schema.py` - Ledger phase 1 schema
- `20260109_ledger_phase1_nonnull.py` - Ledger non-null constraints
- `20251227_rename_partner_5_25_to_partner_promo.py` - Partner promo rename
- `20251226_add_is_active_to_promotions.py` - Active flag for promotions
- `20251224_add_friends_leagues.py` - Friends leagues feature
- `20251224_add_coin_amount_to_promo_grants.py` - Coin amount support
- `20251222_add_bonus_bet_promo.py` - Bonus bet promotions
- `20251220_add_deposit_matching_promo.py` - Deposit matching
- `20251218_withdrawable_amount_changelog.py` - Withdrawable amount tracking
- `20251216_add_set_piece_actions_to_zaoprops.py` - Set piece actions
- `20251215_set_piece_flags.py` - Set piece flag columns
- `20251213_add_lineup_released_to_notif_events.py` - Lineup notifications
- `20251212_add_updated_at_to_withdrawal_status_history.py` - Withdrawal status tracking
- `20251208_add_bet_promo_applications.py` - Bet promo applications
- `20251201_add_data_locking.py` - Data locking for match data

### Backend-Odds Migrations
**Location:** `/workspace/extra/programming/Backend-Odds/alembic/versions/`
**Total Files:** 26 migration files

**Key Migrations:**
- `p1q2r3s4t5u6_add_player_stats_table.py` - Player statistics
- `o0p1q2r3s4t5_add_predicted_lineups_tables.py` - Predicted lineups
- `n9o0p1q2r3s4_add_missing_players_table.py` - Missing players tracking
- `m8n9o0p1q2r3_add_odds_api_player_mapping.py` - Odds API player mapping
- `k7l8m9n0o1p2_add_odds_api_market_tables.py` - Odds API market tables
- `j6k7l8m9n0o1_add_totals_and_spread_odds_tables.py` - Totals and spread odds
- `i5j6k7l8m9n0_add_moneyline_odds_table.py` - Moneyline odds
- `fc5e8936995a_new_team_stats_table.py` - Team statistics
- `e49dbfge3eb4_add_odds_history_table.py` - Odds history
- `d38caffd2da3_add_trading_tables_user_bets_exposure_.py` - Trading tables
- `d5b3bd068db4_add_back_historical_odds_data_db.py` - Historical odds data
- `cascade_foreign_keys.py` - Foreign key cascade rules
- `aae6c37ac766_add_mapping_db.py` - ID mapping tables

---

## 3. Shared Tables

These tables exist in both systems and contain core sports data:

### 3.1 Seasons
**Table:** `seasons`
**Purpose:** Tournament seasons
**Primary Key:** `season_id` (Integer)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| season_id | Integer | PK | Season identifier |
| name | String(255) | NOT NULL | Season name (e.g., "2024/2025") |

**Indexes:**
- Primary key on `season_id`

### 3.2 Teams
**Table:** `teams`
**Purpose:** Team information
**Primary Key:** `team_id` (String)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| team_id | String | PK | Team UUID |
| team_name/name | String(255) | NOT NULL | Official team name |
| short_name | String | | Short team name |
| official_name | String | | Official long name |
| code | String | | Team code |
| season_id | Integer | FK → seasons.season_id | Associated season (Backend-Odds) |
| wh_team_id | Integer | UNIQUE | WhosScored team ID |
| region_code | Integer | | Region/country code |
| venue | String | | Home stadium |
| founded | String | | Founding year |
| status | String | | Active status |

**Foreign Keys:**
- `season_id` → `seasons.season_id` (CASCADE DELETE/UPDATE) - Backend-Odds only
- Backend-Server uses String team_id without season FK

**Indexes:**
- Primary key on `team_id`
- `idx_teams_season_id` on `season_id` (Backend-Odds)
- Unique constraint on `wh_team_id`

### 3.3 Players
**Table:** `players`
**Purpose:** Player information
**Primary Key:** `player_id` (String in Backend-Server, Integer in Backend-Odds)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| player_id | String/Integer | PK | Player identifier |
| first_name | String | | Player first name |
| last_name | String | | Player last name |
| match_name/name | String | | Display name |
| team_id | String/Integer | FK → teams.team_id | Current team |
| position | String(50) | | Player position |
| nationality | String | | Nationality |
| date_of_birth | String | | Birth date |
| height | Integer | | Height in cm |
| weight | Integer | | Weight in kg |
| wh_player_id | Integer | UNIQUE | WhosScored player ID |
| jersey_number/shirt_number | Integer | | Jersey number |

**Foreign Keys:**
- `team_id` → `teams.team_id` (CASCADE DELETE/UPDATE)
- `game_id` → `games.game_id` (CASCADE DELETE) - Backend-Odds only
- `season_id` → `seasons.season_id` (CASCADE DELETE/UPDATE) - Backend-Odds only

**Indexes:**
- Primary key on `player_id`
- `idx_players_game_id` on `game_id` (Backend-Odds)
- `idx_players_season_id` on `season_id` (Backend-Odds)
- `idx_players_team_id` on `team_id` (Backend-Odds)
- Unique constraint on `wh_player_id`

### 3.4 Games / Tournament Schedule
**Backend-Odds Table:** `games`
**Backend-Server Table:** `tournament_schedule`
**Purpose:** Match/game information

#### Backend-Odds Schema (`games`):

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| game_id | Integer | PK | Game identifier |
| game | String(255) | | Game description |
| score | String(50) | | Final score |
| home_team_id | Integer | FK → teams.team_id | Home team |
| away_team_id | Integer | FK → teams.team_id | Away team |
| season_id | Integer | FK → seasons.season_id | Season |
| date | DateTime(TZ) | | Match date/time |
| matchday | Integer | | Matchday number |

**Foreign Keys:**
- `home_team_id` → `teams.team_id`
- `away_team_id` → `teams.team_id`
- `season_id` → `seasons.season_id` (CASCADE DELETE/UPDATE)

**Indexes:**
- `idx_games_away_team_id` on `away_team_id`
- `idx_games_date` on `date`
- `idx_games_home_team_id` on `home_team_id`
- `idx_games_season_id` on `season_id`

#### Backend-Server Schema (`tournament_schedule`):

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| match_id | String | PK | Match UUID |
| competition_id | String | FK → competitions.competition_id | Competition |
| tournament_id | String | FK → tournament_calendar.tournament_id | Tournament/season |
| home_contestant_id | String | FK → teams.team_id | Home team |
| away_contestant_id | String | FK → teams.team_id | Away team |
| kickoff_datetime | DateTime(TZ) | INDEXED | Match kickoff time |
| home_score | Integer | | Home team score |
| away_score | Integer | | Away team score |
| status | String | CHECK constraint | Match status enum |
| wh_match_id | Integer | UNIQUE | WhosScored match ID |
| data_locked | Boolean | DEFAULT false | Prevent scraper overwrites |
| void_status | String(50) | | Void status for 48-hour rule |

**Check Constraints:**
- `status` IN ('NOT_STARTED', 'LIVE', 'INPROGRESS', 'FINISHED', 'CANCELLED', 'POSTPONED', 'INTERRUPTED', 'ABANDONED')

**Indexes:**
- `idx_tournament_schedule_competition_kickoff` on (`competition_id`, `kickoff_datetime`)
- Unique constraint on `wh_match_id`

### 3.5 Events / Match Projection
**Backend-Odds Table:** `events`
**Backend-Server Table:** `match_projection`
**Purpose:** Match events (goals, shots, passes, etc.)

#### Backend-Odds Schema (`events`):

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Event ID |
| game_id | Integer | FK → games.game_id | Match |
| player_id | Integer | FK → players.player_id | Player involved |
| team_id | Integer | FK → teams.team_id | Team |
| season_id | Integer | FK → seasons.season_id | Season |
| period | String(50) | | Match period |
| minute | Integer | | Event minute |
| x, y | Double | | Event coordinates |
| zone | Text | | Pitch zone |
| type | String(255) | | Event type |
| outcome_type | Boolean | | Success/failure |
| is_shot | Double | DEFAULT 0 | Shot flag |
| is_goal | Double | DEFAULT 0 | Goal flag |
| is_assist | Double | DEFAULT 0 | Assist flag |
| is_pass | Double | DEFAULT 0 | Pass flag |
| qualifiers | JSONB | | Event qualifiers |
| created_at | DateTime(TZ) | DEFAULT now() | Creation timestamp |

**Foreign Keys:**
- `game_id` → `games.game_id` (CASCADE DELETE)
- `player_id` → `players.player_id` (CASCADE DELETE)
- `team_id` → `teams.team_id` (CASCADE DELETE)
- `season_id` → `seasons.season_id` (CASCADE DELETE/UPDATE)
- `related_id` → `events.id` (CASCADE DELETE) - self-referential

**Indexes:**
- `idx_events_game_id` on `game_id`
- `idx_events_player_id` on `player_id`
- `idx_events_is_shot` on `is_shot`
- `idx_events_is_goal` on `is_goal`
- Multiple indexes on event type flags

#### Backend-Server Schema (`match_projection`):

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | BigInteger | PK | Event ID |
| match_id | String | FK → tournament_schedule.match_id | Match |
| player_id | String | FK → players.player_id | Player |
| team_id | String | FK → teams.team_id | Team |
| type_id | Integer | | Event type ID |
| time_min | Integer | | Event minute |
| x, y | Float | | Event coordinates |
| qualifiers | JSON | | Event qualifiers |
| is_shot | Boolean | DEFAULT false | Shot flag |
| is_goal | Boolean | DEFAULT false | Goal flag |
| wh_match_id | Integer | | WhosScored match ID |
| wh_player_id | Integer | | WhosScored player ID |

**Foreign Keys:**
- `match_id` → `tournament_schedule.match_id` (CASCADE DELETE)
- `player_id` → `players.player_id` (CASCADE DELETE/UPDATE)
- `team_id` → `teams.team_id` (CASCADE DELETE/UPDATE)

**Indexes:**
- Primary key on `event_id`
- Index on `match_id`
- Index on `player_id`
- Index on `team_id`

### 3.6 Lineups
**Table:** `lineups` (Backend-Odds) / `lineup` (Backend-Server)
**Purpose:** Team lineups for matches

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id/lineup_id | BigInteger/Integer | PK | Lineup ID |
| game_id/match_id | Integer/String | FK | Match reference |
| player_id | Integer/String | FK | Player reference |
| team_id | Integer/String | FK | Team reference |
| is_starter | Boolean | | Starting XI flag |
| jersey_number | Integer | | Jersey number |
| minutes_played | Integer | DEFAULT 0 | Minutes played |
| rating | Float | | Player rating |
| formation | String | | Team formation |

**Unique Constraints:**
- `(match_id, team_id)` in Backend-Server

---

## 4. Backend-Server Exclusive Tables

### 4.1 User Management

#### Users Table
**Table:** `users`
**Purpose:** User accounts and authentication

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | UUID | PK | User identifier |
| username | String | UNIQUE per account_type | Username |
| email | String | UNIQUE per account_type | Email address |
| phone_number | String | UNIQUE per account_type, CHECK regex | Phone number |
| hashed_password | String | DEFAULT '' | Password hash |
| role | String | CHECK IN ('admin', 'test_user', 'user') | User role |
| account_type | String | CHECK IN ('TBG', 'AB', 'SLOUGH_TOWN') | Account type |
| registration_date | DateTime(TZ) | DEFAULT now() | Registration timestamp |
| is_active | Boolean | DEFAULT true | Active status |
| max_entry_amount | Integer | | Gambling limit |
| weekly_deposit_limit | Double | | Weekly deposit limit |
| favorite_team_id | String | FK → teams.team_id | Favorite team |
| preferred_language | String(2) | CHECK IN ('en', 'es', 'da') | Language preference |
| follow_privacy | String | CHECK IN ('public', 'private') | Follow privacy |
| paypal_customer_id | String | | PayPal customer ID |
| odds_accept_mode | String | DEFAULT 'accept_favorable' | Live betting mode |

**Check Constraints:**
- Phone number regex: `'^[+][1-9][0-9]{9,14}$'`
- Multiple enum constraints on role, register_method, account_type, language, privacy

**Unique Constraints:**
- `(email, account_type)`
- `(username, account_type)`
- `(phone_number, account_type)`

**Indexes:**
- `idx_users_type_regdate` on (`account_type`, `registration_date`, `user_id`)

#### User Preferences
**Table:** `user_prefs`
**Purpose:** Notification preferences

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | UUID | PK, FK → users.user_id | User reference |
| push_token | String(255) | | Expo push token |
| is_active | Boolean | DEFAULT true | Notifications enabled |
| preferences | JSONB | NOT NULL | Notification settings |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |
| updated_at | DateTime(TZ) | DEFAULT now() | Last update |

**Indexes:**
- `idx_user_prefs_active` on `is_active`
- `idx_user_prefs_preferences` on `preferences` (GIN index)

### 4.2 Betting System

#### UserBetHistory
**Table:** `userbethistory`
**Purpose:** User bet records

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| bet_id | UUID | PK | Bet identifier |
| user_id | UUID | FK → users.user_id | User |
| tournament_id | UUID | FK → tournaments.tournament_id | Tournament |
| wager | Double | NOT NULL | Bet amount |
| payout | Double | | Potential payout |
| initial_payout | Double | NOT NULL | Original payout at placement |
| combined_odds | Float | | Combined odds |
| hit | Boolean | | Final hit status |
| draft_hit | Boolean | | Preliminary hit |
| confirmed_hit | Boolean | | Confirmed hit after policy |
| voided | Boolean | | Void status |
| voided_multiplier | Float | DEFAULT 1.0 | M_void multiplier |
| backing_group_id | UUID | INDEXED | Bet backing group |
| is_backing_original | Boolean | DEFAULT false | Original shared bet flag |
| settled_at | DateTime(TZ) | | Settlement timestamp |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Indexes:**
- Partial unique index: `uq_backing_group_user` on (`backing_group_id`, `user_id`) WHERE `backing_group_id IS NOT NULL`

#### BetSlipBets
**Table:** `betslipbets`
**Purpose:** Bet legs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| bet_id | UUID | PK, FK → userbethistory.bet_id | Parent bet |
| leg_id | UUID | PK, UNIQUE | Leg identifier |
| leg_type | String | PK, CHECK | Leg type enum |
| odds | Float | | Individual leg odds |

**Check Constraint:**
- `leg_type` IN ('playerprop', 'teamprop', 'teamactionprop', 'zaoprops', 'momprop')

#### PlayerProps
**Table:** `playerprops`
**Purpose:** Player proposition bets

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| leg_id | UUID | PK | Leg identifier |
| game_id | String | FK → tournament_schedule.match_id | Match |
| player_id | String | FK → players.player_id | Player |
| user_id | UUID | FK → users.user_id | User |
| action | String(50) | | Action type (goals, shots, etc.) |
| is_over | Boolean | | Over/under flag |
| occ_threshold | Double | | Occurrence threshold |
| zones | ARRAY(String) | | Pitch zones |
| zone_type | String | | Zone type |
| voided | Boolean | | Void status |
| hit | Boolean | | Hit status |
| draft_hit | Boolean | | Preliminary hit |
| confirmed_hit | Boolean | | Confirmed hit |

**Indexes:**
- `idx_playerprops_user_id` on `user_id`

#### Similar Tables: ZATProps, TeamProps, ZAOProps
All follow similar patterns for different bet types with zone-based or team-based props.

### 4.3 Financial System

#### Transactions (Ledger System)
**Table:** `transactions`
**Purpose:** All financial transactions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| transaction_id | String | PK | Transaction ID |
| user_id | UUID | FK → users.user_id | User |
| tournament_id | UUID | FK → tournaments.tournament_id | Associated tournament |
| amount | Float | NOT NULL | Transaction amount |
| currency | String | NOT NULL | Currency code |
| transaction_type | String | CHECK constraint | Transaction type |
| direction | String(10) | CHECK IN ('credit', 'debit') | Money direction |
| balance_after | Numeric(18,2) | | Running balance after tx |
| withdrawable_after | Numeric(18,2) | | Withdrawable amount after tx |
| idempotency_key | String | UNIQUE | Duplicate prevention |
| reference_id | String | | Related entity ID |
| reference_type | String | | Related entity type |
| payment_method | String | | Payment method |
| created_at | DateTime(TZ) | DEFAULT now() | Transaction time |

**Check Constraint:**
- `transaction_type` IN ('deposit', 'withdrawal', 'entry_fee', 'entry_fee_refund', 'winnings', 'promotion', 'referral', 'shop_purchase', 'daily_bonus', 'weekly_bonus', 'tournament_prize', 'coupon_redemption', 'raffle_entry', 'migration_adjustment', etc.)

**Indexes:**
- `ix_transactions_user_currency_created` on (`user_id`, `currency`, `created_at DESC`)
- `ix_transactions_idempotency` on `idempotency_key` (UNIQUE)
- `ix_transactions_reference` on (`reference_type`, `reference_id`)
- `ix_transactions_user_type_created` on (`user_id`, `transaction_type`, `created_at DESC`)

#### Exchange Rates
**Table:** `exchange_rates`
**Purpose:** Currency conversion rates

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK | Record ID |
| from_currency | String(3) | NOT NULL | Source currency |
| to_currency | String(3) | NOT NULL | Target currency |
| rate | Numeric(18,8) | NOT NULL | Exchange rate |
| fetched_at | DateTime(TZ) | DEFAULT now() | Fetch timestamp |
| source | String(50) | DEFAULT 'frankfurter' | Data source |
| is_active | Boolean | DEFAULT true | Active status |

**Unique Constraint:**
- `(from_currency, to_currency, fetched_at)`

**Indexes:**
- `idx_exchange_rates_active` on (`from_currency`, `to_currency`, `is_active`)

### 4.4 Promotions System

#### Promotions
**Table:** `promotions`
**Purpose:** Promotional campaigns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Promotion ID |
| type | String | CHECK constraint | Promo type enum |
| category | String | CHECK IN ('wallet', 'bet', 'tournament', 'raffle') | High-level category |
| amount | Float | DEFAULT 5.0 | Cash amount |
| coin_amount | Integer | DEFAULT 500 | Coin amount |
| description | String | | Description |
| config | JSONB | DEFAULT '{}' | Promo configuration |
| start_date | DateTime(TZ) | DEFAULT now() | Start date |
| end_date | DateTime(TZ) | | End date |
| is_referral | Boolean | DEFAULT false | Referral flag |
| referral_user_id | UUID | FK → users.user_id | Referrer |
| redemption_count | Integer | DEFAULT 0 | Times redeemed |
| max_redemptions | Integer | DEFAULT 1 | Max redemptions |
| app_type | String | CHECK IN ('AB', 'TBG', 'SLOUGH_TOWN') | App type |
| custom_code | String | UNIQUE (case-insensitive) | Promo code |
| is_active | Boolean | DEFAULT true | Active status |

**Check Constraints:**
- `type` IN ('new_sign_up_bonus', 'referral', 'instant_promo', 'daily_bonus', 'weekly_bonus', 'partner_promo', 'bet_modifier', 'bonus_bet', 'deposit_matching')

#### Promo Redemptions
**Table:** `promo_redemptions`
**Purpose:** Track promo usage

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| redemption_id | UUID | PK | Redemption ID |
| user_id | UUID | FK → users.user_id | User |
| promo_id | UUID | FK → promotions.id | Promotion |
| referrer_id | UUID | FK → users.user_id | Referrer if applicable |
| redeemed_at | DateTime(TZ) | DEFAULT now() | Redemption time |
| referral_bonus_paid | Boolean | DEFAULT false | Referral bonus paid |
| config_snapshot | JSONB | | Config at redemption time |

**Unique Constraint:**
- `(user_id, promo_id)` - Prevent double redemption

### 4.5 Competitions & Tournaments

#### Competitions
**Table:** `competitions`
**Purpose:** Sports competitions/leagues

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| competition_id | String | PK | Competition UUID |
| name | String | | Full name |
| known_name | String | | Common name |
| country | String | | Country |
| country_code | String | | Country code |
| wh_tournament_id | Integer | | WhosScored tournament ID |
| wh_region_id | Integer | | WhosScored region ID |
| competition_format | String | | Format (League, Cup, etc.) |
| is_national_team | Boolean | | National team flag |

#### Tournament Calendar
**Table:** `tournament_calendar`
**Purpose:** Competition seasons

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| tournament_id | String | PK | Tournament UUID |
| competition_id | String | FK → competitions.competition_id | Parent competition |
| name | String | | Season name (e.g., "2024/2025") |
| start_date | DateTime(TZ) | | Season start |
| end_date | DateTime(TZ) | | Season end |
| wh_season_id | Integer | | WhosScored season ID |

#### Tournament Stages
**Table:** `tournament_stages`
**Purpose:** Tournament stage mappings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| wh_stage_id | Integer | PK | WhosScored stage ID |
| tournament_id | String | FK → tournament_calendar.tournament_id | Tournament |
| stage_name | String | NOT NULL | Stage name |
| min_date | DateTime(TZ) | | Stage start |
| max_date | DateTime(TZ) | | Stage end |
| calendar_mask | JSON | | Calendar data |

**Unique Constraint:**
- `(tournament_id, wh_stage_id)`

### 4.6 Shop & E-commerce

#### Shop Packages
**Table:** `shop_packages`
**Purpose:** In-app purchases

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| package_id | String | PK | Package identifier |
| name | String | | Package name |
| cash_value | Float | | Cash value |
| coin_value | Integer | | Coin value |
| price_usd | Float | | Price in USD |
| is_active | Boolean | DEFAULT true | Active status |

#### Credit Coupons
**Table:** `credit_coupons`
**Purpose:** Credit vouchers

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| coupon_id | UUID | PK | Coupon ID |
| user_id | UUID | FK → users.user_id | User |
| amount | Float | | Coupon value |
| is_redeemed | Boolean | DEFAULT false | Redeemed flag |
| redeemed_at | DateTime(TZ) | | Redemption time |

---

## 5. Backend-Odds Exclusive Tables

### 5.1 Historical Odds Tables

#### MoneylineOdds
**Table:** `moneyline_odds`
**Purpose:** Head-to-head odds history

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| bookmaker | String(100) | | Bookmaker name |
| home_odds | Float | | Home win odds (decimal) |
| away_odds | Float | | Away win odds (decimal) |
| draw_odds | Float | | Draw odds (decimal) |
| last_update | DateTime(TZ) | | Last update time |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Unique Constraint:**
- `(game_id, bookmaker)`

**Indexes:**
- `idx_moneyline_odds_game_id` on `game_id`

#### TotalsOdds
**Table:** `totals_odds`
**Purpose:** Over/under odds history

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| bookmaker | String(100) | | Bookmaker name |
| total_line | Float | | Total line (e.g., 2.5) |
| over_odds | Float | | Over odds (decimal) |
| under_odds | Float | | Under odds (decimal) |
| last_update | DateTime(TZ) | | Last update time |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Unique Constraint:**
- `(game_id, bookmaker, total_line)`

#### SpreadOdds
**Table:** `spread_odds`
**Purpose:** Handicap odds history

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| bookmaker | String(100) | | Bookmaker name |
| home_spread | Float | | Home spread (e.g., -0.5) |
| home_odds | Float | | Home odds (decimal) |
| away_odds | Float | | Away odds (decimal) |
| last_update | DateTime(TZ) | | Last update time |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Unique Constraint:**
- `(game_id, bookmaker, home_spread)`

### 5.2 Alternate & Specialized Markets

#### AlternateSpreads
**Table:** `alternate_spreads`
**Purpose:** All available spread lines

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| bookmaker | String(100) | | Bookmaker name |
| team_name | String(255) | | Team name |
| spread | Float | | Spread value |
| odds | Float | | Odds (decimal) |
| last_update | DateTime(TZ) | | Last update time |

**Unique Constraint:**
- `(game_id, bookmaker, team_name, spread)`

#### AlternateTotals
**Table:** `alternate_totals`
**Purpose:** All available total lines

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| bookmaker | String(100) | | Bookmaker name |
| total_line | Float | | Total line |
| is_over | Boolean | | Over flag |
| odds | Float | | Odds (decimal) |

**Unique Constraint:**
- `(game_id, bookmaker, total_line, is_over)`

### 5.3 Player Props Markets

#### PlayerGoalscorer
**Table:** `player_goalscorer_odds`
**Purpose:** Player goalscorer odds

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| bookmaker | String(100) | | Bookmaker name |
| player_name | String(255) | | Player name |
| market_type | String(50) | | 'anytime', 'first', 'last' |
| odds | Float | | Odds (decimal) |

**Unique Constraint:**
- `(game_id, bookmaker, player_name, market_type)`

**Indexes:**
- `idx_player_goalscorer_odds_game_id` on `game_id`
- `idx_player_goalscorer_odds_player_name` on `player_name`

#### PlayerShots, PlayerShotsOnTarget, PlayerAssists
Similar structures for different player prop types.

### 5.4 Statistics Tables

#### MatchStatistics
**Table:** `match_statistics`
**Purpose:** Team match statistics

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| game_id | Integer | PK, FK → games.game_id | Match |
| team_id | Integer | PK, FK → teams.team_id | Team |
| goals | Integer | DEFAULT 0 | Goals scored |
| shots | Integer | DEFAULT 0 | Total shots |
| shots_on_target | Integer | DEFAULT 0 | Shots on target |
| passes | Integer | DEFAULT 0 | Total passes |
| fouls | Integer | DEFAULT 0 | Fouls committed |
| corner_kicks | Integer | DEFAULT 0 | Corner kicks |
| is_home | Boolean | | Home team flag |

**Indexes:**
- `idx_match_statistics_game_id` on `game_id`

#### PlayerStatistics
**Table:** `player_statistics`
**Purpose:** Player match statistics

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| player_id | BigInteger | FK → players.player_id | Player |
| game_id | BigInteger | FK → games.game_id | Match |
| goals | Integer | DEFAULT 0 | Goals scored |
| assists | Integer | DEFAULT 0 | Assists |
| shots | Integer | DEFAULT 0 | Total shots |
| shots_on_target | Integer | DEFAULT 0 | Shots on target |
| passes | Integer | DEFAULT 0 | Passes |
| tackles | Integer | DEFAULT 0 | Tackles |
| dribbles | Integer | DEFAULT 0 | Dribbles |

**Unique Constraint:**
- `(player_id, game_id)`

**Indexes:**
- `idx_player_statistics_game_id` on `game_id`
- `idx_player_statistics_player_id` on `player_id`
- `idx_player_statistics_player_stats` on (`player_id`, `goals`, `assists`)

#### ZonalStatistics
**Table:** `zonal_statistics`
**Purpose:** Player zonal event counts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| player_id | Integer | FK → players.player_id | Player |
| game_id | Integer | FK → games.game_id | Match |
| action | Text | | Action type |
| zone | Text | | Pitch zone |
| zone_type | Integer | | Zone type ID |
| count | Integer | DEFAULT 0 | Event count |

**Composite Key:**
- `(player_id, game_id, action, zone)`

**Indexes:**
- `idx_zonal_statistics_player_id` on `player_id`
- `idx_zonal_statistics_game_id` on `game_id`
- `idx_zonal_statistics_action` on `action`
- `idx_zonal_statistics_zone_type` on `zone_type`

#### TeamZonalStatistics
Similar to ZonalStatistics but for team-level data.

### 5.5 Trading & Risk Management

#### UserBets
**Table:** `user_bets`
**Purpose:** Persistent bet storage for exposure tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| bet_id | String(64) | PK | Bet identifier |
| user_id | String(64) | NOT NULL | User identifier |
| bet_type | String(20) | | 'single' or 'parlay' |
| status | ENUM | DEFAULT 'pending' | Bet status |
| selections | JSON | NOT NULL | Bet selections |
| stake | Float | NOT NULL | Bet stake |
| odds | Float | NOT NULL | Combined odds |
| potential_payout | Float | NOT NULL | Potential payout |
| match_ids | JSONB | NOT NULL | Match IDs (for GIN index) |
| market_keys | JSONB | NOT NULL | Market keys (for GIN index) |
| placed_at | DateTime(TZ) | DEFAULT now() | Placement time |
| settled_at | DateTime(TZ) | | Settlement time |
| payout | Float | | Actual payout |

**Enum:** `bet_status_enum` - ('pending', 'active', 'won', 'lost', 'void', 'cashed_out')

**Indexes:**
- `idx_user_bets_user_id` on `user_id`
- `idx_user_bets_status` on `status`
- `idx_user_bets_placed_at` on `placed_at`
- `idx_user_bets_match_ids` on `match_ids` (GIN index)

#### ExposureSnapshots
**Table:** `exposure_snapshots`
**Purpose:** Historical exposure tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK | Record ID |
| market_key | String(255) | NOT NULL | Market identifier |
| match_id | String(64) | | Match ID |
| total_bets | Integer | DEFAULT 0 | Total bet count |
| total_stake | Float | DEFAULT 0.0 | Total stake amount |
| single_liability | Float | DEFAULT 0.0 | Single bet liability |
| parlay_liability_mean | Float | DEFAULT 0.0 | Parlay mean liability |
| parlay_liability_var95 | Float | DEFAULT 0.0 | 95% VaR |
| parlay_liability_var99 | Float | DEFAULT 0.0 | 99% VaR |
| timestamp | DateTime(TZ) | DEFAULT now() | Snapshot time |

**Indexes:**
- `idx_exposure_snapshots_market_key` on `market_key`
- `idx_exposure_snapshots_timestamp` on `timestamp`

### 5.6 ID Mapping Tables

#### SeasonIdMapping, TeamIdMapping, PlayerIdMapping, GameIdMapping
**Purpose:** Map internal IDs to WhosScored IDs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| [entity]_id | Integer | PK | Internal ID |
| uuid_string | String(36) | UNIQUE | UUID string |
| wh_[entity]_id | Integer | | WhosScored ID |
| source_type | String(50) | DEFAULT 'tournament'/'team'/'player'/'match' | Source type |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Indexes:**
- `idx_[entity]_id_mapping_uuid` on `uuid_string`
- `idx_[entity]_id_mapping_wh_id` on `wh_[entity]_id`

#### OddsApiPlayerMapping
**Table:** `odds_api_player_mapping`
**Purpose:** Map odds API player names to internal player IDs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| odds_api_name | String(255) | UNIQUE | Player name from odds API |
| player_id | Integer | FK → players.player_id | Internal player ID |
| player_name_db | String(255) | | Internal player name |
| confidence | Float | | Match confidence (0-1) |
| verified | Boolean | DEFAULT false | Manually verified |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Indexes:**
- `idx_odds_api_player_mapping_name` on `odds_api_name`
- `idx_odds_api_player_mapping_player_id` on `player_id`

### 5.7 ML & Clustering Models

#### PlayerPositionCluster
**Table:** `player_position_clusters`
**Purpose:** Player position clustering (k-means)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| player_id | Integer | PK, FK → players.player_id | Player |
| season_id | Integer | PK | Season |
| cluster_id | Integer | NOT NULL | Cluster ID |
| centroid_x | Float | NOT NULL | Position X centroid |
| centroid_y | Float | NOT NULL | Position Y centroid |
| n_events | Integer | DEFAULT 0 | Event count |
| n_games | Integer | DEFAULT 0 | Game count |
| fitted_at | DateTime(TZ) | DEFAULT now() | Model fit time |
| model_version | String(50) | | Model version |

**Indexes:**
- `idx_player_position_clusters_cluster_id` on `cluster_id`
- `idx_player_position_clusters_season_id` on `season_id`

#### ClusterPrior
**Table:** `cluster_priors`
**Purpose:** Action priors per position cluster (Bayesian shrinkage)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| cluster_id | Integer | PK | Cluster ID |
| season_id | Integer | PK | Season |
| action | String(50) | PK | Action type |
| avg_share | Float | NOT NULL | Mean share for cluster |
| std_share | Float | | Standard deviation |
| n_players | Integer | DEFAULT 0 | Player count |
| cluster_label | String(100) | | Cluster label |
| cluster_centroid_x | Float | | Cluster X centroid |
| cluster_centroid_y | Float | | Cluster Y centroid |
| fitted_at | DateTime(TZ) | DEFAULT now() | Fit time |

**Indexes:**
- `idx_cluster_priors_cluster_id` on `cluster_id`
- `idx_cluster_priors_season_id` on `season_id`

### 5.8 Historical Odds Storage

#### SpreadLegs, OverUnderLegs, GoalscorerLegs
**Purpose:** Legacy historical odds legs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BigInteger | PK | Record ID |
| game_id | Integer | FK → games.game_id | Match |
| [entity]_id | Integer | FK | Team/Player ID |
| odds | Float | | Odds value |
| created_at | DateTime(TZ) | DEFAULT now() | Creation time |

**Indexes:**
- `idx_[table]_game_id` on `game_id`
- `idx_[table]_[entity]_id` on entity ID

---

## 6. Foreign Key Relationships

### 6.1 Core Sports Data Relationships

```
seasons (season_id)
  ↓
teams (season_id) [Backend-Odds only]
  ↓
players (team_id, season_id)
  ↓
games/tournament_schedule (home_team_id, away_team_id)
  ↓
events/match_projection (game_id, player_id, team_id)
  ↓
lineups (game_id, player_id, team_id)
```

### 6.2 Backend-Server User & Betting Flow

```
users (user_id)
  ↓
  ├→ user_prefs (user_id)
  ├→ social_accounts (user_id)
  ├→ transactions (user_id)
  │   ↓
  │   └→ withdrawal_status_history (transaction_id)
  │
  ├→ promo_redemptions (user_id)
  │   ↓
  │   └→ promotions (id)
  │
  ├→ user_tournaments (user_id, tournament_id)
  │   ↓
  │   └→ tournaments (tournament_id)
  │       ↓
  │       └→ tournament_games (tournament_id, game_id)
  │           ↓
  │           └→ tournament_schedule (match_id)
  │
  └→ userbethistory (user_id, tournament_id)
      ↓
      ├→ betslipbets (bet_id)
      │   ↓
      │   └→ playerprops/zatprops/teamprops/zaoprops (leg_id)
      │       ↓
      │       ├→ tournament_schedule (game_id)
      │       ├→ players (player_id)
      │       └→ teams (team_id)
      │
      └→ bet_promo_applications (bet_id)
          ↓
          └→ promotions (promotion_id)
```

### 6.3 Backend-Server Competition Hierarchy

```
competitions (competition_id)
  ↓
tournament_calendar (competition_id)
  ↓
  ├→ tournament_stages (tournament_id)
  │
  └→ tournament_schedule (tournament_id, competition_id)
      ↓
      ├→ lineup (match_id, team_id)
      │   ↓
      │   └→ lineup_player (lineup_id, player_id)
      │
      ├→ match_projection (match_id, player_id, team_id)
      │
      ├→ match_metadata (match_id)
      │
      ├→ predicted_lineups (game_id, team_id)
      │   ↓
      │   └→ predicted_lineup_players (predicted_lineup_id, player_id)
      │
      └→ missing_players (game_id, player_id)
```

### 6.4 Backend-Odds Odds & Statistics Flow

```
games (game_id)
  ↓
  ├→ match_statistics (game_id, team_id)
  │
  ├→ player_statistics (game_id, player_id)
  │
  ├→ zonal_statistics (game_id, player_id)
  │
  ├→ team_zonal_statistics (game_id, team_id)
  │
  ├→ moneyline_odds (game_id)
  │
  ├→ totals_odds (game_id)
  │
  ├→ spread_odds (game_id)
  │
  ├→ alternate_spreads (game_id)
  │
  ├→ alternate_totals (game_id)
  │
  ├→ player_goalscorer_odds (game_id)
  │
  ├→ player_shots_odds (game_id)
  │
  ├→ spread_legs (game_id, team_id)
  │
  ├→ over_under_legs (game_id)
  │
  └→ goalscorer_legs (game_id, player_id)
```

### 6.5 Cascade Rules

**DELETE CASCADE:**
- Most foreign keys have `ondelete="CASCADE"` to ensure referential integrity
- Example: Deleting a team cascades to delete all related players, matches, events

**UPDATE CASCADE:**
- Many foreign keys have `onupdate="CASCADE"` to propagate ID changes
- Example: Updating a team_id propagates to all related tables

**SET NULL:**
- Some optional relationships use `ondelete="SET NULL"`
- Example: `users.favorite_team_id` → `teams.team_id` (SET NULL)

**No Action (Default):**
- Some relationships have no cascade action
- Example: Odds tables typically don't cascade deletes

---

## 7. Indexes and Constraints

### 7.1 Primary Key Indexes

All tables have primary key indexes automatically created:
- **UUID Primary Keys:** `users`, `tournaments`, `promotions`, `userbethistory`, etc.
- **Integer Primary Keys:** `seasons`, `games` (Backend-Odds), most Backend-Odds tables
- **String Primary Keys:** `teams`, `players` (Backend-Server), `tournament_schedule.match_id`
- **Composite Primary Keys:** `betslipbets` (bet_id, leg_id, leg_type), `zonal_statistics` (player_id, game_id, action, zone)

### 7.2 Foreign Key Indexes

Foreign keys are indexed for join performance:
- `idx_teams_season_id` on `teams.season_id`
- `idx_players_game_id` on `players.game_id`
- `idx_players_season_id` on `players.season_id`
- `idx_players_team_id` on `players.team_id`
- `idx_events_game_id` on `events.game_id`
- `idx_events_player_id` on `events.player_id`
- Many more...

### 7.3 Query Performance Indexes

#### Backend-Server
- **Users:**
  - `idx_users_type_regdate` on (`account_type`, `registration_date`, `user_id`)

- **Transactions:**
  - `ix_transactions_user_currency_created` on (`user_id`, `currency`, `created_at DESC`)
  - `ix_transactions_idempotency` on `idempotency_key` (UNIQUE)
  - `ix_transactions_reference` on (`reference_type`, `reference_id`)
  - `ix_transactions_user_type_created` on (`user_id`, `transaction_type`, `created_at DESC`)

- **Tournament Schedule:**
  - `idx_tournament_schedule_competition_kickoff` on (`competition_id`, `kickoff_datetime`)

- **User Bet History:**
  - Partial unique index: `uq_backing_group_user` on (`backing_group_id`, `user_id`) WHERE `backing_group_id IS NOT NULL`

#### Backend-Odds
- **Events:**
  - Multiple indexes on action flags: `idx_events_is_shot`, `idx_events_is_goal`, `idx_events_is_assist`, etc.
  - `idx_events_type` on `type`
  - `idx_events_is_own_goal` on `is_own_goal`

- **Player Statistics:**
  - `idx_player_statistics_player_stats` on (`player_id`, `goals`, `assists`)

- **Zonal Statistics:**
  - `idx_zonal_statistics_action` on `action`
  - `idx_zonal_statistics_zone_type` on `zone_type`

- **User Bets:**
  - `idx_user_bets_match_ids` on `match_ids` (GIN index for JSONB array containment)

### 7.4 Unique Constraints

#### Backend-Server
- **Users:**
  - `(email, account_type)`
  - `(username, account_type)`
  - `(phone_number, account_type)`

- **Promotions:**
  - Case-insensitive unique on `custom_code` (via database index)

- **Promo Redemptions:**
  - `(user_id, promo_id)` - Prevent double redemption

- **Lineup:**
  - `(match_id, team_id)` - One lineup per team per match

- **Tournament Stages:**
  - `(tournament_id, wh_stage_id)`

#### Backend-Odds
- **Odds Tables:**
  - `(game_id, bookmaker)` for moneyline_odds
  - `(game_id, bookmaker, total_line)` for totals_odds
  - `(game_id, bookmaker, home_spread)` for spread_odds
  - Similar patterns for alternate and player prop odds

- **Player Statistics:**
  - `(player_id, game_id)`

- **ID Mapping:**
  - `uuid_string` in all mapping tables

### 7.5 Check Constraints

#### Backend-Server
- **Users:**
  - `phone_number ~ '^[+][1-9][0-9]{9,14}$'` - Phone number format
  - `role IN ('admin', 'test_user', 'user')`
  - `account_type IN ('TBG', 'AB', 'SLOUGH_TOWN')`
  - `preferred_language IN ('en', 'es', 'da')`

- **Tournament Schedule:**
  - `status IN ('NOT_STARTED', 'LIVE', 'INPROGRESS', 'FINISHED', 'CANCELLED', 'POSTPONED', 'INTERRUPTED', 'ABANDONED')`

- **Tournaments:**
  - `current_entries <= max_entries`
  - `start_timestamp < end_timestamp`
  - `entry_fee >= 0`

- **Transactions:**
  - `direction IN ('credit', 'debit')`
  - `transaction_type IN (...)` - Large enum of transaction types

- **BetSlipBets:**
  - `leg_type IN ('playerprop', 'teamprop', 'teamactionprop', 'zaoprops', 'momprop')`

- **Promotions:**
  - `type IN ('new_sign_up_bonus', 'referral', 'instant_promo', ...)` - Large enum
  - `category IN ('wallet', 'bet', 'tournament', 'raffle')`
  - `app_type IN ('AB', 'TBG', 'SLOUGH_TOWN')`

#### Backend-Odds
- **User Bets:**
  - `status` - ENUM constraint via custom type `bet_status_enum`

### 7.6 JSONB/GIN Indexes

- **user_prefs.preferences** - GIN index for fast JSONB queries
- **user_bets.match_ids** - GIN index for array containment queries
- **user_bets.market_keys** - GIN index for array containment queries

---

## 8. Data Types and Defaults

### 8.1 Common Data Types

#### Numeric Types
- **Integer:** IDs, counts, years
- **BigInteger:** Large IDs (event_id, player stats), auto-incrementing large tables
- **Float/Double:** Odds, rates, statistics (use Float for odds, Double for precise calculations)
- **Numeric(18,2):** Financial amounts (balance_after, withdrawable_after)
- **Numeric(18,8):** Exchange rates (high precision)

#### String Types
- **String:** Variable length text (username, email, names)
- **String(N):** Fixed max length (phone_number, codes, enums)
- **Text:** Unlimited text (descriptions, qualifiers, large data)

#### Date/Time Types
- **DateTime(timezone=True):** Timestamp with timezone (preferred for all timestamps)
- **Date:** Date only (rarely used)
- **Time:** Time only (rarely used)

#### Structured Types
- **JSON:** Generic JSON data (qualifiers, config)
- **JSONB:** Indexed JSON (preferences, selections, metadata)
- **ARRAY(String):** String arrays (zones, leagues, played_positions)
- **UUID/Uuid:** Universal unique identifiers

#### Boolean Types
- **Boolean:** Flags and yes/no fields

#### Custom Types
- **ENUM:** Custom enums (bet_status_enum in Backend-Odds)

### 8.2 Common Default Values

#### Auto-generated IDs
```sql
DEFAULT gen_random_uuid()  -- UUID columns
DEFAULT nextval('sequence')  -- Auto-incrementing integers
```

#### Timestamps
```sql
DEFAULT timezone('utc'::text, now())  -- Creation timestamps
```

#### Counters
```sql
DEFAULT 0  -- counts, amounts, scores
```

#### Booleans
```sql
DEFAULT false  -- is_active, flags
DEFAULT true  -- is_active (when active by default)
```

#### Text
```sql
DEFAULT ''  -- empty string defaults
DEFAULT 'value'  -- specific text defaults (e.g., 'user' for role)
```

#### JSON
```sql
DEFAULT '{}'::jsonb  -- empty JSON object
```

#### Floats
```sql
DEFAULT 0.0  -- numeric zero
DEFAULT 1.0  -- multipliers, ratios
```

### 8.3 Nullable vs Non-Nullable

#### Non-Nullable (NOT NULL)
- Primary keys (always)
- Foreign keys (usually, but optional relations are nullable)
- Required business fields (username, email, amount, transaction_type)
- Enum fields with CHECK constraints

#### Nullable
- Optional metadata (descriptions, notes)
- Foreign keys for optional relationships (favorite_team_id)
- Calculated fields that may not exist yet (hit, payout)
- Timestamps for future events (settled_at, redeemed_at)
- Denormalized fields (player_name in events - can fall back to player_id)

---

## 9. Database Features

### 9.1 Triggers and Functions

No explicit triggers or functions were found in the model files. However, SQLAlchemy event listeners are used:

```python
@event.listens_for(PlayerModel, "before_insert")
def set_name_before_insert(mapper, connection, target):
    """If name is not provided, set it to f"{first_name} {last_name}"."""
    if not target.name:
        fn = target.short_first_name or ""
        ln = target.short_last_name or ""
        target.name = f"{fn} {ln}".strip()
```

### 9.2 Views and Materialized Views

No views or materialized views are defined in the SQLAlchemy models. The application uses:
- **Direct queries** on tables
- **Python-side aggregations** for complex calculations
- **Redis caching** for frequently accessed data (exposure snapshots)

### 9.3 Partitioning Strategies

No explicit table partitioning is defined in the models. Potential partitioning candidates:

**Time-based Partitioning:**
- `transactions` - by `created_at` (monthly/quarterly)
- `events`/`match_projection` - by `created_at` or `game_id` (seasonal)
- `user_bets` - by `placed_at` (monthly)
- `exposure_snapshots` - by `timestamp` (daily/weekly)

**Range Partitioning:**
- `userbethistory` - by `created_at` (monthly)
- `player_statistics` - by `season_id`
- `odds tables` - by `created_at`

**Hash Partitioning:**
- `users` - by `user_id` (if massive scale)
- `transactions` - by `user_id` (if very high volume)

### 9.4 Data Locking

**Backend-Server Tournament Schedule:**
```python
data_locked: Boolean = DEFAULT false
data_locked_at: DateTime(TZ)
locked_by: String(50)
```

Prevents scraper from overwriting verified match data during bet settlement.

### 9.5 Idempotency

**Transactions Table:**
```python
idempotency_key: String (UNIQUE)
```

Prevents duplicate transactions on retry/race conditions.

### 9.6 Soft Deletes

No soft delete patterns (is_deleted flag) are used. The system uses:
- **CASCADE DELETE** for referential integrity
- **is_active flags** for deactivation without deletion (promotions, exchange_rates)

### 9.7 Audit Trails

**Withdrawal Status History:**
- Tracks all status changes for withdrawals
- Immutable history table

**Promo Config Snapshots:**
- `config_snapshot` in `promo_redemptions` preserves promo configuration at redemption time

**Changelog Tracking:**
- `last_seen_changelog_id` in `users` table

### 9.8 Multi-tenancy

**Account Type Separation:**
- `account_type` column in `users` ('TBG', 'AB', 'SLOUGH_TOWN')
- Unique constraints include `account_type` to allow same email/username across different apps
- Promotions have `app_type` to separate promotional campaigns

---

## 10. ERD Structure

### 10.1 Entity Relationship Diagram Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND-SERVER SCHEMA                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Users       │◄─────────┬──────────────────────┬────────────────┐
│ (user_id)    │          │                      │                │
└──────────────┘          │                      │                │
       │                  │                      │                │
       │                  │                      │                │
       ├──────────────────┼──────────────────────┘                │
       │                  │                                       │
       ▼                  ▼                                       ▼
┌──────────────┐   ┌──────────────┐                    ┌──────────────┐
│ UserPrefs    │   │Transactions  │                    │PromoRedemp-  │
│              │   │              │                    │ tions        │
└──────────────┘   └──────────────┘                    └──────────────┘
                          │                                     │
                          │                                     ▼
                          │                            ┌──────────────┐
                          │                            │ Promotions   │
                          │                            └──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Withdrawal   │
                   │ StatusHistory│
                   └──────────────┘

┌──────────────┐
│Competitions  │
│(comp_id)     │
└──────────────┘
       │
       ▼
┌──────────────┐
│Tournament    │
│Calendar      │
│(tournament_id│
└──────────────┘
       │
       ├─────────┬──────────┐
       ▼         ▼          ▼
┌──────────┐ ┌──────┐  ┌──────────────┐
│Tourna-   │ │Teams │  │ Tournament   │
│ment      │ │      │  │ Schedule     │
│Stages    │ │      │  │ (match_id)   │
└──────────┘ └──────┘  └──────────────┘
                              │
                              ├──────────┬──────────┬──────────┐
                              ▼          ▼          ▼          ▼
                       ┌──────────┐ ┌──────┐ ┌──────────┐ ┌─────────┐
                       │ Lineup   │ │Match │ │Predicted │ │Missing  │
                       │          │ │Projec│ │Lineups   │ │Players  │
                       │          │ │tion  │ │          │ │         │
                       └──────────┘ └──────┘ └──────────┘ └─────────┘
                              │
                              ├──────────┐
                              ▼          ▼
                       ┌──────────┐ ┌──────────┐
                       │ Players  │ │Teams     │
                       │          │ │          │
                       └──────────┘ └──────────┘

┌──────────────┐
│ Tournaments  │
│(tournament_id)│
└──────────────┘
       │
       ├──────────────┐
       ▼              ▼
┌──────────────┐ ┌──────────────┐
│UserTourna-   │ │Tournament    │
│ments         │ │Games         │
└──────────────┘ └──────────────┘

┌──────────────┐
│UserBetHistory│◄──────────────┐
│ (bet_id)     │               │
└──────────────┘               │
       │                       │
       ▼                       │
┌──────────────┐               │
│ BetSlipBets  │               │
│ (bet_id,     │               │
│  leg_id,     │               │
│  leg_type)   │               │
└──────────────┘               │
       │                       │
       ├───────┬───────┬───────┼───────┐
       ▼       ▼       ▼       ▼       ▼
┌─────────┐┌─────┐┌──────┐┌──────┐┌──────┐
│Player   ││ZAT  ││Team  ││ZAO   ││Mom   │
│Props    ││Props││Props ││Props ││Props │
└─────────┘└─────┘└──────┘└──────┘└──────┘

┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND-ODDS SCHEMA                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Seasons     │
│ (season_id)  │
└──────────────┘
       │
       ▼
┌──────────────┐
│  Teams       │
│ (team_id)    │
└──────────────┘
       │
       ├──────────────┐
       ▼              ▼
┌──────────────┐ ┌──────────────┐
│  Players     │ │  Games       │
│ (player_id)  │ │ (game_id)    │
└──────────────┘ └──────────────┘
       │              │
       │              ├─────────────┬──────────────┬──────────────┐
       │              ▼             ▼              ▼              ▼
       │       ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
       │       │ Events   │  │Match     │  │Player    │  │Zonal     │
       │       │          │  │Statistics│  │Statistics│  │Statistics│
       │       └──────────┘  └──────────┘  └──────────┘  └──────────┘
       │              │
       │              ├─────────────┬──────────────┬──────────────┐
       │              ▼             ▼              ▼              ▼
       │       ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
       │       │Moneyline │  │ Totals   │  │ Spread   │  │Alternate │
       │       │ Odds     │  │ Odds     │  │ Odds     │  │ Markets  │
       │       └──────────┘  └──────────┘  └──────────┘  └──────────┘
       │              │
       │              ├─────────────┬──────────────┐
       │              ▼             ▼              ▼
       │       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │       │ Player   │  │Historical│  │ ML/      │
       │       │ Props    │  │ Odds     │  │Clustering│
       │       │ Odds     │  │ Legs     │  │ Models   │
       │       └──────────┘  └──────────┘  └──────────┘
       │
       └──────────────────────────────────────────────────┐
                                                           │
┌──────────────────────────────────────────────────────┐  │
│              Trading & Risk Management                │  │
└──────────────────────────────────────────────────────┘  │
       │                                                   │
       ▼                                                   │
┌──────────────┐                                          │
│  UserBets    │◄─────────────────────────────────────────┘
│ (bet_id)     │
└──────────────┘
       │
       ▼
┌──────────────┐
│ Exposure     │
│ Snapshots    │
└──────────────┘
```

### 10.2 Key Relationships Summary

**1-to-Many:**
- `users` → `transactions`
- `users` → `userbethistory`
- `competitions` → `tournament_calendar`
- `tournament_calendar` → `tournament_schedule`
- `tournament_schedule` → `lineup`
- `seasons` → `teams` (Backend-Odds)
- `teams` → `players`
- `games` → `events`

**Many-to-Many (via junction tables):**
- `users` ↔ `tournaments` (via `user_tournaments`)
- `tournaments` ↔ `tournament_schedule` (via `tournament_games`)
- `teams` ↔ `tournament_stages` (via `team_stages`)
- `users` ↔ `promotions` (via `promo_redemptions`)

**Self-referential:**
- `events.related_id` → `events.id` (event relationships)

**Cross-system references (via WhosScored IDs):**
- `Backend-Server.teams.wh_team_id` ↔ `Backend-Odds.teams.wh_team_id`
- `Backend-Server.players.wh_player_id` ↔ `Backend-Odds.players.wh_player_id`
- `Backend-Server.tournament_schedule.wh_match_id` ↔ `Backend-Odds.games.wh_match_id` (via mapping)

### 10.3 Shared Data Integration Points

Both systems share core sports data through WhosScored IDs:

**Integration Pattern:**
1. Backend-Odds scrapes and stores raw sports data with WhosScored IDs
2. ID mapping tables convert WhosScored IDs to UUID-based internal IDs
3. Backend-Server references these mapped IDs for betting operations
4. Both systems maintain their own copies of core entities (teams, players, matches)

**Mapping Tables:**
- `season_id_mapping`
- `team_id_mapping`
- `player_id_mapping`
- `game_id_mapping`
- `odds_api_player_mapping`

**Synchronization:**
- WhosScored IDs serve as the common key
- Data flows: Backend-Odds (scrape) → Mapping → Backend-Server (betting)
- Both systems can independently query their own schemas

---

## Appendix A: Table Count Summary

### Backend-Server Tables: 51
1. competitions
2. tournament_calendar
3. tournament_stages
4. tournament_schedule
5. lineup
6. lineup_player
7. teams
8. players
9. match_projection
10. users
11. user_prefs
12. social_accounts
13. tournaments
14. user_tournaments
15. zone_configs
16. withdrawal_status_history
17. transactions
18. exchange_rates
19. userbethistory
20. betslipbets
21. tournament_games
22. playerprops
23. zatprops
24. teamprops
25. zaoprops
26. related_events
27. promotions
28. daily_bonus_redemptions
29. weekly_bonus_redemptions
30. promo_redemptions
31. admin_codes
32. player_stats
33. match_metadata
34. predicted_lineups
35. predicted_lineup_players
36. missing_players
37. test_table
38. team_stages
39. mappings
40. leaderboard_bh
41. shop_packages
42. game_notification_tracking
43. bet_notification_tracking
44. notification_outbox
45. provider_id_mapping
46. credit_coupons
47. iap_purchases
48. player_heatmap_coordinates
49. momprops
50. cart_sessions
51. woocommerce_orders

### Backend-Odds Tables: 44
1. seasons
2. teams
3. games
4. match_statistics
5. players
6. events
7. player_season_stats_fbref
8. player_statistics
9. lineups
10. zonal_statistics
11. team_zonal_statistics
12. season_id_mapping
13. team_id_mapping
14. player_id_mapping
15. game_id_mapping
16. spreadlegs
17. overunderlegs
18. goalscorerlegs
19. missing_players
20. predicted_lineups
21. predicted_lineup_players
22. player_stats
23. player_position_clusters
24. cluster_priors
25. user_bets
26. exposure_snapshots
27. moneyline_odds
28. totals_odds
29. spread_odds
30. alternate_spreads
31. alternate_totals
32. half_moneyline
33. half_spreads
34. half_totals
35. btts_odds
36. double_chance_odds
37. draw_no_bet_odds
38. team_totals_odds
39. corner_totals_odds
40. corner_spreads_odds
41. card_totals_odds
42. card_spreads_odds
43. player_goalscorer_odds
44. odds_api_player_mapping
... and more player prop odds tables

### Shared Tables (conceptually): 7
1. seasons
2. teams
3. players
4. games / tournament_schedule
5. events / match_projection
6. lineups
7. player_statistics (different schemas)

---

## Appendix B: Key Differences Between Systems

| Aspect | Backend-Server | Backend-Odds |
|--------|---------------|--------------|
| **Primary Key Type** | UUID (String) | Integer (Auto-increment) |
| **ID Strategy** | UUID for all main entities | Integer for sports data, mapping via WhosScored IDs |
| **Focus** | User management, betting, transactions | Odds calculation, statistics, market data |
| **Match Entity** | `tournament_schedule` (String match_id) | `games` (Integer game_id) |
| **Player ID** | String (UUID) | Integer |
| **Team ID** | String (UUID) | Integer |
| **Season Relationship** | Indirect via tournament_calendar | Direct foreign key to seasons |
| **Odds Storage** | Not stored (queries Backend-Odds) | Comprehensive historical odds |
| **Betting Logic** | Complete betting system | Trading & exposure tracking |
| **User Data** | Full user accounts & profiles | Only bet tracking (no user accounts) |
| **Financial System** | Ledger system with transactions | Limited (exposure snapshots) |
| **Promotions** | Full promo management | None |
| **Migrations** | 258+ files | 26 files |
| **Complexity** | High (business logic) | Medium-High (data science) |

---

## Appendix C: Schema Evolution Patterns

### Recent Changes (2024-2026)

**Ledger System (Jan 2026):**
- Phase 1: Added ledger columns to transactions
- Phase 2: Enforced non-null constraints
- Impact: Enabled O(1) balance lookups

**Promotion System Enhancements:**
- Added bonus_bet promo type
- Added deposit_matching promo type
- Added config_snapshot to promo_redemptions
- Added is_active flag to promotions

**Data Locking (Dec 2025):**
- Added data_locked, data_locked_at, locked_by to tournament_schedule
- Prevents scraper overwrites during bet settlement

**Set Piece Tracking (Dec 2025):**
- Added set piece action columns to multiple tables
- Enhanced event tracking for corner kicks, free kicks, throw-ins

**WhosScored Integration:**
- Added wh_* ID columns to all shared entities
- Created mapping tables for ID conversion
- Unified data flow from scraper to betting system

---

*End of Documentation*
