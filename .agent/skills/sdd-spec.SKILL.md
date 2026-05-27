# sdd-spec SKILL

Purpose: translate proposal into a verifiable specification with acceptance criteria and scenarios.

Spec structure:
- Feature summary
- Actors and preconditions
- Scenarios (Given/When/Then) — at least one happy-path and 1-2 edge cases
- Non-functional requirements (performance, security)
- Acceptance tests mapping (test ids or commands)

Output:
- Spec saved to `sdd/{change}/spec` via `mem_save` (capture_prompt: false).

Guidance:
- Each scenario should map to automated tests where possible.
