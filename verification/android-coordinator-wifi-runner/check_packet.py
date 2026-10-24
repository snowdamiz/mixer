#!/usr/bin/env python3
"""Verify the frozen host packet and immutable references without SDK commands."""
import hashlib
import json
from pathlib import Path
import run as adapter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def check():
    packet = json.loads((HERE / 'packet-seal.json').read_text())
    files = packet['files']
    observed = set()
    for relative in packet['membershipRoots']:
        path = ROOT / relative
        found = [path] if path.is_file() else [p for p in path.rglob('*') if p.is_file()]
        for p in found:
            if p.is_symlink():
                raise ValueError('symlink in frozen packet: ' + str(p))
            observed.add(str(p.relative_to(ROOT)))
    if observed != set(files):
        raise ValueError('frozen packet membership drift')
    for relative, binding in files.items():
        p = ROOT / relative
        if p.stat().st_size != binding['bytes'] or adapter.sha(p) != binding['sha256']:
            raise ValueError('frozen packet drift: ' + relative)
    tree = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if tree != packet['fileTreeSHA256'] or packet['immutableReferences'] != adapter.BINDINGS:
        raise ValueError('frozen packet tree/reference drift')
    runner, source, _ = adapter.load_runner()
    if hashlib.sha256(source.encode()).hexdigest() != packet['transformedRunnerSHA256']:
        raise ValueError('frozen transformed runner drift')
    runner.bind_candidate(runner.BUILDS / 'candidate-2')
    return {'schema': 1, 'status': 'passed-frozen-host-packet-only', 'files': len(files),
            'fileTreeSHA256': tree, 'transformedRunnerSHA256': packet['transformedRunnerSHA256'],
            'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'physicalTargetsQueried': False,
            'nativeRuntime': 'NOT RUN by packet checker; no app acceptance'}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, sort_keys=True))
