#!/usr/bin/env python3
"""Read-only final contract review audit; no model/compiler/product execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'verification/swift-ordered-retention-analyzer-fsm-contract-review'
EXPECTED = '101e6c9a67e41cce0e3c82c67ba92ef8025da19376b0578f8ddcdd694fb67212'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(path, row):
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], str(path)


def verify_seal(path, expected):
    assert sha(path) == expected
    data = json.loads(path.read_bytes())
    assert len(data['members']) == len({r['path'] for r in data['members']})
    for row in data['members']:
        check(ROOT / row['path'], row)
    return data


seal = verify_seal(BASE / 'seal.json', EXPECTED)
assert len(seal['members']) == 528 and sum(r['bytes'] for r in seal['members']) == 16_129_288
assert (BASE / 'seal.sha256').read_text().strip() == EXPECTED
final = json.loads((BASE / 'final-receipt.json').read_bytes())
assert final['verdict'] == 'accept-corrected-bounded-fixture-envelope-contract-only'
assert final['total_methods'] == 62 and final['independent_methods'] == 38
assert final['differential_comparisons'] == 5390 and final['actual_GA_or_reviewer_promotions'] == 0
assert final['remaining_contract_blockers_to_preparing_Rust_integration'] == []
assert final['implementation_selection'] is False
for name in ('fullReplayAccepted', 'storedPrefixValidated', 'semantic_counters_valid'):
    assert final[name] is False
assert hashlib.sha256(json.dumps(final['source_rows'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() == final['source_tree_sha256']
for row in final['source_rows'] + final['selected_accepted_framing_source_matches']:
    check(ROOT / row['path'], row)
producer = final['producer']
prod = verify_seal(ROOT / producer['seal'], producer['sha256'])
assert len(prod['members']) == 245
for row in prod['members']:
    check(BASE / 'producer-freeze-2/repository' / row['path'], row)
upstream = 0
for row in final['upstream']:
    checked = verify_seal(ROOT / row['seal'], row['sha256'])
    assert len(checked['members']) == row['members']
    upstream += row['members']
assert upstream == 845
counts = {'independent-oracle': 18, 'frozen-producer': 24, 'independent-cross-checks': 12}
run = json.loads((BASE / 'commands/run-2/result.json').read_bytes())
assert run['frozen_before'] == run['frozen_after'] == run['original_before'] == run['original_after']
assert run['upstream_before'] == run['upstream_after']
assert run['expected_exits_match'] and not run['Rust_implementation_executed']
for command in run['commands']:
    assert command['exit'] == command['expected_exit'] == 0
    for stream in ('stdout', 'stderr'):
        assert sha(BASE / 'commands/run-2' / (command['name'] + '.' + stream)) == command[stream + '_sha256']
    if command['name'] in counts:
        output = (BASE / 'commands/run-2' / (command['name'] + '.stderr')).read_text()
        assert f"Ran {counts[command['name']]} tests" in output and '\nOK\n' in output
assert sha(ROOT / run['layout_binary']['path']) == run['layout_binary']['sha256']
amended = json.loads((BASE / 'commands/amendment-controls/result.json').read_bytes())
assert amended['passed'] and amended['independent_additional_methods'] == 8
assert amended['frozen_before'] == amended['frozen_after'] == amended['producer_before'] == amended['producer_after']
assert amended['upstream_before'] == amended['upstream_after']
assert amended['command']['exit'] == 0
for stream in ('stdout', 'stderr'):
    assert sha(BASE / 'commands/amendment-controls' / stream) == amended['command'][stream + '_sha256']
assert 'Ran 8 tests' in (BASE / 'commands/amendment-controls/stderr').read_text()
for row in amended['archives']:
    assert sha(ROOT / row['path']) == row['sha256']
    assert row['extracted_restored_imported_or_executed'] is False
for name in ('python', 'rustc'):
    assert sha(Path(final[name]['path'])) == final[name]['sha256']
assert final['cleanup']['synchronous_children_reaped'] and not final['cleanup']['disposable_scratch_created']
print(json.dumps({
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
    'python': platform.python_version(), 'script_sha256': sha(Path(__file__)),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'review_seal_sha256': EXPECTED, 'review_members': 528, 'review_bytes': 16129288,
    'producer_members': 245, 'upstream_members': upstream,
    'recorded_total_methods': 62, 'recorded_independent_methods': 38,
    'differential_comparisons': 5390, 'source_tree_sha256': final['source_tree_sha256'],
    'root_model_layout_or_compiler_executed': False,
    'verdict': 'corrected-bounded-fixture-contract-review-verified',
    'actual_Rust_integration_accepted': False, 'ga_gates_promoted': 0,
}, indent=2))
