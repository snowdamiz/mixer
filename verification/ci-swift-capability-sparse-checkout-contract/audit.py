#!/usr/bin/env python3
"""Finite offline source-closure audit. Never builds or executes product inputs.

Writes only this packet. Git metadata for the full committed tree is read once;
only selected current blobs and the fixed historical pin's small input set are
read. No full tree extraction, sparse-index mutation, network or toolchain run.
"""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
TREE = '076842155358f5be57a6f97af73577687a32a6d4'
WORKFLOW_SHA = 'fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88'
PIN = '1adb25c48a8723f56ed2649712fe5e357920c53e'
LOG = []
START = time.monotonic()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(argv, data=None, maximum=100 * 1024 * 1024):
    began = time.monotonic()
    result = subprocess.run(argv, input=data, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=50)
    if len(result.stdout) > maximum or len(result.stderr) > 1024 * 1024:
        raise RuntimeError('offline command output bound exceeded')
    LOG.append({'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 50,
                'exit': result.returncode, 'seconds': round(time.monotonic() - began, 6),
                'stdin_bytes': len(data or b''), 'stdin_sha256': sha(data or b''),
                'stdout_bytes': len(result.stdout), 'stdout_sha256': sha(result.stdout),
                'stderr': result.stderr.decode('utf-8')})
    if result.returncode:
        raise RuntimeError('offline command failed: ' + repr(argv))
    return result.stdout


def git(*args, **kwargs):
    return run(['git', '--no-replace-objects', '-c', 'core.fsmonitor=false', *args], **kwargs)


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def parse_tree(raw):
    entries = {}
    for record in raw.split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        mode, kind, oid, size = meta.split()
        name = name.decode('utf-8')
        if kind != b'blob':
            raise RuntimeError('non-blob tree entry: ' + name)
        entries[name] = {'mode': mode.decode(), 'git_blob': oid.decode(), 'bytes': int(size)}
    return entries


def read_blobs(entries):
    ordered = sorted(entries)
    raw = git('cat-file', '--batch', data=''.join(entries[p]['git_blob'] + '\n' for p in ordered).encode())
    cursor = 0
    blobs = {}
    for path in ordered:
        end = raw.index(b'\n', cursor)
        oid, kind, length = raw[cursor:end].split()
        length = int(length)
        assert kind == b'blob' and oid.decode() == entries[path]['git_blob']
        cursor = end + 1
        blobs[path] = raw[cursor:cursor + length]
        assert len(blobs[path]) == length == entries[path]['bytes']
        assert raw[cursor + length:cursor + length + 1] == b'\n'
        cursor += length + 1
    assert cursor == len(raw)
    return blobs


def literal_assignment(raw, name):
    tree = ast.parse(raw)
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in statement.targets):
            return ast.literal_eval(statement.value)
    raise RuntimeError('literal assignment missing: ' + name)


def prefix_paths(entries, prefix):
    return {p for p in entries if p == prefix or p.startswith(prefix.rstrip('/') + '/')}


def main():
    # Whole audit guard; every child also has its own <=50-second timeout.
    signal.alarm(54)
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert git('rev-parse', 'HEAD^{tree}').decode().strip() == TREE
    workflow = (ROOT / '.github/workflows/verify.yml').read_bytes()
    assert sha(workflow) == WORKFLOW_SHA
    patterns = (OUT / 'sparse-checkout.txt').read_bytes()
    lines = patterns.decode().splitlines()
    assert len(lines) == len(set(lines)) and all(p.startswith('/') and not p.startswith('!') for p in lines)
    tools = {'git': git('--version').decode().strip(), 'python': sys.version,
             'python_executable': sys.executable, 'bytecode_writes_disabled': sys.dont_write_bytecode}
    assert sys.dont_write_bytecode
    all_entries = parse_tree(git('ls-tree', '-r', '-z', '-l', BASE))
    absent_tool_configs = ['rust-toolchain', 'rust-toolchain.toml', '.cargo', '.swiftpm', '.gitattributes',
                           '.gitmodules', '.lfsconfig', *[p + '/.swiftpm' for p in [
                               'experimental-capability-runtime', 'sdk', 'updates', 'runtime-identity',
                               'capability-activation', 'verification/capability-bridge-review']]]
    assert not any(prefix_paths(all_entries, p) for p in absent_tool_configs)
    names = b''.join(p.encode() + b'\0' for p in sorted(all_entries))
    matched = git('sparse-checkout', 'check-rules', '--no-cone', '--rules-file', str(OUT / 'sparse-checkout.txt'), '-z', data=names)
    selected_names = {p.decode() for p in matched.split(b'\0') if p}
    selected = {p: all_entries[p] for p in sorted(selected_names)}
    assert all(v['mode'] in ('100644', '100755') for v in selected.values())
    current_blobs = read_blobs(selected)
    for p, value in selected.items():
        value['sha256'] = sha(current_blobs[p])
    builder = current_blobs['experimental-capability-runtime/build-vm.py']
    builder_paths = literal_assignment(builder, 'PATHS')
    header_hashes = literal_assignment(builder, 'HEADER_HASHES')
    pin_source = current_blobs['experimental-capability-runtime/build-tests/test_builder.py']
    assert literal_assignment(pin_source, 'PIN') == PIN
    assert git('cat-file', '-t', PIN).strip() == b'commit'
    git('merge-base', '--is-ancestor', PIN, BASE)
    historical_required = ['vm/include/mixer_vm.h', 'vm/include/mixer_vm_capability.h',
                           'vm/include/mixer_vm_guest_ui.h', 'contracts/vm-profile-v1.json',
                           'contracts/vm-session-v1.json', 'contracts/guest-capability-transport-v1.json',
                           'capabilities/schema/v1.json', 'capabilities/schema/hashes.json',
                           'runtime/Sources/CMixerVM/include/mixer_vm.h']
    historical = parse_tree(git('ls-tree', '-r', '-z', '-l', PIN, '--', *historical_required))
    assert set(historical) == set(historical_required)
    historical_blobs = read_blobs(historical)
    for p, entry in historical.items():
        entry['sha256'] = sha(historical_blobs[p])
    for p, expected in header_hashes.items():
        assert selected[p]['sha256'] == historical[p]['sha256'] == expected
    assert selected['contracts/guest-capability-transport-v1.json']['sha256'] == '052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439'
    assert current_blobs['vm/include/mixer_vm.h'] == current_blobs['runtime/Sources/CMixerVM/include/mixer_vm.h']
    assert json.loads(current_blobs['capabilities/schema/hashes.json'])['nativeImplementationSHA256'] == sha(
        current_blobs['capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/native-preimage.json'])

    groups = {}
    packages = ['experimental-capability-runtime', 'runtime-identity', 'updates', 'sdk', 'capability-activation']
    for package in packages:
        group = set()
        for part in ['Package.swift', 'Package.resolved', 'Sources', 'Tests']:
            group |= prefix_paths(all_entries, package + '/' + part)
        groups['package:' + package] = group
    groups['builder-current-frozen-git-export'] = set().union(*(prefix_paths(all_entries, p) for p in builder_paths))
    groups['builder-runner-and-original-boundaries'] = prefix_paths(all_entries, 'experimental-capability-runtime/build-tests') | {
        'experimental-capability-runtime/build-vm.py', 'experimental-capability-runtime/verification/with-loopback.py'}
    groups['ci-tool-and-binding-runners'] = {'scripts/ci/verify-apple-toolchain.py', 'scripts/ci/check-android-binding.py'}
    groups['native-preimage-generator-read-only-check'] = set().union(*(prefix_paths(all_entries, p) for p in [
        'sdk/Sources/MixerCapabilities', 'capabilities/java/mixer/capabilities', 'capabilities/schema'])) | {
        'capabilities/tools/export-native-preimage.py', 'capabilities/tools/generate.py',
        'verification/capability-installed-material/test_native_preimage.py'}
    groups['public-bridge-target-and-complete-resources'] = prefix_paths(all_entries, 'verification/capability-bridge-review/PublicHarness') | {
        'verification/capability-bridge-review/Package.swift'}
    bridge_pin = 'verification/capability-bridge-review/Package.resolved'
    if bridge_pin in all_entries:
        groups['public-bridge-target-and-complete-resources'].add(bridge_pin)
    groups['android-binding-exact-explicit-inputs'] = prefix_paths(all_entries, 'native/android/signed-guest-ui/binding/include') | {
        'native/android/signed-guest-ui/transport/transport.c', 'native/android/signed-guest-ui/transport/internal.h',
        'native/android/signed-guest-ui/transport/include/mixer_ui_transport.h',
        *('verification/android-binding-stage4/' + p for p in ['HostEntry.swift', 'HostTests.swift', 'HoldingExecutor.swift']),
        *('verification/android-binding-stage4/host-bridge/' + p for p in ['host_bridge.c', 'mixer_android_host_bridge.h',
           'host_test.h', 'module.modulemap', 'test.modulemap'])}
    groups['copied-sdk-tests-external-canonical-data'] = {
        'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
        'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
        'verification/ui-appearance-foundation/design-corpus.json'}
    required = set().union(*groups.values())
    assert required <= selected_names
    assert required <= all_entries.keys()
    # Source set accounting is exact, including the three conservative copied-test data files.
    assert selected_names == required
    dirty = []
    for p in selected:
        live = ROOT / p
        if not live.is_file() or sha(live.read_bytes()) != selected[p]['sha256']:
            dirty.append(p)
    assert not dirty, 'working tree differs from canonical selected inputs: ' + repr(dirty)
    optional_absent = [p for p in lines if not any(x == p[1:] or x.startswith(p[1:]) for x in all_entries)]
    controls = {
        'vm/src/future-source.rs': True,
        'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/future.json': True,
        'experimental-capability-runtime/Package.resolved': True,
        'verification/capability-bridge-review/PublicHarness/Fixtures/future.wasm': True,
        'verification/capability-bridge-review/final-receipt.json': False,
        'verification/capability-bridge-review/InternalHarness/Package.swift': False,
        'verification/capability-installed-material/evidence-manifest.sha256': False,
        'verification/android-binding-stage4/host-bridge/scheduler_probe.c': False,
        'verification/unrelated-packet/Package.swift': False,
        'vm/verification/unrelated-receipt.json': False,
        'native/android/tests/run-private-owner-host.py': False,
        'services/lib/mixer.ex': False,
    }
    control_matches = git('sparse-checkout', 'check-rules', '--no-cone', '--rules-file', str(OUT / 'sparse-checkout.txt'), '-z',
                          data=b''.join(p.encode() + b'\0' for p in controls))
    observed_controls = {p.decode() for p in control_matches.split(b'\0') if p}
    assert observed_controls == {p for p, keep in controls.items() if keep}

    text = workflow.decode()
    start = text.index('  swift-capability-native:\n')
    end = text.index('  vm:\n', start)
    job = text[start:end]
    anchor = '          # Builder boundary fixtures read the independently reviewed native pin.\n          fetch-depth: 0\n'
    assert job.count(anchor) == 1 and 'sparse-checkout:' not in job
    addition = ('          # Keep the committed VM export, declared packages and exact host fixtures.\n'
                '          # The builder boundary tests still need the historical native pin.\n'
                '          sparse-checkout-cone-mode: false\n          sparse-checkout: |\n' +
                ''.join('            ' + p + '\n' for p in lines))
    proposed_job = job.replace(anchor, anchor + addition)
    proposed = text[:start] + proposed_job + text[end:]
    assert proposed_job.replace(addition, '') == job
    assert proposed[:start] == text[:start] and proposed.endswith(text[end:])
    diff = ''.join(difflib.unified_diff(text.splitlines(True), proposed.splitlines(True),
                                      fromfile='a/.github/workflows/verify.yml', tofile='b/.github/workflows/verify.yml'))
    (OUT / 'workflow-base.txt').write_bytes(workflow)
    (OUT / 'proposed-workflow.diff').write_text(diff)
    git('apply', '--check', str(OUT / 'proposed-workflow.diff'))
    # Required fetch depth and every non-checkout byte remain unchanged.
    write_json('source-closure.json', {
        'source_revision': BASE, 'source_tree': TREE, 'files': selected,
        'groups': {k: sorted(v) for k, v in sorted(groups.items())},
        'optional_patterns_without_current_entries': optional_absent,
        'absent_tracked_tool_configuration_paths_checked': absent_tool_configs,
        'complete_resource_subtrees': [p for p in selected if '/Fixtures/' in p],
        'canonical_data': {p: selected[p] for p in sorted(groups['copied-sdk-tests-external-canonical-data'])},
        'manifest_files': {p: v for p, v in selected.items() if Path(p).name in ['Package.swift', 'Package.resolved', 'Cargo.toml', 'Cargo.lock']},
    })
    write_json('historical-inputs.json', {'revision': PIN, 'is_ancestor_of_source_revision': True,
                                         'fetch_depth_required': 0, 'files': historical})
    (OUT / 'source-manifest.sha256').write_text(''.join(f'{v["sha256"]}  {p}\n' for p, v in sorted(selected.items())))
    write_json('rule-controls.json', {'git_matcher': tools['git'], 'controls': [
        {'path': p, 'expected_selected': keep, 'observed_selected': p in observed_controls} for p, keep in controls.items()]})
    total_bytes = sum(v['bytes'] for v in all_entries.values())
    selected_bytes = sum(v['bytes'] for v in selected.values())
    receipt = {
        'schema': 1, 'status': 'source-only-proposal-frozen',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'source_revision': BASE, 'source_tree': TREE,
        'workflow_base_sha256': sha(workflow), 'proposed_workflow_sha256': sha(proposed.encode()),
        'patterns_sha256': sha(patterns), 'pattern_count': len(lines),
        'fetch_depth': 0, 'tools': tools, 'commands': LOG,
        'full_committed_tree': {'files': len(all_entries), 'bytes': total_bytes},
        'selected_current_closure': {'files': len(selected), 'bytes': selected_bytes,
                                     'source_manifest_sha256': sha((OUT / 'source-manifest.sha256').read_bytes())},
        'historical_pin_inputs': {'files': len(historical), 'bytes': sum(v['bytes'] for v in historical.values())},
        'checks': {'required_path_coverage': True, 'selected_set_equals_declared_closure': True,
                   'selected_worktree_equals_canonical_blobs': True, 'native_header_pins': True,
                   'historical_pin_available': True, 'git_noncone_rule_controls': len(controls),
                   'proposed_patch_applies_without_writes': True, 'native_preimage_fixture_matches_metadata_digest': True,
                   'all_non_checkout_workflow_bytes_unchanged': True,
                   'outside_target_job_bytes_unchanged_in_proposal': True,
                   'no_tracked_toolchain_cargo_swiftpm_attribute_submodule_overrides_at_checked_paths': True,
                   'live_workflow_unchanged': sha((ROOT / '.github/workflows/verify.yml').read_bytes()) == WORKFLOW_SHA},
        'elapsed_seconds': round(time.monotonic() - START, 6),
        'cleanup': {'scratch_created': False, 'alternate_git_index_created': False, 'materialization_performed': False,
                    'process_inventory_performed': False, 'persistent_child_processes_started': False,
                    'native_simulator_emulator_ui_capture_started': False, 'network_started': False,
                    'owned_cleanup_required': False},
        'limitations': [
            'No workflow edit, commit, push, remote CI lookup or hosted checkout was performed.',
            'No compiler, product/native/JVM host harness, loopback fixture, simulator, emulator, device or UI run.',
            'Source/metadata and local Git rule coverage do not prove Actions checkout timing, job success, product semantics, release or GA.',
            'Actions runner Git/filter behavior, remote object availability, SwiftPM resolution and runtime behavior remain unverified.',
            'Full history is intentionally retained; no timing or network-byte reduction is asserted.',
            'Three appearance JSON inputs are retained for copied SDK tests; this job does not explicitly execute dependency test suites.',
        ],
    }
    assert receipt['checks']['live_workflow_unchanged']
    write_json('receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'selected': receipt['selected_current_closure'],
                      'full': receipt['full_committed_tree'], 'historical_pin': receipt['historical_pin_inputs'],
                      'patterns': len(lines), 'rule_controls': len(controls), 'elapsed_seconds': receipt['elapsed_seconds']}))


if __name__ == '__main__':
    main()
