#!/usr/bin/env python3
"""Bind historical layout measurements to the corrected integrated prerequisite."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = ROOT / 'verification/swift-executor-layout'
F = ROOT / 'verification/swift-final-boundary-accounting/candidate-2'
R = ROOT / 'verification/swift-executor-final-accounting-review'
sha = lambda data: hashlib.sha256(data).hexdigest()
bindings = {}
historical = {}
checks = 0


def bind(path, expected=None):
    global checks
    data = path.read_bytes()
    digest = sha(data)
    if expected is not None:
        assert digest == expected, str(path)
    bindings[str(path.relative_to(ROOT))] = digest
    checks += 1
    return data


def read(path):
    return json.loads(bind(path))


producer = read(P / 'receipt.json')
freeze = read(P / 'source-freeze.json')
old_inputs = read(P / 'input-manifest.json')
assert producer['status'] == 'complete' and producer['input_bytes_unchanged']
assert len(producer['commands']) == 41
assert sha(json.dumps(old_inputs['files'], sort_keys=True).encode()) == producer['input_manifest_sha256']
changed = []
for path, expected in old_inputs['files'].items():
    if sha((ROOT / path).read_bytes()) == expected:
        bind(ROOT / path, expected)
    else:
        data = subprocess.check_output(['git', 'show', old_inputs['revision'] + ':' + path], cwd=ROOT)
        assert sha(data) == expected, path
        historical[path] = {'revision': old_inputs['revision'], 'sha256': expected}
        changed.append(path)
        checks += 1
assert set(changed) == {
    'vm/src/experimental/execution/mod.rs', 'vm/src/experimental/mod.rs',
    'vm/src/experimental_swift_reactor/mod.rs', 'vm/src/experimental_swift_reactor/control.rs',
    'vm/src/experimental_swift_reactor/control_tests.rs', 'vm/src/experimental_swift_reactor/cache_tests.rs'}
for path, expected in freeze['owned_source'].items():
    bind(ROOT / path, expected)
for path, expected in freeze['artifacts'].items():
    bind(ROOT / path, expected)
for command in producer['commands']:
    assert (command['exit_code'] == 0) == (command['expected'] == 0)
    bind(ROOT / command['log'], command['sha256'])
for directory in [R, R / 'root-correction']:
    seal = read(directory / 'seal.json')
    assert sha(json.dumps(seal['files'], sort_keys=True, separators=(',', ':')).encode()) == seal['digest']
    for path, expected in seal['files'].items():
        bind(directory / path, expected)
review = read(R / 'root-correction/decision.json')
assert review['decision'] == 'accepted_scoped_final_boundary_named_object_correction'
assert review['whole_phase_allowance'] == 864 and review['corrected_foundation'] == 17368
assert review['field_count'] == 84 and review['all_commands_passed']
assert review['outside_additive_control_inventory_formula_byte_identical']
assert review['runtime_formula_array_iterator_fold_absent']
for path, expected in review['exact_source_sha256'].items():
    bind(ROOT / path, expected)
current = read(F / 'receipt.json')
inputs = read(F / 'input-manifest.json')
assert current['status'] == 'passed' and len(current['commands']) == 28
assert sha(json.dumps(inputs['files'], sort_keys=True, separators=(',', ':')).encode()) == inputs['source_tree_sha256'] == current['source_tree_sha256']
for path, expected in inputs['files'].items():
    bind(ROOT / path, expected)
    bind(F / 'inputs' / path, expected)
counts = {}
for command in current['commands']:
    log = bind(ROOT / command['log'], command['log_sha256']).decode()
    if command['expected_rejection'] is None:
        assert command['exit_code'] == 0
    else:
        assert command['exit_code'] != 0 and command['expected_rejection'] in log
    totals = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', log)
    if totals:
        counts[command['name']] = {k: sum(int(row[i]) for row in totals) for i, k in enumerate(['passed', 'failed', 'ignored'])}
for mode in ['debug', 'release']:
    assert counts['all-' + mode] == {'passed': 350, 'failed': 0, 'ignored': 9}
    assert counts['swift-' + mode] == {'passed': 106, 'failed': 0, 'ignored': 0}
    assert counts['final-boundary-' + mode]['passed'] == 2
    assert counts['executor-layout-' + mode]['passed'] == 7
assert current['production_metadata'][0] == 'foundation 17368 additional 864 control 1720'
bind(F / 'metadata-probe.rs')
for path, expected in current['metadata_overlays'].items():
    # The temporary example is later overwritten by the two negative probes.
    # Reconstruct its original source for the recorded production hash.
    if path == 'examples/root_final_metadata.rs':
        assert sha(b'fn main() { mixer_vm::experimental_swift_reactor::root_final_metadata_probe(); }\n') == expected
        checks += 1
    elif path == 'src/experimental_swift_reactor/control.rs':
        assert sha((F / 'inputs/vm' / path).read_bytes() + (F / 'metadata-probe.rs').read_bytes()) == expected
        checks += 1
    else:
        assert path == 'src/experimental_swift_reactor/mod.rs'
        hook = b'\npub fn root_final_metadata_probe() { control::root_final_metadata_probe(); }\n'
        assert sha((F / 'inputs/vm' / path).read_bytes() + hook) == expected
        checks += 1
for path in [Path(__file__), F.parent / 'README.md', F.parent / 'receipt.json',
             ROOT / 'docs/swift-executor-layout.md', ROOT / 'docs/swift-final-boundary-accounting.md']:
    bind(path)
result = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'accepted-private-compiling-executor-layout-and-final-foundation-correction',
    'integrator': 'root', 'independent_reviewer': 'swift_executor_final_accounting_review',
    'corrected_source_tree_sha256': current['source_tree_sha256'], 'binding_checks': checks,
    'bindings': bindings, 'historical_inputs': historical, 'test_counts': counts,
    'foundation_bytes': 17368, 'new_disjoint_final_allowance_bytes': 864,
    'production_state_bytes': 312, 'production_instance_bytes': 4480,
    'production_execution_header_bytes': 50592, 'unit_execution_header_bytes': 50832,
    'phase_maps': 8, 'layout_source': 'Four layout source files unchanged from producer freeze. Owner field layouts unchanged by root integration. Corrected foundation metadata measured separately in production and unit Debug/Release.',
    'limits': 'Private compiling types, borrows, layout and named-object accounting only. Nine preexisting ignored tests are not passes. No constructor/interpreter/initialization/invocation, natural executor failure origin, full target run, physical stack/RSS, device, release, immutable published FieldLog, store, customer, operational or GA acceptance. Historical cache C3 and original layout receipts are not rewritten.'}
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'decision': result['decision'], 'binding_checks': checks, 'all_features_tests_per_mode': 350, 'ignored_per_mode': 9}))
