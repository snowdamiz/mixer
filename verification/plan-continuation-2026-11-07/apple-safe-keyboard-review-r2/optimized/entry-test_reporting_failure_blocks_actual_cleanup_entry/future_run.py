"""Future root-only single experiment. This file was NOT executed by this lane."""
import json, sys, traceback
from pathlib import Path
from commands import write, digest
from controller import setup, dispatch, cleanup, require
from mac_backend import MacBackend
from verify_bindings import HERE

def run(folder, reviewed_seal_sha):
    seal_path=HERE/'candidate-seal.json'
    require(digest(seal_path.read_bytes())==reviewed_seal_sha,'Root must bind the reviewed controller seal')
    seal=json.loads(seal_path.read_text())
    for name,expected in seal['sourceFiles'].items():
        require(digest((HERE/name).read_bytes())==expected,'Controller source differs: '+name)
    folder=Path(folder)
    require(folder.resolve()==folder and folder.parent==HERE and not folder.exists(),'Fresh owned output directory required')
    folder.mkdir()
    backend=MacBackend(folder)
    # Even an unavailable preflight has a receipt, but no simulator or marker.
    if not backend.ax_trusted():
        write(folder/'result.json',dict(status='Accessibility unavailable',nativeAttempts=0,devicesCreated=0))
        return
    # One global candidate launch reservation, exclusive and never auto-retried.
    write(HERE/'future-setup-once.json',dict(output=str(folder),reviewedControllerSealSHA256=reviewed_seal_sha))
    owned=None; baseline=None; outcome={}
    try:
        owned,baseline=setup(backend)
        write(folder/'external-baseline.json',baseline)
        plan=dispatch(backend,owned,baseline)
        write(folder/'exact-dispatch-command.json',plan)
        backend.native_dispatch(plan['argv'])
        outcome['native']=json.loads((folder/'dispatch-result.json').read_text())
        native=outcome['native']
        gates=native.get('cleanupResults', [])
        expected={'loopback-server-shutdown','loopback-server-close','loopback-thread-join',
                  'ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation'}
        require(len(gates)==5 and {g.get('resource') for g in gates}==expected and
                all(g.get('passed') is True for g in gates) and native.get('sessionFailure') is None and
                native.get('xcodebuildExitCode') in (0,65) and native.get('reportingFailures')==[],
                'Inner terminal evidence incomplete; retain nested custody')
    except BaseException as error:
        backend.c.unresolved=True
        outcome['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        if owned is not None and baseline is not None:
            try: outcome['outerCleanup']=cleanup(backend,owned,baseline)
            except BaseException as error:
                outcome['cleanupFailure']=str(error)
        outcome['custody']='Retain all files on failure; no frontend quit or held-process operation'
        outcome['gaAccepted']=False
        write(folder/'result.json',outcome)
    require('failure' not in outcome and 'cleanupFailure' not in outcome,'Experiment or cleanup failed; retained receipt')

if __name__=='__main__':
    require(len(sys.argv)==4 and sys.argv[1]=='run-reviewed-once','Explicit root command and seal required')
    run(sys.argv[2],sys.argv[3])
