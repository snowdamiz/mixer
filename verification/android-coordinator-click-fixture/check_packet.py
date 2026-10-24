#!/usr/bin/env python3
"""Check the frozen fixture packet and referenced failures without native commands."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('click_packet_local_adapter', HERE / 'run.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def check():
    packet = json.loads((HERE / 'packet-seal-2.json').read_text())
    observed = set()
    for relative in packet['membershipRoots']:
        root = ROOT / relative
        for p in ([root] if root.is_file() else (p for p in root.rglob('*') if p.is_file())):
            if p.is_symlink():
                raise ValueError('frozen packet symlink')
            observed.add(str(p.relative_to(ROOT)))
    if observed != set(packet['files']):
        raise ValueError('frozen packet membership drift')
    for name, value in packet['files'].items():
        p = ROOT / name
        if p.stat().st_size != value['bytes'] or adapter.sha(p) != value['sha256']:
            raise ValueError('frozen packet drift: ' + name)
    tree = hashlib.sha256(json.dumps(packet['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if tree != packet['fileTreeSHA256'] or packet['immutableReferences'] != adapter.BINDINGS:
        raise ValueError('frozen packet tree/reference drift')
    runner, source, _ = adapter.load_runner()
    if hashlib.sha256(source.encode()).hexdigest() != packet['transformedRunnerSHA256']:
        raise ValueError('frozen concrete runner drift')
    runner.bind_candidate(HERE / 'candidate-1')
    return {'status': 'passed-frozen-host-test-only-packet', 'files': len(observed), 'fileTreeSHA256': tree,
        'transformedRunnerSHA256': packet['transformedRunnerSHA256'],
        'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'physicalTargetsQueried': False,
        'nativeRuntime': 'NOT RUN by packet checker; fresh root dispatch pending'}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, sort_keys=True))
