# Backend-Odds Statistical Models and Algorithms
## Comprehensive Technical Documentation

**Repository:** Backend-Odds
**Location:** /workspace/extra/programming/Backend-Odds
**Documentation Date:** 2026-03-03

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Team Action Model (TAM)](#2-team-action-model-tam)
3. [Player Action Model (PAM)](#3-player-action-model-pam)
4. [Zonal Dirichlet Model (ZDM)](#4-zonal-dirichlet-model-zdm)
5. [Vine Copula Implementation](#5-vine-copula-implementation)
6. [Monte Carlo Simulation Engine](#6-monte-carlo-simulation-engine)
7. [Odds Calculation Pipeline](#7-odds-calculation-pipeline)
8. [Model Calibration and Validation](#8-model-calibration-and-validation)
9. [External Odds Ingestion](#9-external-odds-ingestion)
10. [Market Making and Risk Management](#10-market-making-and-risk-management)

---

## 1. System Architecture Overview

### 1.1 Core Components

The Backend-Odds system implements a hierarchical Bayesian sports betting odds calculation engine with three primary statistical models:

```
MainPredictionPipeline
├── TeamModelPipeline (TAM)
│   └── TeamActionModel (GLM with copulas)
├── PlayerActionPipeline (PAM)
│   └── PlayerActionModel (Beta-binomial rates)
├── ZonalModelPipeline (ZDM)
│   └── ZonalDirichletModel (Bayesian spatial priors)
├── SimulationEngine (Monte Carlo)
├── PricingPipeline (Vig & adjustments)
└── CalibrationEngine (Market odds alignment)
```

**File Locations:**
- Main Pipeline: `/src/backend_odds/core/prediction_models/orchestration/main_pipeline.py`
- Team Models: `/src/backend_odds/core/prediction_models/team_models/stats_team_model.py`
- Player Models: `/src/backend_odds/core/prediction_models/player_action_models/player_action_model.py`
- Zonal Models: `/src/backend_odds/core/prediction_models/zonal_models/dirichlet.py`

### 1.2 Data Flow

```
Historical Match Data
    ↓
[Model Fitting & Training]
    ↓
Parameter Storage (JSON)
    ↓
[Match Prediction Request]
    ↓
Team GLM → Action Rates (λ)
    ↓
Vine Copula → Correlated Samples
    ↓
Player Rates → Action Distribution
    ↓
Zonal Priors → Spatial Allocation
    ↓
Monte Carlo Simulation (3000+ runs)
    ↓
Aggregate Statistics
    ↓
Probability Calculations
    ↓
Vig Application
    ↓
Final Odds Output
```

---

## 2. Team Action Model (TAM)

### 2.1 Mathematical Foundation

The Team Action Model uses Generalized Linear Models (GLM) with either Poisson or Negative Binomial distributions to model team-level action counts.

**File:** `/src/backend_odds/core/prediction_models/team_models/stats_team_model.py`

### 2.2 Model Specification

For action type `a` (goals, shots, assists, etc.), the count for team `i` against opponent `j` at home/away `h`:

**Log-Linear Predictor:**
```
log(λ_ija) = β₀ₐ + αᵢₐ + γⱼₐ + δₐ·h
```

Where:
- `λ_ija` = Expected action count
- `β₀ₐ` = Global intercept for action `a`
- `αᵢₐ` = Team `i` ability for action `a`
- `γⱼₐ` = Opponent `j` defensive counter-ability for action `a`
- `δₐ` = Home advantage effect for action `a`
- `h` = 1 if home, 0 if away

**Distribution Selection:**

The model tests for overdispersion using Pearson residuals:

```python
# Fit Poisson first
pois_mod = Poisson(y, X)
pois_res = pois_mod.fit()
mu_hat = pois_res.predict()

# Calculate dispersion
pearson = (y - mu_hat) / sqrt(mu_hat)
dispersion = sum(pearson²) / (n - p)

# If dispersion > 1.20, use Negative Binomial
if dispersion > 1.20:
    model = NegativeBinomial(y, X, loglike_method='nb2')
else:
    model = Poisson(y, X)
```

**Negative Binomial (NB2) Parameterization:**
```
Var[Y] = μ + α·μ²
```

Where `α` is the dispersion parameter estimated via maximum likelihood.

### 2.3 Formula Specification

Using `patsy` for design matrix construction:

```python
formula = f"{action} ~ C(team_id, Treatment(reference={ref_team})) +
                        C(opponent_id, Treatment(reference={ref_team})) +
                        is_home"
```

This creates indicator variables with treatment contrasts, setting one team as reference (baseline).

### 2.4 Confidence Bounds

Parameters are stored with confidence intervals using standard errors from the Hessian matrix:

```python
z_score = norm.ppf((1 + confidence_level) / 2)  # Default: 0.95 → 1.96

bounds = (param - z_score * stderr, param + z_score * stderr)
```

**Fallback for singular Hessian:**
```python
if isnan(stderr) or stderr == 0:
    # Use 20% of parameter value or global std of existing parameters
    half_bound = max(abs(param) * 0.2, 0.1)
    bounds = (param - half_bound, param + half_bound)
```

### 2.5 Insufficient Data Handling

Teams with fewer than `min_games_for_model` (default: 10) receive averaged parameters:

```python
# Calculate averages from teams with sufficient data
avg_ability = mean([team_abilities[tid][action]
                    for tid in sufficient_teams])
avg_counter = mean([team_counter_abilities[tid][action]
                    for tid in sufficient_teams])

# Apply to insufficient data teams
for team_id in insufficient_teams:
    team_abilities[team_id][action] = avg_ability
    team_counter_abilities[team_id][action] = avg_counter
```

### 2.6 Prediction

For a specific matchup, the predicted rate is:

```python
log_rate = intercept + team_ability + opponent_counter_ability
if is_home:
    log_rate += home_advantage

# Clamp to prevent overflow
log_rate = min(log_rate, MAX_LOG_RATE)  # MAX_LOG_RATE = 7.0

lambda_predicted = exp(log_rate)
```

---

## 3. Player Action Model (PAM)

### 3.1 Mathematical Foundation

The Player Action Model estimates player contribution rates as proportions of team actions using empirical rates with confidence intervals.

**File:** `/src/backend_odds/core/prediction_models/player_action_models/player_action_model.py`

### 3.2 Rate Calculation

For player `p` and action `a`:

**Proportion of Team Actions:**
```
r_pa = Σ(player_actions_pa) / Σ(team_actions_a)
```

Calculated over all matches where player `p` started.

**Per-Match Rate Distribution:**

For each match `m` where player started:
```
r_pam = player_count_pam / team_count_am
```

The distribution of per-match rates gives variance estimate:

```python
match_rates = [player_count_m / team_count_m for m in matches]
mean_rate = mean(match_rates)
std_dev = std(match_rates, ddof=1)
```

### 3.3 Confidence Intervals

Using normal approximation for the sampling distribution of proportions:

```python
n = len(match_rates)  # Number of matches
z = norm.ppf((1 + confidence_level) / 2)  # 1.96 for 95%

std_err = std_dev / sqrt(n)
lower_bound = max(0, mean_rate - z * std_err)
upper_bound = min(1, mean_rate + z * std_err)
```

**Insufficient Data Fallback:**
```python
if n <= 1:
    lower_bound = max(0, overall_rate * 0.7)
    upper_bound = min(1, overall_rate * 1.3)
```

### 3.4 Eligibility Criteria

Players must satisfy:
```python
starting_matches >= min_starting_matches  # Default: 10
current_season_starts >= min_current_season_starts  # Default: 5
starts_percentage >= min_starts_percentage  # Default: 0.3
```

### 3.5 Hierarchical Conversion Rates

For correlated actions (shots → shots_on_target → goals):

```python
# Shots to SoT conversion
shots_to_sot = total_sot / total_shots if total_shots >= 20 else None

# SoT to goals conversion
sot_to_goals = total_goals / total_sot if total_sot >= 10 else None

# League-wide fallbacks
if shots_to_sot is None:
    shots_to_sot = league_shots_to_sot_avg  # Default: 0.351 (EPL)

if sot_to_goals is None:
    sot_to_goals = league_sot_to_goals_avg  # Default: 0.322 (EPL)
```

### 3.6 Beta-Binomial Extension (Implicit)

While not explicitly implemented as Beta-Binomial, the rate estimation with confidence intervals approximates the posterior distribution:

**Approximate Beta Prior:**
```
r_pa ~ Beta(α, β)

α ≈ mean_rate · n_effective
β ≈ (1 - mean_rate) · n_effective

where n_effective = (mean_rate · (1 - mean_rate)) / var(rates)
```

This provides Bayesian shrinkage toward league averages for players with limited data.

---

## 4. Zonal Dirichlet Model (ZDM)

### 4.1 Mathematical Foundation

The Zonal Dirichlet Model uses Bayesian inference to estimate the probability distribution of actions across pitch zones.

**File:** `/src/backend_odds/core/prediction_models/zonal_models/dirichlet.py`

### 4.2 Zone Structure

**Zone Type 1 (Standard 3×3 Grid):**
```
Away Goal
┌─────┬─────┬─────┐
│ a1  │ a2  │ a3  │  Attacking Third
├─────┼─────┼─────┤
│ b1  │ b2  │ b3  │  Middle Third
├─────┼─────┼─────┤
│ c1  │ c2  │ c3  │  Defensive Third
└─────┴─────┴─────┘
Home Goal

Left  Center Right
```

### 4.3 Prior Distribution

**Global Action Prior:**

For action `a`, compute league-wide zone distribution with Laplace smoothing:

```python
# Initialize with prior_alpha pseudo-counts
smoothed_counts[zone] = prior_alpha  # Default: 1

# Add observed counts
for zone, count in zone_counts.items():
    smoothed_counts[zone] += count

# Normalize to probabilities
total = sum(smoothed_counts.values())
prior_probs[zone] = smoothed_counts[zone] / total
```

**Dirichlet Prior:**
```
θ ~ Dir(α₁, α₂, ..., α_k)

where αᵢ = prior_alpha · prior_probs[zone_i]
```

### 4.4 Bayesian Updating

For player/team `p` with observed zone counts `n = (n₁, n₂, ..., n_k)`:

**Posterior Distribution:**
```
θ_p | n ~ Dir(α₁ + n₁, α₂ + n₂, ..., α_k + n_k)
```

**Posterior Mean (Point Estimate):**
```
E[θᵢ | n] = (αᵢ + nᵢ) / (Σⱼ αⱼ + Σⱼ nⱼ)
```

### 4.5 Per-Match Variance Estimation

For more accurate uncertainty quantification, the model calculates per-match zone rates:

```python
match_rates = {}  # zone -> list of per-match rates

for game_id in player_games:
    zone_counts_game = get_zone_counts(player_id, game_id, action)
    total_actions = sum(zone_counts_game.values())

    if total_actions > 0:
        for zone in all_zones:
            rate = zone_counts_game[zone] / total_actions
            match_rates[zone].append(rate)

# Include prior as pseudo-matches
for zone in all_zones:
    for _ in range(prior_alpha):
        match_rates[zone].append(prior_probs[zone])
```

**Confidence Intervals:**
```python
mean_rate = mean(match_rates[zone])
std_dev = std(match_rates[zone], ddof=1)
n_effective = len(match_rates[zone])

z = norm.ppf((1 + confidence_level) / 2)
std_err = std_dev / sqrt(n_effective)

lower_bound = max(0, mean_rate - z * std_err)
upper_bound = min(1, mean_rate + z * std_err)
```

### 4.6 Symmetry Transformation

For away teams, zones are mirrored:

```python
def get_symmetry_zone_name(zone):
    """Mirror zone for away team perspective"""
    # a1 -> c1, a2 -> c2, a3 -> c3
    # b1 -> b1, b2 -> b2, b3 -> b3  (middle unchanged)
    # c1 -> a1, c2 -> a2, c3 -> a3

    if zone.startswith('a'):
        return 'c' + zone[1:]
    elif zone.startswith('c'):
        return 'a' + zone[1:]
    else:
        return zone  # Middle third unchanged
```

---

## 5. Vine Copula Implementation

### 5.1 Mathematical Foundation

Vine copulas model the dependency structure between multiple action types, enabling correlated sampling.

**File:** `/src/backend_odds/core/prediction_models/team_models/stats_team_model.py`
**Library:** `pyvinecopulib`

### 5.2 Copula Theory

**Sklar's Theorem:**
```
F(x₁, ..., x_d) = C(F₁(x₁), ..., F_d(x_d))
```

Where:
- `F` = Joint distribution
- `Fᵢ` = Marginal distributions
- `C` = Copula function (dependency structure)

### 5.3 Data Transformation

**Step 1: Marginal CDF Transformation**

For team `i`, opponent `j`, action `a`, observed count `y`:

```python
def transform_to_uniform(y, team_id, opponent_id, is_home, action):
    # Get predicted mean
    lambda_pred = predict_team_mean(team_id, opponent_id, is_home, action)

    # Get distribution type (Poisson or NB2)
    dist_type = team_action_distributions[team_id][action]

    if dist_type == NEGATIVE_BINOMIAL:
        alpha = dispersion_params[action]
        r = 1.0 / alpha
        p = 1.0 / (1.0 + alpha * lambda_pred)
        u = nbinom.cdf(y, r, p)
    else:  # POISSON
        u = poisson.cdf(y, lambda_pred)

    # Clip to avoid numerical issues
    return clip(u, 0.001, 0.999)
```

This transforms observed counts to uniform [0,1] values via probability integral transform.

### 5.4 Vine Copula Structure

**Parametric Family Set:**
```python
family_set = [
    BicopFamily.gaussian,   # Normal copula
    BicopFamily.clayton,    # Lower tail dependence
    BicopFamily.gumbel,     # Upper tail dependence
    BicopFamily.frank,      # Symmetric dependence
    BicopFamily.joe,        # Upper tail dependence
    BicopFamily.bb1,        # Both tail dependencies
    BicopFamily.bb7         # Both tail dependencies
]
```

**Fitting:**
```python
# u_data shape: (n_matches, n_actions)
# Each column is uniform-transformed action count

controls = FitControlsVinecop(family_set=family_set)
vine = Vinecop.from_data(data=u_data, controls=controls)
```

The vine copula automatically selects:
1. Tree structure (which actions to pair first)
2. Bivariate copula families for each pair
3. Parameters for each copula

### 5.5 Copula Types

**Global vs. Team-Specific:**

```python
# Option 1: Single global copula for all teams
if use_global_copula:
    # Fit on all match data
    vine = fit_copula_from_data(all_match_u_values)
    global_action_copula = vine

# Option 2: Team-specific copulas
else:
    for team_id in teams:
        team_match_data = matches[team_id]
        vine = fit_copula_from_data(team_match_data)
        vine_copula_models[team_id] = vine
```

### 5.6 Correlated Sampling

**Step 1: Sample from Copula**
```python
# Generate n_simulations correlated uniform samples
u_samples = vine.simulate(n_simulations)
# Shape: (n_simulations, n_actions)
```

**Step 2: Inverse Transform**
```python
for i, action in enumerate(actions):
    u_vals = u_samples[:, i]
    lambda_pred = predict_team_mean(team_id, opponent_id, is_home, action)

    if dist_type == NEGATIVE_BINOMIAL:
        alpha = dispersion_params[action]
        r = 1.0 / alpha
        p = 1.0 / (1.0 + alpha * lambda_pred)
        samples[action] = nbinom.ppf(u_vals, r, p).astype(int)
    else:  # POISSON
        samples[action] = poisson.ppf(u_vals, lambda_pred).astype(int)
```

This produces correlated action counts that preserve:
- Marginal distributions (from GLM)
- Dependency structure (from copula)

### 5.7 Copula Persistence

Vine copulas are serialized to JSON:

```python
# Save
vine_json = vine.to_json()
params["vine_copulas"]["team_models"][team_id] = {
    "model_json": vine_json,
    "actions": actions
}

# Load
vine = Vinecop.from_json(model_json)
```

---

## 6. Monte Carlo Simulation Engine

### 6.1 Architecture

**File:** `/src/backend_odds/core/prediction_models/orchestration/simulation.py`

### 6.2 Simulation Flow

```
simulate_match(game_id, home_team_id, away_team_id, n_simulations=3000)
    ↓
[Get Zonal Probabilities]
    For each action:
        home_zone_probs[action] = zonal_model.get_team_probs(home_team_id, action)
        away_zone_probs[action] = zonal_model.get_team_probs(away_team_id, action)
    ↓
[Simulate Team Action Counts] (with copula)
    home_actions = team_model.simulate_team_actions(home_team_id, away_team_id,
                                                     is_home=True, n_simulations=3000)
    away_actions = team_model.simulate_team_actions(away_team_id, home_team_id,
                                                     is_home=False, n_simulations=3000)
    ↓
[Distribute Actions to Zones] (vectorized multinomial)
    For each action:
        home_zone_counts = vectorized_multinomial(home_actions[action],
                                                   home_zone_probs[action])
        away_zone_counts = vectorized_multinomial(away_actions[action],
                                                   away_zone_probs[action])
    ↓
[Sample First/Last Zones] (vectorized)
    first_zones, last_zones = sample_first_last_zones(home_zone_counts,
                                                        away_zone_counts)
    ↓
[Aggregate Results]
    Store per-simulation:
        - Action counts (home/away)
        - Zone distributions
        - Action sequences (first/last)
```

### 6.3 Vectorized Multinomial Sampling

**Algorithm:**

Instead of `n_simulations` separate multinomial calls, group by unique total counts:

```python
def vectorized_multinomial(totals, probs, rng):
    """
    Args:
        totals: (n_sims,) array of total action counts
        probs: (n_zones,) array of zone probabilities
    Returns:
        zone_counts: (n_sims, n_zones) array
    """
    result = zeros((n_sims, n_zones), dtype=int32)

    # Group by unique total values
    unique_vals, inverse = unique(totals, return_inverse=True)

    for i, total in enumerate(unique_vals):
        if total == 0:
            continue

        # Find all simulations with this total
        mask = (inverse == i)
        n_with_total = sum(mask)

        # Single batched call for all simulations with this total
        samples = rng.multinomial(total, probs, size=n_with_total)
        result[mask] = samples

    return result
```

**Performance:**
- Goals (0-5 typical range): 3000 calls → ~6 calls (500× faster)
- Shots (0-20 typical range): 3000 calls → ~21 calls (143× faster)

### 6.4 First/Last Zone Sampling

**Vectorized Algorithm:**

```python
def sample_first_last_zones(home_zone_counts, away_zone_counts, all_zones, rng):
    """
    Args:
        home_zone_counts: (n_sims, n_zones)
        away_zone_counts: (n_sims, n_zones)
    Returns:
        first_tuples: [(zone, team), ...] length n_sims
        last_tuples: [(zone, team), ...] length n_sims
    """
    # Concatenate home and away zones
    combined = concatenate([home_zone_counts, away_zone_counts], axis=1)
    # Shape: (n_sims, 2*n_zones)

    # Normalize to probabilities
    row_sums = combined.sum(axis=1, keepdims=True)
    probs = combined / where(row_sums == 0, 1.0, row_sums)

    # Build CDF
    cdf = cumsum(probs, axis=1)

    # Draw two uniform randoms per simulation
    u = rng.uniform(size=(n_sims, 2))

    # Binary search in CDF for first and last
    first_idx = (cdf < u[:, 0:1]).sum(axis=1)
    last_idx = (cdf < u[:, 1:2]).sum(axis=1)

    # Map flat indices to (zone, team) tuples
    first_tuples = [(all_zones[idx % n_zones],
                     'home' if idx < n_zones else 'away')
                    for idx in first_idx]
    last_tuples = [(all_zones[idx % n_zones],
                    'home' if idx < n_zones else 'away')
                   for idx in last_idx]

    return first_tuples, last_tuples
```

### 6.5 Deterministic Seeding

For reproducibility across parallel workers:

```python
import hashlib

seed_str = f"{game_id}:{':'.join(sorted(actions))}"
seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)

rng = np.random.RandomState(seed)
np.random.seed(seed)  # For code using global np.random
```

### 6.6 Caching Strategy

Simulation results are cached in Redis with hierarchical keys:

```python
cache_key = f"odds:sim:unified:{game_id}:{actions_str}{bounds_str}_v2"

# Cache with TTL
redis_cache.set(cache_key, json.dumps(result), ex=CacheTTL.SIMULATION)
# CacheTTL.SIMULATION = 3600 seconds (1 hour)
```

Cache invalidation occurs on:
- Parameter updates
- Model retraining
- Explicit flush commands

---

## 7. Odds Calculation Pipeline

### 7.1 Architecture

**File:** `/src/backend_odds/core/prediction_models/orchestration/main_pipeline.py`

### 7.2 Bet Type Taxonomy

```
Bet Types
├── Team Props
│   ├── Moneyline (H/D/A)
│   ├── Spread (±goals with line)
│   └── Totals (Over/Under)
├── ZAO (Zone-Action-Occurrence)
│   ├── First Occurrence (specific zone)
│   ├── Most Occurrence (zone group comparison)
│   └── Last Occurrence (specific zone)
├── ZAT (Zone-Action-Team totals)
│   └── Over/Under for team in zones
└── ZAP (Zone-Action-Player)
    └── Over/Under for player actions in zones
```

### 7.3 Probability to Odds Conversion

**Fair Odds:**
```
odds_fair = 1 / probability
```

**Bounds Checking:**
```python
min_prob = 1 / max_odds_multiplier  # Default: 1/30 = 0.0333
max_prob = 1 / min_odds_multiplier  # Default: 1/1.01 = 0.9901

if prob <= 0 or prob < min_prob:
    odds = max_odds_multiplier  # 30.0
elif prob >= 1 or prob > max_prob:
    odds = min_odds_multiplier  # 1.01
else:
    odds = 1 / prob
```

### 7.4 Vigorish (Vig) Application

**Method 1: Simple Divisive (Single Outcomes)**

Used for ZAP, ZAT, single ZAO bets:

```python
def apply_vig_to_odds(odds, vig_margin=0.05):
    """
    Args:
        odds: Fair odds (e.g., 2.5)
        vig_margin: Bookmaker margin (e.g., 0.05 = 5%)
    Returns:
        vigged_odds: Odds with vig applied
    """
    if odds < min_odds_multiplier:
        return odds  # Don't apply vig to already low odds

    vigged_odds = odds / (1 + vig_margin)

    # Clamp to bounds
    vigged_odds = max(min_odds_multiplier,
                     min(vigged_odds, max_odds_multiplier))

    return vigged_odds
```

**Example:**
```
Fair odds: 2.50 → Implied prob: 40%
With 5% vig: 2.50 / 1.05 = 2.38 → Implied prob: 42%
Bookmaker keeps 2% edge
```

**Method 2: Odds-Power Compression (Multi-Outcome Markets)**

Used for MOM (Man of the Match), ZAO "most" bets:

```python
def apply_vig_odds_power(probability, hold=0.05, gamma=0.85):
    """
    Args:
        probability: Fair probability (0 < p < 1)
        hold: Total overround margin (e.g., 0.05 = 105% book)
        gamma: Compression exponent (< 1 compresses favorites)
    Returns:
        vigged_odds: Odds with power compression
    """
    # Step 1: Convert to odds ratio
    r = probability / (1 - probability)

    # Step 2: Compress with gamma
    r_prime = r ** gamma

    # Step 3: Convert back to probability
    p_tilde = r_prime / (1 + r_prime)

    # Step 4: Apply hold
    vigged_odds = (1 - hold) / p_tilde

    return clip(vigged_odds, min_odds_multiplier, max_odds_multiplier)
```

**Effect:**
```
gamma < 1: Compresses favorites, expands longshots
gamma = 1: No compression (linear)
gamma > 1: Expands favorites, compresses longshots

Example (gamma=0.85):
Fair: [0.40, 0.30, 0.20, 0.10]
→ Compressed: [0.42, 0.30, 0.19, 0.09]
→ With 5% hold: [0.44, 0.32, 0.20, 0.09]  (sum = 105%)
```

### 7.5 Team Props Calculation

**Moneyline (Match Result):**

Using upper/lower bound simulations:

```python
def evaluate_moneyline(home_upper, home_lower, away_upper, away_lower):
    """
    Args:
        home_upper, home_lower: Goal arrays from bound simulations
        away_upper, away_lower: Goal arrays from bound simulations
    Returns:
        probs: {home, draw, away}
    """
    n = len(home_upper)

    # Home wins: optimistic home > pessimistic away
    p_home_win = sum(home_upper > away_lower) / n

    # Away wins: optimistic away > pessimistic home
    p_away_win = sum(away_upper > home_lower) / n

    # Draw: determine underdog, use their upper vs favorite's lower
    if home_lower.mean() < away_upper.mean():
        # Home underdog
        p_draw = sum(home_upper == away_lower) / n
    else:
        # Away underdog
        p_draw = sum(away_upper == home_lower) / n

    return {
        'home': p_home_win,
        'draw': p_draw,
        'away': p_away_win
    }
```

**Spread:**

```python
def evaluate_spread(home_upper, home_lower, away_upper, away_lower, line):
    """
    Args:
        line: Spread line (e.g., -1.5 for home favorite)
    Returns:
        prob_home_cover: P(home + line > away)
    """
    n = len(home_upper)

    # Home covers: optimistic home + line > pessimistic away
    home_cover = sum((home_upper + line) > away_lower) / n

    return home_cover
```

**Totals (Over/Under):**

```python
def evaluate_totals(home_upper, home_lower, away_upper, away_lower, line):
    """
    Args:
        line: Total goals line (e.g., 2.5)
    Returns:
        probs: {over, under}
    """
    n = len(home_upper)

    # Over: optimistic both teams
    p_over = sum((home_upper + away_upper) > line) / n

    # Under: pessimistic both teams
    p_under = sum((home_lower + away_lower) <= line) / n

    return {
        'over': p_over,
        'under': p_under
    }
```

### 7.6 ZAO Calculation

**First Occurrence:**

```python
def evaluate_zao_first(simulations, action, zones):
    """
    Count simulations where first action occurred in specified zones
    """
    wins = 0
    for sim in simulations:
        action_data = sim['actions'][action]
        action_sequence = action_data['action_sequence']

        if action_sequence:
            first_zone, first_team = action_sequence[0]
            if first_zone in zones:
                wins += 1

    return wins / len(simulations)
```

**Most Occurrence:**

```python
def evaluate_zao_most(simulations, action, zones, competing_zones):
    """
    Count simulations where zones had most actions among competing groups
    """
    wins = 0
    for sim in simulations:
        zone_counts = sim['actions'][action]['zone_counts']

        # Calculate count for each zone group
        combo_counts = []
        for combo in competing_zones:
            combo_count = sum(zone_counts.get(z, 0) for z in combo)
            combo_counts.append(combo_count)

        max_count = max(combo_counts)
        our_idx = competing_zones.index(zones)
        our_count = combo_counts[our_idx]

        # Win if we have max and it's > 0
        if our_count == max_count and max_count > 0:
            n_winners = sum(1 for c in combo_counts if c == max_count)
            wins += 1.0 / n_winners  # Split if tie

    return wins / len(simulations)
```

**Last Occurrence:**

```python
def evaluate_zao_last(simulations, action, zones):
    """
    Count simulations where last action occurred in specified zones
    """
    wins = 0
    for sim in simulations:
        action_sequence = sim['actions'][action]['action_sequence']

        if action_sequence:
            last_zone, last_team = action_sequence[-1]
            if last_zone in zones:
                wins += 1

    return wins / len(simulations)
```

### 7.7 ZAT Calculation

```python
def evaluate_zat(simulation_data, action, team, line, is_over):
    """
    Zone-Action-Team: Over/Under for team's actions in specific zones

    Args:
        action: Action type (e.g., 'goals')
        team: 'home' or 'away'
        line: Betting line (e.g., 1.5)
        is_over: True for over bet, False for under
    """
    team_key = f"{team}_team"

    if use_bounds:
        # Use appropriate bound
        if is_over:
            action_counts = simulation_data[team_key]['upper'][action]
        else:
            action_counts = simulation_data[team_key]['lower'][action]
    else:
        action_counts = simulation_data[team_key][action]

    if is_over:
        prob = sum(action_counts > line) / len(action_counts)
    else:
        prob = sum(action_counts <= line) / len(action_counts)

    return prob
```

### 7.8 ZAP Calculation

**Zone-Action-Player** combines player rates with zonal distributions:

```python
def get_prob_for_zap(player_id, action, zones, line, is_over):
    """
    Calculate probability for player to achieve line in specified zones
    """
    # Get player's action rate relative to team
    player_rate = player_model.predict_player_action_rate(
        player_id, action,
        use_lower_bound=(not is_over),
        use_upper_bound=is_over
    )

    # Get player's zone distribution for this action
    zone_probs = zonal_model.get_player_zonal_probs(
        player_id, action,
        use_lower_bound=(not is_over),
        use_upper_bound=is_over
    )

    # Calculate probability that specified zones occur
    zone_prob = sum(zone_probs[z] for z in zones)

    # Get team's expected action count
    team_id = get_player_team(player_id)
    opponent_id = get_opponent(game_id, team_id)
    is_home = is_team_home(game_id, team_id)

    team_rate = team_model.predict_team_mean(
        team_id, opponent_id, is_home, action,
        use_upper=is_over,
        use_lower=(not is_over)
    )

    # Expected player actions in zones
    lambda_player_zones = team_rate * player_rate * zone_prob

    # Calculate probability using Poisson/NB distribution
    dist_type = player_model.get_distribution_type(player_id, action)

    if is_over:
        # P(X > line) = 1 - P(X <= line)
        if dist_type == POISSON:
            prob = 1 - poisson.cdf(line, lambda_player_zones)
        else:  # NEGATIVE_BINOMIAL
            alpha = get_dispersion(action)
            r = 1.0 / alpha
            p = 1.0 / (1.0 + alpha * lambda_player_zones)
            prob = 1 - nbinom.cdf(line, r, p)
    else:
        # P(X <= line)
        if dist_type == POISSON:
            prob = poisson.cdf(line, lambda_player_zones)
        else:
            alpha = get_dispersion(action)
            r = 1.0 / alpha
            p = 1.0 / (1.0 + alpha * lambda_player_zones)
            prob = nbinom.cdf(line, r, p)

    return prob
```

---

## 8. Model Calibration and Validation

### 8.1 Calibration Architecture

**File:** `/src/backend_odds/core/model_calibration/calibrate_params.py`

### 8.2 Objective Function

The calibration minimizes mean squared error between model probabilities and market-implied probabilities:

```python
def objective(theta):
    """
    Args:
        theta: [z_score, delta_goals, delta_shots, delta_assists, ...]
    Returns:
        mse: Mean squared error
    """
    z_score = theta[0]
    deltas = {action: theta[i+1] for i, action in enumerate(actions)}

    # Update model parameters
    team_model.update_z_score(z_score)
    player_model.update_z_score(z_score)

    # Shift parameter centers
    apply_deltas_to_team_params(team_model, deltas)
    apply_deltas_to_player_params(player_model, deltas)

    # Calculate errors
    total_squared_error = 0
    count = 0

    # Player props
    for item in player_props:
        model_prob = calculate_player_prop_probability(item)
        market_prob = 1 / item['market_odds']
        total_squared_error += (model_prob - market_prob)**2
        count += 1

    # Team props
    for item in team_props:
        model_prob = calculate_team_prop_probability(item)
        market_prob = 1 / item['market_odds']
        total_squared_error += (model_prob - market_prob)**2
        count += 1

    return total_squared_error / count
```

### 8.3 Parameter Adjustment

**Z-Score Adjustment:**

Affects confidence interval width for all parameters:

```python
def update_z_score(model, new_z):
    """Update all parameter bounds with new z-score"""
    for action in actions:
        # Global parameters
        for param in [intercepts, home_advantages, dispersions]:
            if action in param:
                value = param[action].original_value
                stderr = stored_stderr[action]
                param[action].bounds = (
                    value - new_z * stderr,
                    value + new_z * stderr
                )

        # Team parameters
        for team_id in team_abilities:
            if action in team_abilities[team_id]:
                value = team_abilities[team_id][action].original_value
                stderr = team_abilities_stderr[team_id][action]
                team_abilities[team_id][action].bounds = (
                    value - new_z * stderr,
                    value + new_z * stderr
                )
```

**Parameter Center Shifts:**

Adjusts mean of parameter distributions:

```python
def apply_deltas_to_team_params(model, deltas):
    """Shift team parameter centers"""
    for action, delta in deltas.items():
        # Global intercepts
        if action in model.intercepts:
            model.intercepts[action].original_value += delta

        # Team abilities (shift in same direction)
        for team_id in model.team_abilities:
            if action in model.team_abilities[team_id]:
                model.team_abilities[team_id][action].original_value += delta

        # Counter abilities (shift in opposite direction)
        for team_id in model.team_counter_abilities:
            if action in model.team_counter_abilities[team_id]:
                model.team_counter_abilities[team_id][action].original_value -= delta
```

### 8.4 Optimization

```python
from scipy.optimize import minimize

# Initial values
x0 = np.concatenate([[z_initial], np.zeros(len(actions))])
# x0 = [1.96, 0.0, 0.0, 0.0, ...] for z and action deltas

# Optimize using Nelder-Mead simplex
result = minimize(
    objective,
    x0,
    method='Nelder-Mead',
    options={
        'maxiter': 30,
        'xatol': 1e-3,
        'disp': True
    }
)

# Extract optimal values
best_z = result.x[0]
best_deltas = {action: result.x[i+1] for i, action in enumerate(actions)}
final_mse = result.fun
```

### 8.5 Backtesting Framework

**File:** `/src/backend_odds/core/eval/backtest.py`

**Metrics Calculated:**

1. **Log Loss (Cross-Entropy):**
```
LL = -Σᵢ [yᵢ log(pᵢ) + (1-yᵢ) log(1-pᵢ)]
```

2. **Brier Score:**
```
BS = (1/N) Σᵢ (pᵢ - yᵢ)²
```

3. **Calibration Curve:**
```python
from sklearn.calibration import calibration_curve

prob_true, prob_pred = calibration_curve(
    y_true, y_pred,
    n_bins=10,
    strategy='quantile'
)

# Perfect calibration: prob_true ≈ prob_pred for all bins
```

4. **ROI (Return on Investment):**
```python
profits = []
for i in range(n_bets):
    if outcome[i]:  # Win
        profit = (1 / prob[i]) - 1  # Payout - stake
    else:  # Loss
        profit = -1  # Lose stake
    profits.append(profit)

total_roi = sum(profits) / len(profits)
```

5. **Expected Value (EV):**
```
EV = p_win * (odds - 1) - p_lose * 1
   = p_win * odds - 1
```

Positive EV indicates profitable bets long-term.

### 8.6 Calibration Curves

**Plot Generation:**

```python
def plot_calibration_curve(y_true, y_pred, output_dir):
    """Plot reliability diagram"""
    prob_true, prob_pred = calibration_curve(
        y_true, y_pred,
        n_bins=10
    )

    plt.figure(figsize=(10, 8))
    plt.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
    plt.plot(prob_pred, prob_true, 's-', label='Model')

    plt.xlabel('Predicted Probability')
    plt.ylabel('Observed Frequency')
    plt.title('Calibration Curve')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.savefig(f'{output_dir}/calibration_curve.png')
```

**Interpretation:**
- Points on diagonal = well-calibrated
- Points above diagonal = underconfident (too low probabilities)
- Points below diagonal = overconfident (too high probabilities)

---

## 9. External Odds Ingestion

### 9.1 Architecture

**Files:**
- Live Odds: `/src/backend_odds/core/data_scraping/odds_api/live_odds_api.py`
- Historical Odds: `/src/backend_odds/core/data_scraping/odds_api/historical_odds_api.py`

### 9.2 The Odds API Integration

**Base Configuration:**

```python
class LiveOddsAPI:
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key):
        self.api_key = api_key
        self.default_params = {
            'apiKey': self.api_key,
            'regions': 'us',  # US bookmakers
            'oddsFormat': 'decimal',
            'markets': 'h2h,spreads,totals'
        }
```

### 9.3 Supported Markets

**Market Types:**

```python
SUPPORTED_MARKETS = {
    'h2h': 'Moneyline (Head-to-Head)',
    'spreads': 'Point Spread',
    'totals': 'Over/Under Totals',
    'alternate_spreads': 'Alternate Spreads',
    'alternate_totals': 'Alternate Totals',
    'player_goal_scorer_anytime': 'Anytime Goal Scorer',
    'player_shots_on_target': 'Player Shots on Target',
    'player_assists': 'Player Assists',
    'player_shots': 'Player Total Shots'
}
```

### 9.4 Data Fetching

**Live Odds:**

```python
def get_odds(self, sport='soccer_epl', market='h2h'):
    """Fetch current odds for upcoming events"""
    url = f"{self.BASE_URL}/sports/{sport}/odds"
    params = {**self.default_params, 'markets': market}

    response = requests.get(url, params=params)
    data = response.json()

    # Track API usage
    remaining = response.headers.get('x-requests-remaining')
    used = response.headers.get('x-requests-used')
    logger.info(f"API: {used} used, {remaining} remaining")

    return data
```

**Historical Odds:**

```python
def fetch_historical_odds_by_event(self, event_id, market, date):
    """Fetch historical odds for specific event"""
    url = f"{self.BASE_URL}/historical/sports/{sport}/events/{event_id}/odds"
    params = {
        **self.default_params,
        'markets': market,
        'date': date  # ISO format: 2024-01-15T19:00:00Z
    }

    response = requests.get(url, params=params)
    return response.json()
```

### 9.5 Odds Normalization

**Goto Conversion (Remove Vig):**

```python
import goto_conversion

def normalize_odds(odds_list):
    """
    Remove vig from bookmaker odds to get fair probabilities

    Args:
        odds_list: [home_odds, draw_odds, away_odds]
    Returns:
        fair_probs: [p_home, p_draw, p_away] summing to 1.0
    """
    # goto_conversion removes vig using margin-proportional method
    fair_probs = goto_conversion.goto_conversion(odds_list)

    return fair_probs
```

**Example:**
```
Bookmaker odds: [2.10, 3.40, 3.60]
Implied probs: [0.476, 0.294, 0.278] → sum = 1.048 (4.8% vig)

After normalization:
Fair probs: [0.454, 0.281, 0.265] → sum = 1.000
```

### 9.6 Market Average Calculation

```python
def get_average_odds(self, game_id, market):
    """Calculate consensus odds across multiple bookmakers"""
    event_odds = self.get_odds_for_event(game_id, market)

    if not event_odds or 'bookmakers' not in event_odds:
        return {}

    # Collect odds from all bookmakers
    bookmaker_odds = {}
    for bookmaker in event_odds['bookmakers']:
        bookmaker_name = bookmaker['key']

        for market_data in bookmaker['markets']:
            if market_data['key'] == market:
                for outcome in market_data['outcomes']:
                    name = outcome['name']
                    odds = outcome['price']
                    point = outcome.get('point')  # For spreads/totals

                    key = (name, point) if point else name

                    if key not in bookmaker_odds:
                        bookmaker_odds[key] = []
                    bookmaker_odds[key].append(odds)

    # Calculate average
    average_odds = {}
    for key, odds_list in bookmaker_odds.items():
        average_odds[key] = np.mean(odds_list)

    return average_odds
```

### 9.7 Database Storage

**Odds API Models:**

```python
from sqlalchemy import Column, Integer, Float, String, DateTime

class MoneylineOdds(Base):
    __tablename__ = 'moneyline_odds'

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    bookmaker = Column(String)
    home_odds = Column(Float)
    draw_odds = Column(Float)
    away_odds = Column(Float)
    timestamp = Column(DateTime)

class TotalsOdds(Base):
    __tablename__ = 'totals_odds'

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    bookmaker = Column(String)
    line = Column(Float)  # e.g., 2.5 goals
    over_odds = Column(Float)
    under_odds = Column(Float)
    timestamp = Column(DateTime)

class SpreadOdds(Base):
    __tablename__ = 'spread_odds'

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    bookmaker = Column(String)
    team = Column(String)  # 'home' or 'away'
    line = Column(Float)  # e.g., -1.5
    odds = Column(Float)
    timestamp = Column(DateTime)
```

### 9.8 Player Name Mapping

```python
def match_player_to_db(api_player_name, db_player_repo):
    """
    Map Odds API player name to internal database player_id

    Handles variations:
    - "Mohamed Salah" -> "M. Salah"
    - "Heung-Min Son" -> "Son Heung-Min"
    """
    # Try exact match first
    player = db_player_repo.get_player_by_name(api_player_name)
    if player:
        return player['player_id']

    # Try fuzzy matching
    from fuzzywuzzy import fuzz

    all_players = db_player_repo.get_all_players()
    best_match = None
    best_score = 0

    for db_player in all_players:
        score = fuzz.ratio(
            api_player_name.lower(),
            db_player['player_name'].lower()
        )

        if score > best_score and score > 80:  # Threshold
            best_score = score
            best_match = db_player

    if best_match:
        logger.info(
            f"Fuzzy matched '{api_player_name}' -> "
            f"'{best_match['player_name']}' (score: {best_score})"
        )
        return best_match['player_id']

    logger.warning(f"Could not match player: {api_player_name}")
    return None
```

---

## 10. Market Making and Risk Management

### 10.1 Price Adjustment Architecture

**File:** `/src/backend_odds/core/prediction_models/orchestration/price_adjustment/pricing_pipeline.py`

### 10.2 Dynamic Vig Adjustment

**Concept:**

Adjust vigorish based on:
1. Model confidence (wider CI → higher vig)
2. Betting volume (one-sided action → adjust line)
3. Sharp money detection (reduce limits)
4. Liability exposure (hedge position)

**Confidence-Based Vig:**

```python
def calculate_dynamic_vig(base_vig, confidence_interval_width):
    """
    Increase vig for uncertain predictions

    Args:
        base_vig: Base bookmaker margin (e.g., 0.05)
        confidence_interval_width: Width of 95% CI
    Returns:
        adjusted_vig: Vig scaled by uncertainty
    """
    # Normalize CI width (typical range 0.1 to 0.5)
    ci_normalized = (confidence_interval_width - 0.1) / 0.4
    ci_normalized = np.clip(ci_normalized, 0, 1)

    # Scale vig: low confidence → higher vig
    vig_multiplier = 1.0 + ci_normalized  # Range: 1.0 to 2.0
    adjusted_vig = base_vig * vig_multiplier

    return adjusted_vig
```

### 10.3 Volume-Based Line Movement

**Algorithm:**

```python
def adjust_line_for_volume(fair_prob, bet_volume_fraction):
    """
    Move line based on one-sided betting action

    Args:
        fair_prob: Model's fair probability
        bet_volume_fraction: Fraction of bets on this outcome (-1 to 1)
    Returns:
        adjusted_prob: Probability after volume adjustment
    """
    # Shading factor: how much to move per % of one-sided action
    SHADING_RATE = 0.02  # Move 2% per 100% one-sided

    # Calculate adjustment
    # Positive volume → lower probability (worse odds for bettors)
    prob_adjustment = bet_volume_fraction * SHADING_RATE
    adjusted_prob = fair_prob - prob_adjustment

    # Ensure valid probability
    adjusted_prob = np.clip(adjusted_prob, 0.01, 0.99)

    return adjusted_prob
```

**Example:**
```
Fair probability: 0.50
80% of bets on this outcome → volume_fraction = 0.80
Adjustment: 0.80 * 0.02 = 0.016
Adjusted probability: 0.50 - 0.016 = 0.484 (worse odds for bettors)
```

### 10.4 Parlay Pricing

**File:** `/src/backend_odds/core/prediction_models/orchestration/parlay_odds.py`

**Independent Events:**

For parlay of N independent bets with probabilities `p₁, p₂, ..., pₙ`:

```python
def calculate_parlay_odds(individual_probs):
    """
    Calculate parlay odds for independent events

    Args:
        individual_probs: [p1, p2, ..., pn]
    Returns:
        parlay_odds: Fair odds for parlay
    """
    # Joint probability
    joint_prob = np.prod(individual_probs)

    # Fair odds
    parlay_odds = 1 / joint_prob

    return parlay_odds
```

**With Correlation:**

For same-game parlays (e.g., "Team A wins AND Over 2.5 goals"):

```python
def calculate_correlated_parlay_odds(prob_a, prob_b, correlation):
    """
    Calculate parlay odds accounting for correlation

    Args:
        prob_a: Probability of event A
        prob_b: Probability of event B
        correlation: Pearson correlation (-1 to 1)
    Returns:
        parlay_odds: Adjusted odds
    """
    # For positive correlation, joint probability is higher
    # Use Gaussian copula approximation

    from scipy.stats import norm, multivariate_normal

    # Convert probabilities to standard normal quantiles
    z_a = norm.ppf(prob_a)
    z_b = norm.ppf(prob_b)

    # Correlation matrix
    corr_matrix = [[1, correlation],
                   [correlation, 1]]

    # Joint probability under Gaussian copula
    joint_prob = multivariate_normal.cdf(
        [z_a, z_b],
        mean=[0, 0],
        cov=corr_matrix
    )

    parlay_odds = 1 / joint_prob

    return parlay_odds
```

**Example:**
```
Event A: Team wins (p=0.60)
Event B: Over 2.5 goals (p=0.50)

Independent: 0.60 * 0.50 = 0.30 → Odds: 3.33

Correlated (ρ=0.3): Joint prob ≈ 0.35 → Odds: 2.86
(Team winning increases goal expectation)
```

### 10.5 Position Limits

**Kelly Criterion:**

Optimal bet size to maximize long-term growth:

```python
def kelly_fraction(prob_win, odds):
    """
    Calculate Kelly optimal bet size

    Args:
        prob_win: Probability of winning
        odds: Decimal odds
    Returns:
        kelly_fraction: Fraction of bankroll to bet
    """
    # Kelly formula: f* = (p*odds - 1) / (odds - 1)
    kelly = (prob_win * odds - 1) / (odds - 1)

    # Clamp to reasonable range
    kelly = np.clip(kelly, 0, 0.25)  # Max 25% of bankroll

    return kelly
```

**Liability Cap:**

```python
def calculate_max_bet_size(bankroll, kelly_fraction, liability_limit=0.10):
    """
    Calculate maximum bet size given constraints

    Args:
        bankroll: Total available capital
        kelly_fraction: Kelly criterion result
        liability_limit: Max % of bankroll at risk on single bet
    Returns:
        max_bet: Maximum bet size to accept
    """
    # Kelly-optimal size
    kelly_size = bankroll * kelly_fraction

    # Liability cap
    max_liability = bankroll * liability_limit

    # Take minimum
    max_bet = min(kelly_size, max_liability)

    return max_bet
```

### 10.6 Sharp Detection

**Clvity (Closing Line Value):**

```python
def calculate_clv(opening_odds, closing_odds, bet_odds):
    """
    Calculate Closing Line Value - measure of bet quality

    Args:
        opening_odds: Odds when bet was placed
        closing_odds: Odds at market close
        bet_odds: Odds bettor received
    Returns:
        clv: Closing line value (positive = good bet)
    """
    # Convert to implied probabilities
    opening_prob = 1 / opening_odds
    closing_prob = 1 / closing_odds
    bet_prob = 1 / bet_odds

    # CLV = how much better than closing line
    clv = (1 / closing_prob - 1 / bet_prob) / (1 / closing_prob)

    return clv
```

**Sharp Bettor Identification:**

```python
def is_sharp_bettor(bettor_history):
    """
    Identify sharp bettors based on historical performance

    Criteria:
    - High ROI (>5%)
    - Positive CLV
    - Consistent winners across markets
    - Quick to bet after line movement
    """
    avg_roi = np.mean([bet['profit'] for bet in bettor_history])
    avg_clv = np.mean([bet['clv'] for bet in bettor_history])
    win_rate = np.mean([bet['won'] for bet in bettor_history])

    # Sharp criteria
    is_sharp = (
        avg_roi > 0.05 and
        avg_clv > 0.02 and
        win_rate > 0.55 and
        len(bettor_history) > 100
    )

    return is_sharp
```

### 10.7 Risk Metrics

**Value at Risk (VaR):**

```python
def calculate_var(position_values, confidence_level=0.95):
    """
    Calculate Value at Risk

    Args:
        position_values: Array of potential P&L outcomes
        confidence_level: VaR confidence (e.g., 0.95 = 95% VaR)
    Returns:
        var: Maximum loss at confidence level
    """
    # Sort outcomes
    sorted_values = np.sort(position_values)

    # Find percentile
    index = int((1 - confidence_level) * len(sorted_values))
    var = -sorted_values[index]  # Negative of loss

    return var
```

**Conditional Value at Risk (CVaR):**

```python
def calculate_cvar(position_values, confidence_level=0.95):
    """
    Calculate Conditional Value at Risk (Expected Shortfall)

    Args:
        position_values: Array of potential P&L outcomes
        confidence_level: CVaR confidence level
    Returns:
        cvar: Average loss beyond VaR
    """
    # Sort outcomes
    sorted_values = np.sort(position_values)

    # Find VaR threshold
    var_index = int((1 - confidence_level) * len(sorted_values))

    # Average of losses beyond VaR
    tail_losses = sorted_values[:var_index]
    cvar = -np.mean(tail_losses)

    return cvar
```

**Example:**
```
Position values from simulation:
[-500, -200, -100, 0, 50, 100, 150, 200, 300, 500]

95% VaR: 5th percentile = -200 (expect loss no worse than $200 in 95% of cases)
95% CVaR: Average of worst 5% = mean([-500, -200]) = -350
```

### 10.8 Hedging Strategy

```python
def calculate_hedge_position(current_position, market_odds):
    """
    Calculate optimal hedge to reduce exposure

    Args:
        current_position: Current liability if bet wins
        market_odds: Current market odds for opposite side
    Returns:
        hedge_size: Amount to bet on opposite side
    """
    # To eliminate risk entirely: hedge to guarantee breakeven
    # If current bet pays out P at odds O₁, and hedge at odds O₂:
    # Break even when: P - hedge_bet = hedge_bet * (O₂ - 1)

    payout = current_position['potential_payout']
    stake = current_position['stake']
    hedge_odds = market_odds

    # Solve for hedge size
    # P - H = H * (O₂ - 1)
    # P = H * O₂
    hedge_size = payout / hedge_odds

    # Net result: guaranteed (P - H - H*(O₂-1)) = 0

    return hedge_size
```

---

## 11. Implementation Notes

### 11.1 Performance Optimizations

**Vectorization:**
- Multinomial sampling: 500× faster via batching
- Zone sampling: Eliminated Python loops
- CDF transformations: NumPy array operations

**Caching:**
- Redis for simulation results (1 hour TTL)
- JSON for model parameters (disk)
- LRU cache for frequently accessed rates

**Parallel Processing:**
- Multiprocessing for batch odds calculation
- Thread pool for API requests
- Deterministic seeding for reproducibility

### 11.2 Numerical Stability

**Overflow Prevention:**
```python
MAX_LOG_RATE = 7.0  # exp(7) ≈ 1097, prevents inf
log_rate = min(log_rate, MAX_LOG_RATE)
```

**Probability Clipping:**
```python
prob = np.clip(prob, 0.001, 0.999)  # Avoid log(0) errors
u_val = np.clip(u_val, 0.001, 0.999)  # Copula edge cases
```

**Hessian Singular Fallback:**
```python
if np.isnan(stderr) or stderr == 0:
    # Use global std or 20% of parameter value
    half_bound = max(abs(param) * 0.2, std(existing_params))
```

### 11.3 Configuration Management

**Hierarchical Configs:**
```python
MainPipelineConfig
├── TeamActionModelConfig
├── PlayerActionModelConfig
├── ZonalModelConfig
├── PricingConfig
└── MOMConfig
```

**Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# API Keys
ODDS_API_KEY=your_api_key_here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Model Paths
TEAM_MODEL_PATH=models/team_params.json
PLAYER_MODEL_PATH=models/player_params.json
ZONAL_MODEL_PATH=models/zonal_params.json
```

### 11.4 Error Handling

**Graceful Degradation:**
```python
try:
    # Use copula for correlated samples
    samples = simulate_with_copula(vine_model)
except Exception as e:
    logger.warning(f"Copula failed: {e}, using independent samples")
    samples = simulate_independent()
```

**Missing Data Fallbacks:**
```python
# Team has no parameters
if team_id not in team_abilities:
    logger.warning(f"Team {team_id} not in model, using league average")
    return league_average_params

# Player has insufficient data
if player_starts < min_starts:
    logger.info(f"Player {player_id} has insufficient data, using position average")
    return position_average_rate
```

---

## 12. Mathematical Summary

### Key Formulas

**Team Action Model (GLM):**
```
log(λ) = β₀ + α_team + γ_opponent + δ·is_home

Y ~ Poisson(λ) or NB(λ, α)
```

**Zonal Dirichlet:**
```
θ ~ Dir(α₁, ..., α_k)
θ|n ~ Dir(α₁+n₁, ..., α_k+n_k)
E[θᵢ|n] = (αᵢ+nᵢ) / Σⱼ(αⱼ+nⱼ)
```

**Vine Copula:**
```
F(x₁,...,x_d) = C(F₁(x₁),...,F_d(x_d))
u_i = F_i(x_i)  [transform to uniform]
(u₁,...,u_d) ~ Vinecop  [sample correlated uniforms]
x_i = F_i^{-1}(u_i)  [inverse transform]
```

**Probability to Odds:**
```
odds_fair = 1/p
odds_vigged = odds_fair / (1 + vig)
```

**Confidence Intervals:**
```
CI = μ ± z·σ/√n
z = 1.96 for 95% confidence
```

---

## 13. File Path Reference

**Core Models:**
- Team: `/src/backend_odds/core/prediction_models/team_models/stats_team_model.py`
- Player: `/src/backend_odds/core/prediction_models/player_action_models/player_action_model.py`
- Zonal: `/src/backend_odds/core/prediction_models/zonal_models/dirichlet.py`

**Orchestration:**
- Main: `/src/backend_odds/core/prediction_models/orchestration/main_pipeline.py`
- Simulation: `/src/backend_odds/core/prediction_models/orchestration/simulation.py`
- ZAO: `/src/backend_odds/core/prediction_models/orchestration/zao_odds.py`
- Parlay: `/src/backend_odds/core/prediction_models/orchestration/parlay_odds.py`

**Calibration:**
- Calibration: `/src/backend_odds/core/model_calibration/calibrate_params.py`
- Backtest: `/src/backend_odds/core/eval/backtest.py`

**Data Ingestion:**
- Odds API: `/src/backend_odds/core/data_scraping/odds_api/historical_odds_api.py`
- Live Odds: `/src/backend_odds/core/data_scraping/odds_api/live_odds_api.py`

**Configuration:**
- Config: `/src/backend_odds/core/prediction_models/config.py`
- Constants: `/src/backend_odds/core/prediction_models/constants.py`

---

## 14. Conclusion

The Backend-Odds system implements a sophisticated multi-model hierarchical Bayesian framework for sports betting odds calculation. The architecture combines:

1. **Generalized Linear Models** for team-level predictions with overdispersion handling
2. **Empirical Bayes** for player contribution rates with uncertainty quantification
3. **Dirichlet processes** for spatial probability distributions
4. **Vine copulas** for modeling action dependencies
5. **Monte Carlo simulation** with performance optimizations
6. **Market calibration** to align with external odds
7. **Risk management** for position sizing and hedging

The system achieves real-time performance through vectorization, caching, and parallel processing while maintaining numerical stability and providing comprehensive uncertainty quantification.

---

**Document Author:** Claude (Anthropic)
**Repository:** Backend-Odds
**Last Updated:** 2026-03-03
