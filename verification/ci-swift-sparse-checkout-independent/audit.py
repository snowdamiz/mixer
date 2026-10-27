#!/usr/bin/env python3
"""Independent read-only Git/source audit; writes only this audit directory.

Does not import or run a producer checker, materialize a checkout, invoke a
compiler/product command, access the network, or inspect global processes.
"""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/ci-swift-sparse-checkout'
REVISION = '114a2632fd58076574bd5b2444c511861c3b30d4'
CANDIDATE_SHA = '80d09b839d91a8be0a50bb19fc84b63b421193af26e1b2a95aa668f98b7a4680'
BASE_SHA = '2c701a47ef42129547048623eff7db7db721fb2fe39d3dabf4bb7bb6d1f939a0'
PACKETS = [
    'verification/runtime-review', 'verification/guest-capability-contract',
    'verification/swift-ordered-retention-analyzer-library',
    'verification/swift-ordered-retention-analyzer-library-review',
    'verification/swift-envelope-ci-pack',
]
DATA = [
    'verification/android-default-appearance-packaging/run-2/created-descriptor.json',
    'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
    'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
    'verification/ui-appearance-foundation/design-corpus.json',
]
COMMANDS = []
ENV = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
ENV.update(GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0',
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def run(argv, data=None):
    need(argv[0] == 'git', 'Only read-only Git subprocesses are permitted')
    need(argv[1] in ('--version', 'rev-parse', 'show', 'ls-tree', 'cat-file', 'archive')
         or argv[1:3] == ['sparse-checkout', 'check-rules'], 'Unapproved Git command')
    started = time.monotonic()
    p = subprocess.run(argv, input=data, cwd=ROOT, env=ENV, capture_output=True,
                       timeout=45, check=False)
    COMMANDS.append({'argv': argv, 'cwd': str(ROOT), 'exit': p.returncode,
                     'stdin_bytes': len(data or b''), 'stdin_sha256': sha(data or b''),
                     'stdout_bytes': len(p.stdout), 'stdout_sha256': sha(p.stdout),
                     'stderr': p.stderr.decode(errors='replace'),
                     'elapsed_seconds': round(time.monotonic() - started, 6)})
    need(p.returncode == 0, 'Read-only Git command failed: ' + repr(argv))
    return p.stdout


def snapshot_producer():
    rows = []
    for p in sorted(PRODUCER.rglob('*')):
        need(not p.is_symlink(), 'Unexpected producer packet symlink')
        if p.is_file():
            data = p.read_bytes()
            rows.append({'path': p.relative_to(PRODUCER).as_posix(),
                         'bytes': len(data), 'sha256': sha(data)})
    return {'files': len(rows), 'bytes': sum(r['bytes'] for r in rows),
            'inventory_sha256': digest(rows)}


def parse_assignments(path):
    module = ast.parse((ROOT / path).read_bytes())
    return {t.id: n.value for n in module.body if isinstance(n, ast.Assign)
            for t in n.targets if isinstance(t, ast.Name)}


def source_guard(paths):
    rows = []
    for path in sorted(paths):
        p = ROOT / path
        need(not p.is_symlink(), 'Unexpected source symlink: ' + path)
        raw = p.read_bytes()
        rows.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
    return rows


def main():
    started = datetime.now(timezone.utc).isoformat()
    producer_before = snapshot_producer()
    source_paths = {
        '.github/workflows/verify.yml', 'AGENTS.md', 'Package.swift', 'sdk/Package.swift',
        'capabilities/Package.swift', 'updates/Package.swift', 'cli/Package.swift',
        'native/android/engine/Package.swift', 'runtime-identity/Package.swift',
        'runtime/Package.swift', 'activation/Package.swift',
        'verification/runtime-review/Package.swift', 'scripts/check-policy.py',
        'runtime/build-vm.py', 'experimental-capability-runtime/build-vm.py',
        'cli/Sources/MixerBuild/ProjectGenerator.swift',
        'cli/Sources/MixerBuild/Configuration.swift', 'cli/Sources/MixerCLI/main.swift',
        'sdk/Tests/MixerUITests/AppearanceV1Tests.swift',
        'sdk/Tests/MixerUITests/AppearanceDescriptorV2Tests.swift',
        'capabilities/tools/check-guest-transport-fixtures.py',
    }
    for directory in ('scripts/ci', 'cli/build-tests', 'runtime/build-tests',
                      'runtime-identity/build-tools', 'runtime-identity/tools'):
        source_paths.update(p.relative_to(ROOT).as_posix()
                            for p in (ROOT / directory).rglob('*.py')
                            if '__pycache__' not in p.parts)
    source_before = source_guard(source_paths)
    python_identity = {'version': platform.python_version(), 'executable': sys.executable,
                       'platform': platform.platform()}
    git = run(['git', '--version']).decode().strip()
    head_before = run(['git', 'rev-parse', 'HEAD']).decode().strip()
    tree_id = run(['git', 'rev-parse', REVISION + '^{tree}']).decode().strip()
    base = run(['git', 'show', REVISION + ':.github/workflows/verify.yml'])
    candidate = (ROOT / '.github/workflows/verify.yml').read_bytes()
    need(sha(base) == BASE_SHA and sha(candidate) == CANDIDATE_SHA, 'Frozen workflow identity differs')
    original_lines, candidate_lines = base.splitlines(keepends=True), candidate.splitlines(keepends=True)
    changes = [op for op in difflib.SequenceMatcher(a=original_lines, b=candidate_lines,
                                                   autojunk=False).get_opcodes() if op[0] != 'equal']
    need(len(changes) == 1 and changes[0][0] == 'insert', 'Workflow has another byte delta')
    _, i1, i2, j1, j2 = changes[0]
    need(i1 == i2 and b'  swift:\n' in original_lines[:i1]
         and b'  swift-capability-native:\n' not in original_lines[:i1], 'Insertion outside Swift job')
    need(original_lines[i1-1] == b'          fetch-depth: 0\n'
         and original_lines[i1] == b'      - name: Verify and record pinned Apple toolchain\n',
         'Insertion outside checkout with block')
    inserted = b''.join(candidate_lines[j1:j2])
    before_patterns, rendered = inserted.split(b'          sparse-checkout: |\n', 1)
    need(b'          sparse-checkout-cone-mode: false\n' in before_patterns,
         'Non-cone mode not explicit')
    need(all(line.startswith(b'            ') for line in rendered.splitlines()), 'Malformed pattern indentation')
    patterns = b'\n'.join(line[12:] for line in rendered.splitlines()) + b'\n'
    need(patterns == (PRODUCER / 'patterns.txt').read_bytes(), 'Evidence and workflow rules differ')
    (HERE / 'workflow.diff').write_text(''.join(difflib.unified_diff(
        base.decode().splitlines(True), candidate.decode().splitlines(True),
        fromfile=REVISION + '/verify.yml', tofile='candidate/verify.yml')))

    raw_tree = run(['git', 'ls-tree', '-r', '-l', '-z', REVISION])
    tree = {}
    for row in raw_tree.split(b'\0'):
        if not row:
            continue
        metadata, path = row.split(b'\t', 1)
        mode, kind, oid, size = metadata.decode().split()
        need(kind == 'blob', 'Unexpected submodule/nonblob tree member')
        tree[path.decode()] = {'mode': mode, 'oid': oid, 'bytes': int(size)}
    for path in source_paths - {'.github/workflows/verify.yml'}:
        data = (ROOT / path).read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        need(path in tree and oid == tree[path]['oid'], 'Reviewed source differs from canonical: ' + path)
    manifests = ast.literal_eval(parse_assignments('scripts/check-policy.py')['manifests'])
    excluded = ast.literal_eval(parse_assignments('scripts/check-policy.py')['excluded'])
    def selected(path):
        return (not path.startswith('verification/') or Path(path).name in manifests
                or path in DATA or any(path.startswith(packet + '/') for packet in PACKETS))
    expected = {path for path in tree if selected(path)}
    actual = set(run(['git', 'sparse-checkout', 'check-rules', '--no-cone', '--rules-file',
                      str(PRODUCER / 'patterns.txt'), '-z'],
                     b'\0'.join(p.encode() for p in tree) + b'\0').decode().strip('\0').split('\0'))
    need(actual == expected, 'Independent Git selection differs')
    inventory = json.loads((PRODUCER / 'materialization-2/selected-inventory.json').read_bytes())
    inventory_map = {r['path']: {k: r[k] for k in ('mode', 'oid', 'bytes')} for r in inventory}
    need(len(inventory_map) == len(inventory) and inventory_map == {p: tree[p] for p in expected},
         'Materialized inventory differs from canonical Git tree')
    need(not [p for p in expected if tree[p]['mode'] == '120000'], 'Selected symlink needs further closure review')
    policy_paths = {p for p in tree if Path(p).name in manifests
                    and not (set(Path(p).parts[:-1]) & excluded)}
    all_manifest_paths = {p for p in tree if Path(p).name in manifests}
    need(all_manifest_paths <= actual and policy_paths <= actual, 'Policy manifest walk narrowed')
    synthetic = [f'verification/probe/.hidden/deep/{name}' for name in sorted(manifests)]
    synthetic += ['verification/probe/.hidden/deep/ordinary.bin', 'verification/ordinary.bin',
                  'future/.hidden/source.swift']
    controls = set(run(['git', 'sparse-checkout', 'check-rules', '--no-cone', '--rules-file',
                        str(PRODUCER / 'patterns.txt'), '-z'],
                       b'\0'.join(p.encode() for p in synthetic) + b'\0').decode().strip('\0').split('\0'))
    need(controls == {p for p in synthetic if selected(p)}, 'Future nested/hidden basename semantics differ')

    content_requirements = {}
    sealed_counts, external_sealed = {}, set()
    for packet, pin, count in [
        (PACKETS[2], '777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63', 270),
        (PACKETS[3], 'a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e', 624),
    ]:
        seal_raw = (ROOT / packet / 'seal.json').read_bytes()
        need(sha(seal_raw) == pin, 'Framing runner seal pin differs')
        need((ROOT / packet / 'seal.sha256').read_text().split()[0] == pin, 'Framing sidecar differs')
        rows = json.loads(seal_raw)['members']
        need(len(rows) == len({r['path'] for r in rows}) == count, 'Sealed member roster differs')
        sealed_counts[packet] = count
        for r in rows:
            need(r['path'] in expected, 'Sealed member omitted: ' + r['path'])
            content_requirements[r['path']] = r
            if not any(r['path'].startswith(pack + '/') for pack in PACKETS):
                external_sealed.add(r['path'])
    envelope = ROOT / PACKETS[4]
    manifest_raw = (envelope / 'manifest.json').read_bytes()
    need(sha(manifest_raw) == '4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a',
         'Envelope runner manifest pin differs')
    envelope_rows = json.loads(manifest_raw)['members']
    need(len(envelope_rows) == 86 and sum(r['bytes'] for r in envelope_rows) == 8330464,
         'Envelope member count/bytes differ')
    need({p[len(PACKETS[4]) + 1:] for p in expected if p.startswith(PACKETS[4] + '/')}
         == {'manifest.json'} | {r['path'] for r in envelope_rows}, 'Envelope packet inventory differs')
    need(digest(envelope_rows) == '7a73ac6f477b6ac90db0be8444712bc195c184fb21239266c07601f9ea90ecee',
         'Envelope inventory tree pin differs')
    for row in envelope_rows:
        r = dict(row, path=PACKETS[4] + '/' + row['path'])
        content_requirements[r['path']] = r
    corpus_raw = (ROOT / PACKETS[1] / 'cases.json').read_bytes()
    need(sha(corpus_raw) == '1b3813aba9f72c13ed8c6da498d75b89a1d6615a727b0309ea35ad4fc739c258',
         'Guest transport runner corpus pin differs')
    corpus_rows = json.loads(corpus_raw)['cases']
    need(len(corpus_rows) == 90, 'Guest corpus count differs')
    for row in corpus_rows:
        r = dict(row, path=PACKETS[1] + '/' + row['file'])
        content_requirements[r['path']] = r
    for path in DATA:
        raw = (ROOT / path).read_bytes()
        content_requirements[path] = {'path': path, 'bytes': len(raw), 'sha256': sha(raw)}
    for path in (PACKETS[2] + '/seal.json', PACKETS[2] + '/seal.sha256',
                 PACKETS[3] + '/seal.json', PACKETS[3] + '/seal.sha256',
                 PACKETS[4] + '/manifest.json', PACKETS[1] + '/cases.json'):
        raw = (ROOT / path).read_bytes()
        content_requirements[path] = {'path': path, 'bytes': len(raw), 'sha256': sha(raw)}
    requested = sorted(content_requirements)
    raw = run(['git', 'cat-file', '--batch'],
              b''.join((tree[p]['oid'] + '\n').encode() for p in requested))
    stream = io.BytesIO(raw)
    for path in requested:
        oid, kind, size = stream.readline().strip().decode().split()
        data = stream.read(int(size))
        need(stream.read(1) == b'\n' and kind == 'blob' and oid == tree[path]['oid'], 'Malformed batch blob')
        row = content_requirements[path]
        need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'Required canonical content differs: ' + path)
    need(not stream.read(), 'Unexpected batch tail')
    materialization = json.loads((PRODUCER / 'materialization-2/receipt.json').read_bytes())
    collector = (PRODUCER / 'materialization-2/collector.py').read_bytes()
    need(sha(collector) == materialization['collector_sha256']
         and collector == (PRODUCER / 'offline_check.py').read_bytes(), 'Frozen collector identity differs')
    need(materialization['status'] == 'passed-offline-materialization'
         and materialization['cleanup']['removed'], 'Final materialization or cleanup did not pass')
    need(all(r['exit'] == 0 and not r['timed_out'] and r['child_reaped'] and r['owned_group_gone']
             for r in materialization['commands']), 'Final producer command failure or unclosed group')
    archive = run(['git', 'archive', REVISION, 'vm', 'contracts/vm-session-v1.json'])
    archive_row = next(r for r in materialization['commands'] if r['name'] == 'head-vm-archive')
    need(sha(archive) == archive_row['stdout']['sha256'], 'Canonical VM archive differs')
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        need(tar.extractfile('vm/include/mixer_vm.h').read()
             == (ROOT / 'runtime/Sources/CMixerVM/include/mixer_vm.h').read_bytes(), 'VM archive/header closure differs')
        archive_paths = {member.name for member in tar if member.isfile()}
    need(archive_paths == {p for p in tree if p.startswith('vm/')} | {'contracts/vm-session-v1.json'},
         'Archive input roster differs')
    pin = materialization['materialization']['historical_pin']
    pin_hashes = {}
    for path, row in materialization['materialization']['historical_pin_inputs'].items():
        data = run(['git', 'show', pin + ':' + path])
        pin_hashes[path] = {'bytes': len(data), 'sha256': sha(data)}
        need(pin_hashes[path] == row, 'Historical pin content differs')
    # Three additional immutable VM source reads are retained in history; their
    # actual positive builder belongs to the unchanged sibling native job.
    remaining_pin_inputs = {}
    for path in ('vm/Cargo.toml', 'vm/Cargo.lock', 'vm/src/lib.rs'):
        data = run(['git', 'show', pin + ':' + path])
        remaining_pin_inputs[path] = {'bytes': len(data), 'sha256': sha(data)}
    source_after = source_guard(source_paths)
    producer_after = snapshot_producer()
    head_after = run(['git', 'rev-parse', 'HEAD']).decode().strip()
    need(source_before == source_after and producer_before == producer_after and head_before == head_after,
         'Reviewed source, frozen producer packet or source revision changed')
    result = {
        'schema': 1, 'status': 'accepted-bounded-independent-source-offline-review',
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(Path(__file__).resolve())],
        'auditor_sha256': sha(Path(__file__).read_bytes()), 'python': python_identity, 'git': git,
        'canonical_revision': REVISION, 'canonical_tree': tree_id, 'observed_head': head_before,
        'canonical_workflow_sha256': sha(base), 'candidate_workflow_sha256': sha(candidate),
        'patterns_sha256': sha(patterns), 'workflow_only_delta': {'inserted_lines': j2-j1,
        'location': 'swift.steps[0].with', 'all_commands_pins_triggers_timeouts_artifacts_other_jobs_equal': True},
        'canonical': {'files': len(tree), 'bytes': sum(r['bytes'] for r in tree.values()),
                      'git_ls_tree_stdout_sha256': sha(raw_tree)},
        'selected': {'files': len(expected), 'bytes': sum(tree[p]['bytes'] for p in expected),
                     'source_and_producer_inventory_equal': True, 'symlinks': 0},
        'non_verification': {'files': sum(not p.startswith('verification/') for p in tree),
                             'every_path_selected': True},
        'policy': {'basenames': sorted(manifests), 'all_basename_paths': len(all_manifest_paths),
                   'effective_walk_paths': len(policy_paths), 'omitted_paths': [],
                   'future_hidden_nested_manifest_controls_passed': True},
        'sealed_and_external_inputs': {'framing_members': sealed_counts,
             'outside_packet_sealed_paths': sorted(external_sealed), 'envelope_members': 86,
             'guest_corpus_cases': 90, 'exact_extra_data_paths': DATA,
             'distinct_canonical_content_hashes_verified': len(content_requirements)},
        'archive': {'revision': REVISION, 'bytes': len(archive), 'sha256': sha(archive),
                    'canonical_roster_and_working_wrapper_header_equal': True},
        'historical_pin': {'revision': pin, 'producer_nine_reads_equal': pin_hashes,
                            'additional_three_source_reads_available': remaining_pin_inputs,
                            'positive_builder_scope': 'unchanged swift-capability-native sibling'},
        'frozen_producer_before': producer_before, 'frozen_producer_after': producer_after,
        'reviewed_source_digest': digest(source_before), 'reviewed_source_unchanged': True,
        'reviewed_sources_match_canonical_git_blobs_except_candidate_workflow': True,
        'source_revision_unchanged': True, 'commands': COMMANDS,
        'limitations': ['No product test or compiler was run by this independent audit.',
                        'No checkout was rematerialized; producer actual materialization remains retained evidence.',
                        'Remote GitHub checkout behavior, timing and existing job commands remain pending CI.',
                        'Native runtime, physical devices, capture, operational and GA gates remain pending/out of scope.'],
        'network_requested': False, 'git_mutations': False, 'global_process_inventory': False,
        'product_or_compiler_execution': False, 'native_or_capture_execution': False,
        'finding_count': 0,
    }
    (HERE / 'reviewed-source-inputs.json').write_text(json.dumps(source_before, sort_keys=True, indent=2) + '\n')
    (HERE / 'receipt.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'selected', 'policy', 'finding_count',
                                          'candidate_workflow_sha256', 'reviewed_source_digest')}))


if __name__ == '__main__':
    main()
