# Proposal: Core Timer Domain

## Goal
Establish domain model, command schema, and rule-based parser for Cuqui's 9 MVP voice intents.

## Background
Phase 1 of 6-phase build plan. Greenfield — no source code yet. Hexagonal scaffold exists at `backend/cuqui/{domain,application,ports,adapters}/`. Pydantic + pytest available.

## Scope

### In Scope
- Timer domain entity (id, name, duration, remaining, status, created_at) with start/pause/resume/cancel/extend/reduce/rename methods
- TimerStatus enum (pending, running, paused, completed, cancelled)
- Intent enum (8 of 9 MVP intents — SYNC_FINISH_TIME deferred)
- Command Pydantic model with per-intent parameter validation
- Rule-based regex parser (ordered per-intent patterns → Command)
- Unit tests for all domain logic

### Out of Scope
- Session model, FastAPI, WebSocket, ASR, storage adapters
- SYNC_FINISH_TIME intent (cross-timer relatime complexity deferred)

## Capabilities

### New Capabilities
- `timer-domain`: Timer entity, TimerStatus, value objects, state transitions
- `command-schema`: Intent enum, Command Pydantic model, parameter validation
- `timer-parser`: Rule-based text→Command parser with per-intent patterns

### Modified Capabilities
None — first change in greenfield project.

## Approach
1. TDD: write failing tests first, then implement
2. Timer model as frozen dataclass + pure state-transition methods
3. Command Pydantic model with discriminated union per intent
4. Parser: ordered regex list, first match wins, return Command or ParseError
5. Zero framework imports in domain/ — pure Python stdlib + Pydantic only

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| `backend/cuqui/domain/timer.py` | New | Timer entity, TimerStatus, factory |
| `backend/cuqui/domain/commands.py` | New | Intent enum, Command models |
| `backend/cuqui/domain/parser.py` | New | Rule-based text→Command parser |
| `backend/tests/unit/domain/` | New | Unit tests for all models |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Parser regex conflicts between similar intents | Med | Ordered matching; test ambiguous edge cases |

## Rollback Plan
Remove `backend/cuqui/domain/timer.py`, `commands.py`, `parser.py` and `backend/tests/unit/domain/`. No downstream dependencies exist yet.

## Dependencies
- Python 3.12+ stdlib (dataclasses, enum, re)
- Pydantic v2 (in pyproject.toml)
- pytest 9.0.3 (in .venv)

## Success Criteria
- [ ] All 8 intents parse correctly across 50+ test cases
- [ ] Timer state transitions: pending→running→paused→resumed→completed
- [ ] Invalid commands raise Pydantic ValidationError
- [ ] Zero FastAPI/async imports in domain/
- [ ] ≥90% branch coverage on domain/ module
