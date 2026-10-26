#!/usr/bin/env python3
"""Read-only independent controls custody check; prints JSON only."""
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

bindings = json.loads((ROOT / 'input-bindings.json').read_text())
for row in bindings['inputs']:
    assert sha(REPO / row['path']) == row['sha256'], row['path']
identity = json.loads((ROOT / 'evidence/compiled-source-identity.json').read_text())
selected = REPO / 'verification/swift-cache-state-scalar-cursor-proposal/source/cache_state.rs.txt'
derivative = ROOT / 'source/library/cache_state.rs'
assert derivative.read_bytes() == selected.read_bytes() + identity['append_only_cfg_test_suffix'].encode()
assert sha(derivative) == identity['derivative_sha256']
for row in bindings['copied_source_files']:
    path = ROOT / row['path']
    if path == derivative:
        assert row['sha256'] == sha(selected)
    else:
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
for path, digest in identity['library_sources_and_test_oracles_before'].items():
    assert sha(ROOT / path) == digest, path
result = json.loads((ROOT / 'result.json').read_text())
assert result['all_commands_passed'] and result['owned_children_reaped']
for label in ['rust-version', 'compile-debug', 'tests-debug', 'compile-optimized', 'tests-optimized']:
    receipt = json.loads((ROOT / f'evidence/{label}.json').read_text())
    assert receipt['exit'] == 0 and receipt['failure'] is None
    assert receipt['parent_exit_observed'] and not receipt['group_termination_requested']
    assert receipt['elapsed_seconds'] < receipt['deadline_seconds'] == 60
    for stream, digest in receipt['output_sha256'].items():
        assert sha(ROOT / f'evidence/{label}.{stream}') == digest
    assert receipt['independent_controls_sha256'] == sha(ROOT / 'source/scalar_cursor_independent.rs')
    assert receipt['runner_sha256'] == sha(ROOT / 'run.py')
for row in result['owned_binaries_hashed_then_removed']:
    assert row['absent_after_removal'] and not (ROOT / row['path']).exists()
assert not list(ROOT.rglob('__pycache__'))
assert not list(ROOT.glob('.scratch*'))
print(json.dumps({'input_bindings_verified': len(bindings['inputs']),
    'copied_source_files_verified': len(bindings['copied_source_files']),
    'compiled_tree_members_verified': len(identity['library_sources_and_test_oracles_before']),
    'five_command_output_hashes_verified': True,
    'selected_prefix_and_cfg_test_only_append_verified': True,
    'owned_products_absent': True, 'scope': 'read-only own-packet custody'}, indent=2))
