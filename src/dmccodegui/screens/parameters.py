"""ParametersScreen -- grouped-card parameter editor with dirty tracking and validation.

Replaces the old placeholder grid with:
  - 5 groups: Geometry, Feedrates, Calibration, Positions, Safety
  - Immediate validation (red=invalid, amber=modified)
  - Batch apply to controller with read-back and NV burn
  - Role-based readonly (Operator cannot edit)
"""
from __future__ import annotations

from typing import Dict, Optional

from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty
from kivy.uix.screenmanager import Screen

from dmccodegui.utils.jobs import submit

# ---------------------------------------------------------------------------
# Parameter definitions
# ---------------------------------------------------------------------------

PARAM_DEFS = [
    # Geometry group
    {"label": "Knife Thickness", "var": "knfThk", "unit": "mm", "group": "Geometry", "min": 0.1, "max": 50.0},
    {"label": "Edge Thickness", "var": "edgeThk", "unit": "mm", "group": "Geometry", "min": 0.01, "max": 10.0},
    # Feedrates group
    {"label": "Feed Rate A", "var": "fdA", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate B", "var": "fdB", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate C Down", "var": "fdCdn", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate C Up", "var": "fdCup", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate Park", "var": "fdPark", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate D", "var": "fdD", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    # Calibration group (pitch/ratio/ctsRev x 4 axes)
    {"label": "Pitch A", "var": "pitchA", "unit": "mm/rev", "group": "Calibration", "min": 0.001, "max": 100.0},
    {"label": "Pitch B", "var": "pitchB", "unit": "mm/rev", "group": "Calibration", "min": 0.001, "max": 100.0},
    {"label": "Pitch C", "var": "pitchC", "unit": "mm/rev", "group": "Calibration", "min": 0.001, "max": 100.0},
    {"label": "Pitch D", "var": "pitchD", "unit": "deg/rev", "group": "Calibration", "min": 0.001, "max": 3600.0},
    {"label": "Ratio A", "var": "ratioA", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Ratio B", "var": "ratioB", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Ratio C", "var": "ratioC", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Ratio D", "var": "ratioD", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Counts/Rev A", "var": "ctsRevA", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
    {"label": "Counts/Rev B", "var": "ctsRevB", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
    {"label": "Counts/Rev C", "var": "ctsRevC", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
    {"label": "Counts/Rev D", "var": "ctsRevD", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
]

# Build lookup dict by var name
_PARAM_BY_VAR: Dict[str, dict] = {p["var"]: p for p in PARAM_DEFS}

# Groups that reject zero values (calibration params)
_ZERO_REJECT_GROUPS = {"Calibration"}

# Groups that reject negative values
_NEGATIVE_REJECT_GROUPS = {"Feedrates", "Calibration"}

# Border color constants
BORDER_NORMAL = [0.118, 0.145, 0.188, 1]
BORDER_AMBER = [0.980, 0.749, 0.043, 0.9]
BORDER_RED = [0.900, 0.200, 0.200, 0.9]

# Group accent colors for card headers and left-edge stripe
GROUP_COLORS: dict[str, list[float]] = {
    "Geometry":    [0.980, 0.569, 0.043, 1],   # orange
    "Feedrates":   [0.024, 0.714, 0.831, 1],   # cyan
    "Calibration": [0.659, 0.333, 0.965, 1],   # purple
}


class ParametersScreen(Screen):
    """Parameters screen with grouped cards, dirty tracking, validation, and batch apply."""

    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)

    # Kivy properties for KV bindings
    pending_count = NumericProperty(0)
    _loading = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Param defs dict -- keyed by var name
        self._param_defs: Dict[str, dict] = _PARAM_BY_VAR.copy()
        # Last known controller values {var_name: float}
        self._controller_vals: Dict[str, float] = {}
        # User-edited strings not yet applied {var_name: str}
        self._dirty: Dict[str, str] = {}
        # Widget refs for border color updates {var_name: widget_ref}
        self._field_widgets: Dict[str, object] = {}

    # ---------------------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------------------

    def validate_field(self, var_name: str, text: str) -> str:
        """Validate a text entry for the named parameter.

        Returns:
            'error'    -- non-numeric, out of range, or special rule violation
            'modified' -- valid numeric value that differs from controller value
            'valid'    -- valid numeric value matching controller value
        """
        param = self._param_defs.get(var_name)
        if param is None:
            return 'error'

        # Must be numeric
        try:
            value = float(text)
        except (ValueError, TypeError):
            return 'error'

        # Calibration: reject zero
        if param['group'] in _ZERO_REJECT_GROUPS and value == 0.0:
            return 'error'

        # Feedrates/Calibration/Safety: reject negative
        if param['group'] in _NEGATIVE_REJECT_GROUPS and value < 0:
            return 'error'

        # Range check
        if not (param['min'] <= value <= param['max']):
            return 'error'

        # Compare to controller value
        ctrl_val = self._controller_vals.get(var_name)
        if ctrl_val is not None and abs(value - ctrl_val) < 1e-9:
            return 'valid'

        return 'modified'

    # ---------------------------------------------------------------------------
    # Field change handler
    # ---------------------------------------------------------------------------

    def on_field_text_change(self, var_name: str, text: str) -> None:
        """Called by KV on_text bindings when a field value changes."""
        if self._loading:
            return

        state = self.validate_field(var_name, text)
        widget = self._field_widgets.get(var_name)
        if widget is not None:
            self._set_field_state(widget, state)

        if state == 'modified':
            self._dirty[var_name] = text
        else:
            # 'valid' (reverted) or 'error' -- remove from dirty
            self._dirty.pop(var_name, None)

        self.pending_count = len(self._dirty)

    def _set_field_state(self, widget, state: str) -> None:
        """Update the border color of a TextInput widget based on validation state."""
        try:
            if state == 'error':
                color = BORDER_RED
            elif state == 'modified':
                color = BORDER_AMBER
            else:
                color = BORDER_NORMAL

            # Update canvas instruction if present (KV-drawn border)
            if hasattr(widget, '_border_color_instruction'):
                widget._border_color_instruction.rgba = color
            # Also store for programmatic access
            widget._param_state = state
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # Apply to controller
    # ---------------------------------------------------------------------------

    def apply_to_controller(self) -> None:
        """Send all dirty parameters to controller, read back, then burn NV."""
        if not self._dirty:
            return
        if self.controller is None or not self.controller.is_connected():
            return
        if self.state is not None and self.state.cycle_running:
            return

        # Snapshot dirty dict before background job
        dirty_snapshot = dict(self._dirty)

        def _job():
            ctrl = self.controller
            if ctrl is None:
                return

            # Write each dirty param
            for var_name, text in dirty_snapshot.items():
                try:
                    ctrl.cmd(f"{var_name}={text}")
                except Exception:
                    pass

            # Read back all params
            new_vals: Dict[str, float] = {}
            for p in PARAM_DEFS:
                var = p['var']
                try:
                    raw = ctrl.cmd(f"MG {var}")
                    new_vals[var] = float(raw.strip())
                except Exception:
                    pass

            # Burn NV memory
            try:
                ctrl.cmd("BV")
            except Exception:
                pass

            # Update screen state directly (Kivy properties are thread-safe for
            # simple value assignments; widget canvas ops are deferred to next frame)
            self._controller_vals.update(new_vals)
            self._dirty.clear()
            self.pending_count = 0
            # Reset all field borders to normal (safe on background thread)
            for var_name, widget in self._field_widgets.items():
                self._set_field_state(widget, 'valid')

        submit(_job)

    # ---------------------------------------------------------------------------
    # Read from controller
    # ---------------------------------------------------------------------------

    def read_from_controller(self) -> None:
        """Refresh all parameter values from the controller."""
        if self.controller is None:
            return

        def _job():
            ctrl = self.controller
            if ctrl is None:
                return

            new_vals: Dict[str, float] = {}
            for p in PARAM_DEFS:
                var = p['var']
                try:
                    raw = ctrl.cmd(f"MG {var}")
                    new_vals[var] = float(raw.strip())
                except Exception:
                    pass

            # Update screen state directly. _loading suppresses on_text callbacks
            # while we programmatically update field widgets.
            self._loading = True
            try:
                self._controller_vals.update(new_vals)
                # Update field widgets
                for var_name, widget in self._field_widgets.items():
                    val = new_vals.get(var_name)
                    if val is not None and hasattr(widget, 'text'):
                        widget.text = str(val)
                # Clear dirty state
                self._dirty.clear()
                self.pending_count = 0
                # Reset all borders
                for var_name, widget in self._field_widgets.items():
                    self._set_field_state(widget, 'valid')
            finally:
                self._loading = False

        submit(_job)

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
    # Screen lifecycle
    # ---------------------------------------------------------------------------

    def on_pre_enter(self, *args):
        """Apply role mode and refresh values when screen is entered."""
        setup_unlocked = True
        if self.state is not None:
            setup_unlocked = self.state.setup_unlocked
        self._apply_role_mode(setup_unlocked)
        self.read_from_controller()

    def on_kv_post(self, base_widget):
        """Build parameter cards after KV post."""
        super().on_kv_post(base_widget)
        self.build_param_cards()

    def build_param_cards(self) -> None:
        """Build grouped parameter cards dynamically in the cards_container."""
        from collections import OrderedDict

        try:
            container = self.ids.get('cards_container')
        except Exception:
            container = None

        if container is None:
            return

        from kivy.graphics import Color, RoundedRectangle, Rectangle
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.textinput import TextInput
        from kivy.uix.widget import Widget

        # Group params preserving order
        groups: OrderedDict[str, list] = OrderedDict()
        for p in PARAM_DEFS:
            groups.setdefault(p['group'], []).append(p)

        container.clear_widgets()

        for group_name, params in groups.items():
            accent = GROUP_COLORS.get(group_name, [0.5, 0.5, 0.5, 1])

            # Card wrapper with left color stripe
            card_wrapper = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                spacing=0,
            )
            card_wrapper.bind(minimum_height=card_wrapper.setter('height'))

            # Left accent stripe
            stripe = Widget(size_hint_x=None, width=6, size_hint_y=1)
            with stripe.canvas.before:
                Color(rgba=accent)
                _rect = RoundedRectangle(pos=stripe.pos, size=stripe.size, radius=[3, 0, 0, 3])
            stripe.bind(pos=lambda w, v, r=_rect: setattr(r, 'pos', v))
            stripe.bind(size=lambda w, v, r=_rect: setattr(r, 'size', v))
            card_wrapper.add_widget(stripe)

            # Card body
            card = BoxLayout(
                orientation='vertical',
                padding=[12, 12, 12, 12],
                spacing=6,
                size_hint_y=None,
            )
            card.bind(minimum_height=card.setter('height'))

            # Card background
            with card.canvas.before:
                Color(rgba=[0.051, 0.071, 0.102, 1])
                _bg = Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=lambda w, v, r=_bg: setattr(r, 'pos', v))
            card.bind(size=lambda w, v, r=_bg: setattr(r, 'size', v))

            # Group header with accent color
            header = Label(
                text=group_name,
                font_size='22sp',
                bold=True,
                size_hint_y=None,
                height=40,
                halign='left',
                valign='middle',
                color=accent,
            )
            header.bind(size=header.setter('text_size'))
            card.add_widget(header)

            for p in params:
                row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=48,
                    spacing=4,
                )

                # Column 1: human-readable label
                lbl = Label(
                    text=p['label'],
                    font_size='18sp',
                    size_hint_x=0.35,
                    halign='left',
                    valign='middle',
                )
                lbl.bind(size=lbl.setter('text_size'))
                row.add_widget(lbl)

                # Column 2: DMC variable code
                var_lbl = Label(
                    text=p['var'],
                    font_size='16sp',
                    size_hint_x=0.15,
                    halign='center',
                    valign='middle',
                    color=[accent[0], accent[1], accent[2], 0.6],
                )
                var_lbl.bind(size=var_lbl.setter('text_size'))
                row.add_widget(var_lbl)

                # Column 3: TextInput
                ti = TextInput(
                    text='',
                    multiline=False,
                    size_hint_x=0.35,
                    font_size='18sp',
                    halign='center',
                )
                var_name = p['var']
                ti.bind(text=lambda widget, text, v=var_name: self.on_field_text_change(v, text))
                self._field_widgets[var_name] = ti
                row.add_widget(ti)

                # Column 4: unit label
                unit_lbl = Label(
                    text=p['unit'],
                    font_size='16sp',
                    size_hint_x=0.15,
                    halign='right',
                    valign='middle',
                )
                unit_lbl.bind(size=unit_lbl.setter('text_size'))
                row.add_widget(unit_lbl)

                card.add_widget(row)

            card_wrapper.add_widget(card)
            container.add_widget(card_wrapper)
