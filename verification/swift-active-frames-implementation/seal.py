#!/usr/bin/env python3
"""Seal preserved producer evidence without touching product or historical bytes."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


assert not (HERE / 'build').exists(), 'Dispose only owned, already-preserved build scratch first.'
for path in list(HERE.rglob('__pycache__')):
    shutil.rmtree(path)
excluded = {'seal.json', 'post-seal-verification.json'}
files = {
    str(path.relative_to(HERE)): sha(path)
    for path in sorted(HERE.rglob('*'))
    if path.is_file() and str(path.relative_to(HERE)) not in excluded
    and '__pycache__' not in path.relative_to(HERE).parts
}
receipt = json.loads((HERE / 'final-receipt.json').read_text())
seal = dict(
    schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='sealed-tested-checkpoint-independent-review-complete-root-acceptance-pending-at-user-pause',
    files=files, filesTreeSHA256=hashlib.sha256(encoded(files)).hexdigest(),
    excluded=sorted(excluded),
    exclusionReason='The seal cannot hash itself; the after-seal verifier report is an output, not an input.',
    finalCandidateTree=receipt['finalSource']['sourceTreeSHA256'],
    sourceArchiveSHA256=receipt['finalSource']['archive']['sha256'],
    finalReceiptSHA256=sha(HERE / 'final-receipt.json'),
    implementationDocumentSHA256=sha(HERE / 'inputs/implementation.md'),
    verifierCommand='python3 verification/swift-active-frames-implementation/verify.py',
    optionalWorktreeVerifierCommand='python3 verification/swift-active-frames-implementation/verify.py --check-worktree',
    rootAcceptance=False, gaGatePassed=False, newTestsAfterPause=False,
    buildDirectoryAbsent=True, nativeRuntimeStarted=False,
)
(HERE / 'seal.json').write_bytes(encoded(seal))
print('seal.json', sha(HERE / 'seal.json'))
print('preserved files', len(files), 'bytes', sum((HERE / name).stat().st_size for name in files))
