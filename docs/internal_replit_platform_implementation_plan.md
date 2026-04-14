# Implementation Plan: Internal Replit‑Like AI Development Platform

This document describes a **practical step‑by‑step implementation plan**
for building the internal AI development platform described in the
architecture document.

Goal: build an MVP that allows employees to generate and run small
services with **Claude Code + MCP + automated infrastructure**.

Estimated time for MVP: **\~5--7 days**.

------------------------------------------------------------------------

# Overview

Final system architecture:

    Claude Code
        │
        ▼
    MCP Server
        │
        ▼
    Platform API
        │
        ├ Template Engine
        ├ Repo Manager
        ├ Database Manager
        ├ Storage Manager
        ├ Deploy Manager
        └ Runtime Manager
               │
               ▼
    Infrastructure
        ├ Coolify
        ├ PostgreSQL
        ├ MinIO
        ├ Redis
        ├ Fluent Bit
        └ OpenSearch

------------------------------------------------------------------------

# Phase 1 --- Infrastructure Setup (Day 1)

## 1. Deploy Core Infrastructure

Install on company VPS cluster.

Recommended services:

-   Coolify
-   PostgreSQL
-   MinIO
-   Redis
-   Fluent Bit
-   OpenSearch (already exists in company)

Example layout:

    infra-server
     ├ coolify
     ├ postgres
     ├ minio
     ├ redis
     └ fluentbit

------------------------------------------------------------------------

## 2. Configure MinIO

Create S3-compatible storage.

Create admin bucket:

    projects

Later each project receives its own bucket:

    project-{id}-files

------------------------------------------------------------------------

## 3. Configure PostgreSQL

Single cluster.

Example structure:

    postgres
     ├ platform_db
     ├ project_1_db
     ├ project_2_db

Platform DB stores metadata:

-   projects
-   users
-   deployments
-   resources

------------------------------------------------------------------------

## 4. Logging Pipeline

Install Fluent Bit.

Pipeline:

    Docker Containers
          │
          ▼
    Fluent Bit
          │
          ▼
    OpenSearch

Logs should include metadata:

-   project_id
-   service_name
-   environment

------------------------------------------------------------------------

# Phase 2 --- Platform API (Day 2--3)

Build a **Platform API service**.

Recommended stack:

    FastAPI
    Python

Directory structure:

    platform-api/
      app/
        main.py
        services/
          repo.py
          database.py
          storage.py
          deploy.py
          templates.py

------------------------------------------------------------------------

## Platform API Responsibilities

### Repo Manager

Creates Git repositories.

Possible integrations:

-   GitHub
-   GitLab

Functions:

    create_repo(project_name)
    delete_repo(project_id)

------------------------------------------------------------------------

### Database Manager

Creates Postgres databases.

Example logic:

    create_database(project_id)
    drop_database(project_id)

Example SQL:

    CREATE DATABASE project_db;
    CREATE USER project_user;
    GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;

------------------------------------------------------------------------

### Storage Manager

Creates storage buckets.

    create_bucket(project_id)
    delete_bucket(project_id)

MinIO API is S3-compatible.

------------------------------------------------------------------------

### Deploy Manager

Triggers deployment through Coolify.

Actions:

    deploy_project(project_id)
    redeploy_project(project_id)
    get_logs(project_id)

------------------------------------------------------------------------

### Template Engine

Clones template repository and prepares project.

    create_from_template(template_name)

------------------------------------------------------------------------

# Phase 3 --- Template System (Day 3--4)

Create template repository.

Structure:

    templates/
      fastapi-api/
      nextjs-app/
      fullstack-app/
      telegram-bot/
      worker/
      image-service/

Each template must:

-   run locally
-   run in Docker
-   include tests
-   include health endpoint

------------------------------------------------------------------------

## Template Example

    fastapi-api/

    Dockerfile
    requirements.txt

    app/
      main.py
      routes.py
      models.py

    platform/
      logging.py
      storage.py
      database.py

    tests/
      test_health.py

    template.yaml

------------------------------------------------------------------------

## Platform SDK

Templates include helper modules.

    platform/
      logging.py
      storage.py
      database.py

Purpose:

Hide infrastructure complexity from AI-generated code.

Example:

``` python
from platform.storage import storage
storage.upload(file)
```

------------------------------------------------------------------------

# Phase 4 --- MCP Server (Day 4)

Create MCP server for Claude Code.

Expose a **single universal tool**:

    platform.run(task)

Example call:

    {
      "task": "create image upload service"
    }

MCP server forwards requests to Platform API.

------------------------------------------------------------------------

# Phase 5 --- Agent Workflow (Day 5)

Implement AI workflow loop.

    PLAN → ACT → OBSERVE → FIX

Example execution:

1.  Claude generates architecture
2.  template selected
3.  infrastructure created
4.  code written
5.  tests executed
6.  errors fixed

Repeat until success.

------------------------------------------------------------------------

# Phase 6 --- Local Development Mode (Optional)

Developers may run services locally.

Flow:

    Claude Code
        │
        ▼
    Local Docker
        │
        ▼
    localhost

Useful for debugging and development.

------------------------------------------------------------------------

# Phase 7 --- Deployment Mode

Production mode uses Coolify.

Flow:

    Claude Code
        │
        ▼
    Platform API
        │
        ▼
    Coolify
        │
        ▼
    app.company.dev

------------------------------------------------------------------------

# Phase 8 --- Automated Testing

Templates include baseline tests.

AI should run tests automatically.

Example:

    pytest
    npm test

Failing tests trigger AI fixes.

------------------------------------------------------------------------

# Phase 9 --- Logging Integration

All services log to stdout.

Docker logs collected by Fluent Bit.

Example application logging:

    print("processing image")

No configuration required from developers.

------------------------------------------------------------------------

# Phase 10 --- Security

All generated services run inside Docker containers.

Apply limits:

    --memory=512m
    --cpus=0.5
    --pids-limit=100
    --read-only

Prevents resource abuse.

------------------------------------------------------------------------

# Phase 11 --- MVP Success Criteria

MVP is complete when:

-   Claude can create a project
-   infrastructure auto-provisions
-   service runs locally
-   tests execute automatically
-   logs appear in OpenSearch
-   files upload via S3
-   database works

------------------------------------------------------------------------

# Future Improvements

Possible upgrades later:

-   ephemeral preview environments
-   AI browser testing (Playwright)
-   cost controls
-   resource quotas
-   project dashboard UI
-   template marketplace

------------------------------------------------------------------------

# Summary

Minimal platform components:

    Claude Code
    MCP Server
    Platform API
    Coolify
    PostgreSQL
    MinIO
    Redis
    Fluent Bit
    OpenSearch

With well-designed templates and automation this provides a
**Replit‑like internal developer experience**.
