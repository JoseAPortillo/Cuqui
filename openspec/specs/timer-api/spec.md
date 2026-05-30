# Timer API Specification

## Purpose

REST and WebSocket API exposing timer commands and state sync to clients. Accepts natural language text, routes through the application layer, and returns or broadcasts structured timer state. Protocol-agnostic — describes WHAT the API does, not how it is implemented.

## Requirements

### Text Command Endpoint

The API SHALL expose a `POST /commands/text` endpoint accepting raw text and session_id. The system SHALL parse the text into a CuquiCommand, execute it via process_command, and return the updated timer state.

#### Scenario: Valid text creates timer

- GIVEN text "set 5 minute timer for pasta" and session_id "abc"
- WHEN POST /commands/text with body `{"text": "...", "session_id": "abc"}`
- THEN the response SHALL be 200 with timer state containing name "pasta", status "pending", remaining 300

#### Scenario: Invalid text returns 400

- GIVEN malformed text "do something weird"
- WHEN POST /commands/text
- THEN the response SHALL be 400 with error details including the ParseError message

#### Scenario: Domain error returns structured error

- GIVEN text producing a valid command but invalid domain transition
- WHEN POST /commands/text
- THEN the response SHALL be 422 with a domain error payload

### Timer Snapshot Endpoint

The API SHALL expose `GET /timers?session_id={id}` returning all timers in the session as a JSON array. Non-existent sessions SHALL return an empty array, not an error.

#### Scenario: Session with timers

- GIVEN session "abc" containing two timers
- WHEN GET /timers?session_id=abc
- THEN response SHALL be 200 with an array of two timer state objects

#### Scenario: Unknown session returns empty

- GIVEN a session_id that does not exist
- WHEN GET /timers?session_id=nonexistent
- THEN response SHALL be 200 with an empty array

### WebSocket Session Channel

The API SHALL expose `WS /ws/session/{session_id}` for real-time state sync. On any timer mutation in that session, the server SHALL broadcast the full state to all connected clients. The client MAY send messages; the server SHALL NOT require client messages to function.

#### Scenario: Connect and receive broadcast

- GIVEN two WebSocket clients connected to `/ws/session/abc`
- WHEN a mutation occurs in session "abc" (e.g., via POST /commands/text)
- THEN both clients SHALL receive a message with the updated timer state

#### Scenario: Disconnect does not affect other clients

- GIVEN three clients connected to `/ws/session/abc`
- WHEN one client disconnects
- THEN the other two SHALL continue receiving broadcasts without error

### Error Response Contract

All endpoints SHALL return structured JSON error responses. Parse errors SHALL include original text and human-readable message. Domain errors SHALL include the error type and details.

#### Scenario: ParseError response structure

- GIVEN invalid text "xyzzy"
- WHEN POST /commands/text
- THEN the body SHALL contain `{"error": "parse_error", "message": "...", "original_text": "xyzzy"}`

#### Scenario: Missing session_id returns 400

- GIVEN a request without session_id
- WHEN POST /commands/text or GET /timers
- THEN the response SHALL be 400 with a validation error
