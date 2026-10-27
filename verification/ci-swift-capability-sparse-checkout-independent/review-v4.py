#!/usr/bin/env python3
"""Independent finite offline checkout audit; never imports or executes subjects.

New evidence is exclusive-create in this directory. Canonical Git reads are
restricted to the proposed positive paths and the fixed nine historical paths.
No worktree, alternate index, product build, network, or native process is used.
"""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PROPOSAL = ROOT / 'verification/ci-swift-capability-sparse-checkout-contract'
BASE = 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
BASE_TREE = '076842155358f5be57a6f97af73577687a32a6d4'
PIN = '1adb25c48a8723f56ed2649712fe5e357920c53e'
PACKET_SHA = '99b65cf71f7a07bb2fb8f129b673b82759cbb8c6796dd69a4dce6250a3d73ddc'
WORKFLOW_SHA = 'fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88'
PROPOSED_SHA = 'f83defbefd14e710103f4a948f02c15eea8cfd789841d3a5e3593efdb0572eeb'
START = time.monotonic()
COMMANDS = []


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def command(argv, stdin=b'', max_bytes=40 * 1024 * 1024):
    began = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, input=stdin, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=50)
    require(len(result.stdout) <= max_bytes and len(result.stderr) <= 65536,
            'command output exceeds bound')
    COMMANDS.append({'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 50,
                     'exit': result.returncode, 'elapsed_seconds': round(time.monotonic() - began, 6),
                     'stdin_bytes': len(stdin), 'stdin_sha256': digest(stdin),
                     'stdout_bytes': len(result.stdout), 'stdout_sha256': digest(result.stdout),
                     'stderr': result.stderr.decode()})
    require(result.returncode == 0, 'command failed: ' + repr(argv))
    return result.stdout


def git(*args, **kwargs):
    return command(['git', '--no-replace-objects', '-c', 'core.fsmonitor=false', *args], **kwargs)


def tree(revision, paths):
    raw = git('ls-tree', '-r', '-z', '-l', revision, '--', *paths)
    entries = {}
    for row in raw.split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            mode, kind, oid, size = meta.split()
            require(kind == b'blob' and mode in (b'100644', b'100755'), 'not a regular source blob')
            entries[path.decode()] = {'mode': mode.decode(), 'git_blob': oid.decode(), 'bytes': int(size)}
    return entries


def blobs(entries):
    ordered = sorted(entries)
    raw = git('cat-file', '--batch', stdin=''.join(entries[p]['git_blob'] + '\n' for p in ordered).encode())
    result = {}
    cursor = 0
    for path in ordered:
        end = raw.index(b'\n', cursor)
        oid, kind, size = raw[cursor:end].split()
        size = int(size)
        require(oid.decode() == entries[path]['git_blob'] and kind == b'blob' and size == entries[path]['bytes'], 'blob header mismatch')
        cursor = end + 1
        result[path] = raw[cursor:cursor + size]
        require(raw[cursor + size:cursor + size + 1] == b'\n', 'blob framing mismatch')
        cursor += size + 1
    require(cursor == len(raw), 'extra blob output')
    return result


def assignment(raw, name):
    for item in ast.parse(raw).body:
        if isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in item.targets):
            return item.value
    raise RuntimeError('missing assignment: ' + name)


def subset(entries, roots):
    return {p for p in entries if any(p == root or p.startswith(root.rstrip('/') + '/') for root in roots)}


def exclusive(name, raw):
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def main():
    signal.alarm(54)
    require(sys.dont_write_bytecode, 'run with python3 -B')
    head = git('rev-parse', 'HEAD').decode().strip()
    current_tree = git('rev-parse', 'HEAD^{tree}').decode().strip()
    require(git('rev-parse', BASE + '^{tree}').decode().strip() == BASE_TREE, 'proposal tree mismatch')
    tools = {'git': git('--version').decode().strip(), 'python': sys.version,
             'python_executable': sys.executable, 'bytecode_writes_disabled': True}

    manifest = (PROPOSAL / 'packet-manifest.sha256').read_bytes()
    require(digest(manifest) == PACKET_SHA, 'proposal packet seal differs from assignment')
    packet_members = {}
    for line in manifest.decode().splitlines():
        expected, name = line.split('  ', 1)
        require('/' not in name and name not in packet_members, 'unsafe packet manifest entry')
        raw = (PROPOSAL / name).read_bytes()
        require(digest(raw) == expected, 'proposal packet member changed: ' + name)
        packet_members[name] = expected
    require(len(packet_members) == 10, 'proposal member count mismatch')

    patterns = (PROPOSAL / 'sparse-checkout.txt').read_bytes()
    rules = patterns.decode().splitlines()
    require(len(rules) == 60 and len(set(rules)) == 60, 'expected 60 unique patterns')
    require(all(p.startswith('/') and not any(c in p for c in '![]*?\\\0') for p in rules), 'positive literal rooted rules required')
    roots = [p.strip('/') for p in rules]
    canonical = tree(BASE, roots)
    require(tree(head, roots) == canonical, 'relevant source changed since proposal base')
    payloads = blobs(canonical)
    declared = json.loads((PROPOSAL / 'source-closure.json').read_bytes())
    require(set(canonical) == set(declared['files']), 'finite tree differs from declared closure')
    for path, info in canonical.items():
        independently_observed = dict(info, sha256=digest(payloads[path]))
        require(independently_observed == declared['files'][path], 'canonical metadata mismatch: ' + path)
        require((ROOT / path).is_file() and (ROOT / path).read_bytes() == payloads[path], 'live input differs: ' + path)
    source_manifest = ''.join(digest(payloads[p]) + '  ' + p + '\n' for p in sorted(canonical)).encode()
    require(source_manifest == (PROPOSAL / 'source-manifest.sha256').read_bytes(), 'independent source manifest mismatch')
    require(len(canonical) == 370 and sum(x['bytes'] for x in canonical.values()) == 22995155, 'closure size mismatch')

    # Independently require the union learned from the invoked command bodies.
    packages = ['experimental-capability-runtime', 'sdk', 'updates', 'runtime-identity', 'capability-activation']
    package_roots = [p + '/' + tail for p in packages for tail in ['Package.swift', 'Package.resolved', 'Sources', 'Tests']]
    builder_ast = ast.parse(payloads['experimental-capability-runtime/build-vm.py'])
    export_paths = ast.literal_eval(assignment(payloads['experimental-capability-runtime/build-vm.py'], 'PATHS'))
    explicit_android = [
        'native/android/signed-guest-ui/binding/include/module.modulemap',
        'native/android/signed-guest-ui/binding/include/mixer_ui_binding.h',
        'native/android/signed-guest-ui/transport/transport.c',
        'native/android/signed-guest-ui/transport/internal.h',
        'native/android/signed-guest-ui/transport/include/mixer_ui_transport.h',
        'verification/android-binding-stage4/HostEntry.swift',
        'verification/android-binding-stage4/HostTests.swift',
        'verification/android-binding-stage4/HoldingExecutor.swift',
        *['verification/android-binding-stage4/host-bridge/' + p for p in
          ['host_bridge.c', 'mixer_android_host_bridge.h', 'host_test.h', 'module.modulemap', 'test.modulemap']],
    ]
    appearance = [
        'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
        'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
        'verification/ui-appearance-foundation/design-corpus.json',
    ]
    independent_roots = [*package_roots, *export_paths, *explicit_android, *appearance,
        'scripts/ci/verify-apple-toolchain.py', 'scripts/ci/check-android-binding.py',
        'experimental-capability-runtime/build-vm.py', 'experimental-capability-runtime/build-tests',
        'experimental-capability-runtime/verification/with-loopback.py',
        'capabilities/java/mixer/capabilities', 'capabilities/schema',
        'capabilities/tools/generate.py', 'capabilities/tools/export-native-preimage.py',
        'verification/capability-installed-material/test_native_preimage.py',
        'verification/capability-bridge-review/Package.swift',
        'verification/capability-bridge-review/Package.resolved',
        'verification/capability-bridge-review/PublicHarness',
    ]
    independently_required = tree(BASE, independent_roots)
    require(independently_required == canonical, 'independent command-input union mismatch')
    require(len(subset(canonical, export_paths)) == 145, 'VM export count mismatch')
    require(len(subset(canonical, ['verification/capability-bridge-review'])) == 11, 'public bridge count mismatch')
    require(set(explicit_android) <= canonical.keys() and len(explicit_android) == 13, 'Android explicit inputs incomplete')

    # Git's own matcher, including adversarial adjacent names and future inputs.
    controls = {p: True for p in canonical}
    positives = ['vm/src/future/new.rs', 'vm/build.rs', 'sdk/Package.resolved',
        'experimental-capability-runtime/Package.resolved', 'verification/capability-bridge-review/Package.resolved',
        'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/future/nested.json',
        'verification/capability-bridge-review/PublicHarness/Fixtures/future.wasm']
    negatives = ['vm/src-neighbor/omit.rs', 'vm/verification/receipt.json',
        'sdk/Tests-neighbor/omit.swift', 'sdk/.swiftpm/configuration/mirrors.json',
        'verification/capability-bridge-review/InternalHarness/Tests.swift',
        'verification/capability-bridge-review/final-receipt.json',
        'verification/capability-installed-material/evidence-manifest.sha256',
        'verification/android-binding-stage4/host-bridge/scheduler_probe.c',
        'verification/android-binding-stage4/host-bridge/mixer_android_host_bridge.h.extra',
        'verification/android-binding-stage4/HostTests.swift.extra',
        'native/android/signed-guest-ui/transport/transport.c.extra',
        'native/android/signed-guest-ui/transport/include-neighbor/mixer_ui_transport.h',
        'verification/unrelated/Package.swift', 'hosted/lib/unrelated.ex',
        'vm/Cargo.toml.extra', 'experimental-capability-runtime/build-vm.py.extra']
    controls.update({p: True for p in positives})
    controls.update({p: False for p in negatives})
    matched = git('sparse-checkout', 'check-rules', '--no-cone', '--rules-file', str(PROPOSAL / 'sparse-checkout.txt'), '-z',
                  stdin=b''.join(p.encode() + b'\0' for p in controls))
    actual = {p.decode() for p in matched.split(b'\0') if p}
    require(actual == {p for p, retain in controls.items() if retain}, 'independent Git matcher control failed')

    # A finite canonical archive proves tar membership and all 370 actual bytes,
    # without extraction or a checkout; this does not run the subject builder.
    archived = git('archive', '--format=tar', BASE, '--', *sorted(canonical))
    with tarfile.open(fileobj=io.BytesIO(archived), mode='r:') as archive:
        members = {m.name: m for m in archive.getmembers() if not m.isdir()}
        require(set(members) == set(canonical), 'canonical archive member mismatch')
        for path, member in members.items():
            require(member.isreg() and archive.extractfile(member).read() == payloads[path], 'canonical archive data mismatch')

    # Determine historical reads from REQUIRED's starred header dictionary.
    constants = {}
    for node in builder_ast.body:
        if not isinstance(node, ast.Assign):
            continue
        for name in node.targets:
            if isinstance(name, ast.Name) and name.id in ['HEADER_HASHES', 'REQUIRED']:
                if name.id == 'HEADER_HASHES':
                    constants[name.id] = ast.literal_eval(node.value)
                else:
                    values = []
                    for element in node.value.elts:
                        values.extend(constants[element.value.id] if isinstance(element, ast.Starred) else [ast.literal_eval(element)])
                    constants[name.id] = values
    historical_paths = [p for p in constants['REQUIRED'] if p not in ['vm/Cargo.toml', 'vm/Cargo.lock', 'vm/src/lib.rs']]
    require(ast.literal_eval(assignment(payloads['experimental-capability-runtime/build-tests/test_builder.py'], 'PIN')) == PIN, 'historical test pin mismatch')
    git('merge-base', '--is-ancestor', PIN, head)
    historical = tree(PIN, historical_paths)
    historical_blobs = blobs(historical)
    historical_packet = json.loads((PROPOSAL / 'historical-inputs.json').read_bytes())
    require(len(historical) == 9 and sum(v['bytes'] for v in historical.values()) == 62506, 'historical closure differs')
    for path, info in historical.items():
        require(dict(info, sha256=digest(historical_blobs[path])) == historical_packet['files'][path], 'historical input mismatch')
    for path, expected in constants['HEADER_HASHES'].items():
        require(digest(payloads[path]) == digest(historical_blobs[path]) == expected, 'header pin mismatch')
    require(digest(payloads['contracts/guest-capability-transport-v1.json']) == '052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439', 'transport contract drift')
    require(payloads['vm/include/mixer_vm.h'] == payloads['runtime/Sources/CMixerVM/include/mixer_vm.h'], 'legacy header differs')
    fixture = payloads['capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/native-preimage.json']
    require(digest(fixture) == json.loads(payloads['capabilities/schema/hashes.json'])['nativeImplementationSHA256'] == '4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59', 'preimage fixture digest mismatch')
    # Reconstruct the read-only preimage independently without generator imports.
    native_records = {}
    excluded = ['GeneratedIdentity.swift', 'CapabilityNativeIdentity.java', 'CapabilityProbe.java']
    for path in subset(canonical, ['sdk/Sources/MixerCapabilities', 'capabilities/java/mixer/capabilities']):
        if Path(path).name not in excluded:
            normalized = payloads[path].decode().replace('\r\n', '\n').replace('\r', '\n').encode()
            native_records[path] = digest(normalized)
    schema = json.loads(payloads['capabilities/schema/v1.json'])
    compact = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    native_records['capabilities/schema/v1.json'] = digest(compact(schema))
    reconstructed = compact([{'path': p, 'sha256': h} for p, h in sorted(native_records.items())])
    require(reconstructed == fixture and len(native_records) == 17, 'independent native preimage differs')

    overrides = ['rust-toolchain', 'rust-toolchain.toml', '.cargo', '.swiftpm', '.gitattributes', '.gitmodules', '.lfsconfig',
                 *[p + '/.swiftpm' for p in packages + ['verification/capability-bridge-review']]]
    require(not tree(BASE, overrides) and not tree(head, overrides), 'tracked root/package override requires review')
    workflow = (ROOT / '.github/workflows/verify.yml').read_bytes()
    require(workflow == (PROPOSAL / 'workflow-base.txt').read_bytes() and digest(workflow) == WORKFLOW_SHA, 'workflow base drift')
    lines = workflow.decode().splitlines(True)
    addition = ('          # Keep the committed VM export, declared packages and exact host fixtures.\n'
                '          # The builder boundary tests still need the historical native pin.\n'
                '          sparse-checkout-cone-mode: false\n          sparse-checkout: |\n' +
                ''.join('            ' + p + '\n' for p in rules))
    anchor = '          # Builder boundary fixtures read the independently reviewed native pin.\n          fetch-depth: 0\n'
    job_start = workflow.index(b'  swift-capability-native:\n')
    job_end = workflow.index(b'  vm:\n', job_start)
    original_job = workflow[job_start:job_end].decode()
    require(original_job.count(anchor) == 1, 'ambiguous target-job checkout anchor')
    proposed = workflow[:job_start].decode() + original_job.replace(anchor, anchor + addition) + workflow[job_end:].decode()
    expected_patch = ''.join(difflib.unified_diff(lines, proposed.splitlines(True), fromfile='a/.github/workflows/verify.yml', tofile='b/.github/workflows/verify.yml')).encode()
    require(expected_patch == (PROPOSAL / 'proposed-workflow.diff').read_bytes(), 'patch contains unexpected change')
    require(digest(proposed.encode()) == PROPOSED_SHA and proposed.replace(addition, '').encode() == workflow, 'proposed byte identity mismatch')
    job_start = workflow.index(b'  swift-capability-native:\n')
    job_end = workflow.index(b'  vm:\n', job_start)
    require(job_start < workflow.index(anchor.encode(), job_start, job_end) < job_end, 'addition is outside target job')
    git('apply', '--check', str(PROPOSAL / 'proposed-workflow.diff'))
    require((ROOT / '.github/workflows/verify.yml').read_bytes() == workflow, 'workflow was changed during review')
    require((PROPOSAL / 'packet-manifest.sha256').read_bytes() == manifest, 'proposal seal changed during review')
    require(git('rev-parse', 'HEAD').decode().strip() == head, 'HEAD changed during audit')

    receipt = {
        'schema': 1, 'result': 'bounded-source-coverage-accepted',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'elapsed_seconds': round(time.monotonic() - START, 6), 'whole_audit_alarm_seconds': 54,
        'source': {'head': head, 'tree': current_tree, 'proposal_base': BASE, 'proposal_tree': BASE_TREE,
                   'relevant_base_to_head_metadata_equal': True, 'live_370_inputs_equal_canonical': True},
        'proposal_manifest_sha256': PACKET_SHA, 'proposal_members': packet_members,
        'workflow_base_sha256': WORKFLOW_SHA, 'proposed_workflow_sha256': PROPOSED_SHA,
        'current_closure': {'files': len(canonical), 'bytes': sum(v['bytes'] for v in canonical.values()),
                            'source_manifest_sha256': digest(source_manifest), 'canonical_archive_bytes': len(archived),
                            'canonical_archive_sha256': digest(archived)},
        'counts': {'patterns': len(rules), 'VM_export_files': 145, 'Android_explicit_inputs': 13,
                   'public_bridge_members': 11, 'Git_matcher_controls': len(controls),
                   'additional_positive_controls': len(positives), 'additional_negative_controls': len(negatives),
                   'historical_inputs': 9, 'historical_input_bytes': 62506, 'native_preimage_records': 17},
        'checks': ['ten-member producer packet integrity', 'finite independent command-input union',
                   'base/current/live canonical byte equality', 'canonical tar member and byte equality',
                   'native Git noncone rule inclusion/exclusion controls', 'historical fixed pin ancestry and nine blobs',
                   'native public header and transport contract pins', 'independently reconstructed native preimage',
                   'tracked root/package override absence at bounded paths', 'checkout-only diff and full-history retention',
                   'live workflow unchanged; patch check-only'],
        'tools': tools, 'commands': COMMANDS,
        'scope': 'Offline source and file-coverage review only. No subject script imported or executed.',
        'pending': ['remote Actions checkout/filter behavior and duration', 'remote historical object availability',
                    'actual complete job results and external SwiftPM resolution', 'native/runtime behavior',
                    'paused simulator/emulator/UI/capture checks', 'physical device, release, operational and GA gates'],
        'cleanup': {'only_new_review_evidence_written': True, 'scratch_repository_created': False,
                    'alternate_index_created': False, 'checkout_materialized': False, 'tar_extracted': False,
                    'persistent_child_started': False, 'native_or_capture_started': False, 'network_started': False,
                    'process_inventory_performed': False, 'owned_cleanup_required': False},
    }
    exclusive('receipt.json', json_bytes(receipt))
    exclusive('controls.json', json_bytes({'controls': controls, 'observed_selected': sorted(actual)}))
    print(json.dumps({'result': receipt['result'], 'source': receipt['source'], 'counts': receipt['counts'],
                      'closure': receipt['current_closure'], 'seconds': receipt['elapsed_seconds']}, sort_keys=True))


if __name__ == '__main__':
    main()
