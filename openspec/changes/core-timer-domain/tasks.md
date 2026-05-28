# Tasks: Core Timer Domain

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~990 (270 source + 720 tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Timer domain) → PR 2 (Command schema) → PR 3 (Parser) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Timer entity + state machine | PR 1 | base=`feature/core-timer-domain`; tests included |
| 2 | Intent enum + Command discriminated union | PR 2 | base=PR-1 branch; independent of unit 1; tests included |
| 3 | Rule-based parser | PR 3 | base=PR-2 branch; depends on commands.py; tests included |

## Phase 1: Foundation — Timer Domain

- [x] 1.1 RED: Write `test_timer.py` — failing tests for TimerStatus, Timer creation validation, 7 state transitions, extend/reduce clamp, rename, terminal no-ops
- [x] 1.2 GREEN: Create `backend/cuqui/domain/timer.py` — TimerStatus enum, frozen Timer dataclass, create_timer() factory, all 8 state-transition methods
- [x] 1.3 REFACTOR: Seal public API, validate immutability, enforce zero framework imports in domain

## Phase 2: Command Schema

- [ ] 2.1 RED: Write `backend/tests/unit/domain/test_commands.py` — failing tests for Intent enum membership, per-intent payload validation, discriminated union, extras rejection
- [ ] 2.2 GREEN: Create `backend/cuqui/domain/commands.py` — Intent enum, all 8 per-intent Pydantic payloads, CuquiCommand discriminated union with intent discriminator

## Phase 3: Rule-based Parser

- [ ] 3.1 RED: Write `backend/tests/unit/domain/test_parser.py` — failing tests for all 8 intent patterns, first-match order, no-match→ParseError, empty/partial/ambiguous input
- [ ] 3.2 GREEN: Create `backend/cuqui/domain/parser.py` — ParseError dataclass, TimerParser class with ordered regex list, parse() returning CuquiCommand | ParseError

## Phase 4: Wiring & Verification

- [ ] 4.1 Modify `backend/cuqui/domain/__init__.py` — export all public symbols (Timer, TimerStatus, Intent, CuquiCommand, ParseError, TimerParser, create_timer)
- [x] 4.2 Create `backend/tests/unit/domain/__init__.py` — package init for test domain
- [ ] 4.3 Run full test suite, confirm all ~60 tests pass, verify ≥90% branch coverage on domain/
