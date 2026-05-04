# Deferred Items -- Phase 31

## Pre-existing Test Failures

3 tests in `tests/test_delta_c_bar_chart.py` fail on current main branch (not introduced by Phase 31):
- `test_offsets_to_delta_c_varied` -- peak index assertion
- `test_single_segment_ramp_net_zero` -- peak index assertion
- `test_single_segment_cumsum_triangle` -- related assertion

These failures exist before any Phase 31 changes and are out of scope.
