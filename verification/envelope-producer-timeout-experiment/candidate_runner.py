#!/usr/bin/env python3
"""Closed fixture-envelope host check. No semantic replay or release authority."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
PACK = 'verification/swift-envelope-ci-pack'
MANIFEST_SHA256 = '4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a'
PACK_TREE_SHA256 = '7a73ac6f477b6ac90db0be8444712bc195c184fb21239266c07601f9ea90ecee'
PARENT_SHA256 = '1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b'
ENVELOPE_SHA256 = '2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef'
BASE_RUNNER_SHA256 = '4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c'
OUTPUT_CAP = 8 * 1024 * 1024
TOTAL_OUTPUT_CAP = 64 * 1024 * 1024
REMOVED_ENV = ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER',
               'RUSTC_WORKSPACE_WRAPPER', 'RUSTC', 'RUSTDOCFLAGS', 'RUST_TEST_THREADS',
               'RUST_TEST_NOCAPTURE', 'RUST_TEST_TIME_UNIT', 'RUST_TEST_TIME_INTEGRATION',
               'RUST_TEST_TIME_DOCTEST', 'RUST_TEST_SHUFFLE', 'RUST_TEST_SHUFFLE_SEED',
               'RUST_TEST_FORCE_RUN_IN_PROCESS', 'RUST_TEST_RUN_IGNORED')
FLAGS = {'storedPrefixValidated': False, 'fullReplayAccepted': False,
         'semanticMetricsValid': False, 'GA_qualified': False,
         'model_imported_or_evaluated': False}
API_TARGETS = {
    'private-field': ('E0616', 'envelope_debit', 'FixtureEnvelopeObservationV1', 'private'),
    'no-clone': ('E0277', 'trait bound', 'Clone', 'FixtureEnvelopeObservationV1', 'not satisfied'),
    'no-copy': ('E0277', 'trait bound', 'Copy', 'FixtureEnvelopeOutcomeV1', 'not satisfied'),
    'no-record-constructor': ('E0432', 'unresolved import', 'FixtureDecodedRecordV1'),
    'no-word-or-boolean-entry': ('E0061', 'takes 4 arguments', '2 arguments were supplied'),
    'no-private-reply': ('E0432', 'unresolved import', 'FixtureEnvelopeReplyV1'),
    'no-observation-constructor': ('E0451', 'FixtureEnvelopeObservationV1', 'private'),
    'no-raw-serializer': ('E0599', 'no method named', 'to_bytes', 'FixtureEnvelopeObservationV1'),
}

# Fixed root-selected probe bytes and all 23 primary targets. No caller map or
# extra runtime file is consulted. Root selection SHA-256:
# 24c4d9f7bea9e863a4af917c9ea422005448b39521d14672b3e56349c32a9852
API_SOURCE_TARGETS = {
    'private-field': (98,
        'd0610d700df8cf7dc49679a56721fc1b581c0504907fcef4d9c9514a55c1745f', (
            (69, 83, 'envelope_debit'),
        )),
    'no-clone': (91,
        '0ee91e136e24f7a9a6dd53feac2d4045e77fbc43450380d2bb1c904488b5ad2d', (
            (58, 86, 'FixtureEnvelopeObservationV1'),
        )),
    'no-copy': (86,
        '07c2c35c0a9af7cfffdd897adaf83ec5c524cee7a4dda9631301797890b02edd', (
            (57, 81, 'FixtureEnvelopeOutcomeV1'),
        )),
    'no-record-constructor': (53,
        'c440006bd93877eb930d3a9a506032347e03efaa6044f20ca1cf2f3dbb7fc59c', (
            (4, 41, 'mixer_absence::FixtureDecodedRecordV1'),
        )),
    'no-word-or-boolean-entry': (107,
        '8e67965b8ddbcbd057445c1de64fd081f953870cd06068a3c5b432576baa54c3', (
            (61, 88, 'analyze_fixture_envelope_v1'),
        )),
    'no-private-reply': (53,
        'ab59c1d359d486f34f5fe0b63a9cb7ccb1db0d71e8171eb609653b8b86b19f2c', (
            (4, 41, 'mixer_absence::FixtureEnvelopeReplyV1'),
        )),
    'no-observation-constructor': (398,
        '219dacc044c3d2869155c3def43b53d505871ae90c574fdb21e11f0582ea4934', (
            (66, 74, 'boundary'),
            (114, 120, 'reason'),
            (166, 182, 'observed_records'),
            (185, 190, 'state'),
            (193, 198, 'phase'),
            (201, 205, 'mask'),
            (208, 222, 'last_operation'),
            (225, 241, 'active_operation'),
            (244, 262, 'requested_function'),
            (265, 276, 'pin_failure'),
            (279, 295, 'terminal_failure'),
            (298, 307, 'last_work'),
            (310, 327, 'last_instructions'),
            (330, 344, 'envelope_debit'),
            (347, 367, 'full_replay_accepted'),
            (370, 393, 'stored_prefix_validated'),
        )),
    'no-raw-serializer': (94,
        '9f63c653f6ce93d50cde6d23e8355426a61ea0027ade28c28b0e1724db8fc677', (
            (71, 79, 'to_bytes'),
        )),
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    os.replace(temporary, path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def tree_digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def member_path(value):
    require(isinstance(value, str), 'Member path must be text')
    p = PurePosixPath(value)
    require(value and value == str(p) and value != '.' and not p.is_absolute()
            and not any(x in p.parts for x in ('..', '.git')) and '\\' not in value
            and '\x00' not in value, 'Noncanonical member path: ' + repr(value))
    return Path(value)


def no_symlinks(path):
    require(path.is_absolute(), 'Absolute path required')
    for p in [*reversed(path.parents), path]:
        require(not p.is_symlink(), 'Symlink forbidden: ' + str(p))


def regular(path):
    no_symlinks(path)
    require(stat.S_ISREG(path.stat().st_mode), 'Nonregular file: ' + str(path))
    return path


def inventory(base):
    no_symlinks(base)
    require(stat.S_ISDIR(base.stat().st_mode), 'Not a directory: ' + str(base))
    rows = []
    for directory, dirs, files in os.walk(base, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(directory) / name
            member_path(p.relative_to(base).as_posix())
            mode = p.lstat().st_mode
            require(not stat.S_ISLNK(mode), 'Symlink member: ' + str(p))
            require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'Special member: ' + str(p))
            if stat.S_ISREG(mode):
                rows.append({'path': p.relative_to(base).as_posix(), 'bytes': p.stat().st_size,
                             'sha256': sha(p)})
    return sorted(rows, key=lambda r: r['path'])


def verify_pack(base):
    manifest_file = regular(base / 'manifest.json')
    require(sha(manifest_file) == MANIFEST_SHA256, 'Pinned manifest differs')
    m = json.loads(manifest_file.read_bytes())
    rows = m['members']
    names = [str(member_path(r['path'])) for r in rows]
    require(len(names) == len(set(names)) == m['member_count'] == 86, 'Duplicate/count pack members')
    require(sum(r['bytes'] for r in rows) == m['total_bytes'] == 8330464, 'Pack byte count differs')
    require(tree_digest(rows) == m['tree_sha256'] == PACK_TREE_SHA256, 'Pack tree digest differs')
    actual = [r for r in inventory(base) if r['path'] != 'manifest.json']
    require(actual == rows, 'Missing, unexpected or mutated pack members')
    verify_sources(base)
    return m


def verify_sources(base):
    for location in ('source/library', 'source/independent/source'):
        require(sha(regular(base / location / 'analyzer.rs')) == PARENT_SHA256, 'Parent source differs')
        require(sha(regular(base / location / 'envelope.rs')) == ENVELOPE_SHA256, 'Envelope source differs')
    require(sha(regular(base / 'source/producer/inputs/envelope.rs')) == ENVELOPE_SHA256,
            'Producer envelope differs')
    layout = json.loads((base / 'inventories/proposed-layout.json').read_bytes())
    originals = json.loads((base / 'inventories/selected-input-manifest.json').read_bytes())['inputs']
    by_original = {r['path']: r for r in originals}
    for r in layout['derived_test_only_files']:
        original = by_original[r['original']['path']]['packed_destinations'][0]
        data = (base / member_path(original)).read_bytes() + r['appendix_utf8'].encode()
        require((base / member_path(r['packed_path'])).read_bytes() == data
                and len(data) == r['bytes'] and hashlib.sha256(data).hexdigest() == r['sha256'],
                'Derived overlay differs')


def fresh_output(path, root=ROOT):
    require('..' not in path.parts and '.git' not in path.parts, 'Output path traverses forbidden component')
    out = Path(os.path.abspath(path))
    no_symlinks(out)
    require(out.parent.is_dir() and not out.exists(), 'Output requires existing parent and fresh destination')
    verification = root / 'verification'
    require(not out.is_relative_to(verification) or out.is_relative_to(
        verification / 'swift-envelope-ci-implementation'), 'Output cannot mutate historical/pack evidence')
    require(not (root / PACK).is_relative_to(out), 'Output contains immutable pack')
    out.mkdir(exist_ok=False)
    marker = {'purpose': 'mixer-fixture-envelope-ci-output', 'token': uuid.uuid4().hex}
    with (out / 'output-ownership.json').open('x') as f:
        json.dump(marker, f, sort_keys=True)
    return out


def copy_pack(base, out, manifest):
    target = out / 'pack'
    target.mkdir()
    for r in [*manifest['members'], {'path': 'manifest.json', 'bytes': (base/'manifest.json').stat().st_size,
                                    'sha256': MANIFEST_SHA256}]:
        source, dest = base / member_path(r['path']), target / member_path(r['path'])
        regular(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as f, dest.open('xb') as g:
            shutil.copyfileobj(f, g, 65536)
        require(dest.stat().st_size == r['bytes'] and sha(dest) == r['sha256'], 'Snapshot differs')
        dest.chmod(0o444)
    verify_pack(target)
    return target


class Commands:
    def __init__(self, out, receipt, deadline):
        self.out, self.receipt, self.deadline = out, receipt, deadline
        self.active = None
        self.output_bytes = 0
        (out / 'commands').mkdir()

    def save(self):
        write_json(self.out / 'receipt.json', self.receipt)

    def stop_group(self, proc, row):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            row['owned_group_killed'] = True
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
        row['child_returned'] = True
        until = time.monotonic() + 5
        while True:
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                row['owned_group_gone'] = True
                return
            if time.monotonic() >= until:
                row['owned_group_gone'] = False
                return
            time.sleep(.02)

    def run(self, name, argv, *, cwd, env=None, timeout=15, negative=False):
        require(self.active is None, 'Only one synchronous child group allowed')
        require(re.fullmatch(r'[A-Za-z0-9_-]+', name) is not None, 'Invalid command name')
        start = time.monotonic()
        budget = min(timeout, self.deadline - start)
        require(budget > 0, 'Overall active deadline exhausted')
        argv = list(map(str, argv))
        overrides = {'RUSTUP_AUTO_INSTALL': '0', 'LC_ALL': 'C', **(env or {})}
        command_env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT') if k in os.environ}
        command_env.update(overrides)
        row = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': command_env,
               'environment_policy': 'allowlist', 'caller_injection_variables_removed': list(REMOVED_ENV),
               'started_utc': now(), 'timeout_seconds': budget, 'exit': None,
               'timed_out': False, 'child_returned': False, 'owned_group_gone': False,
               'per_stream_cap_bytes': OUTPUT_CAP, 'aggregate_cap_bytes': TOTAL_OUTPUT_CAP,
               'aggregate_bytes_before': self.output_bytes, 'output_capped': False,
               'pipe_eof': {'stdout': False, 'stderr': False}, 'errors': []}
        self.receipt['commands'].append(row)
        self.save()
        paths = {label: self.out / 'commands' / (name + '.' + label) for label in ('stdout', 'stderr')}
        proc, selector, primary = None, selectors.DefaultSelector(), None
        opened, cleanup_errors = [], []
        def cleanup_error(phase, error):
            cleanup_errors.append(error)
            row['errors'].append({'phase': phase, 'type': type(error).__name__, 'message': str(error)})
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=command_env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, start_new_session=True)
            self.active = proc
            row['pid'] = row['owned_pgid'] = proc.pid
            for label, pipe in [('stdout', proc.stdout), ('stderr', proc.stderr)]:
                opened.append(pipe)
                sink = paths[label].open('xb'); opened.append(sink)
                selector.register(pipe, selectors.EVENT_READ, {'label': label, 'sink': sink, 'count': 0})
            while selector.get_map() or proc.poll() is None:
                if time.monotonic() - start >= budget:
                    row['timed_out'] = True
                    raise TimeoutError('Command timeout: ' + name)
                for key, _ in selector.select(.02):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        row['pipe_eof'][key.data['label']] = True
                        selector.unregister(key.fileobj)
                        continue
                    available = min(OUTPUT_CAP - key.data['count'], TOTAL_OUTPUT_CAP - self.output_bytes)
                    kept = block[:available]
                    key.data['sink'].write(kept)
                    key.data['count'] += len(kept); self.output_bytes += len(kept)
                    if len(block) > available:
                        row['output_capped'] = True
                        raise RuntimeError('Command output cap: ' + name)
            proc.wait(timeout=5)
            row['exit'] = proc.returncode; row['child_returned'] = True
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                row['owned_group_gone'] = True
            else:
                row['descendants_outlived_direct_child'] = True
        except BaseException as error:
            primary = error
            row['errors'].append({'phase': 'active', 'type': type(error).__name__, 'message': str(error)})
            if isinstance(error, OSError) and proc is None:
                row['spawn_error'] = str(error)
        finally:
            if proc is not None and (not row['child_returned'] or not row['owned_group_gone']):
                try:
                    self.stop_group(proc, row)
                    row['exit'] = proc.returncode
                except BaseException as error:
                    row['owned_group_gone'] = False
                    cleanup_error('stop-owned-group', error)
            if proc is None or (row['child_returned'] and row['owned_group_gone']):
                self.active = None
            row['custody_hold'] = self.active is not None
            for stream in opened:
                try:
                    stream.close()
                except BaseException as error:
                    cleanup_error('close-stream', error)
            try:
                selector.close()
            except BaseException as error:
                cleanup_error('close-selector', error)
            row['finished_utc'] = now()
            row['elapsed_seconds'] = round(time.monotonic() - start, 6)
            row['aggregate_bytes_after'] = self.output_bytes
            for label, path in paths.items():
                try:
                    if not path.exists():
                        path.write_bytes(b'')
                    row[label] = {'path': str(path.relative_to(self.out)), 'bytes': path.stat().st_size,
                                  'sha256': sha(path)}
                except BaseException as error:
                    cleanup_error('retain-' + label, error)
            try:
                write_json(self.out / 'commands' / (name + '.json'), row)
            except BaseException as error:
                cleanup_error('save-command', error)
            try:
                self.save()
            except BaseException as error:
                cleanup_error('save-receipt', error)
        if primary is not None:
            raise primary
        if cleanup_errors:
            raise cleanup_errors[0]
        require(row['child_returned'] and row['owned_group_gone'] and not row['timed_out']
                and not row['output_capped'] and all(row['pipe_eof'].values())
                and not row.get('descendants_outlived_direct_child')
                and ((row['exit'] == 1) if negative else row['exit'] == 0),
                'Command failed: ' + name + '; retained command receipt')
        return paths['stdout'].read_text(), paths['stderr'].read_text(), row


def rustc_identity(output):
    lines = output.splitlines()
    header = re.fullmatch(r'rustc ([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?) '
                          r'\(([0-9a-f]{7,40}) ([0-9]{4}-[0-9]{2}-[0-9]{2})\)',
                          lines[0] if lines else '')
    require(header is not None, 'Incomplete/non-rustc compiler identity header')
    required = {'binary', 'release', 'host', 'commit-hash', 'commit-date', 'LLVM version'}
    fields = {}
    for line in lines[1:]:
        key, separator, value = line.partition(': ')
        require(separator and key in required and key not in fields and value
                and value == value.strip(), 'Malformed/duplicate compiler identity field')
        fields[key] = value
    require(set(fields) == required, 'Incomplete compiler identity fields')
    require(fields['binary'] == 'rustc'
            and re.fullmatch(r'[0-9a-f]{40}', fields['commit-hash']) is not None
            and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)+', fields['host']) is not None
            and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', fields['LLVM version']) is not None,
            'Malformed compiler identity value')
    # strptime alone accepts non-padded dates; the official syntax and an actual
    # Gregorian date are both required before any host/release tuple selection.
    require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', fields['commit-date']) is not None,
            'Malformed compiler commit date')
    datetime.strptime(fields['commit-date'], '%Y-%m-%d')
    release, commit, date = header.groups()
    require(fields['release'] == release and fields['commit-hash'].startswith(commit)
            and fields['commit-date'] == date, 'Incoherent compiler identity header/fields')
    return {'binary': fields['binary'], 'release': release, 'host': fields['host'],
            'commit_hash': fields['commit-hash'], 'commit_date': date,
            'llvm_version': fields['LLVM version']}


def select_compiler(requested, commands, root, out):
    found = shutil.which(str(requested))
    require(found is not None, 'rustc launcher missing')
    launcher = Path(os.path.abspath(found))
    # Preserve original launcher spelling: rustup dispatches through argv[0].
    resolved = launcher.resolve(strict=True)
    require(resolved.is_file(), 'Launcher target is not a file')
    selected = commands.run('compiler-sysroot-selection', [launcher, '--print', 'sysroot'], cwd=root)[0].strip()
    require('\n' not in selected and Path(selected).is_absolute(), 'Invalid rustc sysroot')
    compiler = (Path(selected) / 'bin/rustc').resolve(strict=True)
    regular(compiler)
    version = commands.run('rustc-verbose', [compiler, '--version', '--verbose'], cwd=out)[0]
    return compiler, {'requested': str(requested), 'launcher': str(launcher), 'launcher_target': str(resolved),
                      'launcher_sha256': sha(resolved), 'path': str(compiler), 'sha256': sha(compiler),
                      'sysroot': selected, 'version_verbose': version, 'identity': rustc_identity(version)}


def select_host_target(identity, historical_layouts):
    # The inventory's Rust version remains historical evidence. This fixed
    # runner policy selects two possible targets; each needs all fresh checks.
    allowed = {('aarch64-apple-darwin', '1.99.0'), ('aarch64-apple-darwin', '1.98.1')}
    require(isinstance(identity, dict), 'Malformed compiler identity')
    target = (identity.get('host'), identity.get('release'))
    require(all(isinstance(value, str) for value in target) and target in allowed,
            'Compiler host/release not selected')
    return {'actual_host': target[0], 'actual_release': target[1],
            'historical_layout_inventory_host': historical_layouts['host'],
            'historical_layout_inventory_release': historical_layouts['rust'],
            'selection_reference': 'verification/swift-envelope-ci-root-review/compiler-qualification-selection-amendment.json',
            'selection_sha256': 'b7c482646943a34ffae810cfad38962a4b50a455b37d2deab7ea80e38d805e5b',
            'scope': 'selected prospective target; success requires this invocation full fresh checks',
            'other_target_qualification_inferred': False}


def test_compile_argv(compiler, lane, binary):
    sources = {'producer': 'source/producer/independent_tests.rs',
               'independent': 'source/independent/source/analyzer.rs'}
    require(lane in sources, 'Unknown fixed test compile lane')
    allowance = ['-A', 'non_snake_case'] if lane == 'independent' else []
    return [compiler, '--edition=2024', '-Dwarnings', *allowance, '--test', sources[lane], '-o', binary]


def verify_methods(output, expected, executed=False, filtered=0):
    if executed:
        # --nocapture interleaves test labels and their output. Match the label,
        # then require its final ok and the sole complete libtest summary.
        names = re.findall(r'^test (\S+) \.\.\. ', output, re.M)
        summaries = re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out; finished in [^\n]+$', output, re.M)
        require(summaries == [(str(len(expected)), '0', '0', '0', str(filtered))], 'Partial/ignored/failed test result')
        require(len(re.findall(r'(?:^|\n)ok$| \.\.\. ok$', output, re.M)) == len(expected),
                'Executed methods missing terminal ok')
        require(names == expected, 'Executed method order differs')
    else:
        names = [line[:-6] for line in output.splitlines() if line.endswith(': test')]
        require(re.search(r'^' + str(len(expected)) + r' tests, 0 benchmarks$', output, re.M),
                'Listing total differs')
    require(len(names) == len(set(names)) == len(expected) and set(names) == set(expected),
            'Exact method inventory differs')
    return sorted(names)


def producer_groups(names):
    """Fixed shape, original lexical order, exact root filters and one embedded prefix."""
    require(names == sorted(set(names)) and len(names) == 78, 'Producer inventory shape differs')
    roots = [name for name in names if '::' not in name]
    embedded = [name for name in names if name.startswith('product::')]
    require(len(roots) == 17 and len(embedded) == 61, 'Producer partition counts differ')
    groups = []
    for name in names:
        if name in roots:
            groups.append({'name': 'root-' + str(roots.index(name)).zfill(2),
                           'args': [name, '--exact'], 'methods': [name]})
        elif name == embedded[0]:
            groups.append({'name': 'embedded', 'args': ['product::'], 'methods': embedded})
    require([name for group in groups for name in group['methods']] == names,
            'Producer partition omission, duplicate or order change')
    return groups


def execute_test_groups(commands, lane, binary, pack_snapshot, scratch, env, names):
    if lane == 'independent':
        output = commands.run(lane + '-execute', [binary, '--test-threads=1', '--nocapture'],
                              cwd=pack_snapshot, env=env, timeout=120)[0]
        return output, verify_methods(output, names, executed=True)
    require(lane == 'producer', 'Unknown test lane')
    groups = producer_groups(names)
    state = {'schema': 1, 'plan': groups, 'expected_methods': names, 'completed_groups': [],
             'complete_disjoint_coverage': False, 'original_method_order_preserved': True,
             'binary_sha256': sha(binary), 'source_pack_tree': PACK_TREE_SHA256,
             'per_command_seconds': 120, 'aggregate_active_seconds': 480,
             'per_stream_cap_bytes': OUTPUT_CAP, 'all_command_streams_cap_bytes': TOTAL_OUTPUT_CAP}
    commands.receipt['producer_partition'] = state; commands.save()
    parent = scratch / 'producer-partitions'; parent.mkdir()
    observed, chunks = [], []
    for group in groups:
        work = parent / group['name']; work.mkdir()
        for child in ('framing', 'envelope', 'review', 'tmp'):
            (work / child).mkdir()
        group_env = {**env, 'MIXER_ANALYZER_LIBRARY_TEST_SCRATCH': str(work / 'framing'),
                     'MIXER_ENVELOPE_SCRATCH': str(work / 'envelope'),
                     'MIXER_REVIEW_SCRATCH': str(work / 'review'),
                     'TMPDIR': str(work / 'tmp'), 'TMP': str(work / 'tmp'), 'TEMP': str(work / 'tmp')}
        # A command or verification failure escapes immediately. No later group is attempted.
        output, _, row = commands.run('producer-' + group['name'],
            [binary, *group['args'], '--test-threads=1', '--nocapture'],
            cwd=pack_snapshot, env=group_env, timeout=120)
        actual = verify_methods(output, group['methods'], executed=True,
                                filtered=len(names) - len(group['methods']))
        observed.extend(actual); chunks.append(output)
        state['completed_groups'].append({'name': group['name'], 'methods': actual,
                                          'command': row['name'], 'stdout': row['stdout']})
        commands.save()
    require(observed == names and len(observed) == len(set(observed)), 'Producer execution closure differs')
    state['complete_disjoint_coverage'] = True; commands.save()
    return '\n'.join(chunks), observed


def verify_layouts(output, expected):
    matches = re.findall(r'CORRECTED_ACTUAL_COMPLETE_LAYOUTS=(\[[^\n]+\])', output)
    require(len(matches) == 1, 'Missing/duplicate complete layout observation')
    values = json.loads(matches[0])
    require(len(values) == expected['count'] == 32
            and values == [r['bytes'] for r in expected['layouts']], 'Host layouts differ')
    return [{'type': r['type'], 'bytes': value} for r, value in zip(expected['layouts'], values)]


def diagnostic_json(line):
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate diagnostic JSON key: ' + key)
            value[key] = item
        return value
    def invalid_constant(value):
        raise RuntimeError('Non-finite diagnostic JSON constant: ' + value)
    value = json.loads(line, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    require(isinstance(value, dict), 'Diagnostic JSON must be an object')
    return value


def verify_negative(name, stderr, source, executable, row):
    require(row['exit'] == 1 and not row['timed_out']
            and row['child_returned'] and row['owned_group_gone']
            and not row.get('descendants_outlived_direct_child') and not executable.exists(),
            'Negative API abnormal failure or executable')
    require(name in API_TARGETS, 'Unknown fixed API probe')
    source_path = 'api/' + name + '.rs'
    require(source.name == name + '.rs' and source.parent.name == 'api', 'Wrong API probe source path')
    data = regular(source).read_bytes()
    size, digest, selected = API_SOURCE_TARGETS[name]
    require(len(data) == size and hashlib.sha256(data).hexdigest() == digest, 'API probe source bytes differ')
    expected_spans = {(start, end) for start, end, _ in selected}
    for start, end, text in selected:
        require(data[start:end] == text.encode('utf-8'), 'Fixed API target text differs')
    diagnostics = [diagnostic_json(line) for line in stderr.splitlines() if line.strip()]
    code, *targets = API_TARGETS[name]
    matches, seen = [], set()
    # rustc children normally contain notes/help. An error hidden in that tree
    # has the same obligations as a top-level error and cannot be ignored.
    pending = list(reversed(diagnostics))
    while pending:
        diagnostic = pending.pop()
        require(isinstance(diagnostic, dict), 'Malformed diagnostic child')
        children = diagnostic.get('children', [])
        require(isinstance(children, list), 'Malformed diagnostic children')
        pending.extend(reversed(children))
        require(isinstance(diagnostic.get('level'), str) and isinstance(diagnostic.get('message'), str),
                'Malformed diagnostic level/message')
        if diagnostic['level'] != 'error':
            continue
        actual_code = diagnostic.get('code')
        if actual_code is None:
            require(diagnostic['message'].startswith('aborting due to '), 'Unexpected unclassified compiler error')
            continue
        require(isinstance(actual_code, dict) and actual_code.get('code') == code,
                'Unexpected API diagnostic code')
        require(all(target in diagnostic['message'] for target in targets), 'Unrelated API diagnostic message')
        spans = diagnostic.get('spans')
        require(isinstance(spans, list), 'Malformed API diagnostic spans')
        primary = []
        for span in spans:
            require(isinstance(span, dict) and type(span.get('is_primary')) is bool
                    and isinstance(span.get('file_name'), str)
                    and type(span.get('byte_start')) is int and type(span.get('byte_end')) is int,
                    'Malformed API source span')
            start, end = span['byte_start'], span['byte_end']
            require(0 <= start <= end and (span['file_name'] != source_path or end <= len(data)),
                    'Invalid API source span')
            if span['is_primary']:
                require(span['file_name'] == source_path and (start, end) in expected_spans
                        and (start, end) not in seen, 'Wrong/duplicate primary API target span')
                seen.add((start, end))
                primary.append(span)
        require(primary, 'Intended primary API diagnostic/span absent')
        matches.extend({'code': code, 'message': diagnostic['message'], 'primary_span': span} for span in primary)
    require(matches and seen == expected_spans, 'Missing complete intended API target spans')
    return matches


def scratch_identity(path):
    no_symlinks(path)
    s = path.stat()
    require(stat.S_ISDIR(s.st_mode) and s.st_uid == os.geteuid(), 'Scratch ownership differs')
    return [s.st_dev, s.st_ino, s.st_uid]


def preserve_and_cleanup(out, scratch, identity, marker, products, commands):
    require(commands.active is None and all(r.get('owned_group_gone') for r in commands.receipt['commands']
            if 'pid' in r), 'Owned children/groups have not returned')
    require(scratch_identity(scratch) == identity, 'Scratch identity changed; preserved')
    marker_file = regular(scratch / 'ownership.json')
    require(json.loads(marker_file.read_bytes()) == marker, 'Scratch marker changed; preserved')
    before = inventory(scratch)
    retained = out / 'retained'
    retained.mkdir()
    records, product_records = {}, {}
    for r in before:
        relative = r['path']
        if relative == 'ownership.json':
            continue
        if relative in products:
            product_records[relative] = r
            continue
        source = scratch / member_path(relative)
        target = retained / member_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        compressed = r['bytes'] > 16 * 1024 * 1024
        if compressed:
            target = target.with_name(target.name + '.gz')
            with source.open('rb') as stream, target.open('xb') as raw:
                with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as sink:
                    shutil.copyfileobj(stream, sink, 65536)
            h, n = hashlib.sha256(), 0
            with gzip.open(target, 'rb') as f:
                for block in iter(lambda: f.read(65536), b''):
                    h.update(block); n += len(block)
            require(n == r['bytes'] and h.hexdigest() == r['sha256'], 'Sparse retention differs')
        else:
            with source.open('rb') as f, target.open('xb') as g:
                shutil.copyfileobj(f, g, 65536)
            require(sha(target) == r['sha256'], 'Retention differs')
        records[relative] = {'path': str(target.relative_to(out)), 'encoding': 'gzip' if compressed else 'identity',
                             'bytes': target.stat().st_size, 'sha256': sha(target),
                             'original_bytes': r['bytes'], 'original_sha256': r['sha256']}
    # Save a durable retention manifest before removal. Interruptions before this
    # point leave source scratch untouched; interruptions later have retained bytes.
    write_json(out / 'retention.json', {'test_files': records, 'compiler_products': product_records})
    require(scratch_identity(scratch) == identity and json.loads(regular(scratch / 'ownership.json').read_bytes()) == marker
            and inventory(scratch) == before, 'Scratch changed during retention; preserved')
    shutil.rmtree(scratch)
    require(not scratch.exists(), 'Scratch removal incomplete')
    return {'removed': True, 'identity': identity, 'marker': marker, 'test_files': records,
            'compiler_products': product_records, 'children_and_owned_groups_returned': True,
            'unrelated_process_or_native_discovery': False}


def postflight_checks(root, out, runner, receipt, compiler, deadline):
    """One failed check must not suppress evidence for other owned inputs/tools."""
    checks = {}
    def check(name, action):
        try:
            require(time.monotonic() < deadline, 'Postflight retention deadline exhausted')
            checks[name] = {'passed': True, 'observed': action()}
        except BaseException as error:
            checks[name] = {'passed': False, 'type': type(error).__name__, 'message': str(error)}
            receipt['errors'].append({'phase': 'postflight-' + name,
                                      'type': type(error).__name__, 'message': str(error)})
    def pack_state(base):
        m = verify_pack(base)
        return {'manifest_sha256': sha(base/'manifest.json'), 'tree_sha256': m['tree_sha256'],
                'member_count': m['member_count']}
    check('pack', lambda: pack_state(root/PACK))
    if (out/'pack').exists():
        # Record partial/mutated copied inputs even if materialization failed
        # before it could return a complete snapshot identity.
        check('snapshot-observed', lambda: inventory(out/'pack'))
        check('snapshot', lambda: pack_state(out/'pack'))
    def same_file(path, expected):
        observed = sha(regular(path))
        require(observed == expected, 'Identity digest differs: ' + str(path))
        return {'path': str(path), 'sha256': observed}
    check('runner', lambda: same_file(runner, receipt['runner']['sha256']))
    if (out/'executed-runner.py').exists():
        check('runner-snapshot', lambda: same_file(out/'executed-runner.py', receipt['runner']['sha256']))
    def python_state():
        require(Path(receipt['python']['path']).resolve(strict=True) == Path(receipt['python']['resolved_path']),
                'Python launcher target changed')
        return same_file(Path(receipt['python']['resolved_path']), receipt['python']['sha256'])
    check('python', python_state)
    if compiler is not None:
        check('compiler', lambda: same_file(compiler, receipt['rustc']['sha256']))
        def launcher_state():
            require(Path(receipt['rustc']['launcher']).resolve(strict=True) == Path(receipt['rustc']['launcher_target']),
                    'Compiler launcher target changed')
            return same_file(Path(receipt['rustc']['launcher_target']), receipt['rustc']['launcher_sha256'])
        check('launcher', launcher_state)
    return checks


def execute(out, rustc, root=ROOT):
    started = time.monotonic()
    runner = Path(__file__).resolve()
    receipt = {'schema': 1, 'started_utc': now(), 'invocation': sys.argv, **FLAGS,
               'runner': {'path': str(runner), 'sha256': sha(runner)}, 'python': {
                   'path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
                   'sha256': sha(Path(sys.executable).resolve()), 'version': sys.version},
               'os': platform.platform(), 'machine': platform.machine(), 'commands': [], 'errors': [],
               'output_ownership': {'identity': scratch_identity(out),
                                    'marker': json.loads((out/'output-ownership.json').read_bytes())},
               'active_deadline_seconds': 480, 'retention_cleanup_allowance_seconds': 60,
               'candidate_base_runner_sha256': BASE_RUNNER_SHA256,
               'output_limits': {'per_stream_bytes': OUTPUT_CAP, 'all_commands_bytes': TOTAL_OUTPUT_CAP},
               'baseline_timeout': {'run_id': 40801222690, 'artifact_id': 12865728709,
                   'artifact_sha256': 'c215170b4608a7876afdd817134247c72c09badabf452497aa1e04ce474d0b9e',
                   'preserved': True, 'retry_or_performance_equivalence_claim': False},
               'fixed_independent_test_lint_selection': {
                   'reference': 'verification/swift-envelope-ci-root-review/test-lint-selection-amendment.json',
                   'sha256': '1684fb9a329809c8c5bb9a4af20bbceaa7e4d68123a77e54a1115e3534277e52',
                   'flags': ['-Dwarnings', '-A', 'non_snake_case'],
                   'scope': 'independent --test crate only; exact uppercase G method name preserved'},
               'limits': ['quiescent trusted checkout; no adversarial filesystem custody proof',
                          'host fixture methods and reused frozen expected bytes only',
                          'no semantic/full replay, engine/CLI/target/device/signing/store/FieldLog/GA qualification'],
               'status': 'running'}
    commands = Commands(out, receipt, started + 480)
    scratch, identity, marker, compiler, pack_snapshot = None, None, None, None, None
    products = {'libmixer_absence.rlib', 'producer-tests', 'independent-tests', 'api-positive'}
    preflight_manifest = None
    def alarm_handler(signum, frame):
        raise TimeoutError('Active or retention overall deadline exhausted')
    def interrupt_handler(signum, frame):
        raise KeyboardInterrupt('Runner interrupted by signal ' + str(signum))
    old_handlers = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.signal(signal.SIGTERM, interrupt_handler)
    signal.signal(signal.SIGINT, interrupt_handler)
    signal.setitimer(signal.ITIMER_REAL, 480)
    try:
        commands.save()
        preflight_manifest = verify_pack(root / PACK)
        receipt['pack_preflight'] = {'manifest_sha256': MANIFEST_SHA256, 'tree_sha256': PACK_TREE_SHA256,
                                      'member_count': 86, 'bytes': 8330464}
        pack_snapshot = copy_pack(root / PACK, out, preflight_manifest)
        shutil.copyfile(runner, out / 'executed-runner.py')
        receipt['source_tree_digest'] = PACK_TREE_SHA256
        receipt['revision_before'] = commands.run('revision-before', ['git', 'rev-parse', 'HEAD'], cwd=root)[0].strip()
        receipt['git_tree_before'] = commands.run('git-tree-before', ['git', 'rev-parse', 'HEAD^{tree}'], cwd=root)[0].strip()
        commands.run('python-version', [sys.executable, '--version'], cwd=out)
        compiler, receipt['rustc'] = select_compiler(rustc, commands, root, out)
        expected_layouts = json.loads((pack_snapshot / 'inventories/expected-host-layouts.json').read_bytes())
        receipt['compiler_target_selection'] = select_host_target(receipt['rustc']['identity'], expected_layouts)
        scratch = out / 'scratch'; scratch.mkdir()
        marker = {'purpose': 'mixer-fixture-envelope-ci-scratch', 'token': uuid.uuid4().hex}
        with (scratch / 'ownership.json').open('x') as f:
            json.dump(marker, f, sort_keys=True)
        identity = scratch_identity(scratch)
        receipt['scratch_ownership'] = {'identity': identity, 'marker': marker}
        for name in ('producer-framing', 'producer-envelope', 'producer-review', 'independent-files'):
            (scratch / name).mkdir()
        base = [compiler, '--edition=2024', '-Dwarnings']
        commands.run('library-compile', [*base, '--crate-name', 'mixer_absence', '--crate-type=rlib',
                     'source/library/analyzer.rs', '-o', scratch / 'libmixer_absence.rlib'], cwd=pack_snapshot, timeout=60)
        expected = json.loads((pack_snapshot / 'inventories/expected-methods.json').read_bytes())
        receipt['test_binaries'] = {}
        for lane, source, key in [('producer', 'source/producer/independent_tests.rs', 'producer'),
                                  ('independent', 'source/independent/source/analyzer.rs', 'independent_exact_source')]:
            binary = scratch / (lane + '-tests')
            commands.run(lane + '-compile', test_compile_argv(compiler, lane, binary), cwd=pack_snapshot, timeout=60)
            names = expected[key]['names']
            listing = commands.run(lane + '-list', [binary, '--list'], cwd=pack_snapshot)[0]
            listed = verify_methods(listing, names)
            env = {'REVIEW_SCRATCH': str(scratch/'independent-files')} if lane == 'independent' else {
                'MIXER_ANALYZER_LIBRARY_HISTORICAL': str(pack_snapshot/'inputs/historical'),
                'MIXER_ANALYZER_LIBRARY_TEST_SCRATCH': str(scratch/'producer-framing'),
                'MIXER_ENVELOPE_SCRATCH': str(scratch/'producer-envelope'),
                'MIXER_REVIEW_SCRATCH': str(scratch/'producer-review')}
            output, executed = execute_test_groups(commands, lane, binary, pack_snapshot, scratch, env, names)
            receipt['test_binaries'][lane] = {'sha256': sha(binary), 'listed': listed, 'executed': executed,
                                               'source': source, 'source_pack_tree': PACK_TREE_SHA256}
            if lane == 'producer':
                receipt['host_layouts'] = verify_layouts(output, expected_layouts)
                require(len(re.findall(r'ENVELOPE_ORACLE_CASES=16170\b', output)) == 1
                        and len(re.findall(r'CORRECTED_FINITE_BUDGET_CASES=5544\b', output)) == 1,
                        'Fresh candidate comparison counters differ')
                receipt['fresh_candidate_comparisons_against_reused_oracles'] = 21714
        external = [*base, '--extern', 'mixer_absence=' + str(scratch/'libmixer_absence.rlib')]
        commands.run('api-positive', [*external, 'api/positive.rs', '-o', scratch/'api-positive'], cwd=pack_snapshot, timeout=60)
        api = json.loads((pack_snapshot / 'inventories/expected-api.json').read_bytes())
        receipt['api'] = {'positive': True, 'negative': {}}
        for probe in api['negative']:
            source = pack_snapshot / probe['path']; name = source.stem
            target = scratch / ('api-negative-' + name); products.add(target.name)
            _, stderr, row = commands.run('api-negative-' + name, [*external, '--error-format=json',
                probe['path'], '-o', target], cwd=pack_snapshot, timeout=60, negative=True)
            receipt['api']['negative'][name] = verify_negative(name, stderr, source, target, row)
        receipt['revision_after'] = commands.run('revision-after', ['git', 'rev-parse', 'HEAD'], cwd=root)[0].strip()
        receipt['git_tree_after'] = commands.run('git-tree-after', ['git', 'rev-parse', 'HEAD^{tree}'], cwd=root)[0].strip()
        receipt['active_checks_completed'] = True
    except BaseException as error:
        receipt['errors'].append({'phase': 'active', 'type': type(error).__name__, 'message': str(error)})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 60)
        retention_deadline = time.monotonic() + 60
        receipt['active_elapsed_seconds'] = round(time.monotonic() - started, 6)
        commands.save()
        receipt['postflight'] = postflight_checks(root, out, runner, receipt, compiler, retention_deadline)
        try:
            if scratch is not None:
                require(time.monotonic() < retention_deadline, 'Retention deadline expired; scratch preserved')
                receipt['cleanup'] = preserve_and_cleanup(out, scratch, identity, marker, products, commands)
            else:
                receipt['cleanup'] = {'scratch_created': False, 'removed': False}
        except BaseException as error:
            receipt['errors'].append({'phase': 'retention-cleanup', 'type': type(error).__name__, 'message': str(error)})
            receipt['cleanup'] = {'removed': False, 'recoverable_scratch': str(scratch)}
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        receipt['finished_utc'] = now()
        receipt['elapsed_seconds'] = round(time.monotonic() - started, 6)
        receipt['status'] = 'passed-host-fixture-check' if not receipt['errors'] and receipt.get('active_checks_completed') else 'failed'
        commands.save()
    print(json.dumps({'status': receipt['status'], 'receipt': str(out/'receipt.json'), 'errors': receipt['errors']}))
    return 0 if receipt['status'] == 'passed-host-fixture-check' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'analyzer-envelope-ci')
    parser.add_argument('--rustc', default='rustc', help='Original compiler launcher; no installation permitted')
    args = parser.parse_args()
    try:
        out = fresh_output(args.out)
    except (OSError, RuntimeError) as error:
        print('Output refused before mutation: ' + str(error), file=sys.stderr)
        return 1
    return execute(out, args.rustc)


if __name__ == '__main__':
    sys.exit(main())
