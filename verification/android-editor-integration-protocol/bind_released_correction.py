#!/usr/bin/env python3
"""Bind root-released frozen source to a PROPOSAL without granting acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'verification/android-editor-focus-history-correction'
EXPECTED = '2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8'
def ident(data): return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def save(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def main():
    data = (FROZEN / 'seal.json').read_bytes()
    assert ident(data)['sha256'] == EXPECTED
    seal = json.loads(data)
    assert len(seal['members']) == 5325
    destination = HERE / 'inputs/released-correction'
    destination.mkdir(exist_ok=False)
    (destination / 'seal.json').write_bytes(data)
    manifest = json.loads((HERE / 'input-manifest.json').read_text())
    manifest['released-correction/seal.json'] = {'source': str((FROZEN / 'seal.json').relative_to(ROOT)), **ident(data)}
    files = {}
    comparison = []
    profile = json.loads((HERE / 'current-profile4.json').read_text())
    proposal = json.loads((HERE / 'proposed-profile5.json').read_text())
    for member in seal['members']:
        if not member['path'].startswith('source/'):
            continue
        relative = member['path']
        source = FROZEN / relative
        source_data = source.read_bytes()
        identity = ident(source_data)
        assert identity == {key: member[key] for key in ('bytes', 'sha256')}
        target = destination / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(source_data)
        manifest['released-correction/' + relative] = {'source': str(source.relative_to(ROOT)), **identity}
        name = relative.removeprefix('source/')
        files[name] = identity
        old = HERE / 'inputs/historical-preparation/closure-B-directprobe/inputs/product' / name
        prior_identity = ident(old.read_bytes())
        key = 'app/src/dev/mixer/android/' + name
        canonical = profile['adapter_files'].get(key)
        comparison.append({'name': name, 'frozen': identity, 'historical': prior_identity,
            'profile4': canonical, 'changed_from_historical': identity != prior_identity,
            'changed_from_profile4': identity != canonical})
        proposal['adapter_files'][key] = identity
    tree_digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert tree_digest == seal['product_source_tree_digest'] == '2d0a89dac0c629b7257a75dfa42dee3794f021c558300f968fc4d8baaaecba01'
    assert len(files) == 16
    assert {row['name'] for row in comparison if row['changed_from_historical']} == {'NativeAppearanceViewsV2.java', 'NativeRenderer.java'}
    assert {row['name'] for row in comparison if row['changed_from_profile4']} == {
        'NativeAppearanceViewsV2.java', 'NativeCoordinatorV2.java', 'NativeRenderer.java', 'NativeEditorConnectionV2.java'}
    assert all(value is not None for value in proposal['adapter_files'].values())
    proposed_projection = hashlib.sha256(''.join(p + '\0' + proposal['adapter_files'][p]['sha256'] + '\n' for p in sorted(proposal['adapter_files'])).encode()).hexdigest()
    proposal['candidate_binding'] = {'seal_sha256': EXPECTED, 'source_tree_sha256': tree_digest,
        'acceptance': 'pending independent review and root decision; binding is not selection'}
    proposal['status'] = 'unselected proposal bound to root-released frozen correction; not executable admission policy'
    proposal['adapter_compatibility_sha256'] = proposed_projection
    save(HERE / 'proposed-profile5.json', proposal)
    save(HERE / 'input-manifest.json', manifest)
    save(HERE / 'released-correction-binding.json', {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'explicit root release permits frozen-source binding only; producer and active reviewer untouched',
        'seal_sha256': EXPECTED, 'source_tree_sha256': tree_digest, 'checked_source_members': len(files),
        'whole_5325_member_packet_reverified_by_this_lane': False, 'root_reported_packet_verified': True,
        'root_acceptance': None, 'candidate_selection': None, 'proposed_adapter_projection_sha256': proposed_projection,
        'comparisons': comparison, 'native_ui_capture_processes_queried_or_started': False})
    print('PASS released correction source16; only Views/Renderer differ from historical; proposed SDK22/adapter24 profile remains unselected')
if __name__ == '__main__': main()
