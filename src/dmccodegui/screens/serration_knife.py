from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import ObjectProperty

from ..app_state import MachineState
from ..controller import GalilController

# =============================================================================
#  THEME CONSTANTS
# =============================================================================
BG_DARK    = (0.031, 0.047, 0.071, 1)
BG_PANEL   = (0.051, 0.071, 0.102, 1)
BG_ROW     = (0.071, 0.094, 0.133, 1)
BORDER     = (0.118, 0.145, 0.188, 1)
TEXT_MAIN  = (0.886, 0.910, 0.941, 1)
TEXT_MID   = (0.580, 0.631, 0.710, 1)
TEXT_DIM   = (0.282, 0.333, 0.420, 1)
TEXT_FAINT = (0.200, 0.239, 0.314, 1)

C_YELLOW = (0.980, 0.749, 0.043, 1)
C_BLUE   = (0.369, 0.510, 0.965, 1)
C_PURPLE = (0.659, 0.333, 0.965, 1)
C_GREEN  = (0.133, 0.773, 0.369, 1)
C_RED    = (0.937, 0.267, 0.267, 1)
C_CYAN   = (0.024, 0.714, 0.831, 1)
C_ORANGE = (0.980, 0.604, 0.098, 1)
C_LIME   = (0.518, 0.796, 0.071, 1)

GROUP_COLORS = {
    'geometry':    C_YELLOW,
    'feedrates':   C_BLUE,
    'calibration': C_PURPLE,
    'positions':   C_GREEN,
    'safety':      C_RED,
}

# =============================================================================
#  DATA
# =============================================================================
DEFAULT_PARAMS = {
    'grdthk': 3.0,   'spitch': 4.0,  'sdepth': 2.0,   'swidth': 5.0,
    'knflen': 100.0, 'fdA': 40.0,    'fdBin': 15.0,   'fdBout': 40.0,
    'fdCdn': 10.0,   'fdCup': 30.0,  'fdPark': 20.0,  'mmA': 4000.0,
    'mmB': 4000.0,   'mmC': 4000.0,  'startPtA': 0.0, 'startPtB': 0.0,
    'restPtA': 0.0,  'restPtB': 0.0, 'backOff': 2.0,  'pertol': 2000.0,
}

PARAM_META = {
    'grdthk':   ('Grinder Wheel Thickness',   'mm',     'geometry',    'Physical thickness of grinding wheel. Reference for pitch spacing.'),
    'spitch':   ('Serration Pitch',           'mm',     'geometry',    'Center-to-center distance between teeth. Must be >= grdthk.'),
    'sdepth':   ('Serration Depth',           'mm',     'geometry',    'How deep each tooth is cut. C axis is set manually.'),
    'swidth':   ('Base Grind Width',          'mm',     'geometry',    'Base B axis travel into grinder. bComp[n] added on top.'),
    'knflen':   ('Knife Length',              'mm',     'geometry',    'Total blade length to grind. numSerr = INT(knflen/spitch).'),
    'fdA':      ('A Feed Rate',               'mm/s',   'feedrates',   'Speed of A axis travel between teeth.'),
    'fdBin':    ('B Plunge Rate',             'mm/s',   'feedrates',   'Speed of B axis moving INTO the grinder to cut.'),
    'fdBout':   ('B Retract Rate',            'mm/s',   'feedrates',   'Speed of B axis retracting AWAY from grinder.'),
    'fdCdn':    ('C Down Rate',               'mm/s',   'feedrates',   'Manual jog speed C down. Reference only, not used in loop.'),
    'fdCup':    ('C Up Rate',                 'mm/s',   'feedrates',   'Manual jog speed C up. Reference only, not used in loop.'),
    'fdPark':   ('Park Speed',                'mm/s',   'feedrates',   'Speed for all fault recovery and park moves on A and B.'),
    'mmA':      ('Counts/mm  A Axis',         'cts/mm', 'calibration', 'Empirical: move N counts, measure mm, mmA = N / mm.'),
    'mmB':      ('Counts/mm  B Axis',         'cts/mm', 'calibration', 'Same calibration method for B axis.'),
    'mmC':      ('Counts/mm  C Axis',         'cts/mm', 'calibration', 'Same calibration method for C axis.'),
    'startPtA': ('Start Position  A',         'mm',     'positions',   'Absolute A at cycle start. Tooth 0 aligns here.'),
    'startPtB': ('Start Position  B',         'mm',     'positions',   'Absolute B at cycle start. Edge just clear of grinder.'),
    'restPtA':  ('Rest Position  A',          'mm',     'positions',   'A parks here after complete or fault. Reload position.'),
    'restPtB':  ('Rest Position  B',          'mm',     'positions',   'B parks here after complete or fault. Fully retracted.'),
    'backOff':  ('Limit Back-off',            'mm',     'safety',      'How far tripped axis retreats from limit before parking.'),
    'pertol':   ('Position Error Tolerance',  'cts',    'safety',      'Max error counts before #POSERR fires. Set via ER command.'),
}

DEFAULT_BCOMP = [0.0, 0.1, 0.2, 0.3, 0.4, 0.4, 0.3, 0.2, 0.1, 0.0]

SUBROUTINES = [
    ('#PARAMS',  C_YELLOW, 'AUTO INTERRUPT', False,
     'Loads all geometry, feed rate, calibration, position, and safety variables. Must be called first before any motion.',
     ['grdthk', 'spitch', 'sdepth', 'swidth', 'knflen', 'fdA', 'fdBin', 'fdBout', 'fdCdn', 'fdCup', 'fdPark', 'mmA', 'mmB', 'mmC', 'startPt', 'restPt', 'backOff', 'numSerr']),
    ('#PROFILE', C_PURPLE, '', False,
     'Declares and populates the bComp[] array. One B compensation value per serration tooth. numComp must match entries.',
     ['bComp[]', 'numComp']),
    ('#HOME',    C_CYAN,   '', False,
     'Homes all three axes using HMA/HMB/HMC then defines position as 0,0,0. Optional — call before #GRIND.',
     ['DP 0,0,0']),
    ('#GRIND',   C_GREEN,  '', False,
     'Main entry point. Enables A and B servos (C is manual). Moves to startPt[], then enters #LOOP.',
     ['scount', 'currA', 'fltflg', 'startPt[0]', 'startPt[1]']),
    ('#LOOP',    C_GREEN,  '', False,
     'Core cycle. B plunges to (startPt[1]+swidth+bComp[cidx])*mmB, retracts, A steps spitch*mmA. Repeats until scount=numSerr.',
     ['cidx', 'btot', 'scount', 'currA', 'spitch', 'swidth', 'bComp', 'mmA', 'mmB', 'fdBin', 'fdBout', 'fdA']),
    ('#DONE',    C_LIME,   '', False,
     'Normal completion. Retracts B to restPt[1], returns A to restPt[0]. C is NOT moved.',
     ['restPt[0]', 'restPt[1]', 'scount', 'currA']),
    ('#RESUME',  C_ORANGE, '', False,
     'Re-entry after fault recovery. Jumps to #LOOP without reinitialising counters. scount and currA preserved.',
     ['scount', 'currA']),
    ('#LIMSWI',  C_RED,    'AUTO INTERRUPT', False,
     'Fires on hardware limit. Identifies axis/direction, backs off backOff mm, parks B then A, re-seeks A, resumes.',
     ['backOff', 'restPt', '_LFA', '_LRA', '_LFB', '_LRB', '_LFC', '_LRC', 'fdPark', 'mmA', 'mmB']),
    ('#POSERR',  C_RED,    'AUTO INTERRUPT', False,
     'Fires when position error > pertol. Catches stalls/belt slip. Re-enables servos, parks B then A, resumes.',
     ['pertol', '_TEA', '_TEB', '_TEC', 'fdPark', 'mmA', 'mmB', 'restPt']),
    ('#ESTOP',   (0.863, 0.149, 0.149, 1), 'NO RESUME', True,
     'Hard abort. Stops A and B immediately. Operator must restart XQ #GRIND manually. C axis never touched.',
     ['scount', 'currA']),
]

FLOW_STEPS = [
    ('1. XQ #PARAMS',         'Load variables',               C_ORANGE, 'init'),
    ('2. XQ #PROFILE',        'Load bComp[]',                 C_PURPLE, 'init'),
    ('3. Jog C Axis',         'Set knife angle manually',     C_CYAN,   'manual'),
    ('4. XQ #HOME',           'Optional — home axes',         C_CYAN,   'optional'),
    ('5. XQ #GRIND',          'SH AB -> move to startPt[]',   C_GREEN,  'run'),
    ('6. LOOP: B Plunges In', 'PA startPt[1]+swidth+bComp',   C_GREEN,  'loop'),
    ('7. LOOP: B Retracts',   'PA startPt[1]',                C_GREEN,  'loop'),
    ('8. LOOP: A Steps Fwd',  'PR spitch x mmA',              C_GREEN,  'loop'),
    ('9. scount++',           'JP #LOOP if scount < numSerr', C_GREEN,  'loop'),
    ('10. #DONE',             'Park B -> Park A -> wait',     C_LIME,   'done'),
]

# Module-level shared state
_params = dict(DEFAULT_PARAMS)
_bcomp  = list(DEFAULT_BCOMP)


# =============================================================================
#  CANVAS HELPERS
#  All helpers capture direct instruction references — never use index access
#  into canvas.children, which breaks when Kivy inserts internal instructions.
# =============================================================================

def _add_rr_canvas(widget, fill_color, border_color, radius, line_width=1.2):
    """
    Add a rounded-rectangle fill + Line border to widget.canvas.before.
    Bind callbacks keep them in sync as the widget moves/resizes.
    Direct object references are captured — no fragile index arithmetic.
    """
    with widget.canvas.before:
        Color(*fill_color)
        rr = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        Color(*border_color)
        ln = Line(
            rounded_rectangle=[widget.x, widget.y, widget.width, widget.height, radius],
            width=line_width,
        )

    def _upd(inst, _val):
        rr.pos  = inst.pos
        rr.size = inst.size
        ln.rounded_rectangle = [inst.x, inst.y, inst.width, inst.height, radius]

    widget.bind(pos=_upd, size=_upd)


def _themed_label(text, color=None, size=None, bold=False, halign='left', **kw):
    lbl = Label(
        text=text,
        color=color or TEXT_MID,
        font_size=sp(size or 13),
        bold=bold,
        halign=halign,
        valign='middle',
        markup=kw.pop('markup', False),
        **kw,
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _dark_button(text, color=None, height=dp(42), font_size=None, **kw):
    c = color or C_GREEN
    btn = Button(
        text=text,
        size_hint_y=None,
        height=height,
        font_size=sp(font_size or 13),
        bold=True,
        background_normal='',
        background_color=(0, 0, 0, 0),
        color=c,
        **kw,
    )

    def _draw_bg(instance, _value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(c[0], c[1], c[2], 0.18)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(6)])
            Color(c[0], c[1], c[2], 0.55)
            Line(
                rounded_rectangle=[instance.x, instance.y, instance.width, instance.height, dp(6)],
                width=1.2,
            )

    btn.bind(pos=_draw_bg, size=_draw_bg)
    return btn


def _divider():
    w = Widget(size_hint_y=None, height=dp(1))
    with w.canvas:
        Color(*BORDER)
        rect = Rectangle(pos=w.pos, size=w.size)
    w.bind(
        pos=lambda i, v: setattr(rect, 'pos', v),
        size=lambda i, v: setattr(rect, 'size', v),
    )
    return w


# =============================================================================
#  OVERVIEW TAB
# =============================================================================
class OverviewTab(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', spacing=dp(12), padding=dp(14), **kw)
        self._build()

    def _build(self):
        # Axis cards row
        cards = BoxLayout(orientation='horizontal', spacing=dp(10),
                          size_hint_y=None, height=dp(110))
        axes = [
            ('A AXIS', 'Knife Length',           '+ advances along blade toward tip',            C_YELLOW, '->'),
            ('B AXIS', 'Width / Grind Depth',    '+ pushes knife INTO grinder stone',            C_PURPLE, '/>'),
            ('C AXIS', 'Angle / Depth (MANUAL)', 'Operator-controlled. Not touched by program.', C_CYAN,   '<>'),
        ]
        for name, sub, desc, col, icon in axes:
            card = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(4))
            _add_rr_canvas(card, (*col[:3], 0.08), (*col[:3], 0.3), dp(8), line_width=1.2)

            top = BoxLayout(orientation='horizontal')
            top.add_widget(_themed_label(f'[b]{name}[/b]', color=col, size=15,
                                         markup=True, size_hint_x=0.7))
            top.add_widget(_themed_label(icon, color=(*col[:3], 0.4),
                                         size=20, halign='right', size_hint_x=0.3))
            card.add_widget(top)
            card.add_widget(_themed_label(sub,  color=TEXT_MID, size=11))
            card.add_widget(_themed_label(desc, color=TEXT_DIM, size=10))
            cards.add_widget(card)
        self.add_widget(cards)

        # Flow diagram in scroll
        scroll   = ScrollView()
        flow_box = BoxLayout(orientation='vertical', spacing=dp(2),
                             size_hint_y=None, padding=[dp(20), dp(8)])
        flow_box.bind(minimum_height=flow_box.setter('height'))

        loop_start, loop_end = 5, 8

        for i, (label, sub, col, ftype) in enumerate(FLOW_STEPS):
            row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=dp(52), spacing=dp(10))

            # Left bracket indicator for loop steps
            bracket = Widget(size_hint_x=None, width=dp(6))
            if loop_start <= i <= loop_end:
                with bracket.canvas:
                    Color(*C_GREEN[:3], 0.35)
                    brect = Rectangle(pos=bracket.pos, size=bracket.size)
                bracket.bind(
                    pos=lambda inst, v, r=brect: setattr(r, 'pos', v),
                    size=lambda inst, v, r=brect: setattr(r, 'size', v),
                )
            row.add_widget(bracket)

            step_card = BoxLayout(orientation='vertical', padding=[dp(10), dp(6)], spacing=dp(2))
            _add_rr_canvas(step_card, (*col[:3], 0.08), (*col[:3], 0.4), dp(6), line_width=1.0)

            step_row = BoxLayout(orientation='horizontal')
            step_row.add_widget(_themed_label(f'[b]{label}[/b]', color=col,
                                              size=13, markup=True))
            badge_text = {'init': 'INIT', 'manual': 'MANUAL', 'optional': 'OPTIONAL',
                          'run': 'RUN', 'loop': 'LOOP', 'done': 'DONE'}.get(ftype, '')
            step_row.add_widget(_themed_label(badge_text, color=col, size=10, halign='right'))
            step_card.add_widget(step_row)
            step_card.add_widget(_themed_label(sub, color=TEXT_DIM, size=11))
            row.add_widget(step_card)
            flow_box.add_widget(row)

            if i < len(FLOW_STEPS) - 1:
                flow_box.add_widget(
                    _themed_label('v', color=TEXT_FAINT, size=14,
                                  halign='center', size_hint_y=None, height=dp(16))
                )

        flow_box.add_widget(_themed_label(
            '[b]  ^ LOOP repeats while scount < numSerr[/b]',
            color=(*C_GREEN[:3], 0.55), size=11, markup=True,
            size_hint_y=None, height=dp(22)))

        # Fault boxes
        fault_grid = GridLayout(cols=2, spacing=dp(8),
                                size_hint_y=None, height=dp(130))
        faults = [
            ('#LIMSWI fires', C_RED,
             'Hardware limit hit -> back off -> park B -> park A -> re-seek A -> #RESUME'),
            ('#POSERR fires', C_RED,
             'Pos error > pertol -> re-enable servos -> park B -> park A -> re-seek A -> #RESUME'),
            ('#ESTOP called', (0.863, 0.149, 0.149, 1),
             'ST AB immediately -> print fault -> NO resume. Restart required.'),
            ('C Axis (manual)', C_CYAN,
             'Operator jogs C before cycle. C holds position throughout. Never moved by program.'),
        ]
        for title, col, fdesc in faults:
            box = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(4))
            _add_rr_canvas(box, (*col[:3], 0.07), (*col[:3], 0.3), dp(6), line_width=1.0)
            box.add_widget(_themed_label(f'[b]{title}[/b]', color=col, size=12, markup=True))
            box.add_widget(_themed_label(fdesc, color=TEXT_DIM, size=10))
            fault_grid.add_widget(box)
        flow_box.add_widget(fault_grid)

        scroll.add_widget(flow_box)
        self.add_widget(scroll)


# =============================================================================
#  PARAMETERS TAB
# =============================================================================
class ParamsTab(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', spacing=dp(8), padding=dp(14), **kw)
        self._filter = 'all'
        self._rows   = {}
        self._build()

    def _build(self):
        # Group filter buttons
        filter_row = BoxLayout(orientation='horizontal', spacing=dp(6),
                               size_hint_y=None, height=dp(36))
        groups = ['all', 'geometry', 'feedrates', 'calibration', 'positions', 'safety']
        self._filter_btns = {}
        for g in groups:
            col = GROUP_COLORS.get(g, TEXT_MID)
            btn = Button(
                text=g.upper(),
                size_hint_x=None, width=dp(110),
                font_size=sp(11), bold=True,
                background_normal='', background_color=(0, 0, 0, 0),
                color=col,
            )
            btn.bind(on_release=lambda b, grp=g: self._set_filter(grp))
            self._filter_btns[g] = btn
            filter_row.add_widget(btn)
        filter_row.add_widget(Widget())
        self.add_widget(filter_row)

        # Column headers
        hdr = GridLayout(cols=4, size_hint_y=None, height=dp(30), spacing=dp(2))
        with hdr.canvas.before:
            Color(*BG_ROW)
            hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(
            pos=lambda i, v: setattr(hdr_rect, 'pos', v),
            size=lambda i, v: setattr(hdr_rect, 'size', v),
        )
        for h in ('VARIABLE', 'GROUP', 'DESCRIPTION', 'VALUE'):
            hdr.add_widget(_themed_label(h, color=TEXT_DIM, size=11, bold=True))
        self.add_widget(hdr)

        # Scrollable rows
        self._scroll      = ScrollView()
        self._rows_layout = GridLayout(cols=1, spacing=dp(1), size_hint_y=None)
        self._rows_layout.bind(minimum_height=self._rows_layout.setter('height'))
        self._scroll.add_widget(self._rows_layout)
        self.add_widget(self._scroll)

        # Warning bar
        warn = BoxLayout(orientation='horizontal', size_hint_y=None,
                         height=dp(44), padding=dp(10), spacing=dp(8))
        _add_rr_canvas(warn, (*C_YELLOW[:3], 0.07), (*C_YELLOW[:3], 0.25), dp(6), line_width=1.0)
        warn.add_widget(_themed_label('[b]![/b]', color=C_YELLOW,
                                      size=16, markup=True,
                                      size_hint_x=None, width=dp(20)))
        warn.add_widget(_themed_label(
            'All distances in mm, speeds in mm/s. '
            'Multiplied by mmA/mmB/mmC at move time. '
            'Calibrate counts/mm empirically before first run.',
            color=(*C_YELLOW[:3], 0.7), size=11))
        self.add_widget(warn)

        self._rebuild_rows()
        self._set_filter('all')

    def _rebuild_rows(self):
        self._rows_layout.clear_widgets()
        self._rows = {}
        for var, (_label, unit, group, desc) in PARAM_META.items():
            if self._filter not in ('all', group):
                continue
            col = GROUP_COLORS.get(group, TEXT_MID)
            row = GridLayout(cols=4, size_hint_y=None, height=dp(46),
                             spacing=dp(4), padding=[dp(10), dp(4)])
            with row.canvas.before:
                Color(*BG_PANEL)
                row_bg   = Rectangle(pos=row.pos, size=row.size)
                Color(*col[:3], 0.6)
                row_side = Rectangle(pos=row.pos, size=(dp(3), row.height))
            row.bind(
                pos=lambda i, v, b=row_bg, s=row_side: (
                    setattr(b, 'pos', v),
                    setattr(s, 'pos', v),
                ),
                size=lambda i, v, b=row_bg, s=row_side: (
                    setattr(b, 'size', v),
                    setattr(s, 'size', (dp(3), v[1])),
                ),
            )
            row.add_widget(_themed_label(f'[b]{var}[/b]', color=col, size=12, markup=True))
            row.add_widget(_themed_label(group.upper(), color=col, size=10))
            row.add_widget(_themed_label(desc, color=TEXT_DIM, size=11))

            ti = TextInput(
                text=str(_params.get(var, 0)),
                multiline=False,
                background_color=BG_DARK,
                foreground_color=col,
                cursor_color=col,
                font_size=sp(13),
                size_hint_x=None, width=dp(90),
                padding=[dp(6), dp(8)],
            )
            ti.bind(on_text_validate=lambda inst, v=var: self._on_change(v, inst.text))
            ti.bind(focus=lambda inst, focused, v=var: (
                self._on_change(v, inst.text) if not focused else None))
            self._rows[var] = ti
            row.add_widget(ti)

            self._rows_layout.add_widget(row)
            self._rows_layout.add_widget(_divider())

    def _on_change(self, var, text):
        try:
            _params[var] = float(text)
        except ValueError:
            pass

    def _set_filter(self, group):
        self._filter = group
        self._rebuild_rows()


# =============================================================================
#  B-COMP TAB
# =============================================================================
class BCompChart(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(size=self._draw, pos=self._draw)

    def _draw(self, *_a):
        self.canvas.clear()
        data = _bcomp
        if not data:
            return
        mx      = max(data) if max(data) > 0 else 1.0
        n       = len(data)
        w, h    = self.size
        px, py  = self.pos
        pad     = dp(20)

        with self.canvas:
            Color(*BG_PANEL)
            Rectangle(pos=self.pos, size=self.size)

            for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
                Color(*BORDER)
                y = py + pad + frac * (h - pad * 2)
                Line(points=[px + pad, y, px + w - pad, y], width=1)

            if n > 1:
                pts = []
                for i, v in enumerate(data):
                    cx = px + pad + i * (w - pad * 2) / max(n - 1, 1)
                    cy = py + pad + (v / mx) * (h - pad * 2)
                    pts.append((cx, cy))

                Color(*C_PURPLE[:3], 0.25)
                for cx, cy in pts:
                    Line(points=[cx, py + pad, cx, cy], width=2)

                Color(*C_PURPLE)
                flat = [coord for pt in pts for coord in pt]
                Line(points=flat, width=dp(1.5))

                for cx, cy in pts:
                    Color(*C_PURPLE)
                    Ellipse(pos=(cx - dp(4), cy - dp(4)), size=(dp(8), dp(8)))
                    Color(*BG_PANEL)
                    Ellipse(pos=(cx - dp(2), cy - dp(2)), size=(dp(4), dp(4)))

    def refresh(self):
        self._draw()


class BCompTab(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', spacing=dp(10), padding=dp(14), **kw)
        self._build()

    def _build(self):
        top = BoxLayout(orientation='horizontal', spacing=dp(14))

        # Left: editable table
        left = BoxLayout(orientation='vertical', spacing=dp(6))

        hdr = GridLayout(cols=3, size_hint_y=None, height=dp(28))
        with hdr.canvas.before:
            Color(*BG_ROW)
            hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(
            pos=lambda i, v: setattr(hdr_rect, 'pos', v),
            size=lambda i, v: setattr(hdr_rect, 'size', v),
        )
        for h in ('IDX', 'bComp (mm)', 'DEL'):
            hdr.add_widget(_themed_label(h, color=TEXT_DIM, size=11, bold=True))
        left.add_widget(hdr)

        self._table_scroll = ScrollView()
        self._table_layout = GridLayout(cols=3, spacing=dp(2), size_hint_y=None)
        self._table_layout.bind(minimum_height=self._table_layout.setter('height'))
        self._table_scroll.add_widget(self._table_layout)
        left.add_widget(self._table_scroll)

        add_btn = _dark_button('+ ADD TOOTH', color=C_PURPLE, height=dp(36))
        add_btn.bind(on_release=lambda *a: self._add_tooth())
        left.add_widget(add_btn)

        self._info_lbl = _themed_label(
            f'{len(_bcomp)} teeth  |  numComp = {len(_bcomp)}',
            color=C_PURPLE, size=12, size_hint_y=None, height=dp(22))
        left.add_widget(self._info_lbl)
        top.add_widget(left)

        # Right: chart
        right = BoxLayout(orientation='vertical', spacing=dp(6))
        right.add_widget(_themed_label('B COMPENSATION PROFILE',
                                       color=TEXT_DIM, size=11,
                                       size_hint_y=None, height=dp(20)))
        self._chart = BCompChart()
        right.add_widget(self._chart)
        top.add_widget(right)

        self.add_widget(top)
        self.add_widget(_themed_label(
            'Each bComp[n] is extra B travel (mm) added to swidth for that tooth.  '
            'Index 0 = first tooth.  Values from blade profile (AutoCAD export).',
            color=TEXT_DIM, size=12, size_hint_y=None, height=dp(36)))

        self._rebuild_table()

    def _rebuild_table(self):
        self._table_layout.clear_widgets()
        for i, val in enumerate(_bcomp):
            self._table_layout.add_widget(
                _themed_label(f'[{i}]', color=TEXT_DIM, size=12,
                              size_hint_y=None, height=dp(36)))

            ti = TextInput(
                text=str(val),
                multiline=False,
                background_color=BG_DARK,
                foreground_color=C_PURPLE,
                cursor_color=C_PURPLE,
                font_size=sp(13),
                size_hint_y=None, height=dp(36),
                padding=[dp(6), dp(8)],
            )
            ti.bind(on_text_validate=lambda inst, idx=i: self._update(idx, inst.text))
            ti.bind(focus=lambda inst, focused, idx=i: (
                self._update(idx, inst.text) if not focused else None))
            self._table_layout.add_widget(ti)

            del_btn = Button(
                text='x',
                size_hint_y=None, height=dp(36),
                font_size=sp(14), bold=True,
                background_normal='', background_color=(0, 0, 0, 0),
                color=(*C_RED[:3], 0.5),
            )
            del_btn.bind(on_release=lambda b, idx=i: self._remove(idx))
            self._table_layout.add_widget(del_btn)

        self._info_lbl.text = f'{len(_bcomp)} teeth  |  numComp = {len(_bcomp)}'
        self._chart.refresh()

    def _update(self, idx, text):
        try:
            _bcomp[idx] = float(text)
            self._chart.refresh()
        except (ValueError, IndexError):
            pass

    def _add_tooth(self):
        _bcomp.append(0.0)
        self._rebuild_table()

    def _remove(self, idx):
        if len(_bcomp) > 1:
            _bcomp.pop(idx)
            self._rebuild_table()


# =============================================================================
#  RUN CONTROL TAB
# =============================================================================
class RunControlTab(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='horizontal', spacing=dp(14), padding=dp(14), **kw)
        self._timer   = None
        self._scount  = 0
        self._running = False
        self._cpos    = 0.0
        self._build()

    def _build(self):
        # ---- Left column ----
        left = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_x=0.42)

        left.add_widget(_themed_label('C AXIS  —  MANUAL CONTROL',
                                      color=TEXT_DIM, size=11, bold=True,
                                      size_hint_y=None, height=dp(20)))

        c_box = BoxLayout(orientation='vertical', spacing=dp(6),
                          size_hint_y=None, height=dp(120), padding=dp(10))
        _add_rr_canvas(c_box, (*C_CYAN[:3], 0.07), (*C_CYAN[:3], 0.3), dp(8), line_width=1.2)

        jog_row = BoxLayout(orientation='horizontal', spacing=dp(10),
                            size_hint_y=None, height=dp(44))
        dn_btn = _dark_button('v  DOWN', color=C_CYAN)
        dn_btn.bind(on_release=lambda *a: self._jog_c(-0.5))
        jog_row.add_widget(dn_btn)

        self._cpos_lbl = _themed_label('0.00 mm', color=C_CYAN, size=20,
                                       bold=True, halign='center')
        jog_row.add_widget(self._cpos_lbl)

        up_btn = _dark_button('^  UP', color=C_CYAN)
        up_btn.bind(on_release=lambda *a: self._jog_c(0.5))
        jog_row.add_widget(up_btn)

        c_box.add_widget(jog_row)
        c_box.add_widget(_themed_label(
            'Set knife angle here. C holds during grind.',
            color=TEXT_DIM, size=11, halign='center'))
        left.add_widget(c_box)

        # Cycle summary
        left.add_widget(_themed_label('CYCLE SUMMARY', color=TEXT_DIM,
                                      size=11, bold=True,
                                      size_hint_y=None, height=dp(20)))
        sum_box = BoxLayout(orientation='vertical', spacing=dp(1),
                            size_hint_y=None, height=dp(180))
        with sum_box.canvas.before:
            Color(*BG_PANEL)
            sum_rr = RoundedRectangle(pos=sum_box.pos, size=sum_box.size, radius=[dp(8)])
        sum_box.bind(
            pos=lambda i, v: setattr(sum_rr, 'pos', v),
            size=lambda i, v: setattr(sum_rr, 'size', v),
        )

        self._sum_rows = {}
        summary_keys = [
            ('Knife Length',      'knflen', 'mm'),
            ('Serration Pitch',   'spitch', 'mm'),
            ('Base Grind Width',  'swidth', 'mm'),
            ('Grinder Thickness', 'grdthk', 'mm'),
            ('bComp Entries',     None,     ''),
        ]
        for label, key, unit in summary_keys:
            r = BoxLayout(orientation='horizontal', size_hint_y=None,
                          height=dp(30), padding=[dp(12), 0])
            r.add_widget(_themed_label(label, color=TEXT_DIM, size=12))
            val_str = f'{_params.get(key, 0)} {unit}' if key else str(len(_bcomp))
            lbl = _themed_label(val_str, color=TEXT_MAIN, size=13, bold=True, halign='right')
            self._sum_rows[label] = lbl
            r.add_widget(lbl)
            sum_box.add_widget(r)
            sum_box.add_widget(_divider())

        r2 = BoxLayout(orientation='horizontal', size_hint_y=None,
                       height=dp(30), padding=[dp(12), 0])
        r2.add_widget(_themed_label('Total Teeth (numSerr)', color=C_YELLOW, size=12))
        self._numserr_lbl = _themed_label('', color=C_YELLOW, size=13, bold=True, halign='right')
        r2.add_widget(self._numserr_lbl)
        sum_box.add_widget(r2)
        left.add_widget(sum_box)

        left.add_widget(Widget())

        self._start_btn = _dark_button('>  START GRIND', color=C_GREEN,
                                       height=dp(52), font_size=15)
        self._start_btn.bind(on_release=lambda *a: self._start_grind())
        left.add_widget(self._start_btn)

        estop_btn = _dark_button('[]  E-STOP', color=C_RED, height=dp(44), font_size=14)
        estop_btn.bind(on_release=lambda *a: self._estop())
        left.add_widget(estop_btn)

        self.add_widget(left)

        # ---- Right column ----
        right = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_x=0.58)

        right.add_widget(_themed_label('PROGRESS', color=TEXT_DIM,
                                       size=11, bold=True,
                                       size_hint_y=None, height=dp(20)))
        prog_row = BoxLayout(orientation='horizontal', spacing=dp(8),
                             size_hint_y=None, height=dp(20))
        self._prog_track = BoxLayout(size_hint_y=None, height=dp(14))
        with self._prog_track.canvas.before:
            Color(*BG_DARK)
            RoundedRectangle(pos=self._prog_track.pos,
                             size=self._prog_track.size, radius=[dp(7)])

        self._prog_fill = Widget(size_hint_x=0)
        with self._prog_fill.canvas:
            Color(*C_GREEN)
            fill_rr = RoundedRectangle(pos=self._prog_fill.pos,
                                       size=self._prog_fill.size, radius=[dp(7)])
        self._prog_fill.bind(
            pos=lambda i, v: setattr(fill_rr, 'pos', v),
            size=lambda i, v: setattr(fill_rr, 'size', v),
        )
        self._prog_track.add_widget(self._prog_fill)
        prog_row.add_widget(self._prog_track)

        self._prog_lbl = _themed_label('0 / 0', color=C_GREEN, size=12,
                                       size_hint_x=None, width=dp(60), halign='right')
        prog_row.add_widget(self._prog_lbl)
        right.add_widget(prog_row)

        right.add_widget(_themed_label('OPERATION LOG', color=TEXT_DIM,
                                       size=11, bold=True,
                                       size_hint_y=None, height=dp(20)))
        log_scroll = ScrollView()
        self._log_layout = GridLayout(cols=1, spacing=dp(2),
                                      size_hint_y=None, padding=dp(8))
        self._log_layout.bind(minimum_height=self._log_layout.setter('height'))
        log_scroll.add_widget(self._log_layout)
        with log_scroll.canvas.before:
            Color(*BG_DARK)
            RoundedRectangle(pos=log_scroll.pos, size=log_scroll.size, radius=[dp(6)])
        right.add_widget(log_scroll)
        self._log_scroll = log_scroll

        self.add_widget(right)
        self._refresh_summary()

    def _jog_c(self, delta):
        self._cpos = round(self._cpos + delta, 2)
        self._cpos_lbl.text = f'{self._cpos:.2f} mm'
        self._log_msg(f'C jog {"UP" if delta > 0 else "DOWN"} -> {self._cpos:.2f} mm')

    def _refresh_summary(self):
        keys = {'Knife Length': 'knflen', 'Serration Pitch': 'spitch',
                'Base Grind Width': 'swidth', 'Grinder Thickness': 'grdthk'}
        for label, key in keys.items():
            if label in self._sum_rows:
                self._sum_rows[label].text = f'{_params.get(key, 0)} mm'
        if 'bComp Entries' in self._sum_rows:
            self._sum_rows['bComp Entries'].text = str(len(_bcomp))
        ns = int(_params.get('knflen', 0) / max(_params.get('spitch', 1), 0.001))
        self._numserr_lbl.text = str(ns)

    def _log_msg(self, msg):
        from datetime import datetime
        ts  = datetime.now().strftime('%H:%M:%S')
        txt = f'[{ts}] {msg}'
        if 'ESTOP' in msg or '***' in msg:
            col = C_RED
        elif 'DONE' in msg or 'complete' in msg.lower():
            col = C_GREEN
        elif 'Tooth' in msg:
            col = C_PURPLE
        else:
            col = TEXT_DIM
        lbl = _themed_label(txt, color=col, size=11, size_hint_y=None, height=dp(22))
        self._log_layout.add_widget(lbl)
        Clock.schedule_once(lambda *_: self._scroll_log())

    def _scroll_log(self):
        self._log_scroll.scroll_y = 0

    def _start_grind(self):
        if self._running:
            return
        self._refresh_summary()
        self._running  = True
        self._scount   = 0
        num_serr = int(_params.get('knflen', 0) /
                       max(_params.get('spitch', 1), 0.001))
        self._num_serr = num_serr
        self._start_btn.text = 'o  GRINDING...'
        self._log_msg('XQ #GRIND -- Enabling AB servos. Moving to start position.')
        self._log_msg(f'Start: A={_params["startPtA"]}mm  B={_params["startPtB"]}mm  '
                      f'C={self._cpos:.2f}mm (manual hold)')
        self._log_msg(f'Cycle: {num_serr} teeth x {_params["spitch"]}mm pitch = {_params["knflen"]}mm')
        self._timer = Clock.schedule_interval(self._tick, 0.35)

    def _tick(self, _dt):
        if self._scount >= self._num_serr:
            self._timer.cancel()
            self._running = False
            self._start_btn.text = '>  START GRIND'
            self._log_msg(f'#DONE -- Grind complete. {self._num_serr} teeth cut.')
            self._log_msg(f'Parking -> B={_params["restPtB"]}mm, A={_params["restPtA"]}mm')
            self._log_msg('At rest. Reload knife then XQ #GRIND for next cycle.')
            self._update_progress()
            return
        cidx = min(self._scount, len(_bcomp) - 1)
        btot = round(_params['startPtB'] + _params['swidth'] + _bcomp[cidx], 3)
        ns   = self._num_serr
        self._log_msg(
            f'Tooth {self._scount + 1}/{ns} '
            f'-> B plunge {btot}mm (bComp[{cidx}]={_bcomp[cidx]}) '
            f'-> retract -> A +{_params["spitch"]}mm'
        )
        self._scount += 1
        self._update_progress()

    def _update_progress(self):
        ns  = max(self._num_serr, 1)
        pct = self._scount / ns
        self._prog_fill.size_hint_x = pct
        self._prog_lbl.text = f'{self._scount} / {ns}'

    def _estop(self):
        if self._timer:
            self._timer.cancel()
        self._running = False
        self._start_btn.text = '>  START GRIND'
        self._log_msg(f'*** ESTOP -- ST AB. scount={self._scount}. Manual restart required.')


# =============================================================================
#  SUBROUTINES TAB
# =============================================================================
class SubroutinesTab(ScrollView):
    def __init__(self, **kw):
        super().__init__(**kw)
        grid = GridLayout(cols=2, spacing=dp(10), padding=dp(14), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for name, col, badge, _no_resume, desc, variables in SUBROUTINES:
            card = BoxLayout(orientation='vertical', spacing=dp(6),
                             padding=dp(12), size_hint_y=None, height=dp(160))
            _add_rr_canvas(card, (*col[:3], 0.07), (*col[:3], 0.3), dp(8), line_width=1.2)

            top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28))
            top_row.add_widget(_themed_label(f'[b]{name}[/b]', color=col,
                                             size=16, markup=True, size_hint_x=0.5))
            if badge:
                badge_lbl = _themed_label(
                    badge,
                    color=C_RED if 'INTERRUPT' in badge else (0.863, 0.149, 0.149, 1),
                    size=10, halign='right')
                top_row.add_widget(badge_lbl)
            card.add_widget(top_row)
            card.add_widget(_themed_label(desc, color=TEXT_MID, size=11))

            # Variable chips
            chip_row = BoxLayout(orientation='horizontal', spacing=dp(4),
                                 size_hint_y=None, height=dp(26))
            for v in variables[:8]:
                chip = Label(
                    text=v, font_size=sp(10),
                    color=TEXT_MID, size_hint_x=None,
                    width=dp(len(v) * 7 + 14),
                )
                with chip.canvas.before:
                    Color(*BG_DARK)
                    chip_bg = RoundedRectangle(pos=chip.pos, size=chip.size, radius=[dp(3)])
                    Color(*BORDER)
                    chip_ln = Line(
                        rounded_rectangle=[chip.x, chip.y, chip.width, chip.height, dp(3)],
                        width=1,
                    )

                def _upd_chip(inst, _val, bg=chip_bg, ln=chip_ln):
                    bg.pos  = inst.pos
                    bg.size = inst.size
                    ln.rounded_rectangle = [inst.x, inst.y, inst.width, inst.height, dp(3)]

                chip.bind(pos=_upd_chip, size=_upd_chip)
                chip_row.add_widget(chip)
            chip_row.add_widget(Widget())
            card.add_widget(chip_row)

            grid.add_widget(card)

        self.add_widget(grid)


# =============================================================================
#  MAIN SCREEN
# =============================================================================
class SerratedKnifeScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState         = ObjectProperty(None)  # type: ignore

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')

        with root.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda i, v: setattr(self._bg, 'pos', v),
            size=lambda i, v: setattr(self._bg, 'size', v),
        )

        # ── Header ──────────────────────────────────────────────────────────
        hdr = BoxLayout(orientation='horizontal', size_hint_y=None,
                        height=dp(56), padding=[dp(20), 0], spacing=dp(16))
        with hdr.canvas.before:
            Color(*BG_PANEL)
            hdr_bg     = Rectangle(pos=hdr.pos, size=hdr.size)
            Color(*BORDER)
            hdr_border = Rectangle(pos=(hdr.x, hdr.y), size=(hdr.width, dp(1)))
        hdr.bind(
            pos=lambda i, v: (
                setattr(hdr_bg,     'pos', v),
                setattr(hdr_border, 'pos', (v[0], v[1])),
            ),
            size=lambda i, v: (
                setattr(hdr_bg,     'size', v),
                setattr(hdr_border, 'size', (v[0], dp(1))),
            ),
        )

        icon_box = Widget(size_hint_x=None, width=dp(36))
        with icon_box.canvas:
            Color(*C_YELLOW[:3], 0.15)
            RoundedRectangle(pos=(0, 0), size=(dp(36), dp(36)), radius=[dp(6)])
            Color(*C_YELLOW[:3], 0.6)
            Line(rounded_rectangle=[0, 0, dp(36), dp(36), dp(6)], width=1.5)
        hdr.add_widget(icon_box)

        title_box = BoxLayout(orientation='vertical', spacing=dp(2))
        title_box.add_widget(_themed_label('[b]KNIFE GRINDER CONTROL[/b]',
                                           color=TEXT_MAIN, size=17, markup=True))
        title_box.add_widget(_themed_label('GALIL DMC  |  3-AXIS SERRATION SYSTEM',
                                           color=TEXT_DIM, size=11))
        hdr.add_widget(title_box)
        hdr.add_widget(Widget())

        back_btn = _dark_button('<  BACK', color=TEXT_DIM,
                                height=dp(34), size_hint_x=None, width=dp(100))
        back_btn.bind(on_release=self._go_back)
        hdr.add_widget(back_btn)

        self._ns_lbl = _themed_label(
            f'numSerr = {int(_params["knflen"] / _params["spitch"])}',
            color=C_YELLOW, size=12, size_hint_x=None, width=dp(130), halign='right')
        hdr.add_widget(self._ns_lbl)
        root.add_widget(hdr)

        # ── Tabbed Panel ────────────────────────────────────────────────────
        tp = TabbedPanel(do_default_tab=False, tab_width=dp(150),
                         tab_height=dp(38), background_color=BG_PANEL)

        tabs_data = [
            ('OVERVIEW',     OverviewTab()),
            ('PARAMETERS',   ParamsTab()),
            ('B-COMP TABLE', BCompTab()),
            ('RUN CONTROL',  RunControlTab()),
            ('SUBROUTINES',  SubroutinesTab()),
        ]
        for title, content in tabs_data:
            ti = TabbedPanelItem(
                text=title,
                font_size=sp(12), bold=True,
                background_normal='',
                background_color=BG_PANEL,
                color=TEXT_MID,
            )
            ti.add_widget(content)
            tp.add_widget(ti)

        # tab_list is in reverse insertion order; [-1] is the first tab (OVERVIEW)
        tp.default_tab = tp.tab_list[-1]
        tp.switch_to(tp.tab_list[-1])

        root.add_widget(tp)
        self.add_widget(root)

    def _go_back(self, *_a):
        if self.manager:
            self.manager.transition.direction = 'right'
            prev = self.manager.previous()
            if prev:
                self.manager.current = prev

    def on_enter(self, *_a):
        ns = int(_params['knflen'] / max(_params['spitch'], 0.001))
        self._ns_lbl.text = f'numSerr = {ns}'

    def _alert(self, message: str) -> None:
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, '_log_message'):
                app._log_message(message)
                return
        except Exception:
            pass
        if self.state:
            self.state.log(message)
