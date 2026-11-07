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
REMOVED_ENV = ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER',
               'RUSTC_WORKSPACE_WRAPPER', 'RUSTC', 'RUSTDOCFLAGS', 'RUST_TEST_THREADS',
               'RUST_TEST_NOCAPTURE', 'RUST_TEST_TIME_UNIT', 'RUST_TEST_TIME_INTEGRATION',
               'RUST_TEST_TIME_DOCTEST', 'RUST_TEST_SHUFFLE', 'RUST_TEST_SHUFFLE_SEED',
               'RUST_TEST_FORCE_RUN_IN_PROCESS', 'RUST_TEST_RUN_IGNORED')
FLAGS = {'storedPrefixValidated': False, 'fullReplayAccepted': False,
         'semanticMetricsValid': False, 'GA_qualified': False,
         'model_imported_or_evaluated': False}
API_TARGETS = {
    'private-field': ('E0616', 'envelope_debit'),
    'no-clone': ('E0277', 'Clone', 'FixtureEnvelopeObservationV1'),
    'no-copy': ('E0277', 'Copy', 'FixtureEnvelopeOutcomeV1'),
    'no-record-constructor': ('E0432', 'FixtureDecodedRecordV1'),
    'no-word-or-boolean-entry': ('E0061', '4', '2'),
    'no-private-reply': ('E0432', 'FixtureEnvelopeReplyV1'),
    'no-observation-constructor': ('E0451', 'FixtureEnvelopeObservationV1', 'private'),
    'no-raw-serializer': ('E0599', 'to_bytes', 'FixtureEnvelopeObservationV1'),
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
        budget = min(timeout, self.deadline - time.monotonic())
        require(budget > 0, 'Overall active deadline exhausted')
        argv = list(map(str, argv))
        overrides = {'RUSTUP_AUTO_INSTALL': '0', 'LC_ALL': 'C', **(env or {})}
        # Only a small documented environment reaches children. No dynamic-library,
        # compiler, test or Python injection from the caller is inherited.
        command_env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT') if k in os.environ}
        command_env.update(overrides)
        row = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': command_env,
               'environment_policy': 'allowlist', 'caller_injection_variables_removed': list(REMOVED_ENV),
               'started_utc': now(), 'timeout_seconds': budget, 'exit': None,
               'timed_out': False, 'child_returned': False, 'owned_group_gone': False}
        self.receipt['commands'].append(row)
        self.save()
        start = time.monotonic()
        stdout, stderr = [self.out / 'commands' / (name + x) for x in ('.stdout', '.stderr')]
        proc = None
        try:
            with stdout.open('xb') as output, stderr.open('xb') as error:
                proc = subprocess.Popen(argv, cwd=cwd, env=command_env, stdout=output, stderr=error,
                                        start_new_session=True)
                self.active = proc
                row['pid'] = row['owned_pgid'] = proc.pid
                try:
                    proc.wait(timeout=budget)
                except subprocess.TimeoutExpired:
                    row['timed_out'] = True
                    self.stop_group(proc, row)
                row['exit'] = proc.returncode
                row['child_returned'] = True
                if not row['owned_group_gone']:
                    try:
                        os.killpg(proc.pid, 0)
                    except ProcessLookupError:
                        row['owned_group_gone'] = True
                    else:
                        row['descendants_outlived_direct_child'] = True
                        self.stop_group(proc, row)
        except OSError as error:
            row['spawn_error'] = str(error)
        finally:
            if proc is not None and (not row['child_returned'] or not row['owned_group_gone']):
                self.stop_group(proc, row)
                row['exit'] = proc.returncode
            self.active = None
            row['finished_utc'] = now()
            row['elapsed_seconds'] = round(time.monotonic() - start, 6)
            for label, path in [('stdout', stdout), ('stderr', stderr)]:
                if path.exists():
                    row[label] = {'path': str(path.relative_to(self.out)), 'bytes': path.stat().st_size,
                                  'sha256': sha(path)}
            write_json(self.out / 'commands' / (name + '.json'), row)
            self.save()
        require(row['child_returned'] and row['owned_group_gone'] and not row['timed_out']
                and not row.get('descendants_outlived_direct_child')
                and ((row['exit'] == 1) if negative else row['exit'] == 0),
                'Command failed: ' + name + '; retained command receipt')
        return stdout.read_text(), stderr.read_text(), row


def rustc_identity(output):
    lines = output.splitlines()
    header = lines[0].split() if lines else []
    fields = dict(line.split(': ', 1) for line in lines[1:] if ': ' in line)
    release = fields.get('release', '')
    require(len(header) >= 2 and header[0] == 'rustc' and header[1] == release
            and fields.get('binary') == 'rustc' and bool(fields.get('host'))
            and re.fullmatch(r'\d+\.\d+\.\d+(?:-[\w.]+)?', release) is not None,
            'Incomplete/non-rustc compiler identity')
    return {'release': release, 'host': fields['host'], 'commit_hash': fields.get('commit-hash')}


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


def test_compile_argv(compiler, lane, binary):
    sources = {'producer': 'source/producer/independent_tests.rs',
               'independent': 'source/independent/source/analyzer.rs'}
    require(lane in sources, 'Unknown fixed test compile lane')
    allowance = ['-A', 'non_snake_case'] if lane == 'independent' else []
    return [compiler, '--edition=2024', '-Dwarnings', *allowance, '--test', sources[lane], '-o', binary]


def verify_methods(output, expected, executed=False):
    if executed:
        # --nocapture interleaves test labels and their output. Match the label,
        # then require its final ok and the sole complete libtest summary.
        names = re.findall(r'^test (\S+) \.\.\. ', output, re.M)
        summaries = re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out; finished in [^\n]+$', output, re.M)
        require(summaries == [(str(len(expected)), '0', '0', '0', '0')], 'Partial/ignored/failed test result')
        require(len(re.findall(r'(?:^|\n)ok$| \.\.\. ok$', output, re.M)) == len(expected),
                'Executed methods missing terminal ok')
    else:
        names = [line[:-6] for line in output.splitlines() if line.endswith(': test')]
        require(re.search(r'^' + str(len(expected)) + r' tests, 0 benchmarks$', output, re.M),
                'Listing total differs')
    require(len(names) == len(set(names)) == len(expected) and set(names) == set(expected),
            'Exact method inventory differs')
    return sorted(names)


def verify_layouts(output, expected):
    matches = re.findall(r'CORRECTED_ACTUAL_COMPLETE_LAYOUTS=(\[[^\n]+\])', output)
    require(len(matches) == 1, 'Missing/duplicate complete layout observation')
    values = json.loads(matches[0])
    require(len(values) == expected['count'] == 32
            and values == [r['bytes'] for r in expected['layouts']], 'Host layouts differ')
    return [{'type': r['type'], 'bytes': value} for r, value in zip(expected['layouts'], values)]


def verify_negative(name, stderr, source, executable, row):
    require(row['exit'] == 1 and not row['timed_out']
            and row['child_returned'] and row['owned_group_gone'] and not executable.exists(),
            'Negative API abnormal failure or executable')
    diagnostics = [json.loads(line) for line in stderr.splitlines() if line.strip()]
    errors = [d for d in diagnostics if d.get('level') == 'error' and d.get('code')]
    code, *targets = API_TARGETS[name]
    require(errors and all(d['code']['code'] == code for d in errors), 'Unexpected/missing API diagnostic code')
    text = source.read_text()
    matches = []
    for d in errors:
        if not all(target in d['message'] for target in targets):
            continue
        for span in d.get('spans', []):
            if span.get('is_primary') and (source.parents[1] / span['file_name']).resolve() == source.resolve():
                start, end = span.get('byte_start', -1), span.get('byte_end', -1)
                require(0 <= start < end <= len(text.encode()), 'Invalid API source span')
                matches.append({'code': code, 'message': d['message'], 'primary_span': span})
    require(matches, 'Intended primary API diagnostic/span absent')
    require(not any(d.get('level') == 'error' and not d.get('code') and
                    not d.get('message', '').startswith('aborting due to ') for d in diagnostics),
            'Unexpected unclassified compiler error')
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
        require(receipt['rustc']['identity']['host'] == expected_layouts['host']
                and receipt['rustc']['identity']['release'] == expected_layouts['rust'],
                'Compiler host/release not selected for these layouts')
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
            output = commands.run(lane + '-execute', [binary, '--test-threads=1', '--nocapture'],
                                  cwd=pack_snapshot, env=env, timeout=120)[0]
            executed = verify_methods(output, names, executed=True)
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
