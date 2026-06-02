# Timer Manager Specification

## Purpose

Application layer managing Timer instances per session, orchestrating commands by intent routing, and broadcasting state changes via SyncService. Bridges pure domain logic with infrastructure.

## Requirements

### Session-scoped Timer Storage

TimerManager MUST store Timer instances in a two-level map: `session_id -> timer_id -> Timer`. It SHALL support add, get, list, and remove operations. Non-existent sessions or timers SHALL return empty state.

#### Scenario: Add and retrieve timer

- GIVEN session "s1"
- WHEN add_timer("t1", "Pasta", 300) is called
- THEN get_timer("t1") SHALL return a Timer with name "Pasta", duration 300, status "pending"

#### Scenario: Non-existent timer returns None

- GIVEN session "s1" with no timers
- WHEN get_timer("nonexistent") is called
- THEN the result SHALL be None

### State Transition Delegation

TimerManager MUST delegate all transitions to domain Timer methods. start, pause, resume, cancel, and complete SHALL call the matching Timer method. Domain errors MUST propagate without being caught or wrapped.

#### Scenario: Start delegates to Timer.start()

- GIVEN a pending Timer "t1" in session "s1"
- WHEN start_timer("t1") is called
- THEN the Timer's start() SHALL be invoked and status SHALL become "running"

#### Scenario: Domain error propagates

- GIVEN a completed Timer "t1"
- WHEN start_timer("t1") is called
- THEN the system MUST raise the domain's invalid-transition error

### Duration and Metadata Commands

extend_timer, reduce_timer, and rename_timer MUST delegate to domain Timer methods. reduce_timer SHALL clamp remaining at 0. Terminal timers MUST reject any mutation.

#### Scenario: Extend running timer

- GIVEN a running Timer with 120s remaining
- WHEN extend_timer("t1", 30) is called
- THEN remaining SHALL be 150s

#### Scenario: Reduce clamps at zero

- GIVEN a running Timer with 10s remaining
- WHEN reduce_timer("t1", 30) is called
- THEN remaining SHALL be 0s

### Command Orchestration

process_command SHALL accept a CuquiCommand and session_id. SHALL route by intent to the matching TimerManager method. SHALL return the updated timer state dict or None for removals. Domain errors SHALL propagate.

#### Scenario: SET_TIMER adds timer to session

- GIVEN a CuquiCommand with intent SET_TIMER, name "Pasta", duration 300
- WHEN process_command(command, "s1")
- THEN a Timer SHALL be added to session "s1"
- AND the result SHALL contain timer state with status "pending"

#### Scenario: CANCEL_TIMER removes and returns None

- GIVEN a timer "t1" exists in session "s1"
- WHEN process_command(CANCEL_TIMER targeting t1, "s1") is called
- THEN get_timer("t1") SHALL return None

#### Scenario: Intent-to-method mapping covers all 8 intents

- GIVEN all 8 intents from SET_TIMER to QUERY_TIMER
- WHEN process_command is called for each
- THEN each SHALL map to exactly one TimerManager method
- AND unsupported intents SHALL return an error

### SyncService Connection Management

SyncService SHALL track WebSocket connections per session_id. register(ws, session_id) SHALL add a connection. unregister(ws) SHALL remove it. broadcast(session_id, state) SHALL send state to all connections in that session.

#### Scenario: Broadcast reaches session

- GIVEN two WebSocket connections registered for session "s1"
- WHEN broadcast("s1", state) is called
- THEN both connections SHALL receive the state
- AND connections in other sessions SHALL NOT receive it

#### Scenario: Unregister removes connection

- GIVEN one connection registered for session "s1"
- WHEN unregister(ws) is called
- THEN broadcast("s1", state) SHALL be a no-op

### Change Broadcast

On any timer mutation, the system SHOULD broadcast updated state to all session connections via SyncService. Broadcast MUST NOT block the command response.

#### Scenario: Broadcast on timer mutation

- GIVEN a process_command flow with SyncService connected
- WHEN command execution returns timer state
- THEN SyncService.broadcast SHALL be called with the session_id and new state
