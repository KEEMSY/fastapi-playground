# Monorepo App Separation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Organize the existing FastAPI and Svelte applications as separate, independently containerized apps in one monorepo while preserving their local API integration.

**Architecture:** Move the current backend into `apps/api` and the Svelte app into `apps/web`. Give each app its own Dockerfile and keep a root Compose file to run both apps with the existing MySQL and Redis services. The browser will call the API through the host-published URL, while FastAPI CORS allows the web origin; Compose service DNS will be used only for container-to-container traffic.

**Tech Stack:** FastAPI, Uvicorn, SQLAlchemy, Alembic, Svelte, Vite, Docker Compose, MySQL, Redis.

---

### Task 1: Relocate the existing applications

Move backend-owned files (`src`, `tests`, `alembic`, `scripts`, `Dockerfile`, `requirements.txt`, `alembic.ini`, `config.py`, `logging.ini`, `test.sh`, and `HTTP Request.jmx`) to `apps/api/`. Move `frontend/` to `apps/web/`. Keep root `.env`, `.gitignore`, `study/`, and git metadata in place. Do not change Python package imports; run the API from `apps/api` so its existing `src.*` and `config` imports resolve.

### Task 2: Make the apps independently buildable

Update the API Dockerfile for its app-local build context and add a web Dockerfile that installs from the lockfile and starts Vite on `0.0.0.0:5173`. Keep each app's code and dependencies in its own build context.

### Task 3: Orchestrate the local stack from the repository root

Add root `docker-compose.yml` with separate `api` and `web` services plus the current MySQL and Redis services. Preserve published ports (`7777`, `5173`, `13306`, `16379`) and the MySQL named volume. Pass the API configuration from root `.env`. Set the Vite API base URL to the host-visible API address; do not use `http://api:8000` in browser code because the browser is outside the Compose network.

### Task 4: Preserve API/web integration

Keep the API routes and frontend API client behavior unchanged. Configure FastAPI CORS for the local web origin and retain the API host port expected by the current Vite app. Add Compose health/dependency behavior only if needed for startup correctness; service ordering alone must not be treated as readiness.

### Task 5: Document the monorepo

Replace the root README's single-app tree and commands with the new `apps/api`, `apps/web`, `packages` (reserved for future genuinely shared code), and `study` responsibilities. Document root Compose startup, app-specific commands, and the browser-to-API URL relationship. Do not put code under `study/`.

### Task 6: Check the migration

Inspect the final tree and diff for path references, validate Compose configuration if Docker Compose is available, and check that the existing Python and frontend build/test commands can be run from their new app directories. Leave the existing untracked `study/` files untouched.
