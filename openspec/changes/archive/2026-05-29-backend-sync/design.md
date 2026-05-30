# Design: Backend Sync (Phase 2)

## Technical Approach

Hexagonal architecture extending the Phase 1 domain into three new layers.
**Application**: `TimerManager` per session via `dict[str, dict[str, Timer]]`, `process_command` routes by intent via `match/case`, `SyncService` manages WS connections and broadcasts state. **Ports**: `IntentParser` protocol abstracts parsing, `Storage` protocol for persistence. **Adapters**: FastAPI (routes/schemas/dependencies), `parser_rules` wraps `TimerParser`, `storage_memory` implements `Storage` with in-memory dict. Maps to specs `timer-manager` and `timer-api`.

## Architecture Decisions

| Option | Tradeoffs | Decision |
|--------|-----------|----------|
| **Storage**: dict-of-dicts vs SQLite | dict: zero deps, no setup, lost on restart. DB: durable but overkill for MVP | `dict[str, dict[str, Timer]]` — matches spec's session-scoped design, trivial to swap later via Storage protocol |
| **Sync coupling**: SyncService injected into TimerManager vs called externally by process_command | Injected: tighter coupling, harder to test. External: explicit flow, easy to mock | SyncService called **externally** in the orchestration — process_command returns state, caller decides broadcast |
| **Command routing**: `isinstance` match/case vs dict[Intent, Callable] | Dict dispatch: faster, extensible. Match/case: explicit intent-to-method mapping in code, zero indirection | `match/case` on `CuquiCommand` — keeps routing visible in one place, follows domain pattern |
| **Parser adapter**: wrapper vs re-import TimerParser | Wrapper: one interface to maintain. Re-import: tight coupling to domain | Wrapper — `parser_rules/adapter.py` implements `IntentParser` protocol by delegating to `TimerParser.parse()` |
| **FastAPI lifespan**: creates TimerManager per app vs per request | Per app: shared state, one instance. Per request: stateless but pointless for sync | Single `TimerManager` via FastAPI lifespan, injected via `Depends()` (as per proposal) |

## Data Flow

**Command flow** (REST):
```
Client ──POST /commands/text──→ FastAPI Router
                                      │
                                      ▼
                              parser_rules Adapter ──→ TimerParser.parse()
                                      │
                                  CuquiCommand or ParseError
                                      │
                                      ▼
                              process_command (match/case)
                                      │
                                      ▼
                              TimerManager (delegates to Timer methods)
                                      │
                                      ▼
                            TimerState JSON ←── SyncService.broadcast()
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                     HTTP Response           WS Clients
```

**WebSocket flow** (broadcast):
```
Client A ──WS /ws/session/{id}──→ FastAPI
Client B ──WS /ws/session/{id}──→ FastAPI
                                      │
                                      ▼
                              SyncService.register(ws, session_id)
                                      │
                (on any POST /commands/text mutation in same session)
                                      │
                                      ▼
                              SyncService.broadcast(session_id, state)
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                     Client A                 Client B
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/cuqui/application/manage_timers.py` | Create | `TimerManager` — session-scoped dict CRUD, domain delegation |
| `backend/cuqui/application/process_command.py` | Create | `process_command()` — `match/case` routing of all 8 intents |
| `backend/cuqui/application/sync_state.py` | Create | `SyncService` — WS registry + JSON broadcast |
| `backend/cuqui/application/__init__.py` | Modify | Export public symbols |
| `backend/cuqui/ports/intent_parser.py` | Create | `IntentParser` protocol — `parse(text: str) -> CuquiCommand \| ParseError` |
| `backend/cuqui/ports/storage.py` | Create | `Storage` protocol — `load/save/list_sessions` for persistence |
| `backend/cuqui/ports/__init__.py` | Modify | Export public symbols |
| `backend/cuqui/adapters/parser_rules/__init__.py` | Create | Package init |
| `backend/cuqui/adapters/parser_rules/adapter.py` | Create | `TimerParserAdapter` — wraps `TimerParser` as `IntentParser` |
| `backend/cuqui/adapters/storage_memory/__init__.py` | Create | Package init |
| `backend/cuqui/adapters/storage_memory/adapter.py` | Create | `InMemoryTimerStore` — `Storage` impl via dict |
| `backend/cuqui/adapters/api_fastapi/__init__.py` | Create | Package init |
| `backend/cuqui/adapters/api_fastapi/routes.py` | Create | FastAPI router — `POST /commands/text`, `GET /timers`, `WS /ws/session/{id}` |
| `backend/cuqui/adapters/api_fastapi/schemas.py` | Create | Pydantic models — request/response/error schemas |
| `backend/cuqui/adapters/api_fastapi/dependencies.py` | Create | `Depends()` wiring — `TimerManager`, `SyncService`, `IntentParser` |

## Interfaces / Contracts

```python
# ports/intent_parser.py
class IntentParser(Protocol):
    def parse(self, text: str) -> CuquiCommand | ParseError: ...

# ports/storage.py
class Storage(Protocol):
    def load(self, session_id: str) -> dict[str, Timer]: ...
    def save(self, session_id: str, timers: dict[str, Timer]) -> None: ...
    def list_sessions(self) -> list[str]: ...

# Timer serialization (for JSON responses / WS broadcast)
# {
#   "id": str, "name": str, "duration": int, "remaining": int,
#   "status": str, "created_at": str (ISO 8601)
# }

# Error response contracts
# ParseError: {"error": "parse_error", "message": "...", "original_text": "..."}
# DomainError: {"error": "domain_error", "message": "..."}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `TimerManager` — add/get/remove/transition delegation, non-existent states | Pure function tests, mock Timer for edge cases |
| Unit | `process_command` — all 8 intents, unrecognized commands, domain errors | Parametrized test per intent, assert correct method called |
| Unit | `SyncService` — register/unregister/broadcast, multi-session isolation | Mock `WebSocket.send_text()`, verify broadcast scope |
| Unit | `parser_rules` adapter — delegates to `TimerParser`, returns correct types | Mock TimerParser, verify protocol adherence |
| Unit | `InMemoryTimerStore` — load/save/list across sessions | Direct assertions on dict state |
| Integration | FastAPI routes — health, POST commands, GET timers | `httpx.AsyncClient` with TestClient, full stack |
| Integration | WebSocket connect, broadcast, disconnect | `pytest-asyncio`, connect + POST + assert WS message received |

Existing Phase 1 tests must continue passing (183 tests — verify with `pytest` before finalizing).

## Migration / Rollout

No migration required. In-memory storage means no data survives restart — acceptable for MVP. Phase 1 domain layer is untouched. Ship via chained PRs: (1) application layer, (2) ports + adapters, (3) tests.

## Open Questions

- [ ] Confirm `websockets` version pin in pyproject.toml (already declared, verify compat with uvicorn)
