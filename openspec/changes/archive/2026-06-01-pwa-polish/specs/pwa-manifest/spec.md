# PWA Manifest Specification

## Purpose

Make Cuqui installable as a Progressive Web App: manifest, service worker, and icons for "Add to Home Screen" on mobile devices.

## Requirements

### Requirement: Web App Manifest

The build output SHALL include a `manifest.webmanifest` with `name`, `short_name`, `start_url`, `display: standalone`, `theme_color`, `background_color`, and icon references. A `<link rel="manifest">` SHALL exist in `index.html`.

#### Scenario: Manifest present on build

- GIVEN a production build via `vite build`
- WHEN inspecting `dist/index.html`
- THEN it SHALL contain `<link rel="manifest" href="/manifest.webmanifest">`
- AND `dist/manifest.webmanifest` SHALL be a valid JSON with all required fields

#### Scenario: Install prompt on mobile

- GIVEN a mobile device (Android Chrome)
- WHEN navigating to the deployed app
- THEN the browser SHALL fire the `beforeinstallprompt` event
- AND the user SHALL see "Add to Home Screen" in the browser menu

### Requirement: Service Worker

A service worker SHALL be registered on page load. It SHALL precache app shell assets (HTML, JS, CSS, icons) for offline access and SHALL use a skip-waiting strategy in dev to avoid HMR interference.

#### Scenario: Service worker registered

- GIVEN a user loads the app
- WHEN `navigator.serviceWorker` is checked
- THEN a service worker SHALL be registered for the origin
- AND the app SHALL load without network on a subsequent visit (offline)

#### Scenario: Dev HMR not broken

- GIVEN a developer running `vite dev`
- WHEN the service worker activates
- THEN the `skipWaiting` handler SHALL prevent stale asset caching
- AND hot-module reloads SHALL continue to work

### Requirement: Icons

The app SHALL ship with a 192×192 PNG and a 512×512 PNG for the manifest, plus a 180×180 `apple-touch-icon` for iOS Safari.

#### Scenario: Icons exist at known paths

- GIVEN a production build
- WHEN checking `dist/icons/`
- THEN `icon-192.png`, `icon-512.png`, and `apple-touch-icon.png` SHALL exist
- AND each SHALL be a valid PNG of the correct dimensions

#### Scenario: iOS home screen icon

- GIVEN an iOS device (Safari)
- WHEN the user adds the page to the home screen
- THEN the icon SHALL be the `apple-touch-icon` (180×180)
- AND no placeholder or generic icon SHALL appear

### Requirement: Theming Meta Tags

`index.html` SHALL include `<meta name="theme-color">` and `<meta name="apple-mobile-web-app-capable" content="yes">`. The theme-color SHALL match the manifest theme_color.

#### Scenario: Meta tags present

- GIVEN `index.html`
- WHEN parsed as HTML
- THEN `theme-color` meta, `apple-mobile-web-app-capable` meta, and `apple-touch-icon` link SHALL be present

## Non-requirements

- Custom install prompt UI — browser default is sufficient
- Background sync or periodic sync — deferred
- Advanced Workbox runtime caching strategies — default precache only

## Edge Cases

| Edge Case | Expected Behavior |
|-----------|------------------|
| iOS Safari does not support `beforeinstallprompt` | App SHALL still function; no install prompt, but `apple-mobile-web-app-capable` enables fullscreen |
| Manifest fetch fails (404) | App SHALL load normally without PWA features; no crash |
| Service worker registration fails (HTTP/HTTPS mismatch) | App SHALL function without offline support |
