# Cuqui — Voice-Controlled Smart Cooking Assistant

## Overview

Cuqui is a voice-controlled cooking assistant that manages multiple named timers through natural language commands. It is designed as a TFM (Master's Thesis) project to demonstrate AI integration, natural language parsing, real-time synchronization, and reproducible deployment with Docker.

The system supports creating, pausing, resuming, extending, reducing, renaming, and checking timers using voice or text commands. State synchronization happens via WebSockets, and background notifications work through the Push API + Service Worker even when the screen is off.

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.12+, FastAPI, Uvicorn, WebSockets |
| **Frontend** | React 19, TypeScript, Vite 8 |
| **PWA** | Service Worker (injectManifest), VitePWA, Push API + VAPID |
| **Database** | SQLite (session persistence) |
| **Local ASR** | faster-whisper (tiny/base/small) |
| **Cloud ASR** | OpenAI Whisper API (optional fallback) |
| **NLU** | Deterministic rule-based parser |
| **LLM fallback** | OpenAI API (low-confidence commands only) |
| **Push notifications** | pywebpush + Web Push Protocol |
| **Container** | Docker Compose (multi-stage build) |
| **Testing** | pytest, pytest-asyncio, httpx, pytest-cov |
| **Linting** | Ruff |

## Installation & Setup

### Requirements

- Docker and Docker Compose (recommended)
- Or Python 3.12+ and Node.js 20+ (local development)

### With Docker (recommended)

```bash
# Build and start
docker compose up --build

# The app will be available at http://localhost:8000
```

### Without Docker (development)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev,asr,llm]"
uvicorn cuqui.__main__:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `CUQUI_SERVE_FRONTEND` | Serve compiled frontend from the backend | `0` |
| `CUQUI_PORT` | Server port | `8000` |
| `CUQUI_RELOAD` | Hot reload in development | `0` |
| `OPENAI_API_KEY` | API key for cloud ASR/LLM (optional) | — |
| `VAPID_PUBLIC_KEY` | VAPID public key for push notifications | Auto-generated |
| `VAPID_PRIVATE_KEY` | VAPID private key for push notifications | Auto-generated |
| `VAPID_CLAIM_EMAIL` | Email for VAPID claim | `cuqui@localhost` |

### Important Notes

- Browser audio capture requires a secure context: use `localhost` for development or HTTPS in production.
- Push notifications require Service Worker registration (happens automatically on app load).
- The OpenAI API key is **optional**; without it the app works with local ASR (faster-whisper) and the rule-based parser only.

## Project Structure

```
cuqui/
├── backend/
│   ├── cuqui/
│   │   ├── __main__.py              # Entry point (uvicorn)
│   │   ├── domain/
│   │   │   ├── timer.py             # Domain model: Timer, TimerState
│   │   │   ├── commands.py          # Command schemas (SetTimer, ExtendTimer, etc.)
│   │   │   └── parser.py            # Natural language command parser
│   │   ├── application/
│   │   │   ├── manage_timers.py     # Use cases: timer CRUD
│   │   │   ├── process_command.py   # Command processing (text/audio)
│   │   │   └── sync_state.py        # WebSocket state synchronization
│   │   ├── ports/
│   │   │   ├── intent_parser.py     # Port: intent parsing
│   │   │   ├── speech_to_text.py    # Port: audio transcription
│   │   │   ├── push_notification.py # Port: push notifications
│   │   │   └── storage.py           # Port: persistence
│   │   └── adapters/
│   │       ├── api_fastapi/         # HTTP/WS adapter (FastAPI)
│   │       ├── parser_rules/        # Adapter: rule-based parser
│   │       ├── asr_faster_whisper/  # Adapter: local ASR
│   │       ├── asr_openai/          # Adapter: cloud ASR (OpenAI)
│   │       ├── push_webpush/        # Adapter: push notifications
│   │       ├── storage_memory/      # Adapter: in-memory storage
│   │       └── storage_sqlite/      # Adapter: SQLite storage
│   ├── tests/
│   │   ├── unit/                    # Unit tests
│   │   └── integration/             # Integration tests (API, WS)
│   ├── Dockerfile                   # Multi-stage build (frontend + backend)
│   └── pyproject.toml               # Python config
├── frontend/
│   ├── src/
│   │   ├── main.tsx                 # React entry point
│   │   ├── App.tsx                  # Main component
│   │   ├── sw.js                    # Service Worker (push, audio, cache)
│   │   ├── components/
│   │   │   ├── TimerDashboard.tsx   # Active timers panel
│   │   │   ├── TimerCard.tsx        # Individual timer card
│   │   │   ├── AlertBanner.tsx      # Active alarm banners
│   │   │   ├── VoiceButton.tsx      # Push-to-talk button
│   │   │   ├── CommandInput.tsx     # Text command input
│   │   │   ├── CommandsHelp.tsx     # Available commands help
│   │   │   ├── DebugPanel.tsx       # Debug panel (TFM demo)
│   │   │   └── ApiKeySettings.tsx   # API key configuration
│   │   ├── hooks/
│   │   │   ├── useCuquiApi.ts       # API hook (REST + WebSocket)
│   │   │   └── useTimerNotifications.ts # Notification hook
│   │   ├── types/
│   │   │   └── timer.ts             # TypeScript types
│   │   └── utils/
│   │       ├── chime.ts             # Alarm sound playback
│   │       └── errorMessages.ts     # User-friendly error messages
│   ├── public/
│   │   └── icons/                   # PWA icons
│   ├── index.html
│   ├── vite.config.ts               # Vite + PWA + SSL config
│   └── package.json
├── docker-compose.yml               # Docker orchestration
└── data/                            # Persistent data (SQLite, caches)
```

## Features

### Voice-Controlled Timers

- Create named timers: _"set 10 minutes for pasta"_
- Add time: _"add 5 minutes to the chicken"_
- Reduce time: _"reduce rice by 2 minutes"_
- Pause/resume: _"pause the fish"_, _"resume all timers"_
- Cancel: _"cancel the potatoes"_
- Rename: _"rename pasta to spaghetti"_

### Command Input

- **Voice**: Push-to-talk button with microphone recording
- **Text**: Text input field for typed commands

### Background Notifications

- Push notifications with alarm sound even when the screen is off
- Audible alarm from the Service Worker via Web Audio API (AudioContext)
- Visual sync when returning to the app

### Control Panel

- Dashboard with active timer cards
- Real-time WebSocket connection indicator
- Context-aware user-friendly error messages

### Cost Panel (TFM Demo)

- Processing mode display (local vs cloud)
- OpenAI API key control (optional)
- Ready for paid API usage tracking

## Test Credentials

The project **does not implement authentication**. No username or password required. Each session is identified by an auto-generated UUID stored in `localStorage`. No sensitive data or multi-tenancy.

## License

Academic project — TFM.
