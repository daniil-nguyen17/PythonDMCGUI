# Deferred Items - Phase 27

## Pre-existing Test Failures (out of scope for 27-01)

The following tests were failing BEFORE phase 27-01 changes were made.
Confirmed by git stash test: same failures on commit ad87b85 (pre-changes).

17 pre-existing failures:
- tests/test_axes_setup.py::test_enter_setup_skips_fire_when_already_setup
- tests/test_delta_c_bar_chart.py::test_offsets_to_delta_c_varied
- tests/test_delta_c_bar_chart.py::test_single_segment_ramp_net_zero
- tests/test_delta_c_bar_chart.py::test_single_segment_cumsum_triangle
- tests/test_main_estop.py::TestEStop::test_estop_commands_order
- tests/test_mg_reader.py::TestStateFilteredFromLog::test_state_message_not_in_log_handlers
- tests/test_mg_reader.py::TestStateFilteredFromLog::test_position_message_not_in_log_handlers
- tests/test_parameters.py::test_enter_skips_fire_when_already_setup
- tests/test_run_screen.py::test_motion_gate_homing
- tests/test_screen_loader.py::test_on_stop_calls_cleanup_on_screens_with_cleanup
- tests/test_screen_loader.py::test_on_stop_does_not_call_nonexistent_cleanup
- tests/test_screen_loader.py::test_on_stop_no_stop_pos_poll_or_stop_mg_reader_called
- tests/test_status_bar.py::TestStatusBarStateLabel::test_state_text_idle
- tests/test_status_bar.py::TestStatusBarStateLabel::test_state_text_grinding
- tests/test_status_bar.py::TestStatusBarStateLabel::test_state_text_setup
- tests/test_status_bar.py::TestStatusBarStateLabel::test_state_text_homing
- tests/test_status_bar.py::TestStatusBarStateLabel::test_state_always_recomputed

These are unrelated to display preset detection and should be addressed in a
separate phase or bug-fix session.
