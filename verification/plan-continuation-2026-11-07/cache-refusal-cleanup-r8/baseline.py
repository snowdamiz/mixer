"""Reproduce both actual R3 failures using only the original accounting mocks."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
R3=HERE.parent/'cache-custody-fix-r3'
sys.dont_write_bytecode=True
def audit(event,args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Baseline permits fake process APIs only')
sys.addaudithook(audit)
spec=importlib.util.spec_from_file_location('r3_baseline_adapter',R3/'adopt_fixture.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
a.verify();a.previous()
import local_support
from control_source import control_source
source=control_source()
local_support.HERE=HERE
local_support.write_guard()
module,destination=local_support.workspace('baseline-optimized' if sys.flags.optimize else 'baseline-normal',source)
a.install(module.r)
names=['test_mocked_cpu_timeout_retains_failure_and_aggregate','test_mocked_cpu_custody_hold_withholds_delta']
suite=unittest.TestSuite(module.RunnerControls(name) for name in names)
result=unittest.TextTestRunner(verbosity=2).run(suite)
expected=(result.testsRun==2 and len(result.errors)==1 and len(result.failures)==1
          and "KeyError: 'cleanup_deadline'" in result.errors[0][1]
          and '[call(-1)] != [call(-1), call(-1)]' in result.failures[0][1])
local_support.save(destination/'result.json',{'tests':result.testsRun,'expected_both_failures_reproduced':expected,
    'errors':[(str(c),e) for c,e in result.errors],'failures':[(str(c),e) for c,e in result.failures]})
sys.exit(0 if expected else 1)
