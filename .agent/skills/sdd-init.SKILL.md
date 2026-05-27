# sdd-init SKILL

Purpose: detect project stack, testing capabilities, and initialize SDD context for the project.

When to run:
- Automatically at the start of any SDD flow, or when the orchestrator cannot find prior init.

Responsibilities:
- Detect language/runtime (Python/FastAPI, Node, Go, etc.) and common test commands.
- Detect project framework and architecture patterns:
  - **Python/FastAPI**: look for `fastapi` in `requirements.txt`, `pyproject.toml`, or `Pipfile`.
  - **Hexagonal architecture**: look for directory structure `domain/`, `application/`, `ports/`, `adapters/` under backend/.
  - **Test framework**: detect `pytest` via `pytest.ini`, `pyproject.toml` [tool.pytest.ini_options], or `conftest.py`.
  - **Docker**: detect `Dockerfile` or `docker-compose.yml` for deployment reproducibility.
  - **Frontend/PWA**: detect `package.json` with React/Vue/Svelte, `vite.config.*`, or `next.config.*`.
  - **WebSocket**: detect WebSocket usage via `websockets` in Python deps or `ws://` references.
  - **Smartwatch**: detect Wear OS project files (Kotlin, Jetpack Compose) under a watch/ directory.
- Identify recommended test command and whether tests run headlessly.
- Determine `strict_tdd` viability: if pytest is detected and tests can run headlessly, enable it.
- Produce a structured artifact saved to engram/topic `sdd-init/{project}` with:

Output format:
```json
{
  "language": "python",
  "framework": "fastapi",
  "architecture": "hexagonal",
  "test_command": "pytest -v",
  "strict_tdd": true,
  "test_runner_details": "pytest 8.x, coverage available",
  "backend_dir": "backend/",
  "frontend_framework": "svelte",
  "has_docker": true,
  "has_websocket": true,
  "has_watch_prototype": false,
  "deploy_mode": "docker-compose"
}
```

Detection guide for `backend/cuqui/` hexagonal structure:
- `domain/` → timer.py, command.py, session.py
- `application/` → process_command.py, manage_timers.py, sync_state.py
- `ports/` → speech_to_text.py, intent_parser.py, notification.py, storage.py
- `adapters/` → api_fastapi/, parser_rules/, asr_*/ , llm_*/, storage_memory/

Notes for sub-agents:
- If `strict_tdd` is true, include `"STRICT TDD MODE IS ACTIVE"` in apply/verify prompts.
- If `architecture` is `"hexagonal"`, remind sub-agents to follow the layer dependency rules: domain → application → ports → adapters (inward dependencies only).
- Save artifact via `mem_save` with topic_key `sdd-init/{project}` (capture_prompt: false).
