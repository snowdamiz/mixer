"""Retain real inner custody before test teardown; stop admission on UNKNOWN."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import unittest
from stdin_guard import run_direct

HERE=Path(__file__).resolve().parent
CONTROL=HERE.parent/'native-custody-premise/cleanup_control.py'
CONTROL_SHA='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'

def attach(module, destination):
    if hashlib.sha256(CONTROL.read_bytes()).hexdigest()!=CONTROL_SHA:
        raise RuntimeError('Accepted supervisor drift')
    spec=importlib.util.spec_from_file_location('r4_direct_controller',CONTROL)
    control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
    state=types.SimpleNamespace(records=[],holds=[],direct=[])
    def save():
        (destination/'inner-custody.json').write_text(json.dumps(state.summary(),indent=2)+'\n')
    def summary():
        return {'commands':state.records,'direct_subprocess_controls':state.direct,'holds':state.holds,
                'all_terminal':not state.holds and all(not r['custody_hold'] and (r.get('spawn_error') or all(r[k] for k in ['child_returned','owned_group_gone','stdout_eof','stderr_eof'])) for r in state.records)}
    state.summary=summary
    original_commands=module.RunnerControls.commands
    def commands(case):
        if state.holds:raise RuntimeError('Inner UNKNOWN; campaign admission closed')
        c=original_commands(case)
        original_run=c.run
        def run(*args,**kwargs):
            if state.holds:raise RuntimeError('Inner UNKNOWN; campaign admission closed')
            count=len(c.receipt['commands'])
            try:return original_run(*args,**kwargs)
            finally:
                if len(c.receipt['commands'])>count:
                    row=json.loads(json.dumps(c.receipt['commands'][-1]))
                    row['scratch']=str(c.scratch)
                    state.records.append(row)
                    if c.unknown_custody or c.active is not None:
                        state.holds.append({'pgid':row.get('pgid'),'scratch':str(c.scratch),'row':row})
                        (HERE/'HOLD.json').write_text(json.dumps(state.holds,indent=2)+'\n')
                    save()
        c.run=run
        return c
    module.RunnerControls.commands=commands
    # The original optimized-validation test uses subprocess.run directly.
    # Keep its body/assertions, but route that exact tiny Python command through
    # the accepted controller and retain its separate custody receipt.
    def direct_run(argv,*,capture_output,timeout,cwd):
        if state.holds:raise RuntimeError('Inner UNKNOWN; campaign admission closed')
        if (list(argv[:4])!=[sys.executable,'-B','-O','-c'] or len(argv)!=5
                or not capture_output or timeout!=15 or Path(cwd)!=destination):
            raise RuntimeError('Unexpected direct subprocess control')
        d=destination/'direct-control';d.mkdir()
        scratch=d/'scratch';scratch.mkdir()
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch))
        controller=control.Commands(d,env,deadline=time.monotonic()+20,
            output_bytes=8*1024*1024,total_output_bytes=8*1024*1024,cleanup_seconds=5)
        try:
            run_direct(controller, argv, cwd)
        finally:
            cleanup=controller.cleanup(scratch)
            state.direct.append({'records':controller.records,'cleanup':cleanup})
            if not cleanup['allTerminalCustody']:
                state.holds.append({'direct_control':controller.records,'scratch':str(scratch)})
                (HERE/'HOLD.json').write_text(json.dumps(state.holds,indent=2)+'\n')
            save()
        record=controller.records[-1]
        return subprocess.CompletedProcess(argv,record['exit_code'],
            Path(record['logs']['stdout']).read_bytes(),Path(record['logs']['stderr']).read_bytes())
    module.subprocess=types.SimpleNamespace(run=direct_run)
    class Result(unittest.TextTestResult):
        def stopTest(self,test):
            super().stopTest(test)
            if state.holds:self.stop()
    state.result_class=Result
    return state
