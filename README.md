# Cuqui — Asistente de cocina inteligente por voz

## Descripción general

Cuqui es un asistente de cocina controlado por voz que permite gestionar múltiples temporizadores con nombre mediante comandos en lenguaje natural. Está diseñado como proyecto de TFM para demostrar integración de IA, parseo de lenguaje natural, sincronización en tiempo real, y despliegue reproducible con Docker.

El sistema permite crear, pausar, reanudar, extender, reducir, renombrar y consultar temporizadores usando comandos de voz o texto. La sincronización de estado se realiza mediante WebSockets, y las notificaciones en segundo plano funcionan vía Push API + Service Worker incluso con la pantalla apagada.

## Stack tecnológico

| Capa | Tecnología |
| :--- | :--- |
| **Backend** | Python 3.12+, FastAPI, Uvicorn, WebSockets |
| **Frontend** | React 19, TypeScript, Vite 8 |
| **PWA** | Service Worker (injectManifest), VitePWA, Push API + VAPID |
| **Base de datos** | SQLite (persistencia entre sesiones) |
| **ASR local** | faster-whisper (tiny/base/small) |
| **ASR cloud** | OpenAI Whisper API (fallback opcional) |
| **NLU** | Parser basado en reglas deterministas |
| **LLM fallback** | OpenAI API (solo para comandos de baja confianza) |
| **Notificaciones push** | pywebpush + Web Push Protocol |
| **Contenedor** | Docker Compose (multi-stage build) |
| **Testing** | pytest, pytest-asyncio, httpx, pytest-cov |
| **Linting** | Ruff |

## Instalación y ejecución

### Requisitos

- Docker y Docker Compose (recomendado)
- O Python 3.12+ y Node.js 20+ (desarrollo local)

### Con Docker (recomendado)

```bash
# Construir y levantar
docker compose up --build

# La aplicación estará disponible en http://localhost:8000
```

### Sin Docker (desarrollo)

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev,asr,llm]"
uvicorn cuqui.__main__:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Variables de entorno

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `CUQUI_SERVE_FRONTEND` | Servir el frontend compilado desde el backend | `0` |
| `CUQUI_PORT` | Puerto del servidor | `8000` |
| `CUQUI_RELOAD` | Hot reload en desarrollo | `0` |
| `OPENAI_API_KEY` | API key para ASR/LLM cloud (opcional) | — |
| `VAPID_PUBLIC_KEY` | Clave pública VAPID para push | Se genera automáticamente |
| `VAPID_PRIVATE_KEY` | Clave privada VAPID para push | Se genera automáticamente |
| `VAPID_CLAIM_EMAIL` | Email para VAPID claim | `cuqui@localhost` |

### Notas importantes

- El audio del navegador requiere un contexto seguro: usa `localhost` en desarrollo o HTTPS en producción.
- Las notificaciones push requieren registro de Service Worker (se hace automáticamente al cargar la app).
- La API key de OpenAI es **opcional**; sin ella funciona solo con ASR local (faster-whisper) y parser de reglas.

## Estructura del proyecto

```
cuqui/
├── backend/
│   ├── cuqui/
│   │   ├── __main__.py              # Punto de entrada (uvicorn)
│   │   ├── domain/
│   │   │   ├── timer.py             # Modelo de dominio: Timer, TimerState
│   │   │   ├── commands.py          # Esquemas de comandos (SetTimer, ExtendTimer, etc.)
│   │   │   └── parser.py            # Parser de comandos en lenguaje natural
│   │   ├── application/
│   │   │   ├── manage_timers.py     # Casos de uso: CRUD de temporizadores
│   │   │   ├── process_command.py   # Procesamiento de comandos (texto/audio)
│   │   │   └── sync_state.py        # Sincronización de estado vía WebSocket
│   │   ├── ports/
│   │   │   ├── intent_parser.py     # Puerto: parseo de intenciones
│   │   │   ├── speech_to_text.py    # Puerto: transcripción de audio
│   │   │   ├── push_notification.py # Puerto: notificaciones push
│   │   │   └── storage.py           # Puerto: persistencia
│   │   └── adapters/
│   │       ├── api_fastapi/         # Adaptador HTTP/WS (FastAPI)
│   │       ├── parser_rules/        # Adaptador: parser basado en reglas
│   │       ├── asr_faster_whisper/  # Adaptador: ASR local
│   │       ├── asr_openai/          # Adaptador: ASR cloud (OpenAI)
│   │       ├── push_webpush/        # Adaptador: notificaciones push
│   │       ├── storage_memory/      # Adaptador: almacenamiento en memoria
│   │       └── storage_sqlite/      # Adaptador: almacenamiento SQLite
│   ├── tests/
│   │   ├── unit/                    # Tests unitarios
│   │   └── integration/             # Tests de integración (API, WS)
│   ├── Dockerfile                   # Multi-stage build (frontend + backend)
│   └── pyproject.toml               # Configuración Python
├── frontend/
│   ├── src/
│   │   ├── main.tsx                 # Punto de entrada React
│   │   ├── App.tsx                  # Componente principal
│   │   ├── sw.js                    # Service Worker (push, audio, caché)
│   │   ├── components/
│   │   │   ├── TimerDashboard.tsx   # Panel de temporizadores activos
│   │   │   ├── TimerCard.tsx        # Tarjeta individual de temporizador
│   │   │   ├── AlertBanner.tsx      # Banner de alarmas activas
│   │   │   ├── VoiceButton.tsx      # Botón push-to-talk
│   │   │   ├── CommandInput.tsx     # Entrada de texto para comandos
│   │   │   ├── CommandsHelp.tsx     # Ayuda de comandos disponibles
│   │   │   ├── DebugPanel.tsx       # Panel de depuración (TFM)
│   │   │   └── ApiKeySettings.tsx   # Configuración de API key
│   │   ├── hooks/
│   │   │   ├── useCuquiApi.ts       # Hook de API (REST + WebSocket)
│   │   │   └── useTimerNotifications.ts # Hook de notificaciones
│   │   ├── types/
│   │   │   └── timer.ts             # Tipos TypeScript
│   │   └── utils/
│   │       ├── chime.ts             # Reproducción de sonido de alarma
│   │       └── errorMessages.ts     # Mensajes de error amigables
│   ├── public/
│   │   └── icons/                   # Iconos PWA
│   ├── index.html
│   ├── vite.config.ts               # Configuración Vite + PWA + SSL
│   └── package.json
├── docker-compose.yml               # Orquestación Docker
└── data/                            # Datos persistentes (SQLite, cachés)
```

## Funcionalidades principales

### Temporizadores por voz

- Crear temporizadores con nombre: _"poner 10 minutos a la pasta"_
- Añadir tiempo: _"Añadir 5 minutos al pollo"_
- Reducir tiempo: _"Quitar 2 minutos al arroz"_
- Pausar/reanudar: _"Pausar el pescado"_, _"Reanudar todos los temporizadores"_
- Cancelar: _"Cancelar las patatas"_
- Renombrar: _"Renombrar pasta a spaghetti"_

### Entrada de comandos

- **Voz**: Botón push-to-talk con grabación de micrófono

### Notificaciones en segundo plano

- Notificaciones push con sonido de alarma incluso con la pantalla apagada
- Alarma audible desde el Service Worker mediante Web Audio API (AudioContext)
- Sincronización visual al volver a la aplicación

### Panel de control

- Dashboard con tarjetas de temporizadores activos
- Indicador de sincronización WebSocket en tiempo real
- Sistema de mensajes de error amigables con contexto

### Panel de costos (TFM)

- Visualización del modo de procesamiento (local vs cloud)
- Control de API key de OpenAI (opcional)
- Preparado para registrar uso de APIs de pago

## Usuario y contraseña de prueba

El proyecto **no implementa autenticación**. No requiere usuario ni contraseña. Cada sesión se identifica con un UUID generado automáticamente y almacenado en `localStorage`. No hay datos sensibles ni multiinquilino.

## Licencia

Proyecto académico — TFM.
