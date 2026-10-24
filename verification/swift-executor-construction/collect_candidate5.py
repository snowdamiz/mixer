#!/usr/bin/env python3
"""Qualify candidate5 with runtime snapshot-bound working directories."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

import collect
from target_isolation import SnapshotBuildIsolation

BASE = Path(__file__).resolve().parent
collect.OUT = BASE / 'candidate-5'
collect.OUT.mkdir(exist_ok=True)
collect.TREE = collect.OUT / 'build/source/vm'
collect.META = collect.OUT / 'build/metadata/vm'
collect.ENV.pop('CARGO_TARGET_DIR', None)
isolation = SnapshotBuildIsolation(collect.OUT, collect.TREE, collect.META)
collect.receipt['schema'] = 'mixer.swift-executor-construction-producer.candidate5'
collect.receipt['prior_candidate'] = {
    'receipt': '../candidate-4/receipt.json',
    'sha256': hashlib.sha256((BASE / 'candidate-4/receipt.json').read_bytes()).hexdigest(),
    'preserved': True,
    'qualification_blocked': 'Candidate4 post-metadata full runs reused a metadata-only test binary from a shared target directory; their product-regression claim is blocked. Preserve its receipt/source/logs unchanged; root owns a separate fresh-target product supplement.',
}

EXPECTED_INPUTS = {
    'src/experimental_swift_reactor/control_tests.rs': '9cd7a9cf60ba9f10feaba9535878d15673c7bc2ed3d9ae0a8ab0ad48bd55655d',
    'src/experimental_swift_reactor/execution.rs': 'ed4c0f10f84096b665f8bcfc7f5b08173bcef7d7ddc8b3ccb88186bf00be3924',
    'src/experimental_swift_reactor/execution_tests.rs': '8615969f23ae7562c81802ddc410549e3622d0c1ad187e3ed5c8476323f5d8b2',
}
for relative, expected in EXPECTED_INPUTS.items():
    assert collect.sha(collect.ROOT / 'vm' / relative) == expected, relative
collect.receipt['required_input_hashes'] = EXPECTED_INPUTS
collect.receipt['working_directory_correction'] = 'Every command resolves cwd at runtime. It must equal this candidate source or its derived metadata overlay; cargo also receives an explicit absolute manifest path. Snapshot hashes are checked before and after every command.'
collect.receipt['build_target_isolation'] = {
    'target_dirs': {kind: str(path) for kind, path in isolation.targets.items()},
    'fresh_at_start': True,
    'policy': 'Source and metadata never share a target root. Each Cargo command receives both an explicit target-dir argument and matching subprocess environment. Every unit-test execution binds the executable hash and direct runtime --list; source lists must omit the derived-only metadata probe.',
}


def snapshot_manifest(root):
    return {str(path.relative_to(root)): collect.sha(path)
            for path in sorted(root.rglob('*')) if path.is_file()}


def candidate5_run(name, argv, cwd=None, expected=0):
    # Never capture TREE in a function default: an imported collector can
    # redirect its current snapshot only after its functions are defined.
    runtime_cwd = Path(collect.TREE if cwd is None else cwd).resolve()
    source = collect.TREE.resolve()
    metadata = collect.META.resolve()
    assert runtime_cwd in (source, metadata), (name, runtime_cwd)
    assert runtime_cwd.is_dir(), (name, runtime_cwd)
    assert runtime_cwd.is_relative_to((collect.OUT / 'build').resolve())
    inputs = json.loads((collect.OUT / 'source-manifest.json').read_text())
    assert snapshot_manifest(source) == inputs, f'{name}: source snapshot differs before command'
    for relative, digest in EXPECTED_INPUTS.items():
        assert collect.sha(runtime_cwd / relative) == digest or runtime_cwd == metadata, relative
    cwd_inputs = snapshot_manifest(runtime_cwd)
    effective_argv = isolation.arguments(argv, runtime_cwd)
    command_env = isolation.environment(collect.ENV, runtime_cwd)
    print(name, runtime_cwd, flush=True)
    started = time.time()
    result = subprocess.run(effective_argv, cwd=runtime_cwd, env=command_env,
                            text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    log = collect.OUT / 'logs' / (name + '.log')
    log.parent.mkdir(exist_ok=True)
    log.write_text(result.stdout)
    source_unchanged = snapshot_manifest(source) == inputs
    cwd_unchanged = snapshot_manifest(runtime_cwd) == cwd_inputs
    binary_witnesses = []
    witness_error = None
    if result.returncode == 0:
        try:
            binary_witnesses = isolation.test_binary_witnesses(name, argv, result.stdout,
                                                            runtime_cwd, command_env)
        except Exception as error:
            witness_error = repr(error)
    source_unchanged = source_unchanged and snapshot_manifest(source) == inputs
    cwd_unchanged = cwd_unchanged and snapshot_manifest(runtime_cwd) == cwd_inputs
    row = {
        'name': name, 'argv': effective_argv, 'requested_argv': argv,
        'cwd': str(runtime_cwd),
        'cwd_kind': 'source' if runtime_cwd == source else 'derived_metadata',
        'expected_cwd': str(source if runtime_cwd == source else metadata),
        'cwd_asserted': True,
        'cargo_target_dir': command_env['CARGO_TARGET_DIR'],
        'test_binary_witnesses': binary_witnesses,
        'test_binary_witness_error': witness_error,
        'source_tree_digest': collect.receipt['source_tree_digest'],
        'cwd_tree_digest': hashlib.sha256(json.dumps(cwd_inputs, sort_keys=True).encode()).hexdigest(),
        'source_unchanged': source_unchanged, 'cwd_unchanged': cwd_unchanged,
        'exit_code': result.returncode, 'expected': expected,
        'seconds': round(time.time() - started, 3),
        'log': str(log.relative_to(collect.ROOT)), 'sha256': collect.sha(log),
    }
    collect.receipt['commands'].append(row)
    collect.save('receipt.partial.json', collect.receipt)
    assert source_unchanged and cwd_unchanged, f'{name}: tested snapshot changed'
    assert witness_error is None, f'{name}: test executable provenance rejected: {witness_error}'
    if (result.returncode == 0) != (expected == 0):
        raise RuntimeError(f'{name}: exit {result.returncode}; see {log}')
    return result.stdout


collect.run = candidate5_run
assert collect.run.__defaults__ == (None, 0)
frozen_metadata_roles = {}


def candidate5_metadata_overlay():
    shutil.copytree(collect.TREE, collect.META)
    execution = collect.META / 'src/experimental_swift_reactor/execution.rs'
    source = execution.read_text()
    originals = ['SwiftExecutionState', 'SwiftReactorInstance', 'SwiftFrame',
                 'ExecutionConstructionPhase', 'ExecutionOperationPhase', 'PartialState',
                 'PartialInstance', 'ExecutionCleanupTail', 'HeaderCompletionParts',
                 'ConstructionCleanupTail', 'ScalarReader', 'ConstructionDescriptors',
                 'ConstructionTransfers', 'ConstructionBorrowChain', 'ConstructionIterationInventory',
                 'ConstructionBootstrapInventory', 'CleanupPreflightInventory']
    supplements = [name for name in re.findall(r'\bstruct (\w+)', source)
                   if 'Supplement' in name or name.startswith(('ConstructorApi', 'ConstructionPositive'))]
    names = list(dict.fromkeys(originals + supplements))
    generic = {'ExecutionConstructionPhase', 'ExecutionOperationPhase', 'ScalarReader'}
    probe = '\npub(super) fn construction_metadata_probe() {\n'
    probe += 'println!("bounds foundation {} bootstrap {} construction {} header {} cleanup_original {}", foundation_construction_bytes().unwrap(), CONSTRUCTION_BOOTSTRAP_BYTES, construction_bytes().unwrap(), execution_header_bytes().unwrap(), phase_bytes("cleanup").unwrap());\n'
    roles = {}
    for name in names:
        ty = name + ("<'static>" if name in generic else '')
        if name == 'ConstructionPositiveTestHookArguments':
            probe += '#[cfg(test)] {\n'
        probe += f'println!("layout {name} {{}} {{}}", size_of::<{ty}>(), std::mem::align_of::<{ty}>());\n'
        roles[name] = []
        for field, field_type in collect.fields(source, name):
            field_type = field_type.replace("'a", "'static")
            roles[name].append({'field': field, 'type': field_type})
            probe += f'println!("role {name} {field} {{}} {{}} {{}}", std::mem::offset_of!({ty}, {field}), size_of::<{field_type}>(), std::mem::align_of::<{field_type}>());\n'
        if name == 'ConstructionPositiveTestHookArguments':
            probe += '}\n'
    for ty in ['ConstructionFailure', 'Option<ConstructionFailure>',
               'Result<SwiftReactorInstance,ConstructionFailure>',
               'Option<Result<SwiftReactorInstance,ConstructionFailure>>',
               'Option<ConstructionCleanupTail>',
               'Result<ConstructionCleanupTail,SwiftRunFailure>',
               '(HeaderCompletionParts,usize)']:
        roles[ty] = []
        probe += f'println!("layout {ty} {{}} {{}}", size_of::<{ty}>(), std::mem::align_of::<{ty}>());\n'
    descriptor = collect.META / 'src/experimental/swift.rs'
    descriptor_source = descriptor.read_text()
    descriptor_name = 'ConstructionPositiveDescriptor'
    descriptor_probe = '\npub(crate) fn construction_descriptor_metadata_probe() {\n'
    descriptor_probe += f'println!("layout {descriptor_name} {{}} {{}}", std::mem::size_of::<{descriptor_name}>(), std::mem::align_of::<{descriptor_name}>());\n'
    roles[descriptor_name] = []
    for field, field_type in collect.fields(descriptor_source, descriptor_name):
        roles[descriptor_name].append({'field': field, 'type': field_type})
        descriptor_probe += f'println!("role {descriptor_name} {field} {{}} {{}} {{}}", std::mem::offset_of!({descriptor_name}, {field}), std::mem::size_of::<{field_type}>(), std::mem::align_of::<{field_type}>());\n'
    descriptor_probe += '}\n'
    descriptor.write_text(descriptor_source + descriptor_probe)
    probe += 'crate::experimental::swift::construction_descriptor_metadata_probe();\n}\n#[cfg(test)]\n#[test]\nfn frozen_construction_metadata() { construction_metadata_probe(); }\n'
    execution.write_text(source + probe)
    module = collect.META / 'src/experimental_swift_reactor/mod.rs'
    module.write_text(module.read_text() + '\npub fn construction_metadata_probe_only() { execution::construction_metadata_probe(); }\n')
    example = collect.META / 'examples/construction_metadata.rs'
    example.parent.mkdir(exist_ok=True)
    example.write_text('fn main() { mixer_vm::experimental_swift_reactor::construction_metadata_probe_only(); }\n')
    (collect.OUT / 'metadata-probe.rs').write_text(probe)
    collect.save('metadata-overlay.json', {str(p.relative_to(collect.META)): collect.sha(p)
                                         for p in [execution, descriptor, module, example]})
    frozen_metadata_roles.update(roles)
    return roles


collect.metadata_overlay = candidate5_metadata_overlay
original_parse_metadata = collect.parse_metadata


def candidate5_parse_metadata(output, roles):
    excluded = []
    expected = dict(roles)
    name = 'ConstructionPositiveTestHookArguments'
    if f'layout {name} ' not in output:
        expected.pop(name, None)
        excluded.append({'type': name, 'reason': 'cfg(test) instrumentation only; production constant is zero'})
    result = original_parse_metadata(output, expected)
    result['cfg_excluded'] = excluded
    return result


collect.parse_metadata = candidate5_parse_metadata
collect.main()
layouts = json.loads((collect.OUT / 'layout-map.json').read_text())
for profile, opts in [('debug', []), ('release', ['--release'])]:
    for kind, argv in [('production', ['cargo', 'run', '--locked'] + opts + ['--all-features', '--example', 'construction_metadata']),
                       ('unit', ['cargo', 'test', '--locked'] + opts + ['--all-features', '--lib', 'frozen_construction_metadata', '--', '--nocapture'])]:
        output = collect.run('metadata-all-' + kind + '-' + profile, argv, cwd=collect.META)
        observed = collect.parse_metadata(output, frozen_metadata_roles)
        assert observed == layouts['configurations'][kind + '-' + profile]
        layouts['configurations'][kind + '-all-' + profile] = observed
collect.save('layout-map.json', layouts)
for profile, opts in [('debug', []), ('release', ['--release'])]:
    collect.run('all-features-full-' + profile,
                ['cargo', 'test', '--locked', '--offline'] + opts + ['--all-features'])
expected_bounds = {
    'production': {'foundation': 267800, 'bootstrap': 250432,
                   'construction': 1062312, 'header': 207352},
    'unit': {'foundation': 268336, 'bootstrap': 250968,
             'construction': 1065072, 'header': 208312},
}
layouts = json.loads((collect.OUT / 'layout-map.json').read_text())
for kind, values in expected_bounds.items():
    for profile in ('debug', 'release'):
        bounds = layouts['configurations'][kind + '-' + profile]['bounds']
        assert all(bounds[key] == value for key, value in values.items()), (kind, profile, bounds)
test_counts = {}
for row in collect.receipt['commands']:
    assert row['cwd_asserted'] and row['source_unchanged'] and row['cwd_unchanged']
    assert row['cwd'] == row['expected_cwd']
    output = (collect.ROOT / row['log']).read_text()
    results = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', output)
    if results:
        totals = [sum(int(result[index]) for result in results) for index in range(3)]
        assert totals[1] == 0
        test_counts[row['name']] = dict(zip(('passed', 'failed', 'ignored'), totals))
for profile in ('debug', 'release'):
    for label, count in [('construction', 14), ('layout', 7), ('neither', 7),
                         ('span', 13), ('swift', 122), ('swift-cache', 122),
                         ('swift-span', 122), ('all', 151)]:
        assert test_counts[label + '-' + profile] == {'passed': count, 'failed': 0, 'ignored': 0}
    assert test_counts['all-features-full-' + profile]['ignored'] == 9
shutil.copy2(collect.ROOT / 'docs/swift-executor-construction.md', collect.OUT / 'document.md')
archive = collect.OUT / 'frozen-source.tar.gz'
with tarfile.open(archive, 'w:gz') as packed:
    packed.add(collect.TREE, arcname='vm')
receipt_path = collect.OUT / 'receipt.json'
receipt = json.loads(receipt_path.read_text())
receipt['commands'] = collect.receipt['commands']
receipt['test_counts'] = test_counts
receipt['expected_aggregate_bounds_verified'] = True
receipt['expected_aggregate_bounds'] = expected_bounds
receipt['all_command_cwds_verified'] = True
receipt['document_hash'] = collect.sha(collect.OUT / 'document.md')
receipt['independent_positive_map'] = {
    str(path.relative_to(collect.ROOT)): collect.sha(path)
    for path in [collect.ROOT / 'verification/swift-executor-construction-independent-review/candidate2-api' / name
                 for name in ['proposal-freeze.json', 'positive-accounting-map.json', 'test-hook-positions.json']]
}
receipt['archive'] = {'path': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
receipt['collector_hashes'] = {
    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [BASE / 'collect.py', BASE / 'target_isolation.py', Path(__file__).resolve()]
}
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
