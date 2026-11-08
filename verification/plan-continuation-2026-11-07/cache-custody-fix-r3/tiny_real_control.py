"""NOT RUN. One root-selected tiny descendant control after independent review."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def child():
    import adopt_fixture
    proof=adopt_fixture.verify()
    output=HERE/'tiny-real-child';output.mkdir()
    runner=adopt_fixture.install(adopt_fixture.previous().previous().load_runner(output))
    scratch=output/'scratch';scratch.mkdir()
    commands=runner.Commands(output,{'commands':[]},time.monotonic()+12)
    commands.bind_scratch(scratch)
    # A single fresh group: leader exits while its child retains both pipe writers.
    payload="import subprocess,sys; subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(4)']); print('leader-exit',flush=True)"
    runner.CHILD_SECONDS=.25
    observed=None
    try:commands.run('tiny-descendant',[sys.executable,'-B','-c',payload],output)
    except BaseException as error:observed=error
    row=commands.receipt['commands'][-1]
    passed=(isinstance(observed,RuntimeError) and row['timed_out'] and row['child_returned'] and row['owned_group_gone'] and row['stdout_eof'] and row['stderr_eof'] and not row['custody_hold'] and not row['unknown_custody'])
    if passed:
        # Exact empty command-tmp only; retained command evidence stays outside scratch.
        (scratch/'command-tmp').rmdir();scratch.rmdir()
    (output/'result.json').write_text(json.dumps({'passed':passed,'scratch_retained':scratch.exists(),'exception':repr(observed),'adoption':proof,'first_historical_EPERM_cause_resolved':False},indent=2)+'\n')
    return 0 if passed else 1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--child',action='store_true');args=parser.parse_args()
    if args.child:return child()
    control=HERE.parent/'native-custody-premise/cleanup_control.py'
    if hashlib.sha256(control.read_bytes()).hexdigest()!='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df':raise RuntimeError('Accepted controller drift')
    spec=importlib.util.spec_from_file_location('accepted_tiny_outer',control);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    out=HERE/'tiny-real-supervision';out.mkdir()
    scratch=out/'scratch';scratch.mkdir()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch))
    c=m.Commands(out,env,deadline=time.monotonic()+25,output_bytes=8*1024*1024,total_output_bytes=16*1024*1024,cleanup_seconds=5)
    error=None
    try:c.run('tiny-descendant-control',[sys.executable,'-B',str(Path(__file__).resolve()),'--child'],ROOT,timeout=20,allowed=(0,1))
    except BaseException as e:error=repr(e)
    result=c.cleanup(scratch)
    (out/'result.json').write_text(json.dumps({'cleanup':result,'error':error,'scope':'One fresh tiny control, not original36 or compiler suite; no retry'},indent=2)+'\n')
    return 0 if error is None and c.records[-1]['exit_code']==0 and result['allTerminalCustody'] else 1
if __name__=='__main__':sys.exit(main())
