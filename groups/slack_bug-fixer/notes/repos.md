# Repository Reference

## Backend-Server (TBG-AI/Backend-Server)
- **Framework**: FastAPI + Python
- **Base branch**: `dev`
- **Bug label**: `Bug`
- **Architecture**: Clean architecture — domain/application/infrastructure layers
- **Key paths**:
  - `src/backend_server/app.py` — Main app, exception handlers
  - `src/backend_server/infrastructure/api/rest/` — API routes
  - `src/backend_server/application/services/` — Business logic
  - `src/backend_server/infrastructure/microservices/` — External service clients
  - `src/backend_server/infrastructure/middleware/` — Middleware (metrics, request ID, timing)

## Backend-Odds (TBG-AI/Backend-Odds)
- **Framework**: FastAPI + Python
- **Base branch**: `dev`
- **Bug label**: `bug`
- **Purpose**: Odds calculation microservice
- **Key endpoints**:
  - `/odds/get_parlay_odds` — Parlay odds calculation
  - `/odds/builder/game/{game_id}/all-odds` — Game odds builder

## Conventions
- Branch naming: `fix/<issue-number>-<short-description>`
- Commit message: include `Fixes #<issue-number>`
- PR base: always `dev`
- PR body: Summary, Root Cause, Changes, Testing sections
