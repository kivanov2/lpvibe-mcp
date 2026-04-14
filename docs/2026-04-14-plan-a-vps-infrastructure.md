# Plan A: VPS Infrastructure Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision a single corporate VPS with all shared infrastructure services needed by the LPVibe platform (PostgreSQL, MinIO, Redis, Fluent Bit, Coolify, Caddy), verified end-to-end.

**Architecture:** Coolify is installed standalone (includes its own Traefik for routing user-deployed services via `*.apps.company.dev`). All supporting services (PG, MinIO, Redis, Fluent Bit) and reverse proxy (Caddy for platform API/MCP endpoints) run in a separate docker-compose stack. Platform API and MCP Server containers will be added to this stack in Plans B and C respectively.

**Tech Stack:** Docker, Docker Compose v2, PostgreSQL 16, MinIO (latest), Redis 7, Fluent Bit 3.x, Caddy 2, Coolify (latest)

**Prerequisite:** A VPS (Ubuntu 22.04+ recommended) with root/sudo access, a public IP, and DNS records:
- `api.platform.company.dev` → VPS IP (Platform API, used in Plan B)
- `mcp.platform.company.dev` → VPS IP (MCP Server, used in Plan C)
- `*.apps.company.dev` → VPS IP (Coolify/Traefik, user services)

---

## File Structure

```
lpvibe-mcp/
├── infra/
│   ├── docker-compose.yml              # PG, MinIO, Redis, Fluent Bit, Caddy
│   ├── .env.example                    # all required env vars with placeholders
│   ├── .env                            # real values (gitignored)
│   ├── caddy/
│   │   └── Caddyfile                   # reverse proxy for platform endpoints
│   ├── fluent-bit/
│   │   ├── fluent-bit.conf             # input (docker logs) + output (OpenSearch)
│   │   └── parsers.conf                # JSON log parser
│   ├── postgres/
│   │   └── init.sql                    # platform_db + platform_user creation
│   └── scripts/
│       ├── setup-vps.sh                # one-shot VPS bootstrap (Docker, Compose)
│       ├── install-coolify.sh          # Coolify installation wrapper
│       └── verify-infra.sh             # health-check all services
├── .gitignore                          # .env, secrets, docker volumes
└── docs/
    └── (existing spec + this plan)
```

---

## Task 1: Repository Bootstrap

**Files:**
- Create: `.gitignore`
- Create: `infra/.env.example`
- Create: `infra/scripts/verify-infra.sh`

This task establishes the repo structure and a verification script that will fail until services are up. The verify script is our "test harness" for all subsequent infra tasks.

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp
git init
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Secrets
infra/.env
*.pem
*.key

# Docker volumes
infra/volumes/

# OS
.DS_Store

# Python (for Plans B/C)
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: Create `infra/.env.example`**

```env
# PostgreSQL
POSTGRES_USER=platform_admin
POSTGRES_PASSWORD=CHANGE_ME_PG_ADMIN_PASS
POSTGRES_DB=platform_db
PLATFORM_DB_USER=platform_user
PLATFORM_DB_PASSWORD=CHANGE_ME_PG_USER_PASS

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=CHANGE_ME_MINIO_PASS

# Redis
REDIS_PASSWORD=CHANGE_ME_REDIS_PASS

# Fluent Bit → Corporate OpenSearch
OPENSEARCH_HOST=opensearch.company.internal
OPENSEARCH_PORT=443
OPENSEARCH_USER=CHANGE_ME
OPENSEARCH_PASSWORD=CHANGE_ME
OPENSEARCH_INDEX=platform-logs

# Caddy
PLATFORM_DOMAIN=platform.company.dev
```

- [ ] **Step 4: Create `infra/scripts/verify-infra.sh`**

This script checks every service. Initially all checks fail — that's expected.

```bash
#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
PASS=0
FAIL=0

# Source .env for passwords if available
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

check() {
    local name="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ${name}${NC}"
        ((PASS++))
    else
        echo -e "${RED}✗ ${name}${NC}"
        ((FAIL++))
    fi
}

echo "=== LPVibe Infrastructure Health Check ==="
echo ""

# PostgreSQL: connect and run SELECT 1
check "PostgreSQL is up" docker exec lpvibe-postgres pg_isready -U platform_admin

# PostgreSQL: platform_db exists
check "platform_db exists" docker exec lpvibe-postgres psql -U platform_admin -d platform_db -c "SELECT 1"

# PostgreSQL: platform_user exists
check "platform_user can connect" docker exec lpvibe-postgres psql -U platform_user -d platform_db -c "SELECT 1"

# MinIO: health endpoint
check "MinIO is up" curl -sf http://localhost:9000/minio/health/live

# Redis: PING
check "Redis is up" docker exec lpvibe-redis redis-cli -a "${REDIS_PASSWORD:-changeme}" ping

# Fluent Bit: health
check "Fluent Bit is up" curl -sf http://localhost:2020/api/v1/health

# Caddy: responds on HTTPS (will fail until domains resolve)
check "Caddy is up" curl -sf http://localhost:2019/config/

# Coolify: web UI
check "Coolify is up" curl -sf http://localhost:8080/api/health

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="
[ "$FAIL" -eq 0 ] || exit 1
```

```bash
chmod +x infra/scripts/verify-infra.sh
```

- [ ] **Step 5: Run verify script (expect all failures)**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp
./infra/scripts/verify-infra.sh
```

Expected: all 8 checks fail (services not running). Exit code 1. This confirms the script works.

- [ ] **Step 6: Commit**

```bash
git add .gitignore infra/.env.example infra/scripts/verify-infra.sh
git commit -m "chore: repo bootstrap with .env template and infra verify script"
```

---

## Task 2: VPS Base Provisioning Script

**Files:**
- Create: `infra/scripts/setup-vps.sh`

One-shot script to run on a fresh Ubuntu VPS. Installs Docker, Docker Compose plugin, configures firewall.

- [ ] **Step 1: Create `infra/scripts/setup-vps.sh`**

```bash
#!/usr/bin/env bash
# Run on fresh Ubuntu 22.04+ VPS as root or with sudo.
set -euo pipefail

echo "=== LPVibe VPS Setup ==="

# Update system
apt-get update && apt-get upgrade -y

# Install Docker (official method)
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker installed."
else
    echo "Docker already installed."
fi

# Docker Compose plugin (comes with Docker now, but verify)
if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
    echo "Docker Compose plugin installed."
else
    echo "Docker Compose plugin already available."
fi

# UFW firewall: allow SSH, HTTP, HTTPS
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "Firewall configured."

# Create platform directory
mkdir -p /opt/lpvibe/volumes
echo "Created /opt/lpvibe/"

echo ""
echo "=== VPS base setup complete ==="
echo "Next: install Coolify, then run docker-compose."
```

```bash
chmod +x infra/scripts/setup-vps.sh
```

- [ ] **Step 2: Commit**

```bash
git add infra/scripts/setup-vps.sh
git commit -m "chore: add VPS base provisioning script (Docker, firewall)"
```

---

## Task 3: Install Coolify

**Files:**
- Create: `infra/scripts/install-coolify.sh`

Coolify has an official one-liner install. We wrap it to document the process and post-configure.

- [ ] **Step 1: Create `infra/scripts/install-coolify.sh`**

```bash
#!/usr/bin/env bash
# Installs Coolify on the VPS. Run as root after setup-vps.sh.
set -euo pipefail

echo "=== Installing Coolify ==="

if curl -sf http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "Coolify already running on :8080. Skipping install."
    exit 0
fi

# Official Coolify install (self-hosted)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

echo ""
echo "=== Coolify installed ==="
echo "Open http://<VPS_IP>:8080 in browser to complete initial setup."
echo ""
echo "Post-install checklist:"
echo "  1. Create admin account in Coolify UI"
echo "  2. Add this server as a Coolify destination"
echo "  3. Configure wildcard domain: *.apps.company.dev"
echo "  4. Generate API token: Settings → API → Create Token"
echo "  5. Save the token as COOLIFY_API_TOKEN in infra/.env"
```

```bash
chmod +x infra/scripts/install-coolify.sh
```

- [ ] **Step 2: Commit**

```bash
git add infra/scripts/install-coolify.sh
git commit -m "chore: add Coolify install wrapper with post-install checklist"
```

---

## Task 4: PostgreSQL Service + platform_db

**Files:**
- Create: `infra/postgres/init.sql`
- Create: `infra/docker-compose.yml` (start with just postgres)

- [ ] **Step 1: Create `infra/postgres/init.sql`**

This runs on first container start when the data directory is empty.

```sql
-- Create the platform application user (non-superuser)
CREATE USER platform_user WITH ENCRYPTED PASSWORD 'PLATFORM_DB_PASSWORD_PLACEHOLDER';

-- Create platform metadata database
CREATE DATABASE platform_db OWNER platform_user;

-- Connect to platform_db and set up permissions
\c platform_db

-- platform_user owns the DB and can create tables
GRANT ALL PRIVILEGES ON SCHEMA public TO platform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO platform_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO platform_user;
```

- [ ] **Step 2: Create entrypoint init script**

Docker's initdb.d runs `*.sh` and `*.sql` files. We use a shell script that reads `init.sql` as a template, substitutes the env var, and pipes to psql. The `.sql` file is mounted to a separate path (NOT in initdb.d) to prevent double execution.

Create `infra/postgres/init-db.sh`:

```bash
#!/usr/bin/env bash
# Runs on first postgres start (empty data dir).
# Reads init.sql template, substitutes env vars, executes.
set -euo pipefail
sed "s/PLATFORM_DB_PASSWORD_PLACEHOLDER/${PLATFORM_DB_PASSWORD}/g" /init-templates/init.sql | psql -U "$POSTGRES_USER"
```

```bash
chmod +x infra/postgres/init-db.sh
```

- [ ] **Step 3: Create `infra/docker-compose.yml` (postgres only for now)**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    container_name: lpvibe-postgres
    restart: unless-stopped
    ports:
      - "127.0.0.1:5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PLATFORM_DB_PASSWORD: ${PLATFORM_DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init.sql:/init-templates/init.sql:ro
      - ./postgres/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 4: Create real `.env` from example, start postgres**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/infra
cp .env.example .env
# Edit .env — set real passwords for local dev / VPS
```

```bash
docker compose up -d postgres
```

- [ ] **Step 5: Verify postgres is healthy**

```bash
# Wait for healthy
docker compose ps postgres
# Should show "healthy"

# Check platform_db exists and platform_user can connect
docker exec lpvibe-postgres psql -U platform_user -d platform_db -c "SELECT current_database(), current_user;"
```

Expected output:
```
 current_database | current_user
------------------+---------------
 platform_db      | platform_user
```

- [ ] **Step 6: Commit**

```bash
git add infra/docker-compose.yml infra/postgres/
git commit -m "feat(infra): add PostgreSQL 16 with platform_db auto-provisioning"
```

---

## Task 5: MinIO Service

**Files:**
- Modify: `infra/docker-compose.yml` — add minio service

- [ ] **Step 1: Add MinIO to `infra/docker-compose.yml`**

Add under `services:`:

```yaml
  minio:
    image: minio/minio:latest
    container_name: lpvibe-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Add to `volumes:`:

```yaml
  minio_data:
```

- [ ] **Step 2: Start MinIO**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/infra
docker compose up -d minio
```

- [ ] **Step 3: Verify MinIO health**

```bash
curl -sf http://localhost:9000/minio/health/live
# Expected: HTTP 200
```

```bash
# MinIO console should be reachable
curl -sf http://localhost:9001 -o /dev/null -w "%{http_code}"
# Expected: 200
```

- [ ] **Step 4: Commit**

```bash
git add infra/docker-compose.yml
git commit -m "feat(infra): add MinIO S3-compatible storage"
```

---

## Task 6: Redis Service

**Files:**
- Modify: `infra/docker-compose.yml` — add redis service

- [ ] **Step 1: Add Redis to `infra/docker-compose.yml`**

Add under `services:`:

```yaml
  redis:
    image: redis:7-alpine
    container_name: lpvibe-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Add to `volumes:`:

```yaml
  redis_data:
```

- [ ] **Step 2: Start Redis**

```bash
docker compose up -d redis
```

- [ ] **Step 3: Verify Redis**

```bash
docker exec lpvibe-redis redis-cli -a "${REDIS_PASSWORD}" ping
# Expected: PONG
```

- [ ] **Step 4: Commit**

```bash
git add infra/docker-compose.yml
git commit -m "feat(infra): add Redis 7 with auth"
```

---

## Task 7: Fluent Bit → Corporate OpenSearch

**Files:**
- Create: `infra/fluent-bit/fluent-bit.conf`
- Create: `infra/fluent-bit/parsers.conf`
- Modify: `infra/docker-compose.yml` — add fluent-bit service

- [ ] **Step 1: Create `infra/fluent-bit/parsers.conf`**

```ini
[PARSER]
    Name        docker
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L
    Time_Keep   On

[PARSER]
    Name        json_payload
    Format      json
```

- [ ] **Step 2: Create `infra/fluent-bit/fluent-bit.conf`**

```ini
[SERVICE]
    Flush         5
    Daemon        Off
    Log_Level     info
    Parsers_File  /fluent-bit/etc/parsers.conf
    HTTP_Server   On
    HTTP_Listen   0.0.0.0
    HTTP_Port     2020

[INPUT]
    Name              tail
    Path              /var/lib/docker/containers/*/*.log
    Parser            docker
    Tag               docker.<container_id>
    Read_from_Head    False
    DB                /fluent-bit/db/tail.db
    Mem_Buf_Limit     5MB
    Skip_Long_Lines   On
    Refresh_Interval  10

[FILTER]
    Name              modify
    Match             docker.*
    Add               platform lpvibe
    Add               environment production

[OUTPUT]
    Name              opensearch
    Match             *
    Host              ${OPENSEARCH_HOST}
    Port              ${OPENSEARCH_PORT}
    HTTP_User         ${OPENSEARCH_USER}
    HTTP_Passwd       ${OPENSEARCH_PASSWORD}
    Index             ${OPENSEARCH_INDEX}
    Type              _doc
    tls               On
    tls.verify        On
    Suppress_Type_Name On
    Retry_Limit       3

[OUTPUT]
    Name              stdout
    Match             *
    Format            json_lines
```

Note: dual output — OpenSearch + stdout (for debugging during setup). Remove stdout output when stable.

- [ ] **Step 3: Add Fluent Bit to `infra/docker-compose.yml`**

Add under `services:`:

```yaml
  fluent-bit:
    image: fluent/fluent-bit:latest
    container_name: lpvibe-fluent-bit
    restart: unless-stopped
    environment:
      OPENSEARCH_HOST: ${OPENSEARCH_HOST}
      OPENSEARCH_PORT: ${OPENSEARCH_PORT}
      OPENSEARCH_USER: ${OPENSEARCH_USER}
      OPENSEARCH_PASSWORD: ${OPENSEARCH_PASSWORD}
      OPENSEARCH_INDEX: ${OPENSEARCH_INDEX}
    volumes:
      - ./fluent-bit/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro
      - ./fluent-bit/parsers.conf:/fluent-bit/etc/parsers.conf:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - fluent_bit_db:/fluent-bit/db
    ports:
      - "127.0.0.1:2020:2020"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:2020/api/v1/health"]
      interval: 15s
      timeout: 5s
      retries: 3
```

Add to `volumes:`:

```yaml
  fluent_bit_db:
```

- [ ] **Step 4: Start Fluent Bit**

```bash
docker compose up -d fluent-bit
```

- [ ] **Step 5: Verify Fluent Bit health**

```bash
curl -sf http://localhost:2020/api/v1/health
# Expected: {"status":"ok"}
```

```bash
# Check that it's reading docker logs (metrics endpoint)
curl -s http://localhost:2020/api/v1/metrics | head -20
# Should show input/output plugin metrics
```

Note: actual log delivery to corporate OpenSearch depends on correct credentials in `.env`. If OpenSearch creds aren't available yet (per Open Question §13.2 in spec), Fluent Bit will start but OpenSearch output will show errors in its own logs. That's acceptable — the stdout output proves it's collecting. Wiring to real OpenSearch is verified once creds are provided.

- [ ] **Step 6: Commit**

```bash
git add infra/fluent-bit/ infra/docker-compose.yml
git commit -m "feat(infra): add Fluent Bit log shipper with OpenSearch output"
```

---

## Task 8: Caddy Reverse Proxy

**Files:**
- Create: `infra/caddy/Caddyfile`
- Modify: `infra/docker-compose.yml` — add caddy service

Caddy handles TLS termination and reverse-proxies to Platform API (:8000) and MCP Server (:8001) which are deployed in Plans B and C. For now, we set up the proxy with upstream placeholders.

- [ ] **Step 1: Create `infra/caddy/Caddyfile`**

```caddyfile
# Platform API
api.{$PLATFORM_DOMAIN} {
    reverse_proxy platform-api:8000
}

# MCP Server
mcp.{$PLATFORM_DOMAIN} {
    reverse_proxy mcp-server:8001
}

# Caddy admin API (localhost only, for health checks)
:2019 {
    respond /health 200
}
```

Note: `platform-api` and `mcp-server` are docker-compose service names that don't exist yet. Caddy will start but proxy requests will return 502 until those services are added in Plans B/C. This is expected.

- [ ] **Step 2: Add Caddy to `infra/docker-compose.yml`**

Add under `services:`:

```yaml
  caddy:
    image: caddy:2-alpine
    container_name: lpvibe-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "127.0.0.1:2019:2019"
    environment:
      PLATFORM_DOMAIN: ${PLATFORM_DOMAIN}
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
```

Add to `volumes:`:

```yaml
  caddy_data:
  caddy_config:
```

- [ ] **Step 3: Start Caddy**

```bash
docker compose up -d caddy
```

- [ ] **Step 4: Verify Caddy is running**

```bash
curl -sf http://localhost:2019/health
# Expected: HTTP 200
```

Note: TLS for `api.platform.company.dev` / `mcp.platform.company.dev` will auto-provision via Let's Encrypt when DNS is configured and port 443 is reachable from the internet. For local dev, Caddy serves over HTTP or with self-signed certs.

- [ ] **Step 5: Commit**

```bash
git add infra/caddy/ infra/docker-compose.yml
git commit -m "feat(infra): add Caddy reverse proxy for platform endpoints"
```

---

## Task 9: Full Stack Verification

**Files:**
- Modify: `infra/scripts/verify-infra.sh` (already created in Task 1, now services exist)

- [ ] **Step 1: Start all services together**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/infra
docker compose up -d
```

- [ ] **Step 2: Wait for healthy state**

```bash
docker compose ps
```

Expected: all 5 services (postgres, minio, redis, fluent-bit, caddy) show `Up` or `healthy`.

- [ ] **Step 3: Source .env and run full verification**

```bash
source .env
../infra/scripts/verify-infra.sh
```

Expected results:
```
=== LPVibe Infrastructure Health Check ===

✓ PostgreSQL is up
✓ platform_db exists
✓ platform_user can connect
✓ MinIO is up
✓ Redis is up
✓ Fluent Bit is up
✓ Caddy is up
✗ Coolify is up          ← fails if Coolify not yet installed (VPS-only)

=== Results: 7 passed, 1 failed ===
```

Note: Coolify check will pass only on the actual VPS after running `install-coolify.sh`. On local dev machine it's expected to fail. Update verify script to mark Coolify as optional:

- [ ] **Step 4: Make Coolify check optional in verify script**

Replace the Coolify check line in `infra/scripts/verify-infra.sh`:

```bash
# Coolify: web UI (optional — only on VPS)
if [ "${CHECK_COOLIFY:-false}" = "true" ]; then
    check "Coolify is up" curl -sf http://localhost:8080/api/health
fi
```

- [ ] **Step 5: Run verify again — expect all green**

```bash
./infra/scripts/verify-infra.sh
```

Expected: 7/7 passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add infra/scripts/verify-infra.sh infra/docker-compose.yml
git commit -m "feat(infra): full stack running — PG, MinIO, Redis, Fluent Bit, Caddy verified"
```

---

## Task 10: Final docker-compose.yml Review + Documentation

**Files:**
- Verify: `infra/docker-compose.yml` (final state)
- Create: `infra/README.md`

- [ ] **Step 1: Verify final `infra/docker-compose.yml` has all services**

The file should contain exactly these services: `postgres`, `minio`, `redis`, `fluent-bit`, `caddy`. And these volumes: `postgres_data`, `minio_data`, `redis_data`, `fluent_bit_db`, `caddy_data`, `caddy_config`.

Run:

```bash
docker compose config --services
```

Expected:
```
caddy
fluent-bit
minio
postgres
redis
```

- [ ] **Step 2: Create `infra/README.md`**

```markdown
# LPVibe Infrastructure

## Quick Start (local dev)

```bash
cp .env.example .env
# Edit .env with real passwords

docker compose up -d
./scripts/verify-infra.sh
```

## VPS Deployment

```bash
# 1. Bootstrap VPS
sudo ./scripts/setup-vps.sh

# 2. Install Coolify
sudo ./scripts/install-coolify.sh

# 3. Start platform infra
cp .env.example .env
# Edit .env with production values
docker compose up -d

# 4. Verify
CHECK_COOLIFY=true ./scripts/verify-infra.sh
```

## Services

| Service    | Port (host) | Purpose                                |
|------------|-------------|----------------------------------------|
| PostgreSQL | 5432        | platform_db + per-project databases    |
| MinIO      | 9000, 9001  | S3-compatible storage, console on 9001 |
| Redis      | 6379        | Locks, anti-loop counters, cache       |
| Fluent Bit | 2020        | Log collection → corporate OpenSearch  |
| Caddy      | 80, 443     | TLS reverse proxy for API + MCP        |

## Adding Platform API / MCP Server

Plans B and C add `platform-api` and `mcp-server` services to this docker-compose. Caddy is already configured to proxy to them.
```

- [ ] **Step 3: Commit**

```bash
git add infra/README.md
git commit -m "docs(infra): add README with quick start and VPS deployment guide"
```

---

## Plan A Complete — Deliverables Checklist

After completing all tasks, the following should be true:

- [ ] Git repo initialized with proper `.gitignore`
- [ ] `docker compose up -d` starts PG, MinIO, Redis, Fluent Bit, Caddy
- [ ] PostgreSQL has `platform_db` + `platform_user` auto-provisioned
- [ ] MinIO health endpoint returns 200
- [ ] Redis accepts authenticated connections
- [ ] Fluent Bit collects docker logs (OpenSearch delivery verified separately when creds available)
- [ ] Caddy proxies to `api.platform.company.dev` and `mcp.platform.company.dev` (502 until Plans B/C)
- [ ] `verify-infra.sh` passes 7/7 checks
- [ ] VPS provisioning scripts exist for one-shot setup
- [ ] Coolify installation scripted with post-install checklist

**Next:** Plan B (Platform API) — adds `platform-api` service to docker-compose, implements project CRUD, GitHub/Coolify/PG/MinIO integrations.
