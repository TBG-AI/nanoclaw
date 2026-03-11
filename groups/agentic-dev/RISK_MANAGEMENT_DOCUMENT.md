# Risk & Fraud Management System Documentation
## Backend-Server at /workspace/extra/programming/Backend-Server

**Document Version:** 1.0
**Last Updated:** 2026-03-03
**System:** TBG Betting Platform

---

## Table of Contents
1. [Overview](#overview)
2. [User Tier System & Limits](#user-tier-system--limits)
3. [Betting Limits & Restrictions](#betting-limits--restrictions)
4. [Exposure Tracking Mechanisms](#exposure-tracking-mechanisms)
5. [Velocity Checks & Rate Limits](#velocity-checks--rate-limits)
6. [Fraud Detection Patterns](#fraud-detection-patterns)
7. [Manual Review Triggers](#manual-review-triggers)
8. [Multi-Accounting Detection](#multi-accounting-detection)
9. [KYC & Verification System](#kyc--verification-system)
10. [Configuration & Feature Flags](#configuration--feature-flags)

---

## 1. Overview

The Backend-Server implements a comprehensive risk and fraud management system to protect against abuse, fraud, and ensure responsible gambling practices. The system is built using Domain-Driven Design principles with clear separation between domain logic and infrastructure.

### Key Components
- **Domain Layer**: `/src/backend_server/domain/` - Pure business rules
- **Application Layer**: `/src/backend_server/application/services/` - Use cases and orchestration
- **Infrastructure Layer**: `/src/backend_server/infrastructure/` - External integrations

---

## 2. User Tier System & Limits

### 2.1 Account Types

**Location:** `/src/backend_server/domain/constants.py`

```python
class AccountType:
    TBG = "TBG"              # Standard retail accounts
    AB = "AB"                # Internal/test accounts (Copenhagen)
    SLOUGH_TOWN = "SLOUGH_TOWN"  # Partner accounts
```

### 2.2 Initial Balance & Limits by Account Type

| Account Type | Initial Credits | Initial Coins | Weekly Deposit Limit | Max Entry Amount |
|--------------|----------------|---------------|---------------------|------------------|
| TBG          | $5             | 500           | $500                | $100             |
| AB           | $20            | 0             | $500                | $50,000          |
| SLOUGH_TOWN  | $50            | 0             | $500                | $50,000          |

**Constants:**
```python
# TBG Accounts
INITIAL_BALANCE = 5
INITIAL_COIN_BALANCE = 500
INITIAL_WEEKLY_DEPOSIT_LIMIT = 500
INITIAL_MAX_ENTRY_AMOUNT = 100

# AB Accounts
INITIAL_BALANCE_AB = 20
INITIAL_COIN_BALANCE_AB = 0
INITIAL_WEEKLY_DEPOSIT_LIMIT_AB = 500
MAX_ENTRY_AMOUNT_AB = 50000

# SLOUGH_TOWN Accounts
INITIAL_BALANCE_SLOUGH_TOWN = 50
INITIAL_COIN_BALANCE_SLOUGH_TOWN = 0
INITAL_WEEKLY_DEPOSIT_LIMIT_SLOUGH_TOWN = 500
MAX_ENTRY_AMOUNT_SLOUGH_TOWN = 50000
```

### 2.3 Universal Limits

**Location:** `/src/backend_server/domain/constants.py`

```python
MAX_WEEKLY_DEPOSIT_LIMIT = 500        # Hard cap on deposits per week
MAX_ENTRY_AMOUNT = 100                # Maximum single bet for TBG accounts
MINIMUM_COIN_BALANCE = 0.0            # Minimum coin balance threshold
MAX_SELF_EXCLUSION_DAYS = 365         # Maximum self-exclusion period
MAX_SELF_EXCLUSION_CANCEL_DAYS = 2    # Days before end to cancel exclusion
```

### 2.4 Responsible Gambling Controls

**Location:** `/src/backend_server/domain/user_account/user.py`

#### Weekly Deposit Limit
- Users can set custom weekly deposit limits (max $500)
- Limit changes have a 7-day cooldown period
- Tracked via `weekly_deposit_limited_requested_at` timestamp

```python
def set_weekly_deposit_limit(self, limit: float):
    if limit < 0 or limit > MAX_WEEKLY_DEPOSIT_LIMIT:
        raise DomainSetWeeklyDepositLimitError(max_value=MAX_WEEKLY_DEPOSIT_LIMIT)
    if (self.weekly_deposit_limited_requested_at is not None
        and self.weekly_deposit_limited_requested_at > time_config.now() - timedelta(days=7)):
        raise DomainWeeklyDepositLimitEarlyRequestError()
    self.weekly_deposit_limit = limit
    self.weekly_deposit_limited_requested_at = time_config.now()
```

#### Max Entry Amount (Per Bet)
- Users can set maximum single bet amount
- Enforced per identical bet (same legs/picks)
- Aggregates multiple bets on same entry

```python
def set_max_entry_amount(self, amount: int):
    if amount < 0 or amount > MAX_ENTRY_AMOUNT:
        raise DomainSetMaxEntryAmountError(max_value=MAX_ENTRY_AMOUNT)
    self.max_entry_amount = amount
```

#### Self-Exclusion
- Users can self-exclude for up to 365 days
- Account deactivated during exclusion period
- Can cancel within 2 days of start date only

---

## 3. Betting Limits & Restrictions

### 3.1 Bet Backing Limits

**Location:** `/src/backend_server/config/bet_backing_config.py`

```python
_DEFAULT_CONFIG = {
    "enabled": True,
    "max_backers": 20,                    # Maximum users backing a single bet
    "min_wager": 5.00,                    # Minimum wager to back a bet
    "multiplier_per_backer": 0.05,        # 5% profit boost per backer
    "max_profit_multiplier": 2.0,         # 2x max profit multiplier
}
```

**Bet Backing Rules:**
- Minimum wager: $5.00
- Maximum 20 backers per bet
- Each backer adds 5% profit multiplier
- Capped at 200% (2x) total multiplier
- Cannot back your own bets
- Cannot back after games start
- Cannot back promo bets

### 3.2 Odds & Payout Limits

**Promotion Odds Limits:**
- Minimum odds requirements vary by promotion
- Maximum odds limits for bonus bets
- Rivalry boost: 30% profit boost, capped at $25 extra payout

```python
RIVALRY_BOOST_PCT = 0.30           # 30% profit boost
RIVALRY_MAX_EXTRA_PAYOUT = 25.0    # Cap on extra payout
```

### 3.3 Live Betting Restrictions

**Location:** `/src/backend_server/config/config.py`

```python
class LiveCheckMode(str, Enum):
    ALWAYS = "always"      # All games live (dev/test)
    WINDOW = "window"      # Time-window check

# Live betting window configuration
LIVE_CHECK_WINDOW_BEFORE = 10     # 10 minutes before kickoff
LIVE_CHECK_WINDOW_AFTER = 240     # 240 minutes (4 hours) after kickoff
```

**Odds Acceptance Modes:**
- `ACCEPT_FAVORABLE`: Only accept if odds improve
- `ACCEPT_ANY`: Accept any odds changes

### 3.4 Max Entry Amount Enforcement

**Location:** `/src/backend_server/application/services/bets/user_bet_service.py`

For credit bets (not coins), the system aggregates wagers on identical bets:

```python
# Check max_entry_amount for credit bets only
if not request.is_coin and effective_wager > 0 and user.max_entry_amount is not None:
    bet_leg_keys = BetLegKeys.from_picks(request.parlay_bet.picks)

    existing_wager = await self.user_bet_history_repository.get_total_wager_for_identical_bets(
        user_id=user.user_id,
        is_coin=False,
        bet_leg_keys=bet_leg_keys,
    )

    total_wager = existing_wager + effective_wager
    if total_wager > user.max_entry_amount:
        raise MaxEntryAmountExceededError(
            f"Total stake on this entry (${total_wager}) exceeds max entry amount "
            f"(${user.max_entry_amount}). You already have ${existing_wager} stake "
            f"on identical entries."
        )
```

---

## 4. Exposure Tracking Mechanisms

### 4.1 Per-Game Void Policy Multipliers

**Location:** `/src/backend_server/application/services/bets/user_bet_service.py`

The system tracks per-game multipliers for void policy adjustment:

```python
async def _compute_game_multipliers(self, parlay_picks: List[Any]) -> Dict[str, float]:
    """
    Compute per-game multipliers for void policy adjustment.
    For single-leg games: returns individual leg odds
    For multi-leg SGP: returns correlation-adjusted price
    """
    game_multipliers: Dict[str, float] = {}
    picks_by_game: Dict[str, List[Any]] = defaultdict(list)

    # Group picks by game_id
    for pick in parlay_picks:
        picks_by_game[str(pick.game_id)].append(pick)

    for game_id, game_picks in picks_by_game.items():
        request = ParlayRequest(picks=game_picks, live=False)
        odds_data = await self.odds_client.get_odds_full(request)
        game_multipliers[game_id] = odds_data["combined_odds"]

    return game_multipliers
```

### 4.2 Balance Tracking

**Dual Currency System:**
- **Credits**: Real money currency
- **Coins**: Virtual currency with minimum balance protection

```python
MINIMUM_COIN_BALANCE = 0.0  # Never allow coin balance below this
```

### 4.3 Bet Data Caching

All bet data cached in Redis with:
- `bet_id`: Unique identifier
- `wager`: Effective wager amount
- `payout`: Expected payout
- `base_payout`: Raw payout before promos
- `is_coin`: Currency type flag
- `game_multipliers`: Per-game exposure
- `generated_at`: Timestamp for freshness check

---

## 5. Velocity Checks & Rate Limits

### 5.1 Deposit Rate Limiting

**Location:** `/src/backend_server/application/services/deposits/deposit_service.py`

```python
class DepositService:
    MAX_FAILED_ATTEMPTS = 3
    RATE_LIMIT_WINDOW_SECONDS = 15 * 60  # 15 minutes
    _failed_attempts: Dict[str, List[float]] = defaultdict(list)

    def _check_rate_limit(self, user_id: str) -> None:
        """Reject if user has too many recent failed payment attempts."""
        now = time.monotonic()
        cutoff = now - self.RATE_LIMIT_WINDOW_SECONDS
        attempts = [t for t in self._failed_attempts[user_id] if t > cutoff]

        if len(attempts) >= self.MAX_FAILED_ATTEMPTS:
            minutes_left = max(1, int((attempts[0] + self.RATE_LIMIT_WINDOW_SECONDS - now) / 60))
            raise TooManyFailedAttemptsError(
                f"Too many failed payment attempts. Please wait ~{minutes_left} minutes."
            )
```

**Key Metrics:**
- **3 failed attempts** trigger rate limit
- **15-minute** lockout window
- In-memory storage (resets on server restart)
- Per-user tracking

### 5.2 Weekly Deposit Velocity

**Location:** `/src/backend_server/application/services/deposits/deposit_service.py`

```python
# Check weekly deposit limit
total_weekly_deposit = await self.transaction_repo.get_total_weekly_deposit(user.user_id)
current_weekly = Money(total_weekly_deposit, Currency.USD)

can_deposit, reason = deposit.validate_deposit(current_weekly)
if not can_deposit:
    remaining_amount = max(0.0, user.weekly_deposit_limit - total_weekly_deposit)
    reset_date = get_week_end_date(time_config.now())

    raise DomainWeeklyDepositLimitExceededError(
        reason,
        details={
            "weekly_deposit_limit": user.weekly_deposit_limit,
            "remaining_amount": remaining_amount,
            "reset_date": reset_date.isoformat(),
        },
    )
```

### 5.3 Favorite Team Change Cooldown

**Location:** `/src/backend_server/domain/user_account/user.py`

```python
def set_favorite_team(self, team_id: str):
    """Set the user's favorite team with a 7-day cooldown."""
    if self.favorite_team_id is not None and self.favorite_team_changeable_at is not None:
        if time_config.now() < self.favorite_team_changeable_at:
            raise DomainFavoriteTeamCooldownError(
                changeable_at=self.favorite_team_changeable_at.isoformat()
            )
    self.favorite_team_id = team_id
    self.favorite_team_changeable_at = time_config.now() + timedelta(days=7)
```

**Purpose:** Prevents abuse of rivalry promotions by constantly changing favorite team.

---

## 6. Fraud Detection Patterns

### 6.1 Referral Fraud Detection System

**Location:** `/src/backend_server/domain/referral/audit.py`

The system uses a sophisticated multi-signal fraud detection algorithm:

#### Signal Types

**Strong Signals (high confidence):**
1. **IP Exact Match**: Same device/network
2. **PayPal Email Match**: Both users withdraw to same PayPal account

**Weak Signals (individually explainable):**
1. **IP Prefix Match**: Same /24 subnet (ISP area)
2. **Geographic Distance**: < 5 km apart
3. **Email Similarity**: Similar TBG account emails
4. **PayPal-TBG Email Overlap**: One user's PayPal email ≈ other's TBG email

#### Detection Rules

```python
@dataclass
class ReferralPairSignals:
    referrer_id: str
    referred_id: str
    ip_exact_match: bool = False
    ip_prefix_match: bool = False
    distance_km: Optional[float] = None
    email_similar: bool = False
    referrer_has_kyc: bool = False
    referred_has_kyc: bool = False
    referred_deposited: bool = False
    referred_has_played: bool = False
    paypal_email_match: bool = False
    paypal_tbg_email_overlap: bool = False
```

**Flag Types:**
1. **SELF_REFERRAL**: Same person creating multiple accounts
2. **MULTI_ACCOUNTING**: Different people sharing devices
3. **BULK_SCAM**: Multiple deposit-only referrals without playing

#### Detection Logic

```python
def evaluate_signals(result: AuditResult) -> None:
    """
    Flagging Logic:

    1. PayPal email match → INSTANT FLAG (strongest signal)
       - Two accounts withdrawing to same PayPal = same person
       - Flags regardless of KYC status

    2. IP exact match + missing KYC → SELF_REFERRAL
       - High confidence with identity not verified

    3. 2+ weak signals + missing KYC → SELF_REFERRAL
       - Multiple suspicious patterns without verification

    4. Both have KYC + IP exact match → MULTI_ACCOUNTING
       - Verified identities but same device (possible friend/family ID abuse)

    5. 3+ deposit-only referrals without KYC → BULK_SCAM
       - Pattern of deposit-trigger-withdraw without actual play
    """
```

### 6.2 Email Similarity Detection

```python
def check_email_similarity(email1: str, email2: str) -> bool:
    """
    Detects email aliasing tricks:
    1. Plus addressing: john+ref1@gmail.com → john@gmail.com
    2. Gmail dot trick: j.o.h.n@gmail.com → john@gmail.com
    3. Digit stripping: john1@domain → john2@domain (same base)
    4. Levenshtein distance ≤ 2 (typos/variations)
    """
```

### 6.3 Bulk Scam Detection

Automatically flags users with **3 or more** referrals that:
- Deposited (triggered referral bonus)
- Never placed bets (didn't actually play)
- Don't have KYC verification

---

## 7. Manual Review Triggers

### 7.1 KYC Review Statuses

**Location:** `/src/backend_server/domain/user_account/kyc.py`

```python
class KycStatus(str, Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    APPROVED = "Approved"
    DECLINED = "Declined"
    REVIEW = "In Review"           # Manual review required
    EXPIRED = "Expired"
    ABANDONED = "Abandoned"
    KYC_EXPIRED = "Kyc Expired"
```

**Alert-Triggering Statuses:**
- `DECLINED`: Critical severity Slack alert
- `REVIEW`: Warning severity Slack alert

### 7.2 Audit System

**Location:** `/src/backend_server/domain/user_account/kyc.py`

```python
class AuditStatus(str, Enum):
    CLEAN = "clean"      # No suspicious activity
    FLAGGED = "flagged"  # Requires review
    BANNED = "banned"    # Account suspended
```

### 7.3 Withdrawal Review Triggers

**Configuration:** `/src/backend_server/config/config.py`

```python
REQUIRE_KYC_FOR_WITHDRAWAL = True  # KYC required for withdrawals
```

**Manual Review Triggers:**
1. **KYC Status != APPROVED**: Automatic block
2. **Referral Audit Flagged**: Requires approval
3. **First Withdrawal**: Extra scrutiny
4. **Large Withdrawals**: Threshold-based review
5. **Velocity Patterns**: Multiple rapid withdrawals

### 7.4 Referral Audit Notifications

**Location:** `/src/backend_server/schedule/notifs/pending_withdrawals.py`

System automatically audits users on withdrawal requests and sends Slack notifications with:
- User ID and username
- Audit status and flag type
- Matched signals (IP, email, PayPal, geo)
- Referral relationship details
- Deposit and play history

---

## 8. Multi-Accounting Detection

### 8.1 Detection Signals

**Primary Indicators:**
1. **Same IP Address** (exact match)
2. **Same PayPal Withdrawal Email**
3. **Similar Email Addresses** (aliasing detection)
4. **Geographic Proximity** (< 5km)
5. **Same Device Fingerprint** (via PostHog)

### 8.2 IP Tracking

**Location:** `/src/backend_server/domain/referral/audit.py`

```python
def check_ip_prefix_match(ip1: str, ip2: str) -> bool:
    """Check if two IPs share the first 3 octets (same /24 subnet)."""
    parts1 = ip1.split(".")
    parts2 = ip2.split(".")
    if len(parts1) < 3 or len(parts2) < 3:
        return False
    return parts1[:3] == parts2[:3]
```

### 8.3 Geographic Distance

```python
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance between two points in km."""
    # Standard haversine formula implementation
    # Flags if users are < 5km apart
```

### 8.4 Device Fingerprinting

**Integration:** PostHog Analytics

Tracks:
- Last IP address
- Last latitude/longitude
- Device properties
- Browser fingerprint

### 8.5 Account Restrictions

**AB Accounts (Internal/Test):**

```python
@property
def is_ab_account(self) -> bool:
    """AB accounts have special restrictions:
    - Cannot deposit
    - Cannot withdraw
    - Used for testing bet flows without real money
    """
    return self.account_type.upper() == AccountType.AB
```

---

## 9. KYC & Verification System

### 9.1 KYC Features

**Location:** `/src/backend_server/domain/user_account/kyc.py`

```python
class KycFeature(str, Enum):
    OCR = "OCR"                              # Document scanning
    OCR_NFC = "OCR + NFC"                    # + NFC chip reading
    OCR_AML = "OCR + AML"                    # + Anti-money laundering
    OCR_NFC_AML = "OCR + NFC + AML"
    OCR_FACE = "OCR + FACE"                  # + Facial recognition
    OCR_NFC_FACE = "OCR + NFC + FACE"
    OCR_FACE_AML = "OCR + FACE + AML"
    OCR_NFC_FACE_AML = "OCR + NFC + FACE + AML"  # Full verification
    ALL = "OCR + NFC + FACE + AML"
```

### 9.2 Verification Requirements

**Withdrawal Requirements:**
- KYC Status = `APPROVED` required
- Blocks withdrawals if KYC declined/expired
- Terminal statuses require new verification session

### 9.3 KYC Provider Integration

**Provider:** Didit (Document Verification)

```python
class KYCProvider:
    DIDIT = "didit"
```

### 9.4 Session Management

**Terminal Statuses** (require new session):
- `EXPIRED`: Session timed out
- `DECLINED`: Verification failed
- `ABANDONED`: User left verification
- `KYC_EXPIRED`: Previous verification expired

---

## 10. Configuration & Feature Flags

### 10.1 Deposit Configuration

**Location:** `/src/backend_server/config/config.py`

```python
# Deposit mode controls
DEPOSIT_MODE: str = "both"  # Options: "cash_only", "shop_packages_only", "both"

# Withdrawal controls
ENABLE_WITHDRAWALS: bool = True
REQUIRE_KYC_FOR_WITHDRAWAL: bool = True
```

**Deposit Modes:**
- `cash_only`: Direct dollar deposits only
- `shop_packages_only`: Must purchase packages
- `both`: All deposit methods available

### 10.2 QA & Testing Bypass

```python
# QA: Bypass game time checks (non-prod only)
QA_BYPASS_GAME_TIME: bool = os.getenv("ENV", "dev").lower() != "prod"
```

**Purpose:** Allows testing with past games in non-production environments.

### 10.3 Live Betting Configuration

```python
class LiveCheckMode(str, Enum):
    ALWAYS = "always"      # Every game returns is_live=True (dev/test)
    WINDOW = "window"      # Time-window pre-filter + API check

LIVE_CHECK_MODE = "always"
LIVE_CHECK_WINDOW_BEFORE = 10    # minutes before kickoff
LIVE_CHECK_WINDOW_AFTER = 240    # minutes after kickoff (4 hours)
```

### 10.4 MOM (Man of Match) Betting Thresholds

```python
MOM_MIN_PLAYERS_MATCH_WIDE = 22      # Minimum players with ratings (match-wide)
MOM_MIN_PLAYERS_TEAM_SPECIFIC = 11   # Minimum players (team-specific)
```

### 10.5 Referral Program Configuration

**Location:** `/src/backend_server/domain/referral/value_objects.py`

```python
@dataclass(frozen=True)
class ReferralRewardConfig:
    # Purchase threshold for rewards
    threshold: float = 9.99

    # Redemption limits
    redemption_limit: int = 100
    limit_period_days: int = 30

    # Referrer rewards
    referrer_amount: float = 50.0
    referrer_coin_amount: int = 500

    # Friend rewards
    friend_amount: float = 50.0
    friend_coin_amount: int = 500

    # Reward mechanism
    reward_type: RewardType = RewardType.PLAYTHROUGH

    # Welcome offer blocking
    blocks_welcome_offer: bool = True
```

**Reward Types:**
- `PLAYTHROUGH`: Direct credits/coins to balance
- `BONUS_BET`: Grants bonus bets with expiration
- `DEPOSIT_MATCH`: Referrer reward + friend deposit match

### 10.6 Feature Flags (PostHog)

**Location:** `/src/backend_server/config/feature_flags.py`

Key feature flags:
- `TUNE_BET_BACKING`: Bet backing configuration
- Rivalry promotions
- Live betting toggles
- Promotional campaigns

---

## Summary of Risk Controls

### Financial Controls
| Control | Threshold | Cooldown |
|---------|-----------|----------|
| Weekly Deposit Limit | $500 | 7 days to change |
| Max Entry Amount (TBG) | $100 | None |
| Max Entry Amount (AB) | $50,000 | None |
| Deposit Rate Limit | 3 failed attempts | 15 minutes |
| Self-Exclusion | Up to 365 days | 2-day cancel window |

### Fraud Detection
| Signal Type | Threshold | Action |
|-------------|-----------|--------|
| PayPal Email Match | Exact match | Instant flag |
| IP Exact Match | Same IP + No KYC | Flag for review |
| Weak Signal Combo | 2+ signals + No KYC | Flag for review |
| Bulk Referral Scam | 3+ deposit-only refs | Flag for review |
| Geographic Distance | < 5km | Weak signal |

### Verification Requirements
| Action | KYC Required | Additional Checks |
|--------|--------------|-------------------|
| Registration | No | Email/phone verification |
| First Deposit | No | Rate limiting |
| Withdrawal | Yes | Referral audit + balance check |
| Large Withdrawal | Yes | Manual review |

### Betting Restrictions
| Restriction | Limit | Account Type |
|-------------|-------|--------------|
| Min Backing Wager | $5.00 | All |
| Max Backers per Bet | 20 | All |
| Profit Multiplier Cap | 2.0x | All |
| Live Bet Window Before | 10 min | All |
| Live Bet Window After | 240 min | All |

---

## Risk Management Services Architecture

### Domain Services
1. **User Domain** (`domain/user_account/user.py`)
   - Responsible gambling controls
   - Account type restrictions
   - Balance validation

2. **Referral Audit Domain** (`domain/referral/audit.py`)
   - Pure fraud detection logic
   - Signal evaluation algorithms
   - No I/O dependencies

3. **Promotion Domain** (`domain/promotion/`)
   - Bet promo validation
   - Bonus bet rules
   - Odds limits

### Application Services
1. **DepositService** (`application/services/deposits/deposit_service.py`)
   - Rate limiting
   - Weekly velocity checks
   - Deposit mode validation

2. **ReferralAuditService** (`application/services/referrals/audit_service.py`)
   - Signal collection orchestration
   - PostHog integration
   - Audit record persistence

3. **UserBetService** (`application/services/bets/user_bet_service.py`)
   - Max entry enforcement
   - Exposure tracking
   - Balance validation

### Infrastructure
1. **Repositories**
   - Audit repository (flagging/banning)
   - Transaction repository (velocity)
   - User repository (limits)

2. **External Services**
   - PostHog (analytics, device fingerprinting)
   - Didit (KYC verification)
   - PayPal (payment processing)
   - Slack (alert notifications)

---

## File Reference Index

| System Component | File Path |
|------------------|-----------|
| Constants & Limits | `/src/backend_server/domain/constants.py` |
| User Domain | `/src/backend_server/domain/user_account/user.py` |
| Referral Fraud Detection | `/src/backend_server/domain/referral/audit.py` |
| KYC System | `/src/backend_server/domain/user_account/kyc.py` |
| Deposit Service | `/src/backend_server/application/services/deposits/deposit_service.py` |
| Bet Service | `/src/backend_server/application/services/bets/user_bet_service.py` |
| Audit Service | `/src/backend_server/application/services/referrals/audit_service.py` |
| Configuration | `/src/backend_server/config/config.py` |
| Bet Backing Config | `/src/backend_server/config/bet_backing_config.py` |
| Error Constants | `/src/backend_server/infrastructure/api/rest/constants.py` |

---

**End of Document**
