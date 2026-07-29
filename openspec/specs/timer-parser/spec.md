# Timer Parser Specification

## Purpose

Rule-based parser that transforms natural language text into typed `Command` objects. Uses ordered regex-list per intent — first match wins. Returns `Command` on success, `ParseError` on failure.

## Requirements

### Requirement: Ordered Pattern Matching

The parser SHALL evaluate intents in a defined order and return the first matching `Command`. Pattern order: SET_TIMER, PAUSE_TIMER, CANCEL_TIMER, RESUME_TIMER, EXTEND_TIMER, REDUCE_TIMER, RENAME_TIMER.

#### Scenario: First match wins

- GIVEN text "set a 5 minute timer for pasta"
- WHEN parsed
- THEN result SHALL be a `SET_TIMER` Command with duration=300, unit="minutes", name="pasta"

#### Scenario: No match

- GIVEN text "do something random"
- WHEN parsed
- THEN result SHALL be a `ParseError`

### Requirement: Per-Intent Pattern Coverage

Each intent SHALL match its expected utterance patterns. The parser MUST handle variations in phrasing and word order.

#### Scenario: SET_TIMER variations

- GIVEN "timer 10 minutes", "set timer for 10 minutes", "10 minute timer eggs"
- WHEN parsed
- THEN all SHALL return `SET_TIMER` with correct duration

#### Scenario: CANCEL_TIMER with name

- GIVEN "cancel the pasta timer"
- WHEN parsed
- THEN result SHALL be `CANCEL_TIMER` with name="pasta"

#### Scenario: EXTEND_TIMER with unit

- GIVEN "add 2 more minutes"
- WHEN parsed
- THEN result SHALL be `EXTEND_TIMER` with duration=120, unit="minutes"

#### Scenario: REDUCE_TIMER

- GIVEN "reduce by 30 seconds"
- WHEN parsed
- THEN result SHALL be `REDUCE_TIMER` with duration=30, unit="seconds"

#### Scenario: RENAME_TIMER

- GIVEN "rename timer to rice"
- WHEN parsed
- THEN result SHALL be `RENAME_TIMER` with name="rice"

### Requirement: Ambiguity and Edge Cases

The parser SHALL handle ambiguous or malformed input gracefully, returning `ParseError` without crashing.

#### Scenario: Empty input

- GIVEN empty string ""
- WHEN parsed
- THEN result SHALL be `ParseError`

#### Scenario: Partial duration

- GIVEN "set timer for" (no duration)
- WHEN parsed
- THEN result SHALL be `ParseError` (required parameter missing)

#### Scenario: Ambiguous intent

- GIVEN text matching both PAUSE and CANCEL patterns
- WHEN parsed
- THEN the earlier pattern in order SHALL win

### Requirement: ParseError Structure

`ParseError` SHALL carry a human-readable message and the original input text for debugging.

#### Scenario: ParseError fields

- GIVEN failing input "xyzzy"
- WHEN parsing produces a `ParseError`
- THEN it SHALL contain message "No matching intent" and original text "xyzzy"
