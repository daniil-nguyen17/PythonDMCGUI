"""Unit tests for dmccodegui.hmi.dmc_vars constants module and MachineState.dmc_state field."""
from __future__ import annotations

import glob
import os
import re

import pytest


# ---------------------------------------------------------------------------
# HMI trigger variable name constants
# ---------------------------------------------------------------------------

class TestHmiTriggerConstants:
    """All 8 HMI trigger variable name constants have correct values and fit 8-char limit."""

    def test_hmi_grnd_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_GRND
        assert HMI_GRND == "hmiGrnd"

    def test_hmi_setp_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_SETP
        assert HMI_SETP == "hmiSetp"

    def test_hmi_more_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_MORE
        assert HMI_MORE == "hmiMore"

    def test_hmi_less_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_LESS
        assert HMI_LESS == "hmiLess"

    def test_hmi_news_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_NEWS
        assert HMI_NEWS == "hmiNewS"

    def test_hmi_home_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_HOME
        assert HMI_HOME == "hmiHome"

    def test_hmi_jog_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_JOG
        assert HMI_JOG == "hmiJog"

    def test_hmi_calc_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_CALC
        assert HMI_CALC == "hmiCalc"

    def test_all_trigger_names_8_chars_or_fewer(self):
        from dmccodegui.hmi.dmc_vars import (
            HMI_GRND, HMI_SETP, HMI_MORE, HMI_LESS,
            HMI_NEWS, HMI_HOME, HMI_JOG, HMI_CALC,
        )
        for name in (HMI_GRND, HMI_SETP, HMI_MORE, HMI_LESS,
                     HMI_NEWS, HMI_HOME, HMI_JOG, HMI_CALC):
            assert len(name) <= 8, f"{name!r} exceeds 8-char DMC limit"

    def test_all_hmi_triggers_list_has_8_items(self):
        from dmccodegui.hmi.dmc_vars import ALL_HMI_TRIGGERS
        assert len(ALL_HMI_TRIGGERS) == 8

    def test_all_hmi_triggers_list_contains_all_vars(self):
        from dmccodegui.hmi.dmc_vars import (
            ALL_HMI_TRIGGERS,
            HMI_GRND, HMI_SETP, HMI_MORE, HMI_LESS,
            HMI_NEWS, HMI_HOME, HMI_JOG, HMI_CALC,
        )
        for var in (HMI_GRND, HMI_SETP, HMI_MORE, HMI_LESS,
                    HMI_NEWS, HMI_HOME, HMI_JOG, HMI_CALC):
            assert var in ALL_HMI_TRIGGERS


# ---------------------------------------------------------------------------
# Trigger default values
# ---------------------------------------------------------------------------

class TestTriggerDefaults:
    def test_trigger_default_is_1(self):
        from dmccodegui.hmi.dmc_vars import HMI_TRIGGER_DEFAULT
        assert HMI_TRIGGER_DEFAULT == 1

    def test_trigger_fire_is_0(self):
        from dmccodegui.hmi.dmc_vars import HMI_TRIGGER_FIRE
        assert HMI_TRIGGER_FIRE == 0


# ---------------------------------------------------------------------------
# State variable and encoding constants
# ---------------------------------------------------------------------------

class TestHmiStateConstants:
    def test_hmi_state_var_value(self):
        from dmccodegui.hmi.dmc_vars import HMI_STATE_VAR
        assert HMI_STATE_VAR == "hmiState"

    def test_hmi_state_var_8_chars_or_fewer(self):
        from dmccodegui.hmi.dmc_vars import HMI_STATE_VAR
        assert len(HMI_STATE_VAR) <= 8

    def test_state_uninitialized_is_0(self):
        from dmccodegui.hmi.dmc_vars import STATE_UNINITIALIZED
        assert STATE_UNINITIALIZED == 0

    def test_state_idle_is_1(self):
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        assert STATE_IDLE == 1

    def test_state_grinding_is_2(self):
        from dmccodegui.hmi.dmc_vars import STATE_GRINDING
        assert STATE_GRINDING == 2

    def test_state_setup_is_3(self):
        from dmccodegui.hmi.dmc_vars import STATE_SETUP
        assert STATE_SETUP == 3

    def test_state_homing_is_4(self):
        from dmccodegui.hmi.dmc_vars import STATE_HOMING
        assert STATE_HOMING == 4

    def test_all_valid_states_nonzero(self):
        from dmccodegui.hmi.dmc_vars import STATE_IDLE, STATE_GRINDING, STATE_SETUP, STATE_HOMING
        for s in (STATE_IDLE, STATE_GRINDING, STATE_SETUP, STATE_HOMING):
            assert s != 0, f"Valid state {s} must be nonzero"


# ---------------------------------------------------------------------------
# Position variable constants — rest points
# ---------------------------------------------------------------------------

class TestRestPointConstants:
    def test_restpt_a_value(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_A
        assert RESTPT_A == "restPtA"

    def test_restpt_b_value(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_B
        assert RESTPT_B == "restPtB"

    def test_restpt_c_value(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_C
        assert RESTPT_C == "restPtC"

    def test_restpt_d_value(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_D
        assert RESTPT_D == "restPtD"

    def test_all_restpt_names_8_chars_or_fewer(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D
        for name in (RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D):
            assert len(name) <= 8, f"{name!r} exceeds 8-char DMC limit"

    def test_restpt_vars_list_order(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_VARS, RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D
        assert RESTPT_VARS == [RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D]

    def test_restpt_vars_has_4_items(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_VARS
        assert len(RESTPT_VARS) == 4

    def test_restpt_by_axis_map(self):
        from dmccodegui.hmi.dmc_vars import RESTPT_BY_AXIS, RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D
        assert RESTPT_BY_AXIS["A"] == RESTPT_A
        assert RESTPT_BY_AXIS["B"] == RESTPT_B
        assert RESTPT_BY_AXIS["C"] == RESTPT_C
        assert RESTPT_BY_AXIS["D"] == RESTPT_D


# ---------------------------------------------------------------------------
# Position variable constants — start points
# ---------------------------------------------------------------------------

class TestStartPointConstants:
    def test_startpt_a_value(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_A
        assert STARTPT_A == "startPtA"

    def test_startpt_b_value(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_B
        assert STARTPT_B == "startPtB"

    def test_startpt_c_value(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_C
        assert STARTPT_C == "startPtC"

    def test_startpt_d_value(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_D
        assert STARTPT_D == "startPtD"

    def test_all_startpt_names_8_chars_or_fewer(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D
        for name in (STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D):
            assert len(name) <= 8, f"{name!r} exceeds 8-char DMC limit"

    def test_startpt_vars_list_order(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_VARS, STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D
        assert STARTPT_VARS == [STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D]

    def test_startpt_vars_has_4_items(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_VARS
        assert len(STARTPT_VARS) == 4

    def test_startpt_by_axis_map(self):
        from dmccodegui.hmi.dmc_vars import STARTPT_BY_AXIS, STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D
        assert STARTPT_BY_AXIS["A"] == STARTPT_A
        assert STARTPT_BY_AXIS["B"] == STARTPT_B
        assert STARTPT_BY_AXIS["C"] == STARTPT_C
        assert STARTPT_BY_AXIS["D"] == STARTPT_D


# ---------------------------------------------------------------------------
# No stale string literals in screen files (xfail until Plan 09-03)
# ---------------------------------------------------------------------------

def test_no_stale_position_strings_in_screen_files():
    """Assert no screen file uses raw 'StartPnt' or 'RestPnt' string literals.

    This test is expected to fail until plan 09-03 migrates all screen files
    to import from dmc_vars.py.
    """
    screens_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "src", "dmccodegui", "screens",
    )
    screen_files = glob.glob(os.path.join(screens_dir, "*.py"))
    assert screen_files, "No screen files found — check path"

    stale_pattern = re.compile(r'["\'](?:StartPnt|RestPnt)["\']')
    violations: list[str] = []
    for fpath in screen_files:
        with open(fpath, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                # Skip comment lines
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                if stale_pattern.search(line):
                    violations.append(f"{os.path.basename(fpath)}:{lineno}: {line.rstrip()}")

    assert not violations, (
        f"Found {len(violations)} stale string literal(s):\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Knife count variable name constants
# ---------------------------------------------------------------------------

class TestKnifeCountConstants:
    """CT_SES_KNI and CT_STN_KNI constants have correct values and fit 8-char limit."""

    def test_ct_ses_kni_constant(self):
        from dmccodegui.hmi.dmc_vars import CT_SES_KNI
        assert CT_SES_KNI == "ctSesKni"

    def test_ct_stn_kni_constant(self):
        from dmccodegui.hmi.dmc_vars import CT_STN_KNI
        assert CT_STN_KNI == "ctStnKni"

    def test_ct_ses_kni_length(self):
        from dmccodegui.hmi.dmc_vars import CT_SES_KNI
        assert len(CT_SES_KNI) <= 8, f"{CT_SES_KNI!r} exceeds 8-char DMC limit"

    def test_ct_stn_kni_length(self):
        from dmccodegui.hmi.dmc_vars import CT_STN_KNI
        assert len(CT_STN_KNI) <= 8, f"{CT_STN_KNI!r} exceeds 8-char DMC limit"


# ---------------------------------------------------------------------------
# MachineState.dmc_state field
# ---------------------------------------------------------------------------

class TestMachineStateDmcState:
    def test_dmc_state_default_is_0(self):
        from dmccodegui.app_state import MachineState
        ms = MachineState()
        assert ms.dmc_state == 0

    def test_dmc_state_is_int(self):
        from dmccodegui.app_state import MachineState
        ms = MachineState()
        assert isinstance(ms.dmc_state, int)

    def test_dmc_state_field_exists(self):
        from dmccodegui.app_state import MachineState
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(MachineState)]
        assert "dmc_state" in field_names
