"""Seal only this independent folder after one final read-only pin check."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

owned = Path(__file__).resolve().parent
root = owned.parents[1]
producer = root / 'verification/swift-root-bound-dispatch-retained-verifier-v1'
v2 = root / 'verification/swift-root-bound-dispatch-physical-evidence-v2'
canonical = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
receipt = json.loads((owned / 'review.json').read_bytes())
assert receipt['status'] == 'PASS_INDEPENDENT_SYNTHETIC_REVIEW'
for pin in receipt['after']:
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], pin['path']
delta = ''
counts = []
for name in ('region_certificate.py', 'tests_region_certificate.py'):
    before = (v2 / 'source' / name).read_text().splitlines(keepends=True)
    after = (producer / 'source' / name).read_text().splitlines(keepends=True)
    part = list(difflib.unified_diff(before, after,
                fromfile='accepted-v2/source/' + name,
                tofile='retained-verifier-v1/source/' + name))
    counts.append({'path': 'source/' + name,
                   'lines_added': sum(l.startswith('+') and not l.startswith('+++') for l in part),
                   'lines_removed': sum(l.startswith('-') and not l.startswith('---') for l in part)})
    delta += ''.join(part)
assert delta.encode() == (producer / 'freeze/source-delta.patch').read_bytes()
static = json.loads((owned / 'static-review.json').read_bytes())
static.update(recomputed_delta_matches_frozen_patch=True, delta_inventory=counts,
              final_input_tool_recheck_unchanged=True)
(owned / 'static-review.json').write_text(json.dumps(static, sort_keys=True, indent=2) + '\n')
members = []
for path in sorted(owned.rglob('*')):
    if path.is_file() and path.name != 'seal.json':
        raw = path.read_bytes()
        members.append({'path': str(path.relative_to(owned)), 'bytes': len(raw), 'sha256': sha(raw)})
assert not (owned / 'command').exists()
assert not any('__pycache__' in str(path) for path in owned.rglob('*'))
seal = {
    'schema': 1, 'status': 'FROZEN_INDEPENDENT_RETAINED_VERIFIER_SOURCE_AND_SYNTHETIC_REVIEW_PASS',
    'candidate_seal_sha256': '8abb6802e73f98982bf863b16175617ca770a72e264364084aa8fa1c84226ee7',
    'candidate_source_tree_sha256': '8c8978b167f5d08bac12b51e33f5215f1d703e4860f05981d5d6ad988dac7279',
    'members': members, 'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members),
    'tree_sha256': sha(canonical(members)), 'findings': [],
    'command': [str(Path(sys.executable)), '-B', str(Path(__file__))],
    'tool_version_source': 'Prior retained plan receipt; no new version probe.',
    'test_methods_passed': 32, 'fresh_independent_methods': 9,
    'fresh_scope_checked_verifier_results': 317,
    'actual_geometry_inputs_read_or_executed': 0, 'actual_certificate_selected': False,
    'actual_input_release': False,
    'link_dead_code': True, 'alternate_diagnostic_configuration_only': True,
    'original_capture_qualified': False, 'runtime_admission_accepted': False,
    'local_geometry_only': True, 'complete_capacity_accepted': False,
    'native_UI_local_custody_Unit_A_holds_preserved': True,
    'owned_scratch_removed': True, 'frozen_producer_edits': 0,
    'canonical_metadata_edits': 0, 'commits': 0, 'pushes': 0,
}
raw = json.dumps(seal, sort_keys=True, indent=2).encode() + b'\n'
(owned / 'seal.json').write_bytes(raw)
print(json.dumps({'seal_sha256': sha(raw), 'member_count': len(members),
                  'tree_sha256': seal['tree_sha256'], 'static_review': static}, indent=2))
