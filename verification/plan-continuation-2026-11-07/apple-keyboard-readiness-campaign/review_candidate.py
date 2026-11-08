"""Read-only root handoff. No native entrypoint is admitted by this campaign."""
import hashlib
import json
import sys
from pathlib import Path
from verify_bindings import verify

HERE=Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def check(expected):
    if sha(HERE/'candidate-seal.json') != expected:
        raise RuntimeError('Candidate seal differs')
    seal=json.loads((HERE/'candidate-seal.json').read_text())
    for group in ('sourceFiles','testHarnessFiles','preservedFiles'):
        for name,value in seal[group].items():
            if sha(HERE/name) != value:raise RuntimeError('Sealed file changed: '+name)
    for path,value in json.loads((HERE/'historical-identities.json').read_text()).items():
        if sha(Path(path)) != value:raise RuntimeError('Historical input changed: '+path)
    bindings=verify()
    return dict(candidateVerified=True,nativeEligible=False,
        blockedOn='Public keyboard action effect/preference scope is not established',
        devicesCreated=0,nativeAttempts=0,oldDeletedUUIDAdoptable=False,
        watchedInputFiles=bindings['watchedInputFiles'],inputsUnchanged=bindings['inputsUnchanged'],
        markersUnchanged=bindings['markersUnchanged'],dispatchCalled=bindings['dispatchCalled'],
        nextUnlock='Root reviews executable cleanup repair and decides the concrete isolation alternative')


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='check-candidate':
        raise SystemExit('Only check-candidate <sealed SHA256> is supported; no native mode')
    print(json.dumps(check(sys.argv[2]),indent=2))
