---
name: deploy
description: Deploy a TBG service. Builds Docker image, pushes to ECR, updates ECS task def, bumps build version. Use when user asks to deploy, ship, or release.
user_invocable: true
---

# Deploy

## Purpose

Wraps the unified deploy script in the **deployment repo** so contributors never have to remember which repo, flags, or ECS service name to use. Handles the 4 TBG services, ensures the right branch is deployed, and runs post-deploy health checks.

> **Key fact about this codebase**: the actual `deploy.sh` does NOT live inside any of the source repos. It lives in a separate `deployment` repo at `/Users/jlee/Desktop/programming/startup/project_zap/session_12_26/deployment`, and `--build` does a **fresh shallow clone from GitHub** — it never uses the local working tree. That means: to deploy a change, it must be **committed and pushed** to the branch you pass via `--branch`.

## Scope: 4 services

All four services go through the same unified script:

```bash
cd /Users/jlee/Desktop/programming/startup/project_zap/session_12_26/deployment
./scripts/deploy.sh <env> --services <svc> --build [--branch <name>]
```

| Service | Source repo (GitHub) | `--services` flag | ECS service name | Log group |
|---|---|---|---|---|
| Backend-Server (main + scheduler) | `TBG-AI/Backend-Server` | `main` and/or `scheduler` | `softlaunch-{env}-main`, `softlaunch-{env}-scheduler` | `/ecs/softlaunch-{env}-main`, `/ecs/softlaunch-{env}-scheduler` |
| Backend-Odds | `TBG-AI/Backend-Odds` | `odds` | `softlaunch-{env}-odds` | `/ecs/softlaunch-{env}-odds` |
| Frontend (web + admin) | `TBG-AI/Frontend` | `frontend` and/or `admin` | `softlaunch-{env}-frontend`, `softlaunch-{env}-admin` | `/ecs/softlaunch-{env}-frontend`, `/ecs/softlaunch-{env}-admin` |
| Kalshi ingest (TBG Streaming) | `TBG-AI/Backend-Odds` (subdirectory `tbg-streaming/`) | `tbg-streaming --tbg-stream-sub kalshi` | `softlaunch-{env}-tbg-ingest-kalshi` | `/ecs/softlaunch-{env}-tbg` |

**About Kalshi / `tbg-streaming`**: the TBG-DOCS plan calls out `tbg-streaming` as a "separate repo". In reality, `tbg-streaming/` lives as a **subdirectory inside `Backend-Odds`** (`Backend-Odds/tbg-streaming/`), with its own `pyproject.toml`, Dockerfile, and deploy path. The deploy script handles it through the `--services tbg-streaming` flag plus an optional `--tbg-stream-sub` list. All 5 sub-services (`api`, `worker`, `updater`, `ingest`, `kalshi`) share a single log group `/ecs/softlaunch-{env}-tbg`.

**Environments**: `test` (direct deploy), `prod` (requires `y/N` confirmation at script level), `dev` (direct). Branch defaults: stage→test, main→prod.

## Step 1: Ask which service

If the user didn't say which service or environment, use AskUserQuestion:

1. **Which service(s)?** — Backend-Server (main), Backend-Odds (odds), Frontend (web), Admin, Scheduler, Kalshi ingest, or a combination. If unclear, offer: `main`, `odds`, `frontend`, `admin`, `scheduler`, `kalshi`, `all`.
2. **Which environment?** — `test` (default), `prod`, `dev`.
3. **Which branch?** — If omitted, the script uses `stage` for test and `main` for prod. Ask if they want to override (e.g., a feature branch).

Map the user's plain-English answer to the right flags:

| User says | Flag(s) |
|---|---|
| "backend", "main backend" | `--services main` |
| "odds" | `--services odds` |
| "scheduler" | `--services scheduler` |
| "frontend", "web" | `--services frontend` |
| "admin" | `--services admin` |
| "kalshi", "kalshi ingest" | `--services tbg-streaming --tbg-stream-sub kalshi` |
| "streaming", "tbg streaming", "odds-v2" | `--services tbg-streaming` (all sub-services) |
| "everything", "all" | `--all` |

## Step 2: Pre-deploy checks

**Important**: because `deploy.sh --build` clones fresh from GitHub, the source of truth is the **remote branch**, not the local working tree. The checks below make sure the remote branch actually contains what the user expects.

Run these from the repo being deployed (or from a worktree of it):

```bash
# Which branch would we deploy?
git rev-parse --abbrev-ref HEAD

# Is the working tree clean?
git status --porcelain

# Is HEAD pushed?
git fetch origin && git log origin/<branch>..HEAD --oneline
#   → empty output means remote is up-to-date with local HEAD

# What commit will actually be deployed (what the deploy script will clone)?
git ls-remote origin <branch> | awk '{print substr($1,1,7)}'
```

Pre-deploy checklist:

- [ ] Working tree clean (`git status --porcelain` is empty)
- [ ] On the branch the user expects
- [ ] Local HEAD is pushed to `origin/<branch>`
- [ ] Optional but recommended: CI is green on that commit (`gh run list --branch <branch> --limit 1`)
- [ ] **Prod only**: the user has explicitly confirmed they want prod

If any check fails, STOP and surface the problem. Do NOT auto-commit, do NOT auto-push.

## Step 3: Bump build version

**Reality check**: there is no single "build version" file to bump in this codebase. The deploy mechanism is different per service — here's what actually happens:

### Backend-Server and Backend-Odds (Python services)

- No manual version bump required.
- `pyproject.toml` contains no `version` field (tool config only).
- `src/backend_server/__init__.py` / similar has `__version__ = "1.0.0"` as a static constant; this has **not** been used as the rolling build marker in practice.
- The deploy script auto-captures the **git commit short hash** from the freshly cloned repo and injects it into the ECS task def as the env var `GIT_COMMIT_HASH`. The backend reads `os.getenv("APP_VERSION", "1.0.0")` in `src/backend_server/logging_formatter.py:168` for the `service.version` log field, which defaults to `1.0.0` unless `APP_VERSION` is set at runtime.
- **Action**: make sure your latest commit is pushed. `GIT_COMMIT_HASH` will bump automatically as a side effect.

### Frontend web (`apps/web`)

- `apps/web/package.json` has a `version` field (currently `0.1.0`). It is **not** required for deploys to work — the Docker image is tagged by env (`test`, `latest`, or `dev`), not by this field. Bump it manually only if the team has chosen to use it as a release marker for the client-side `X-App-Version` header.
- Web builds get `GIT_COMMIT_HASH` injected into the task def just like the backends.

### Frontend mobile (`apps/mobile`)

- `apps/mobile/app.config.js` reads from env vars: `VERSION`, `ANDROID_VERSION_CODE`, `IOS_BUILD_NUMBER` (see lines 89-91).
- `eas.json` sets `"appVersionSource": "remote"` and `autoIncrement: true` for the `production` profile — **EAS bumps build numbers automatically on production builds**.
- Mobile releases go through EAS Build + EAS Submit, not through this deploy skill. This skill only handles the web `frontend` service behind the ALB.

### Kalshi ingest (inside `Backend-Odds/tbg-streaming/`)

- Same story as Backend-Odds: no manual version file, git commit hash auto-captured.

### Pre-flight one-liners to verify the above before authoring a PR about versions

Run in the source repo if you want to double-check anything before deploying:

```bash
# Backend-Server version references
grep -rn "__version__\|APP_VERSION\|GIT_COMMIT_HASH" src/ | head

# Backend-Odds version references
grep -rn "__version__\|APP_VERSION\|GIT_COMMIT_HASH" src/ | head

# Frontend web version
node -p "require('./apps/web/package.json').version"

# Frontend mobile version env vars
grep -n "VERSION\|BUILD_NUMBER\|VERSION_CODE" apps/mobile/app.config.js
```

**Bottom line**: the only thing the user MUST do for a deploy to actually ship new code is **commit and push to the branch being deployed**. The "bumped build version" is the new git commit hash.

If the user is making a breaking client-facing change that needs the stale-file convention to kick in (see cross-refs below), then they must bump the client app version (`apps/mobile` env vars for mobile, `apps/web/package.json` for web) and update the `X-App-Version` header flow — but that's a code change, not a deploy step, and should already be committed before running this skill.

## Step 4: Run the deploy command

Move into the deployment repo and run the unified script. Show the exact command to the user before running it.

```bash
cd /Users/jlee/Desktop/programming/startup/project_zap/session_12_26/deployment
```

### Common invocations

```bash
# Backend-Server (main) → test
./scripts/deploy.sh test --services main --build

# Backend-Odds → test
./scripts/deploy.sh test --services odds --build

# Frontend (web) → test
./scripts/deploy.sh test --services frontend --build

# Scheduler (lives in Backend-Server repo) → test
./scripts/deploy.sh test --services scheduler --build

# Kalshi ingest only → test
./scripts/deploy.sh test --services tbg-streaming --tbg-stream-sub kalshi --build

# All TBG Streaming sub-services (api, worker, updater, ingest, kalshi)
./scripts/deploy.sh test --services tbg-streaming --build

# Feature branch
./scripts/deploy.sh test --services odds --build --branch my-feature-branch

# Prod deploy (script will prompt y/N)
./scripts/deploy.sh prod --services main,odds,scheduler --build

# Everything to test
./scripts/deploy.sh test --all --build

# Redeploy existing image without rebuild (just rolls ECS service)
./scripts/deploy.sh test --services main

# Update .env files in S3 only, no code rebuild (then force a redeploy to pick them up)
./scripts/deploy.sh test --services main --env-only
aws ecs update-service --cluster softlaunch-test --service softlaunch-test-main \
  --force-new-deployment --region us-east-1
```

### What `--build` actually does (Build Pipeline, 7 steps)

1. Clones the source repo from GitHub (`https://github.com/TBG-AI/<repo>.git`, shallow, specific branch)
2. Uploads `.env.{env}` to `s3://softlaunch-{env}/{service}/`
3. Docker build via `buildx` targeting `linux/amd64`
4. Pushes image to ECR at `014498654370.dkr.ecr.us-east-1.amazonaws.com/softlaunch/{test/}{svc}:{tag}`
5. Auto-generates a task definition JSON (queries SSM at `/tbg/{env}/{service}/` for secrets)
6. Registers the new task def revision
7. Updates the ECS service to the new task def (rolling deployment)

### Execution rules for this skill

- For `test` / `dev`: run the command directly after showing the user what it is.
- For `prod`: **always** confirm interactively before running, even though the script itself also prompts. Two gates is fine.
- Never suppress stdout/stderr — the user needs to see build and push progress.
- If the script exits non-zero, STOP and surface the error. Do not move to Step 5.

## Step 5: Post-deploy verification

Immediately after `deploy.sh` returns successfully, run these checks:

### 5a. Confirm the ECS service is rolling the new task def

```bash
aws ecs describe-services --cluster softlaunch-<env> \
  --services softlaunch-<env>-<svc> \
  --query 'services[].deployments[].{status:status,running:runningCount,desired:desiredCount,taskDef:taskDefinition}' \
  --output table --region us-east-1
```

- Wait until the PRIMARY deployment has `running == desired`. On test, that's typically 1-3 minutes; on prod, 3-8 minutes.
- If a new task keeps stopping, run the "Container keeps crashing" diagnostic in the Troubleshooting section below.

### 5b. Tail logs for ~30 seconds (invoke the `cw-logs` skill if available)

Equivalent raw command:

```bash
aws logs tail /ecs/softlaunch-<env>-<svc> --since 5m --format short --region us-east-1 \
  | grep -i -E "error|exception|traceback|critical|startup|initialized|listening" | head -40
```

For Kalshi specifically:
```bash
aws logs tail /ecs/softlaunch-<env>-tbg --since 5m --format short --region us-east-1 \
  | grep -i -E "kalshi|error|Processed.*ticker" | head -40
```

### 5c. Health endpoints (HTTP services only)

Hit the ALB-exposed health endpoint. Paths vary by service — on the new ALB layout:

```bash
# Main backend
curl -sS -o /dev/null -w "%{http_code}\n" https://<test-alb-dns>/main/health

# Odds backend
curl -sS -o /dev/null -w "%{http_code}\n" https://<test-alb-dns>/odds/health

# Frontend (web) — Next.js health route
curl -sS -o /dev/null -w "%{http_code}\n" https://<test-alb-dns>/api/health
```

Expect `200`. If unknown, look up the current ALB DNS:
```bash
aws elbv2 describe-load-balancers --names softlaunch-alb-test \
  --query 'LoadBalancers[0].DNSName' --output text --region us-east-1
```

### 5d. Error-rate spike check (Grafana)

The plan calls for confirming error rate has not spiked in Grafana 5 minutes after deploy. Open the Grafana dashboard for the service and compare the last 5 min to the previous 15 min. If no Grafana access, substitute:

```bash
aws logs tail /ecs/softlaunch-<env>-<svc> --since 5m --format short --region us-east-1 \
  | grep -c -i -E "error|exception|traceback"
```

Report the count and flag anything above ~10/min as suspect (tune per-service — odds and main have higher baselines than scheduler).

### 5e. Report to the user

Structured summary:
- Service(s) deployed
- Env
- Branch
- Git commit short hash (`git ls-remote origin <branch> | awk '{print substr($1,1,7)}'`)
- Task definition family + revision (from the `describe-services` output)
- Running/desired count
- Any errors or warnings spotted in logs
- Direct link: `aws logs tail /ecs/softlaunch-<env>-<svc> --follow --region us-east-1`

## Step 6: Rollback procedure

If health checks fail or errors spike, roll back immediately. There are two paths:

### Option A: Use the rollback script (preferred)

```bash
cd /Users/jlee/Desktop/programming/startup/project_zap/session_12_26/deployment/scripts/deploy
./rollback_deployment.sh --service <svc> --env <env>
#   or, to a specific revision:
./rollback_deployment.sh --service <svc> --env <env> --version <N>
```

Where `<svc>` is the short name (`main`, `odds`, `frontend`, `admin`, `scheduler`). Note: this script targets the blue/green service name `softlaunch-{env}-{svc}-bg` — if your service isn't on blue/green yet, fall back to Option B.

### Option B: Manual rollback via ECS update-service

```bash
# 1. List prior task def revisions
aws ecs list-task-definitions --family-prefix softlaunch-<env>-<svc> \
  --sort DESC --max-items 5 --region us-east-1

# 2. Update the service to the previous revision
aws ecs update-service --cluster softlaunch-<env> \
  --service softlaunch-<env>-<svc> \
  --task-definition softlaunch-<env>-<svc>:<previous-revision> \
  --region us-east-1

# 3. Watch it roll back
aws ecs describe-services --cluster softlaunch-<env> \
  --services softlaunch-<env>-<svc> \
  --query 'services[].deployments[].{status:status,running:runningCount,taskDef:taskDefinition}' \
  --output table --region us-east-1
```

### When to rollback vs. roll forward

| Situation | Action |
|---|---|
| New tasks fail to reach RUNNING | Rollback |
| Health endpoint returns 5xx consistently | Rollback |
| Error rate spike >3× baseline in 5 min | Rollback |
| Minor new warnings, service healthy | Roll forward with a fix |
| ECS deployment stuck but no crashes | Check for bad secret or missing SSM param first, then rollback |

### Ask before rolling back prod

For `prod`, STOP and get explicit user approval before running the rollback command, even if errors spike. For `test`/`dev`, just go.

## Troubleshooting

### Container keeps crashing (task stopped)

```bash
# Find stopped tasks
aws ecs list-tasks --cluster softlaunch-<env> --service-name softlaunch-<env>-<svc> \
  --desired-status STOPPED --region us-east-1

# Then describe them for exit reason
aws ecs describe-tasks --cluster softlaunch-<env> --tasks <task-arn> \
  --query 'tasks[].{stopCode:stopCode,reason:stoppedReason,containers:containers[].{name:name,exitCode:exitCode,reason:reason}}' \
  --region us-east-1
```

### Task def inspect (what env vars are set?)

```bash
aws ecs describe-task-definition --task-definition softlaunch-<env>-<svc> \
  --query 'taskDefinition.containerDefinitions[0].{env:environment,secrets:secrets[*].name,envFiles:environmentFiles}' \
  --region us-east-1
```

### Force redeploy without rebuild (e.g., to pick up new S3 env or SSM secret)

```bash
aws ecs update-service --cluster softlaunch-<env> --service softlaunch-<env>-<svc> \
  --force-new-deployment --region us-east-1
```

## Cross-references

- **Deployment command reference** (exhaustive flag list, all scenarios): `/Users/jlee/.claude/commands/deploy.md`
- **CloudWatch log viewer skill**: `cw-logs` (`/Users/jlee/.claude/commands/cw-logs.md`) — wraps `aws logs tail` per service and env
- **Deployment overview (AWS infra)**: `TBG-DOCS/deployment/deployment_overview.md`
- **Stale code rules**: `TBG-DOCS/plans/03-skills/stale-code-rules.md` — explains why client app build version matters for routing between legacy and new service code. The deploy step only ships code; it's the frontend `X-App-Version` header that the backend middleware keys off to choose between `user_bet_service.py` and `user_bet_service_legacy.py`. If you're shipping a breaking change, the stale-code convention must be in the source code BEFORE this deploy runs.
- **Plan spec this skill implements**: `TBG-DOCS/plans/03-skills/deploy.md`
- **Canonical deploy script**: `/Users/jlee/Desktop/programming/startup/project_zap/session_12_26/deployment/scripts/deploy.sh`
