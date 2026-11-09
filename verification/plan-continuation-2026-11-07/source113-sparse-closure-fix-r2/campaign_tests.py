#!/usr/bin/env python3
"""Retain bootstrap assertions and envelope suites in one pure/fake payload."""
from pathlib import Path
import importlib.util
import json
import sys
import runpy
import subprocess
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def load(name, p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
broad=load('campaign_guard',ROOT/'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
broad.install(Path("/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/source113-sparse-closure-fix-r2/scratch-remainder"))
results=[]
bootstrap=Path("/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/source113-sparse-closure-fix-r2/scratch-remainder/auxiliary-controls/verification/plan-continuation-2026-11-07/generated-java-ci-integration")
for name,cls,count in [('test_bootstrap.py','BootstrapControls',28),('test_sparse_checkout.py','SparseControls',12)]:
    module=load('source113_'+cls,bootstrap/name)
    calls=[]
    def fake_git(argv, *, input, stdout, stderr, timeout, check):
        # Deliberately fake six-directory path matching. This is not a Git receipt.
        if argv[:2]!=['git','-C'] or timeout!=15 or check is not True:
            raise RuntimeError('Unexpected fake Git invocation')
        rules=Path(argv[argv.index('--rules-file')+1]).read_text().splitlines()
        paths=input.decode().rstrip('\0').split('\0')
        selected=[p for p in paths if any('/'+p==r or r.endswith('/') and ('/'+p).startswith(r) for r in rules)]
        calls.append({'argv':argv,'paths':len(paths),'selected':len(selected)})
        return subprocess.CompletedProcess(argv,0,(''.join(p+'\0' for p in selected)).encode(),b'')
    with patch.object(subprocess,'run',fake_git):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module,cls)))
    results.append({'script':name,'tests':result.testsRun,'expected':count,'passed':result.wasSuccessful(),
                    'skipped':len(result.skipped),'fake_git_calls':calls})
    if not result.wasSuccessful() or result.testsRun!=count: break
if len(results)==2 and all(r['passed'] for r in results):
    for name,count in [('test_binding.py',10),('test_ownership.py',27),('test_rebind.py',12)]:
        sys.argv=[str(HERE/name)]
        try: runpy.run_path(str(HERE/name),run_name='__main__')
        except SystemExit as error: status=0 if error.code is None else error.code
        else: status=0
        results.append({'script':name,'expected_tests':count,'status':status})
        if status!=0: break
closure=load('actual_sparse_closure_regression',HERE/'test_sparse_closure.py')
proof=closure.exercise(ROOT,"verification/plan-continuation-2026-11-07/source113-sparse-closure-fix-r2","/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/source113-sparse-closure-fix-r2/selection-fixed.json",False)
results.append({'script':'test_sparse_closure.py','actual_eight':proof['tests_run'],'membership_pass':proof['membership_pass'],'status':0})
mode='optimized' if sys.flags.optimize else 'normal'
receipt={'mode':mode,'python':sys.version,'executable':sys.executable,'results':results,
         'denied_runtime_attempts':broad.DENIED,
         'scope':'Pure/fake only; sparse test Git responses fake; no compiler, JVM, native, network or consumer run'}
(HERE/('campaign-'+mode+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
sys.exit(0 if len(results)==6 and not broad.DENIED and all(r.get('passed',r.get('status')==0) for r in results) else 1)
