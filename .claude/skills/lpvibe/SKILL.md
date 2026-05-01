---
name: lpvibe
description: >-
  LPVibe Platform developer assistant. Activate when user works on an lpvibe project,
  mentions creating/deploying/debugging/testing a project, or asks about project status.
  Provides proactive IDE-like workflows: auto-screenshot after deploy, auto-check logs
  on errors, auto-run migrations after schema changes. Use this skill any time the
  lpvibe MCP tools are available in the session.
---

# LPVibe Platform — Developer Assistant

## What is LPVibe Platform

LPVibe is a cloud development platform in the style of Replit. Each project gets a full isolated environment provisioned in one call: **GitHub repository** (code, auto-deploy on push), **PostgreSQL database** (dedicated credentials), **MinIO bucket** (S3-compatible object storage), and a **Coolify app** (Docker-based deployment with HTTPS preview URL).

Developers write code locally, push to GitHub, and the platform automatically builds and deploys via Coolify. The MCP server is the primary interface for Claude to manage this entire lifecycle — creating projects, reading logs, running commands in containers, and visually verifying deployments through a headless browser.

All 11 MCP tools are prefixed with `lpvibe` in the server config. They communicate with the Platform API at `https://api.main.loyaltyapp-tools.com`, which orchestrates GitHub/Postgres/MinIO/Coolify as a unit.

---

## Proactive Rules — When to Act Without Being Asked

These rules are **mandatory**. Apply them automatically based on context.

| User signal | Immediate action |
|---|---|
| "создай проект" / "new project" / "init project" | Run **Workflow A** (Bootstrap) |
| "git push" just happened, code was committed | Run **Workflow B** (Deploy & Verify) after ~30s |
| "сломалось" / "не работает" / error in output | Run **Workflow C** (Diagnose) immediately |
| Schema/model changed + deployed | Run **Workflow D** (Migrations) |
| "запусти тесты" / "run tests" / CI failed | Run **Workflow E** (Testing) |
| "посмотри UI" / "как выглядит" / "check the page" | `browser_screenshot(preview_url, full_page=True)` |
| Session starts on an existing project | `get_deploy_status(project_id)` to confirm it's running |
| Any 500 error in app output | `get_logs(project_id, lines=200)` before proposing fixes |

**Rule: always know the project_id.** If it's unknown, call `list_projects()` to find it or ask the user once. Store it in CLAUDE.md under `LPVIBE_PROJECT_ID`.

---

## Workflow A — Bootstrap New Project

Use when: user asks to create a new project.

```
1. health_check()
   → If unhealthy: report which services are down, stop here.

2. create_project(name="<name>", template="<template>")
   → Provisions: GitHub repo + Postgres DB + MinIO bucket + Coolify app
   → Save returned project_id — you'll need it for every subsequent call
   → Templates: "fastapi-api" (default), "nextjs-app"

3. get_project(project_id)
   → Extract and display to user:
     - github_repo_url  → clone URL
     - preview_url      → HTTPS URL of the deployed app
     - postgres_db_name → already injected as DATABASE_URL env var in app
     - minio_bucket_name → already injected as S3_BUCKET env var in app

4. Output to user:
   - project_id (save to CLAUDE.md as LPVIBE_PROJECT_ID=<uuid>)
   - git clone <github_repo_url>
   - Preview URL: <preview_url> (will be live after first push + deploy)
   - Note: DATABASE_URL and S3_* vars are already set in the container
```

**Name rules:** 3-50 chars, lowercase letters/digits/hyphens, must start with a letter. Example: `my-api`, `user-service-v2`.

---

## Workflow B — Deploy & Visual Verify

Use when: user pushed code, or after any change that should affect the running app.

```
1. Wait ~30 seconds for Coolify to pick up the push.

2. get_deploy_status(project_id)
   → Check "status" field:
     - "running:healthy" or "running:unknown" → proceed
     - "stopped" or "exited" → call get_logs(project_id, lines=100), report error
     - Still building → wait another 30s, retry (max 3 attempts)

3. browser_screenshot(preview_url, full_page=True)
   → Show the screenshot to the user for visual confirmation.

4. browser_content(preview_url)
   → Scan HTML for: "500", "Internal Server Error", "Application Error",
     traceback keywords. If found → trigger Workflow C.

5. Report: "Deploy successful. App is live at <preview_url>."
   Attach the screenshot.
```

---

## Workflow C — Diagnose & Fix Error

Use when: user reports something is broken, or browser_content shows an error page.

```
1. get_logs(project_id, lines=200)
   → Look for: ERROR, CRITICAL, Traceback, Exception, ImportError,
     OperationalError, ConnectionRefused.

2. Identify the root cause from logs. Common patterns:
   - "relation does not exist" → migration not run → Workflow D
   - "connection refused" to DB/Redis → service down, check health_check()
   - "ModuleNotFoundError" → missing dependency in Dockerfile/pyproject.toml
   - "address already in use" → port conflict, restart needed

3. Propose and apply fix in the code.

4. After fix is committed and pushed → run Workflow B to verify.

5. If logs are empty or unclear:
   run_command(project_id, "python -c 'import app; print(\"ok\")'")
   → Quick import check. If this fails → look at the error output.
```

---

## Workflow D — Database Migrations

Use when: SQLAlchemy models or Alembic migrations were changed and deployed.

```
1. get_deploy_status(project_id)
   → Wait until "running:*" before running migrations.

2. run_command(project_id, "alembic upgrade head")
   → Wait for output. Timeout = 60s.

3. get_logs(project_id, lines=50)
   → Confirm: no "ERROR", migration steps printed correctly.

4. If migration failed with "target database is not up to date":
   run_command(project_id, "alembic stamp head")
   Then retry step 2.

5. Confirm to user: "Migration applied successfully."
```

---

## Workflow E — Run Tests

Use when: user asks to run tests, or CI is failing and you need to reproduce.

```
1. run_command(project_id, "pytest -v --tb=short 2>&1 | tail -80")
   → Timeout: 120s. Captures both stdout and stderr.

2. Parse output:
   - "passed" with no failures → report ✅
   - "FAILED" → show failing test names + error messages
   - "ERROR" during collection → get_logs(project_id, lines=50) for context

3. If test failure involves UI/HTTP:
   browser_screenshot(preview_url)
   browser_evaluate(preview_url, "document.title")
   → Helps diagnose frontend vs backend issues.

4. Fix failing tests or underlying code, push, re-run Workflow B, then E again.
```

---

## Tool Quick Reference

| Tool | Parameters | Returns | Use for |
|---|---|---|---|
| `health_check()` | — | `{status, services}` | Before any workflow |
| `list_projects()` | — | `{projects: [...]}` | Find project_id |
| `create_project(name, template)` | name: str, template: str | project metadata | New project |
| `get_project(project_id)` | project_id: uuid | full metadata | Get URLs/config |
| `delete_project(project_id)` | project_id: uuid | `{deleted: id}` | Cleanup |
| `get_logs(project_id, lines)` | project_id: uuid, lines: int=100 | `{logs: str}` | Debug errors |
| `get_deploy_status(project_id)` | project_id: uuid | `{status, preview_url}` | Check if running |
| `run_command(project_id, command)` | project_id: uuid, command: str | `{output: str}` | Migrations, tests, exec |
| `browser_screenshot(url, full_page)` | url: str, full_page: bool=False | PNG Image | Visual verify |
| `browser_content(url)` | url: str | `{html: str}` | Check rendered HTML |
| `browser_evaluate(url, expression)` | url: str, expression: str | `{data: any}` | JS assertions |

**run_command examples:**
```bash
# Migrations
"alembic upgrade head"
"python manage.py migrate"

# Tests
"pytest -v --tb=short 2>&1 | tail -80"
"npm test 2>&1 | tail -50"

# Environment check
"python -c 'import app; print(app.__version__)'"
"env | grep -E 'DATABASE|S3|PORT'"

# Seed data
"python scripts/seed.py"
```

**browser_evaluate examples:**
```javascript
// Page title
"document.title"

// All H1 text
"(() => Array.from(document.querySelectorAll('h1')).map(e => e.textContent))()"

// API health from browser
"fetch('/api/health').then(r => r.json()).then(d => JSON.stringify(d))"

// Check for JS errors (call after page load)
"window.__errors || 'no errors'"
```

---

## Storing project_id

Always persist `project_id` for the active project. On first use:

1. Write to the project's `CLAUDE.md`:
   ```
   ## LPVibe
   LPVIBE_PROJECT_ID=<uuid>
   LPVIBE_PREVIEW_URL=https://<name>.main.loyaltyapp-tools.com
   ```
2. At the start of each session, read `CLAUDE.md` to restore context.
3. If multiple projects: ask user which one, then lock to that `project_id` for the session.

---

## MCP Connection Config

Add to `~/.claude.json` (or run the CLI command):

```json
{
  "mcpServers": {
    "lpvibe": {
      "type": "http",
      "url": "https://mcp.main.loyaltyapp-tools.com/mcp",
      "headers": {
        "Authorization": "Bearer KF2dZUmJNtSiIECIc3O1wXQh0_ZeDJXQdHWpMsx8qzko41wLSaudCc0oTbC-tZkV"
      }
    }
  }
}
```

Or via CLI:
```bash
claude mcp add --transport http lpvibe https://mcp.main.loyaltyapp-tools.com/mcp \
  -H "Authorization: Bearer KF2dZUmJNtSiIECIc3O1wXQh0_ZeDJXQdHWpMsx8qzko41wLSaudCc0oTbC-tZkV"
```

**Install this skill globally:**
```bash
cp -r .claude/skills/lpvibe ~/.claude/skills/lpvibe
```

---

## Error Handling

| Symptom | First step | Recovery |
|---|---|---|
| `create_project` failed mid-way | `list_projects()` | If partially created, `delete_project` then retry |
| `get_logs` returns empty string | Deploy still in progress | Wait 15s, retry. Max 3 attempts. |
| `run_command` times out (>120s) | `get_logs` for context | Command hung — check for input prompts or infinite loops |
| `browser_screenshot` SSL error | `get_deploy_status` | App may be down or domain not propagated yet |
| `get_deploy_status` returns "stopped" | `get_logs(lines=200)` | Crash on startup — fix code, push, wait for redeploy |
| "Project not found" on any call | `list_projects()` | Wrong project_id — find correct one |
| `health_check` shows postgres=down | Stop all workflows | Infrastructure issue — not fixable from MCP |
