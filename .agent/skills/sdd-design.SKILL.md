# sdd-design SKILL

Purpose: capture architecture and design decisions, tradeoffs, and diagrams needed to implement the spec.

Deliverables:
- Decision list: name, chosen option, rejected alternatives, why
- Data model changes, API contract sketches, sequence diagrams (textual)
- Migration plan for DB or schema changes

Output:
- Design saved to `sdd/{change}/design` via `mem_save`.

## Project architecture: Hexagonal (Ports & Adapters)

This project follows a **lightweight Hexagonal Architecture**. Design decisions MUST respect these layer boundaries:

```
backend/cuqui/
  domain/        → Pure business logic, zero dependencies on frameworks
  application/   → Use cases / application services
  ports/         → Abstract interfaces / contracts (SPI)
  adapters/      → Concrete implementations (FastAPI, Whisper, OpenAI, etc.)
```

**Layer dependency rules:**
- `domain` → depends on NOTHING outside Python stdlib
- `application` → depends on `domain` only
- `ports` → depends on `domain` only (defines interfaces)
- `adapters` → depends on `ports` and `domain` (implements interfaces)

**Key project conventions:**
- Timer state: in-memory for MVP, SQLite only if persistence becomes necessary
- State sync: WebSockets broadcast from backend to all clients
- NLU: rule-based parser as main path; LLM as optional low-confidence fallback
- ASR: local `faster-whisper` or cloud fallback, both behind a port interface
- Cost controls: paid APIs disabled by default, with daily limits and logging

Guidance:
- Prefer small, testable modules. Highlight high-risk decisions needing review.
- Keep abstractions lean — only add ports for boundaries that genuinely change (ASR provider, LLM provider, storage backend).
- For PWA/mobile client design, keep it independent of the smartwatch. The watch is a companion layer, not a core dependency.
