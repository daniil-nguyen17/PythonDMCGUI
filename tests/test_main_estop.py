"""Tests for e_stop() and recover() methods in DMCApp (main.py).

These tests exercise the inner do_estop / do_recover functions directly
without starting a full Kivy app. The tests mock jobs, controller, and
Clock to keep execution headless.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')


def _make_app():
    """Create a minimal DMCApp-like object without starting Kivy."""
    from dmccodegui.main import DMCApp
    from dmccodegui.app_state import MachineState
    from dmccodegui.controller import GalilController

    app = DMCApp.__new__(DMCApp)
    app.state = MachineState()
    app.controller = MagicMock(spec=GalilController)
    app.controller.is_connected.return_value = True
    app.banner_text = ""
    app._log_message = MagicMock()
    return app


class TestEStop(unittest.TestCase):

    def test_estop_uses_submit_urgent(self):
        """e_stop() must call jobs.submit_urgent, never jobs.submit."""
        app = _make_app()

        with patch('dmccodegui.utils.jobs.submit_urgent') as mock_urgent, \
             patch('dmccodegui.utils.jobs.submit') as mock_submit:
            app.e_stop()
            mock_urgent.assert_called_once()
            mock_submit.assert_not_called()

    def test_estop_commands_order(self):
        """do_estop inner function must call cmd('ST ABCD') then cmd('HX') in order."""
        app = _make_app()
        captured_fn = []

        def capture_urgent(fn, *a, **kw):
            captured_fn.append(fn)

        with patch('dmccodegui.utils.jobs.submit_urgent', side_effect=capture_urgent):
            app.e_stop()

        assert len(captured_fn) == 1, "submit_urgent must be called exactly once"

        # Run the captured inner function directly
        captured_fn[0]()

        calls = app.controller.cmd.call_args_list
        cmd_args = [c[0][0] for c in calls]
        assert 'ST ABCD' in cmd_args, f"Expected 'ST ABCD' in cmd calls, got {cmd_args}"
        assert 'HX' in cmd_args, f"Expected 'HX' in cmd calls, got {cmd_args}"
        # Verify order: ST ABCD before HX
        assert cmd_args.index('ST ABCD') < cmd_args.index('HX'), \
            f"ST ABCD must come before HX; got order: {cmd_args}"

    def test_estop_calls_reset_handle(self):
        """do_estop must call controller.reset_handle() after HX."""
        app = _make_app()
        app.controller.reset_handle = MagicMock(return_value=True)
        captured_fn = []

        def capture_urgent(fn, *a, **kw):
            captured_fn.append(fn)

        with patch('dmccodegui.utils.jobs.submit_urgent', side_effect=capture_urgent):
            app.e_stop()

        captured_fn[0]()
        app.controller.reset_handle.assert_called_once()

    def test_estop_stays_connected(self):
        """e_stop must NOT call controller.disconnect() and must NOT navigate to setup."""
        app = _make_app()
        app.controller.disconnect = MagicMock()

        # Give app a mock root so we can detect navigation
        mock_root = MagicMock()
        mock_sm = MagicMock()
        mock_root.ids.sm = mock_sm
        app.root = mock_root

        captured_fn = []

        def capture_urgent(fn, *a, **kw):
            captured_fn.append(fn)

        with patch('dmccodegui.utils.jobs.submit_urgent', side_effect=capture_urgent), \
             patch('dmccodegui.main.Clock'):
            app.e_stop()
            captured_fn[0]()

        app.controller.disconnect.assert_not_called()
        # Navigation must not set screen to 'setup'
        for c in mock_sm.mock_calls:
            if 'current' in str(c) and 'setup' in str(c):
                self.fail(f"e_stop must not navigate to setup screen; got call: {c}")

    def test_recover_sends_xq_auto(self):
        """The do_recover inner function must call cmd('XQ #AUTO')."""
        app = _make_app()
        captured_submit = []

        def capture_submit(fn, *a, **kw):
            captured_submit.append(fn)

        with patch('dmccodegui.utils.jobs.submit', side_effect=capture_submit), \
             patch('kivy.uix.modalview.ModalView.open'), \
             patch('kivy.uix.modalview.ModalView.dismiss'):
            # Directly call recover and simulate confirmation
            # We need to capture the do_recover function that _confirm would call
            original_recover = app.recover

            confirm_callbacks = []

            class _MockModal:
                def add_widget(self, w): pass
                def open(self): pass
                def dismiss(self): pass

            class _MockBoxLayout:
                def add_widget(self, w): pass

            class _MockButton:
                _callbacks = {}
                def bind(self, **kwargs):
                    for k, v in kwargs.items():
                        _MockButton._callbacks[k] = v
                def add_widget(self, w): pass

            class _MockLabel:
                def __init__(self, **kw): pass
                def add_widget(self, w): pass

            with patch('kivy.uix.modalview.ModalView', return_value=_MockModal()), \
                 patch('kivy.uix.boxlayout.BoxLayout', return_value=_MockBoxLayout()), \
                 patch('kivy.uix.button.Button') as MockBtn, \
                 patch('kivy.uix.label.Label', return_value=_MockLabel()):

                # Collect the _confirm function by tracking Button creation
                confirm_fn_holder = []

                def mock_button(**kwargs):
                    btn = MagicMock()
                    def bind_side_effect(**bkw):
                        if 'on_release' in bkw:
                            confirm_fn_holder.append(bkw['on_release'])
                    btn.bind.side_effect = bind_side_effect
                    return btn

                MockBtn.side_effect = mock_button

                app.recover()

            # Trigger the confirm callback if captured
            if confirm_fn_holder:
                confirm_fn_holder[0]()  # call _confirm

        # Now run the do_recover function submitted to jobs.submit
        if captured_submit:
            captured_submit[0]()
            app.controller.cmd.assert_called_with("XQ #AUTO")

    def test_recover_uses_normal_submit(self):
        """recover() confirmation must use jobs.submit (NOT submit_urgent) for do_recover."""
        app = _make_app()
        captured_submit = []
        captured_urgent = []

        def capture_submit(fn, *a, **kw):
            captured_submit.append(fn)

        def capture_urgent(fn, *a, **kw):
            captured_urgent.append(fn)

        with patch('dmccodegui.utils.jobs.submit', side_effect=capture_submit), \
             patch('dmccodegui.utils.jobs.submit_urgent', side_effect=capture_urgent):

            class _MockModal:
                def add_widget(self, w): pass
                def open(self): pass
                def dismiss(self): pass

            class _MockBoxLayout:
                def add_widget(self, w): pass

            class _MockLabel:
                def __init__(self, **kw): pass

            confirm_fn_holder = []

            with patch('kivy.uix.modalview.ModalView', return_value=_MockModal()), \
                 patch('kivy.uix.boxlayout.BoxLayout', return_value=_MockBoxLayout()), \
                 patch('kivy.uix.button.Button') as MockBtn, \
                 patch('kivy.uix.label.Label', return_value=_MockLabel()):

                def mock_button(**kwargs):
                    btn = MagicMock()
                    def bind_side_effect(**bkw):
                        if 'on_release' in bkw:
                            confirm_fn_holder.append(bkw['on_release'])
                    btn.bind.side_effect = bind_side_effect
                    return btn

                MockBtn.side_effect = mock_button
                app.recover()

            # Trigger confirm
            if confirm_fn_holder:
                confirm_fn_holder[0]()

        assert len(captured_submit) >= 1, \
            "recover() must call jobs.submit (not submit_urgent) for do_recover"
        assert len(captured_urgent) == 0, \
            "recover() must NOT call jobs.submit_urgent"


if __name__ == '__main__':
    unittest.main()
