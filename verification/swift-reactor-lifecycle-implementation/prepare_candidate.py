#!/usr/bin/env python3
"""Materialize an isolated candidate from the exact selected 130-file closure."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/swift-calls-dispatch-root-review/live-v7-integration-retry/final-live-manifest.json'
EXPECTED = '3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3'
PINS = {
    'verification/swift-reactor-lifecycle-contract/seal.json': 'bee5dd7ee357a8d19458bbd925b4ddfbc74e0641bede0ab9ab7ee26e197ff8ff',
    'verification/swift-reactor-lifecycle-contract-root-review/selection.json': '5fc30aee1ab3ebd306ff24de52e18a0a18cc56abb84264920273a096db5bcc6f',
}
def sha(data):
    return hashlib.sha256(data).hexdigest()
def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def main():
    baseline = json.loads(BASE.read_bytes())
    assert len(baseline) == 130 and sha(encoded(baseline)) == EXPECTED
    for name, pin in PINS.items():
        assert sha((ROOT / name).read_bytes()) == pin, name
    candidate = HERE / 'candidate'
    assert not candidate.exists()
    candidate.mkdir()
    for name, pin in baseline.items():
        path = Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        data = (ROOT / 'vm' / path).read_bytes()
        assert sha(data) == pin, name
        destination = candidate / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (HERE / 'baseline-manifest.json').write_bytes(encoded(baseline))
    (HERE / 'input-bindings.json').write_bytes(encoded(PINS | {str(BASE.relative_to(ROOT)): EXPECTED}))
if __name__ == '__main__':
    main()
