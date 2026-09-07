# ADR-0002: 2.x Platform Hardening & Tool Extension Roadmap

[繁體中文](0002-platform-hardening-and-tool-extension-roadmap.md) | [English](0002-platform-hardening-and-tool-extension-roadmap_en.md)

## Status

Proposed - 2026-09-07

---

## Context & Problem Statement

The 2.0.0 "lightweight" refactor made AskMiao bootable without Docker, PostgreSQL, or Redis. Subsequent 2.x iterations added custom API tools (OpenAPI import), MCP server integration, and SSRF egress protection. Alongside these features the following technical debt and architectural risks accumulated:

1. **Token blacklist lives in a single process**: `TokenBlacklist` in `core/redis_client.py` is a class-level dict; revocation is lost across workers or restarts, and it stores whole tokens instead of JTIs.
2. **No database migrations**: tables are created via `Base.metadata.create_all`; `custom_api_tools` and `mcp_servers` are still evolving and every column change needs manual SQL.
3. **No CI**: the repository has no `.github/`; lint, type checks, pytest, vitest, and CodeQL are run manually, and CodeQL findings have historically been fixed after the fact.
4. **Test gaps**: backend tests cover agentic research, API tools, MCP, the OpenAPI parser, modular RAG, and SSRF, but not auth, documents, or chat endpoints; the frontend has vitest configured with zero test files.
5. **Half-finished JSX → TSX migration**: `pages/Chat.jsx` is dead code, `utils/logger.js` duplicates `utils/secureLogger.ts`, several pages remain untyped JSX, and `backend/app/models/payloads.py` still carries removed workflow types.
6. **Coupled tool sources**: `ResearchToolRegistry.get_tool_definitions()` and `execute_tool()` merge built-in tools, the `custom_api_tools` table, and MCP `discovered_tools` through conditional branches; every new source means editing the same class.
7. **Configuration drift**: `config.py`, `.env.example`, and the README disagree on defaults such as `DATABASE_URL`, `LLM_API_BASE`, and `CHUNK_SIZE`.
8. **No observability**: plain-text logs, no request id, no metrics endpoint, and research traces are only stored inside `messages.context_used` where they cannot be queried.

This ADR fixes the decisions and priorities for the next phase. Each item may later become its own ADR or simply cite this document.

---

## Decision Outcome

Ordered by risk and cost: P0 (now), P1 (next iteration), P2 (when capacity allows).

### P0-1: Establish a CI pipeline

- Add `.github/workflows/ci.yml` triggered on push and pull request:
  - **backend**: `pip install -r requirements.txt`, `pytest -q`, with `FORCE_CPU=true`, `DATABASE_URL=sqlite:///./test.db`, `RATE_LIMIT_ENABLED=false`; cache `data/hf_home` via actions cache or mock the embedding model in tests to avoid downloads.
  - **frontend**: `bun install`, `bun run lint`, `bunx tsc --noEmit`, `bun run test`, `bun run build`.
  - **CodeQL**: Python and JavaScript/TypeScript scans.
- Make a green CI a merge requirement.

### P0-2: Pluggable token blacklist keyed by JTI

- Define a `BlacklistBackend` Protocol in `core/`: `add(jti, expires_in)`, `is_blacklisted(jti)`, `remove(jti)`.
- Implement `MemoryBlacklist` (default, preserving current behaviour) and `RedisBlacklist` (enabled when `REDIS_URL` is set; `redis` becomes an optional extra).
- Switch `jwt_auth.py` to use the payload `jti`; `revoke_token()` decodes the token and stores only the JTI with the remaining TTL.
- Log an explicit warning at startup when `ENVIRONMENT=production`, more than one worker is configured, and `REDIS_URL` is unset.

### P0-3: Fill core test gaps

- Backend: add `tests/test_auth.py` (register / login / refresh / blacklist effective after logout / validate-token), `tests/test_documents.py` (upload success and failure, delete, rebuild-index, with RAG mocked via fixtures), `tests/test_chat_send.py` (SSE event sequence with the LLM client mocked).
- Frontend: establish a vitest + Testing Library baseline for the main `components/ui` components (Button, Dialog, Tabs, Snackbar) and `pages/Chat/ResearchTraceBlock.tsx`.
- Coverage targets: backend `app/api` line coverage ≥ 70%, frontend `components/ui` ≥ 50%; reported by CI but not blocking initially.

### P1-1: Adopt Alembic migrations

- `alembic init backend/alembic` and generate a baseline revision from the current `Base.metadata`.
- Change `lifespan.py`: keep `create_all` for SQLite development mode; otherwise run `alembic upgrade head` (or run it from the deployment script).
- Enable batch mode for SQLite to support ALTER.

### P1-2: Unified `ToolProvider` interface

- Define a `ToolProvider` Protocol: `list_definitions() -> list[dict]`, `can_handle(name) -> bool`, `execute(name, arguments) -> Any`.
- Implement `BuiltinToolProvider` (the existing four tools), `CustomApiToolProvider` (reads `custom_api_tools`), and `McpToolProvider` (reads `mcp_servers.discovered_tools`).
- Reduce `ResearchToolRegistry` to an aggregator: compose providers, detect name collisions, inject SSRF checks and timeouts uniformly, and keep the `GET /api/chat/tools` response format unchanged.
- Adding a new source (e.g. a future database query tool) then only requires a new provider.

### P1-3: Finish the TSX migration and remove dead code

- Delete `frontend/src/pages/Chat.jsx`, `frontend/src/utils/logger.js` (standardise on `secureLogger.ts`), and the workflow types in `backend/app/models/payloads.py`.
- Convert `App.jsx`, `Layout.jsx`, `PrivateRoute.jsx`, `AdminDashboard.jsx`, `Documents.jsx`, `AiTools.jsx`, `LoginPage.jsx`, `RegisterPage.jsx`, and `ProfilePage.jsx` to `.tsx`, one page per PR.
- Extend the lint script in `package.json` to `--ext js,jsx,ts,tsx`.

### P2-1: Observability

- Structured JSON logs (reusing `security_logging.py` redaction) and a request-id middleware.
- Expose `/metrics` via `prometheus-fastapi-instrumentator`; labels must never contain user input or sensitive values.
- Move `research_trace` out of `messages.context_used` into its own table to support queries and statistics (depends on P1-1).

### P2-2: Configuration governance

- Make `config.py` the single source of truth: give `DATABASE_URL` a default of `sqlite:///./chatbot.db`; generate `.env.example` and the README environment matrix from `Settings` via a script, or verify them with a test.
- Reconcile differences such as `CHUNK_SIZE` / `CHUNK_OVERLAP` between `.env.example` and `config.py`, and state them in the CHANGELOG.

---

## Consequences & Trade-offs

### Positive Consequences

- **Correctness**: revocation only becomes reliable once the blacklist works across processes; Alembic makes schema evolution traceable.
- **Maintainability**: CI and a test baseline block regressions; ToolProvider lets tool sources evolve independently; finishing TSX removes the dual code paths.
- **Operability**: metrics and request ids make performance and errors attributable.

### Negative Consequences & Risks

- **Optional dependencies return**: `RedisBlacklist` and `/metrics` reintroduce external components, but the default mode stays zero-dependency, so Lite deployments are unaffected.
- **One-off refactoring cost**: ToolProvider and the TSX migration touch core files and must rely on CI and tests as a safety net, split into small PRs.
- **CI duration**: embedding model downloads can slow pytest; control with cache or mocks.
- **SQLite migration limits**: ALTER support is limited and Alembic batch mode rebuilds tables, which matters for large datasets.

---

## Alternatives Considered

| Option | Reason not adopted |
|---|---|
| Require Redis for every deployment | Contradicts the 2.0.0 zero-dependency goal; an optional backend already solves the multi-worker issue |
| Switch ORM (e.g. SQLModel, Tortoise) for built-in migrations | Migration cost far exceeds adopting Alembic, and the existing SQLAlchemy models carry over unchanged |
| Replace the in-house registry with LangChain Tools / OpenAI Agents SDK | A large framework would conflict with the existing native tool-calling compatibility handling for Azure v1 / Ollama; the ToolProvider abstraction is sufficient |
| Complete the TSX migration in a single PR | Too large to review; split per page instead |
