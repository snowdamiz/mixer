"""Verify immutable companion and base bindings; never launch runtime tools."""
from pathlib import Path
import json, hashlib, sys
HERE = Path(__file__).resolve().parent
def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(8 * 1024 * 1024): h.update(b)
    return h.hexdigest()
def main():
    seal = json.loads((HERE / 'review-seal.json').read_bytes())
    for rel, row in seal['bindings'].items():
        p = HERE / rel
        assert p.is_file() and p.stat().st_size == row['bytes'] and digest(p) == row['sha256'], rel
    for path, row in seal['baseBindings'].items():
        p = Path(path)
        assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256'], path
    controls = json.loads((HERE / 'controls.json').read_bytes())
    assert len(controls['controls']) == 25 and controls['allRejected'] and controls['dummyTargetRemoved']
    assert all(r['rejected'] for r in controls['controls'])
    assert controls['positiveFullLoaderCache']['systemCacheFiles'] == 82
    assert controls['positiveFullLoaderCache']['systemCacheBytes'] == 7048019583
    assert controls['wasmExecuted'] is False and controls['compilerCompilationExecuted'] is False
    cleanup = json.loads((HERE / 'cleanup.json').read_bytes())
    assert cleanup['allOwnedMetadataGroupsEmpty'] and cleanup['syntheticTargetRemoved']
    assert seal['runtimeSelected'] is False
    print('Companion seal/base bindings and 25 pure controls verified; no runtime execution')
if __name__ == '__main__': main()
