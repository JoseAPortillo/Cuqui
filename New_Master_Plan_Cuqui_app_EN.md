# Development Plan - TFM: "Cuqui" Intelligent Cooking Assistant

## Index

- [Development Plan - TFM: "Cuqui" Intelligent Cooking Assistant](#development-plan---tfm-cuqui-intelligent-cooking-assistant)
  - [Index](#index)
  - [1. Project Overview](#1-project-overview)
  - [2. Honest Viability Strategy](#2-honest-viability-strategy)
  - [3. Recommended Low-Cost Stack](#3-recommended-low-cost-stack)
  - [4. Natural Language Understanding Engine](#4-natural-language-understanding-engine)
    - [MVP Command Grammar](#mvp-command-grammar)
    - [Supported MVP Intents](#supported-mvp-intents)
    - [Stretch Commands](#stretch-commands)
    - [Example NLU Output](#example-nlu-output)
    - [Processing Strategy](#processing-strategy)
  - [5. Technical Architecture](#5-technical-architecture)
  - [5.1 Backend: FastAPI + Python](#51-backend-fastapi--python)
  - [5.2 Mobile/PWA Client](#52-mobilepwa-client)
  - [5.3 Smartwatch Companion Prototype](#53-smartwatch-companion-prototype)
  - [6. Architecture Strategy](#6-architecture-strategy)
  - [7. Data Flow](#7-data-flow)
    - [MVP Mobile Voice Flow](#mvp-mobile-voice-flow)
    - [Stretch Watch PTT Flow](#stretch-watch-ptt-flow)
  - [8. Realistic Development Plan: 12-16 Weeks](#8-realistic-development-plan-12-16-weeks)
  - [9. Deployment and Reproducibility](#9-deployment-and-reproducibility)
    - [Defense Mode](#defense-mode)
    - [Public Demo Mode](#public-demo-mode)
    - [Important Constraint](#important-constraint)
  - [10. Budget and Cost Plan](#10-budget-and-cost-plan)
  - [11. Risks and Mitigations](#11-risks-and-mitigations)
  - [11.1 Smartwatch Integration Risk](#111-smartwatch-integration-risk)
  - [11.2 Watch Microphone Noise](#112-watch-microphone-noise)
  - [11.3 Local ASR Performance](#113-local-asr-performance)
  - [11.4 Overly Complex Natural Language](#114-overly-complex-natural-language)
  - [11.5 Architecture Overhead](#115-architecture-overhead)
  - [12. TFM Deliverables](#12-tfm-deliverables)
  - [13. Final Scope Decision](#13-final-scope-decision)

---

## 1. Project Overview

"Cuqui" is a voice-assisted cooking timer system designed to manage multiple named timers through natural language commands. The reliable core of the project is a **mobile/web application plus FastAPI backend** that can process voice commands, synchronize timer state in real time, and demonstrate cost-aware AI integration.

This scope makes the project more realistic for a 3-4 month TFM while still demonstrating AI, API design, synchronization, wearable integration, and reproducible deployment.

**Academic Objective:** Demonstrate applied AI integration, natural language command parsing, API design, real-time synchronization, wearable companion architecture, reproducible local deployment, and cost-aware engineering.

**Practical Value:** Provide a useful, ergonomic cooking assistant that helps users manage several cooking tasks without manually editing timers during food preparation.

**MVP Product Definition:**
- Mobile/PWA interface for active timers.
- FastAPI backend with centralized timer state.
- Text command input for deterministic testing.
- Voice command input from the mobile/PWA.
- Rule-based NLU for common cooking timer commands.
- WebSocket synchronization between backend and UI.
- Optional cloud ASR/LLM fallback behind cost controls.
- Watch companion prototype for timer display.

**Stretch Product Definition:**
- Watch Push-to-Talk voice capture.
- Local `faster-whisper` transcription as offline/demo mode.
- Advanced command disambiguation with a local or cloud LLM.
- Voice Activity Detection (VAD).
- Recipe retrieval/RAG.

**Success Metrics:**
- Rule-based NLU accuracy >90% on a controlled project test set.
- End-to-end latency <3 seconds for mobile voice command to timer update in the demo environment.
- Watch display synchronization latency <2 seconds when the companion app is connected.
- Monthly operating cost close to $0 for the TFM demo, with fallback API usage capped under $5/month.

---

## 2. Honest Viability Strategy

The project is viable if the build order protects the core system from wearable risk. The main technical risk is not the AI layer; it is smartwatch integration, audio capture permissions, device-to-device communication, and background behavior.

Therefore, Cuqui will be developed in layers:

1. **Reliable Core:** backend, timer engine, parser, WebSocket sync, and mobile/PWA interface.
2. **Voice Layer:** mobile microphone recording and ASR integration.
3. **Experimental Layer:** watch PTT audio capture, local ASR, VAD, and advanced LLM fallback.

The TFM must remain defensible even if the watch microphone path has limitations. The mobile/backend system is the main product; the watch is a companion demonstration.

---

## 3. Recommended Low-Cost Stack

- **Backend:** FastAPI running locally with Docker for the defense.
- **Frontend/Mobile:** React/Vue/Svelte PWA, hosted locally for defense or on Cloudflare Pages/Vercel for public demo.
- **Smartwatch Client:** Prefer **one platform only**. Recommended: Wear OS with Kotlin/Jetpack Compose if an Android watch is available.
- **State Sync:** WebSockets from backend to clients.
- **Timer Storage:** In-memory for MVP; SQLite only if session persistence becomes necessary.
- **Speech-to-Text MVP:** Cloud ASR fallback or browser/mobile audio upload to backend.
- **Speech-to-Text Offline Demo:** `faster-whisper` with `tiny`, `base`, or `small`, depending on available hardware.
- **NLU Main Path:** Deterministic rule-based parser.
- **NLU Fallback:** Small LLM call for JSON command extraction only when the rule parser has low confidence.
- **TTS:** Browser or native OS `SpeechSynthesis` instead of paid TTS.

The project should not depend on paid APIs to work, but it should include a controlled fallback for demo reliability.

---

## 4. Natural Language Understanding Engine

The NLU engine is the core academic contribution. It translates user commands into structured timer actions.

### MVP Command Grammar

The first version should support a controlled but useful command set:

- "Set 10 minutes for pasta."
- "Add 5 minutes to chicken."
- "Reduce rice by 2 minutes."
- "Cancel the potatoes."
- "Pause the fish timer."
- "Resume all timers."
- "Rename pasta to spaghetti."
- "Make rice finish with chicken."
- "How much time is left on the steak?"

### Supported MVP Intents

- `SET_TIMER`
- `CANCEL_TIMER`
- `PAUSE_TIMER`
- `RESUME_TIMER`
- `EXTEND_TIMER`
- `REDUCE_TIMER`
- `RENAME_TIMER`
- `SYNC_FINISH_TIME`
- `QUERY_TIMER`

### Stretch Commands

More complex natural language should be treated as stretch scope:

> "Set 10 minutes for the turbot, but if there is already an alarm for the potatoes, make them finish at the same time."

This type of multi-action command is valuable for the thesis, but it should not block the MVP.

### Example NLU Output

```json
{
  "intent": "EXTEND_TIMER",
  "actions": [
    {
      "type": "EXTEND_TIMER",
      "target": "steak",
      "delta_seconds": 300
    }
  ],
  "confidence": 0.94,
  "processing_mode": "rule_parser"
}
```

### Processing Strategy

1. Accept text command directly for repeatable tests.
2. Accept audio command from mobile/PWA and transcribe it.
3. Run deterministic parser first.
4. If confidence is low, optionally call an LLM fallback constrained to a JSON schema.
5. Validate output against the application command schema.
6. Execute timer changes through application use cases.

---

## 5. Technical Architecture

## 5.1 Backend: FastAPI + Python

The backend is the main source of truth.

Responsibilities:
- REST endpoint for text commands.
- REST endpoint for audio command upload.
- WebSocket endpoint for live timer state.
- Central timer manager.
- Rule-based parser.
- Optional ASR and LLM adapters.
- Cost-control service for API usage.

Recommended endpoints:

```text
POST /commands/text
POST /commands/audio
GET  /timers
WS   /ws/session/{session_id}
```

## 5.2 Mobile/PWA Client

The mobile/PWA client is the main user-facing application.

Required features:
- Active timer dashboard.
- Text command input for testing and fallback.
- Push-to-talk voice button using browser/mobile microphone APIs.
- Clear timer alerts.
- Real-time updates from backend.
- Cost/debug panel for the TFM demo.

The mobile/PWA must be fully usable even without the smartwatch.

## 5.3 Smartwatch Companion Prototype

The smartwatch app should be intentionally small.

Required features:
- Show active timers.
- Show timer completion alerts.
- Pause/silence timer alert.
- Sync state from backend/mobile bridge.

Optional features:
- Push-to-Talk recording.
- Hardware button shortcut for "Pause All" or "Silence".
- Circular progress ring UI.

Important decision: build for **one watch platform only**. Do not attempt both Wear OS and watchOS during the TFM unless the core project is already complete.

---

## 6. Architecture Strategy

Cuqui will use a lightweight Hexagonal Architecture. The goal is separation of concerns, not over-engineering.

Recommended structure:

```text
backend/
  cuqui/
    domain/
      timer.py
      command.py
      session.py
    application/
      process_command.py
      manage_timers.py
      sync_state.py
    ports/
      speech_to_text.py
      intent_parser.py
      notification.py
      storage.py
    adapters/
      api_fastapi/
      parser_rules/
      asr_faster_whisper/
      asr_openai/
      llm_openai/
      storage_memory/
```

This keeps the timer logic independent from FastAPI, OpenAI, Whisper, or smartwatch-specific code.

The architecture should stay simple enough to finish. Avoid adding abstractions that do not protect a real boundary.

---

## 7. Data Flow

### MVP Mobile Voice Flow

```text
[ Mobile/PWA ]
  (1) User presses PTT and says: "Add 5 minutes to the steak"
        |
        v
[ FastAPI Backend ]
  (2) Receives audio through /commands/audio
  (3) Transcribes audio
  (4) Parses intent: { type: "EXTEND_TIMER", target: "steak", delta_seconds: 300 }
  (5) Updates central timer manager
  (6) Broadcasts new timer state through WebSocket
        |
        v
[ Mobile/PWA ]
  (7) Render updated countdowns
```

### Stretch Watch PTT Flow

```text
[ Smartwatch ]
  (1) User presses PTT and records a short audio clip
  (2) Sends compressed audio to mobile or backend
        |
        v
[ Backend ]
  (3) Transcribes, parses, executes, and broadcasts state
```

---

## 8. Realistic Development Plan: 12-16 Weeks

| Phase | Activities | Duration | Milestone |
| :--- | :--- | :---: | :--- |
| **Phase 1: Core Domain + Parser** | Timer domain, command schema, rule parser, text command tests. | 2 weeks | Text commands correctly modify timers. |
| **Phase 2: Backend + Sync** | FastAPI endpoints, WebSocket broadcasting, in-memory sessions. | 2 weeks | Multiple clients receive live timer updates. |
| **Phase 3: Mobile/PWA MVP** | Timer dashboard, text command UI, voice button placeholder, alerts. | 2 weeks | Usable mobile/web app without watch. |
| **Phase 4: ASR Integration** | Mobile audio upload, local or cloud transcription, parser integration. | 2 weeks | Voice commands update timers reliably. |
| **Phase 5: Watch Companion** | One-platform watch app, timer display, alert/silence control. | 3-5 weeks | Watch shows synchronized timers. |
| **Phase 6: Polish + Thesis Prep** | Tests, kitchen noise trials, Docker, cost logs, defense script. | 2-3 weeks | Stable reproducible defense demo. |

If time becomes tight, Phase 5 should be reduced to timer display only. The project remains valid because the main system is complete.

---

## 9. Deployment and Reproducibility

### Defense Mode

- Backend runs locally through Docker Compose.
- Frontend/PWA runs locally or as a static build.
- Watch app is sideloaded only if the companion prototype is ready.
- Paid API fallbacks are controlled by environment variables.

### Public Demo Mode

- Frontend hosted on Cloudflare Pages or Vercel Hobby.
- Backend hosted on a free or low-cost provider, accepting cold starts.
- SQLite or in-memory state depending on demo needs.

### Important Constraint

Browser audio recording requires a secure context. Use `localhost` for local development or HTTPS for hosted demos.

---

## 10. Budget and Cost Plan

| Item | Cheapest Choice | Estimated Monthly Cost | Notes |
| :--- | :--- | :---: | :--- |
| Frontend/PWA hosting | Cloudflare Pages / Vercel Hobby | $0 | Static hosting. |
| Backend for defense | Local Docker Compose | $0 | Most reliable for presentation day. |
| Backend public demo | Free/low-cost hosting | $0-$5 | Cold starts may apply. |
| Database | In-memory / SQLite | $0 | Enough for MVP. |
| Speech-to-text | Local `faster-whisper` or paid fallback | $0-$5 | Local mode may vary by hardware. |
| NLU | Rule parser | $0 | Main path. |
| LLM fallback | Low-cost JSON extraction | Cents/month | Only for low-confidence commands. |
| TTS | Device/browser native TTS | $0 | Avoid paid TTS. |
| Smartwatch testing | Existing device + sideloading | $0 | Avoid buying hardware late. |

Cost controls:
- Disable paid APIs by default.
- Add daily API call limits.
- Log estimated ASR/LLM spend.
- Show fallback usage in the demo panel.

---

## 11. Risks and Mitigations

## 11.1 Smartwatch Integration Risk

**Risk:** Watch development can consume too much time due to permissions, connectivity, device differences, and background behavior.

**Mitigation:** The watch is a companion prototype. The mobile/PWA remains fully functional without it. Build watch display before watch microphone capture.

## 11.2 Watch Microphone Noise

**Risk:** Kitchen noise and wrist microphone placement can reduce transcription quality.

**Mitigation:** Use strict PTT. Keep audio clips short. Ask the user to bring the wrist near the mouth. Keep mobile PTT as the reliable fallback.

## 11.3 Local ASR Performance

**Risk:** `faster-whisper` may be too slow or inaccurate on the defense machine.

**Mitigation:** Benchmark early. Keep cloud ASR fallback available. Cache demo test clips for repeatability.

## 11.4 Overly Complex Natural Language

**Risk:** Complex conversational commands may create unreliable behavior.

**Mitigation:** Define a controlled command grammar for MVP. Treat multi-action conversational parsing as stretch scope.

## 11.5 Architecture Overhead

**Risk:** Hexagonal Architecture may slow development if implemented too rigidly.

**Mitigation:** Use clear boundaries only where needed: domain, application, ports, adapters. Avoid unnecessary layers.

---

## 12. TFM Deliverables

Required:
- Git repository with backend and mobile/PWA source code.
- Timer domain model and command parser.
- FastAPI API with WebSocket synchronization.
- Reproducible Docker Compose setup.
- Test set for NLU command accuracy.
- Thesis document covering ASR, NLU, timer synchronization, architecture, and cost controls.
- Demo script showing text command, voice command, timer sync, and cost logging.

Recommended:
- Smartwatch companion prototype for one platform.
- Side-loadable watch package if available.
- Local ASR benchmark results.

Optional:
- Watch PTT audio capture.
- VAD.
- Recipe RAG.
- Advanced LLM fallback.

---

## 13. Final Scope Decision

The project should be evaluated as:

> A reliable voice-controlled multi-timer cooking assistant with a smartwatch companion prototype.

It should not be evaluated as:

> A fully polished commercial smartwatch-first cooking assistant.

This makes the project honest, buildable, and academically strong. The core system proves the important engineering ideas, while the watch integration demonstrates future product potential without putting the entire TFM at risk.
