# platform_spec.md

## Internal Replit‑Like Platform --- Technical Specification

This document defines the **strict API and MCP specification** for the
internal AI development platform.

It is intended to be used directly by **Claude Code or other AI coding
agents** to implement the system.

------------------------------------------------------------------------

# 1. System Overview

The platform provides automated infrastructure provisioning and project
generation.

Core responsibilities:

-   project scaffolding
-   database provisioning
-   storage provisioning
-   deployment
-   logging integration
-   runtime execution
-   test execution

The system is controlled via a **single MCP tool** and a **Platform
API**.

------------------------------------------------------------------------

# 2. Core Architecture

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

# 3. Platform API

Base URL:

    /api/v1

All responses:

    {
      "success": true,
      "data": {}
    }

Error format:

    {
      "success": false,
      "error": "error_message"
    }

------------------------------------------------------------------------

# 4. Project Model

Project object:

    {
      "id": "uuid",
      "name": "string",
      "template": "string",
      "repo_url": "string",
      "database_url": "string",
      "storage_bucket": "string",
      "status": "creating | ready | failed"
    }

------------------------------------------------------------------------

# 5. Project Endpoints

## Create Project

POST

    /projects

Request:

    {
      "name": "image-service",
      "template": "fastapi-api"
    }

Behavior:

1.  create repo
2.  clone template
3.  create database
4.  create storage bucket
5.  return project metadata

------------------------------------------------------------------------

## Get Project

GET

    /projects/{project_id}

Returns project metadata.

------------------------------------------------------------------------

## List Projects

GET

    /projects

Returns list of projects.

------------------------------------------------------------------------

## Delete Project

DELETE

    /projects/{project_id}

Removes:

-   repo
-   database
-   storage bucket
-   deployment

------------------------------------------------------------------------

# 6. Database API

Endpoint:

    POST /database/create

Request:

    {
      "project_id": "uuid"
    }

Behavior:

-   create postgres database
-   create database user
-   grant privileges

Response:

    {
      "database_url": "postgres://user:pass@host/db"
    }

------------------------------------------------------------------------

# 7. Storage API

Endpoint:

    POST /storage/create

Request:

    {
      "project_id": "uuid"
    }

Behavior:

-   create MinIO bucket

Response:

    {
      "bucket": "project-uuid-files"
    }

------------------------------------------------------------------------

# 8. Deployment API

## Deploy Project

POST

    /deploy

Request:

    {
      "project_id": "uuid"
    }

Behavior:

-   trigger Coolify deployment
-   return deployment URL

Response:

    {
      "url": "https://project.apps.company.dev"
    }

------------------------------------------------------------------------

## Get Deployment Logs

GET

    /deploy/logs/{project_id}

Returns deployment logs.

------------------------------------------------------------------------

# 9. Runtime Execution API

Run commands inside sandbox container.

Endpoint:

    POST /runtime/run

Request:

    {
      "project_id": "uuid",
      "command": "pytest"
    }

Response:

    {
      "stdout": "...",
      "stderr": "...",
      "exit_code": 0
    }

Containers must enforce limits:

    memory: 512mb
    cpu: 0.5
    pids: 100
    filesystem: read-only

------------------------------------------------------------------------

# 10. Template Engine

Templates stored in:

    templates/

Template structure:

    template-name/
      Dockerfile
      template.yaml
      app/
      platform/
      tests/

------------------------------------------------------------------------

## template.yaml example

    name: fastapi-api

    stack:
      backend: fastapi
      database: postgres
      storage: s3

    features:
      - logging
      - tests
      - docker

------------------------------------------------------------------------

# 11. Platform SDK

Templates must include:

    platform/
      logging.py
      storage.py
      database.py

Purpose: hide infrastructure complexity from generated code.

------------------------------------------------------------------------

# 12. Logging

Applications log to stdout.

Example:

    print("processing file")

Log pipeline:

    Docker container
         │
         ▼
    Fluent Bit
         │
         ▼
    OpenSearch

Logs must include:

-   project_id
-   service
-   timestamp

------------------------------------------------------------------------

# 13. MCP Tool Specification

Expose a **single MCP tool**.

Tool name:

    platform.run

Input schema:

    {
      "task": "string"
    }

Examples:

    { "task": "create image upload service" }
    { "task": "run tests" }
    { "task": "deploy project" }
    { "task": "debug failing tests" }

MCP server interprets task and calls Platform API.

------------------------------------------------------------------------

# 14. AI Development Loop

Claude agents must follow loop:

    PLAN
    ACT
    OBSERVE
    FIX
    REPEAT

Example:

1 generate project plan 2 create project 3 modify code 4 run tests 5
inspect logs 6 fix issues

Repeat until success.

------------------------------------------------------------------------

# 15. Health Endpoint Requirement

Every service must implement:

    GET /health

Example:

    @app.get("/health")
    def health():
        return {"status": "ok"}

Used for:

-   deployment checks
-   monitoring
-   debugging

------------------------------------------------------------------------

# 16. Environment Variables

Injected automatically:

    DATABASE_URL
    S3_ENDPOINT
    S3_ACCESS_KEY
    S3_SECRET_KEY
    S3_BUCKET

Applications should access via environment.

------------------------------------------------------------------------

# 17. MVP Requirements

The system is considered operational when:

-   AI can create projects
-   infrastructure auto‑provisions
-   services run locally
-   deployment works
-   logs appear in OpenSearch
-   database works
-   file uploads work

------------------------------------------------------------------------

# 18. Future Extensions

Possible improvements:

-   preview environments per branch
-   browser testing via Playwright
-   cost controls
-   resource quotas
-   dashboard UI
-   multi‑language templates

------------------------------------------------------------------------

# End of Specification
