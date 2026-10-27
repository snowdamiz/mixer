#!/usr/bin/env python3
"""Offline Git pattern/closure observations; never run product tests or compilers.

All Git writes are confined to one fresh, marked temporary directory. The source
repository is read via canonical Git objects. The optional checkout uses its
object directory only as an alternate and has no remote or network access.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

REVISION = '114a2632fd58076574bd5b2444c511861c3b30d4'
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MANIFESTS = {'Package.swift', 'Package.resolved', 'Cargo.toml', 'Cargo.lock',
             'package.json', 'package-lock.json', 'go.mod', 'go.sum',
             'build.gradle', 'build.gradle.kts', 'settings.gradle.kts'}
PACKETS = ('verification/runtime-review', 'verification/guest-capability-contract',
           'verification/swift-ordered-retention-analyzer-library',
           'verification/swift-ordered-retention-analyzer-library-review',
           'verification/swift-envelope-ci-pack')
FILES = ('verification/android-default-appearance-packaging/run-2/created-descriptor.json',
         'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
         'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
         'verification/ui-appearance-foundation/design-corpus.json')
LIMIT_BYTES = 250_000_000


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def wanted(path):
    return (not path.startswith('verification/') or Path(path).name in MANIFESTS
            or path in FILES or any(path.startswith(packet + '/') for packet in PACKETS))


class Commands:
    def __init__(self, output, receipt, deadline):
        self.output, self.receipt, self.deadline = output, receipt, deadline
        self.env = dict(os.environ)
        for key in tuple(self.env):
            if key.startswith('GIT_'):
                self.env.pop(key)
        self.env.update(GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0')

    def run(self, name, argv, cwd=ROOT, data=None, retain=True):
        left = self.deadline - time.monotonic()
        require(left > 0, 'Active deadline exhausted')
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd),
               'timeout_seconds': min(45, left), 'stdin_bytes': len(data or b''),
               'stdin_sha256': sha(data or b''), 'exit': None, 'timed_out': False}
        self.receipt['commands'].append(row)
        before = time.monotonic()
        child = None
        try:
            child = subprocess.Popen(list(map(str, argv)), cwd=cwd, env=self.env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, start_new_session=True)
            row['pid'] = child.pid
            try:
                out, err = child.communicate(data, timeout=min(45, left))
            except subprocess.TimeoutExpired:
                row['timed_out'] = True
                os.killpg(child.pid, signal.SIGKILL)
                out, err = child.communicate(timeout=3)
            row['exit'] = child.returncode
            row['child_reaped'] = True
            for label, raw in [('stdout', out), ('stderr', err)]:
                row[label] = {'bytes': len(raw), 'sha256': sha(raw), 'retained': retain or label == 'stderr'}
                if retain or label == 'stderr':
                    path = self.output / (name + '.' + label)
                    path.write_bytes(raw)
                    row[label]['path'] = path.name
            require(child.returncode == 0 and not row['timed_out'], 'Command failed: ' + name)
            return out
        finally:
            if child is not None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    row['remaining_owned_group_killed'] = True
                except ProcessLookupError:
                    row['remaining_owned_group_killed'] = False
                if child.poll() is None:
                    child.wait(timeout=3)
                try:
                    os.killpg(child.pid, 0)
                    row['owned_group_gone'] = False
                except ProcessLookupError:
                    row['owned_group_gone'] = True
            row['elapsed_seconds'] = round(time.monotonic() - before, 6)
            write(self.output / 'receipt.json', self.receipt)


def blob(commands, path, revision=REVISION):
    return commands.run('blob-' + sha((revision + ':' + path).encode())[:12],
                        ['git', 'show', revision + ':' + path], retain=False)


def closure(commands, tree):
    """Data-driven members are parsed, then compared to actual checkout bytes."""
    required, seals = set(FILES), {}
    for packet in PACKETS[2:4]:
        seal = json.loads(blob(commands, packet + '/seal.json'))
        names = [row['path'] for row in seal['members']]
        require(len(names) == len(set(names)), 'Duplicate seal member')
        for row in seal['members']:
            require(row['path'] in tree and tree[row['path']]['bytes'] == row['bytes'],
                    'Sealed canonical member missing/size differs')
        required.update(names)
        required.update((packet + '/seal.json', packet + '/seal.sha256'))
        seals[packet] = seal['members']
    manifest = json.loads(blob(commands, PACKETS[4] + '/manifest.json'))
    pack_rows = [{**row, 'path': PACKETS[4] + '/' + row['path']} for row in manifest['members']]
    required.update(row['path'] for row in pack_rows)
    required.add(PACKETS[4] + '/manifest.json')
    seals[PACKETS[4]] = pack_rows
    corpus = json.loads(blob(commands, PACKETS[1] + '/cases.json'))
    require(len(corpus['cases']) == 90, 'Guest corpus case count differs')
    for row in corpus['cases']:
        required.add(PACKETS[1] + '/' + row['file'])
    required.add(PACKETS[1] + '/cases.json')
    policy = ast.parse(blob(commands, 'scripts/check-policy.py'))
    declared = next(ast.literal_eval(node.value) for node in policy.body
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
                    and t.id == 'manifests' for t in node.targets))
    require(declared == MANIFESTS, 'Policy basename closure changed')
    required.update(path for path in tree if Path(path).name in declared)
    require(all(wanted(path) for path in required), 'Explicit closure not retained')
    return required, seals, corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialize', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    require(output.parent == HERE and not output.exists(), 'Fresh output must be under owned evidence directory')
    output.mkdir()
    shutil.copyfile(Path(__file__), output / 'collector.py')
    began = time.monotonic()
    receipt = {'schema': 1, 'started_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'offline Git pattern and input materialization only',
               'revision': REVISION, 'collector_sha256': sha(Path(__file__).read_bytes()),
               'python': platform.python_version(), 'python_executable': sys.executable,
               'platform': platform.platform(), 'materialize_requested': args.materialize,
               'active_limit_seconds': 50, 'total_limit_seconds': 55,
               'byte_ceiling': LIMIT_BYTES, 'commands': [], 'status': 'failed',
               'network_requested': False, 'product_tests_or_compilers_run': False,
               'native_runtime_or_capture_started': False}
    commands = Commands(output, receipt, began + 50)
    scratch = Path(tempfile.mkdtemp(prefix='mixer-ci-swift-sparse-', dir=str(Path(tempfile.gettempdir()).resolve())))
    stamp = scratch.stat()
    identity = (stamp.st_dev, stamp.st_ino)
    marker = {'owner': str(Path(__file__).resolve()), 'nonce': str(uuid.uuid4())}
    write(scratch / 'ownership.json', marker)
    try:
        receipt['git'] = commands.run('git-version', ['git', '--version']).decode().strip()
        receipt['tree'] = commands.run('tree-revision', ['git', 'rev-parse', REVISION + '^{tree}']).decode().strip()
        tree_raw = commands.run('canonical-tree', ['git', 'ls-tree', '-r', '-l', '-z', REVISION], retain=False)
        tree = {}
        for entry in tree_raw.split(b'\0'):
            if not entry:
                continue
            meta, path = entry.split(b'\t', 1)
            mode, kind, oid, size = meta.split()
            require(kind == b'blob', 'Unexpected non-blob tree member')
            tree[path.decode()] = {'bytes': int(size), 'oid': oid.decode(), 'mode': mode.decode()}
        expected = {path for path in tree if wanted(path)}
        required, seals, corpus = closure(commands, tree)
        receipt['canonical'] = {'files': len(tree), 'bytes': sum(row['bytes'] for row in tree.values())}
        receipt['selected'] = {'files': len(expected), 'bytes': sum(tree[path]['bytes'] for path in expected)}
        require(receipt['selected']['bytes'] <= LIMIT_BYTES, 'Expected selection exceeds byte ceiling')
        write(output / 'selected-inventory.json', [{'path': path, **tree[path]} for path in sorted(expected)])
        write(output / 'required-data-paths.json', sorted(required))
        patterns = (HERE / 'patterns.txt').read_bytes()
        receipt['patterns_sha256'] = sha(patterns)
        (output / 'patterns.txt').write_bytes(patterns)
        synthetic = scratch / 'synthetic'
        commands.run('synthetic-init', ['git', '-c', 'core.hooksPath=/dev/null', 'init', '--quiet', '--template=', synthetic])
        tiny = {'README.md', 'source/input.swift', 'verification/ordinary/nested/no.bin',
                'verification/ordinary/no.bin', 'verification/ordinary/Package.swift',
                'verification/ordinary/nested/Package.swift', 'verification/ordinary/nested/.hidden/go.mod',
                'verification/Package.swift', *FILES}
        tiny.update(packet + '/nested/.hidden/source.bin' for packet in PACKETS)
        for path in tiny:
            target = synthetic / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(('tiny-' + path).encode())
        commands.run('synthetic-add', ['git', '-c', 'core.hooksPath=/dev/null', 'add', '.'], cwd=synthetic)
        commands.run('synthetic-commit', ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                     '-c', 'user.name=Offline closure', '-c', 'user.email=offline@example.invalid', 'commit', '--quiet', '-m', 'Owned tiny pattern control'], cwd=synthetic)
        def select(label, raw_patterns, names):
            rules = scratch / (label + '.patterns')
            rules.write_bytes(raw_patterns)
            raw = commands.run(label, ['git', 'sparse-checkout', 'check-rules', '--no-cone',
                               '--rules-file', rules, '-z'], cwd=synthetic,
                               data=b'\0'.join(path.encode() for path in sorted(names)) + b'\0', retain=False)
            return set(raw.decode().strip('\0').split('\0')) if raw else set()
        tiny_actual = select('tiny-candidate', patterns, tiny)
        require(tiny_actual == {path for path in tiny if wanted(path)}, 'Tiny candidate mismatch')
        bad = patterns + b'/verification/**/\n'
        tiny_bad = select('tiny-broad-directory-negative', bad, tiny)
        require('verification/ordinary/nested/no.bin' in tiny_bad, 'Broad directory negative control did not expose unwanted recursion')
        actual = select('canonical-candidate', patterns, tree)
        require(actual == expected, 'Canonical Git rule semantics differ from independent closure predicate')
        receipt['canonical_git_selection'] = {'files': len(actual), 'bytes': sum(tree[path]['bytes'] for path in actual),
            'matches_independent_closure': True}
        broad = select('canonical-broad-directory-negative', bad, tree)
        receipt['broad_directory_negative'] = {'files': len(broad), 'bytes': sum(tree[path]['bytes'] for path in broad),
            'materialized': False}
        require(expected < broad and receipt['broad_directory_negative']['bytes'] > LIMIT_BYTES,
                'Broad-directory negative control did not exceed the checkout bound')
        without_manifests = b'\n'.join(line for line in patterns.splitlines() if b'/**/' not in line) + b'\n'
        missing = expected - select('canonical-missing-policy-negative', without_manifests, tree)
        require(missing and all(Path(path).name in MANIFESTS for path in missing), 'Manifest negative control differs')
        receipt['controls'] = {'tiny_candidate': {'passed': True, 'files': len(tiny_actual)},
            'recursive_directory_rejected': {'passed': True, 'canonical_files': len(broad),
                'canonical_bytes': sum(tree[path]['bytes'] for path in broad), 'materialized': False},
            'missing_policy_manifests_rejected': {'passed': True, 'missing_files': len(missing),
                'examples': sorted(missing)[:8]},
            'canonical_semantics_equal_independent_selection': True,
            'required_data_paths_selected': len(required)}
        require(required <= actual, 'Required dynamic inputs omitted')
        if args.materialize:
            materialized = scratch / 'materialized'
            commands.run('materialized-init', ['git', '-c', 'core.hooksPath=/dev/null', 'init', '--quiet', '--template=', materialized])
            original_objects = commands.run('objects-directory', ['git', 'rev-parse', '--git-path', 'objects']).decode().strip()
            original_objects = (ROOT / original_objects).resolve()
            (materialized / '.git/objects/info/alternates').write_text(str(original_objects) + '\n')
            commands.run('materialized-sparse-rules', ['git', 'sparse-checkout', 'set', '--no-cone', '--stdin'],
                         cwd=materialized, data=patterns)
            commands.run('materialized-head', ['git', 'update-ref', 'HEAD', REVISION], cwd=materialized)
            commands.run('materialized-read-tree', ['git', '-c', 'core.hooksPath=/dev/null', 'read-tree', '-mu', REVISION], cwd=materialized)
            found = set()
            for directory, dirs, files in os.walk(materialized):
                dirs[:] = [name for name in dirs if name != '.git']
                for filename in files:
                    path = Path(directory) / filename
                    relative = path.relative_to(materialized).as_posix()
                    found.add(relative)
                    raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
                    row = tree[relative]
                    require(len(raw) == row['bytes'], 'Materialized size differs: ' + relative)
                    actual_oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                    require(actual_oid == row['oid'], 'Materialized Git blob differs: ' + relative)
            require(found == expected, 'Materialized path set differs')
            for packet, rows in seals.items():
                for row in rows:
                    require(sha((materialized / row['path']).read_bytes()) == row['sha256'], 'Sealed content differs')
            for row in corpus['cases']:
                raw = (materialized / PACKETS[1] / row['file']).read_bytes()
                require(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'Guest corpus differs')
            archive = commands.run('head-vm-archive', ['git', 'archive', REVISION, 'vm', 'contracts/vm-session-v1.json'],
                                   cwd=materialized, retain=False)
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                require(tar.extractfile('vm/include/mixer_vm.h').read() == (materialized / 'runtime/Sources/CMixerVM/include/mixer_vm.h').read_bytes(), 'Archived VM header differs')
            # Historical pin belongs to swift-capability-native, whose checkout is
            # untouched. Check its independent ABI blob reads without executing it.
            builder = ast.parse(blob(commands, 'experimental-capability-runtime/build-vm.py'))
            headers = next(ast.literal_eval(n.value) for n in builder.body if isinstance(n, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == 'HEADER_HASHES' for t in n.targets))
            required_node = next(n.value for n in builder.body if isinstance(n, ast.Assign)
                                 and any(isinstance(t, ast.Name) and t.id == 'REQUIRED' for t in n.targets))
            require(isinstance(required_node, ast.List), 'Builder REQUIRED is no longer a literal list')
            required_pin = []
            for item in required_node.elts:
                if isinstance(item, ast.Starred):
                    require(isinstance(item.value, ast.Name) and item.value.id == 'HEADER_HASHES',
                            'Unexpected computed native pin input')
                    required_pin.extend(headers)
                else:
                    required_pin.append(ast.literal_eval(item))
            pin = '1adb25c48a8723f56ed2649712fe5e357920c53e'
            pinned = {}
            for path in required_pin:
                if path in ('vm/Cargo.toml', 'vm/Cargo.lock', 'vm/src/lib.rs'):
                    continue
                raw = commands.run('pin-' + sha(path.encode())[:12], ['git', 'show', pin + ':' + path],
                                   cwd=materialized, retain=False)
                pinned[path] = {'bytes': len(raw), 'sha256': sha(raw)}
            receipt['materialization'] = {'passed': True, **receipt['selected'],
                'all_selected_git_blobs_equal': True, 'sealed_member_content_equal': True,
                'guest_corpus_cases_equal': 90, 'all_manifest_basename_paths_equal': True,
                'head_vm_archive_available': True, 'head_vm_archive_bytes': len(archive),
                'historical_pin': pin, 'historical_pin_inputs': pinned,
                'object_alternate_read_only_commands': True, 'remotes_configured': False}
        receipt['status'] = 'passed-offline-materialization' if args.materialize else 'passed-offline-selection-plan'
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        current = scratch.stat()
        require((current.st_dev, current.st_ino) == identity and json.loads((scratch / 'ownership.json').read_text()) == marker,
                'Owned scratch identity changed; cleanup refused')
        shutil.rmtree(scratch)
        receipt['cleanup'] = {'scratch': str(scratch), 'identity': list(identity), 'marker': marker,
                              'removed': not scratch.exists(), 'global_process_inventory': False,
                              'main_index_or_git_refs_written': False}
        receipt['elapsed_seconds'] = round(time.monotonic() - began, 6)
        receipt['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(output / 'receipt.json', receipt)
    print(json.dumps({key: receipt.get(key) for key in ('status', 'canonical', 'selected', 'elapsed_seconds', 'error', 'cleanup')}))
    return 0 if receipt['status'].startswith('passed-') else 1


if __name__ == '__main__':
    sys.exit(main())
