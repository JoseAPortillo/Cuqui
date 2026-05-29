# Design: Core Timer Domain

## Technical Approach

Pure domain layer (Phase 1 only) — three modules in `backend/cuqui/domain/`: `timer.py` (entity + state machine), `commands.py` (intent enum + frozen dataclass commands), `parser.py` (regex-based text→Command translation). All domain logic TDD-driven, zero framework dependencies — pure Python stdlib everywhere.

## Architecture Decisions

| Decision | Choice | Alternatives Considered | Rationale |
|---|---|---|---|
| Timer model | Frozen dataclass (immutable) | Mutable class, `@dataclass(slots=True)` | Thread-safe for future WebSocket concurrency; state transitions return new instances, preventing accidental shared-mutation bugs |
| State machine | Pure methods returning new Timer | In-place mutation with validation, explicit state table | Immutability gives free undo/event sourcing path; each transition is a pure function: `(Timer, args) → Timer` |
| Discriminated union | `Union` type alias with `isinstance` narrowing | Pydantic `Field(discriminator='intent')`, manual `__init_subclass__` | Pure stdlib — domain MUST have zero external dependencies. Frozen dataclasses + `Union` preserve type safety without Pydantic |
| Parser | Ordered regex list, first-match-wins | LLM-based NLU, `spaCy` patterns, PEG parser | Zero external deps; predictable, deterministic, fast (~µs). LLM fallback for low-confidence in Phase 3 |
| ParseError | Value object (dataclass), NOT an exception | `ValueError` subclass, `Optional[Command]` | Spec says "returns Command or ParseError" — both are return values, callers pattern-match with `isinstance` |

## Data Flow

```
User utterance (str)
        │
        ▼
  Parser.parse(text)
        │
        ├── match → Command { intent, duration?, name? }
        │
        └── no match → ParseError { message, original_text }
```

Phase 2 (application) will pipe `Command → Timer.method()` downstream.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/cuqui/domain/timer.py` | Create | `TimerStatus` enum + frozen `Timer` dataclass + `create_timer()` factory |
| `backend/cuqui/domain/commands.py` | Create | `Intent` enum + 8 per-intent frozen dataclass commands + `CuquiCommand` Union type alias |
| `backend/cuqui/domain/parser.py` | Create | `ParseError` dataclass + `TimerParser` class with ordered regex patterns |
| `backend/cuqui/domain/__init__.py` | Modify | Export all public symbols (Timer, TimerStatus, Intent, CuquiCommand, ParseError, TimerParser) |
| `backend/tests/unit/domain/__init__.py` | Create | Package init |
| `backend/tests/unit/domain/test_timer.py` | Create | Timer lifecycle, transitions, duration ops, rename, edge cases (~25 tests) |
| `backend/tests/unit/domain/test_commands.py` | Create | Intent enum, per-intent payload validation, discriminated union (~15 tests) |
| `backend/tests/unit/domain/test_parser.py` | Create | Pattern matching, intent order, edge cases, ambiguous input (~20 tests) |

## Interfaces / Contracts

```python
# timer.py — pure stdlib
class TimerStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class Timer:
    id: str
    name: str
    duration: int          # total seconds
    remaining: int         # current remaining seconds
    status: TimerStatus
    created_at: datetime

    def start(self) -> Timer: ...
    def pause(self) -> Timer: ...
    def resume(self) -> Timer: ...
    def complete(self) -> Timer: ...
    def cancel(self) -> Timer: ...
    def extend(self, seconds: int) -> Timer: ...
    def reduce(self, seconds: int) -> Timer: ...
    def rename(self, name: str) -> Timer: ...

def create_timer(name: str, duration_secs: int) -> Timer: ...

# commands.py — pure stdlib (frozen dataclasses)
class Intent(enum.IntEnum):
    SET_TIMER = 1; CANCEL_TIMER = 2; PAUSE_TIMER = 3
    RESUME_TIMER = 4; EXTEND_TIMER = 5; REDUCE_TIMER = 6
    RENAME_TIMER = 7; QUERY_TIMER = 8

@dataclass(frozen=True)
class SetTimerCommand:
    duration: int
    unit: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        _validate_duration_positive(self.duration)
        _validate_unit(self.unit)
        _validate_name(self.name)

# ... 7 more per-intent commands ...

CuquiCommand = Union[
    SetTimerCommand, CancelTimerCommand, PauseTimerCommand,
    ResumeTimerCommand, ExtendTimerCommand, ReduceTimerCommand,
    RenameTimerCommand, QueryTimerCommand,
]

# parser.py — pure stdlib
@dataclass
class ParseError:
    message: str
    original_text: str

class TimerParser:
    def __init__(self) -> None: ...
    def parse(self, text: str) -> CuquiCommand | ParseError: ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit — Timer | Creation validation, all 7 state transitions, extend/reduce clamping, rename, terminal no-ops | Pure function assertions — call method, assert returned Timer fields |
| Unit — Commands | Each command validates required fields, rejects invalid durations (0, negative), rejects invalid units, rejects long names | Direct constructor call + `__post_init__`, assert raises `ValueError` |
| Unit — Parser | All 8 intent patterns, first-match order, no-match→ParseError, edge cases (empty, partial) | Feed strings, assert `isinstance(result, CuquiCommand/ParseError)` and field values |

No integration or E2E tests needed — Phase 1 is pure domain logic with zero I/O.

## Migration / Rollout

No migration required. Greenfield — no existing data or consumers.

## Open Questions

None.
