"""Replay frozen controls from the independent copied closure, never in place."""
import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
from contextlib import redirect_stdout,redirect_stderr

OWNED=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
assert args.attempt in (1,2,3)
supplement=OWNED/'supplemental-inputs.json'
if args.attempt>1: assert supplement.exists(),'Bind supplemental inputs before replay'
meta=json.loads((OWNED/'input-bindings.json').read_bytes())
scratch=Path(meta['scratch']);repo=Path(meta['scratchRepo'])
base=repo/'verification/apple-focus-reference-runtime-v4'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stable=lambda value:(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
allowed={p.stem:sha(p.read_bytes()) for p in (OWNED/'inspected-programs').glob('*.py')}
assert all(key==value for key,value in allowed.items()) and len(allowed)==4
spawns=[]
def guard(event,args):
    if event=='subprocess.Popen':
        executable,argv=args[:2]
        assert Path(executable).resolve()==Path(sys.executable).resolve(),argv
        assert len(argv)==5 and argv[1:3]==['-B','-c'] and sha(argv[3].encode()) in allowed,argv
        assert Path(argv[4]).resolve().is_relative_to(base),argv
        spawns.append({'argv':argv,'programSHA256':sha(argv[3].encode())})
    elif event in ('os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Independent review guard forbids '+event)
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=os.fsdecode(args[0])
        if any(word in path.lower() for word in ('hosted','catalog','authority-driver','worker-transport')):
            raise AssertionError('Excluded lane read: '+path)
        flags=args[2] if len(args)>2 else 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
            assert Path(path).resolve().is_relative_to(OWNED),path
sys.addaudithook(guard)
sys.dont_write_bytecode=True
sys.path.insert(0,str(base))
os.environ['PYTHONPATH']=str(OWNED/'child-guard')
os.environ['MIXER_REVIEW_OWNED']=str(OWNED)
out=OWNED/('replay-attempt-'+str(args.attempt));out.mkdir()
host_attempt=args.attempt+2
started=time.monotonic();error=None
try:
    with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr,redirect_stdout(stdout),redirect_stderr(stderr):
        import verify_host
        verify_host.main(host_attempt)
except BaseException:
    error=traceback.format_exc()
finally:
    generated=base/('host-attempt-'+str(host_attempt))
    if generated.exists():shutil.copytree(generated,out/'controls')
    receipt={'schema':'mixer.apple-focus-reference-runtime-v4-independent-replay.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),
             'copiedClosureTreeSHA256':meta['bindingTreeSHA256'],'producerHandoffSHA256':meta['expected']['handoff.json'],
             'producerPacketSHA256':meta['expected']['packet.json'],'producerReceiptSHA256':meta['expected']['host-attempt-2/receipt.json'],
             'processes':spawns,'elapsedSeconds':time.monotonic()-started,'error':error,'nativeExecuted':False,
             'scope':'Unchanged copied host replay; child audit guard added before unchanged program, no native dispatch',
             'supplementalHistoricalInputs':args.attempt>1,
             'supplementalInputManifestSHA256':sha(supplement.read_bytes()) if args.attempt>1 else None}
    (out/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'error':error,'hostPythonCompositionProbes':len(spawns),'receiptSHA256':sha((out/'receipt.json').read_bytes())},sort_keys=True))
if error:raise SystemExit(1)
