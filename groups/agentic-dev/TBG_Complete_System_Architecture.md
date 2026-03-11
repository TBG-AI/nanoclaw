# The Beautiful Game (TBG) - Complete System Architecture & User Flow

## Executive Summary

The Beautiful Game (TBG) is a **narrative-driven fantasy soccer betting platform** that combines innovative zonal betting mechanics with social features and real-time odds calculation. The system consists of three main repositories working together to deliver a seamless user experience from registration through bet placement and settlement.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                              │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 15 + React Native)                               │
│  - Web App (desktop/mobile browser)                                 │
│  - Mobile App (iOS/Android via Expo)                                │
│  - Admin Dashboard                                                   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ ↑
                         REST + WebSocket
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND SERVICES                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Backend-Server (Python/FastAPI)          Backend-Odds (Python)     │
│  ┌──────────────────────────────┐        ┌────────────────────────┐│
│  │ • User Management            │◄───────►│ • Odds Calculation    ││
│  │ • Authentication             │         │ • Statistical Models  ││
│  │ • Bet Management             │         │ • Live Odds Streaming ││
│  │ • Payment Processing         │         │ • Parlay Pricing      ││
│  │ • Promotions System          │         │ • Market Calibration  ││
│  │ • Tournament Management      │         │ • Risk Management     ││
│  │ • Social Features            │         │                        ││
│  │ • Notifications              │         │                        ││
│  └──────────────────────────────┘         └────────────────────────┘│
│                ↓ ↑                                  ↓ ↑              │
└────────────────┼─┼──────────────────────────────────┼─┼──────────────┘
                 ↓ ↑                                  ↓ ↑
┌────────────────┴─┴──────────────────────────────────┴─┴──────────────┐
│                      DATA LAYER                                       │
├───────────────────────────────────────────────────────────────────────┤
│  PostgreSQL (AWS RDS)      Redis (ElastiCache)    Kafka/Redpanda    │
│  • User data               • Cache layer          • Event streaming  │
│  • Bets & transactions     • Session storage      • Real-time odds   │
│  • Match/player stats      • Live odds            • Job queue        │
│  • Odds parameters         • Rate limiting        • Analytics        │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Breakdown

### Frontend (Next.js 15 + React Native)

| Category | Web | Mobile | Shared |
|----------|-----|--------|--------|
| **Framework** | Next.js 15.5.7 | React Native 0.79.5 + Expo | React 19.0.1 |
| **State Management** | Zustand 5.0.6 | Zustand 5.0.6 | TanStack Query 5.83.0 |
| **Styling** | Tailwind CSS 4 | Native styles | Shared theme |
| **3D Graphics** | Three.js + R3F | Expo GL | - |
| **API Client** | Axios 1.12.2 | Axios 1.12.2 | Shared config |
| **Auth** | NextAuth / JWT | JWT | Token storage |
| **Analytics** | PostHog + GA4 | PostHog + Firebase | Feature flags |
| **Payments** | PayPal SDK | Apple Pay / PayPal | Shared flows |

### Backend-Server (Python FastAPI)

| Category | Technology | Purpose |
|----------|------------|---------|
| **Framework** | FastAPI | Async REST API |
| **Database** | PostgreSQL + asyncpg | Primary data store |
| **ORM** | SQLAlchemy 2.0 | Database models |
| **Migrations** | Alembic | Schema versioning |
| **Cache** | Redis 7.0 | Session, rate limiting |
| **Auth** | JWT + PyJWT | Token-based auth |
| **Payments** | PayPal SDK | Payment processing |
| **Notifications** | Twilio | SMS verification |
| **Cloud** | AWS (boto3, S3) | File storage |
| **Monitoring** | OpenTelemetry | Observability |
| **Scraping** | Playwright, Selenium | Sports data |

### Backend-Odds (Python FastAPI)

| Category | Technology | Purpose |
|----------|------------|---------|
| **Framework** | FastAPI + WebSocket | REST + real-time streaming |
| **Statistics** | NumPy, Pandas, SciPy | Data processing |
| **ML** | PyTorch (CPU), scikit-learn | Model training |
| **Statistical Models** | Statsmodels, pyvinecopulib | GLM, copulas |
| **Database** | PostgreSQL + asyncpg | Historical stats |
| **Cache** | Redis | Fast odds retrieval |
| **Message Queue** | Kafka/Redpanda (AWS MSK) | Event streaming |
| **Monitoring** | OpenTelemetry + Grafana | Tracing, metrics |

---

## Complete User Journey: From Registration to Payout

### Phase 1: User Onboarding

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1: Registration & Authentication                                │
└──────────────────────────────────────────────────────────────────────┘

[Frontend] User visits /download or web app
    ↓
[Frontend] Chooses authentication method:
    • Native (email/password)
    • Google OAuth → /google/oauth/callback
    • Apple OAuth → /apple/oauth/callback
    ↓
[Backend-Server] POST /users/register
    • Validates email/phone uniqueness
    • Hashes password (bcrypt)
    • Creates user record in PostgreSQL
    • Generates JWT access + refresh tokens
    • Sends verification SMS (Twilio)
    ↓
[Frontend] Stores JWT in:
    • Web: httpOnly cookie + localStorage
    • Mobile: SecureStore (encrypted)
    ↓
[Frontend] Sets globalUser in Zustand store
    ↓
[Backend-Server] Background tasks:
    • Create default user settings
    • Initialize referral code
    • Set up promotional eligibility
    • Send welcome email
    ↓
[Frontend] Redirect to onboarding flow:
    • Tutorial/guide
    • Location detection (for geo-compliance)
    • Push notification permission (mobile)
    ↓
[Backend-Server] POST /users/active_status
    • Mark user as active
    • Track device info
    • Initialize analytics session (PostHog)
```

**Key Files:**
- Frontend: `packages/shared/src/api/routes/users/auth.ts`
- Backend: `src/backend_server/application/services/user_accounts/user_service.py`
- Backend: `src/backend_server/infrastructure/api/rest/routes/users/auth.py`

---

### Phase 2: Account Funding (First Deposit)

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 2: KYC Verification & Deposit                                   │
└──────────────────────────────────────────────────────────────────────┘

[Frontend] User attempts to place bet or clicks "Deposit"
    ↓
[Frontend] Check balance → trigger deposit modal if insufficient
    ↓
[Frontend] Navigate to /payment/purchase
    • Display payment options
    • Show bonus offers (first deposit bonus)
    ↓
[Frontend] User selects payment method:
    • PayPal
    • Credit/Debit Card
    • Apple Pay (mobile only)
    ↓
[Backend-Server] GET /users/kyc_status
    • Check if KYC verification required
    • Based on amount threshold ($50+)
    • Based on jurisdiction (US states)
    ↓
IF KYC REQUIRED:
    [Backend-Server] POST /users/verify
        • Generate verification session (Persona/Onfido)
        • Return verification URL
        ↓
    [Frontend] Redirect to verification URL
        • User uploads ID + selfie
        • Liveness check
        ↓
    [Backend-Server] Webhook from verification provider
        • Update user.kyc_verified = True
        • Store verification metadata
        ↓
    [Frontend] Return to purchase flow

[Frontend] Initiate payment:
    PayPal Flow:
        • SDK creates order
        • User approves in PayPal popup
        • Capture payment

    Card Flow:
        • Collect card details (PCI-compliant form)
        • Tokenize card (Square SDK)
        • 3DS authentication if required
        ↓
[Backend-Server] POST /transactions/cashier
    {
        "amount": 100.00,
        "currency": "USD",
        "payment_method": "paypal",
        "payment_token": "ORDER-123..."
    }
    ↓
[Backend-Server] Process deposit:
    • Validate payment token
    • Call PayPal/Square API to capture funds
    • Create transaction record
    • Update user.balance += amount
    • Apply deposit bonus if eligible
    • Trigger promotional grants
    ↓
[Backend-Server] Response:
    {
        "transaction_id": "tx_123",
        "new_balance": 100.00,
        "bonus_granted": 10.00,
        "status": "completed"
    }
    ↓
[Frontend] Update UI:
    • Show success message
    • Update balance in Zustand store
    • Trigger confetti animation
    • Navigate to /zonal-fantasy
```

**Key Files:**
- Frontend: `apps/web/src/app/payment/purchase/page.tsx`
- Backend: `src/backend_server/application/services/payments/payment_service.py`
- Backend: `src/backend_server/infrastructure/api/rest/routes/transactions/cashier.py`

---

### Phase 3: Bet Creation (Core User Experience)

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 3: Zonal Fantasy Bet Creation                                  │
└──────────────────────────────────────────────────────────────────────┘

[Frontend] User navigates to /zonal-fantasy
    ↓
[Frontend] Fetch available matches:
    GET /info/games/upcoming
    ↓
[Backend-Server] Query PostgreSQL:
    • Games in next 7 days
    • Status = 'scheduled'
    • Include team info, kickoff times
    ↓
[Frontend] Display match list with:
    • Team names & logos
    • League badges
    • Kickoff countdown timers
    ↓
[Frontend] User selects match → Load interactive pitch
    ↓
[Frontend] Initialize bet crafter:
    • 3D soccer pitch (Three.js / React Three Fiber)
    • 5x3 zone grid overlay
    • Team strip (team selection interface)
    ↓
[Frontend] User builds bet:
    Step 1: Select Action Type
        • Goals
        • Shots
        • Shots on Target
        • Assists
        • Tackles
        • etc.

    Step 2: Drag Teams onto Zones
        • Click team from TeamStrip
        • Drag onto pitch zone (e.g., B2, C3)
        • Visual feedback (zone highlights)

    Step 3: Set Line (threshold)
        • Over/Under toggle
        • Line value (0.5, 1.5, 2.5, etc.)

    [Frontend State] Store in crafterStore (Zustand):
        {
            game_id: 12345,
            legs: [
                {
                    action: "goals",
                    team_id: 789,
                    zones: ["b2"],
                    line: 0.5,
                    direction: "over"
                },
                {
                    action: "shots",
                    team_id: 790,
                    zones: ["c2", "c3"],
                    line: 2.5,
                    direction: "over"
                }
            ]
        }
    ↓
[Frontend] Real-time odds calculation:
    Debounced API call (500ms after last change)
    ↓
[Backend-Odds] POST /get_parlay_odds
    Request body:
    {
        "game_id": 12345,
        "legs": [
            {
                "action": "goals",
                "team_id": 789,
                "zones": ["b2"],
                "line": 0.5,
                "direction": "over"
            },
            ...
        ],
        "use_bounds": "conservative"
    }
    ↓
[Backend-Odds] Odds calculation pipeline:

    1. Load Parameters:
        • Team/player action rates (TAM)
        • Zonal distributions (ZDM)
        • Copula correlation matrix
        • Cached in Redis (10min TTL)

    2. For each leg:
        a) Calculate team action rate: λ (Poisson/NB parameter)
           GLM: log(λ) = β₀ + θ_team + φ_opponent + δ_home

        b) Get zonal probability: π_z (Dirichlet posterior)
           π_z = (α₀ × prior + observed_counts) / (α₀ + total)

        c) Expected count in zone: μ = λ × π_z

        d) Tail probability: P = 1 - F_Poisson(L-1; μ)

        e) Convert to odds: odds = 1 / P

        f) Apply vig/margin: odds × (1 - margin)

    3. Parlay correlation adjustment:
        • Monte Carlo simulation (10k samples)
        • Vine copula for action dependencies
        • Simulate correlated outcomes
        • Calculate joint probability

    4. Final parlay odds:
        odds_parlay = 1 / P_joint

    5. Risk adjustments:
        • Bounds: conservative (upper), moderate (mean), aggressive (lower)
        • Exposure limits per game
        • User tier-based caps
    ↓
[Backend-Odds] Response:
    {
        "parlay_odds": 5.23,
        "leg_odds": [3.2, 1.85],
        "expected_value": -0.02,  # House edge
        "correlation_factor": 0.92,
        "payout": 523.00  # for $100 stake
    }
    ↓
[Frontend] Display betslip:
    • Visual odds display
    • Payout calculator (reactive to stake input)
    • EV indicator (green if +EV, red if -EV)
    • Terms acknowledgment
    ↓
[Frontend] User adjusts stake:
    • Min: $0.10
    • Max: Lesser of (balance, game_limit, user_tier_limit)
    • Real-time payout update
    ↓
[Frontend] User clicks "Place Bet"
    ↓
[Backend-Server] POST /bets/place_bet
    Request:
    {
        "game_id": 12345,
        "legs": [...],
        "stake": 100.00,
        "odds": 5.23,
        "bet_type": "parlay"
    }
    ↓
[Backend-Server] Validation:
    • User balance >= stake
    • Game not started (kickoff_time > now)
    • Odds within tolerance (±5% of current)
    • User not restricted/banned
    • Bet within limits (exposure, game, user tier)
    • Legs are valid (actions exist, zones valid)
    ↓
[Backend-Server] Create bet record:
    INSERT INTO userbethistory (
        user_id, game_id, stake, odds, potential_payout,
        legs_json, status, placed_at
    )
    ↓
[Backend-Server] Deduct balance:
    UPDATE users SET balance = balance - stake WHERE user_id = ?
    ↓
[Backend-Server] Update exposure tracking:
    • Game-level exposure
    • Action-level exposure
    • User bet count
    ↓
[Backend-Server] Trigger side effects:
    • Send bet confirmation notification
    • Update tournament standings if applicable
    • Track analytics event (PostHog)
    • Check promotional triggers
    ↓
[Backend-Server] Response:
    {
        "bet_id": "bet_abc123",
        "status": "placed",
        "placed_at": "2026-03-03T10:30:00Z",
        "new_balance": 900.00
    }
    ↓
[Frontend] Success flow:
    • Show success animation
    • Update balance in Zustand
    • Add bet to history store
    • Offer share options:
        - Generate share card (canvas)
        - Social media links
        - Team Up link (bet backing)
    • Navigate to bet detail page
```

**Key Files:**
- Frontend: `apps/web/src/app/zonal-fantasy/page.tsx`
- Frontend: `packages/shared/src/stores/crafterStores.ts`
- Frontend: `packages/shared/src/api/routes/bets/submission.ts`
- Backend-Server: `src/backend_server/application/services/bets/user_bet_service.py`
- Backend-Odds: `src/backend_odds/core/prediction_models/orchestration/main_pipeline.py`
- Backend-Odds: `src/backend_odds/infrastructure/api/rest/routes/odds.py`

---

### Phase 4: Live Match & Odds Updates

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 4: Real-Time Match Tracking                                    │
└──────────────────────────────────────────────────────────────────────┘

PRE-MATCH:
[Backend-Odds] Background task (every 60s):
    • run_odds_broadcast()
    • Calculate odds for upcoming games
    • Update Redis cache
    • Publish to WebSocket subscribers

LIVE MATCH STARTS:
[External Data] Match kicks off
    ↓
[Backend-Server] Scraper detects match start:
    • WhoScored live feed
    • Opta data feed
    • Update game.status = 'live'
    ↓
[Backend-Odds] Kafka consumer receives event:
    Topic: odds.market_updates
    Message: {
        "game_id": 12345,
        "status": "live",
        "minute": 0,
        "score": {"home": 0, "away": 0}
    }
    ↓
[Backend-Odds] Enable live odds calculation:
    • Adjust models for in-game context
    • Apply time-decay factors
    • Update correlation structure
    ↓
[Frontend] User opens bet detail page:
    • Establish WebSocket connection
    • Subscribe to game updates

[Frontend] WebSocket connection:
    ws://api.tbg.com/odds/ws/{client_id}
    ↓
[Frontend] Send subscription message:
    {
        "type": "subscribe",
        "subscription_type": "game_odds",
        "game_id": 12345,
        "actions": ["goals", "shots"],
        "zones": ["b2", "c2"]
    }
    ↓
[Backend-Odds] Register subscription in Redis:
    Key: ws_subs:{client_id}:{game_id}
    Value: {actions, zones, timestamp}

LIVE EVENT OCCURS (e.g., Goal):
[External Data] Goal scored at 23:15
    Team: Home
    Player: #10 Silva
    Zone: B2 (left wing)
    ↓
[Backend-Server] Scraper ingests event:
    • Parse WhoScored/Opta feed
    • Validate event data
    • Store in events table
    ↓
[Backend-Server] Update match statistics:
    • Increment home_team.goals
    • Update score display
    • Recalculate in-game metrics
    ↓
[Backend-Odds] Triggered re-calculation:
    • Updated state: score 1-0, minute 23
    • Adjust expected goals remaining
    • Update action rate projections
    • Recalculate all live odds
    ↓
[Backend-Odds] Broadcast to WebSocket subscribers:
    {
        "type": "odds_update",
        "subscription_id": "game_12345",
        "timestamp": "2026-03-03T15:23:15Z",
        "event": {
            "type": "goal",
            "team": "home",
            "player_id": 10,
            "minute": 23,
            "zone": "b2"
        },
        "updated_odds": [
            {
                "leg_id": "leg_1",
                "old_odds": 3.2,
                "new_odds": 1.8,
                "status": "still_possible"
            }
        ],
        "match_state": {
            "score": {"home": 1, "away": 0},
            "minute": 23
        }
    }
    ↓
[Frontend] WebSocket receives update:
    • Parse message
    • Update UI in real-time:
        - Score display
        - Live odds ticker
        - Bet status indicator
        - Potential payout recalculation
    • Play notification sound if bet affected
    • Show toast notification
    ↓
[Frontend] User bet tracking:
    • Green: Winning / On track
    • Amber: Close / Edge case
    • Red: Losing / Unlikely
    • Live probability meter

MATCH ENDS:
[Backend-Server] Scraper detects full-time whistle
    • Update game.status = 'completed'
    • Finalize statistics
    ↓
[Backend-Server] Bet settlement job:
    • Query all bets for game_id
    • For each bet, evaluate legs:
        - Compare line vs. actual result
        - Mark leg as win/loss
    • Calculate bet outcome:
        - All legs win → payout = stake × odds
        - Any leg loss → payout = 0
        - Push (exact line) → stake refund
    ↓
[Backend-Server] Process settlements:
    UPDATE userbethistory
    SET status = 'settled',
        result = 'win'/'loss',
        payout = calculated_payout,
        settled_at = NOW()
    WHERE bet_id = ?

    UPDATE users
    SET balance = balance + payout
    WHERE user_id = ?
    ↓
[Backend-Server] Trigger notifications:
    • Push notification: "Your bet won! +$523.00"
    • Email summary (if enabled)
    • Update tournament standings
    • Award achievement badges
    ↓
[Frontend] Real-time balance update:
    • WebSocket message: balance_update
    • Update globalUser.balance
    • Show celebration animation (if win)
    • Update bet history status
```

**Key Files:**
- Frontend: `packages/shared/src/api/routes/bets/live.ts`
- Backend-Odds: `src/backend_odds/infrastructure/api/websocket/connection_manager.py`
- Backend-Odds: `src/tbg-streaming/src/tbg_streaming/services/api_ws/gateway.py`
- Backend-Server: `src/backend_server/application/services/bets/settlement_service.py`

---

### Phase 5: Social Features (Team Up / Bet Backing)

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 5: Bet Backing & Social Betting                                │
└──────────────────────────────────────────────────────────────────────┘

[Frontend] User places bet (as in Phase 3)
    ↓
[Frontend] After bet placement, show share options:
    • Copy Team Up link
    • Share to social media
    • Generate share card (visual)
    ↓
[Frontend] User clicks "Share Bet"
    ↓
[Frontend] Generate Team Up URL:
    https://tbg.com/team-up?bet_id=bet_abc123

    Or deep link for mobile:
    tbg://team-up/bet_abc123
    ↓
[Frontend] User shares link via:
    • WhatsApp
    • Twitter/X
    • Discord
    • iMessage
    • Copy to clipboard

FRIEND RECEIVES LINK:
[Frontend] Friend opens link
    • Parse URL parameters
    • Extract bet_id
    ↓
[Backend-Server] GET /bets/{bet_id}/public
    • Fetch bet details (anonymized)
    • Return odds, legs, potential payout
    • Check if still open for backing
    ↓
[Frontend] Display TeamUpContent component:
    • Original bet details
    • Odds breakdown
    • Visual representation (pitch with zones)
    • Original bettor name/avatar (if public profile)
    • Time remaining to back
    ↓
[Frontend] Friend clicks "Back This Bet"
    ↓
[Frontend] Authentication check:
    IF not logged in:
        • Show signup/login modal
        • Store bet_id in deep link store
        • Complete auth flow
        • Return to backing flow

    IF logged in:
        • Proceed to backing
    ↓
[Frontend] Backing interface:
    • Suggested stake (10-100% of original)
    • Custom stake input
    • Backing terms:
        - Same odds as original bet
        - Payout shared proportionally
        - Cannot cancel once backed
    ↓
[Frontend] User confirms backing
    ↓
[Backend-Server] POST /bets/{bet_id}/back
    Request:
    {
        "stake": 50.00,
        "backing_user_id": "user_xyz"
    }
    ↓
[Backend-Server] Validation:
    • Bet not started (game kickoff > now)
    • Backer balance >= stake
    • Backer != original bettor
    • Bet still open for backing
    • Total backing <= configured limit (e.g., 5x original)
    ↓
[Backend-Server] Create backing record:
    INSERT INTO bet_backings (
        bet_id,
        backing_user_id,
        stake,
        share_percentage,
        backed_at
    )

    share_percentage = backer_stake / (original_stake + total_backings)
    ↓
[Backend-Server] Deduct backer balance:
    UPDATE users SET balance = balance - stake
    WHERE user_id = backing_user_id
    ↓
[Backend-Server] Update bet record:
    UPDATE userbethistory
    SET total_backed = total_backed + stake,
        backer_count = backer_count + 1
    WHERE bet_id = bet_id
    ↓
[Backend-Server] Notify original bettor:
    • Push notification: "John just backed your bet with $50!"
    • Update bet detail page UI
    ↓
[Backend-Server] Response:
    {
        "backing_id": "back_123",
        "share_percentage": 33.33,
        "potential_payout": 174.33,
        "status": "active"
    }
    ↓
[Frontend] Success flow:
    • Show confirmation
    • Update balance
    • Navigate to shared bet tracking page
    • Show both users on bet detail

BET SETTLEMENT (WIN SCENARIO):
[Backend-Server] After match ends:
    • Calculate total payout
    • Distribute proportionally:
        - Original bettor: (original_stake / total_stakes) × payout
        - Each backer: (backer_stake / total_stakes) × payout

    Example:
        Original: $100 @ 5.23 odds → potential $523
        Backer: $50
        Total stakes: $150
        Total payout: $784.50

        Original gets: (100/150) × 784.50 = $523.00
        Backer gets: (50/150) × 784.50 = $261.50
    ↓
[Backend-Server] Credit accounts:
    UPDATE users SET balance = balance + share_payout
    WHERE user_id IN (original_bettor, backers...)
    ↓
[Backend-Server] Send notifications:
    • Push to all participants
    • Show breakdown of winnings
    ↓
[Frontend] Celebration UI:
    • Confetti animation
    • Winnings breakdown
    • Social sharing options
    • "Back More Bets" CTA
```

**Key Files:**
- Frontend: `apps/web/src/app/team-up/[betId]/page.tsx`
- Frontend: `packages/shared/src/api/routes/bets/backing.ts`
- Backend-Server: `src/backend_server/application/services/bets/backing_service.py`

---

### Phase 6: Withdrawal & Payout

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 6: User Withdrawal Flow                                        │
└──────────────────────────────────────────────────────────────────────┘

[Frontend] User navigates to /payment/withdrawal
    ↓
[Backend-Server] GET /users/withdrawal_eligibility
    • Check KYC status (must be verified)
    • Check minimum balance ($10)
    • Check pending bets (may require wait)
    • Check withdrawal cooldown (24h after deposit)
    • Check withdrawal limits (daily/monthly)
    ↓
[Backend-Server] Response:
    {
        "eligible": true/false,
        "available_balance": 450.00,
        "locked_balance": 100.00,  # pending bets
        "reason": "kyc_required" / "min_balance" / null
    }
    ↓
IF NOT ELIGIBLE:
    [Frontend] Show blocking message:
        • KYC required → redirect to verification
        • Min balance → show deposit CTA
        • Cooldown → show timer
        ↓
    Exit flow

IF ELIGIBLE:
[Frontend] Display withdrawal interface:
    • Available balance: $450.00
    • Withdrawal methods:
        - Original payment method (preferred)
        - PayPal email
        - Bank transfer (ACH)
    • Amount input
    • Fee display (if applicable)
    ↓
[Frontend] User enters withdrawal amount:
    • Min: $10
    • Max: available_balance
    • Real-time fee calculation
    • Net payout display
    ↓
[Frontend] User submits withdrawal request:
    ↓
[Backend-Server] POST /transactions/withdrawals
    Request:
    {
        "amount": 450.00,
        "method": "paypal",
        "destination": "user@example.com"
    }
    ↓
[Backend-Server] Validation:
    • Amount <= available_balance
    • Method supported for user's region
    • Destination valid (email format, bank account verified)
    • User not flagged for fraud review
    • Within daily/monthly limits
    ↓
[Backend-Server] Create withdrawal record:
    INSERT INTO transactions (
        user_id,
        type,
        amount,
        status,
        method,
        destination,
        requested_at
    ) VALUES (
        user_id,
        'withdrawal',
        450.00,
        'pending',
        'paypal',
        'user@example.com',
        NOW()
    )
    ↓
[Backend-Server] Place hold on balance:
    UPDATE users
    SET balance = balance - amount,
        locked_balance = locked_balance + amount
    WHERE user_id = user_id
    ↓
[Backend-Server] Trigger approval workflow:
    IF amount > $1000 OR user.risk_level = 'high':
        • Queue for manual review
        • Notify admin dashboard
        • Email compliance team
    ELSE:
        • Auto-approve
        • Process immediately
    ↓
[Backend-Server] Response:
    {
        "transaction_id": "tx_withdrawal_123",
        "status": "pending",
        "estimated_completion": "2026-03-05T12:00:00Z",
        "message": "Your withdrawal is being processed"
    }
    ↓
[Frontend] Show pending status:
    • Confirmation message
    • Transaction ID
    • Expected completion date
    • Support contact info

PROCESSING (BACKEND ASYNC JOB):
[Backend-Server] Withdrawal processor job (runs every 5 min):
    • Query pending withdrawals
    • For each withdrawal:
        ↓
[Backend-Server] Call payment provider API:
    PayPal Flow:
        POST https://api.paypal.com/v1/payments/payouts
        {
            "sender_batch_header": {
                "sender_batch_id": "tx_withdrawal_123",
                "email_subject": "You have a payout!"
            },
            "items": [{
                "recipient_type": "EMAIL",
                "amount": {
                    "value": "450.00",
                    "currency": "USD"
                },
                "receiver": "user@example.com",
                "note": "TBG Withdrawal"
            }]
        }
        ↓
    PayPal Response:
        {
            "batch_header": {
                "payout_batch_id": "PAYOUTITEM_ABC123",
                "batch_status": "SUCCESS"
            }
        }

    Bank Transfer Flow:
        • Use Plaid/Stripe for ACH
        • 3-5 business days
        • Verify bank account ownership
    ↓
[Backend-Server] Update transaction:
    UPDATE transactions
    SET status = 'completed',
        external_id = 'PAYOUTITEM_ABC123',
        completed_at = NOW()
    WHERE transaction_id = tx_withdrawal_123
    ↓
[Backend-Server] Unlock balance:
    UPDATE users
    SET locked_balance = locked_balance - amount
    WHERE user_id = user_id
    ↓
[Backend-Server] Send confirmation:
    • Push notification: "Withdrawal complete! $450 sent to PayPal"
    • Email receipt
    • Update transaction history
    ↓
[Frontend] Real-time update:
    • WebSocket message or polling
    • Show completed status
    • Update transaction history UI
    • Show success message

ERROR HANDLING:
IF withdrawal fails (insufficient PayPal balance, invalid account, etc.):
    [Backend-Server] Rollback:
        • UPDATE transactions SET status = 'failed'
        • Return funds: balance += amount, locked_balance -= amount
        • Send notification with reason
        • Suggest alternative withdrawal method
```

**Key Files:**
- Frontend: `apps/web/src/app/payment/withdrawal/page.tsx`
- Backend-Server: `src/backend_server/application/services/payments/withdrawal_service.py`
- Backend-Server: `src/backend_server/infrastructure/api/rest/routes/transactions/withdrawals.py`

---

## System Integration Map

### API Communication Flow

```
Frontend ←→ Backend-Server ←→ Backend-Odds

1. User Management:
   Frontend → Backend-Server
   - POST /users/register
   - POST /users/login
   - GET /users/profile
   - PUT /users/settings

2. Bet Placement:
   Frontend → Backend-Server → Backend-Odds
   - Frontend: GET /info/games/upcoming (from Backend-Server)
   - Frontend: POST /get_parlay_odds (from Backend-Odds via proxy)
   - Frontend: POST /bets/place_bet (to Backend-Server)
   - Backend-Server: Validates bet, stores in DB
   - Backend-Server: MAY call Backend-Odds for odds verification

3. Live Odds:
   Frontend ←WebSocket← Backend-Odds
   - Direct WebSocket connection to Backend-Odds
   - Real-time odds streaming
   - No Backend-Server intermediary (performance)

4. Payment Processing:
   Frontend → Backend-Server → External (PayPal/Square)
   - Frontend: Initiates payment flow
   - Backend-Server: Orchestrates with payment provider
   - Backend-Server: Updates user balance

5. Match Data:
   External Scrapers → Backend-Server → PostgreSQL
   Backend-Odds: Reads match data from shared PostgreSQL
```

### Database Schema Integration

**Shared Tables (accessed by both Backend-Server & Backend-Odds):**
- `games` - Match schedules
- `teams` - Team information
- `players` - Player rosters
- `seasons` - Season/competition data
- `match_statistics` - Post-match stats
- `events` - Play-by-play events

**Backend-Server Exclusive:**
- `users` - User accounts
- `userbethistory` - Bet records
- `transactions` - Payments/withdrawals
- `bonus_grants` - Promotional bonuses
- `tournaments` - Tournament data
- `referral_codes` - Referral tracking

**Backend-Odds Exclusive:**
- `model_parameters` - Fitted model params (TAM, PAM, ZDM)
- `odds_cache` - Pre-calculated odds
- `external_odds` - Market odds from other books
- `exposure_tracking` - Risk management

**Sync Points:**
- Backend-Server writes to `games` when scraper updates
- Backend-Odds reads `games` for odds calculation
- Backend-Server reads `model_parameters` for bet validation (rarely)

### Redis Key Namespaces

```
Backend-Server:
- session:{user_id} - User sessions
- rate_limit:{ip}:{endpoint} - Rate limiting
- cache:promotions:{user_id} - User promos
- active_users:{user_id} - Online status

Backend-Odds:
- odds_cache:{game_id}:{leg_hash} - Cached odds
- live_odds:{game_id} - Live match odds
- ws_subs:{client_id}:{game_id} - WebSocket subscriptions
- exposure:{game_id} - Real-time exposure tracking
- model_params:{competition_id} - Model parameters
```

### Kafka Topics

```
Produced by Backend-Odds:
- odds.market_updates - External odds ingestion
- odds.compute_jobs - Async calculation requests
- odds.compute_results - Calculation results
- odds.history_1s - Time-series odds (1s granularity)
- odds.history_15s - Aggregated odds (15s)

Consumed by Backend-Server:
- odds.market_updates - For display on frontend
- odds.compute_results - For bet validation

Consumed by Backend-Odds:
- odds.compute_jobs - Process heavy computations
```

---

## Data Flow Diagrams

### Odds Calculation Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ODDS CALCULATION PIPELINE                       │
└─────────────────────────────────────────────────────────────────────┘

Historical Data (PostgreSQL)
    ↓
┌───────────────────────────────┐
│ 1. Data Loading & Preparation │
│   - Query match statistics     │
│   - Filter by competition      │
│   - Rolling window (20 games)  │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 2. Team Action Model (TAM)    │
│   - GLM regression             │
│   - Poisson/NegBin fit         │
│   - Output: λ (action rate)    │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 3. Player Share Model (PAM)   │
│   - Beta-Binomial model        │
│   - Wilson confidence intervals│
│   - Output: r (share rate)     │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 4. Zonal Dirichlet Model (ZDM)│
│   - Bayesian Dirichlet prior   │
│   - Team-specific zones        │
│   - Output: π (zone prob)      │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 5. Expected Value Calculation  │
│   μ = λ × r × π                │
│   (team rate × player share    │
│    × zone probability)         │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 6. Tail Probability           │
│   P(X > L) = 1 - F_Poisson(L-1; μ)│
│   (Probability over line)      │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 7. Parlay Correlation         │
│   - Vine copula simulation     │
│   - Monte Carlo (10k samples)  │
│   - Joint probability          │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 8. Odds Conversion            │
│   odds = 1 / P_joint           │
│   Apply vig/margin             │
│   Bounds adjustment            │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 9. Cache & Serve              │
│   - Store in Redis (10min TTL)│
│   - Return to Frontend         │
└───────────────────────────────┘
```

### Bet Lifecycle State Machine

```
┌────────────┐
│  DRAFTED   │ (Frontend: User building bet)
└─────┬──────┘
      │ User clicks "Place Bet"
      ↓
┌────────────┐
│  PENDING   │ (Backend: Validating & processing)
└─────┬──────┘
      │ Validation passes
      ↓
┌────────────┐
│   PLACED   │ (Bet active, waiting for match)
└─────┬──────┘
      │ Match starts
      ↓
┌────────────┐
│    LIVE    │ (Match in progress, tracking)
└─────┬──────┘
      │ Match ends
      ↓
┌────────────┐
│ SETTLING   │ (Backend: Evaluating legs)
└─────┬──────┘
      │ All legs evaluated
      ↓
      ├──────────┬──────────┐
      ↓          ↓          ↓
┌──────────┐ ┌──────┐ ┌──────────┐
│   WON    │ │ LOST │ │  PUSHED  │
│(Pay user)│ │(Keep)│ │ (Refund) │
└──────────┘ └──────┘ └──────────┘
      │          │          │
      └──────────┴──────────┘
                 ↓
          ┌────────────┐
          │  SETTLED   │ (Final state)
          └────────────┘
```

---

## Key System Features

### 1. Real-Time Capabilities

**WebSocket Architecture:**
- Frontend establishes persistent connection to Backend-Odds
- Subscription-based model (per-game, per-action, per-zone)
- Server-side connection pooling (max 10k concurrent)
- Automatic reconnection with exponential backoff
- Heartbeat/ping every 30s to keep alive

**Update Frequency:**
- Pre-match odds: 60s interval (background broadcast)
- Live odds: <5s latency after event ingestion
- Score updates: Real-time (as events occur)
- Balance updates: Immediate after transaction

### 2. Scalability & Performance

**Caching Strategy:**
```
Frontend Cache:
    └─ TanStack Query (5min stale time)
       └─ Match list, standings, user profile

Backend-Server Cache:
    └─ Redis (Session store, rate limits)
       └─ TTL: 30min-24h depending on data

Backend-Odds Cache:
    └─ Redis (Odds results, model params)
       └─ TTL: 10min (odds), 1h (params)
          └─ Invalidation: On model refit

Database:
    └─ PostgreSQL Connection Pooling
       └─ Backend-Server: 40 + 20 overflow
       └─ Backend-Odds: 40 + 20 overflow
```

**Load Distribution:**
- Frontend: Static assets via CDN (Vercel Edge)
- Backend-Server: ALB → ECS tasks (2-10 auto-scaled)
- Backend-Odds: Separate cluster (CPU-intensive)
- Database: Read replicas for analytics queries

### 3. Observability

**Tracing (OpenTelemetry):**
- Request-ID propagation across services
- Span creation for each major operation
- Exporters: Grafana Cloud, AWS X-Ray
- Custom attributes: user_id, game_id, bet_id

**Metrics (Prometheus):**
- Request rate, latency, error rate (RED metrics)
- Business metrics: bets/min, odds calculation time
- System metrics: CPU, memory, connection pool size
- Custom counters: bet_placement_total, odds_cache_hits

**Logging (Structured JSON):**
- Python: python-json-logger
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Context: user_id, request_id, game_id
- Aggregation: CloudWatch Logs + Grafana Loki

**Alerting:**
- PagerDuty integration
- Alert on: API error rate >1%, odds calculation >5s, DB connection pool >80%
- Slack notifications for non-critical warnings

### 4. Security & Compliance

**Authentication:**
- JWT tokens (access: 1h, refresh: 7d)
- Secure cookie storage (httpOnly, SameSite=Strict)
- Mobile: Encrypted SecureStore (iOS Keychain, Android Keystore)
- OAuth: Google, Apple Sign-In

**Authorization:**
- Role-based access control (RBAC)
- Permission decorators on API routes
- Geo-compliance: IP geolocation checks
- Age verification: KYC integration

**Data Protection:**
- PCI-DSS compliance (payment data)
- Tokenization: Never store raw card numbers
- Encryption: AES-256 for PII at rest
- TLS 1.3 for all API communication

**Fraud Prevention:**
- Velocity checks: Max bets per user per hour
- Anomaly detection: Unusual betting patterns
- Multi-accounting detection: Device fingerprinting
- Manual review queue: High-value transactions

### 5. Testing Strategy

**Frontend:**
- Unit: Vitest for component logic
- Integration: Playwright for E2E flows
- Visual: Percy for snapshot testing
- Mobile: Detox for native interactions

**Backend-Server:**
- Unit: pytest for service layer
- Integration: pytest-asyncio for API tests
- E2E: Postman collections for critical flows
- Load: k6 for performance testing

**Backend-Odds:**
- Unit: pytest for model logic
- Statistical: Backtesting against historical results
- Integration: Mock Kafka/Redis for pipelines
- Validation: Pandera schemas for data integrity

---

## Next Steps for Complete Understanding

### Immediate Action Items:

1. **Deep Dive into Bet Settlement Logic:**
   - Read: `Backend-Server/src/backend_server/application/services/bets/settlement_service.py`
   - Understand: How legs are evaluated, tie-breaking rules, partial refunds

2. **Explore Promotional System:**
   - Read: `Backend-Server/src/backend_server/application/services/promotions/`
   - Understand: First deposit bonus, referral rewards, bet boosts, tournament prizes

3. **Study Fraud & Risk Management:**
   - Read: `Backend-Server/src/backend_server/application/services/risk/`
   - Understand: User tier system, exposure limits, manual review triggers

4. **Examine Statistical Models in Detail:**
   - Read: `Backend-Odds/src/backend_odds/core/prediction_models/`
   - Understand: GLM fitting, copula simulation, Dirichlet updates

5. **Review Admin Dashboard:**
   - Explore: `Frontend/apps/admin/`
   - Understand: Trading dashboard, policy engine, user management

6. **Analyze Tournament System:**
   - Read: `Backend-Server/src/backend_server/application/services/tournaments/`
   - Understand: Free-to-play tournaments, leaderboard calculations, prize distribution

7. **Investigate Mobile-Specific Features:**
   - Explore: `Frontend/apps/mobile/src/`
   - Understand: Push notifications, deep linking, native integrations

8. **Study Scraping Infrastructure:**
   - Read: `Backend-Server/src/scraper/`
   - Understand: WhoScored parser, Opta integration, data validation

9. **Review Deployment & CI/CD:**
   - Read: `Backend-Server/.github/workflows/`, `Backend-Odds/scripts/`
   - Understand: Docker build, ECS deployment, migration strategies

10. **Explore Multi-Brand Support:**
    - Read: `Frontend/packages/brands/`
    - Understand: TBG vs. AB configurations, white-label approach

### Documentation Tasks:

1. **Create Architecture Decision Records (ADRs):**
   - Document key design choices (e.g., why separate odds service, WebSocket vs polling)

2. **Build Sequence Diagrams:**
   - For complex flows (parlay calculation, live odds update, withdrawal approval)

3. **Map Database Relationships:**
   - ERD diagrams showing all tables and foreign keys

4. **Document API Contracts:**
   - OpenAPI/Swagger specs for all endpoints
   - Request/response examples with error cases

5. **Write Runbooks:**
   - Incident response procedures
   - Deployment checklists
   - Rollback procedures

---

## Conclusion

The Beautiful Game (TBG) is a sophisticated, multi-tier betting platform that seamlessly integrates:

1. **Frontend Excellence:** Modern React/Next.js with 3D visualizations, real-time updates, and mobile-first design
2. **Backend Reliability:** Scalable Python/FastAPI services with clean architecture and comprehensive business logic
3. **Statistical Rigor:** Advanced ML models for fair and accurate odds calculation
4. **User Experience:** Social features, promotional systems, and engaging interactions
5. **Operational Excellence:** Observability, security, and fraud prevention built-in

The system handles the complete user journey from registration through bet placement, live tracking, settlement, and payout with millisecond-level precision and enterprise-grade reliability.

**Total System Complexity:**
- **Frontend:** ~50k LOC (TypeScript/React)
- **Backend-Server:** ~30k LOC (Python)
- **Backend-Odds:** ~25k LOC (Python + statistical models)
- **Total:** ~105k lines of production code

This documentation provides a foundation for understanding the complete architecture. Refer to the "Next Steps" section above to dive deeper into specific subsystems as needed.
