#!/usr/bin/env python3
"""Seal only this bounded execution evidence and its selected runtime output."""
import hashlib
import json
import pathlib
import stat

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUNTIME = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3/runtime'
DOC = ROOT / 'docs/apple-toggle-keyboard-full-case-v3-runtime.md'
EXCLUDED = {'packet-seal.json', 'seal-verification.stdout', 'seal-verification.stderr', 'seal-verification.json'}


def record(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError('Only regular execution evidence may be sealed: ' + str(path))
    return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=info.st_size, mode=stat.S_IMODE(info.st_mode))


def main():
    if (BASE / 'packet-seal.json').exists():
        raise ValueError('Original execution seal is immutable')
    inspection = json.loads((BASE / 'outcome-inspection.json').read_bytes())
    files = {str(p.relative_to(ROOT)):record(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in EXCLUDED}
    files[str(DOC.relative_to(ROOT))] = record(DOC)
    runtime = {str(p.relative_to(ROOT)):record(p) for p in sorted(RUNTIME.rglob('*')) if p.is_file()} if RUNTIME.is_dir() else {}
    files.update(runtime)
    seal = dict(schema='mixer.apple-toggle.keyboard-full-case-v3-execution.1',
        status='original-native-outcome-retained', sourceRevision='50f70a798fea43e1e77b1d95faa1bbda3fc029e0',
        adapterSealSHA256='137b6dc9b681eff1358712c34d9b71a3b356072ee6954b4a99e9a8c32b60f46b',
        executionSelectionSHA256='07fd2d6cde05214ee9a5d89359326081e174ae60f4989117997d027356f5ce49',
        nativeInvocationCount=inspection['nativeInvocationCount'], nativeOutcome=inspection['nativeOutcome'],
        files=files, runtimeFiles=runtime,
        excludedAncillaryVerificationReceipts=sorted(EXCLUDED - {'packet-seal.json'}),
        physicalPhones='disconnected-deferred', nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False)
    with (BASE / 'packet-seal.json').open('x') as stream:
        json.dump(seal, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(hashlib.sha256((BASE / 'packet-seal.json').read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
