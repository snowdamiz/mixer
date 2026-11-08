"""Execute the R5 counterexample before repair, with zero inner processes."""
import ast
import contextvars
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest import mock
OWN = Path(__file__).resolve().parent
R5 = OWN.parent / 'cache-supervision-premise-r5'
MODE = 'optimized' if sys.flags.optimize else 'normal'
OUT = OWN / ('baseline-' + MODE)
OUT.mkdir()
spec = importlib.util.spec_from_file_location('stdin_guard', R5 / 'stdin_guard.py')
guard = importlib.util.module_from_spec(spec)
sys.modules['stdin_guard'] = guard
spec.loader.exec_module(guard)
def forbid(event, args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Pure baseline forbids process/network operations')
sys.addaudithook(forbid)
guard.write_guard(OWN)

def definitions(path, namespace, names, imports=False):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    body = [n for n in tree.body if (imports and isinstance(n, (ast.Import, ast.ImportFrom))) or
            (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names)]
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), namespace)

prior = types.ModuleType('prior_guard_controls')
prior.__dict__.update(HERE=OWN, __file__=str(R5 / 'test_stdin_premise.py'))
definitions(R5 / 'test_stdin_premise.py', prior.__dict__, {'Controls'}, True)
prior_result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(prior.Controls))
review = OWN.parent / 'cache-supervision-review-r5/campaign-optimized/executed-review.py'
namespace = dict(guard=guard, OWN=OWN, EVIDENCE=OUT, subprocess=subprocess, contextvars=contextvars,
                 types=types, unittest=unittest, os=os, sys=sys, json=json)
definitions(review, namespace, {'Independent'})
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
    namespace['Independent']('test_copied_context_cannot_outlive_run_direct')]))
observed = json.loads((OUT / 'copied-context.json').read_bytes())
expected = (prior_result.wasSuccessful() and prior_result.testsRun == 6 and result.testsRun == 1
            and len(result.failures) == 1 and not result.errors and observed == {
                'caller_scope_after': False, 'captured_scope_after': True,
                'devnull_open_after_run_direct_allowed': True, 'real_children': 0})
(OUT / 'result.json').write_text(json.dumps({
    'expected_baseline_reproduced': expected, 'mode': MODE,
    'prior_guards': {'tests': prior_result.testsRun, 'successful': prior_result.wasSuccessful(),
                     'failures': [(str(t),e) for t,e in prior_result.failures],
                     'errors': [(str(t),e) for t,e in prior_result.errors]},
    'counterexample': {'tests': result.testsRun, 'successful': result.wasSuccessful(),
                       'failures': [(str(t),e) for t,e in result.failures],
                       'errors': [(str(t),e) for t,e in result.errors]},
    'guard_sha256': hashlib.sha256((R5/'stdin_guard.py').read_bytes()).hexdigest(),
    'review_sha256': hashlib.sha256(review.read_bytes()).hexdigest(),
    'actual_R5_guard': True, 'actual_original_stdlib_method': True, 'real_inner_children': 0
}, indent=2) + '\n')
sys.exit(0 if expected else 1)
