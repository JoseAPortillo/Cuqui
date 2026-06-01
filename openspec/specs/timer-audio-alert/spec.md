# Timer Audio Alert Specification

## Purpose

Play an audible chime when a timer reaches "completed" state. Must work on iOS Safari despite autoplay restrictions.

## Requirements

### Requirement: Completion Chime

The system SHALL play a short chime when a timer transitions to "completed". The chime SHALL be a short audio snippet (WAV or similar) embedded in the frontend bundle.

#### Scenario: Chime plays on completion

- GIVEN a timer that is about to complete
- WHEN the timer status becomes "completed"
- THEN an audible chime SHALL be heard from the device speakers
- AND the chime SHALL play within 500ms of the status change

#### Scenario: Multiple concurrent timers

- GIVEN two timers completing simultaneously
- WHEN both reach "completed" status
- THEN the chime SHALL play at least once
- AND no runtime error SHALL occur from overlapping playback

### Requirement: User-Gesture Gate

Audio playback MUST be gated on a prior user gesture (click, tap, keypress, voice input). The system SHALL track a `hasInteracted` flag; audio SHALL NOT play unless `hasInteracted` is true.

#### Scenario: No gesture, no audio

- GIVEN a user who opens the app and does NOT interact
- WHEN a timer completes
- THEN no audio SHALL play
- AND no console error related to autoplay SHALL appear

#### Scenario: Gesture enables audio

- GIVEN a user who has tapped or spoken a command
- WHEN a timer completes later in the same session
- THEN the chime SHALL play normally

### Requirement: iOS Compatibility

On iOS Safari, the system SHALL use a Web Audio `AudioContext` that is resumed by the first user gesture. This SHALL happen once per session.

#### Scenario: iOS audio context resumed

- GIVEN an iOS device running Safari
- WHEN the user performs the first gesture (tap or command)
- THEN the `AudioContext` SHALL be resumed
- AND subsequent chimes SHALL play through the resumed context

## Non-requirements

- Notification API (push or local notifications) — explicitly deferred
- Volume control or mute toggle
- Different sounds for different timers
- Vibration pattern on completion

## Edge Cases

| Edge Case | Expected Behavior |
|-----------|------------------|
| Audio file fails to load or decode | Chime SHALL silently fail; no error visible to user |
| Rapid completion of many timers | Audio SHALL play at least once; MAY overlap or coalesce |
| Page reload before first gesture | `hasInteracted` flag SHALL reset on page load |
| iOS silent switch is ON | Chime SHALL NOT play (OS-level restriction — not a bug) |
