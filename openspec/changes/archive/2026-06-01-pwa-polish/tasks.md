# Tasks: PWA + Polish — Cuqui Cooking Timer

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180–240 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

## Phase 1: Foundation — PWA Manifest & Icons

- [x] 1.1 Add `vite-plugin-pwa` to `frontend/package.json` dependencies
- [x] 1.2 Configure Vite PWA plugin in `frontend/vite.config.ts` with manifest (`name: "Cuqui"`, `short_name: "Cuqui"`, `theme_color: "#4fc3f7"`, `background_color: "#0f0f23"`, `display: standalone`), precache SW with skipWaiting in dev
- [x] 1.3 Create `frontend/public/icons/icon-192.png` (192×192 SVG-based PNG)
- [x] 1.4 Create `frontend/public/icons/icon-512.png` (512×512 SVG-based PNG)
- [x] 1.5 Create `frontend/public/icons/apple-touch-icon.png` (180×180)
- [x] 1.6 Update `frontend/index.html`: add `<link rel="manifest">`, `<meta name="theme-color" content="#4fc3f7">`, `<meta name="apple-mobile-web-app-capable" content="yes">`, `<link rel="apple-touch-icon">`

## Phase 2: Backend — Timer Control Endpoints

- [x] 2.1 Add `TimerActionRequest` schema to `backend/cuqui/adapters/api_fastapi/schemas.py`
- [x] 2.2 Add `POST /timers/{timer_id}/pause`, `/resume`, `/cancel` to `backend/cuqui/adapters/api_fastapi/routes.py` — each receives `session_id`, calls `TimerManager.pause_timer/resume_timer/cancel_timer`, broadcasts via `SyncService`, returns updated timer dict; 404 on unknown timer, 422 on invalid transition

## Phase 3: Frontend — Control Buttons

- [x] 3.1 Add `pauseTimer`, `resumeTimer`, `cancelTimer` methods to `frontend/src/hooks/useCuquiApi.ts` — POST to new endpoints, merge response into timers state
- [x] 3.2 Update `frontend/src/components/TimerCard.tsx`: accept `onPause`/`onResume`/`onCancel` props + `disabled`; render contextual buttons (running→Pause+Cancel, paused→Resume+Cancel, completed/cancelled→none); disable during request
- [x] 3.3 Update `frontend/src/components/TimerDashboard.tsx`: pass `onPause`/`onResume`/`onCancel` through to TimerCard
- [x] 3.4 Update `frontend/src/App.tsx`: wire `pauseTimer`/`resumeTimer`/`cancelTimer` from `useCuquiApi` into TimerDashboard

## Phase 4: Audio Alert Chime

- [x] 4.1 Add base64-encoded chime WAV constant (`frontend/src/utils/chime.ts`) + playback logic to `AlertBanner.tsx`; gate on `hasInteracted` flag; play only on new completions

## Phase 5: UI Polish

- [x] 5.1 Add `autoFocus` with mobile-safe guard (avoid keyboard pop on touch devices) to `frontend/src/components/CommandInput.tsx`
- [x] 5.2 Return `null` when `import.meta.env.PROD` in `frontend/src/components/DebugPanel.tsx`

## Phase 6: Verify

- [x] 6.1 Verify `vite build` succeeds and `dist/manifest.webmanifest` + SW are present
- [x] 6.2 Verify Pause→Resume→Cancel buttons render contextually and trigger correct API calls
- [x] 6.3 Verify 404 for unknown timer_id, 422 for invalid transition (12 new tests, 287/287 pass)
- [x] 6.4 Verify DebugPanel absent in production build, CommandInput auto-focuses on desktop
- [x] 6.5 Test audio chime on timer completion (manual: desktop + iOS)
