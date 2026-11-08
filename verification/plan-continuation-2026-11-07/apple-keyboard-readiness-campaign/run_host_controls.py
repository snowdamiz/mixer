"""Exactly two fake-host children under the unchanged accepted lifecycle."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
LIFECYCLE=HERE.parent/'native-custody-premise/cleanup_control.py'
EXPECTED='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
if hashlib.sha256(LIFECYCLE.read_bytes()).hexdigest()!=EXPECTED:
    raise RuntimeError('Accepted lifecycle changed')
spec=importlib.util.spec_from_file_location('accepted_cleanup_supervisor',LIFECYCLE)
life=importlib.util.module_from_spec(spec);spec.loader.exec_module(life)


def main():
    from review_candidate import check,sha
    seal_sha=sha(HERE/'candidate-seal.json')
    before=check(seal_sha)
    out=HERE/'control-supervisor';out.mkdir(exist_ok=False)
    scratch=out/'scratch';scratch.mkdir()
    manager=life.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
        deadline=time.monotonic()+250,output_bytes=4*life.MIB,total_output_bytes=32*life.MIB)
    receipt=dict(argv=[sys.executable,'-B',str(Path(__file__).resolve())],
        maximumInvocations=2,maximumSecondsPerInvocation=120,status='failed',
        sourceRevision='62ce9b76840b2fa56306736fc4c4fe2962780adf',python=sys.version,
        executableSHA256=sha(Path(sys.executable).resolve()),candidateSealSHA256=seal_sha,
        lifecycleSHA256=EXPECTED,preflight=before,nativeAttempts=0,UIActions=0)
    try:
        for mode in ('normal','optimized'):
            argv=[sys.executable,'-B',*(['-O'] if mode=='optimized' else []),str(HERE/'harness/review_tests.py')]
            # Completed test failure permits the second mode; unknown custody
            # closes the accepted manager's admission gate.
            manager.run(mode,argv,HERE.parents[2],120,allowed=(0,1))
        receipt['status']='passed' if all(row['exit_code']==0 for row in manager.records) else 'tests-failed'
    except BaseException as error:
        receipt['error']=repr(error)
    finally:
        receipt['cleanup']=manager.cleanup(scratch)
        receipt['commands']=manager.records
        if not receipt['cleanup']['allTerminalCustody']:receipt['status']='failed'
        try:receipt['postflight']=check(seal_sha)
        except BaseException as error:
            receipt['postflightError']=repr(error);receipt['status']='failed'
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'],invocations=len(manager.records),cleanup=receipt['cleanup'])))
    return 0 if receipt['status']=='passed' else 1


if __name__=='__main__':sys.exit(main())
