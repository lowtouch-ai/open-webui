# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Open WebUI is a self-hosted AI platform (v0.8.5) supporting Ollama and OpenAI-compatible APIs with RAG, web search, and tool-use capabilities. It is a full-stack app: **SvelteKit frontend** + **FastAPI backend**.

## Commands

### Frontend

```bash
npm run dev          # Dev server with hot reload
npm run build        # Production build
npm run check        # SvelteKit sync + TypeScript type check
npm run lint         # ESLint + Svelte type check + Pylint (all linters)
npm run lint:frontend  # ESLint with auto-fix
npm run lint:types   # svelte-check (TypeScript types)
npm run format       # Prettier (JS/TS/Svelte/CSS/MD/JSON)
npm run format:backend  # Black (Python)
```

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn open_webui.main:app --reload --port 8080
```

### Tests

```bash
# Backend (pytest, requires Docker for PostgreSQL)
pytest backend/open_webui/test/
pytest backend/open_webui/test/apps/webui/routers/test_auths.py  # single file
pytest -k "test_get_session_user"  # pattern match

# Frontend E2E
npm run cy:open      # Cypress interactive runner
```

### Docker (full stack)

```bash
docker compose -f docker-compose.dev.yaml up --build   # backend + frontend + ollama
make install        # docker compose up -d
make startAndBuild  # docker compose up -d --build
```

## Architecture

### Frontend (`src/`)

- **Framework**: SvelteKit 2 + Svelte 5, TypeScript, Vite, Tailwind CSS 4
- **`src/lib/apis/`** — typed API client functions (one file per backend router)
- **`src/lib/components/`** — Svelte components organized by feature
- **`src/lib/stores/`** — Svelte stores for global state (auth, settings, chat, etc.)
- **`src/routes/`** — file-based routing (SvelteKit pages and layouts)
- Real-time updates via Socket.io client; rich text via TipTap; code editing via CodeMirror 6

### Backend (`backend/open_webui/`)

- **Framework**: FastAPI + Uvicorn, async throughout
- **`main.py`** — app initialization, CORS, Socket.io mount, all router includes
- **`routers/`** — one file per feature area (30+ routers), all under `/api/v1/`
- **`models/`** — SQLAlchemy ORM models + Pydantic schemas (one file per entity)
- **`utils/`** — shared utilities: auth, chat, embeddings, middleware, plugin pipeline
- **`socket/`** — Socket.io event handling and WebSocket connection management
- **`retrieval/`** — RAG subsystem:
  - `vector/dbs/` — 9 vector DB adapters (ChromaDB, PGVector, Qdrant, Milvus, etc.)
  - `web/` — 15+ web search providers (SearXNG, Brave, Kagi, DuckDuckGo, etc.)
  - `loaders/` — document loaders (PDF, web, YouTube, Docling, Tika, etc.)
- **`internal/`** — Peewee-based legacy migrations; `db.py` manages DB connections
- **`migrations/versions/`** — Alembic migration scripts (primary schema management)

### Database

- Dev: SQLite; Production: PostgreSQL
- ORM: SQLAlchemy 2.0 with Alembic for migrations
- Add migrations: `alembic revision --autogenerate -m "description"` in `backend/`

### Configuration

- **`env.py`** — parses all environment variables with defaults
- **`config.py`** — large (~135KB) central config object built from env vars
- **`.env.example`** — template; copy to `.env` for local dev

### Testing Patterns

Backend tests use `AbstractPostgresTest` (spins up PostgreSQL via Docker) and `mock_webui_user()` to simulate authenticated requests:

```python
class TestAuths(AbstractPostgresTest):
    def test_get_session_user(self):
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
```

### Key Conventions

- **New API endpoint**: add router in `routers/`, ORM model in `models/`, API client in `src/lib/apis/`
- **New DB table**: create Alembic migration in `migrations/versions/`
- **New vector DB**: implement adapter in `retrieval/vector/dbs/`, register in `retrieval/vector/factory.py`
- **New web search provider**: add in `retrieval/web/`, implement the standard search interface
- **Auth**: JWT-based; `get_verified_user` / `get_admin_user` FastAPI dependencies for route protection
- **Formatting**: tabs + single quotes + no trailing commas + 100-char line width (Prettier); Black defaults for Python

---

## Custom Features (lowtouch-ai)

These features are maintained in this fork and must be re-applied whenever syncing from upstream.

### 1. X-LTAI Header Forwarding

All request headers starting with `x-ltai-` are extracted from the incoming chat request and forwarded to every upstream LLM provider (Ollama and OpenAI-compatible).

**Files changed:**

| File | What was changed |
|------|-----------------|
| `backend/open_webui/main.py` | In `chat_completion()`: extract `vault_user_id`, `vault_keys`, and `ltai_headers` (all `x-ltai-*`) from request headers; add all three to the `metadata` dict |
| `backend/open_webui/routers/ollama.py` | `send_post_request()`: replaced `vault_keys` param with `extra_headers: Optional[dict]`; calls `headers.update(extra_headers)`. In `generate_chat_completion()`: collects all `x-ltai-*` headers, normalises `x-ltai-vault-keys` via `sanitize_vault_keys_header()`, and passes them as `extra_headers` |
| `backend/open_webui/routers/openai.py` | `get_headers_and_cookies()`: loop at the end copies every `x-ltai-*` header from the incoming request into the outbound headers dict, normalising `x-ltai-vault-keys` via `sanitize_vault_keys_header()` |
| `backend/open_webui/utils/vault.py` | Added `sanitize_vault_keys_header(vault_keys_str, model)` — normalises vault key agent-name portion to match agent backend format |

**Key headers used at runtime:**
- `x-ltai-vault-user` — Vault user ID for secret lookup
- `x-ltai-vault-keys` — comma-separated list of Vault keys to inject (e.g. `COMMON/api_key`)
- Any other `x-ltai-*` header is passed through transparently

**Vault key format for `x-ltai-vault-keys`:**

The agent backend resolves keys using this agent-name derivation:
```python
agent_name = re.sub(r'[^a-zA-Z0-9]', '_', re.match(r'([^:]+)', model).group(1))
```
So for model `appz/tracker` the expected format is `appz_tracker/KEY_NAME`.

OpenWebUI normalises the header before forwarding via `sanitize_vault_keys_header()` in `vault.py`:
- `^KEY_NAME` — COMMON scope, passed through unchanged
- `appz/tracker_KEY_NAME` — raw model prefix + `_` separator → `appz_tracker/KEY_NAME`
- `appz/tracker/KEY_NAME` — slash-separated but unsanitized → `appz_tracker/KEY_NAME`
- `appz_tracker/KEY_NAME` — already correct, passes through unchanged

### 2. ENABLE_TOOLS_FUNCTION_CALLING — Disable Tool Selection Preflight

OpenWebUI 0.6+ sends a non-streaming tool selection preflight to every model before each real chat, even when no tools are configured. The system message is `"Available Tools: [] — Your task is to choose and return the correct tool(s)..."`. This causes DAG-triggering agents (e.g. ClipFoundry) to fire their pipeline on the preflight instead of only on real user messages.

Added `ENABLE_TOOLS_FUNCTION_CALLING` to gate this behaviour. **Default is `False`** (preflight disabled). Set to `True` only if OpenWebUI-registered Python tools are actively used.

**Files changed:**

| File | What was changed |
|------|-----------------|
| `backend/open_webui/config.py` | Added `ENABLE_TOOLS_FUNCTION_CALLING` `PersistentConfig` — reads from env, defaults to `False` |
| `backend/open_webui/main.py` | Imported `ENABLE_TOOLS_FUNCTION_CALLING`; assigned to `app.state.config` |
| `backend/open_webui/routers/tasks.py` | Added to GET config response, `TaskConfigForm`, POST update handler, and POST response |
| `backend/open_webui/utils/middleware.py` | Changed `else:` → `elif request.app.state.config.ENABLE_TOOLS_FUNCTION_CALLING:` in the tools handler block |

**Root cause in `middleware.py`:** The `else` branch of `if tools_dict:` (line ~2534) fires when `tools_dict` is empty — meaning `chat_completion_tools_handler` was always called regardless of whether any tools were configured.

**Env var:**
```
ENABLE_TOOLS_FUNCTION_CALLING=false   # default — disables preflight
ENABLE_TOOLS_FUNCTION_CALLING=true    # re-enable if OpenWebUI tools are needed
```

### 3. HashiCorp Vault Integration

Agent connection secrets are stored in and retrieved from HashiCorp Vault (KV v1) instead of the local database.

**Files:**

| File | Purpose |
|------|---------|
| `backend/open_webui/utils/vault.py` | `VaultClient` class; `store/get/delete_agent_connection_from_vault()`; `sanitize_vault_keys_header()` — normalises `x-ltai-vault-keys` header to `sanitized_model/KEY_NAME` format |
| `backend/open_webui/routers/agent_connections.py` | REST API for CRUD on Vault-backed agent connection keys; mounted at `/api/v1/agent_connections` |
| `backend/open_webui/config.py` | `ENABLE_VAULT_INTEGRATION`, `VAULT_URL`, `VAULT_TOKEN`, `VAULT_MOUNT_PATH`, `VAULT_VERSION`, `VAULT_TIMEOUT`, `VAULT_VERIFY_SSL` |

**Vault secret layout:** `users/<user_id>/<agent_name>` → `{ <key_name>: <value> }`
`COMMON` scope: `users/<user_id>/COMMON`

**Required env vars when vault is enabled:**
```
ENABLE_VAULT_INTEGRATION=true
VAULT_URL=http://vault:8200
VAULT_TOKEN=<token>
VAULT_MOUNT_PATH=secret   # KV v1 mount
```

### Testing Custom Features (no Docker required)

```bash
# Tier 1 – pure Python, zero deps
cd backend
python3 open_webui/test/test_ltai_headers.py

# Tier 2 – full import tests (needs deps)
pip install ".[dev]"
pytest open_webui/test/test_ltai_headers.py -v
```

Test file: `backend/open_webui/test/test_ltai_headers.py`

Covers: metadata extraction in `main.py`, `extra_headers` forwarding in `ollama.py`, and `x-ltai-*` injection in `openai.py`.
