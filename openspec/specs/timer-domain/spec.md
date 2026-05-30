# Timer Domain Specification

## Purpose

Core entity for Cuqui's cooking timers. Defines `Timer`, `TimerStatus`, lifecycle transitions, and duration manipulation — pure domain logic with zero framework dependencies.

## Requirements

### Requirement: Timer Creation

A Timer SHALL be created with a unique id, name, duration (seconds), and `pending` status. `created_at` SHALL be recorded on creation. Duration MUST be positive.

#### Scenario: Create valid timer

- GIVEN duration 300s and name "Pasta"
- WHEN a Timer is created
- THEN status SHALL be "pending", remaining SHALL equal duration, and name SHALL be "Pasta"

#### Scenario: Reject zero duration

- GIVEN duration 0s
- WHEN creating a Timer
- THEN the system MUST reject with a domain error

#### Scenario: Reject negative duration

- GIVEN duration -60s
- WHEN creating a Timer
- THEN the system MUST reject with a domain error

### Requirement: State Transitions

Timer SHALL follow this state machine: `pending → running → paused → resumed → running`, with terminal states `completed` and `cancelled` reachable from any active state.

| From | Action | To |
|------|--------|----|
| pending | start | running |
| running | pause | paused |
| running | complete | completed |
| paused | resume | running |
| any active | cancel | cancelled |
| completed | cancel | no-op |
| cancelled | any | no-op |

#### Scenario: Full lifecycle

- GIVEN a Timer in "pending" state
- WHEN start → pause → resume → complete
- THEN final state SHALL be "completed" with remaining=0

#### Scenario: Invalid transition

- GIVEN a Timer in "paused" state
- WHEN calling pause again
- THEN the system MUST raise a domain error

#### Scenario: Cancel running timer

- GIVEN a running Timer
- WHEN cancel is called
- THEN state SHALL be "cancelled" and remaining SHALL be preserved

### Requirement: Duration Manipulation

`extend(seconds)` SHALL add to remaining time. `reduce(seconds)` SHALL subtract, clamping at 0 minimum. Both SHALL reject if timer is in terminal state.

#### Scenario: Extend timer

- GIVEN a running Timer with 120s remaining
- WHEN extend(30) is called
- THEN remaining SHALL be 150s

#### Scenario: Reduce below zero

- GIVEN a running Timer with 10s remaining
- WHEN reduce(30) is called
- THEN remaining SHALL be 0s (clamped)

#### Scenario: Extend completed timer

- GIVEN a Timer in "completed" state
- WHEN extend is called
- THEN the system MUST raise a domain error

### Requirement: Rename

A Timer SHALL support renaming in any non-terminal state. Terminal states SHALL reject rename.

#### Scenario: Rename active timer

- GIVEN a running Timer named "Pasta"
- WHEN rename("Rice") is called
- THEN name SHALL be "Rice"

#### Scenario: Rename cancelled timer

- GIVEN a cancelled Timer
- WHEN rename is called
- THEN the system MUST raise a domain error
