"""SerrationParametersScreen -- grouped-card parameter editor with dirty tracking and validation.

Replaces the old placeholder grid with:
  - 5 groups: Geometry, Feedrates, Calibration, Positions, Safety
  - Immediate validation (red=invalid, amber=modified)
  - Batch apply to controller with read-back and NV burn
  - Role-based readonly (Operator cannot edit)
  - Dynamic PARAM_DEFS per machine type from machine_config

Serration variant: uses _SERRATION_PARAM_DEFS (no D-axis vars).
"""
from __future__ import annotations

from kivy.clock import Clock
from kivy.properties import BooleanProperty, NumericProperty

import dmccodegui.machine_config as mc
from ..base import BaseParametersScreen

# ---------------------------------------------------------------------------
# Backward-compatible PARAM_DEFS re-export
# ---------------------------------------------------------------------------
# machine_config is now the authoritative source for parameter definitions.
# PARAM_DEFS is kept as a module-level name for test compatibility and any
# external code that imports it — it always reflects the Serration defaults
# (no D-axis vars) from machine_config._SERRATION_PARAM_DEFS.
# At runtime, SerrationParametersScreen uses mc.get_param_defs() to get the active type's defs.
from dmccodegui.machine_config import _SERRATION_PARAM_DEFS as PARAM_DEFS  # noqa: F401

# ---------------------------------------------------------------------------
# Validation constants kept as module-level names for backward compatibility
# ---------------------------------------------------------------------------

# Groups that reject zero values (calibration params)
_ZERO_REJECT_GROUPS = {"Calibration"}

# Groups that reject negative values
_NEGATIVE_REJECT_GROUPS = {"Feedrates", "Calibration"}

# Border color constants
BORDER_NORMAL = [0.118, 0.145, 0.188, 1]
BORDER_AMBER = [0.980, 0.749, 0.043, 0.9]
BORDER_RED = [0.900, 0.200, 0.200, 0.9]

# Group accent colors for card headers and left-edge stripe
# Consistent across all machine types (same physical meaning per group name)
GROUP_COLORS: dict[str, list[float]] = {
    "Geometry":    [0.980, 0.569, 0.043, 1],   # orange
    "Feedrates":   [0.024, 0.714, 0.831, 1],   # cyan
    "Calibration": [0.659, 0.333, 0.965, 1],   # purple
    "Info":        [0.2, 0.9, 0.3, 1],          # green
}


class SerrationParametersScreen(BaseParametersScreen):
    """Parameters screen with grouped cards, dirty tracking, validation, and batch apply.

    Serration variant: parameter definitions come from _SERRATION_PARAM_DEFS
    (D-axis vars excluded) plus numSerr.

    Inherits controller/state ObjectProperties, build_param_cards, validate_field,
    dirty tracking, apply_to_controller, read_from_controller, and setup-mode lifecycle
    from BaseParametersScreen.
    """

    # Screen-specific KV properties
    pending_count = NumericProperty(0)
    _loading = BooleanProperty(False)

    # ---------------------------------------------------------------------------
    # Field change handler — override base to update pending_count
    # ---------------------------------------------------------------------------

    def on_field_text_change(self, var_name: str, text: str) -> None:
        """Called by KV on_text bindings when a field value changes.

        Extends base class to also update pending_count (KV-bound dirty counter).
        """
        super().on_field_text_change(var_name, text)
        self.pending_count = len(self._dirty)

    # ---------------------------------------------------------------------------
    # Apply button visual gate
    # ---------------------------------------------------------------------------

    def _update_apply_button(self) -> None:
        """Disable Apply button when motion is active or disconnected."""
        apply_btn = getattr(self, '_apply_btn', None)
        if apply_btn is None:
            # Try to find it via ids
            try:
                apply_btn = self.ids.get('apply_btn')
            except Exception:
                return
            if apply_btn is None:
                return
        if self.state is None:
            motion_active = False
        else:
            from dmccodegui.hmi.dmc_vars import STATE_GRINDING, STATE_HOMING
            motion_active = (
                not self.state.connected
                or self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)
            )
        # Only gate if not already role-gated (operator readonly makes it invisible)
        if not (self.state is not None and not self.state.setup_unlocked):
            apply_btn.disabled = motion_active
            apply_btn.opacity = 0.4 if motion_active else 1.0

    # ---------------------------------------------------------------------------
    # Role-based readonly
    # ---------------------------------------------------------------------------

    def _apply_role_mode(self, setup_unlocked: bool) -> bool:
        """Apply readonly mode based on role. Returns readonly flag.

        Returns True if readonly (Operator), False if editable (Setup/Admin).
        """
        readonly = not setup_unlocked

        # Update all field widgets
        for var_name, widget in self._field_widgets.items():
            try:
                if hasattr(widget, 'readonly'):
                    widget.readonly = readonly
            except Exception:
                pass

        # Update apply button if present
        apply_btn = getattr(self, '_apply_btn', None)
        if apply_btn is not None:
            try:
                apply_btn.opacity = 0 if readonly else 1
                apply_btn.disabled = readonly
            except Exception:
                pass

        return readonly

    # ---------------------------------------------------------------------------
    # Machine type rebuild — override to reset pending_count
    # ---------------------------------------------------------------------------

    def _rebuild_for_machine_type(self) -> None:
        """Rebuild parameter cards. Extends base to reset pending_count."""
        super()._rebuild_for_machine_type()
        self.pending_count = 0

    # ---------------------------------------------------------------------------
    # Screen lifecycle
    # ---------------------------------------------------------------------------

    def on_pre_enter(self, *args):
        """Rebuild cards, apply role mode, subscribe to state, then refresh values.

        BaseParametersScreen.on_pre_enter handles:
          - _rebuild_for_machine_type() (which we extend to reset pending_count)
          - MachineState subscription (_on_state_change)
          - _enter_setup_if_needed() (hmiSetp=0)

        SerrationParametersScreen adds:
          - _apply_role_mode() for role-based readonly
          - Additional subscription for apply button gating (stored in _btn_unsub)
          - read_from_controller()
        """
        # Base handles: rebuild, subscribe, enter_setup_if_needed
        super().on_pre_enter(*args)

        # Apply role-based readonly
        setup_unlocked = True
        if self.state is not None:
            setup_unlocked = self.state.setup_unlocked
        self._apply_role_mode(setup_unlocked)

        # Subscribe separately for apply button gating (stored in _btn_unsub to
        # allow clean unsubscribe in on_leave — base owns _state_unsub exclusively)
        if self.state is not None:
            self._btn_unsub = self.state.subscribe(
                lambda s: Clock.schedule_once(lambda *_: self._update_apply_button())
            )
        self._update_apply_button()

        self.read_from_controller()

    def on_leave(self, *args):
        """Unsubscribe apply button listener, then delegate to base class."""
        # Unsubscribe the apply button gating listener (separate from base's _state_unsub)
        btn_unsub = getattr(self, '_btn_unsub', None)
        if btn_unsub is not None:
            btn_unsub()
            self._btn_unsub = None
        # BaseParametersScreen.on_leave fires _exit_setup_if_needed() and unsubscribes
        super().on_leave(*args)

    def on_kv_post(self, base_widget):
        """Build parameter cards after KV post (initial load only)."""
        super().on_kv_post(base_widget)
        self.build_param_cards()

    # build_param_cards is inherited from BaseParametersScreen
