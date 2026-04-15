"""DMC variable name constants and hmiState encoding.

This module is the single source of truth for all DMC variable names used by
Python code. Every screen file that communicates with the controller must import
from here instead of using raw string literals. This prevents 8-char name typos
and ensures Python and DMC stay in sync.

All DMC variable names are limited to 8 characters by the Galil firmware.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# HMI trigger variable names
# These correspond to variables declared with default=1 in the DMC #PARAMS
# block. Setting a variable to 0 fires the associated trigger. The DMC
# program resets each variable to 1 as its first line inside the triggered
# block (one-shot pattern — never use XQ direct calls).
# ---------------------------------------------------------------------------

HMI_GRND: str = "hmiGrnd"  # Trigger: start/continue grinding cycle
HMI_SETP: str = "hmiSetp"  # Trigger: enter setup mode
HMI_MORE: str = "hmiMore"  # Trigger: more grinding passes
HMI_LESS: str = "hmiLess"  # Trigger: fewer grinding passes
HMI_NEWS: str = "hmiNewS"  # Trigger: new session / reset
HMI_HOME: str = "hmiHome"  # Trigger: home axes
HMI_JOG: str = "hmiJog"   # Trigger: jog axis
HMI_CALC: str = "hmiCalc"  # Trigger: recalculate variable positions

HMI_GO_REST: str    = "hmiGoRs"   # Trigger: go to rest position (in setup)
HMI_GO_START: str   = "hmiGoSt"   # Trigger: go to start position (in setup)
HMI_EXIT_SETUP: str = "hmiExSt"   # Trigger: exit setup, return to #MAIN

# Ordered list for batch operations (e.g., initializing all triggers to default)
ALL_HMI_TRIGGERS: list[str] = [
    HMI_GRND, HMI_SETP, HMI_MORE, HMI_LESS,
    HMI_NEWS, HMI_HOME, HMI_JOG, HMI_CALC,
    HMI_GO_REST, HMI_GO_START, HMI_EXIT_SETUP,
]

# ---------------------------------------------------------------------------
# Trigger default/fire values
# Default = 1 means "not triggered". Fire = 0 means "trigger this action".
# The DMC program resets the variable to HMI_TRIGGER_DEFAULT immediately
# upon entering the triggered subroutine.
# ---------------------------------------------------------------------------

HMI_TRIGGER_DEFAULT: int = 1  # Resting / not triggered
HMI_TRIGGER_FIRE: int = 0     # Write this value to fire the trigger

# ---------------------------------------------------------------------------
# Controller state variable
# The DMC program sets hmiState to distinct integer values at each state
# boundary. Python reads this to determine the machine's current state.
# hmiState=0 means uninitialized or error — all valid states are nonzero.
# ---------------------------------------------------------------------------

HMI_STATE_VAR: str = "hmiState"

# hmiState integer encoding
STATE_UNINITIALIZED: int = 0  # Not yet set by DMC, or error condition
STATE_IDLE: int = 1           # Machine at rest position, ready
STATE_GRINDING: int = 2       # Grinding cycle active
STATE_SETUP: int = 3          # Setup loop active
STATE_HOMING: int = 4         # Homing sequence active

# ---------------------------------------------------------------------------
# Position variable names — rest points
# Individual named variables (not arrays) so each name fits the 8-char limit
# and can be read/written individually via gclib MG/GV commands.
# Declared in DMC #PARAMS: restPtA, restPtB, restPtC, restPtD
# ---------------------------------------------------------------------------

RESTPT_A: str = "restPtA"  # Rest position for A axis
RESTPT_B: str = "restPtB"  # Rest position for B axis
RESTPT_C: str = "restPtC"  # Rest position for C axis
RESTPT_D: str = "restPtD"  # Rest position for D axis

# Ordered list (A-B-C-D) for iteration over all axes
RESTPT_VARS: list[str] = [RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D]

# Mapping from axis letter to rest-point variable name
RESTPT_BY_AXIS: dict[str, str] = {
    "A": RESTPT_A,
    "B": RESTPT_B,
    "C": RESTPT_C,
    "D": RESTPT_D,
}

# ---------------------------------------------------------------------------
# Position variable names — start points
# Declared in DMC #PARAMS: startPtA, startPtB, startPtC, startPtD
# ---------------------------------------------------------------------------

STARTPT_A: str = "startPtA"  # Start/grind position for A axis
STARTPT_B: str = "startPtB"  # Start/grind position for B axis
STARTPT_C: str = "startPtC"  # Start/grind position for C axis
STARTPT_D: str = "startPtD"  # Start/grind position for D axis

# Ordered list (A-B-C-D) for iteration over all axes
STARTPT_VARS: list[str] = [STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D]

# Mapping from axis letter to start-point variable name
STARTPT_BY_AXIS: dict[str, str] = {
    "A": STARTPT_A,
    "B": STARTPT_B,
    "C": STARTPT_C,
    "D": STARTPT_D,
}

# ---------------------------------------------------------------------------
# Knife count variable names
# Session knife count: increments each grind cycle, resets on new session (#NEWSESS)
# Stone knife count: increments each grind cycle, resets only when stone is changed
# Both fit within the 8-character DMC variable name limit.
# ---------------------------------------------------------------------------

CT_SES_KNI: str = "ctSesKni"  # Session knife count (resets each new stone session)
CT_STN_KNI: str = "ctStnKni"  # Stone knife count (cumulative per grindstone)

# ---------------------------------------------------------------------------
# #SHOWPOS label variables — live position from controller thread
# The DMC #SHOWPOS label runs on its own thread, reads _TDA/_TDB/_TDC/_TDD
# every 50ms, and writes decimal positions into these variables plus a ring
# buffer. Reading these does NOT disturb the controller during grinding.
# ---------------------------------------------------------------------------

APOS: str = "aPos"   # Live A-axis position (decimal, set by #SHOWPOS)
BPOS: str = "bPos"   # Live B-axis position (decimal, set by #SHOWPOS)
CPOS: str = "cPos"   # Live C-axis position (decimal, set by #SHOWPOS)
DPOS: str = "dPos"   # Live D-axis position (decimal, set by #SHOWPOS)

POS_BY_AXIS: dict[str, str] = {
    "A": APOS,
    "B": BPOS,
    "C": CPOS,
    "D": DPOS,
}

# Ring buffer index and arrays (written by #SHOWPOS, 300 elements each)
POS_BUF_IDX: str = "idx"       # Current write index in ring buffer (0-299)
POS_BUF_A: str = "aBuf"        # Ring buffer array for A-axis positions
POS_BUF_B: str = "bBuf"        # Ring buffer array for B-axis positions
POS_BUF_C: str = "cBuf"        # Ring buffer array for C-axis positions
POS_BUF_D: str = "dBuf"        # Ring buffer array for D-axis positions
POS_BUF_SIZE: int = 300         # Ring buffer capacity

# ---------------------------------------------------------------------------
# Serration bComp array variable names
# TODO: verify exact names against real Serration DMC program (customer to confirm)
# ---------------------------------------------------------------------------

BCOMP_ARRAY: str = "bComp"      # DMC array variable for per-serration B-axis compensation
BCOMP_NUM_SERR: str = "numSerr" # DMC variable for number of serrations

# ---------------------------------------------------------------------------
# Serration-only infeed control variables (NOT used by Flat or Convex)
# See "3 Axis Serration grind.dmc" #PARAMS / #VARCALC / #GRIND.
# ---------------------------------------------------------------------------

SERR_EDGE_LEFT: str = "edgeLef"  # mm - estimated remaining edge stock after flat grind (reference)
SERR_GRIND_DP:  str = "grindDp"  # mm - B infeed past startPtB per tooth (actual bite depth)
SERR_B_CLEAR:   str = "bClear"   # mm - extra B pullback after grinding for clearance

# ---------------------------------------------------------------------------
# Mega-batch MG command — reads all 8 poll values in a single controller call.
# Uses _TD (told/desired position) NOT _TP (actual encoder position).
# Response: 8 space-delimited floats: a, b, c, d, dmc_state, ses_kni, stn_kni, xq_raw
# CRITICAL: Do NOT change _TDA/_TDB/_TDC/_TDD to _TPA/_TPB/_TPC/_TPD.
# ---------------------------------------------------------------------------

BATCH_CMD: str = (
    f"MG _TDA,_TDB,_TDC,_TDD,{HMI_STATE_VAR},{CT_SES_KNI},{CT_STN_KNI},_XQ"
)
