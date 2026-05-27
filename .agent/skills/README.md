# SDD/TDD Skills — README

Purpose
- This folder contains orchestration instructions and SKILL.md files used to run Spec-Driven Development (SDD) and Strict TDD workflows via agent orchestration.

Files
- `skill-registry.md`: lookup table of skill names → SKILL.md paths
- `orchestrator.instructions.md`: lightweight orchestrator rules the agent follows
- `*.SKILL.md`: phase-specific skill definitions (sdd-init, sdd-explore, sdd-propose, sdd-spec, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive, strict-tdd)

Quick Usage
- Ensure the orchestrator reads `skill-registry.md` before delegating to sub-agents.
- Run `sdd-init` first to detect test commands and `strict_tdd` status.

Manual: run `sdd-init` via the agent (recommended) or inspect repo files to determine test command.

Best Practices
- Keep tasks small and reviewable (<400 LOC) to make PRs focused.
- If `strict_tdd` is enabled, `sdd-apply` must follow test-first steps in `strict-tdd.SKILL.md`.
- Sub-agents must `mem_save` important discoveries with stable `topic_key`s.

Example Agent Prompts
- "Run `sdd-init` for project and save testing capabilities to engram."
- "Run `sdd-explore` for change `auth-refresh` and return files impacted."
- "Run `sdd-apply` for task 1 from `sdd/auth-refresh/tasks` with strict TDD enabled."

Where to start
- Open [orchestrator.instructions.md](.agent/skills/orchestrator.instructions.md) and [skill-registry.md](.agent/skills/skill-registry.md) to see how skills are wired.
