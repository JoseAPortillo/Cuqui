# strict-tdd SKILL

Purpose: define the strict TDD rules and checklist used by `sdd-apply` and `sdd-verify` when active.

Rules (must-follow):
1. Write the failing automated test first (unit or integration depending on scope).
2. Run the single failing test; confirm it fails for expected reason.
3. Implement the minimal code to make the test pass.
4. Run the full test suite locally; fix regressions.
5. Refactor for clarity and performance; keep tests green.
6. Commit with conventional message and push branch for review.

## Test runner: pytest (Python/FastAPI project)

This project uses **pytest** as the test runner for the backend. All test commands follow this convention:

```bash
# Run all tests
pytest -v

# Run a specific test file
pytest -v backend/tests/test_timer.py

# Run with coverage
pytest -v --cov=backend/cuqui

# Run NLU accuracy test set (when available)
pytest -v backend/tests/test_nlu_accuracy.py
```

**Test structure conventions:**
- Unit tests: `backend/tests/unit/` — domain logic, parser, commands
- Integration tests: `backend/tests/integration/` — API endpoints, WebSocket, full command flow
- NLU accuracy tests: `backend/tests/test_nlu_accuracy.py` — controlled test set with accuracy reporting

**TDD cycle for Cuqui:**
1. Backend domain tests use pure pytest (no FastAPI dependency) — fastest feedback
2. API/WebSocket tests use `httpx` + `pytest-asyncio` for async endpoint testing
3. Always test the command → parser → timer mutation path before the API layer

Notes:
- The `sdd-init` skill must communicate the canonical `test_command` and any environment setup needed to run tests.
- For CI-heavy projects, include guidance on caching and test parallelization to speed feedback.
