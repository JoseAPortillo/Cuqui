# sdd-apply SKILL

Purpose: implement tasks in small batches, follow tests-first when `strict_tdd` is active.

Responsibilities:
- Read `sdd/{change}/tasks`, `spec`, and `design` before modifying code.
- If prior apply-progress exists, merge progress and continue.
- For each task: create branch, write failing test, implement to pass tests, refactor, commit.
- Save `apply-progress` periodically to engram with task status (in-progress/completed).

Strict TDD forwarding:
- If orchestrator indicates `STRICT TDD MODE IS ACTIVE`, do strict test-first workflow and include test commands.

Output:
- `sdd/{change}/apply-progress` mem_save with per-task status and commit refs.
