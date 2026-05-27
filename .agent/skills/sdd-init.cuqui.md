# SDD Init — Cuqui Project

> Generated: 2026-05-27 | Persistence: engram + file artifact

## Project Identity

- **Name**: Cuqui
- **Path**: `D:\CURSOS\CODING\MASTER DESARROLLO CON IA\Cuqui`
- **Type**: Voice-assisted cooking timer system (TFM project)
- **Status**: Greenfield — no source code yet (SDD framework only)

## Stack Detection

| Component | Status | Detail |
|---|---|---|
| **Language** | ✅ Available | Python 3.14.3 (`python`), pip 26.0.1 |
| **Backend Framework** | ⏳ Planned | FastAPI — not installed, no pyproject.toml |
| **Node.js** | ✅ Available | v25.9.0, npm 11.13.0 |
| **Frontend** | ⏳ Planned | PWA (React/Vue/Svelte TBD) — no `package.json` yet |
| **Architecture** | ⏳ Planned | Hexagonal (`domain/`, `application/`, `ports/`, `adapters/`) — not created |
| **Test Runner** | ⏳ Planned | pytest — not installed globally; requires venv + `pip install pytest pytest-asyncio httpx pytest-cov` |
| **Linter / Type Checker / Formatter** | ❌ None | Not installed; recommend `ruff` for all three |
| **Docker** | ✅ Available | Docker v29.4.3 — no `Dockerfile` or `docker-compose.yml` yet |
| **WebSocket** | ⏳ Planned | Per master plan; no dependencies installed |
| **Smartwatch** | ⏳ Planned | Optional Wear OS companion — no Kotlin/Android project files |
| **Deploy Mode** | ⏳ Planned | Docker Compose — not configured |
| **Git** | ❌ Not a git repo | No `.git/` directory |

## Strict TDD

| Field | Value |
|---|---|
| Status | **Enabled** |
| Source | `strict-tdd.SKILL.md` marker in `.agent/skills/` |
| Test Command (planned) | `pytest -v` |
| Headless | Yes (CLI-only, no display required) |

**Note**: pytest is not currently installed. Run `python -m venv .venv && .venv\Scripts\activate && pip install pytest pytest-asyncio httpx pytest-cov` before executing tests.

## Persistence

- **Mode**: Engram (`sdd-init/cuqui` + `sdd/cuqui/testing-capabilities`) + file artifact
- **Engram Observation IDs**: `obs-170cfd26b352dac1` (init), `obs-33bc7f10b5197efb` (testing)
- **File Artifact**: `.agent/skills/sdd-init.cuqui.md`

## Skill Registry

- **Location**: `.atl/skill-registry.md`
- **Status**: Updated — now includes project-level skills from `.agent/skills/`
- **User skills**: Located at `C:\Users\josea\.config\opencode\skills\`

## Next Recommended Steps

1. **Initialize git repo**: `git init` in project root
2. **Create backend skeleton**: Follow hexagonal structure from master plan
3. **Setup Python venv + install dependencies**: `python -m venv .venv && pip install fastapi uvicorn websockets pytest pytest-asyncio httpx pytest-cov`
4. **Create first SDD change**: Run `/sdd-new` to propose the first feature (e.g., "core timer domain and rule-based parser")
5. **Or explore architecture decisions**: Run `/sdd-explore` to discuss stack choices before committing

## Key Risks

| Risk | Impact | Mitigation |
|---|---|---|
| No pytest installed | Tests cannot run | Install in venv as first setup step |
| No git repo | No version control | `git init` immediately |
| Frontend framework undecided | Delays PWA work | Decide React vs Vue vs Svelte early |
| Smartwatch scope creep | TFM timeline risk | Keep watch as companion prototype per plan |
| No linter/formatter | Code quality drift | Add `ruff` to dev dependencies upfront |
