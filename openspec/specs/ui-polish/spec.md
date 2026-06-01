# UI Polish Specification

## Purpose

Minor frontend improvements for production-readiness: auto-focus the command input, hide the debug panel in production, and set the theme-color meta tag.

## Requirements

### Requirement: CommandInput Auto-Focus

The CommandInput component SHALL auto-focus when mounted on desktop viewports. On mobile, auto-focus SHALL NOT open the virtual keyboard automatically at page load.

#### Scenario: Desktop auto-focus

- GIVEN a desktop browser loading the app
- WHEN the CommandInput renders
- THEN the input SHALL have DOM focus
- AND the cursor SHALL be visible in the text field

#### Scenario: Mobile no keyboard pop

- GIVEN a mobile device (touchscreen)
- WHEN the CommandInput renders on initial page load
- THEN the input MAY have focus
- BUT the virtual keyboard SHALL NOT open

### Requirement: DebugPanel Hidden in Production

The DebugPanel component SHALL render nothing (return null) when `import.meta.env.PROD` is true. In development mode, it SHALL remain visible.

#### Scenario: DebugPanel absent in production build

- GIVEN a production build (`vite build` + serve)
- WHEN the app renders
- THEN the DebugPanel DOM node SHALL NOT exist
- AND no debug data SHALL be visible to the end user

#### Scenario: DebugPanel visible in dev

- GIVEN a developer running `vite dev`
- WHEN the app renders
- THEN the DebugPanel SHALL be visible with timer state info

### Requirement: theme-color Meta Tag

`index.html` SHALL include a `<meta name="theme-color">` tag matching the app's primary color. The value SHALL be a valid CSS hex color.

#### Scenario: theme-color present

- GIVEN `index.html`
- WHEN parsed
- THEN a `<meta name="theme-color" content="#...">` SHALL exist
- AND the color SHALL match the manifest `theme_color`

## Non-requirements

- Dark mode toggle
- Animated transitions or micro-interactions
- Responsive layout changes beyond auto-focus behavior

## Edge Cases

| Edge Case | Expected Behavior |
|-----------|------------------|
| CommandInput rendered multiple times (re-insertion) | Auto-focus SHALL fire on each mount |
| DebugPanel manually toggled in dev | No requirement; current visibility logic is acceptable |
| theme-color changed via user preference | Not supported — single static value is sufficient |
