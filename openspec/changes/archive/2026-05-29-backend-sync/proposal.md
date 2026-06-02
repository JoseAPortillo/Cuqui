# Proposal: Backend Sync (Phase 2)

## Intent

Phase 1 delivered the domain layer — stateless Timer entity, parser, and command schemas. Phase 2 connects these into a running backend: an application layer managing timers per session, a FastAPI API (REST + WebSocket), and port/adapter wiring for testable infrastructure.

## Scope

### In Scope
- **Application layer**: TimerManager (dict storage), command orchestrator (intent routing), SyncService (WS broadcast)
- **Ports layer**: IntentParser protocol, Storage protocol
- **Adapters layer**: FastAPI routes/schemas/dependencies, parser adapter, in-memory storage
- **Tests**: ~8 files, unit + integration

### Out of Scope
- Audio commands (`POST /commands/audio`) — deferred to ASR Phase 4
- LLM fallback for parsing
- Auto-completion tick loop (client-side calculation)
- `SYNC_FINISH_TIME` intent
- Persistent database (in-memory only)

## Capabilities

### New Capabilities
- `timer-api`: REST + WebSocket API for timer commands and state sync — endpoints at `POST /commands/text`, `GET /timers`, `WS /ws/session/{session_id}`
- `timer-manager`: Application layer — TimerManager, command orchestrator by intent, SyncService for WS broadcast

### Modified Capabilities
None. Existing Phase 1 specs (`command-schema`, `timer-domain`, `timer-parser`) are untouched — only new infrastructure wraps them.

## Approach

Clean Architecture with three new layers. **Application**: `TimerManager` stores `dict[session_id][timer_id] -> Timer` and delegates state transitions to domain Timer methods. Command orchestrator receives `CuquiCommand`, routes by intent, calls TimerManager, returns updated state. `SyncService` tracks WS connections per session and broadcasts state changes. **Ports**: `IntentParser` protocol abstracts parsing; `Storage` protocol abstracts persistence (in-memory initially). **Adapters**: FastAPI with DI via dependencies, `TimerParser` wrapped as `IntentParser`, `InMemoryTimerStore` as storage adapter. No singleton — FastAPI lifespan manages TimerManager per session.

Files exceed ~1060 total lines (source + tests), so a **chained PR strategy** is recommended: slice 1 = application layer, slice 2 = ports + adapters, slice 3 = tests + integration.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/cuqui/application/manage_timers.py` | New | TimerManager: dict CRUD, domain delegation |
| `backend/cuqui/application/process_command.py` | New | Intent router → TimerManager |
| `backend/cuqui/application/sync_state.py` | New | WS connection manager, broadcast |
| `backend/cuqui/ports/intent_parser.py` | New | Protocol for parse(text) |
| `backend/cuqui/ports/storage.py` | New | Protocol for load/save |
| `backend/cuqui/adapters/api_fastapi/routes.py` | New | FastAPI router, REST + WS |
| `backend/cuqui/adapters/api_fastapi/schemas.py` | New | Pydantic request/response models |
| `backend/cuqui/adapters/api_fastapi/dependencies.py` | New | DI wiring |
| `backend/cuqui/adapters/parser_rules/adapter.py` | New | TimerParser → IntentParser wrapper |
| `backend/cuqui/adapters/storage_memory/adapter.py` | New | In-memory store |
| `backend/pyproject.toml` | Modified | Add FastAPI + uvicorn deps |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|-------------|
| WS broadcast coupling to command flow | Med | SyncService as injectable dependency via protocol |
| Change exceeds 400-line review budget | High | Chained PR strategy — slice by layer |
| Parser wrapping adds indirection | Low | Lightweight adapter, no extra validation |

## Rollback Plan

Revert `backend/cuqui/application/`, `ports/`, `adapters/` dirs. Roll back `pyproject.toml` dep additions. Existing domain layer is untouched — Phase 1 tests continue passing.

## Dependencies

- `fastapi`, `uvicorn[standard]` — HTTP + WS server
- `python-dotenv` — optional config

## Success Criteria

- [ ] All 8 intents route through `POST /commands/text` → TimerManager → correct state update
- [ ] WS broadcast reaches all clients in same session on any state change
- [ ] 95%+ test coverage on new layers (application + adapters)
- [ ] All 183 existing Phase 1 tests pass with no regressions
