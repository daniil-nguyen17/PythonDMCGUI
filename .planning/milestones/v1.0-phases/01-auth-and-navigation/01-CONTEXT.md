# Phase 1: Auth and Navigation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

PIN-based login with three-tier roles (Operator/Setup/Admin), persistent tab bar replacing ActionBar+Spinner, persistent status bar with connection/user/E-STOP info. Existing screens removed and replaced with empty tab placeholders. Connection screen preserved as pre-login step. No screen content is built here — that's Phases 2-4.

</domain>

<decisions>
## Implementation Decisions

### PIN Entry UI
- Fullscreen dark overlay covers entire app on startup — nothing accessible until PIN entered
- Phone-style 3x4 numpad (1-9 top, 0 bottom center, backspace and enter)
- Large 44dp+ numpad buttons for touchscreen
- PIN digits shown as dots (masked)
- Pre-select last logged-in user on startup (name shown at top of overlay)
- "Switch User" available to pick a different name from a list
- Tap user name in status bar to open PIN overlay for switching users
- Reuse same fullscreen PIN overlay for Setup role unlock on restricted tabs

### User Storage
- Plain JSON file (users.json) alongside the app
- PINs stored in plain text (per project scope — no encryption needed for in-house use)
- Kiosk mode (Phase 8) blocks file access on Pi; Windows machines are trusted in-house

### Default Users on First Boot
- When users.json doesn't exist, create three default users:
  - Admin (PIN: 0000)
  - Operator (PIN: 1234)
  - Setup (PIN: 5678)
- Admin can change PINs and manage users in Phase 7

### PIN Feedback & Errors
- Wrong PIN: shake animation + clear dots + "Invalid PIN" message for 2 seconds
- No lockout — operator can retry immediately after wrong PIN
- Numpad button tap: color change highlight (standard Kivy press behavior), no sound
- No attempt counting or brute-force protection (in-house use, not network-exposed)

### Role Switching Flow
- Setup user taps restricted tab -> same fullscreen PIN overlay appears -> enter Setup PIN -> tab unlocks
- Silent auto-lock after 30 minutes of no touch input (grind stone changes take time)
- On auto-lock: stay on current screen, restrict to Operator view; if on restricted tab, switch to Run tab
- No warning before auto-lock — Setup user re-enters PIN to continue

### Tab Bar & Navigation
- Tab bar positioned at TOP of screen, below the status bar
- Icon + text style tabs (icon above label)
- Four tabs: Run, Axes Setup, Parameters, Diagnostics
- Role-aware visibility:
  - Operator: Run only
  - Setup: Run + Axes Setup + Parameters
  - Admin: All tabs (Run + Axes + Parameters + Diagnostics)
- Active tab highlighted with accent color
- Tab bar height: 48dp

### Top Status Bar
- Persistent top bar (48dp) above tab bar
- Layout: Connection status (left) | User name + role badge (left-center) | Banner ticker (center/fill) | E-STOP button (right)
- E-STOP: red, top-right corner, always visible, isolated from other controls
- Connection status: green dot + machine name when connected, red indicator when disconnected
- Tap user name/role area to open PIN overlay for user switching

### Startup Flow
- Boot -> auto-connect to DMC_ADDRESS or first discovered controller
- If auto-connect succeeds: skip connection screen, go straight to PIN overlay
- If auto-connect fails: show connection screen (address discovery + manual connect)
- After connection + PIN login: show tab UI

### Existing Screens
- Remove all 7 old screens (Setup/connection screen preserved separately as pre-login flow)
- Create empty placeholder screens for each tab (Run, Axes Setup, Parameters, Diagnostics)
- Old screens: Rest, Start, AxisD, Params, Buttons & Switches, Serration Knife — all removed
- Setup (connection) screen: preserved as pre-login step, not part of tab structure
- Disconnect mid-session returns to connection screen (must reconnect before accessing tabs)

### Theme & Touch (carried from requirements)
- Dark theme (existing BG_DARK navy palette from theme.kv)
- Axis accent colors: A=orange, B=purple, C=cyan, D=yellow
- All interactive elements 44dp+ minimum touch targets
- No animated transitions — instant screen switches

### Claude's Discretion
- Exact icon choices for tab buttons
- PIN overlay visual design details (background opacity, card styling)
- Banner ticker scroll behavior and timing
- Connection screen layout within the existing pattern
- Exact accent color shade for active tab indicator

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `theme.kv`: Dark palette (BG_DARK, BG_PANEL, BG_ROW, BORDER) and shared widget styles — reuse for all new UI
- `CardFrame` widget: Rounded card with border — could be used for PIN overlay card
- `CenteredTextInput`: Styled text input — could be adapted for PIN display
- `MachineState` dataclass: Subscribe/notify pattern — extend with auth fields (current_user, role, etc.)
- `jobs.submit()` + `Clock.schedule_once()` threading pattern — reuse for any async auth operations

### Established Patterns
- KV files loaded in order in `main.py` (`KV_FILES` list), `base.kv` always last
- `controller` and `state` injected into screens post-build in `DMCApp.build()`
- `SomeMenu_ActionBar` is the current nav — will be fully replaced
- Screen classes use `ObjectProperty` for controller/state injection
- `on_kv_post`, `on_pre_enter`, `on_leave` lifecycle hooks used in screens

### Integration Points
- `RootLayout` in base.kv: entire layout restructure needed (status bar + tab bar + screen manager)
- `DMCApp.build()`: screen injection loop needs updating for new screens
- `DMCApp.e_stop()`: E-STOP logic exists — wire to new button location
- `DMCApp.disconnect_and_refresh()`: disconnect flow exists — integrate with return-to-connection behavior
- `app_state.py`: needs auth fields added to MachineState (or separate AuthState)

</code_context>

<specifics>
## Specific Ideas

- Connection screen auto-connects and skips if successful — operator never sees it in normal workflow
- 30-minute auto-lock timeout chosen because Setup personnel sometimes have to change the grind stone (physical maintenance between parameter adjustments)
- Three default users ship out of the box so the app is usable immediately on first boot without admin setup

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-auth-and-navigation*
*Context gathered: 2026-04-04*
