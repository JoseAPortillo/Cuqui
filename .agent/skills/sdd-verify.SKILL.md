# sdd-verify SKILL

Purpose: validate implementation against spec; run unit/integration tests and report results.

Responsibilities:
- Read `sdd/{change}/spec` and `apply-progress`.
- Run test suite using `sdd-init` discovered `test_command` (typically `pytest -v` for Python/FastAPI backend).
- For NLU-related changes: run the NLU test set and report **accuracy percentage**. The project success metric requires >90% accuracy on the controlled test set.
- Test the full command flow: text command → parser → timer mutation → WebSocket broadcast.
- Produce a `verify-report` enumerating:
  - PASSED/FAILED acceptance scenarios
  - NLU accuracy (if applicable)
  - WebSocket synchronization coverage
  - Flaky tests and remediation recommendations
  - Integration test results (Docker compose if available)

Output:
- Save `sdd/{change}/verify-report` via `mem_save` and return a short executive summary.
