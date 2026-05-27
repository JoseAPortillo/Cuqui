# Orchestrator Instructions for SDD/TDD

Purpose: coordinate SDD phases, resolve skill selection, and enforce Strict TDD forwarding.

Key behaviors:
- Read `.agent/skills/skill-registry.md` to locate skill paths before delegating.
- For any SDD command, ensure `sdd-init` has been run; if not, run it first.
- Inject the `model` alias and a Skills-to-load section listing exact SKILL.md paths into sub-agent prompts.
- For `sdd-apply` and `sdd-verify`, check project `sdd-init` output for `strict_tdd: true` and forward TDD rules.
- Require sub-agents to `mem_save` significant discoveries, decisions, or bugfixes before returning.

Minimal orchestration flow:
1. Resolve skills from `skill-registry.md`.
2. If task is SDD-phase, ensure dependencies exist (proposal/spec/design/tasks) or run `sdd-init`/`sdd-explore`.
3. Launch sub-agent with `model` alias and the exact skill paths to load.
4. After sub-agent returns, validate `skill_resolution` and `artifacts`, then persist a brief session summary.

Keep this file short — orchestration logic is intentionally compact so sub-agents can read it.
