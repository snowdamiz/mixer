#!/usr/bin/env python3
"""Bind completed candidate4 qualification and preserved blocked histories."""
from pathlib import Path
import difflib
import hashlib
import json
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / 'candidate-4'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


receipt = json.loads((OUT / 'receipt.json').read_text())
assert receipt['all_command_cwds_verified']
assert receipt['expected_aggregate_bounds_verified']
assert receipt['source_tree_digest'] == 'b5dced18f98fd166d3da0a7a0d60b51d95f2f67815849c26791ccb15954c5349'
assert receipt['document_hash'] == '39f223fa3cc4028f28be2f29f4419e450cf9770c0fc016b03f6411b8b435912e'
inputs = json.loads((OUT / 'source-manifest.json').read_text())
with tarfile.open(OUT / receipt['archive']['path']) as archive:
    packed = {member.name.removeprefix('vm/'): hashlib.sha256(archive.extractfile(member).read()).hexdigest()
              for member in archive.getmembers() if member.isfile()}
assert packed == inputs
for path, digest in inputs.items():
    assert sha(OUT / 'build/source/vm' / path) == digest
    assert sha(ROOT / 'vm' / path) == digest, f'live VM differs: {path}'
correction = json.loads((BASE / 'qualification-correction.json').read_text())
for path, digest in correction['prior_files_preserved'].items():
    assert sha(BASE / path) == digest, f'blocked candidate2 changed: {path}'
prior = json.loads((BASE / 'candidate-3/receipt.failed.json').read_text())
assert prior['status'].startswith('blocked:')
assert sha(BASE / 'candidate-3' / prior['archive']['path']) == prior['archive']['sha256']
cwd_audit = []
for row in receipt['commands']:
    assert row['cwd'] == row['expected_cwd']
    assert row['cwd_asserted'] and row['source_unchanged'] and row['cwd_unchanged']
    assert row['source_tree_digest'] == receipt['source_tree_digest']
    assert sha(ROOT / row['log']) == row['sha256']
    if row['argv'][0] == 'cargo' and row['argv'][1] in ('test', 'run', 'check', 'clippy'):
        assert row['argv'][row['argv'].index('--manifest-path') + 1] == str(Path(row['cwd']) / 'Cargo.toml')
    cwd_audit.append({key: row[key] for key in ('name', 'cwd', 'cwd_kind', 'source_tree_digest', 'cwd_tree_digest', 'cwd_asserted', 'source_unchanged', 'cwd_unchanged')})
save(OUT / 'cwd-audit.json', cwd_audit)
old = json.loads((BASE / 'candidate-2/source-manifest.json').read_text())
delta = [{'path': path, 'candidate2': old.get(path), 'candidate4': inputs.get(path)}
         for path in sorted(set(old) | set(inputs)) if old.get(path) != inputs.get(path)]
assert [row['path'] for row in delta] == ['src/experimental_swift_reactor/control_tests.rs', 'src/experimental_swift_reactor/execution.rs']
save(OUT / 'source-delta.json', delta)
execution = 'src/experimental_swift_reactor/execution.rs'
before = (BASE / 'candidate-3/build/source/vm' / execution).read_text().splitlines(True)
after = (OUT / 'build/source/vm' / execution).read_text().splitlines(True)
patch = ''.join(difflib.unified_diff(before, after, fromfile='candidate3/execution.rs', tofile='candidate4/execution.rs'))
(OUT / 'annotation-only.patch').write_text(patch)
api = json.loads((BASE / 'candidate-2/api-freeze.json').read_text())
api['schema'] = 'mixer.swift-construction-candidate4-api-freeze.v1'
api['status'] = 'API and positive exact-type accounting frozen; producer qualification passed; independent acceptance pending'
api['source_hashes'] = {'vm/' + path: inputs[path] for path in (execution, 'src/experimental_swift_reactor/execution_tests.rs', 'src/experimental_swift_reactor/control_tests.rs')}
save(OUT / 'api-freeze.json', api)
counts = receipt['test_counts']
full = {profile: counts['all-features-full-' + profile] for profile in ('debug', 'release')}
assert full['debug'] == full['release']
layouts = json.loads((OUT / 'layout-map.json').read_text())
assert len(layouts['configurations']) == 8
readme = f'''# Candidate 4: corrected source-bound construction qualification

Candidate 2's main qualification commands used candidate 1's cwd. Candidate 3
corrected the binding, passed its library tests, and stopped at actual-source
Clippy failures. Both histories remain unchanged. This candidate includes only
the root's admission-test correction and five targeted lint annotations, with
no constructor field, body, allocation or accounting change. The exact diff is
`source-delta.json` and `annotation-only.patch`.

The receipt binds {len(inputs)} VM inputs, the archive and all command/log hashes.
Every command resolves cwd at runtime, checks the snapshot before and after,
and gives Cargo an explicit absolute manifest. `cwd-audit.json` preserves that
per-command evidence; it cannot silently use either older candidate directory.

Both profiles pass 14 narrow construction tests, 7 original layout tests, and
six library feature configurations (7 / 13 / 122 / 122 / 122 / 151). Both
Clippy modes, formatting and external-constructor privacy rejection pass.
Full all-feature host regression passes {full['debug']['passed']} tests with
{full['debug']['ignored']} ordinary ignored tests per profile. The ignored tests
remain pending. Eight production/unit, Debug/Release, minimal/combined metadata
configurations agree with the approved logical bounds: production foundation
267,800 / additional construction 1,062,312 / same header 207,352; unit
268,336 / 1,065,072 / 208,312. These are logical accounting inventories, not
physical stack or RSS measurements.

The independent exact-type map remains in the immutable candidate2-api review
proposal. Product source contains no metadata probes or public construction
route. The archive creates no initialized/Ready reactor and executes no target.
Independent root acceptance, full frozen executor acceptance, interpreter,
initialize/invoke, growth/active-frame unwind/exhaustive interruption, full
target, physical devices, immutable published FieldLog, signing/store/customer/
operational and GA gates remain pending. No commit/push/tracker change is made
by this producer lane.
'''
(OUT / 'README.md').write_text(readme)
receipt['history_preservation_verified'] = True
receipt['archive_manifest_verified'] = True
receipt['live_vm_matches_snapshot'] = True
receipt['finalization_script'] = {'path': str(Path(__file__).relative_to(ROOT)), 'sha256': sha(Path(__file__))}
receipt['artifact_hashes'] = {path.name: sha(path) for path in sorted(OUT.iterdir())
                              if path.is_file() and path.name not in ('receipt.json', 'receipt.partial.json')}
receipt['status'] = 'producer qualification passed against candidate4 exact snapshot; independent acceptance pending'
save(OUT / 'receipt.json', receipt)
correction['replacement_candidate'] = 'candidate-4'
correction['replacement_tree_digest'] = receipt['source_tree_digest']
correction['candidate3_failure_receipt'] = {'path': 'candidate-3/receipt.failed.json', 'sha256': sha(BASE / 'candidate-3/receipt.failed.json')}
correction['status'] = 'candidate4 producer qualification passed; root independent acceptance pending'
save(BASE / 'qualification-correction.json', correction)
print(json.dumps({'receipt': str((OUT / 'receipt.json').relative_to(ROOT)), 'commands': len(cwd_audit), 'full_all_feature_counts': full, 'source_tree_digest': receipt['source_tree_digest'], 'archive_sha256': receipt['archive']['sha256']}, indent=2))
