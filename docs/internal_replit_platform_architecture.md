# Internal Replit‑Like AI Development Platform (Architecture Notes)

## Goal

Create an internal platform that allows employees to rapidly build MVPs
and small services with AI assistance (Claude Code) while automatically
handling infrastructure concerns such as:

-   Repository creation
-   Deployment
-   Databases
-   File storage
-   Logging
-   Testing
-   Environment setup

The system should mimic the convenience of Replit but run entirely on
company infrastructure.

------------------------------------------------------------------------

# Core Principles

1.  **AI edits templates instead of generating projects from scratch**
2.  **Infrastructure provisioning is automated**
3.  **Developers don't manage infra directly**
4.  **Logging, storage, and database are built-in**
5.  **Stack is intentionally limited for stability**

Recommended stack constraints:

-   Backend: FastAPI
-   Frontend: Next.js
-   Database: PostgreSQL
-   Storage: S3-compatible
-   Deployment: Docker
-   Logs: OpenSearch

------------------------------------------------------------------------

# High-Level Architecture

    Claude Code
        │
        ▼
    MCP Server
        │
        ▼
    Platform API
        │
        ├ Repo Manager
        ├ Template Engine
        ├ Database Manager
        ├ Storage Manager
        ├ Deploy Manager
        └ Runtime Manager
               │
               ▼
    Infrastructure
        ├ Coolify (deploy)
        ├ PostgreSQL
        ├ MinIO (S3 storage)
        ├ Redis
        ├ Fluent Bit
        └ OpenSearch

------------------------------------------------------------------------

# Infrastructure Components

## Deployment Platform

Coolify

Responsibilities:

-   Docker builds
-   Auto deploy from git
-   Environment variables
-   Application routing
-   Service lifecycle

------------------------------------------------------------------------

## Database

Single PostgreSQL cluster.

Each project gets its own database.

Example:

    postgres
     ├ project_1_db
     ├ project_2_db
     └ project_3_db

Database provisioning API should:

-   create database
-   create user
-   grant permissions

Example SQL:

    CREATE DATABASE project_db;
    CREATE USER project_user;
    GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;

Admin interface recommendation:

CloudBeaver

------------------------------------------------------------------------

## File Storage

Use MinIO (self-hosted S3-compatible storage).

Each project gets a bucket:

    minio
     ├ project-a-files
     ├ project-b-files
     └ project-c-files

Applications access storage using the S3 API.

------------------------------------------------------------------------

# Logging System

Applications should not manage logging configuration themselves.

All logs are automatically collected.

Architecture:

    Containers
       │
       ▼
    Fluent Bit
       │
       ▼
    OpenSearch

Containers simply log to stdout.

Example application logging:

``` python
print("processing file")
```

Fluent Bit collects container logs and sends them to OpenSearch.

Each log record should include metadata:

-   project_id
-   environment
-   timestamp

------------------------------------------------------------------------

# Sandbox Runtime

User-generated services must run in isolated containers.

Use Docker with resource limits.

Example:

    docker run   --memory=512m   --cpus=0.5   --pids-limit=100   --read-only   app_container

Isolation protects the host from:

-   runaway processes
-   memory exhaustion
-   malicious workloads

------------------------------------------------------------------------

# Universal MCP Tool

Instead of exposing many tools to the AI, expose one high-level tool:

    platform.run(task)

Example call:

    {
     "task": "create image upload service"
    }

Backend orchestrator handles:

-   selecting template
-   provisioning infrastructure
-   deploying project

Benefits:

-   simpler AI interaction
-   fewer hallucinated tool calls

------------------------------------------------------------------------

# Agent Development Loop

AI agents operate in an iterative loop.

    PLAN → ACT → OBSERVE → FIX

Example cycle:

1.  generate architecture
2.  write code
3.  run tests
4.  inspect logs
5.  fix errors
6.  repeat

------------------------------------------------------------------------

# Project Templates (Most Important Component)

Templates provide stable starting points for AI-generated projects.

Directory structure:

    templates/
      fastapi-api/
      nextjs-app/
      fullstack-app/
      telegram-bot/
      worker/
      image-service/

Each template must be a fully working project.

------------------------------------------------------------------------

# Template Structure Example

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

# Platform SDK (Inside Templates)

Infrastructure access should be abstracted.

Example modules:

    platform/
      logging.py
      database.py
      storage.py

------------------------------------------------------------------------

## Logging helper

``` python
from platform.logging import log
log.info("upload completed")
```

------------------------------------------------------------------------

## Storage helper

``` python
from platform.storage import storage
storage.upload(file)
```

------------------------------------------------------------------------

## Database helper

``` python
from platform.database import db
```

------------------------------------------------------------------------

# Health Endpoint

Every service must expose:

    GET /health

Example:

``` python
@app.get("/health")
def health():
    return {"status": "ok"}
```

This supports:

-   deploy checks
-   monitoring
-   debugging

------------------------------------------------------------------------

# Automated Testing

Templates include baseline tests.

Example:

    tests/
      test_health.py

Example test:

``` python
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
```

AI runs tests during the development loop.

------------------------------------------------------------------------

# File Upload Support

Storage is provided automatically.

Workflow:

1.  platform creates bucket
2.  environment variables injected
3.  template SDK handles upload

Example environment variables:

    S3_ENDPOINT
    S3_ACCESS_KEY
    S3_SECRET_KEY
    S3_BUCKET

------------------------------------------------------------------------

# Development Modes

Two possible execution modes.

## Local Mode

Developer runs services locally:

    Claude Code
       │
       ▼
    Local Docker
       │
       ▼
    localhost:3000

Best for development.

------------------------------------------------------------------------

## Cloud Mode

Projects deploy to shared infrastructure:

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

Used for sharing demos or testing integrations.

------------------------------------------------------------------------

# Preview Environments

Preview environments are optional.

They are useful when:

-   sharing MVPs
-   testing integrations
-   demonstrating results

Wildcard DNS example:

    *.apps.company.dev

------------------------------------------------------------------------

# Recommended Template Set

Minimal viable template library:

    fastapi-api
    nextjs-app
    fullstack-app
    telegram-bot
    worker
    image-service

------------------------------------------------------------------------

# Project Creation Flow

    User request
       │
       ▼
    Claude analyzes intent
       │
       ▼
    Select template
       │
       ▼
    Provision infrastructure
       │
       ├ database
       ├ storage
       └ repo
       │
       ▼
    Clone template
       │
       ▼
    AI modifies project
       │
       ▼
    Run tests
       │
       ▼
    Deploy

------------------------------------------------------------------------

# Key Insight

The stability of the system depends primarily on:

**Well-designed templates and infrastructure abstractions.**

AI should modify existing working projects rather than create new ones
from scratch.
