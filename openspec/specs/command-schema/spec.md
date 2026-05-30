# Command Schema Specification

## Purpose

Defines the `Intent` enum and `Command` Pydantic model with discriminated union per intent. Provides type-safe parameter validation for all 8 MVP voice intents.

## Requirements

### Requirement: Intent Enum

The system SHALL define an `Intent` enum with exactly these 8 members: `SET_TIMER`, `CANCEL_TIMER`, `PAUSE_TIMER`, `RESUME_TIMER`, `EXTEND_TIMER`, `REDUCE_TIMER`, `RENAME_TIMER`, `QUERY_TIMER`. `SYNC_FINISH_TIME` SHALL be deferred.

#### Scenario: Recognize valid intent

- GIVEN an `Intent` enum
- WHEN checking for `SET_TIMER`
- THEN it SHALL be a member

#### Scenario: Reject out-of-scope intent

- GIVEN an `Intent` enum
- WHEN checking for `SYNC_FINISH_TIME`
- THEN it SHALL NOT be a member

### Requirement: Command Discriminated Union

The `Command` model SHALL be a Pydantic discriminated union keyed by `intent`. Each intent SHALL have exact parameter fields.

#### Scenario: Build SET_TIMER Command

- GIVEN intent `SET_TIMER`, duration 300, unit "seconds", name "Pasta"
- WHEN building a Command
- THEN the model SHALL validate all fields and disallow extras

#### Scenario: Build QUERY_TIMER Command

- GIVEN intent `QUERY_TIMER`, name "Pasta" (no duration)
- WHEN building a Command
- THEN duration SHALL be absent and validation SHALL pass

### Requirement: Per-Intent Parameter Validation

Each intent SHALL validate its own parameter schema. Common rules: `duration` MUST be positive integer seconds, `name` SHALL be optional string (max 50 chars), `unit` SHALL be "seconds", "minutes", or "hours".

#### Scenario: Invalid duration

- GIVEN intent `SET_TIMER` and duration -30
- WHEN building a Command
- THEN validation SHALL fail with Pydantic `ValidationError`

#### Scenario: Missing required field

- GIVEN intent `SET_TIMER` with no duration
- WHEN building a Command
- THEN validation SHALL fail

#### Scenario: Optional timer identification

- GIVEN intent `CANCEL_TIMER` with no name or id
- WHEN building a Command
- THEN validation SHALL pass (defaults to "last" timer)

### Requirement: Pydantic Framework Constraint

The Command model SHALL use Pydantic v2 `BaseModel` and MUST NOT import FastAPI, async, or framework-specific types.

#### Scenario: Clean imports

- GIVEN the `commands.py` module
- WHEN inspecting imports
- THEN no FastAPI or async framework packages SHALL be present
