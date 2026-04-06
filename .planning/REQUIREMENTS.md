# Requirements: DMC Grinding GUI

**Defined:** 2026-04-06
**Core Value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion.

## v1.1 Requirements

Requirements for deployment release. Carried forward from v1.0 known gaps.

### Deployment

- [ ] **DEPLOY-01**: App runs in kiosk mode on Raspberry Pi — boots straight into the app with no desktop, browser, or file explorer access
- [ ] **DEPLOY-02**: Kiosk mode is operator-locked — no way to exit the app without Setup/Admin credentials
- [ ] **DEPLOY-03**: Deployment is SD card based — install program on SD card, insert into Pi, app runs on boot
- [ ] **DEPLOY-04**: App also runs on Windows 11 as a standard desktop application
- [ ] **DEPLOY-05**: No external JSON/YAML config files required for deployment — machine config is embedded in the application

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Diagnostics

- **DIAG-01**: Raw controller command terminal for Setup users (send commands, see responses)
- **DIAG-02**: Array viewer showing all tracked DMC arrays and their current values
- **DIAG-03**: Command history log with timestamps

### Enhancements

- **ENH-01**: Axis position units display (mm/degrees instead of raw encoder counts)
- **ENH-02**: Profile metadata embedded in CSV (machine type, date, operator name, notes)
- **ENH-03**: Per-tooth B-axis compensation table with live bar chart (serration-specific)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Password hashing / encryption for PINs | In-house use, no network exposure |
| Remote/network software updates | No network infrastructure; manual SD card swap |
| Multi-language UI | English only |
| Database for profiles | CSV is transparent, portable, Excel-compatible |
| Cloud sync / backup | No network infrastructure |
| Web dashboard / REST API | Standalone controllers, not networked |
| Animated screen transitions | Adds latency on industrial tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | Phase 8 | Pending |
| DEPLOY-02 | Phase 8 | Pending |
| DEPLOY-03 | Phase 8 | Pending |
| DEPLOY-04 | Phase 8 | Pending |
| DEPLOY-05 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0

---
*Requirements defined: 2026-04-06*
*Carried forward from v1.0 known gaps (DEPLOY-01 through DEPLOY-05)*
