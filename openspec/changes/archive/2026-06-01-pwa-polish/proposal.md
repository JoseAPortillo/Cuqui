# Proposal: PWA + Polish — Cuqui Cooking Timer

## Intent

The app is not installable (no PWA manifest/SW), has no audible timer-completion alert, no manual pause/resume/cancel controls, and has rough edges (no auto-focus, DebugPanel visible in prod). These block public demo readiness.

## Scope

### In Scope
- PWA manifest + service worker via vite-plugin-pwa (Vite 8 compatible)
- Timer completion chime (iOS-safe, user-gesture gated)
- Backend REST endpoints: POST /timers/{id}/pause, /resume, /cancel
- Frontend pause/resume/cancel in useCuquiApi + TimerCard buttons
- Auto-focus CommandInput, hide DebugPanel in production

### Out of Scope
- Push notifications, background sync, custom install prompt, advanced Workbox caching

## Capabilities

### New Capabilities
- `pwa-manifest`: PWA installability (manifest, SW, icons, index.html meta)
- `timer-audio-alert`: Completion chime with iOS autoplay handling
- `timer-control-buttons`: Manual pause/resume/cancel on TimerCard

### Modified Capabilities
- `timer-api`: New endpoints `POST /timers/{id}/pause|resume|cancel` + WS broadcast
- `timer-domain`: No change (domain already handles pause/resume/cancel)
- `timer-manager`: No change (manager already has pause_timer, resume_timer, cancel_timer)

## Approach

**PWA**: Add `vite-plugin-pwa` to vite.config.ts with manifest (name="Cuqui", theme_color, icons). Generate 192x192 + 512x512 PNGs + apple-touch-icon. Update index.html: manifest link, theme-color meta, apple meta tags. Default precache SW.

**Timer audio**: Generate short chime (base64 WAV). Play via `new Audio()` in AlertBanner when alerts appear. Track `hasInteracted` flag; gate playback on first user gesture. iOS: use Web Audio context resumed by gesture event.

**Pause/Resume/Cancel API**: Add `POST /timers/{timer_id}/{action}` to `routes.py`. Each calls existing `TimerManager.pause/resume/cancel_timer`, broadcasts full state via SyncService. No parser needed — direct action by ID.

**Frontend controls**: `useCuquiApi` gets `pauseTimer(id)`, `resumeTimer(id)`, `cancelTimer(id)` — POST to new endpoints. TimerCard receives callbacks, renders contextual buttons per status. Terminal states show none.

**Polish**: CommandInput uses `autoFocus` prop. DebugPanel: `import.meta.env.PROD && null`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/vite.config.ts` | Modified | Add vite-plugin-pwa + manifest |
| `frontend/index.html` | Modified | PWA meta tags |
| `frontend/package.json` | Modified | Add dep: vite-plugin-pwa |
| `frontend/public/icons/` | New | 192/512 PNGs + apple-touch-icon |
| `frontend/src/components/TimerCard.tsx` | Modified | Pause/Resume/Cancel buttons |
| `frontend/src/components/AlertBanner.tsx` | Modified | Chime playback |
| `frontend/src/components/CommandInput.tsx` | Modified | autoFocus |
| `frontend/src/components/DebugPanel.tsx` | Modified | Hide in production |
| `frontend/src/hooks/useCuquiApi.ts` | Modified | Add pause/resume/cancel |
| `backend/.../routes.py` | Modified | New pause/resume/cancel endpoints |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| vite-plugin-pwa incompatible with Vite 8 | Low | Verify on install, pin version |
| iOS audio silent (autoplay restriction) | Medium | Gate on user gesture, Web Audio resume |
| SW caching breaks dev HMR | Low | Configure dev SW with skipWaiting |

## Rollback

`git revert` the merge commit + `npm uninstall vite-plugin-pwa` + `git rm public/icons/`.

## Dependencies

- `vite-plugin-pwa` (verify Vite 8 compat before install)
- Domain timer already supports all needed transitions

## Success Criteria

- [ ] `vite build` succeeds; served app shows "Add to Home Screen" on mobile
- [ ] Timer completion plays audible chime on desktop and iOS
- [ ] Pause/Resume/Cancel buttons appear contextually and trigger correct transitions
- [ ] CommandInput auto-focuses on mount; DebugPanel absent in production build
- [ ] All existing backend tests pass
