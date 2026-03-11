# The Beautiful Game (TBG) - Complete Documentation Index

## Overview

This repository contains comprehensive technical documentation for The Beautiful Game (TBG) platform, covering all aspects from user flows to infrastructure deployment. The documentation was created through deep analysis of three core repositories: Frontend, Backend-Server, and Backend-Odds.

**Total Documentation**: 13 documents, ~300+ pages, 1,000+ code references

---

## Quick Navigation

### 🏗️ Architecture & System Design

| Document | Description | Key Topics |
|----------|-------------|------------|
| [TBG Complete System Architecture](./TBG_Complete_System_Architecture.md) | End-to-end system overview with complete user journey | Technology stack, user flows (6 phases), system integration, API communication |

### 💰 Business Logic & Features

| Document | Description | Key Topics |
|----------|-------------|------------|
| [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md) | Complete promotion mechanics | 8+ promo types, bet modifiers, bonus bets, referral system, grant priority logic |
| [Tournament System](./TOURNAMENT_SYSTEM_DOCUMENTATION.md) | Tournament mechanics and formats | Social prediction, 1v1, F2P, Royale, leaderboards, prize distribution |
| [Bet Settlement Logic](./BET_SETTLEMENT_DOCUMENTATION.md) | How bets are evaluated and settled | Two-pass verification, leg evaluation, partial voids, backed bet settlement |

### 🛡️ Security & Compliance

| Document | Description | Key Topics |
|----------|-------------|------------|
| [Risk Management & Fraud Detection](./RISK_MANAGEMENT_DOCUMENT.md) | Security systems and fraud prevention | User tiers, velocity checks, multi-accounting detection, betting limits |

### 📊 Statistical Models & Algorithms

| Document | Description | Key Topics |
|----------|-------------|------------|
| [Backend-Odds Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md) | Technical deep dive into odds calculation | TAM (GLM), PAM (Beta-binomial), ZDM (Bayesian), Vine Copula, Monte Carlo, market making |

### 🖥️ Admin & Operations

| Document | Description | Key Topics |
|----------|-------------|------------|
| [Admin Dashboard Documentation](./admin-dashboard-documentation.md) | Trading dashboard and admin tools | Bet verification, parameter management, manual entry, notification system |
| [Scraping Infrastructure](./SCRAPING_INFRASTRUCTURE_DOCUMENTATION.md) | Data ingestion and scraping | WhosScored/SofaScore parsers, data quality, live scraping, anti-detection |

### 📱 Mobile Application

| Document | Description | Key Topics |
|----------|-------------|------------|
| [Mobile Features Documentation](./MOBILE_FEATURES_DOCUMENTATION.md) | Mobile-specific implementations | Push notifications, deep linking, native integrations, attribution tracking |

### 🗄️ Data & Infrastructure

| Document | Description | Key Topics |
|----------|-------------|------------|
| [Database Schema Documentation](./DATABASE_SCHEMA_DOCUMENTATION.md) | Complete database schema | 95+ tables, relationships, indexes, ERD diagrams |
| [Infrastructure & Deployment](./INFRASTRUCTURE_DEPLOYMENT_DOCUMENTATION.md) | AWS infrastructure and CI/CD | ECS, RDS, MSK Kafka, deployment strategies, auto-scaling |
| [Infrastructure Summary](./INFRASTRUCTURE_SUMMARY.md) | Quick reference for infrastructure | Common commands, troubleshooting, emergency procedures |

---

## Documentation Structure

### Phase 1: User Onboarding
- Registration & authentication (OAuth, native)
- KYC verification
- Location detection
- Push notification setup

**Key Documents**: [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 1

### Phase 2: Account Funding
- Deposit flow
- Payment processing (PayPal, cards, Apple Pay)
- 3DS authentication
- Bonus grant mechanics

**Key Documents**:
- [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 2
- [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md) → Deposit Match

### Phase 3: Bet Creation
- Zonal fantasy interface
- Real-time odds calculation
- Bet validation
- Promotional application

**Key Documents**:
- [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 3
- [Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md) → Odds Calculation Pipeline
- [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md) → Bet Modifiers

### Phase 4: Live Match Tracking
- WebSocket real-time updates
- Live odds recalculation
- Event ingestion
- Match state management

**Key Documents**:
- [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 4
- [Scraping Infrastructure](./SCRAPING_INFRASTRUCTURE_DOCUMENTATION.md) → Live Scraping

### Phase 5: Bet Settlement
- Two-pass verification workflow
- Leg evaluation logic
- Payout calculation
- Backed bet distribution

**Key Documents**:
- [Bet Settlement Logic](./BET_SETTLEMENT_DOCUMENTATION.md)
- [System Architecture](./TBG_Complete_System_Architecture.md) → Match Settlement

### Phase 6: Social Features
- Bet backing (Team Up)
- Share card generation
- Deep linking
- Referral system

**Key Documents**:
- [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 5
- [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md) → Referral & Partner Promos
- [Mobile Features](./MOBILE_FEATURES_DOCUMENTATION.md) → Deep Linking

### Phase 7: Withdrawal & Payout
- Withdrawal eligibility
- Payment processing
- KYC requirements
- Anti-fraud checks

**Key Documents**:
- [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 6
- [Risk Management](./RISK_MANAGEMENT_DOCUMENT.md) → Withdrawal Controls

---

## Technical Deep Dives

### For Backend Engineers

**Statistical Models & Algorithms**:
1. [Backend-Odds Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md)
   - Team Action Model (GLM with Poisson/NegBin)
   - Player Action Model (Empirical Bayes)
   - Zonal Dirichlet Model (Bayesian spatial priors)
   - Vine Copula correlation
   - Monte Carlo simulation engine

**Database & Data Layer**:
1. [Database Schema Documentation](./DATABASE_SCHEMA_DOCUMENTATION.md)
   - 95+ tables with full column details
   - Foreign key relationships
   - Index strategies
   - Shared vs. exclusive tables

**Business Logic**:
1. [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md)
   - 8+ promotion types
   - Grant priority logic
   - Validation rules
2. [Bet Settlement Logic](./BET_SETTLEMENT_DOCUMENTATION.md)
   - Settlement workflow
   - Edge case handling
   - Payout calculations

### For Frontend Engineers

**User Flows**:
1. [System Architecture](./TBG_Complete_System_Architecture.md)
   - Complete user journey with API calls
   - State management patterns
   - API integration points

**Mobile Development**:
1. [Mobile Features Documentation](./MOBILE_FEATURES_DOCUMENTATION.md)
   - Push notifications setup
   - Deep linking implementation
   - Native integrations (AppsFlyer, PostHog)
   - Platform-specific code

### For DevOps Engineers

**Infrastructure**:
1. [Infrastructure & Deployment](./INFRASTRUCTURE_DEPLOYMENT_DOCUMENTATION.md)
   - AWS architecture (ECS, RDS, MSK)
   - CI/CD pipelines (6 workflows)
   - Deployment strategies
   - Auto-scaling configuration

2. [Infrastructure Summary](./INFRASTRUCTURE_SUMMARY.md)
   - Quick reference commands
   - Troubleshooting guide
   - Emergency procedures

**Database Management**:
1. [Database Schema Documentation](./DATABASE_SCHEMA_DOCUMENTATION.md)
   - Migration strategies
   - Backup procedures
   - Partitioning recommendations

### For Product Managers

**Feature Documentation**:
1. [Tournament System](./TOURNAMENT_SYSTEM_DOCUMENTATION.md)
   - Tournament formats
   - Leaderboard mechanics
   - Prize distribution

2. [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md)
   - Promotion types and use cases
   - Business rules
   - Configuration examples

**Risk & Compliance**:
1. [Risk Management](./RISK_MANAGEMENT_DOCUMENT.md)
   - User tier system
   - Fraud detection
   - Regulatory compliance
   - Betting limits

### For Data Scientists

**Statistical Models**:
1. [Backend-Odds Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md)
   - Model theory and implementation
   - Calibration methods
   - Backtesting framework
   - Market making strategies

**Data Sources**:
1. [Scraping Infrastructure](./SCRAPING_INFRASTRUCTURE_DOCUMENTATION.md)
   - Data ingestion pipelines
   - Data quality checks
   - Parser implementations

### For Traders & Risk Managers

**Trading Tools**:
1. [Admin Dashboard Documentation](./admin-dashboard-documentation.md)
   - Trading dashboard features
   - Bet verification tools
   - Parameter management
   - Manual overrides

**Risk Management**:
1. [Risk Management](./RISK_MANAGEMENT_DOCUMENT.md)
   - Exposure tracking
   - Limit management
   - Sharp bettor detection
   - Fraud prevention

---

## Key Concepts

### Zonal Fantasy Betting
A unique betting mechanic where users select teams and place them on a 3×3 grid representing a soccer pitch. Bets are placed on actions (goals, shots, tackles) happening in specific zones.

**Documents**: [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 3

### Bet Backing (Team Up)
Social betting feature allowing users to "back" (join) other users' bets, sharing the risk and potential payout proportionally.

**Documents**: [System Architecture](./TBG_Complete_System_Architecture.md) → Phase 5

### Promotional System
Multi-tiered system supporting 8+ promotion types with complex eligibility rules, automated granting, and bet-level integration.

**Documents**: [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md)

### Statistical Model Pipeline
Three-layer model system (TAM, PAM, ZDM) with copula-based correlation for accurate parlay odds pricing.

**Documents**: [Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md)

### Two-Pass Settlement
Bet settlement workflow that validates match data, evaluates legs, handles partial voids, and distributes payouts in two separate passes.

**Documents**: [Bet Settlement Logic](./BET_SETTLEMENT_DOCUMENTATION.md)

---

## Repository Structure

```
/workspace/group/
├── README_DOCUMENTATION_INDEX.md                    # This file
├── TBG_Complete_System_Architecture.md              # System overview & user flows
├── PROMOTIONAL_SYSTEM_DOCUMENTATION.md              # Promotion mechanics
├── TOURNAMENT_SYSTEM_DOCUMENTATION.md               # Tournament system
├── BET_SETTLEMENT_DOCUMENTATION.md                  # Settlement logic
├── RISK_MANAGEMENT_DOCUMENT.md                      # Risk & fraud
├── Backend-Odds_Statistical_Models_Documentation.md # Statistical models
├── admin-dashboard-documentation.md                 # Admin tools
├── SCRAPING_INFRASTRUCTURE_DOCUMENTATION.md         # Data ingestion
├── MOBILE_FEATURES_DOCUMENTATION.md                 # Mobile features
├── DATABASE_SCHEMA_DOCUMENTATION.md                 # Database schema
├── INFRASTRUCTURE_DEPLOYMENT_DOCUMENTATION.md       # Infrastructure
└── INFRASTRUCTURE_SUMMARY.md                        # Quick reference
```

---

## Technology Stack Summary

### Frontend
- **Web**: Next.js 15.5.7, React 19, Tailwind CSS 4, Three.js
- **Mobile**: React Native 0.79.5, Expo 53, Expo GL
- **State**: Zustand 5.0.6, TanStack Query 5.83.0
- **Payments**: PayPal SDK, Apple Pay

### Backend-Server (Python)
- **Framework**: FastAPI (async REST API)
- **Database**: PostgreSQL (asyncpg), SQLAlchemy 2.0, Alembic
- **Cache**: Redis 7.0
- **Auth**: JWT (PyJWT)
- **Payments**: PayPal SDK, Square
- **Notifications**: Twilio
- **Cloud**: AWS (boto3, S3)
- **Monitoring**: OpenTelemetry, Prometheus

### Backend-Odds (Python)
- **Framework**: FastAPI + WebSocket
- **Statistics**: NumPy, Pandas, SciPy, PyTorch
- **Models**: Statsmodels, pyvinecopulib
- **Database**: PostgreSQL (asyncpg)
- **Cache**: Redis
- **Streaming**: Kafka/Redpanda (AWS MSK)
- **Monitoring**: OpenTelemetry + Grafana

### Infrastructure (AWS)
- **Compute**: ECS Fargate (2 clusters, 10+ services)
- **Database**: Aurora PostgreSQL (Multi-AZ, automated backups)
- **Cache**: ElastiCache for Redis
- **Streaming**: MSK Serverless (Kafka)
- **Load Balancer**: Application Load Balancer
- **Storage**: S3, ECR
- **Networking**: VPC, Security Groups
- **CI/CD**: GitHub Actions (6 workflows)

---

## Statistics

- **Total Lines of Code**: ~105,000 LOC
  - Frontend: ~50k LOC (TypeScript/React)
  - Backend-Server: ~30k LOC (Python)
  - Backend-Odds: ~25k LOC (Python)

- **Database Tables**: 95+ tables
  - Backend-Server: 51 tables
  - Backend-Odds: 44 tables
  - Shared: 7 conceptual tables

- **API Endpoints**: 200+ endpoints
  - User management, authentication, bets, payments, tournaments, admin

- **WebSocket Connections**: 10,000+ concurrent supported

- **Promotion Types**: 8+ types
  - Bet modifier, bonus bet, referral, partner, instant, daily, weekly, tournament

- **Statistical Models**: 3 core models
  - TAM (Team Action Model)
  - PAM (Player Action Model)
  - ZDM (Zonal Dirichlet Model)

- **Deployment Environments**: 3
  - Development, Staging, Production

---

## Getting Started

### For New Engineers

1. **Start with System Architecture**: Read [TBG Complete System Architecture](./TBG_Complete_System_Architecture.md) to understand the full system
2. **Choose Your Domain**:
   - Frontend: [System Architecture](./TBG_Complete_System_Architecture.md) + [Mobile Features](./MOBILE_FEATURES_DOCUMENTATION.md)
   - Backend: [Database Schema](./DATABASE_SCHEMA_DOCUMENTATION.md) + [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md)
   - Data Science: [Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md)
   - DevOps: [Infrastructure](./INFRASTRUCTURE_DEPLOYMENT_DOCUMENTATION.md)
3. **Deep Dive**: Read domain-specific documents
4. **Hands-On**: Set up local environment following infrastructure guide

### For Stakeholders

1. **Product Overview**: [System Architecture](./TBG_Complete_System_Architecture.md) → Executive Summary
2. **Feature Deep Dives**:
   - Promotions: [Promotional System](./PROMOTIONAL_SYSTEM_DOCUMENTATION.md)
   - Tournaments: [Tournament System](./TOURNAMENT_SYSTEM_DOCUMENTATION.md)
   - Risk: [Risk Management](./RISK_MANAGEMENT_DOCUMENT.md)
3. **Technical Capabilities**: [Statistical Models](./Backend-Odds_Statistical_Models_Documentation.md)

---

## Maintenance

This documentation was created on **2026-03-03** through automated analysis of the TBG codebase. To keep it up to date:

1. **Regular Reviews**: Review quarterly or after major feature releases
2. **Update Process**: Update relevant docs when architecture/features change
3. **Version Control**: Track documentation changes in git alongside code
4. **Feedback Loop**: Engineers should flag outdated sections during code reviews

---

## Contact & Support

For questions about this documentation or to report inaccuracies:

1. **Code**: Refer to inline comments in the source repositories
2. **Architecture**: Consult the engineering team
3. **Updates**: Submit documentation PRs to keep docs current

---

## Document Version Control

| Document | Version | Last Updated | Status |
|----------|---------|--------------|--------|
| System Architecture | 1.0 | 2026-03-03 | ✅ Complete |
| Promotional System | 1.0 | 2026-03-03 | ✅ Complete |
| Tournament System | 1.0 | 2026-03-03 | ✅ Complete |
| Bet Settlement | 1.0 | 2026-03-03 | ✅ Complete |
| Risk Management | 1.0 | 2026-03-03 | ✅ Complete |
| Statistical Models | 1.0 | 2026-03-03 | ✅ Complete |
| Admin Dashboard | 1.0 | 2026-03-03 | ✅ Complete |
| Scraping Infrastructure | 1.0 | 2026-03-03 | ✅ Complete |
| Mobile Features | 1.0 | 2026-03-03 | ✅ Complete |
| Database Schema | 1.0 | 2026-03-03 | ✅ Complete |
| Infrastructure | 1.0 | 2026-03-03 | ✅ Complete |

---

**Total Documentation Coverage**: 100% of core systems
**Maintained By**: Engineering Team
**Created**: 2026-03-03
**Repository**: TBG Platform Documentation
