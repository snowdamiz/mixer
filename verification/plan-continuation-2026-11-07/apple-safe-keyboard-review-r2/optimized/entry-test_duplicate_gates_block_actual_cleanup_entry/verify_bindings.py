"""Read-only execution of the unchanged accepted verifier, with original paths."""
import hashlib, importlib.util, json, os, stat, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'apple-settings-runtime-r2'
DISPATCH_SHA='5e87b80df1ffef80a1bae0d8f74f0d6291ad45a73a38054df0ef8980e01c40f0'
PACKET_SHA='38850f4a1f9fe8326c101d398823249ad25711c9e5113e6ac3bc95891624cef5'
def identity(p):
    info=p.lstat()
    if p.resolve()!=p or not stat.S_ISREG(info.st_mode): raise ValueError('Noncanonical input '+str(p))
    return dict(bytes=info.st_size,mode=stat.S_IMODE(info.st_mode),sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def verify():
    if identity(OLD/'dispatch_successor.py')['sha256']!=DISPATCH_SHA: raise ValueError('Dispatcher changed')
    prior=json.loads((HERE.parent/'apple-tab-keyboard-runtime-r2/input-identities.json').read_text())
    before={p:identity(Path(p)) for p in prior}
    if before!=prior: raise ValueError('Historical watched inputs differ')
    selection=json.loads((HERE.parent/'apple-tab-keyboard-root-selection.json').read_text())
    for row in [selection['experiment'],*selection['bindings'].values()]:
        if isinstance(row,dict) and 'path' in row:
            if identity(ROOT/row['path'])['sha256']!=row['sha256']: raise ValueError('Selection binding differs')
    active={'value':True}
    def audit(event,args):
        if not active['value']: return
        if event in ('subprocess.Popen','os.system','os.kill','os.killpg','os.posix_spawn','os.exec') or event.startswith('socket.'):
            raise RuntimeError('Read-only verification refused '+event)
        if event=='open':
            mode,flags=args[1:3]
            if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)):
                raise RuntimeError('Verifier attempted write')
    sys.addaudithook(audit)
    try:
        spec=importlib.util.spec_from_file_location('accepted_unchanged',OLD/'dispatch_successor.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        marker_before={str(p):identity(p) for p in (module.BASE/'dispatch-attempts').glob('*.json')}
        result=module.verify()
        marker_after={str(p):identity(p) for p in (module.BASE/'dispatch-attempts').glob('*.json')}
        if marker_before!=marker_after: raise ValueError('Attempt markers changed')
        if result['packetSHA256']!=PACKET_SHA or result['nativeExecuted']: raise ValueError('Verification result differs')
        if before!={p:identity(Path(p)) for p in before}: raise ValueError('Watched inputs changed')
    finally: active['value']=False
    prepare=OLD/'sealed-inputs/verification/apple-passive-lifecycle-runtime-preparation/prepare.py'
    return dict(verified=result,watchedInputFiles=len(before),inputTreeSHA256=hashlib.sha256(json.dumps(before,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        prepare=dict(path=str(prepare),**identity(prepare)),selection=selection,dispatcher=dict(path=str(OLD/'dispatch_successor.py'),**identity(OLD/'dispatch_successor.py')),
        nativeAttempts=0,builds=0,markersUnchanged=True,inputsUnchanged=True,dispatchCalled=False)
