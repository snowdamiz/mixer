#!/usr/bin/env python3
"""Read only selected frozen inputs; never inspect the active producer lane."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
PRIOR = ROOT / 'verification/swift-cache-state-profile-adapter-preparation-independent'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    selection = ROOT / 'verification/swift-semantic-adapter-root-review/profile-adapter-implementation-selection.json'
    assert sha(selection) == 'c4547c12007d8087a6a6ffbdc41a129ebc89959c95cc2ed18a152f98f16a16b0'
    assert sha(PRIOR / 'seal.json') == '7931ac0ea1da9c7a98614b0962063e1396bde8717045b5b7bd0b8b923419b3ca'
    for row in json.loads((PRIOR / 'seal.json').read_bytes())['members']:
        p = PRIOR / row['path']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    inputs = HERE / 'inputs'; inputs.mkdir(exist_ok=False)
    selected = [(selection, 'implementation-selection.json'),
        (PRIOR / 'root-protocol-amendment.md', 'protocol-amendment.md'),
        (PRIOR / 'decision.json', 'preselection-decision.json'),
        (PRIOR / 'preparation/proposed-contract.md', 'proposed-contract.md'),
        (PRIOR / 'preparation/test-plan.md', 'test-plan.md'),
        (PRIOR / 'additional-validator-inputs/src/experimental/swift.rs', 'validator/swift.rs'),
        (PRIOR / 'additional-validator-inputs/src/experimental/metadata.rs', 'validator/metadata.rs'),
        (PRIOR / 'additional-validator-inputs/src/experimental/policy.rs', 'validator/policy.rs'),
        (PRIOR / 'additional-validator-inputs/src/experimental/descriptors.rs', 'validator/descriptors.rs')]
    completion = json.loads((PRIOR / 'preparation/inputs/verification/swift-ordered-retention-diagnostic-completion/candidate-manifest.json').read_bytes())
    descriptor = ROOT / 'vm/src/experimental_wasi/descriptor.rs'
    assert sha(descriptor) == completion['src/experimental_wasi/descriptor.rs'] == '5d62e14ef35bd53911d7b251fdcf0f25454767d225e20abdfe7dfccfccafbdff'
    selected.append((descriptor, 'validator/wasi-descriptor.rs'))
    canonical = ROOT / 'verification/swift-cache-state-ci/pack'
    assert sha(canonical / 'manifest.json') == '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'
    closed = json.loads((canonical / 'manifest.json').read_bytes())
    for row in closed['members']:
        p = canonical / row['path']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    for name in ['manifest.json', 'inventories/api-contract.json', 'source/library/analyzer.rs', 'source/library/envelope.rs', 'source/library/cache_state.rs']:
        selected.append((canonical / name, 'closed-fixture/' + name))
    rows = []
    for source, name in selected:
        target = inputs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        rows.append({'source': str(source.relative_to(ROOT)), 'snapshot': str(target.relative_to(HERE)),
                     'bytes': target.stat().st_size, 'sha256': sha(target)})
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': sha(Path(__file__)), 'inputs': rows,
        'prior_preselection_sealed_members_verified': 86,
        'canonical_closed_fixture_members_verified': len(closed['members']),
        'canonical_closed_fixture_bytes_verified': closed['total_bytes'],
        'active_producer_lane_accessed': False, 'product_source_compiled_or_executed': False,
        'no_source_identity_inferred_from_HEAD': True}
    (HERE / 'input-custody.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print('PASS preaccess custody:15selected inputs;86prior+86closed members; no active producer access')

if __name__ == '__main__':
    main()
