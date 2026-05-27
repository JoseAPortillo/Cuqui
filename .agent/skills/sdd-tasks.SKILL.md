# sdd-tasks SKILL

Purpose: break spec+design into ordered, reviewable implementation tasks (work-unit commits).

Task format:
- id, title, estimate (small/medium/large), files likely changed, acceptance criteria, dependencies

## Build order: protect the core, add layers incrementally

This project has a defined build order that MUST be respected. Tasks should be planned in this layer sequence:

1. **Core Domain + Parser** — Timer model, command schema, rule-based NLU parser, domain tests
2. **Backend + Sync** — FastAPI endpoints, WebSocket broadcasting, in-memory session management
3. **Mobile/PWA MVP** — Timer dashboard, text command input, voice button placeholder, real-time alerts
4. **ASR Integration** — Audio upload endpoint, local/cloud transcription, parser integration
5. **Watch Companion** — One-platform watch app (Wear OS), timer display, pause/silence alert
6. **Polish + Thesis Prep** — Kitchen noise trials, Docker Compose, cost logging, demo script

**Important:**
- Layer N+1 should NOT block or delay layer N. Each layer must be functional on its own.
- The smartwatch (layer 5) is a **companion prototype** — the project must be defensible without it.
- Tests should be created alongside each layer, NOT deferred.

Rules:
- Keep each task focused and reviewable (<400 lines ideally).
- Mark tasks that require chained PRs or special CI gating.
- For NLU-related tasks, include acceptance criteria for command accuracy metrics (>90% on the test set).

Output:
- Tasks saved to `sdd/{change}/tasks` via `mem_save`.
