"""Actual stdlib descriptor checks for revocation, nesting, and unchanged boundaries."""
import contextvars
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
import stdin_guard as guard
from descriptor_preflight import no_children
HERE = Path(__file__).resolve().parent
MODE = 'optimized' if sys.flags.optimize else 'normal'
OUT = HERE / ('scope-' + MODE)
OUT.mkdir()
sys.addaudithook(no_children)
guard.write_guard(HERE)
observations = []

class ScopeControls(unittest.TestCase):
    def devnull(self, method=None):
        obj = object.__new__(subprocess.Popen)
        try:
            fd = (method or subprocess.Popen._get_devnull)(obj)
            self.assertEqual(os.read(fd, 1), b'')
        finally:
            if hasattr(obj, '_devnull'):
                os.close(obj._devnull)

    def denied(self, context):
        with self.assertRaisesRegex(RuntimeError, 'Write outside owned correction'):
            context.run(self.devnull)

    def call(self, fn):
        return guard.run_direct(types.SimpleNamespace(run=fn), [], HERE)

    def test_copied_context_cannot_outlive_run_direct(self):
        captured = []
        def run(*args, **kwargs):
            captured.append(contextvars.copy_context())
            captured[0].run(self.devnull)
        self.call(run)
        self.assertIsNone(guard._stdin_scope.get())
        self.assertFalse(captured[0].get(guard._stdin_scope).active)
        self.denied(captured[0])
        observations.append({'case': self._testMethodName, 'caller_active': False,
                             'captured_active': False, 'devnull_open_after_run_direct_allowed': False})

    def test_nested_inner_exit_keeps_outer_active_then_revokes_both(self):
        captured = {}
        def inner(*args, **kwargs):
            captured['inner'] = contextvars.copy_context()
            self.devnull()
        def outer(*args, **kwargs):
            captured['outer'] = contextvars.copy_context()
            outer_capability = guard._stdin_scope.get()
            self.call(inner)
            self.assertIs(guard._stdin_scope.get(), outer_capability)
            self.assertTrue(outer_capability.active)
            self.denied(captured['inner'])
            captured['outer'].run(self.devnull)
            self.devnull()
            self.denied(contextvars.Context())
        self.call(outer)
        self.assertIsNot(captured['inner'].get(guard._stdin_scope), captured['outer'].get(guard._stdin_scope))
        for context in captured.values():
            self.assertFalse(context.get(guard._stdin_scope).active)
            self.denied(context)
        observations.append({'case': self._testMethodName, 'inner_revoked_while_outer_active': True,
                             'outer_admitted_after_inner_exit': True, 'both_denied_after_outer_exit': True})

    def test_exception_exit_revokes_copied_contexts(self):
        for error in [ValueError('synthetic'), KeyboardInterrupt('synthetic'), SystemExit('synthetic')]:
            with self.subTest(error=type(error).__name__):
                captured = []
                def fail(*args, **kwargs):
                    captured.append(contextvars.copy_context())
                    raise error
                with self.assertRaises(type(error)) as raised:
                    self.call(fail)
                self.assertIs(raised.exception, error)
                self.assertIsNone(guard._stdin_scope.get())
                self.denied(captured[0])
                self.assertFalse(captured[0].get(guard._stdin_scope).active)

    def test_nested_exception_preserves_outer_and_revokes_inner(self):
        captured = []
        def inner(*args, **kwargs):
            captured.append(contextvars.copy_context())
            raise ValueError('synthetic inner failure')
        def outer(*args, **kwargs):
            captured.append(contextvars.copy_context())
            with self.assertRaises(ValueError):
                self.call(inner)
            self.denied(captured[1])
            captured[0].run(self.devnull)
            self.devnull()
        self.call(outer)
        for context in captured:
            self.denied(context)

    def test_fresh_sibling_denied_and_old_copies_never_revived(self):
        captured = []
        self.call(lambda *a, **k: captured.append(contextvars.copy_context()))
        copied_again = captured[0].copy()
        def next_entry(*args, **kwargs):
            self.denied(contextvars.Context())
            self.denied(captured[0])
            self.denied(copied_again)
            self.devnull()
        self.call(next_entry)
        for context in [captured[0], copied_again, contextvars.copy_context()]:
            self.denied(context)

    def test_exact_original_code_path_and_flags(self):
        original = subprocess.Popen._get_devnull
        variants = [('/dev/null', os.O_WRONLY), ('/dev/null', os.O_RDWR | os.O_TRUNC),
                    ('/dev/null', os.O_RDWR | os.O_CREAT), ('/dev/null', os.O_RDWR | os.O_APPEND),
                    ('/dev/./null', os.O_RDWR), (str(HERE.parent / 'forbidden-r6'), os.O_RDWR | os.O_CREAT)]
        def check(*args, **kwargs):
            self.devnull()
            for path, flags in variants:
                with self.subTest(path=path, flags=flags):
                    globals_copy = dict(original.__globals__, os=types.SimpleNamespace(devnull=path, O_RDWR=flags, open=os.open))
                    method = types.FunctionType(original.__code__, globals_copy)
                    self.assertIs(method.__code__, guard._devnull_code)
                    with self.assertRaisesRegex(RuntimeError, 'Write outside owned correction'):
                        self.devnull(method)
        self.call(check)
        self.assertIs(subprocess.Popen._get_devnull, original)

    def test_impostor_code_and_direct_open_refused(self):
        space = {'os': os}
        exec(compile('def _get_devnull(obj): return os.open(os.devnull, os.O_RDWR)', subprocess.__file__, 'exec'), space)
        def check(*args, **kwargs):
            with self.assertRaisesRegex(RuntimeError, 'Write outside owned correction'):
                self.devnull(space['_get_devnull'])
            with self.assertRaisesRegex(RuntimeError, 'Write outside owned correction'):
                os.open('/dev/null', os.O_RDWR)
        self.call(check)

    def test_descriptor_failure_revokes_capability(self):
        captured = []
        def fail(*args, **kwargs):
            captured.append(contextvars.copy_context())
            os.open('/dev/null', os.O_RDWR)  # Direct open must remain forbidden.
        with self.assertRaisesRegex(RuntimeError, 'Write outside owned correction'):
            self.call(fail)
        self.denied(captured[0])
        self.assertIsNone(guard._stdin_scope.get())

result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScopeControls))
(OUT / 'result.json').write_text(json.dumps({'tests': result.testsRun, 'successful': result.wasSuccessful(),
    'failures': [(str(t),e) for t,e in result.failures], 'errors': [(str(t),e) for t,e in result.errors],
    'observations': observations, 'real_inner_children': 0, 'stdlib_modified': False}, indent=2) + '\n')
sys.exit(0 if result.wasSuccessful() else 1)
