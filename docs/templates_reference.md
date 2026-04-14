# templates_reference.md

## Reference Templates (Production-Ready)

These templates are strict, minimal, and stable. They must be used as
the ONLY base for generated projects.

All templates follow: - deterministic structure - Docker-first
execution - built-in logging via stdout - health endpoint - tests
included

------------------------------------------------------------------------

# 1. FASTAPI API TEMPLATE

## Structure

fastapi-api/ Dockerfile requirements.txt app/ main.py tests/
test_health.py

------------------------------------------------------------------------

## requirements.txt

fastapi uvicorn pytest httpx

------------------------------------------------------------------------

## Dockerfile

FROM python:3.11-slim

WORKDIR /app COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD \["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"\]

------------------------------------------------------------------------

## app/main.py

from fastapi import FastAPI

app = FastAPI()

@app.get("/health") def health(): return {"status": "ok"}

@app.get("/") def root(): return {"message": "API is running"}

------------------------------------------------------------------------

## tests/test_health.py

from fastapi.testclient import TestClient from app.main import app

client = TestClient(app)

def test_health(): r = client.get("/health") assert r.status_code == 200

------------------------------------------------------------------------

# 2. NEXT.JS TEMPLATE

## Structure

nextjs-app/ Dockerfile package.json pages/ index.js

------------------------------------------------------------------------

## package.json

{ "name": "app", "scripts": { "dev": "next dev", "build": "next build",
"start": "next start" }, "dependencies": { "next": "14", "react": "18",
"react-dom": "18" } }

------------------------------------------------------------------------

## Dockerfile

FROM node:18

WORKDIR /app COPY . .

RUN npm install RUN npm run build

CMD \["npm", "start"\]

------------------------------------------------------------------------

## pages/index.js

export default function Home() { return

<div>

App is running

</div>

; }

------------------------------------------------------------------------

# 3. WORKER TEMPLATE (PYTHON)

## Structure

worker/ Dockerfile requirements.txt worker.py

------------------------------------------------------------------------

## worker.py

import time

while True: print("worker running") time.sleep(5)

------------------------------------------------------------------------

# 4. RULES (CRITICAL)

These MUST NOT be violated:

1.  No extra frameworks
2.  No dynamic structure generation
3.  Only modify existing files
4.  Always keep Docker working
5.  Health endpoint must exist
6.  Tests must pass

------------------------------------------------------------------------

# 5. AI USAGE RULES

Claude MUST:

-   start from template
-   never rewrite project from scratch
-   only extend functionality
-   always run tests after changes

------------------------------------------------------------------------

# END
