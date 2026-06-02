# Design: PWA + Polish — Cuqui Cooking Timer

## Technical Approach

Four isolated concerns, one backend contract addition. PWA layer via `vite-plugin-pwa` injecting manifest + SW. Timer audio as base64 WAV chime gated on user gesture. Control buttons map to existing domain transitions via new REST endpoints. UI polish via React patterns (autoFocus, env guard, meta tags).

---

## Architecture Decisions

### Decision: Direct REST endpoints (not through process_command)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Route through `process_command` + `IntentParser` | Reuses "name lookup" pattern but requires constructing command objects from IDs | **Direct** |
| Call `TimerManager` directly from route handler | Simpler, matches spec intent, avoids unnecessary parse layer | ✅ |

**Rationale**: Pause/resume/cancel by `timer_id` (known from WS state) makes name-lookup in `process_command` redundant. Routes call `manager.pause_timer(sid, tid)` directly, then broadcast the same way `post_command` does.

### Decision: Base64 WAV embedded in bundle for chime

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Fetch from `public/` | One extra network request, cache concern | |
| Base64 WAV string constant | Zero network, no cache worries, works offline | ✅ |

**Rationale**: The chime is ~1 KB as a minimal WAV. Base64-in-JS avoids a fetch dependency and works with the service worker precache automatically if we import the asset URL.

### Decision: `AudioContext` gate for iOS, `new Audio()` for desktop

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Web Audio API everywhere | More complex, but required for iOS | ✅ Hybrid |
| `new Audio()` only | Fails on iOS autoplay | |

**Rationale**: `new Audio(url).play()` works on desktop. On iOS Safari the audio context is suspended until user gesture. We create an `AudioContext` once, attach `resume()` to the first `click/keydown` handler, and play chime through `AudioBufferSourceNode` for iOS, `new Audio()` for others.

---

## Data Flow

```
                    Timer completes (tick_all → WS broadcast)
                              │
                    ┌─────────▼─────────┐
                    │   AlertBanner     │
                    │  detects new alert │
                    └─────────┬─────────┘
                              │ playChime()
                    ┌─────────▼─────────┐
                    │  hasInteracted?   │
                    │    ┌──┴──┐        │
                    │   NO    YES       │
                    │   ↓      ↓        │
                    │  silent  play()   │
                    └──────────────────┘

User clicks Pause ──→ POST /timers/{id}/pause
                            │
                    ┌───────▼────────┐
                    │  session_id    │
                    │  from client   │
                    └───────┬────────┘
                            │
            ┌───────────────▼──────────────┐
            │ TimerManager.pause_timer()   │
            │ returns updated Timer object │
            └───────────────┬──────────────┘
                            │
            ┌───────────────▼──────────────┐
            │ SyncService.broadcast(sid,   │
            │   {timers: full_state})      │
            └───────────────┬──────────────┘
                            │
            ┌───────────────▼──────────────┐
            │ Return updated Timer as JSON │
            └──────────────────────────────┘
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/vite.config.ts` | Modify | Add `vite-plugin-pwa` with manifest, SW config |
| `frontend/index.html` | Modify | Add manifest link, theme-color, apple meta tags |
| `frontend/package.json` | Modify | Add `vite-plugin-pwa` dependency |
| `frontend/public/icons/icon-192.png` | Create | 192×192 PWA icon |
| `frontend/public/icons/icon-512.png` | Create | 512×512 PWA icon |
| `frontend/public/icons/apple-touch-icon.png` | Create | 180×180 iOS icon |
| `frontend/src/hooks/useCuquiApi.ts` | Modify | Add `pauseTimer`, `resumeTimer`, `cancelTimer` methods |
| `frontend/src/components/TimerCard.tsx` | Modify | Add contextual Pause/Resume/Cancel buttons + callbacks |
| `frontend/src/components/TimerDashboard.tsx` | Modify | Pass `onPause`/`onResume`/`onCancel` down from App |
| `frontend/src/components/AlertBanner.tsx` | Modify | Play chime on new alerts with iOS-safe audio |
| `frontend/src/components/CommandInput.tsx` | Modify | Add `autoFocus` with mobile-safe guard |
| `frontend/src/components/DebugPanel.tsx` | Modify | Return `null` when `import.meta.env.PROD` |
| `frontend/src/App.tsx` | Modify | Wire pause/resume/cancel through useCuquiApi, add `useAudioAlert` |
| `backend/.../routes.py` | Modify | Add `POST /timers/{timer_id}/{action}` endpoints |
| `backend/.../schemas.py` | Modify | Add `TimerActionRequest` / `TimerActionResponse` |

---

## Interfaces / Contracts

### Backend — New Endpoints

```
POST /timers/{timer_id}/pause
POST /timers/{timer_id}/resume
POST /timers/{timer_id}/cancel

Request (JSON body):
{
  "session_id": "uuid-string"
}

Response 200:
{
  "id": "timer-uuid",
  "name": "Pasta",
  "duration": 600,
  "remaining": 420,
  "status": "paused",
  "created_at": "2026-06-01T12:00:00"
}

Response 404:
{ "error": "not_found", "message": "Timer not found" }

Response 422:
{ "error": "domain_error", "message": "Cannot pause timer in pending state" }
```

### Frontend — useCuquiApi additions

```typescript
interface CuquiApiState {
  // ... existing fields
  pauseTimer: (timerId: string) => Promise<void>
  resumeTimer: (timerId: string) => Promise<void>
  cancelTimer: (timerId: string) => Promise<void>
}
```

### TimerCard — new props

```typescript
interface TimerCardProps {
  timer: Timer
  onPause: (timerId: string) => void
  onResume: (timerId: string) => void
  onCancel: (timerId: string) => void
  disabled?: boolean  // true while an action is in-flight
}
```

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — domain | Timer state transitions (pause/resume/cancel) | Already tested; verify no regression |
| Unit — commands | Domain command dataclasses | Already exist; no changes needed |
| Integration — API | `POST /timers/{id}/pause` returns correct status, WS broadcasts | FastAPI `TestClient`, mock `SyncService` |
| Integration — API | 404 for unknown timer_id, 422 for invalid transition | Assert error response shape |
| E2E — frontend | Click Pause → timer card shows Resume button | Playwright component test or manual |
| E2E — PWA | `manifest.webmanifest` in build output, SW registered | `vite build` + verify dist/ contents |
| E2E — audio | Chime plays on completion after gesture | Manual (iOS + desktop); `hasInteracted` flag testable via mock |

---

## Migration / Rollout

No migration required. The domain already supports all transitions. New REST endpoints are additive — existing clients (voice commands via `process_command`) are unaffected.

## Open Questions

- [ ] Verify `vite-plugin-pwa` version compatibility with Vite 8 on install
- [ ] Test iOS audio on real device: does `AudioContext.resume()` on `touchend` work reliably?
- [ ] Confirm the exact primary color hex for PWA theme_color (`#4fc3f7`? `#0f0f23`?)
