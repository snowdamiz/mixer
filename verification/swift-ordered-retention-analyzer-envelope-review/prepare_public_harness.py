#!/usr/bin/env python3
"""Emit Rust expected cases from the pre-access manifest, without product access."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
manifest_path = BASE / 'pre-access-vectors/run-1/manifest.json'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
assert sha(manifest_path.read_bytes()) == '28fe5c0a510c5e414fb8b2e661ebe064612eda9e2d05f627a628ba3652f730a3'
manifest = json.loads(manifest_path.read_text())
lines = ['// Prepared before implementation access; no product execution.']

def option(value):
    return 'None' if value is None else f'Some({value})'

for case in manifest['vectors']:
    expectation = case['expected']
    if not expectation['framing']:
        boundary, reason, coordinate, state, phase, mask = 0, 17, 0, 0, 0, 0
    elif expectation.get('boundary') == 'Closed':
        boundary, reason, coordinate, state, phase, mask = 1, 0, expectation['fixture_coordinate'], 0, 5, 33
    elif expectation.get('boundary') == 'CapCutUnknownTail':
        boundary, reason, coordinate, state, phase, mask = 2, 0, expectation['fixture_coordinate'], expectation['state'], 0, 1
    else:
        boundary = 3
        reason = {'Stage': 12, 'ForbiddenResume': 9, 'TerminalPhase': 4}[expectation['reason']]
        coordinate = expectation['fixture_coordinate']
        if reason == 12:
            state, phase, mask = 1, 0, 1
        elif reason == 9:
            state, phase, mask = 0, 0, 1
        else:
            state, phase, mask = 0, 5, 33
    name = case['id'].replace('-', '_')
    lines.extend([
        '#[test]',
        f'fn independent_{name}() {{',
        '    check_fixture(Expected {',
        f'        id: "{case["id"]}", boundary: {boundary}, reason: {reason}, coordinate: {coordinate},',
        f'        state: {option(state)}, phase: {option(phase)}, mask: {option(mask)},',
        f'        framed: {str(expectation["framing"]).lower()}, physical_records: {len(case["records"])},',
        '    });',
        '}',
    ])
output = BASE / 'generated_public_cases.rs'
output.write_text('\n'.join(lines) + '\n')
receipt = dict(schema=1, scope='Independent public harness preparation only; uncompiled and unexecuted',
               interface_proposal_sha256='32e3c49a1640c15f807c45f6a24c09c6c595e1e4f79f69c2938f47d31275be7d',
               binding_addendum_sha256='3058c7a0c3dfed57842014874db94b8014c6e8beee4386cce6478b6615634e64',
               pre_access_manifest_sha256=sha(manifest_path.read_bytes()), generated_methods=len(manifest['vectors']),
               generated_source_sha256=sha(output.read_bytes()), harness_sha256=sha((BASE/'public_fixture_harness.rs').read_bytes()),
               emitter_sha256=sha(Path(__file__).read_bytes()), implementation_read=False, product_executed=False,
               limitation='Getter names may require mechanical adaptation to the frozen implementation; expectations and original vectors remain immutable')
(BASE / 'public-harness-preparation.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt))
