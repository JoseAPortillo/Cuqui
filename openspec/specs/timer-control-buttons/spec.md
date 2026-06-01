# Timer Control Buttons Specification

## Purpose

Provide manual pause, resume, and cancel controls on TimerCard, with corresponding backend REST endpoints and WebSocket state sync.

## Requirements

### Requirement: REST Endpoints

The backend SHALL expose `POST /timers/{timer_id}/pause`, `POST /timers/{timer_id}/resume`, and `POST /timers/{timer_id}/cancel`. Each SHALL accept a `session_id` parameter, delegate to the existing TimerManager method, and return the updated timer state. Invalid transitions SHALL return 422 with a domain error.

#### Scenario: Pause a running timer

- GIVEN a running timer "t1" in session "s1"
- WHEN POST /timers/t1/pause with `session_id=s1`
- THEN the response SHALL be 200 with status "paused"
- AND the full state SHALL be broadcast via WebSocket

#### Scenario: Cancel from any active state

- GIVEN a timer "t1" in state "paused"
- WHEN POST /timers/t1/cancel with `session_id=s1`
- THEN the response SHALL be 200 with status "cancelled"

#### Scenario: Invalid transition returns 422

- GIVEN a timer "t1" in "pending" state
- WHEN POST /timers/t1/pause
- THEN the response SHALL be 422 with a domain error payload

#### Scenario: Non-existent timer returns 404

- GIVEN session "s1" with no timer "nonexistent"
- WHEN POST /timers/nonexistent/pause
- THEN the response SHALL be 404

### Requirement: TimerCard Contextual Buttons

TimerCard SHALL render pause, resume, and cancel buttons based on current timer status. Terminal states ("completed", "cancelled") SHALL show no action buttons. Each button SHALL call the corresponding API method and update the UI optimistically.

#### Scenario: Running timer shows Pause + Cancel

- GIVEN a TimerCard for a timer with status "running"
- WHEN the card renders
- THEN a "Pause" button and a "Cancel" button SHALL be visible
- AND a "Resume" button SHALL NOT be visible

#### Scenario: Paused timer shows Resume + Cancel

- GIVEN a TimerCard for a timer with status "paused"
- WHEN the card renders
- THEN a "Resume" button and a "Cancel" button SHALL be visible
- AND a "Pause" button SHALL NOT be visible

#### Scenario: Completed timer shows no controls

- GIVEN a TimerCard for a timer with status "completed"
- WHEN the card renders
- THEN no action button SHALL be visible

#### Scenario: Pause triggers WS broadcast

- GIVEN multiple WebSocket clients connected to session "s1"
- WHEN a user clicks Pause on a running timer
- THEN the timer state SHALL update on all connected clients
- AND the Pause button SHALL change to a Resume button on all clients

## Non-requirements

- Drag-to-reschedule or swipe gestures
- Keyboard shortcuts for pause/resume/cancel
- Batch operations on multiple timers

## Edge Cases

| Edge Case | Expected Behavior |
|-----------|------------------|
| Timer completes while paused | Status transitions to "completed"; Resume/Cancel buttons replaced by empty state via WS |
| Network error on POST | Button SHALL remain in pre-click state; error SHALL be silently logged |
| Double-click Pause rapidly | Second request SHALL receive 422; UI SHALL stay in paused state |
| Offline click | Button SHALL appear to do nothing; state SHALL correct on reconnect |
