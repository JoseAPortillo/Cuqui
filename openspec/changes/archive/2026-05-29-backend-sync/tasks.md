# Tasks: Backend Sync (Phase 2)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1060–1530 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (App+Ports) → PR 2 (Adapters) → PR 3 (Integration tests) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Ports + Application layer | PR 1 | protocols + TimerManager + process_command + SyncService; tests included |
| 2 | Adapters | PR 2 | parser_rules, storage_memory, FastAPI routes/schemas/deps; tests included |
| 3 | Integration + wiring | PR 3 | conftest.py, full-stack test suite, WS broadcast tests |

## Phase 1: Foundation — Ports + Adapters

- [x] 1.1 RED: Tests for `IntentParser` protocol + `TimerParserAdapter`
- [x] 1.2 GREEN: Create `ports/intent_parser.py` with `IntentParser(Protocol)`
- [x] 1.3 GREEN: Create `adapters/parser_rules/adapter.py` — wraps `TimerParser`
- [x] 1.4 RED: Tests for `Storage` protocol + `InMemoryTimerStore`
- [x] 1.5 GREEN: Create `ports/storage.py` with `Storage(Protocol)`
- [x] 1.6 GREEN: Create `adapters/storage_memory/adapter.py` — dict-based store
- [x] 1.7 Update `ports/__init__.py` and adapter `__init__.py` files

## Phase 2: Application Layer — Core Logic

- [x] 2.1 RED: Tests for `TimerManager` (add/get/remove/state delegation)
- [x] 2.2 GREEN: Create `application/manage_timers.py` with `TimerManager`
- [x] 2.3 RED: Tests for `process_command` (all 8 intents + errors)
- [x] 2.4 GREEN: Create `application/process_command.py` with `match/case` routing
- [x] 2.5 RED: Tests for `SyncService` (register/unregister/broadcast isolation)
- [x] 2.6 GREEN: Create `application/sync_state.py` with `SyncService`
- [x] 2.7 Update `application/__init__.py` exports

## Phase 3: API Layer — FastAPI

- [x] 3.1 RED: Tests for FastAPI routes (POST 200/400/422, GET timers, WS connect)
- [x] 3.2 GREEN: Create `adapters/api_fastapi/schemas.py` — Pydantic models
- [x] 3.3 GREEN: Create `adapters/api_fastapi/dependencies.py` — DI with `Depends()`
- [x] 3.4 GREEN: Create `adapters/api_fastapi/routes.py` — REST + WS endpoints
- [x] 3.5 Update `adapters/api_fastapi/__init__.py`

## Phase 4: Integration — Full Suite

- [x] 4.1 Create `conftest.py` with fixtures (TestClient, TimerManager, SyncService)
- [x] 4.2 Integration: POST commands → GET timers → state verification
- [x] 4.3 Integration: WS connect + command POST → broadcast received
- [x] 4.4 Integration: Error scenarios (400 on bad text, 422 on domain error)
- [x] 4.5 Verify all 257 existing tests pass with no regressions (273 total)
