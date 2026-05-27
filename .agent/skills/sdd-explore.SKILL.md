# sdd-explore SKILL

Purpose: quick, read-only exploration to collect facts, constraints, and areas impacted by a proposed change.

What to collect:
- Relevant files, entry points, dependencies, data storage, CI/test hooks.
- Existing specs, TODOs, or design notes in the repo.
- Possible risk areas (db, auth, external APIs, long-running jobs).

Output:
- Short findings list and file references saved as `sdd/{change}/explore` via `mem_save`.
- Provide a suggested scope for the proposal (minimal, moderate, large).

Guidance:
- Keep exploration to a few files (3-10). If more required, note that a deeper exploration is needed and return findings.
