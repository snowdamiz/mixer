#!/usr/bin/env python3
"""Bounded independent DATA audit. Never import or execute fixture source.

Rerun from this checkout with python3 -I -B -S <this-file>.
Only this script's directory may receive writes. The original ZIP and extraction
are read, not extracted, changed, run, or used as an import path.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from datetime import datetime
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = 'verification/plan-continuation-2026-11-07/'
V2 = 'verification/cache-fixture-shared-input-candidate-v2/'
RUN = V2 + 'runs/ci-42429965271-1/'
NEW = PREFIX + 'cache-deadline-control-fix/'
OLD = 'verification/shared-fixture-clock-controls-correction/'
FIX = PREFIX + 'cache-fix/'
REV = '25ac442c5213326b3601456a5fd62898f152111f'
TREE = '1a08391fd1c317c88ccf6cbf8d9bed081ce37f38'
ZIP_SHA = '6d70b144f7abfb93009fcf0194b86240890e489cb7756138da3055b6586cde96'
COMPILER = '1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1'
RUNNER = '5b29269988838c8af4fdfd4858645b17837bddd8812a133ef4e6aaa709ba55ad'
MANIFEST = 'e8a74a521ddbc01f0fc1274a32838cab57c60d63ee7924b5b830b56686836c3d'
PACK_TREE = 'ac3263770d66a981bc20ee859fb0081bb28d5001ff550163b0a8030a355a505b'
IDENTITY = {'binary': 'rustc', 'commit-hash': '58cf8f9c35b355199727627d07ae34a4e2846d67',
            'commit-date': '2026-10-13', 'host': 'aarch64-apple-darwin',
            'release': '1.99.1', 'LLVM version': '23.1.1'}
VERBOSE = 'rustc 1.99.1 (58cf8f9c3 2026-10-13)\n' + ''.join(f'{k}: {v}\n' for k, v in IDENTITY.items())
APPEND = b'\n#[cfg(test)]\n#[path = "../selected_controls.rs"]\nmod selected_scalar_controls;\n\n#[cfg(test)]\n#[path = "../scalar_cursor_independent.rs"]\nmod scalar_cursor_independent;\n'
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 96 * 1024 * 1024
DENIALS = []


def guard(event, args):
    if (event.startswith(('subprocess.', 'socket.', 'ctypes.', 'pty.'))
            or event in {'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn',
                         'os.exec', 'os.kill', 'os.killpg', 'os.startfile'}):
        DENIALS.append(event)
        raise RuntimeError('Data-only audit forbids ' + event)
    paths = []
    if event == 'open':
        name, mode, flags = args
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            paths = [name]
    elif event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime', 'os.truncate'}:
        paths = [args[0]]
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        paths = list(args[:2])
    for name in paths:
        if not isinstance(name, (str, bytes, os.PathLike)) or not Path(os.fsdecode(name)).is_absolute():
            raise RuntimeError('Write requires absolute owned path')
        if not Path(os.fsdecode(name)).resolve().is_relative_to(HERE):
            raise RuntimeError('Write outside owned namespace forbidden')


sys.addaudithook(guard)


def require(value, message):
    if not value:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(data):
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + x)))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def member(name):
    p = PurePosixPath(name)
    require(name == str(p) and name not in {'', '.'} and not p.is_absolute()
            and not any(c in {'..', '.git'} for c in p.parts) and '\\' not in name and '\x00' not in name,
            'Noncanonical member ' + name)
    return name


def data(path):
    require(path.is_file() and not path.is_symlink(), 'Missing/nonregular input: ' + str(path))
    require(stat.S_ISREG(path.stat().st_mode) and path.stat().st_size <= MAX_FILE, 'Input bound: ' + str(path))
    return path.read_bytes()


def rows(base):
    result = []
    for p in sorted(base.rglob('*')):
        require(not p.is_symlink(), 'Symlink in data tree')
        if p.is_dir():
            continue
        raw = data(p)
        result.append({'path': member(p.relative_to(base).as_posix()), 'bytes': len(raw), 'sha256': digest(raw)})
        require(len(result) <= 1600 and sum(r['bytes'] for r in result) <= MAX_TOTAL, 'Tree audit bound exceeded')
    return result


def methods(text, names, executed=False, filtered=0):
    require(len(names) == len(set(names)), 'Duplicate expected methods')
    if executed:
        observed = re.findall(r'^test (\S+) \.\.\. ', text, re.M)
        summary = re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out; finished in [^\n]+$', text, re.M)
        require(summary == [(str(len(names)), '0', '0', '0', str(filtered))], 'Missing/failed/ignored method summary')
        require(len(re.findall(r'(?:^|\n)ok$| \.\.\. ok$', text, re.M)) == len(names), 'Missing terminal method success')
    else:
        observed = [line[:-6] for line in text.splitlines() if line.endswith(': test')]
        require(re.findall(r'^(\d+) tests, (\d+) benchmarks$', text, re.M) == [(str(len(names)), '0')], 'Incomplete list summary')
    require(len(observed) == len(set(observed)) == len(names) and set(observed) == set(names), 'Method roster mismatch')
    return observed


def negative(probe, stderr, source):
    require(len(source) == probe['bytes'] and digest(source) == probe['sha256'], 'API source mismatch')
    expected = {(s['byte_start'], s['byte_end']) for s in probe['primary_spans']}
    for s in probe['primary_spans']:
        require(source[s['byte_start']:s['byte_end']] == s['text'].encode(), 'Expected primary span bytes differ')
    pending = [parse(line) for line in stderr.splitlines() if line.strip()]
    seen, matches = set(), []
    while pending:
        d = pending.pop(0)
        require(isinstance(d, dict) and isinstance(d.get('children', []), list), 'Malformed diagnostic tree')
        pending.extend(d.get('children', []))
        require(isinstance(d.get('level'), str) and isinstance(d.get('message'), str), 'Malformed diagnostic')
        if d['level'] != 'error':
            continue
        if d.get('code') is None:
            require(re.fullmatch(r'aborting due to \d+ previous errors?(?:; \d+ warnings? emitted)?', d['message']), 'Unclassified compiler failure')
            continue
        require(isinstance(d['code'], dict) and d['code'].get('code') == probe['code']
                and all(s in d['message'] for s in probe['message_contains']), 'Unexpected API error code/message')
        primary = []
        require(isinstance(d.get('spans'), list), 'Missing API spans')
        for s in d['spans']:
            require(type(s.get('is_primary')) is bool and isinstance(s.get('file_name'), str)
                    and type(s.get('byte_start')) is int and type(s.get('byte_end')) is int, 'Malformed API span')
            start, end = s['byte_start'], s['byte_end']
            require(0 <= start <= end, 'Invalid span bounds')
            if s['file_name'] == probe['source']:
                require(end <= len(source), 'Span beyond source')
            if s['is_primary']:
                require(s['file_name'] == probe['source'] and (start, end) in expected and (start, end) not in seen, 'Wrong/duplicate primary target')
                seen.add((start, end))
                primary.append(s)
        require(primary, 'Error lacks required primary target')
        matches.append({'code': probe['code'], 'message': d['message'], 'primary': primary})
    require(seen == expected and matches, 'Incomplete negative primary target coverage')
    return matches



class ArchivePath:
    """Read-only view of ZIP data. No extraction, imports, processes or compiler."""
    def __init__(self, archive, name=''):
        self.archive, self.name = archive, name.strip('/')
    def __truediv__(self, child):
        return ArchivePath(self.archive, '/'.join(x for x in [self.name, str(child).strip('/')] if x))
    def __str__(self):
        return 'ZIP:' + self.name
    def is_file(self):
        return self.name in self.archive.namelist() and not self.archive.getinfo(self.name).is_dir()
    def is_dir(self):
        return any(n.startswith(self.name + '/') for n in self.archive.namelist())
    def is_symlink(self):
        return self.is_file() and stat.S_ISLNK(self.archive.getinfo(self.name).external_attr >> 16)
    def exists(self):
        return self.is_file() or self.is_dir()
    def stat(self):
        import types
        return types.SimpleNamespace(st_mode=stat.S_IFREG, st_size=self.archive.getinfo(self.name).file_size)
    def read_bytes(self):
        return self.archive.read(self.name)
    def rglob(self, pattern):
        require(pattern == '*', 'Unsupported virtual glob')
        prefix = self.name + '/' if self.name else ''
        return [ArchivePath(self.archive, n) for n in sorted(self.archive.namelist()) if n.startswith(prefix) and n != prefix and not n.endswith('/')]
    def __lt__(self, other):
        return self.name < other.name
    def relative_to(self, parent):
        return PurePosixPath(self.name[len(parent.name)+1:] if parent.name else self.name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--artifact-root', type=Path, default=ROOT / PREFIX / 'ci25-cache-actual/artifact')
    ap.add_argument('--zip', type=Path, default=Path('/tmp/mixer-ci25-cache.zip'))
    ap.add_argument('--review-root', type=Path, default=ROOT, help='Root for prospective review/baseline/proof data; frozen evidence/reviewed is sufficient')
    ap.add_argument('--freeze', action='store_true', help='Save compact byte-for-byte evidence and hash manifests in owned directory')
    ap.add_argument('--zip-only', action='store_true', help='Audit ZIP in memory; no extraction or duplicated packs')
    args = ap.parse_args()
    archive_reader = zipfile.ZipFile(args.zip) if args.zip_only else None
    art = ArchivePath(archive_reader) if archive_reader else args.artifact_root.resolve()
    snapshots = {}
    result = {'schema': 1, 'scope': 'Independent actual immutable ordinary-CI DATA audit; no imported fixture execution',
              'source_revision': REV, 'source_tree': TREE, 'groups': [], 'failures': [], 'summary': {},
              'environment': {'python': sys.version, 'executable': sys.executable,
                              'python_sha256': digest(data(Path(sys.executable).resolve())),
                              'audit_script_sha256': digest(data(Path(__file__).resolve()))},
              'actions': {'compiler_native_process_probes': 0, 'runner_imports': 0, 'children': 0,
                          'network_or_CI_polling': 0, 'commits_or_pushes': 0}}

    def a(name, compact=False):
        raw = data(art / member(name))
        if compact:
            snapshots['artifact/' + name] = raw
        return raw

    def aj(name, compact=False):
        return parse(a(name, compact))

    def local(name):
        raw = data(args.review_root / member(name))
        snapshots['reviewed/' + name] = raw
        return raw

    def group(name, fn):
        try:
            detail = fn()
            result['groups'].append({'name': name, 'passed': True, 'detail': detail})
        except Exception as error:
            result['groups'].append({'name': name, 'passed': False, 'error': str(error)})
            result['failures'].append({'group': name, 'type': type(error).__name__, 'message': str(error)})

    before = rows(art)
    require(len(before) == 1374 and sum(x['bytes'] for x in before) == 83234662, 'Expected exactly 1374 files / 83234662 bytes')
    r = aj(RUN + 'receipt.json', True)
    retained = aj(RUN + 'retention.json', True)
    inv = {name: aj(RUN + 'pack/inventories/' + name + '.json', True)
           for name in ['methods', 'layouts', 'file-cases', 'api-contract', 'control-markers']}
    commands = {c['name']: c for c in r['commands']}
    retention = {f['path']: f for f in retained['files']}
    actual_out = str(PurePosixPath(r['argv'][-1]))
    ci_root = actual_out.split('/verification/', 1)[0]
    pack = actual_out + '/pack'
    scratch = actual_out + '/scratch'
    compiler = r['rustc']['path']
    products = {f['path']: f for f in retained['compiler_products_hashed_before_removal']}

    def output(name, stream):
        return a(RUN + 'commands/' + name + '.' + stream, True).decode()

    def capture(name):
        f = retention[name]
        raw = a(RUN + f['content'])
        require(f['encoding'] == 'identity', 'No compressed retained files expected in this bounded run')
        return raw

    def zip_binding():
        raw = data(args.zip.resolve())
        require(len(raw) == 3376405 and digest(raw) == ZIP_SHA, 'Pinned ZIP differs')
        proof = parse(local(PREFIX + 'ci25-cache-actual/acquisition.json'))
        require((proof['run'], proof['attempt'], proof['job'], proof['artifact'], proof['head']) ==
                (42429965271, 1, 128576481836, 13596788917, REV), 'Acquisition identity differs')
        require(proof['archive']['bytes'] == len(raw) and proof['archive']['sha256'] == ZIP_SHA
                and all(proof[k] is True for k in ['downloadCompleted','responseReaderClosed','zipReaderClosed']), 'Acquisition/reader completion missing')
        listed = parse(local(PREFIX + 'ci25-cache-actual/artifact-list.json'))
        chosen = [x for x in listed['artifacts'] if x['id'] == proof['artifact']]
        require(len(chosen) == 1, 'Ambiguous artifact')
        item = chosen[0]
        require(item['workflow_run']['id'] == proof['run'] and item['workflow_run']['head_sha'] == REV
                and item['digest'] == 'sha256:' + ZIP_SHA and item['size_in_bytes'] == len(raw)
                and item['name'] == 'swift-cache-state-fixture-' + REV + '-42429965271-1', 'API artifact binding differs')
        jobs = parse(local(PREFIX + 'ci25-cache-actual/jobs.json'))
        job = [j for j in jobs['jobs'] if j['id'] == proof['job']]
        require(len(job) == 1 and job[0]['run_id'] == proof['run'] and job[0]['name'] == 'swift-cache-state-fixture'
                and job[0]['status'] == 'completed' and job[0]['conclusion'] == 'success'
                and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job[0]['steps']), 'Job or required step incomplete')
        log = local(PREFIX + 'ci25-cache-actual/job.log').decode()
        require('SHA256 digest of uploaded artifact zip is ' + ZIP_SHA in log
                and 'Final size is 3376405 bytes. Artifact ID is 13596788917' in log
                and 'Complete job name: swift-cache-state-fixture' in log
                and '+%s:refs/remotes/origin/main' % REV in log, 'Job log identity/finalization mismatch')
        mapped = {v['path']: v for v in before}
        require({k:{'bytes':v['bytes'],'sha256':v['sha256']} for k,v in mapped.items()} == proof['files'], 'Acquisition file map differs')
        with zipfile.ZipFile(args.zip) as z:
            info = [i for i in z.infolist() if not i.is_dir()]
            require(len(info) == len({i.filename for i in info}) == 1374, 'ZIP duplicate/count mismatch')
            require(sum(i.file_size for i in info) == 83234662, 'ZIP total differs')
            require(set(mapped) == {member(i.filename) for i in info}, 'ZIP/extraction roster differs')
            for i in info:
                require(i.file_size <= MAX_FILE and not stat.S_ISLNK(i.external_attr >> 16), 'Unsafe ZIP member')
                b = z.read(i)
                require(len(b) == mapped[i.filename]['bytes'] and digest(b) == mapped[i.filename]['sha256'], 'ZIP/extraction mismatch ' + i.filename)
        return {'run':proof['run'], 'attempt':1, 'job':proof['job'], 'artifact':proof['artifact'],
                'revision':REV, 'zip_sha256':ZIP_SHA, 'zip_bytes':len(raw), 'files':len(before),
                'bytes':sum(v['bytes'] for v in before), 'acquisition_completed_and_readers_closed':True,
                'independent_zip_reader_closed':z.fp is None, 'network_metadata_not_refetched':True}

    def reviewed_admission():
        review_raw = local(PREFIX + 'cache-review/controls-result.json')
        review = parse(review_raw)
        review_receipt = parse(local(PREFIX + 'cache-review/receipt.json'))
        require(digest(review_raw) == review_receipt['artifacts_sha256']['controls-result.json']
                == 'c9a6257cf77b08e45de4031de3aa45db81ffa4aeaf7666ede1793481f564458b', 'Prospective review results changed')
        require(digest(local(PREFIX + 'cache-review/verdict.md')) == review_receipt['artifacts_sha256']['verdict.md'], 'Prospective review verdict changed')
        old_base = aj('verification/swift-cache-state-ci/pack/manifest.json', True)
        original = {'verification/swift-cache-state-ci/pack/' + f['path']: f for f in old_base['members']}
        direct = indirect = historical = 0
        for name, h in review['input_hashes'].items():
            if (art / name).is_file():
                require(digest(a(name)) == h, 'Reviewed source differs ' + name)
                direct += 1
            elif name in original:
                require(original[name]['sha256'] == h, 'Original base-manifest binding differs ' + name)
                indirect += 1
            else:
                require(digest(local(name)) == h, 'Historical reviewed input differs ' + name)
                historical += 1
        require((direct, indirect, historical) == (79, 86, 4), 'Reviewed 169-input binding coverage differs')
        selection = aj(FIX + 'compiler-selection.json', True)
        require(selection['profile'] == {'compiler_sha256': COMPILER, 'identity': IDENTITY}
                and selection['qualified'] is False, 'Prospective exact profile changed')
        manifest = aj(FIX + 'sources.json', True)
        require(digest(canonical(manifest['members'])) == manifest['tree_sha256'], 'Selection source tree mismatch')
        for row in manifest['members']:
            b = a(FIX + row['path'], True)
            require(len(b) == row['bytes'] and digest(b) == row['sha256'], 'Selection shipping source mismatch')
            require(a(RUN + 'compiler-selection-sources/' + row['path'], True) == b, 'Invocation selection snapshot mismatch')
        require(a(RUN + 'compiler-selection-sources/sources.json', True) == a(FIX + 'sources.json'), 'Invocation manifest snapshot differs')
        workflow = a('.github/workflows/verify.yml', True)
        local(PREFIX + 'cache-review/prospective-workflow.yml')  # Original proposal retained as history, not current workflow authority.
        proposal = a(NEW + 'workflow/swift-cache-state-fixture.yml').decode()
        lines = workflow.decode().splitlines(keepends=True)
        start = lines.index('  swift-cache-state-fixture:\n')
        end = next((i for i in range(start + 1, len(lines)) if re.match(r'^  \S.*:\n$', lines[i])), len(lines))
        require(''.join(lines[start:end]) == proposal, 'Installed cache job differs')
        seal = aj(OLD + 'seal.json', True)
        dependencies = aj(OLD + 'dependencies.json', True)
        require(digest(canonical(seal['members'])) == seal['tree_sha256'], 'Historical seal tree differs')
        require(digest(canonical(dependencies['members'])) == dependencies['tree_sha256'], 'Dependency tree differs')
        def bound(base, rr):
            for row in rr:
                n = base + row['path']
                if (art / n).is_file():
                    b = a(n, n.endswith(('.py', 'seal.json', 'dependencies.json')))
                    require(len(b) == row['bytes'] and digest(b) == row['sha256'], 'Sealed source differs ' + n)
                else:
                    require(n in original and all(original[n][k] == row[k] for k in ['bytes', 'sha256']), 'Missing unbound source ' + n)
        bound(OLD, seal['members'])
        bound('', dependencies['members'])
        require(digest(a(V2 + 'check_cache_state.py', True)) == RUNNER
                and a(V2 + 'check_cache_state.py') == a(RUN + 'executed-runner.py', True), 'Unchanged runner/snapshot pin')
        return {'reviewed_inputs': 169, 'artifact_input_files_bound_by_bytes': direct, 'original_base_manifest_bindings': indirect,
                'preserved_historical_bytes': historical, 'historical_seal_members': len(seal['members']),
                'historical_dependency_members': len(dependencies['members']), 'selection_shipping_members': len(manifest['members']),
                'installed_cache_job_equals_new_proposal': True, 'runner_sha256': RUNNER}

    def identity():
        require(r['rustc']['identity'] == IDENTITY and r['rustc']['version_verbose'] == VERBOSE, 'Exact Rust verbose identity mismatch')
        require(output('compiler-identity', 'stdout') == VERBOSE and not output('compiler-identity', 'stderr'), 'Raw compiler identity differs')
        require(r['rustc']['sha256'] == COMPILER and r['postflight']['compiler'] == {'passed': True, 'observed': COMPILER}, 'Compiler binary observations differ')
        require(output('compiler-sysroot', 'stdout').strip() == r['rustc']['sysroot']
                and compiler == r['rustc']['sysroot'] + '/bin/rustc', 'Compiler resolver join differs')
        start, end = aj(RUN + 'selection-start.json', True), aj(RUN + 'selection-result.json', True)
        require(start['installed_job_verified'] is True and start['fixture_invocations_admitted'] == 1
                and start['requested_rustc'] == r['rustc']['requested'], 'Admission/start mismatch')
        require(end['fixture_return_status'] == 0 and end['errors'] == []
                and end['selection_sha256'] == start['selection_sha256'] == digest(a(FIX + 'compiler-selection.json')), 'Terminal exact selection did not close')
        require(start['sources_sha256'] == digest(a(FIX + 'sources.json'))
                and start['workflow_job_sha256'] == digest(a(NEW + 'workflow/swift-cache-state-fixture.yml')), 'Admission hashes differ')
        return {'identity': IDENTITY, 'compiler_sha256': COMPILER,
                'raw_verbose_sha256': digest(VERBOSE.encode()), 'one_admitted_invocation': True,
                'compiler_binary_bytes': 'Hash observed twice in trusted CI; compiler binary intentionally not uploaded'}

    def pack_and_retention():
        m = aj(RUN + 'pack/manifest.json', True)
        require(digest(a(RUN + 'pack/manifest.json')) == MANIFEST and m['tree_sha256'] == PACK_TREE
                and digest(canonical(m['members'])) == PACK_TREE and m['member_count'] == 86, 'Pack manifest mismatch')
        for base in [RUN + 'pack/', V2 + 'materialized/pack/']:
            actual = [x for x in rows(art / base) if x['path'] != 'manifest.json']
            require(actual == m['members'], 'Complete pack missing/extra/mutated source')
        require(len(retention) == len(retained['files']) == 901 and len(products) == 14, 'Retention count/duplicates')
        for f in retained['files']:
            member(f['path'])
            b = capture(f['path'])
            require(len(b) == f['bytes'] and digest(b) == f['sha256'] == f['retained_sha256'], 'Retained byte mismatch ' + f['path'])
        source_rows = []
        for f in m['members']:
            if f['path'].startswith('source/'):
                name = f['path'][7:]
                b = a(RUN + 'pack/' + f['path']) + (APPEND if name == 'library/cache_state.rs' else b'')
                require(capture('derived/' + name) == b, 'Derived source bytes differ ' + name)
                source_rows.append({'path': name, 'bytes': len(b), 'sha256': digest(b)})
        for name in ['selected_controls.rs', 'scalar_cursor_independent.rs']:
            b = a(RUN + 'pack/controls/' + name)
            require(capture('derived/' + name) == b, 'Private control append changed')
            source_rows.append({'path': name, 'bytes': len(b), 'sha256': digest(b)})
        source_rows.sort(key=lambda f: f['path'])
        require(source_rows == r['derivative']['source_rows'] == r['postflight']['derived']['observed']
                and len(source_rows) == 19 and r['derivative']['base_prefix_verified'] is True
                and r['derivative']['append_utf8'].encode() == APPEND, 'Derivative complete roster/postflight differs')
        require(r['derivative']['base_sha256'] == digest(a(RUN + 'pack/source/library/cache_state.rs'))
                and r['derivative']['derived_sha256'] == digest(capture('derived/library/cache_state.rs')), 'Derivative digest mismatch')
        return {'pack_members': 86, 'retained_nonproduct_files': 901, 'compiler_products_hashed_then_removed': 14,
                'derived_source_members': 19, 'pack_tree_sha256': PACK_TREE,
                'unique_retained_content_files': len({f['content'] for f in retained['files']})}

    def workload():
        expected = []
        def add(name, argv, cwd, env=None):
            overrides = dict.fromkeys(['TEMP', 'TMP', 'TMPDIR'], scratch + '/command-tmp')
            overrides.update(env or {})
            expected.append((name, argv, cwd, overrides))
        add('compiler-sysroot', [r['rustc']['launcher'], '--print', 'sysroot'], actual_out)
        add('compiler-identity', [compiler, '--version', '--verbose'], actual_out)
        add('source-revision', ['git', 'rev-parse', 'HEAD'], ci_root)
        add('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'], ci_root)
        for mode, opts in [('debug', []), ('optimized', ['-O'])]:
            for lane, source, cfg in [('host', 'source/library/analyzer.rs', []),
                                      ('producer', 'source/regression/independent_tests.rs', ['--cfg', 'inherited_transport']),
                                      ('independent', 'source/library/analyzer.rs', ['--cfg', 'inherited_review']),
                                      ('controls', scratch + '/derived/library/analyzer.rs', [])]:
                binary = scratch + '/' + lane + '-' + mode
                add(lane + '-' + mode + '-compile', [compiler, '--edition=2021', '--test', *cfg, *opts, source, '-o', binary], pack)
                add(lane + '-' + mode + '-list', [binary, '--list'], pack)
                groups = inv['methods']['producer_debug_partition'] if (lane, mode) == ('producer', 'debug') else [{'name': 'all', 'args': []}]
                for g in groups:
                    n = lane + '-' + mode + '-' + g['name']
                    work = scratch + '/' + n
                    env = dict.fromkeys(['MIXER_ANALYZER_LIBRARY_TEST_SCRATCH', 'MIXER_ENVELOPE_SCRATCH', 'MIXER_REVIEW_SCRATCH', 'REVIEW_SCRATCH'], work)
                    env.update(dict.fromkeys(['TMPDIR', 'TMP', 'TEMP'], work + '/tmp'))
                    env['MIXER_ANALYZER_LIBRARY_HISTORICAL'] = pack + '/inputs/historical'
                    if lane in {'host', 'controls'}:
                        env['MIXER_CACHE_FIXTURE_EVIDENCE'] = work + '/cases'
                    add(n, [binary, *g['args'], '--test-threads=1', '--nocapture'], pack, env)
            library = scratch + '/libcache_fixture-' + mode + '.rlib'
            add('library-' + mode, [compiler, '--edition=2021', *opts, '--crate-type=lib', '--crate-name', 'cache_fixture', 'source/library/analyzer.rs', '-o', library], pack)
            for p in inv['api-contract']['probes']:
                name = 'api-' + p['name'].replace('/', '_') + '-' + mode
                target = scratch + '/' + name
                add(name, [compiler, '--edition=2021', *opts, '--extern', p['crate_alias'] + '=' + library, '--error-format=json', p['source'], '-o', target], pack)
                if p['expected_success']:
                    add(name + '-execute', [target], pack)
        add('source-revision-after', ['git', 'rev-parse', 'HEAD'], ci_root)
        add('source-tree-after', ['git', 'rev-parse', 'HEAD^{tree}'], ci_root)
        require(len(r['commands']) == len(commands) == len(expected) == 103, 'Incomplete/duplicate 103-command workload')
        require([c['name'] for c in r['commands']] == [e[0] for e in expected], 'Command order/inventory differs')
        negatives = {'api-' + p['name'].replace('/', '_') + '-' + mode for p in inv['api-contract']['probes'] if not p['expected_success'] for mode in ['debug', 'optimized']}
        for c, (name, argv, cwd, env) in zip(r['commands'], expected):
            require((c['argv'], c['cwd'], c['environment_overrides']) == (argv, cwd, env), 'Exact command/cwd/environment changed ' + name)
            require(aj(RUN + 'commands/' + name + '.json', True) == c, 'Independent command row differs ' + name)
            require(c['exit'] == (1 if name in negatives else 0), 'Wrong exit disposition ' + name)
            for stream in ['stdout', 'stderr']:
                b = output(name, stream).encode()
                require(len(b) <= 8388608 and digest(b) == c[stream + '_sha256'], 'Command output bytes/hash mismatch ' + name)
        return {'commands': 103, 'producer_debug_partitions': len(inv['methods']['producer_debug_partition']),
                'exact_argv_cwd_environment_order': True, 'expected_nonzero_negative_compiles': len(negatives),
                'complete_stdout_stderr_and_json': 309}

    def behavior():
        summary = {}
        for mode in ['debug', 'optimized']:
            summary[mode] = {}
            for lane, count in [('host', 84), ('producer', 108), ('independent', 98), ('controls', 94)]:
                names = inv['methods'][lane]
                require(len(names) == count, 'Expected method count changed')
                methods(output(lane + '-' + mode + '-list', 'stdout'), names)
                groups = inv['methods']['producer_debug_partition'] if (lane, mode) == ('producer', 'debug') else [{'name': 'all', 'methods': names}]
                observed = []
                for g in groups:
                    observed.extend(methods(output(lane + '-' + mode + '-' + g['name'], 'stdout'), g['methods'], True, count - len(g['methods'])))
                require(len(observed) == len(set(observed)) == count and set(observed) == set(names), 'Partition coverage mismatch')
                row = r['modes'][mode]['methods'][lane]
                require(row['count'] == count and row['names'] == sorted(names) and row['complete_disjoint_coverage'] is True
                        and row['binary_sha256'] == products[lane + '-' + mode]['sha256'], 'Method receipt/product hash mismatch')
                summary[mode][lane] = count
        progress_names = [c['name'] for c in r['commands'] if c['context_phase_progress']]
        require(progress_names == ['producer-debug-root-03', 'producer-optimized-all'], 'Context progress command inventory differs')
        for name in progress_names:
            raw = re.findall(r'^context_progress completed=(\d+)/1003 elapsed_ms=(\d+) prepare_ms=(\d+) analyze_ms=(\d+) report_assert_ms=(\d+) cleanup_ms=(\d+)$', output(name, 'stderr'), re.M)
            require(len(raw) == len(commands[name]['context_phase_progress']) == 16, 'Incomplete context progress trace')
            for values, observed in zip(raw, commands[name]['context_phase_progress']):
                completed, elapsed, prepare, analyze, report, cleanup = map(int, values)
                expected = {'completed': completed, 'elapsed_ms': elapsed, 'prepare_ms': prepare,
                            'analyze_ms': analyze, 'report_assert_ms': report, 'cleanup_ms': cleanup,
                            'unattributed_elapsed_remainder_ms': elapsed - prepare - analyze - report - cleanup,
                            'total': 1003, 'progress_is_not_completion': True}
                require(all(observed[k] == v for k, v in expected.items()), 'Context progress receipt differs from raw output')
            require(int(raw[-1][0]) == 1003, 'Context trace incomplete; method terminal success is separately required')
        return {'methods_per_mode': summary, 'total_method_executions': 768, 'ignored_or_failed_methods': 0,
                'context_cases_per_mode': 1003, 'context_progress_records_per_mode': 16,
                'coverage_scope': 'Exact original roster per lane; overlapping methods are not deduplicated as unique tests'}

    def cases_and_layouts():
        require(len(inv['file-cases']['cases']) == 31 and inv['layouts']['count'] == 23, 'Original case/layout inventory changed')
        observations = 0
        for mode in ['debug', 'optimized']:
            for lane in ['host', 'controls']:
                text = output(lane + '-' + mode + '-all', 'stdout')
                layouts = [{'type': n, 'bytes': int(b), 'align': int(align)} for n, b, align in re.findall(r'ACCOUNTING_LAYOUT (.+?) size=(\d+) align=(\d+)', text)]
                require(layouts == inv['layouts']['layouts'] == r['modes'][mode][lane + '_layouts'], 'Actual layout mismatch')
                prefix = lane + '-' + mode + '-all/cases/'
                expect_files = set()
                recorded = []
                for case in inv['file-cases']['cases']:
                    cp = prefix + case['case'] + '/'
                    rr = []
                    for name in ['input-0.bin', 'input-1.bin', 'input-2.bin', 'report.bin', 'result.txt']:
                        expect_files.add(cp + name)
                        b = capture(cp + name)
                        rr.append({'path': name, 'bytes': len(b), 'sha256': digest(b)})
                        if name != 'result.txt':
                            require({'bytes': len(b), 'sha256': digest(b)} == case['raw'][name], 'Actual four-File bytes differ ' + cp + name)
                    raw = capture(cp + 'result.txt')
                    snapshots['actual-cases/' + cp + 'result.txt'] = raw
                    lines = raw.decode().splitlines()
                    require(len(lines) == 2 and lines[0] == case['result_first_line'], 'Full aggregate/error result differs ' + cp)
                    stamps = re.fullmatch(r'input_stamps_before_and_after=\[(.*)\]', lines[1])
                    require(stamps is not None, 'Missing input stability stamps')
                    ss = re.findall(r'Stamp \{ fields: \[([\d, ]+)\], regular: 1 \}', stamps[1])
                    require(len(ss) == 3, 'Incomplete actual input stamps')
                    for i, s in enumerate(ss):
                        fields = [int(x) for x in s.split(', ')]
                        require(len(fields) == 8 and fields[3] == case['raw'][f'input-{i}.bin']['bytes']
                                and stat.S_ISREG(fields[2]), 'Input stamp size/type differs')
                    rr.sort(key=lambda x: x['path'])
                    recorded.append({'case': case['case'], 'scope': case['scope'], 'complete32': case['actual_complete32'],
                                     'aggregate_present': case['aggregate_present'], 'result_first_line_sha256': digest(lines[0].encode()),
                                     'capture_tree_sha256': digest(canonical(rr))})
                    observations += 1
                require({f for f in retention if f.startswith(prefix)} == expect_files, 'Missing/extra case files')
                require(recorded == r['modes'][mode][lane + '_File_cases'], 'Actual case receipt does not bind raw capture')
        for mode in ['debug', 'optimized']:
            text = output('controls-' + mode + '-all', 'stdout')
            for k, v in inv['control-markers'].items():
                require(re.findall(re.escape(k) + r'=([^\n]+)', text) == [v], 'Missing/changed private control marker ' + k)
        return {'four_File_captures': observations, 'unique_case_inventory': 31, 'captures_per_case': 4,
                'aggregate_results': 116, 'outer_errors_without_aggregate': 8,
                'raw_input_report_and_full_result_files': observations * 5, 'layout_observations': 92,
                'private_markers_per_mode': len(inv['control-markers']), 'private_public_reachability_credit': 0}

    def api_controls():
        counts = {'positive_compiles_and_executions': 0, 'negative_compiles': 0, 'primary_target_spans': 0}
        for mode in ['debug', 'optimized']:
            actual = []
            for p in inv['api-contract']['probes']:
                name = 'api-' + p['name'].replace('/', '_') + '-' + mode
                c = commands[name]
                row = {'name': p['name'], 'expected_success': p['expected_success'], 'compile_exit': c['exit']}
                if p['expected_success']:
                    require(c['exit'] == 0 and commands[name + '-execute']['exit'] == 0, 'Positive API compile/run missing')
                    row.update(binary_sha256=products[name]['sha256'], executed=True)
                    counts['positive_compiles_and_executions'] += 1
                else:
                    require(c['exit'] == 1 and name not in products, 'Negative API emitted a compiler product')
                    row['diagnostics'] = negative(p, output(name, 'stderr'), a(RUN + 'pack/' + p['source']))
                    counts['negative_compiles'] += 1
                    counts['primary_target_spans'] += sum(len(d['primary']) for d in row['diagnostics'])
                actual.append(row)
            require(actual == r['modes'][mode]['api'], 'API receipt does not bind raw diagnostics/products')
        require(counts == {'positive_compiles_and_executions': 4, 'negative_compiles': 46, 'primary_target_spans': 76}, 'API disposition/span totals differ')
        return counts

    def bounds_and_custody():
        require((r['active_deadline_seconds'], r['cleanup_allowance_seconds'], r['per_child_seconds']) == (600, 60, 60), 'Original top-level finite limits changed')
        require(0 < r['active_elapsed_seconds'] < 600 and 0 < r['cleanup_elapsed_seconds'] < 60, 'Actual resource bound exceeded')
        last = datetime.fromisoformat(r['started_utc'])
        for c in r['commands']:
            require(c['per_child_limit_seconds'] == 60 and 0 < c['effective_timeout_seconds'] <= 60
                    and 0 <= c['elapsed_seconds'] < c['effective_timeout_seconds'] and c['per_stream_cap_bytes'] == 8388608, 'Command resource bound differs')
            require(c['child_returned'] is True and c['owned_group_gone'] is True and c['new_session'] is True
                    and c['pid'] == c['pgid'] and c['errors'] == []
                    and not any(c.get(k) for k in ['timed_out', 'output_capped', 'custody_hold', 'descendants_outlived_child', 'owned_group_killed']), 'Command lacks clean custody closure')
            start, end = datetime.fromisoformat(c['started_utc']), datetime.fromisoformat(c['finished_utc'])
            require(last <= start <= end, 'Command sessions overlap/out of order')
            last = end
            u = c['child_resource_usage']
            require(u['terminal_facts_verified'] is True and u['aggregate_delta'] is not None, 'Missing terminal child resource snapshots')
            require(all(u['aggregate_delta'][k] >= 0 and abs(u['after'][k] - u['before'][k] - v) < 1e-8 for k, v in u['aggregate_delta'].items()), 'Child resource delta differs')
        require(last <= datetime.fromisoformat(r['finished_utc']), 'Final command extends beyond terminal receipt')
        cleanup = r['cleanup']
        require(cleanup['removed'] is True and cleanup['groups_returned'] is True
                and cleanup['other_project_or_native_discovery'] is False and cleanup['files_hashed_before_removal'] == 916
                and cleanup['products_hashed_before_removal'] == retained['compiler_products_hashed_before_removal']
                and cleanup['files_hashed_before_removal'] == len(retained['files']) + len(products) + 1, 'Missing complete retain-before-removal closure')
        require(not (art / RUN / 'scratch').exists(), 'Scratch unexpectedly uploaded/present')
        marker = aj(RUN + 'ownership.json', True)
        require(marker == r['output_ownership']['marker'] and cleanup['marker']['purpose'] == 'mixer-cache-state-fixture-ci-scratch'
                and marker['purpose'] == 'mixer-cache-state-fixture-ci-output' and cleanup['marker']['token'] != marker['token'], 'Ownership marker join differs')
        return {'active_seconds_observed': r['active_elapsed_seconds'], 'cleanup_seconds_observed': r['cleanup_elapsed_seconds'],
                'longest_child_seconds_observed': max(c['elapsed_seconds'] for c in r['commands']),
                'per_child_active_cleanup_stream_bounds': [60, 600, 60, 8388608],
                'owned_child_groups_returned': 103, 'maximum_concurrent_recorded_groups': 1,
                'scratch_files_hashed_before_removal': 916, 'scratch_removed_observation': True,
                'no_live_host_process_or_scratch_probes': True}

    def postflight():
        expected = {'compiler': COMPILER, 'python': r['python']['sha256'], 'launcher': r['rustc']['launcher_sha256'],
                    'runner': RUNNER, 'runner-snapshot': RUNNER, 'pack': PACK_TREE, 'snapshot': PACK_TREE,
                    'shared-input-overlay': r['shared_input_overlay'], 'derived': r['derivative']['source_rows'],
                    'output-ownership': r['output_ownership']}
        require(r['postflight'] == {k: {'passed': True, 'observed': v} for k, v in expected.items()}, 'Missing/failed/mismatched actual postflight observation')
        require(r['source_revision'] == r['source_revision_after'] == REV and r['source_tree'] == r['source_tree_after'] == TREE, 'Source revision/tree changed')
        for name, value in [('source-revision', REV), ('source-revision-after', REV), ('source-tree', TREE), ('source-tree-after', TREE)]:
            require(output(name, 'stdout') == value + '\n', 'Raw source revision/tree differs')
        require(r['status'] == 'passed-host-fixture-check' and r['active_checks_completed'] is True and r['errors'] == [], 'Incomplete actual success')
        require(aj(OLD + 'logs/postflight.stdout', True)['installed_job_verified'] is True, 'Missing workflow selection postflight')
        return {'source_revision_before_after': REV, 'source_tree_before_after': TREE,
                'complete_actual_postflights': sorted(expected), 'ci_python': r['python'],
                'compiler_launcher': {k: r['rustc'][k] for k in ['launcher', 'launcher_target', 'launcher_sha256']}}

    def test_methods(source):
        text = source.decode()
        return {n.name: ast.get_source_segment(text, n) for owner in ast.parse(text).body
                if isinstance(owner, ast.ClassDef) for n in owner.body
                if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}

    def new_adoption():
        manifest = aj(NEW + 'sources.json')
        require(digest(a(NEW + 'sources.json')) == '8f8f3880b023c62eaaa12bb53911ce2dccb5ee85817a9371f006978f52b3dd59', 'Reviewed new source seal changed')
        require(manifest['member_count'] == len(manifest['members']) == 11
                and digest(canonical(manifest['members'])) == manifest['tree_sha256']
                == 'be46b1c87d1971505d58622a8e189e29f0b5895e15bbd325065e4f24fa2cacb7', 'New shipping manifest tree differs')
        for row in manifest['members']:
            raw = a(NEW + member(row['path']))
            require(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'New shipping source differs ' + row['path'])
        require(a(NEW + 'workflow/previous-job.yml') == a(FIX + 'workflow/swift-cache-state-fixture.yml'), 'Previous job preimage changed')
        prospective = local(PREFIX + 'cache-deadline-control-review/prospective-verify.yml')
        require(digest(prospective) == '99993998b7babd9b85c2c7f8e662720b87b5be82eb8ea787d1effd6191fb5b73'
                and a('.github/workflows/verify.yml') == prospective, 'Whole workflow differs from independently reviewed new proposal')
        old_inputs = aj(NEW + 'old-inputs-before.json')
        require(len(old_inputs['members']) == 163, 'Historical 163-input roster changed')
        original_pack = {'verification/swift-cache-state-ci/pack/'+row['path']:row
                         for row in aj('verification/swift-cache-state-ci/pack/manifest.json')['members']}
        historical_binding_counts = {'direct_unchanged':0,'original_pack_manifest':0,'reconstructed_previous_workflow':0}
        for row in old_inputs['members']:
            name = row['path']
            if name == '.github/workflows/verify.yml':
                new_job = a(NEW + 'workflow/swift-cache-state-fixture.yml')
                require(prospective.count(new_job)==1, 'Ambiguous prospective job')
                raw = prospective.replace(new_job,a(NEW+'workflow/previous-job.yml'),1)
                historical_binding_counts['reconstructed_previous_workflow']+=1
            elif (art / name).is_file():
                raw = a(name)
                historical_binding_counts['direct_unchanged']+=1
            else:
                require(name in original_pack and all(original_pack[name][k]==row[k] for k in ['bytes','sha256']), 'Unbound historical pack source '+name)
                historical_binding_counts['original_pack_manifest']+=1
                continue
            require(len(raw)==row['bytes'] and digest(raw)==row['sha256'], 'Historical input changed '+name)
        require(historical_binding_counts == {'direct_unchanged':76,'original_pack_manifest':86,'reconstructed_previous_workflow':1}, 'Historical binding counts differ')
        original = test_methods(a(V2 + 'test_runner.py'))
        require(len(original) == 36 and test_methods(a(NEW + 'runner-controls.py')) == original, 'Original 36 method bodies changed')
        preflight = a(OLD + 'logs/preflight.stdout').decode().splitlines()
        require(preflight[:4] == [REV, TREE, 'Python 3.15.2', 'Darwin 24.6.0 arm64'], 'Fresh preflight source/tool identity differs')
        proof = parse(preflight[4])
        require(proof == aj(OLD + 'logs/postflight.stdout') == aj(RUN + 'selection-start.json')['deadline_controls'], 'Preflight/admission/postflight new proposal does not close')
        require(proof['installed_job_verified'] is True and proof['correction_sources_sha256'] == digest(a(NEW + 'sources.json'))
                and proof['control_derivative_sha256'] == digest(a(NEW + 'runner-controls.py'))
                and proof['workflow_job_sha256'] == digest(a(NEW + 'workflow/swift-cache-state-fixture.yml')), 'New proof hashes mismatch')
        require(not a(OLD + 'logs/preflight.stderr') and not a(OLD + 'logs/postflight.stderr'), 'Pre/postflight errors')
        historical = proof['previous_adoption']['historical_adoption']
        require(historical['adoption_seal_sha256'] == digest(a(OLD + 'seal.json'))
                and historical['dependencies_sha256'] == digest(a(OLD + 'dependencies.json')), 'Historical seal proof differs')
        return {'shipping_members': manifest['members'], 'manifest_sha256': digest(a(NEW + 'sources.json')),
                'tree_sha256': manifest['tree_sha256'], 'unchanged_original_test_method_bodies':36, 'historical_163_bindings':historical_binding_counts,
                'whole_workflow_equals_independent_prospective_review':True,
                'preflight_admission_postflight_equal':True, 'wall_latency_qualified':False}

    def original_controls():
        counts, bindings = {}, []
        specs = [('adoption',16,OLD+'logs/adoption-controls',OLD+'test_adoption.py'),
                 ('materializer',9,V2+'logs/materializer-controls',V2+'test_materializer.py'),
                 ('selection',16,FIX+'logs/selection-controls',FIX+'test_selection.py'),
                 ('runner-normal',36,V2+'logs/runner-controls',NEW+'runner-controls.py'),
                 ('runner-optimized',36,NEW+'runner-optimized',NEW+'runner-controls.py'),
                 ('contracts-normal',11,NEW+'contracts-normal',NEW+'test_contracts.py'),
                 ('contracts-optimized',11,NEW+'contracts-optimized',NEW+'test_contracts.py')]
        log = re.sub(r'\x1b\[[0-9;]*m', '', local(PREFIX+'ci25-cache-actual/job.log').decode())
        for kind,n,path,source in specs:
            stderr = a(path+'.stderr').decode()
            names = re.findall(r'^(test_\w+) \(.*\) \.\.\. ok$', stderr, re.M)
            require(re.findall(r'^Ran (\d+) tests in [\d.]+s$',stderr,re.M) == [str(n)]
                    and re.findall(r'^OK$',stderr,re.M) == ['OK'] and len(names) == len(set(names)) == n,
                    'Incomplete/failed current '+kind+' controls')
            require(set(names) == set(test_methods(a(source))), 'Current control method inventory mismatch '+kind)
            stdout = a(path+'.stdout').decode()
            if kind in ['adoption','selection']:
                d = parse(stdout)
                require(d['passed'] is True and d['tests'] == n and d['python'].startswith('3.15.2'), 'Control tool mismatch')
                require(d.get('compiler_runtime_or_fixture_executed', d.get('compiler_or_fixture_executed')) is False, 'Unexpected runtime source control')
                require(d.get('denied_operation_attempts',d.get('denied_runtime_attempts')) == [], 'Control guard denial')
                if kind == 'adoption':
                    require(d['control_scratch_absent'] is True, 'Adoption scratch unresolved')
            if kind.startswith(('runner-','contracts-')):
                emitted = [parse(line) for line in stdout.splitlines() if line.strip()]
                destinations = {x['receipt'].split('/scratch/',1)[0] for x in emitted}
                require(len(destinations) == 1, 'Control evidence root ambiguous')
                root = destinations.pop()
                require(root.startswith(ci_root+'/'+NEW+'evidence/'+kind+'-'), 'Historical control evidence mistaken for current')
                relative = root[len(ci_root)+1:]+'/'
                bindings.append({'kind':kind, 'stdout':path+'.stdout', 'stderr':path+'.stderr', 'evidence_root':relative, 'tests':n})
                require(not (art / relative / 'scratch').exists(), 'Fresh test scratch uploaded')
                if kind.startswith('runner-'):
                    result = aj(relative+'result.json')
                    require(result['successful'] is True and result['tests'] == 36 and result['errors'] == result['failures'] == []
                            and result['remaining_test_scratch'] == [] and result['timer_disarmed'] is True, 'Fresh runner result/cleanup mismatch')
                    expected_proof = dict(aj(OLD+'logs/postflight.stdout'), installed_job_verified=False)
                    require(result['adoption'] == expected_proof, 'Control source admission differs')
                    for stage in ['postflight','retention']:
                        d = aj(relative+'logs/deadline-'+stage+'-control.json')
                        require(d['stage'] == stage and d['status'] == 1 and d['exception'] is None
                                and d['receipt']['status'] == 'failed' and d['receipt']['commands'] == []
                                and d['receipt']['cleanup']['deadline_expired'] is True and d['receipt']['cleanup']['removed'] is False
                                and all(d[k] is True for k in ['handlers_restored','timer_disarmed','scratch_preserved','retained_before_assertions_and_teardown'])
                                and d['spawn_calls'] == 0 and d['state']['after_delay'] is False and d['state']['stage_timer_started'] is True,
                                'Fresh functional deadline observations incomplete')
                        require(d['receipt']['argv'] == [ci_root+'/'+NEW+'test_runner.py','-v']
                                and d['receipt']['python'] == r['python'], 'Fresh control command/tool identity differs')
                        ev = d['events']
                        require(sum(e['event']=='handler-raise' and e['type']=='CleanupDeadlineExpired' for e in ev)==1
                                and sum(e['event']=='stage-arm' and 0 < e['seconds'] <= .05 for e in ev)==1, 'Actual armed handler not observed')
                        require(datetime.fromisoformat('2026-11-08T00:29:36+00:00') < datetime.fromisoformat(d['receipt']['started_utc'])
                                < datetime.fromisoformat(d['receipt']['finished_utc']) < datetime.fromisoformat(r['started_utc']), 'Control timestamp outside current step')
                    control = aj(relative+'logs/descendant-control/control.json')
                    command = control['receipt']['commands'][0]
                    require(not control['custody_hold'] and command['child_returned'] is True and command['owned_group_gone'] is True
                            and command['timed_out'] is True and command['owned_group_killed'] is True and command['errors'] == []
                            and command['child_resource_usage']['terminal_facts_verified'] is True
                            and command['argv'][0] == r['python']['launcher'], 'Fresh descendant custody did not close')
                    require(command['cwd'].startswith(root+'/scratch/') and command['pid'] == command['pgid'], 'Descendant ownership binding differs')
                    for row in control['outputs']:
                        raw = a(relative+'logs/descendant-control/'+member(row['path']))
                        require(len(raw)==row['bytes'] and digest(raw)==row['sha256'], 'Descendant output hash mismatch')
                else:
                    for delta,expired in [('.049',False),('.05',True),('.051',True)]:
                        d=aj(relative+'logical-0'+delta+'.json')
                        require(d['status']==1 and d['spawn_calls']==0 and d['scratch_preserved'] is expired
                                and d['receipt']['cleanup']['removed'] is (not expired)
                                and d['receipt']['cleanup'].get('deadline_expired',False) is expired
                                and d['receipt']['cleanup_elapsed_seconds']==float(delta), 'Logical deadline boundary mismatch')
                    for name,error in [('missing-handler','Terminal cleanup deadline required'),('continued-work','Work continued after deadline'),('deleted-scratch','Owned scratch must remain unchanged')]:
                        d=aj(relative+name+'/oracle-rejection.json')
                        raw=aj(relative+name+'/logs/deadline-postflight-control.json')
                        require(d['error']==error and d['actual_timer_registered'] is True and d['retained_before_rejection'] is True
                                and raw['timer_disarmed'] is True and raw['handlers_restored'] is True, 'Oracle mutation not rejected/restored')
            counts[kind]=n
        # Logged exact shell commands/redirects distinguish fresh output from stale names in upload.
        for expected in ['python3 -B "$MIXER_ADOPTION_DIR/test_adoption.py" -v',
                         'python3 -B "$MIXER_SHARED_INPUT_DIR/test_materializer.py" -v',
                         'python3 -B "$GITHUB_WORKSPACE/'+NEW+'test_runner.py" -v',
                         'python3 -B -O "$GITHUB_WORKSPACE/'+NEW+'test_runner.py" -v',
                         'python3 -B "$GITHUB_WORKSPACE/'+NEW+'test_contracts.py" -v',
                         'python3 -B -O "$GITHUB_WORKSPACE/'+NEW+'test_contracts.py" -v',
                         'python3 -I -B -S "$GITHUB_WORKSPACE/'+FIX+'test_selection.py" -v']:
            require(log.count(expected)==1, 'Missing/duplicate current workflow control command '+expected)
        return {'recorded_tests':counts,'total_recorded_control_tests':sum(counts.values()),'fresh_evidence_bindings':bindings,
                'controls_rerun_by_auditor':0,'functional_deadline_observations':4,'logical_boundary_observations':6,
                'mutation_rejections':6,'fresh_descendant_custody_closures':2,'wall_latency_claim':False}

    def retained_failures():
        provenance=aj(NEW+'failure-provenance.json')
        raw=a(NEW+'original-ci-runner-controls.stderr')
        require(digest(raw)==provenance['stderr_sha256'] and b'0.200852' in raw and b'FAILED (failures=1)' in raw,
                'Original wall false-failure record changed')
        historical=aj(NEW+'evidence/final-runner-optimized-4adh1b9d/result.json')
        require(historical['tests']==36 and historical['successful'] is False and len(historical['failures'])==1,
                'Final local 35/36 failure lost')
        old=aj(NEW+'evidence/final-runner-optimized-4adh1b9d/logs/descendant-control/control.json')
        c=old['receipt']['commands'][0]
        require(c['pgid']==23663 and c['owned_group_gone'] is False and old['custody_hold'] is True
                and old['exception']['errno']==1, 'Historical EPERM/custody failure changed')
        local(PREFIX+'cache-deadline-control-review/REPORT.txt')
        return {'original_ci_failure':provenance, 'final_local_optimized':'35/36 EPERM; unresolved PGID23663',
                'historical_records_read_only_from_archive':True,'live_scratch_reads_or_process_probes':0,
                'all_prior_holds_preserved':[23663,20745,20770,20780,20817,20842,20851,20866,'FieldLog40802230894 PGID2424 PID2621','v5','frozen hosted lanes']}

    def baseline_and_scope():
        receipt = parse(local(PREFIX + 'baseline/cache-fixture/receipt.json'))
        require(digest(local(PREFIX + 'baseline/cache-fixture/receipt.json')) == '225732b76d54f583a2570ca1692e6c397c98c4124dce4c0d6d43edc3032f7491'
                and receipt['status'] == 'failed' and len(receipt['commands']) == 2
                and any(e['message'] == 'Actual compiler host/release not selected' for e in receipt['errors']), 'Original baseline failure changed')
        verbose = local(PREFIX + 'baseline/cache-fixture/compiler-identity.stdout').decode()
        require('release: 1.99.1\n' in verbose, 'Historical actual compiler drift observation differs')
        require(r['original_full_Debug_timeout_remains_failed'] is True
                and r['performance_equivalence_claimed'] is False
                and all(r[k] is False for k in ['GA_qualified', 'fullReplayAccepted', 'semanticMetricsValid', 'storedPrefixValidated', 'model_imported_or_evaluated']), 'Fixture evidence widened qualification scope')
        return {'baseline_run': 40974383080, 'baseline_status': 'failed', 'baseline_commands': 2,
                'baseline_policy_selected_release': '1.98.1', 'baseline_actual_verbose_release': '1.99.1',
                'fresh_exact_profile_release': '1.99.1', 'original_full_Debug_timeout': 'remains failed',
                'native_runtime_release_GA_qualification': False, 'blanket_envelope_qualification': False}

    def audit_negative_controls():
        count = 0
        def rejects(fn):
            nonlocal count
            try:
                fn()
            except (ValueError, KeyError):
                count += 1
                return
            raise ValueError('Independent auditor accepted perturbed evidence')
        text = output('host-debug-all', 'stdout')
        names = inv['methods']['host']
        methods(text, names, True)
        rejects(lambda: methods(text.replace('84 passed; 0 failed; 0 ignored', '83 passed; 0 failed; 1 ignored'), names, True))
        rejects(lambda: methods(text.replace(' ... ok', ' ... FAILED', 1), names, True))
        rejects(lambda: methods('', names, True))
        p = next(p for p in inv['api-contract']['probes'] if not p['expected_success'])
        raw = output('api-' + p['name'].replace('/', '_') + '-debug', 'stderr')
        source = a(RUN + 'pack/' + p['source'])
        negative(p, raw, source)
        rejects(lambda: negative(p, '', source))
        rejects(lambda: negative(p, raw.replace('"code":"' + p['code'] + '"', '"code":"E9999"'), source))
        rejects(lambda: negative(p, raw.replace('"is_primary":true', '"is_primary":false'), source))
        rejects(lambda: negative(p, raw, source + b'\n'))
        rejects(lambda: parse('{"same":1,"same":2}'))
        return {'independent_in_memory_rejection_controls': count, 'compiler_or_runner_execution': False}

    for name, fn in [('zip-custody', zip_binding), ('reviewed-admission-and-source-closure', reviewed_admission),
                     ('new-deadline-proposal-adoption', new_adoption), ('retained-failures-and-holds', retained_failures), ('exact-compiler-selection', identity), ('pack-retention-and-derived-source', pack_and_retention),
                     ('complete-unchanged-103-command-workload', workload), ('method-output-and-behavior', behavior),
                     ('actual-file-cases-layouts-and-private-controls', cases_and_layouts), ('positive-and-negative-api-controls', api_controls),
                     ('original-bounds-and-custody-cleanup', bounds_and_custody), ('source-and-tool-postflight-stability', postflight),
                     ('current-original-control-results', original_controls), ('baseline-failure-and-scope', baseline_and_scope),
                     ('independent-auditor-rejection-controls', audit_negative_controls)]:
        group(name, fn)
    after = rows(art)
    group('immutable-extracted-inputs', lambda: require(before == after, 'Artifact changed during audit') or {'unchanged_files': len(after)})
    if archive_reader:
        archive_reader.close()
    result['archive_reader_closed'] = archive_reader is None or archive_reader.fp is None
    result['runtime_guard_denials'] = DENIALS
    result['passed'] = not result['failures'] and not DENIALS
    result['verdict'] = 'ACCEPT exact 1.99.1 ordinary-CI host-fixture profile' if result['passed'] else 'REQUEST CHANGES actual-data qualification'
    result['summary'] = {'passed_groups': sum(g['passed'] for g in result['groups']), 'total_groups': len(result['groups']),
                         'fixture_commands': len(r['commands']), 'scope': 'Only this source, profile and fixture; prior baseline and all broader holds remain'}
    source_manifest = {'schema': 1, 'artifact_root': str(art), 'zip_sha256': ZIP_SHA, 'members': before,
                       'tree_sha256': digest(canonical(before))}
    source_manifest_bytes = json.dumps(source_manifest, sort_keys=True, indent=2).encode() + b'\n'
    result['extracted_source_manifest_sha256'] = digest(source_manifest_bytes)
    if args.freeze:
        snapshots['source-hash-manifest.json'] = source_manifest_bytes
        for name, raw in sorted(snapshots.items()):
            if name.startswith(('artifact/', 'actual-cases/')):
                continue
            p = HERE / 'evidence' / name
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                require(data(p) == raw, 'Frozen evidence changed; refusing overwrite ' + name)
            else:
                p.write_bytes(raw)
        frozen = rows(HERE / 'evidence')
        (HERE / 'frozen-manifest.json').write_text(json.dumps({'schema': 1, 'members': frozen,
            'tree_sha256': digest(canonical(frozen))}, sort_keys=True, indent=2) + '\n')
        result['frozen_evidence'] = {'files': len(frozen), 'bytes': sum(x['bytes'] for x in frozen),
                                     'tree_sha256': digest(canonical(frozen))}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
