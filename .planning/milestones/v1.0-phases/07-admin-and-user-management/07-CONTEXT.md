# Phase 7: Admin and User Management - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin users can create, delete, and update user accounts and PINs from a dedicated screen — no file editing or code changes required. Covers AUTH-07 and AUTH-08 requirements. Does not include diagnostics content, audit logging, or role permission changes beyond the existing three-tier system.

</domain>

<decisions>
## Implementation Decisions

### Screen Location & Access
- New "Users" tab added to tab bar as the 6th (last) tab, after Diagnostics
- Tab order: Run, Axes Setup, Parameters, Profiles, Diagnostics, Users
- Visible to Admin role only — Operator and Setup never see it
- No additional PIN re-entry required; being logged in as Admin is sufficient
- Tab bar ROLE_TABS updated: admin list gets "users" appended

### User List Display
- Card-based layout — one card per user showing name, role badge, and action buttons (Edit, Delete)
- Consistent with card patterns used elsewhere (Parameters screen cards)
- "Add User" button positioned at top-right of the Users screen, always visible

### Edit Flow
- Tap "Edit" on a user card opens a centered modal overlay (reuses PIN overlay pattern)
- Overlay contains fields: Name (text input), PIN (numeric input, masked), Role (selector)
- Save and Cancel buttons on the overlay
- Same overlay pattern used for "Add User" (pre-populated with defaults)

### Delete Behavior
- Tap "Delete" shows confirmation dialog: "Are you sure you want to delete [name]?" with Cancel/Confirm
- Prevents accidental deletions on touchscreen

### PIN Rules
- PIN length: 4-6 digits (enforced on create and edit)
- Duplicate PINs not allowed — show error if PIN is already taken by another user
- PIN displayed as masked dots in the user list; visible in edit overlay for Admin to set

### Role Assignment
- Three roles available: Operator, Setup, Admin (existing three-tier system)
- Default role for new users: Operator (safest default, Admin upgrades explicitly)
- Admin can change their own PIN but cannot change their own role (prevents self-demotion lockout)

### Username Rules
- Usernames must be unique — show error if name already exists
- No character restrictions beyond non-empty (industrial names like "Joe", "Shift-2", etc.)

### Safety Guardrails
- Cannot delete or demote the last Admin user — show error: "At least one Admin must exist"
- Minimum user count: just 1 Admin minimum; all non-Admin users can be deleted
- If currently logged-in user is deleted by another Admin: force logout on next user action (kicked to PIN overlay). No real-time push mechanism needed.
- Factory reset path: delete users.json manually, app recreates defaults on next boot

### Claude's Discretion
- Exact card styling and layout within the Users screen
- Role badge colors and visual design
- Overlay animation/transition details
- Error message exact wording and display duration
- Whether to show PIN in edit overlay as dots with a "show" toggle or plain text

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AuthManager` (src/dmccodegui/auth/auth_manager.py): Has _load(), _save(), user_names, validate_pin(), get_role() — needs create_user(), delete_user(), update_user() methods added
- `PINOverlay` (src/dmccodegui/screens/pin_overlay.py): Fullscreen overlay pattern — reusable as template for edit/create user overlay
- `CardFrame` widget: Rounded card with border — reuse for user cards
- `TabBar.ROLE_TABS` and `TabBar.ALL_TABS`: Need "users" entry added to admin list and ALL_TABS tuple list
- `users.json`: Existing JSON structure with "last_user" and "users" dict — CRUD operations extend this

### Established Patterns
- KV files loaded via `KV_FILES` list in main.py — add ui/users.kv
- Screen classes use `ObjectProperty` for controller/state injection
- Screens exported from screens/__init__.py for Kivy Factory registry
- Modal overlays (PINOverlay) added/removed from root layout dynamically
- Background operations use jobs.submit() + Clock.schedule_once() pattern

### Integration Points
- `TabBar.ALL_TABS`: Add ("users", "Users") tuple
- `TabBar.ROLE_TABS["admin"]`: Append "users" to admin's allowed tabs
- `screens/__init__.py`: Export new UsersScreen
- `ui/base.kv`: Add UsersScreen to ScreenManager with name: 'users'
- `main.py KV_FILES`: Add "ui/users.kv"
- `AuthManager`: Extend with CRUD methods (create_user, delete_user, update_user) + uniqueness validation

</code_context>

<specifics>
## Specific Ideas

- Reuse the existing overlay pattern from PINOverlay for the create/edit user form — keeps the app feeling consistent
- Card layout for user list matches the card-based approach used in Parameters — visual consistency across Setup/Admin screens
- Force-logout-on-next-action is the simplest safe approach; avoids needing a real-time event system between screens

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-admin-and-user-management*
*Context gathered: 2026-04-06*
