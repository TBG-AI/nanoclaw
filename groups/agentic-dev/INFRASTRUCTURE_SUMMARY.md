# Infrastructure and Deployment Summary

Quick reference guide for the TBG platform infrastructure and deployment systems.

---

## System Architecture Overview

### Three Main Application Tiers

1. **Frontend** (Next.js monorepo)
   - Web application (port 3000)
   - Admin panel (port 3001)
   - Mobile app (React Native)

2. **Backend-Server** (FastAPI)
   - Main API service (port 8000)
   - Unified scheduler (background worker)

3. **Backend-Odds** (FastAPI)
   - Odds calculation service (port 8080)
   - TBG-Streaming: 5 microservices (Kafka-based)

### Deployment Environments

| Environment | Branch | Cluster | Image Tag | Purpose |
|-------------|--------|---------|-----------|---------|
| Dev | `dev` | `softlaunch-test` | `dev` | Active development |
| Stage/Test | `stage` | `softlaunch-test` | `test` | Pre-production testing |
| Production | `main` | `softlaunch-prod` | `latest` | Live production |

---

## AWS Infrastructure at a Glance

### Core Services

- **ECS**: Container orchestration (2 clusters)
- **ECR**: Docker image registry
- **RDS**: PostgreSQL Aurora cluster (Multi-AZ)
- **ElastiCache**: Redis cluster
- **MSK**: Kafka serverless (for streaming)
- **ALB**: Application load balancers (2 per environment)
- **S3**: Environment configuration files
- **SSM**: Parameter Store for secrets
- **CloudWatch**: Logs and monitoring

### Region & Networking

- **Region**: us-east-1 (Virginia)
- **VPC**: 2 subnets (us-east-1a, us-east-1b)
- **Security Groups**: ECS tasks + ALB

---

## CI/CD Pipeline Flow

```
Dev Branch
    ↓
Dev Tests (dev_test.yml)
    ↓
Merge dev → stage (merge_dev_to_stage.yml)
    ↓
Stage Deploy (stage_deploy.yml)
    ↓
Stage Tests (stage_test.yml)
    ↓
Merge stage → main (merge_stage_to_main.yml)
    ↓
Production Deploy (main_deploy.yml)
```

### Key Workflows

- **Dev Testing**: Integration tests before stage
- **Stage Deployment**: Parallel service deployment with matrix strategy
- **Production Deployment**: Requires test verification (24h), automatic DB migration
- **Database Sync**: Alembic migrations with rollback capability

---

## Deployment Strategies

### 1. Unified Deployment (Primary Method)

**Script:** `deploy.sh`

```bash
# Full deployment
./deploy.sh test --all --build

# Specific services
./deploy.sh test --services main,odds --build

# Production
./deploy.sh prod --services main --build --branch main
```

### 2. Rolling Deployment (Default)

- Used for: HTTP services (main, odds, frontend, admin)
- Time: 5-10 minutes
- No extra infrastructure cost
- Brief mixed version state

### 3. Blue/Green Deployment (Zero Downtime)

- Used for: Production critical deployments
- CodeDeploy integration
- 100% traffic shift after health checks
- Instant rollback capability
- Time: ~10 minutes

### 4. Canary Deployment (Risk Mitigation)

- Gradual traffic shift (10% → 100%)
- Monitoring period: 5-15 minutes
- Automatic rollback on failure
- Best for high-risk changes

---

## Environment Configuration

### Three-Layer System

```
Layer 1: S3 .env files (non-sensitive)
    ↓
Layer 2: SSM Parameter Store (secrets)
    ↓
Layer 3: Inline environment (build metadata)
```

**Precedence:** Inline > SSM > S3

### Quick Commands

```bash
# View S3 config
aws s3 cp s3://softlaunch-test/main/test_main.env -

# List SSM secrets
aws ssm get-parameters-by-path --path /tbg/test/main/

# Update secret
./scripts/security/update_parameter.sh --env prod --service main --interactive
```

---

## Service Overview

| Service | Port | CPU | Memory | Replicas | Auto-Scale |
|---------|------|-----|--------|----------|------------|
| Main Backend | 8000 | 1024 | 3072 | 2-7 | ✓ |
| Odds Backend | 8080 | 1024 | 3072 | 2-7 | ✓ |
| Frontend | 3000 | 512 | 1024 | 1-5 | ✓ |
| Admin | 3001 | 512 | 1024 | 1 | ✗ |
| Scheduler | - | 1024 | 3072 | 1 | ✗ |
| TBG API/WS | 8082 | 512 | 1024 | 1 | ✗ |
| TBG Workers (4) | - | 512 | 1024 | 1 each | ✗ |

---

## Database Management

### PostgreSQL (RDS Aurora)

**Production:**
- Endpoint: `prod-db-cluster.cluster-cb0m42w8q68o.us-east-1.rds.amazonaws.com:5432`
- Databases: `new_db` (main), `odds_stage_v1` (odds)
- Multi-AZ: Yes
- Backups: Automated (7-day retention)

### Alembic Migrations

```bash
# Upgrade
alembic upgrade head

# Downgrade
alembic downgrade -1

# Check status
alembic current

# View history
alembic history
```

### Automated Migration (GitHub Actions)

Called automatically during deployments:
- Captures pre-migration revision
- Runs `alembic upgrade head`
- Validates success
- Creates GitHub issue on failure

---

## Monitoring & Logging

### CloudWatch Log Groups

```bash
# Main backend
aws logs tail /ecs/softlaunch-test-main --follow

# Odds backend
aws logs tail /ecs/softlaunch-test-odds --follow

# Scheduler
aws logs tail /ecs/softlaunch-test-scheduler --follow

# TBG Streaming (all 5 services)
aws logs tail /ecs/softlaunch-test-tbg --follow
```

### Service Status

```bash
# Quick status
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-main \
  --query 'services[].{name:serviceName,running:runningCount,desired:desiredCount}'

# All services
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-main softlaunch-test-odds \
            softlaunch-test-frontend softlaunch-test-scheduler
```

### Search Logs

```bash
# Find errors
aws logs filter-log-events \
  --log-group-name /ecs/softlaunch-test-main \
  --filter-pattern "ERROR"
```

---

## Auto-Scaling

### Configuration

**Default:**
- Min: 2 tasks
- Max: 7 tasks
- CPU target: 50%
- Memory target: 50%

**Enable Auto-Scaling:**
```bash
./scripts/policies/autoscaling.sh --env test odds main
```

**Check Status:**
```bash
./scripts/policies/check_autoscaling.sh --env test --service odds
```

---

## Secrets Management

### AWS SSM Parameter Store

**Path Convention:** `/tbg/{env}/{service}/{parameter}`

**Common Tasks:**

```bash
# List secrets
./scripts/security/list_parameters.sh --env prod --service main

# Update interactively
./scripts/security/update_parameter.sh --env prod --service main --interactive

# Migrate from .env
./scripts/security/migrate_all_secrets.sh --env prod --dry-run
```

**After secret update:**
```bash
aws ecs update-service --cluster softlaunch-prod \
  --service softlaunch-prod-main --force-new-deployment
```

---

## Disaster Recovery

### Quick Recovery Actions

**1. Rollback Service:**
```bash
./scripts/deploy/rollback_deployment.sh --service main --env test
```

**2. Database Restore:**
```bash
# From snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier prod-db-cluster-restored \
  --snapshot-identifier manual-backup-20250301

# Point-in-time
aws rds restore-db-cluster-to-point-in-time \
  --source-db-cluster-identifier prod-db-cluster \
  --restore-to-time 2025-03-01T12:00:00Z
```

**3. Redeploy from Git Tag:**
```bash
./deploy.sh prod --services main --build --branch <commit-hash>
```

### Git Commit Tracking

Every deployment tagged with:
- Git commit hash
- Branch name
- Timestamp
- Deployer
- Environment

View tags:
```bash
aws ecs describe-task-definition \
  --task-definition softlaunch-test-main:242 \
  --include TAGS
```

---

## Load Balancer Configuration

### ALBs per Environment

1. **Rolling Deployment ALB**
   - Name: `softlaunch-alb-{env}`
   - For: Normal deployments

2. **Blue/Green ALB**
   - Name: `softlaunch-bg-{env}`
   - For: Zero-downtime deployments

### Routing Rules

- `/` → Frontend (3000)
- `/main/*` → Main Backend (8000)
- `/odds/*` → Odds Backend (8080)
- `/odds-v2/*` → TBG Streaming (8082)
- `/admin/*` → Admin (3001)

### Health Checks

- Path: `/health`
- Interval: 30s
- Timeout: 5s
- Healthy threshold: 2
- Grace period: 180s (deployments)

---

## Common Operations

### Deploy New Feature

```bash
# 1. Deploy to test
./deploy.sh test --services main --build

# 2. Monitor deployment
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-main

# 3. Check logs
aws logs tail /ecs/softlaunch-test-main --follow

# 4. If successful, promote to production
./deploy.sh prod --services main --build --branch main
```

### Update Configuration

```bash
# 1. Update .env file in repo
# 2. Upload to S3 only
./deploy.sh test --services main --env-only

# 3. Force reload
aws ecs update-service --cluster softlaunch-test \
  --service softlaunch-test-main --force-new-deployment
```

### Troubleshoot Service Issues

```bash
# 1. Check service status
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-main

# 2. Check recent events
aws ecs describe-services --cluster softlaunch-test \
  --services softlaunch-test-main \
  --query 'services[].events[:5]'

# 3. Check logs
aws logs tail /ecs/softlaunch-test-main --follow

# 4. Check stopped tasks
aws ecs list-tasks --cluster softlaunch-test \
  --service-name softlaunch-test-main \
  --desired-status STOPPED

# 5. Get task stop reason
aws ecs describe-tasks --cluster softlaunch-test \
  --tasks <task-id> \
  --query 'tasks[].{stop:stoppedReason,exit:containers[].exitCode}'
```

### Rotate Secret

```bash
# 1. Generate new secret
openssl rand -base64 64

# 2. Update in SSM
./scripts/security/update_parameter.sh \
  --env prod --service main --parameter JWT_SECRET_KEY

# 3. Restart service
aws ecs update-service --cluster softlaunch-prod \
  --service softlaunch-prod-main --force-new-deployment
```

---

## Resource Locations

### Repositories

- **Deployment**: `/workspace/extra/programming/deployment/`
- **Frontend**: `/workspace/extra/programming/Frontend/`
- **Backend-Server**: `/workspace/extra/programming/Backend-Server/`
- **Backend-Odds**: `/workspace/extra/programming/Backend-Odds/`

### Key Scripts

- **Build**: `deployment/scripts/build/build_services.sh`
- **Deploy**: `deployment/scripts/deploy.sh`
- **Security**: `deployment/scripts/security/`
- **Monitoring**: `deployment/scripts/monitoring/`
- **Policies**: `deployment/scripts/policies/`

### Documentation

- **Main Guide**: `deployment/README.md`
- **Index**: `deployment/docs/index.md`
- **Environment Vars**: `deployment/docs/env-variables.md`
- **Monitoring**: `deployment/docs/monitoring.md`
- **Blue/Green**: `deployment/BLUE_GREEN_SETUP.md`

### GitHub Actions

- **Deployment Workflows**: `deployment/.github/workflows/`
- **Frontend CI**: `Frontend/.github/workflows/deploy.yml`
- **Backend-Server CI**: `Backend-Server/.github/workflows/test-pipeline.yml`
- **Backend-Odds CI**: `Backend-Odds/.github/workflows/test-pipeline.yml`

---

## Emergency Contacts & Support

### Troubleshooting Priority

1. Check ECS service status
2. Review CloudWatch logs
3. Verify ALB target health
4. Check database connectivity
5. Review recent deployments
6. Consider rollback if recent deploy
7. Scale up if capacity issue
8. Check secrets/configuration

### Key AWS Resources

- **ECS Console**: Services → Events
- **CloudWatch**: Log groups, metrics
- **CodeDeploy**: Deployment history
- **ALB**: Target group health
- **RDS**: Database monitoring
- **ECR**: Container images

---

**Quick Start:** For your first deployment, see `deployment/README.md`

**Full Documentation:** See `INFRASTRUCTURE_DEPLOYMENT_DOCUMENTATION.md`

**Support Contact:** vxbrandon00@gmail.com
