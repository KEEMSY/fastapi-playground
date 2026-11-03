# FastAPI Playground Monorepo

This repository contains independently buildable apps and learning notes.

```text
apps/
  api/                 # FastAPI backend, tests, migrations, and scripts
  web/                 # Svelte + Vite frontend
study/                 # Learning plans and notes only
packages/              # Reserved for code genuinely shared by multiple apps
docker-compose.yml     # Local stack for web, API, MySQL, and Redis
```

## Run the local stack

The root `.env` supplies the API's environment variables. Start all containers from the repository root:

```sh
docker compose up --build
```

- Web: <http://localhost:5173>
- API docs: <http://localhost:7777/docs>
- MySQL: `localhost:13306`
- Redis: `localhost:16379`

The browser calls the API using `VITE_SERVER_URL`, which defaults to `http://localhost:7777`. It must be a host-visible URL: a browser cannot resolve the Compose-only hostname `api`. FastAPI currently allows the Vite origin `http://localhost:5173` through CORS.

Each app has its own Docker build context and can be built separately:

```sh
docker build -t fastapi-playground-api ./apps/api
docker build -t fastapi-playground-web ./apps/web
```

To work on one app without containers:

```sh
cd apps/api
pip install -r requirements.txt
uvicorn src.main:app --reload
```

```sh
cd apps/web
npm ci
npm run dev
```

The API test suite is under `apps/api/tests`; run it from `apps/api` with `pytest`. Run the web app's Vite commands from `apps/web`.

## Study project

`study/` contains learning plans, explanations, and experiment notes. Executable exercises belong in app directories, not in `study/`. New apps can be added under `apps/`; add a shared package under `packages/` only when multiple apps need the same code and its ownership is clear.
