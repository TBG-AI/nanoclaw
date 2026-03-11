# Infrastructure and Deployment Documentation

Comprehensive infrastructure, CI/CD, and deployment documentation for the TBG betting platform across all three main repositories: Frontend, Backend-Server, and Backend-Odds.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [AWS Infrastructure](#aws-infrastructure)
3. [CI/CD Pipelines](#cicd-pipelines)
4. [Docker Configuration](#docker-configuration)
5. [Deployment Strategies](#deployment-strategies)
6. [Environment Configuration Management](#environment-configuration-management)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Database Management](#database-management)
9. [Secrets Management](#secrets-management)
10. [Load Balancing and Auto-Scaling](#load-balancing-and-auto-scaling)
11. [Disaster Recovery](#disaster-recovery)
12. [Service-Specific Details](#service-specific-details)

---

## 1. System Overview

### Architecture

The TBG platform consists of three main application tiers deployed on AWS ECS:

- **Frontend**: Next.js monorepo (web + admin + mobile apps)
- **Backend-Server**: FastAPI main backend service + unified scheduler
- **Backend-Odds**: Odds calculation and prediction service
- **TBG-Streaming**: Real-time odds streaming (Kafka-based microservices)

### Environments

| Environment | Branch | Purpose | AWS Cluster | Image Tag |
|-------------|--------|---------|-------------|-----------|
| **Development** | `dev` | Active development | `softlaunch-test` | `dev` |
| **Stage/Test** | `stage` | Pre-production testing | `softlaunch-test` | `test` |
| **Production** | `main` | Live production | `softlaunch-prod` | `latest` |

### Deployment Repository

Central deployment orchestration: `/workspace/extra/programming/deployment/`

Contains:
- Build scripts for all services
- Deployment automation
- Infrastructure configuration
- GitHub Actions workflows
- Task definitions
- Security/secrets management

---

## 2. AWS Infrastructure

### ECS Cluster Configuration

**Clusters:**
- `softlaunch-test` - Shared by dev and stage environments
- `softlaunch-prod` - Production only

**Region:** `us-east-1` (US East - Virginia)

### VPC and Networking

**Network Configuration:** `/workspace/extra/programming/deployment/scripts/config/network.sh`

```bash
# VPC Subnets (us-east-1a, us-east-1b)
SUBNET1="subnet-027e21b4652c664cf"
SUBNET2="subnet-0c1687d4396d1b2bb"

# Security Groups
SECURITY_GROUP1="sg-0ed22f14fb1c3a0bb"  # ECS tasks
SECURITY_GROUP2="sg-017bd0fc47039ea61"  # ALB
```

### ECS Services

| Service | ECS Service Name | Container Port | CPU | Memory | Replicas |
|---------|------------------|----------------|-----|--------|----------|
| Main Backend | `softlaunch-{env}-main` | 8000 | 1024 | 3072 | 2-7 (auto-scaled) |
| Odds Backend | `softlaunch-{env}-odds` | 8080 | 1024 | 3072 | 2-7 (auto-scaled) |
| Frontend | `softlaunch-{env}-frontend` | 3000 | 512 | 1024 | 1-5 (auto-scaled) |
| Admin | `softlaunch-{env}-admin` | 3001 | 512 | 1024 | 1 |
| Scheduler | `softlaunch-{env}-scheduler` | none | 1024 | 3072 | 1 (background) |
| TBG API/WS | `softlaunch-{env}-tbg-api-ws` | 8082 | 512 | 1024 | 1 |
| TBG Worker | `softlaunch-{env}-tbg-compute-worker` | - | 512 | 1024 | 1 |
| TBG Updater | `softlaunch-{env}-tbg-odds-updater` | - | 512 | 1024 | 1 |
| TBG Ingest API | `softlaunch-{env}-tbg-ingest-odds-api` | - | 512 | 1024 | 1 |
| TBG Ingest Kalshi | `softlaunch-{env}-tbg-ingest-kalshi` | - | 512 | 1024 | 1 |

### RDS Database

**Production Cluster:**
- Endpoint: `prod-db-cluster.cluster-cb0m42w8q68o.us-east-1.rds.amazonaws.com`
- Engine: PostgreSQL
- Multi-AZ: Yes (cluster)
- Port: 5432

**Databases:**
- `new_db` - Main backend database
- `odds_stage_v1` - Stage odds database
- `postgres` - Default database

**Connection Pooling:**
```bash
DB_POOL_SIZE=40
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
```

### ElastiCache (Redis)

**Production:**
- Cluster: `softlaunch-demo-cache`
- Endpoint: `clustercfg.softlaunch-demo-cache.rckujr.use1.cache.amazonaws.com:6379`
- Engine: Redis
- Use: Session storage, caching, rate limiting

### MSK (Kafka) - Serverless

**Configuration:**
```bash
KAFKA_BOOTSTRAP=boot-q1yals8l.c3.kafka-serverless.us-east-1.amazonaws.com:9098
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=AWS_MSK_IAM
```

**Topics:**
- `odds.market_updates` - Real-time odds streaming

### ECR (Container Registry)

**Registry:** `014498654370.dkr.ecr.us-east-1.amazonaws.com`

**Image Naming Convention:**

| Environment | Pattern | Example |
|-------------|---------|---------|
| Test | `softlaunch/{env}/{service}:{tag}` | `softlaunch/test/main:test` |
| Production | `softlaunch/{service}:{tag}` | `softlaunch/main:latest` |

**Repositories:**
- `softlaunch/main`
- `softlaunch/odds`
- `softlaunch/frontend`
- `softlaunch/admin`
- `softlaunch/scheduler`
- `softlaunch/test/main`
- `softlaunch/test/odds`
- `softlaunch/test/frontend`
- `softlaunch/test/admin`
- `softlaunch/test/scheduler`

### Application Load Balancers

**Rolling Deployment ALB:**
- Name: `softlaunch-alb-{env}`
- DNS: `softlaunch-alb-{env}-*.us-east-1.elb.amazonaws.com`

**Blue/Green Deployment ALB:**
- Name: `softlaunch-bg-{env}`
- DNS: `softlaunch-bg-{env}-*.us-east-1.elb.amazonaws.com`

**Target Groups:**
- Blue (production): `softlaunch-{env}-{service}-blue`
- Green (staging): `softlaunch-{env}-{service}-green`

**Routing Rules:**
- `/` → Frontend
- `/main/*` → Main Backend
- `/odds/*` → Odds Backend
- `/odds-v2/*` → TBG Streaming
- `/admin/*` → Admin panel

### S3 Buckets

**Environment Files:**
- `softlaunch-test` - Test and dev environment configs
- `softlaunch-prod` - Production environment configs

**Paths:**
```
s3://softlaunch-{bucket}/{service}/{prefix}_{service}.env
```

Examples:
- `s3://softlaunch-test/main/test_main.env`
- `s3://softlaunch-prod/main/production_main.env`
- `s3://softlaunch-test/frontend/test_frontend.env`

---

## 3. CI/CD Pipelines

### GitHub Actions Workflow Architecture

Located in: `/workspace/extra/programming/deployment/.github/workflows/`

#### Development → Production Flow

```
1. Dev Branch Development
   ↓
2. Dev E2E + Integration Tests (dev_test.yml)
   ↓
3. Merge dev → stage (merge_dev_to_stage.yml)
   ↓
4. Stage Deployment (stage_deploy.yml)
   ↓
5. Stage E2E + Integration Tests (stage_test.yml)
   ↓
6. Merge stage → main (merge_stage_to_main.yml)
   ↓
7. Production Deployment (main_deploy.yml)
```

### Key Workflows

#### 1. Development Testing
**File:** `dev_test.yml`

Triggered by:
- Manual workflow dispatch
- Repository dispatch (`dev-branch-updated`)
- Push to dev branch

Actions:
- Sets up testing environment
- Runs integration tests across all services
- Collects and uploads test artifacts
- Auto-cleanup

#### 2. Merge Dev to Stage
**File:** `merge_dev_to_stage.yml`

Triggered by:
- Successful dev tests (automatic)
- Manual workflow dispatch

Actions:
- Merges `dev` → `stage` across all repos
- Creates GitHub issues for merge conflicts
- Includes commit hashes for traceability

#### 3. Stage Deployment
**File:** `stage_deploy.yml`

**Parameters:**
- `services`: Select specific services or `all`
- `action`: `build_only`, `deploy_only`, `build_and_deploy`

**Features:**
- Parallel service deployment using matrix strategy
- Docker buildx with layer caching
- Automatic GitHub issue creation on failure
- Post-deployment verification

**Example:**
```yaml
services: [frontend, main, odds, streaming]
action: build_and_deploy
```

#### 4. Stage Testing
**File:** `stage_test.yml`

Triggered by:
- Manual workflow dispatch
- Post-deployment (automatic)

Actions:
- Comprehensive E2E tests against staged services
- Upload test reports as artifacts

#### 5. Production Deployment
**File:** `main_deploy.yml`

**Safety Features:**
- Branch verification (must be `main`)
- Test status verification (tests must pass within 24 hours)
- Test override option (requires approval)
- Automatic database migration
- Post-deployment verification

**Deployment Steps:**
1. Verify on main branch
2. Check recent test status
3. Build services (if required)
4. Deploy to production
5. Sync production database
6. Verify deployment

#### 6. Database Sync
**File:** `sync_db.yml`

Reusable workflow for database operations:
- Migrate (alembic upgrade head)
- Rollback (alembic downgrade)
- Pre-migration revision capture
- Post-migration verification

**Parameters:**
- `environments`: Comma-separated (sandbox, stage, prod)
- `branch`: Branch to checkout
- `action`: `migrate` or `rollback`
- `rollback_revision`: Target revision for rollback

### Frontend-Specific Workflow
**File:** `/workspace/extra/programming/Frontend/.github/workflows/deploy.yml`

Triggers:
- Push to `dev` branch
- Pull requests to `dev`

Actions:
- Builds Next.js applications
- Runs Playwright E2E tests (currently disabled)
- Triggers deployment repo integration tests on `[ready-to-deploy]` commit message

### Backend-Server Workflow
**File:** `/workspace/extra/programming/Backend-Server/.github/workflows/test-pipeline.yml`

Currently **manual trigger only** (disabled auto-triggers)

Actions:
- Sets up Docker Buildx
- Builds main service with layer caching
- Starts docker-compose test environment
- Runs pytest E2E tests
- Displays Docker logs on failure
- Triggers sandbox deployment on `[deploy-to-sandbox]` message

**Docker Layer Caching:**
```yaml
cache-from: type=gha,scope=main-service
cache-to: type=gha,mode=max,scope=main-service
```

### Backend-Odds Workflow
**File:** `/workspace/extra/programming/Backend-Odds/.github/workflows/test-pipeline.yml`

Similar structure to Backend-Server with odds-specific tests.

---

## 4. Docker Configuration

### Frontend Dockerfile

**Location:** `/workspace/extra/programming/Frontend/deploy/dockers/Dockerfile.prod`

**Multi-stage build:**

**Stage 1 - Builder:**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy workspace configuration
COPY package*.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY patches ./patches
COPY apps/web/package.json ./apps/web/package.json
# ... other workspace package.json files

# Install dependencies (cached layer)
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .
COPY apps/web/.env.prod apps/web/.env.local

# Build with Next.js cache mount
RUN --mount=type=cache,target=/app/apps/web/.next/cache \
    pnpm run build:web

# Prune dev dependencies
RUN pnpm prune --prod
```

**Stage 2 - Runner:**
```dockerfile
FROM node:20-alpine AS runner
WORKDIR /app

RUN npm install -g pnpm

# Copy production dependencies
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/web/node_modules ./apps/web/node_modules

# Copy built application
COPY --from=builder /app/apps/web/.next ./apps/web/.next
COPY --from=builder /app/apps/web/public ./apps/web/public

ENV PORT=3000
EXPOSE 3000
WORKDIR /app/apps/web
CMD ["pnpm", "start"]
```

### Backend-Server Dockerfile

**Location:** `/workspace/extra/programming/Backend-Server/deployment/backend/Dockerfile`

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential g++ gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (caching)
COPY src/backend_server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install local packages
RUN pip install --no-cache-dir src/shared/
RUN pip install --no-cache-dir .

# Create non-root user
RUN chmod +x scripts/deploy/entrypoint.sh scripts/deploy/start_server.sh && \
    groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./scripts/deploy/entrypoint.sh"]
CMD ["./scripts/deploy/start_server.sh"]
```

### Backend-Odds Dockerfile

**Location:** `/workspace/extra/programming/Backend-Odds/deployment/Dockerfile`

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies including C++ libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git libpq-dev build-essential gcc cmake \
    libboost-all-dev libeigen3-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8080

RUN chmod +x scripts/entrypoint.sh scripts/start_server.sh
ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["./scripts/start_server.sh"]
```

### Scheduler Dockerfile

**Location:** `/workspace/extra/programming/Backend-Server/deployment/scheduler/Dockerfile`

Similar to Backend-Server but with scheduler-specific entrypoint:

```dockerfile
CMD ["python", "-m", "scheduler.main"]
```

### Docker Compose (Testing)

**Location:** `/workspace/extra/programming/Backend-Server/tests/docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: jlee
      POSTGRES_DB: new_db
      POSTGRES_HOST_AUTH_METHOD: trust
    ports:
      - "5430:5432"
    volumes:
      - ./test_db_dump.sql:/docker-entrypoint-initdb.d/01_schema.sql
      - ./test_seed_data.sql:/docker-entrypoint-initdb.d/02_seed_data.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jlee -d new_db"]
      interval: 5s

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5670:5672"
      - "15670:15672"

  redis:
    image: redis:alpine
    ports:
      - "6377:6379"

  app:
    build:
      context: ../
      dockerfile: Dockerfile
    env_file: .env.test
    depends_on:
      - postgres
      - rabbitmq
      - redis
    ports:
      - "8000:8000"
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 5. Deployment Strategies

### Unified Deployment Script

**Location:** `/workspace/extra/programming/deployment/scripts/deploy.sh`

**Usage:**
```bash
./deploy.sh <env> [options]
```

**Options:**
- `<env>`: Required - `test`, `prod`, or `dev`
- `--services <list>`: Comma-separated services
- `--all`: Deploy all services
- `--build`: Build and push Docker images
- `--branch <branch>`: Override git branch
- `--env-only`: Upload env files only (no build/deploy)

**Examples:**
```bash
# Full deploy to test
./deploy.sh test --all --build

# Deploy specific services
./deploy.sh test --services main,odds --build

# Deploy scheduler from feature branch
./deploy.sh test --services scheduler --build --branch dev-scheduler-unified

# Update environment variables only
./deploy.sh test --services main --env-only
```

### Rolling Deployment

**Script:** `deploy_rolling.sh`

**Used for:** HTTP services (main, odds, frontend, admin)

**Process:**
1. Register new task definition
2. Update ECS service
3. ECS gradually replaces tasks (min healthy: 100%, max: 200%)
4. Health checks via ALB target groups
5. Old tasks terminated after new tasks healthy

**Advantages:**
- Simple, quick deployment (5-10 minutes)
- No extra infrastructure cost
- Minimal downtime

**Disadvantages:**
- Brief mixed version state
- Harder to rollback instantly

### Blue/Green Deployment

**Script:** `deploy_blue_green.sh`

**Used for:** Production deployments requiring zero downtime

**Process:**
1. Create new task definition (green)
2. Deploy green tasks to green target group
3. Wait for health checks (180s grace period)
4. CodeDeploy shifts ALB listener to green
5. Blue tasks terminated after 5 minutes

**Configuration:**
- Deployment Controller: AWS CodeDeploy
- Strategy: `CodeDeployDefault.ECSAllAtOnce`
- Traffic shift: 100% immediately after health check
- Rollback: Instant via CodeDeploy

**Setup:**
```bash
# One-time setup
cd deployment/scripts/setup
./setup_codedeploy_role.sh

cd ../alb
./create_alb_bluegreen.sh test

# Deploy
cd ../deploy
./deploy_blue_green.sh --service main --env test
```

### Canary Deployment

**Script:** `deploy_canary.sh`

**Used for:** High-risk production changes

**Strategies:**

**Canary10Percent5Minutes (Recommended):**
```
0 min:  Blue: 100% | Green: 0%
5 min:  Blue: 90%  | Green: 10% ← Canary monitoring
10 min: Blue: 0%   | Green: 100% ← Full cutover
```

**Canary10Percent15Minutes (Conservative):**
```
0 min:  Blue: 100% | Green: 0%
15 min: Blue: 90%  | Green: 10% ← Extended canary
30 min: Blue: 0%   | Green: 100%
```

**Usage:**
```bash
./deploy_canary.sh --service main --env prod
```

**Automatic Rollback:** If health checks fail during canary period, CodeDeploy automatically reverts to blue.

### Rollback

**Script:** `rollback_deployment.sh`

**Methods:**

**1. Automatic Rollback (CodeDeploy):**
```bash
aws deploy stop-deployment \
  --deployment-id <id> \
  --auto-rollback-enabled
```

**2. Manual Rollback to Previous Version:**
```bash
./rollback_deployment.sh --service main --env test
```

**3. Rollback to Specific Revision:**
```bash
# List task definitions
aws ecs list-task-definitions \
  --family-prefix softlaunch-test-main \
  --sort DESC

# Rollback
aws ecs update-service \
  --cluster softlaunch-test \
  --service softlaunch-test-main \
  --task-definition softlaunch-test-main:240
```

---

## 6. Environment Configuration Management

### Three-Layer System

Environment variables are loaded in order:

```
┌─────────────────────────────────────────────────┐
│             ECS Container                        │
│                                                  │
│  Layer 1: S3 .env file (non-sensitive config)    │
│  Layer 2: SSM Parameter Store (secrets)          │
│  Layer 3: Inline environment (hardcoded values)  │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Precedence:** Inline > SSM > S3 (last wins)

### Layer 1: S3 Environment Files

**Purpose:** Non-sensitive configuration

**Process:**
1. `build_services.sh` clones repo
2. Finds `.env.{stage|prod}` file
3. Uploads to S3 via `aws s3 cp`
4. ECS task definition references S3 ARN in `environmentFiles`

**S3 Paths:**

| Service | S3 Path | Source File |
|---------|---------|-------------|
| main | `s3://softlaunch-{env}/main/{prefix}_main.env` | `deployment/backend/config/.env.{stage\|prod}` |
| odds | `s3://softlaunch-{env}/odds/{prefix}_odds.env` | `.env.{stage\|prod}` |
| frontend | `s3://softlaunch-{env}/frontend/{prefix}_frontend.env` | `apps/web/.env.{stage\|prod}` |
| admin | `s3://softlaunch-{env}/admin/{prefix}_admin.env` | `apps/admin/.env.{stage\|prod}` |
| scheduler | `s3://softlaunch-{env}/scheduler/{prefix}_scheduler.env` | `deployment/backend/config/.env.scheduler.{stage\|prod}` |

**Update Process:**
```bash
# Full deploy
./deploy.sh test --services main --build

# Env-only (no rebuild)
./build_services.sh --main --env test --env-only
```

After S3 upload, force new deployment to pick up changes:
```bash
aws ecs update-service --cluster softlaunch-test \
  --service softlaunch-test-main --force-new-deployment
```

### Layer 2: SSM Parameter Store (Secrets)

**Purpose:** Sensitive values (passwords, API keys, tokens)

**Path Convention:** `/tbg/{env}/{service}/{PARAM_NAME}`

**Examples:**
- `/tbg/prod/main/JWT_SECRET_KEY`
- `/tbg/test/odds/DATABASE_URL`
- `/tbg/prod/main/TWILIO_AUTH_TOKEN`

**Auto-Discovery:**

During build, `build_services.sh` calls `generate_ssm_secrets()`:
```bash
aws ssm get-parameters-by-path --path /tbg/{env}/{service}/
```

All discovered parameters are automatically templated into task definition's `secrets` array.

**Task Definition Example:**
```json
{
  "secrets": [
    {
      "name": "JWT_SECRET_KEY",
      "valueFrom": "/tbg/prod/main/JWT_SECRET_KEY"
    },
    {
      "name": "DATABASE_URL",
      "valueFrom": "/tbg/prod/main/DATABASE_URL"
    }
  ]
}
```

**Add New Secret:**
```bash
# Create parameter
aws ssm put-parameter \
  --name /tbg/test/main/NEW_SECRET \
  --value "secret-value" \
  --type SecureString \
  --region us-east-1

# Rebuild (auto-discovers new secret)
./deploy.sh test --services main --build
```

**Update Existing Secret:**
```bash
# Update SSM
aws ssm put-parameter \
  --name /tbg/test/main/EXISTING_SECRET \
  --value "new-value" \
  --overwrite

# Force ECS to re-resolve SSM
aws ecs update-service \
  --cluster softlaunch-test \
  --service softlaunch-test-main \
  --force-new-deployment
```

**Tools:**

Located in: `/workspace/extra/programming/deployment/scripts/security/`

```bash
# List parameters
./list_parameters.sh --env prod --service main

# Update parameter interactively
./update_parameter.sh --env prod --service main --interactive

# Migrate secrets from .env files
./migrate_all_secrets.sh --env prod --dry-run
```

### Layer 3: Inline Environment

**Purpose:** Build-time metadata, hardcoded values

**Task Definition Example:**
```json
{
  "environment": [
    {
      "name": "GIT_COMMIT_HASH",
      "value": "3fe2fa8"
    },
    {
      "name": "ENV",
      "value": "prod"
    }
  ]
}
```

**Auto-Generated:**
- `GIT_COMMIT_HASH` - Short SHA from build
- `ENV` - Environment name (for scheduler)

### Viewing Current Configuration

```bash
# Check S3 .env file
aws s3 cp s3://softlaunch-test/main/test_main.env -

# List SSM parameters
aws ssm get-parameters-by-path \
  --path /tbg/test/main/ \
  --region us-east-1 \
  --query 'Parameters[].Name'

# Check running container
aws ecs execute-command \
  --cluster softlaunch-test \
  --task <task-id> \
  --container softlaunch-test-main \
  --interactive \
  --command "env | sort"
```

---

## 7. Monitoring and Logging

### CloudWatch Log Groups

| Service | Log Group | Notes |
|---------|-----------|-------|
| main | `/ecs/softlaunch-{env}-main` | |
| odds | `/ecs/softlaunch-{env}-odds` | |
| frontend | `/ecs/softlaunch-{env}-frontend` | |
| admin | `/ecs/softlaunch-{env}-admin` | |
| scheduler | `/ecs/softlaunch-{env}-scheduler` | |
| tbg-streaming | `/ecs/softlaunch-{env}-tbg` | **All 5 TBG services share one log group** |

### Tail Logs

```bash
# Follow logs in real-time
aws logs tail /ecs/softlaunch-test-main --follow --region us-east-1

# Last 10 minutes only
aws logs tail /ecs/softlaunch-test-main --since 10m --region us-east-1

# TBG Streaming (all services)
aws logs tail /ecs/softlaunch-test-tbg --follow --region us-east-1
```

### Search Logs

```bash
# Search for errors
aws logs filter-log-events \
  --log-group-name /ecs/softlaunch-test-main \
  --filter-pattern "ERROR" \
  --region us-east-1

# Search for specific text
aws logs filter-log-events \
  --log-group-name /ecs/softlaunch-test-scheduler \
  --filter-pattern "bet_verification" \
  --region us-east-1

# Time-bounded search (last hour)
aws logs filter-log-events \
  --log-group-name /ecs/softlaunch-test-odds \
  --filter-pattern "ERROR" \
  --start-time $(date -v-1H +%s000) \
  --region us-east-1
```

### Service Status

```bash
# Single service status
aws ecs describe-services \
  --cluster softlaunch-test \
  --services softlaunch-test-main \
  --query 'services[].{name:serviceName,status:status,desired:desiredCount,running:runningCount}' \
  --region us-east-1

# All services at once
aws ecs describe-services \
  --cluster softlaunch-test \
  --services softlaunch-test-main softlaunch-test-odds \
            softlaunch-test-frontend softlaunch-test-admin \
            softlaunch-test-scheduler \
  --query 'services[].{name:serviceName,running:runningCount,desired:desiredCount}' \
  --region us-east-1

# TBG Streaming services
aws ecs describe-services \
  --cluster softlaunch-test \
  --services softlaunch-test-tbg-api-ws \
            softlaunch-test-tbg-compute-worker \
            softlaunch-test-tbg-odds-updater \
            softlaunch-test-tbg-ingest-odds-api \
            softlaunch-test-tbg-ingest-kalshi \
  --query 'services[].{name:serviceName,running:runningCount,desired:desiredCount}' \
  --region us-east-1
```

### Deployment Status

```bash
# Check if deployment is rolling out
aws ecs describe-services \
  --cluster softlaunch-test \
  --services softlaunch-test-main \
  --query 'services[].deployments[].{status:status,desired:desiredCount,running:runningCount,rollout:rolloutState}' \
  --region us-east-1

# Recent events (task start/stop/errors)
aws ecs describe-services \
  --cluster softlaunch-test \
  --services softlaunch-test-main \
  --query 'services[].events[:5].message' \
  --region us-east-1
```

### Task-Level Debugging

```bash
# List running tasks
aws ecs list-tasks \
  --cluster softlaunch-test \
  --service-name softlaunch-test-main \
  --region us-east-1

# Describe task (see stop reason if crashed)
aws ecs describe-tasks \
  --cluster softlaunch-test \
  --tasks <task-id> \
  --query 'tasks[].{status:lastStatus,stop:stoppedReason,health:healthStatus}' \
  --region us-east-1

# Exec into running container
aws ecs execute-command \
  --cluster softlaunch-test \
  --task <task-id> \
  --container softlaunch-test-main \
  --interactive \
  --command "/bin/sh"
```

### Monitoring Scripts

**Location:** `/workspace/extra/programming/deployment/scripts/monitoring/`

**Scheduler Health Check:**
```bash
./scheduler-health.sh
```

**TBG Streaming Logs:**
```bash
./logs_tbg_streaming.sh
```

### CloudWatch Metrics (via ALB)

- Request count
- Error rates (5xx)
- Response times
- Healthy host count
- Unhealthy host count

### Common Issues

**Task keeps restarting:**
```bash
# Check stopped tasks
aws ecs list-tasks \
  --cluster softlaunch-test \
  --service-name softlaunch-test-main \
  --desired-status STOPPED

# Get stop reason
aws ecs describe-tasks \
  --cluster softlaunch-test \
  --tasks <task-id> \
  --query 'tasks[].{stop:stoppedReason,exitCode:containers[].exitCode}'
```

**Deployment stuck:**
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn>

# Force new deployment
aws ecs update-service \
  --cluster softlaunch-test \
  --service softlaunch-test-main \
  --force-new-deployment
```

---

## 8. Database Management

### Alembic Configuration

**Backend-Server:**
- Config: `/workspace/extra/programming/Backend-Server/alembic.ini`
- Migrations: `/workspace/extra/programming/Backend-Server/alembic/versions/`

**Backend-Odds:**
Multiple alembic configurations:
- `alembic.ini` - Main odds database
- `alembic_postgres.ini` - PostgreSQL schema
- `alembic_remote_postgres.ini` - Remote PostgreSQL

### Database Migration Workflow

**GitHub Actions:** `sync_db.yml` (reusable workflow)

**Parameters:**
- `environments`: Comma-separated (sandbox, stage, prod)
- `branch`: Branch to checkout
- `action`: `migrate` or `rollback`
- `rollback_revision`: Target revision (if rollback)

**Process:**

**Migration:**
1. Checkout branch
2. Install alembic + dependencies
3. Store pre-migration revisions
4. Run `alembic upgrade head` for each environment
5. Capture new revisions
6. Create GitHub issue on failure

**Rollback:**
1. Parse rollback revisions JSON
2. Run `alembic downgrade <revision>` for each environment
3. Verify rollback success

**Example Usage:**

Called from stage deployment workflow:
```yaml
sync-stage-database:
  needs: build_and_deploy
  uses: ./.github/workflows/sync_db.yml
  with:
    environments: "stage"
    branch: "stage"
    action: "migrate"
  secrets:
    ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Manual Migration

```bash
# Set database URL
export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/dbname"

# Upgrade to latest
cd Backend-Server
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Check current revision
alembic current

# View migration history
alembic history
```

### Database Backup Strategy

**RDS Automated Backups:**
- Retention period: 7 days (configurable)
- Backup window: Automated
- Point-in-time recovery: Enabled

**Manual Snapshots:**
```bash
# Create snapshot
aws rds create-db-cluster-snapshot \
  --db-cluster-identifier prod-db-cluster \
  --db-cluster-snapshot-identifier manual-backup-$(date +%Y%m%d-%H%M)

# List snapshots
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier prod-db-cluster
```

### Database Access

**Read Replicas:**
- Read operations use: `READ_DATABASE_URL`, `ASYNC_READ_DATABASE_URL`
- Write operations use: `DATABASE_URL`, `ASYNC_DATABASE_URL`

**Connection Strings in SSM:**
- `/tbg/{env}/main/DATABASE_URL`
- `/tbg/{env}/main/ASYNC_DATABASE_URL`
- `/tbg/{env}/main/READ_DATABASE_URL`
- `/tbg/{env}/main/ASYNC_READ_DATABASE_URL`

---

## 9. Secrets Management

### AWS Systems Manager Parameter Store

**Location:** `/workspace/extra/programming/deployment/scripts/security/`

### Parameter Naming Convention

```
/tbg/{env}/{service}/{parameter}
```

**Examples:**
- `/tbg/prod/main/JWT_SECRET_KEY`
- `/tbg/test/odds/DATABASE_URL`
- `/tbg/prod/main/TWILIO_AUTH_TOKEN`

### Management Scripts

**List Parameters:**
```bash
./list_parameters.sh --env prod --service main
```

**Update Parameter:**
```bash
# Interactive selection
./update_parameter.sh --env prod --service main --interactive

# Specific parameter
./update_parameter.sh \
  --env prod \
  --service main \
  --parameter JWT_SECRET_KEY
```

**Migrate from .env Files:**
```bash
# Dry run (preview changes)
./migrate_all_secrets.sh --env prod --dry-run

# Execute migration
./migrate_all_secrets.sh --env prod

# Force overwrite existing
./migrate_all_secrets.sh --env prod --force
```

### Common Tasks

**Rotate JWT Key:**
```bash
# Generate new key
openssl rand -base64 64

# Update SSM
./update_parameter.sh \
  --env prod \
  --service main \
  --parameter JWT_SECRET_KEY

# Force ECS to reload
aws ecs update-service \
  --cluster softlaunch-prod \
  --service softlaunch-prod-main \
  --force-new-deployment
```

**Update Database Password:**
```bash
# 1. Update RDS
aws rds modify-db-instance \
  --db-instance-identifier softlaunch-prod-db \
  --master-user-password "NEW_PASSWORD" \
  --apply-immediately

# 2. Update SSM
./update_parameter.sh \
  --env prod \
  --service main \
  --parameter DATABASE_URL

# 3. Restart services
aws ecs update-service \
  --cluster softlaunch-prod \
  --service softlaunch-prod-main \
  --force-new-deployment
```

### IAM Permissions

**ECS Task Execution Role:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:GetParameters",
    "kms:Decrypt"
  ],
  "Resource": [
    "arn:aws:ssm:us-east-1:*:parameter/tbg/*",
    "arn:aws:kms:us-east-1:*:key/*"
  ]
}
```

### Security Best Practices

1. **Never commit secrets to git**
2. **Use SecureString type for all secrets**
3. **Rotate credentials regularly**
4. **Use different secrets per environment**
5. **Audit parameter access via CloudTrail**
6. **Restrict IAM permissions to least privilege**

### Troubleshooting

**Permission denied:**
```bash
# Verify AWS identity
aws sts get-caller-identity

# Test parameter access
aws ssm get-parameter \
  --name /tbg/test/main/JWT_SECRET_KEY
```

**Parameter not found:**
```bash
# List all parameters for service
./list_parameters.sh --env prod --service main
```

**Task won't start:**
```bash
# Check CloudWatch logs for SSM errors
aws logs tail /ecs/softlaunch-prod-main --follow
```

---

## 10. Load Balancing and Auto-Scaling

### Application Load Balancers

**Rolling Deployment ALB:**
- Name: `softlaunch-alb-{env}`
- Scheme: Internet-facing
- Listeners: HTTP (80) → HTTPS (443) redirect
- SSL/TLS: ACM certificate

**Blue/Green Deployment ALB:**
- Name: `softlaunch-bg-{env}`
- Two listener rules per service (blue/green)
- CodeDeploy integration

### Target Groups

**Health Check Configuration:**
- Protocol: HTTP
- Path: `/health` or service-specific
- Interval: 30s
- Timeout: 5s
- Healthy threshold: 2
- Unhealthy threshold: 2
- Grace period: 180s (for deployments)

### Auto-Scaling Configuration

**Location:** `/workspace/extra/programming/deployment/scripts/policies/autoscaling.sh`

**Default Settings:**
```bash
MIN_CAPACITY=2
MAX_CAPACITY=7
CPU_TARGET_VALUE=50%
MEMORY_TARGET_VALUE=50%
```

**Enable Auto-Scaling:**
```bash
# Single service
./autoscaling.sh --env test odds

# Multiple services
./autoscaling.sh --env prod odds main

# Custom capacity
./autoscaling.sh -m 2 -M 10 --env test odds
```

**Scaling Metrics:**
- CPU Utilization
- Memory Utilization
- Request count per target (ALB)

**Scaling Policies:**
- Scale-out: When CPU > 50% for 2 consecutive periods (60s each)
- Scale-in: When CPU < 50% for 15 consecutive periods (60s each)
- Cooldown: 300s between scale events

### Service-Specific Auto-Scaling

| Service | Min | Max | Notes |
|---------|-----|-----|-------|
| Main Backend | 2 | 7 | Auto-scales on CPU/memory |
| Odds Backend | 2 | 7 | Auto-scales on CPU/memory |
| Frontend | 1 | 5 | Lower scaling due to static content caching |
| Admin | 1 | 1 | No auto-scaling (low traffic) |
| Scheduler | 1 | 1 | Background worker (no auto-scaling) |
| TBG Services | 1 | 1 | Each microservice fixed capacity |

### Scheduled Auto-Scaling

**Script:** `autoscaling_scheduled.sh`

**Use Case:** Pre-scale for known traffic patterns

**Example:**
```bash
# Scale up before high-traffic period
./autoscaling_scheduled.sh \
  --env prod \
  --service main \
  --min 5 \
  --max 10 \
  --schedule "cron(0 18 * * ? *)"  # 6 PM UTC daily
```

### Check Auto-Scaling Status

```bash
./check_autoscaling.sh --env test --service odds
```

**Output:**
- Current desired/running count
- Auto-scaling targets
- Scaling policies
- Recent scaling activities

---

## 11. Disaster Recovery

### Backup Strategy

**RDS Databases:**
- Automated daily backups (7-day retention)
- Manual snapshots before major changes
- Point-in-time recovery enabled
- Multi-AZ deployment (cluster)

**S3 Configuration Files:**
- Versioning enabled
- Cross-region replication (optional)
- Lifecycle policies for old versions

**Docker Images:**
- ECR image scanning enabled
- Image lifecycle policies (keep last 10)
- All production images tagged with git commit hash

### Recovery Procedures

**Database Recovery:**

**1. Restore from Snapshot:**
```bash
# List available snapshots
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier prod-db-cluster

# Restore from snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier prod-db-cluster-restored \
  --snapshot-identifier manual-backup-20250301 \
  --engine aurora-postgresql
```

**2. Point-in-Time Recovery:**
```bash
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier prod-db-cluster-pitr \
  --source-db-cluster-identifier prod-db-cluster \
  --restore-to-time 2025-03-01T12:00:00Z
```

**Service Recovery:**

**1. Rollback to Previous Version:**
```bash
# Find previous working revision
aws ecs list-task-definitions \
  --family-prefix softlaunch-prod-main \
  --sort DESC

# Rollback
aws ecs update-service \
  --cluster softlaunch-prod \
  --service softlaunch-prod-main \
  --task-definition softlaunch-prod-main:240
```

**2. Redeploy from Git Tag:**
```bash
# Deploy from specific commit
./deploy.sh prod \
  --services main \
  --build \
  --branch <commit-hash-or-tag>
```

**3. Complete Service Recreation:**
```bash
# Delete service
aws ecs delete-service \
  --cluster softlaunch-prod \
  --service softlaunch-prod-main \
  --force

# Wait for deletion
# Redeploy
./deploy.sh prod --services main --build
```

### Git Commit Tracking

**Every deployment is tagged with:**
- Git commit hash
- Git branch
- Deployment timestamp
- Deployer
- Environment
- Service

**View Deployment History:**
```bash
aws ecs describe-task-definition \
  --task-definition softlaunch-test-main:242 \
  --include TAGS \
  --query 'tags'
```

**Example Output:**
```json
{
  "tags": [
    {"key": "GitCommit", "value": "a3f4b9c"},
    {"key": "GitBranch", "value": "main"},
    {"key": "DeployedAt", "value": "2025-10-06T20:45:00Z"},
    {"key": "DeployedBy", "value": "jlee"},
    {"key": "Environment", "value": "test"},
    {"key": "Service", "value": "main"}
  ]
}
```

### Disaster Recovery Checklist

**Production Outage:**
1. Check ECS service status
2. Check ALB target health
3. Review CloudWatch logs for errors
4. Check database connectivity
5. Verify Redis/ElastiCache
6. Review recent deployments
7. Rollback if recent deploy caused issue
8. Scale up if capacity issue
9. Restore from backup if data corruption

**Database Corruption:**
1. Identify corruption scope
2. Stop writes (pause scheduler, scale services to 0)
3. Create snapshot of current state
4. Restore from last known good backup
5. Run data validation
6. Resume services
7. Post-mortem analysis

**Configuration Disaster:**
1. Check S3 bucket versioning
2. Restore previous .env file version
3. Verify SSM parameters
4. Force new deployment to pick up correct config

### High Availability

**Multi-AZ Deployment:**
- RDS cluster: Primary + read replica in different AZs
- ECS tasks: Distributed across two subnets (us-east-1a, us-east-1b)
- ALB: Multi-AZ by default

**Redundancy:**
- ElastiCache: Cluster mode enabled
- MSK Kafka: Serverless (auto-managed replication)

---

## 12. Service-Specific Details

### Main Backend Service

**Repository:** `TBG-AI/Backend-Server`

**Configuration:**
- Branch: `stage` (test), `main` (prod)
- Dockerfile: `deployment/backend/Dockerfile`
- ECR Image: `softlaunch/{env}/main:{tag}`
- Port: 8000
- CPU/Memory: 1024/3072

**Environment:**
- S3: `s3://softlaunch-{env}/main/{prefix}_main.env`
- SSM: `/tbg/{env}/main/*`
- Source: `deployment/backend/config/.env.{stage|prod}`

**Deploy:**
```bash
./deploy.sh test --services main --build
```

**Monitoring:**
```bash
aws logs tail /ecs/softlaunch-test-main --follow
```

---

### Odds Backend Service

**Repository:** `TBG-AI/Backend-Odds`

**Configuration:**
- Branch: `stage` (test), `main` (prod)
- Dockerfile: `deployment/Dockerfile`
- ECR Image: `softlaunch/{env}/odds:{tag}`
- Port: 8080
- CPU/Memory: 1024/3072

**Environment:**
- S3: `s3://softlaunch-{env}/odds/{prefix}_odds.env`
- SSM: `/tbg/{env}/odds/*`
- Source: `.env.{stage|prod}`

**Dependencies:**
- C++ libraries (Boost, Eigen)
- PostgreSQL (odds database)
- Redis (caching)

**Deploy:**
```bash
./deploy.sh test --services odds --build
```

---

### Frontend Service

**Repository:** `TBG-AI/Frontend`

**Configuration:**
- Branch: `stage` (test), `main` (prod)
- Dockerfile: `deploy/dockers/Dockerfile.{stage|prod}`
- ECR Image: `softlaunch/{env}/frontend:{tag}`
- Port: 3000
- CPU/Memory: 512/1024

**Monorepo Structure:**
- `apps/web` - Main web application
- `apps/admin` - Admin panel
- `apps/mobile` - React Native mobile app
- `packages/shared` - Shared utilities
- `packages/brands` - Brand theming

**Environment:**
- S3: `s3://softlaunch-{env}/frontend/{prefix}_frontend.env`
- No SSM secrets (all public `EXPO_PUBLIC_*`)
- Source: `apps/web/.env.{stage|prod}`

**Build Features:**
- Multi-stage Docker build
- pnpm workspace
- Next.js cache mount optimization
- Production dependency pruning

**Deploy:**
```bash
./deploy.sh test --services frontend --build
```

---

### Admin Service

**Repository:** `TBG-AI/Frontend` (same as frontend)

**Configuration:**
- Dockerfile: `deploy/dockers/Dockerfile.admin.{stage|prod}`
- ECR Image: `softlaunch/{env}/admin:{tag}`
- Port: 3001
- CPU/Memory: 512/1024
- Replicas: 1 (no auto-scaling)

**Environment:**
- S3: `s3://softlaunch-{env}/admin/{prefix}_admin.env`
- Source: `apps/admin/.env.{stage|prod}`

---

### Scheduler Service

**Repository:** `TBG-AI/Backend-Server` (same as main)

**Configuration:**
- Dockerfile: `deployment/scheduler/Dockerfile`
- ECR Image: `softlaunch/{env}/scheduler:{tag}`
- Port: None (background worker)
- CPU/Memory: 1024/3072
- Replicas: 1 (no auto-scaling)

**Environment:**
- S3: `s3://softlaunch-{env}/scheduler/{prefix}_scheduler.env`
- SSM: `/tbg/{env}/main/*` (shares main's secrets)
- Source: `deployment/backend/config/.env.scheduler.{stage|prod}`
- Inline: `ENV`, `GIT_COMMIT_HASH`

**Jobs:**

| Job | Interval | Type | Description |
|-----|----------|------|-------------|
| live_fetch | 5 min | scraper | Live match data |
| prelive_lineups | 10 min | scraper | Pre-match lineups |
| postmatch_quick | 10 min | scraper | Recent finished matches |
| postmatch_full | 6 hours | scraper | Full post-match refresh |
| metadata_fetch | 6 hours | scraper | Tournament/season metadata |
| dq_audit | 12 hours | scraper | Data quality checks |
| bet_audit | 24 hours | scraper | Bet data integrity |
| bet_verification | 15 min | backend | Verify bets, payouts |
| game_notifications | 15 min | backend | Lineup notifications |
| exchange_rate | 24 hours | backend | Update exchange rates |
| pending_withdrawals | 2 hours | backend | Alert on pending withdrawals |

**Deploy:**
```bash
./deploy.sh test --services scheduler --build --branch dev-scheduler-unified
```

---

### TBG Streaming Service (odds-v2)

**Repository:** Separate `tbg-streaming` monorepo

**Configuration:**
- Build Script: `build_tbg_streaming.sh` (separate)
- Deploy Script: `deploy_tbg_streaming.sh`
- Log Group: `/ecs/softlaunch-{env}-tbg` (shared)

**Architecture - 5 Microservices:**

1. **tbg-api-ws** - API + WebSocket server
   - Port: 8082
   - Serves odds to clients
   - ALB route: `/odds-v2/*`

2. **tbg-compute-worker** - Kafka consumer
   - Processes odds updates
   - No port (internal)

3. **tbg-odds-updater** - Database writer
   - Writes odds to database
   - No port (internal)

4. **tbg-ingest-odds-api** - External odds ingestion
   - Polls the-odds-api.com
   - No port (internal)

5. **tbg-ingest-kalshi** - Kalshi ingestion
   - Polls Kalshi prediction market
   - No port (internal)

**Environment:**
- S3: `s3://softlaunch-{bucket}/tbg-streaming/{env}_tbg-streaming.env`
- No SSM auto-discovery (custom env management)

**Kafka:**
- Topic: `odds.market_updates`
- Bootstrap: `boot-q1yals8l.c3.kafka-serverless.us-east-1.amazonaws.com:9098`

**Deploy:**
```bash
./deploy.sh test --services tbg-streaming --build
# OR using alias
./deploy.sh test --services odds-v2 --build
```

**Monitor:**
```bash
# All TBG services logs
aws logs tail /ecs/softlaunch-test-tbg --follow

# All service status
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-tbg-api-ws \
            softlaunch-test-tbg-compute-worker \
            softlaunch-test-tbg-odds-updater \
            softlaunch-test-tbg-ingest-odds-api \
            softlaunch-test-tbg-ingest-kalshi
```

---

## Quick Reference Commands

### Deploy Services
```bash
# Full deployment
./deploy.sh test --all --build

# Specific services
./deploy.sh test --services main,odds --build

# Production
./deploy.sh prod --services main --build --branch main

# Update environment only
./deploy.sh test --services main --env-only
```

### Check Status
```bash
# Service status
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-main

# Logs
aws logs tail /ecs/softlaunch-test-main --follow

# Task health
aws ecs describe-tasks --cluster softlaunch-test --tasks <task-id>
```

### Database Operations
```bash
# Migrate
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current
alembic current
```

### Secrets Management
```bash
# List secrets
./scripts/security/list_parameters.sh --env prod --service main

# Update secret
./scripts/security/update_parameter.sh \
  --env prod --service main --interactive
```

### Rollback
```bash
# Automatic rollback (CodeDeploy)
aws deploy stop-deployment --deployment-id <id> --auto-rollback-enabled

# Manual rollback
./scripts/deploy/rollback_deployment.sh --service main --env test
```

---

## Additional Resources

**Documentation Files:**
- `/workspace/extra/programming/deployment/README.md` - Main deployment guide
- `/workspace/extra/programming/deployment/docs/index.md` - Documentation index
- `/workspace/extra/programming/deployment/docs/unified-deploy.md` - Unified deploy usage
- `/workspace/extra/programming/deployment/docs/build-pipeline.md` - Build pipeline details
- `/workspace/extra/programming/deployment/docs/env-variables.md` - Environment management
- `/workspace/extra/programming/deployment/docs/monitoring.md` - Monitoring guide
- `/workspace/extra/programming/deployment/BLUE_GREEN_SETUP.md` - Blue/green setup
- `/workspace/extra/programming/deployment/ALB_MIGRATION_GUIDE.md` - ALB migration
- `/workspace/extra/programming/deployment/ADVANCED_FEATURES.md` - Advanced features

**Scripts:**
- Build: `/workspace/extra/programming/deployment/scripts/build/`
- Deploy: `/workspace/extra/programming/deployment/scripts/deploy/`
- Security: `/workspace/extra/programming/deployment/scripts/security/`
- Monitoring: `/workspace/extra/programming/deployment/scripts/monitoring/`
- Policies: `/workspace/extra/programming/deployment/scripts/policies/`

**GitHub Actions:**
- Deployment: `/workspace/extra/programming/deployment/.github/workflows/`
- Frontend: `/workspace/extra/programming/Frontend/.github/workflows/`
- Backend-Server: `/workspace/extra/programming/Backend-Server/.github/workflows/`
- Backend-Odds: `/workspace/extra/programming/Backend-Odds/.github/workflows/`

---

**Document Version:** 1.0
**Last Updated:** March 3, 2026
**Maintained By:** TBG DevOps Team
