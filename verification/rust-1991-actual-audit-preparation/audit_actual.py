#!/usr/bin/env python3
"""INERT PREPARATION: run only after root separately selects exact future evidence.

Reads local JSON/ZIP/files only. Never downloads or imports artifact contents.
The checked-in partition runner supplies only pure validators through a facade.
This program does not create a compiler-qualification or release acceptance.
"""
import argparse
import ast
import gzip
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from types import SimpleNamespace
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADOPTION = 'verification/envelope-rust-1991-default-ci-adoption'
HISTORICAL = 'verification/envelope-partition-default-ci-adoption'
RUNNER = 'verification/envelope-producer-timeout-experiment/candidate_runner.py'
POLICY = 'scripts/ci/check-analyzer-envelope.py'
PACK = 'verification/swift-envelope-ci-pack'
PINS = {
    'adoption_seal_sha256': '46757940a874b44ec89330d4bbbba9feea0681123685c063283b728c807d6994',
    'implementation_review_seal_sha256': '8f8aa69669b2b14c19fe4bcca0cfb1aae55ceb73e2e2bd52e22366c68d391ce8',
    'workflow_sha256': '5ce51236f178080e3301289513fa3f5a8313e3a3969b0bab3f2b1cd4668de7f5',
    'swift_job_sha256': '0e3ed51a0de31b06a00fa24d1276c58790de7ccc72c72bc9633869601acb4c3f',
    'compiler_selection_sha256': '07db30ea3a63e0a30b8b5762e18255a0e0bc720945ac813b6b7e017aec9edd5c',
    'runner_sha256': '32c98f00c18ce365306c166bc170a7369a89e26b25105858f36e82c2ef6515d5',
    'ordinary_policy_sha256': '4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c',
    'terminal_replay_sha256': '77051730ddf0dfd0731708da97d0e2c363a4a0033f3fa2421c9822deaaa321e4',
}
IDENTITY = {'binary': 'rustc', 'release': '1.99.1', 'host': 'aarch64-apple-darwin',
            'commit_hash': '58cf8f9c35b355199727627d07ae34a4e2846d67',
            'commit_date': '2026-10-13', 'llvm_version': '23.1.1'}
COMPILER_SHA = '1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1'
BOUNDS = {'archive_bytes': 67108864, 'members': 1000, 'member_bytes': 33554432,
          'expanded_archive_bytes': 134217728, 'original_retained_single_bytes': 134217728,
          'original_retained_total_bytes': 536870912}
CHECKS = []


def need(value, label):
    CHECKS.append({'label': label, 'passed': bool(value)})
    if not value:
        raise RuntimeError(label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(name):
    need(type(name) is str and 0 < len(name) <= 1024 and '\\' not in name and ':' not in name
         and all(ord(c) >= 32 and ord(c) != 127 for c in name), 'Canonical bounded path text')
    path = PurePosixPath(name)
    need(not path.is_absolute() and path.as_posix() == name and name != '.'
         and not any(p in {'.', '..', '.git'} for p in path.parts), 'Canonical relative path')
    return Path(name)


def raw(path, cap=BOUNDS['member_bytes']):
    need(path.is_absolute(), 'Absolute source/evidence path')
    for part in [*reversed(path.parents), path]:
        need(not part.is_symlink(), 'No symlink in evidence path')
    need(path.is_file() and stat.S_ISREG(path.stat().st_mode) and path.stat().st_size <= cap,
         'Bounded regular source/evidence file')
    return path.read_bytes()


def strict(data):
    def pairs(items):
        answer = {}
        for key, value in items:
            need(key not in answer, 'Unique JSON object keys')
            answer[key] = value
        return answer
    def nonfinite(value):
        raise RuntimeError('Non-finite JSON number refused')
    def finite_float(text):
        value = float(text)
        need(math.isfinite(value), 'Finite JSON numeric value')
        return value
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite, parse_float=finite_float)


def load(path):
    return strict(raw(path))


def tree(rows):
    return sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())


def rows_verify(base, rows):
    need(type(rows) is list and rows == sorted(rows, key=lambda r: r['path'])
         and len(rows) == len({r['path'] for r in rows}), 'Sorted unique source closure')
    for row in rows:
        need(set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int
             and row['bytes'] >= 0 and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Exact source row schema')
        data = raw(base / canonical(row['path']))
        need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'Bound source ' + row['path'])


def source_closure():
    own = load(HERE / 'preparation-seal.json')
    rows_verify(HERE, own['members'])
    need(own['tree_sha256'] == tree(own['members']), 'Preparation source seal')
    bindings = load(HERE / 'source-bindings.json')
    rows_verify(ROOT, bindings['members'])
    need(bindings['tree_sha256'] == tree(bindings['members']), 'Reviewed source closure digest')
    adoption = load(ROOT / ADOPTION / 'seal.json')
    dependencies = load(ROOT / ADOPTION / 'dependencies.json')
    need(sha(raw(ROOT / ADOPTION / 'seal.json')) == PINS['adoption_seal_sha256']
         and len(adoption['members']) == 19 and adoption['tree_sha256'] == tree(adoption['members']),
         'Frozen19member derivative seal')
    need(len(dependencies['members']) == 111 and dependencies['tree_sha256'] == tree(dependencies['members']),
         'Frozen111member dependency seal')
    rows_verify(ROOT / ADOPTION, adoption['members'])
    rows_verify(ROOT, dependencies['members'])
    source_defs = []
    for relative in (POLICY, RUNNER):
        text = raw(ROOT / relative).decode()
        source_defs.append({node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body
                            if isinstance(node, ast.FunctionDef)})
    for name in ('rustc_identity', 'select_compiler', 'select_host_target'):
        need(source_defs[0][name] == source_defs[1][name], 'Unchanged original policy definition ' + name)
    need(sha(raw(ROOT / '.github/workflows/verify.yml')) == PINS['workflow_sha256']
         and sha(raw(ROOT / ADOPTION / 'workflow/swift-job.yml')) == PINS['swift_job_sha256'],
         'Installed whole workflow and selected job')
    return bindings


def bound_json(row):
    need(set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str
         and Path(row['path']).is_absolute() and type(row['bytes']) is int
         and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Root evidence reference schema')
    data = raw(Path(row['path']), 2 * 1024 * 1024)
    need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'Exact root-retained metadata bytes')
    return strict(data)


def binding(path, artifact):
    value = load(path)
    need(set(value) == {'schema', 'status', 'root_selected', 'repository', 'revision', 'git_tree',
                        'run_id', 'run_attempt', 'job_id', 'artifact', 'pins', 'evidence', 'authority'},
         'Exact future binding fields')
    need(value['schema'] == 1 and type(value['schema']) is int and value['root_selected'] is True
         and value['status'] == 'selected-first-ordinary-result-data-review'
         and value['repository'] == 'snowdamiz/mixer', 'Root selected first ordinary result required')
    need(re.fullmatch('[0-9a-f]{40}', value['revision'] or '')
         and re.fullmatch('[0-9a-f]{40}', value['git_tree'] or ''), 'Exact delivered revision/tree required')
    for key in ('run_id', 'run_attempt', 'job_id'):
        need(type(value[key]) is int and value[key] > 0, 'Exact future integer ' + key)
    need(value['run_attempt'] == 1 and value['pins'] == PINS, 'First attempt and frozen source pins')
    need(value['authority'] == {'compiler_or_product_execution': False, 'retry_or_dispatch': False,
                               'native_ui_capture': False, 'release_or_ga': False}, 'No runtime or release authority')
    a = value['artifact']
    need(set(a) == {'id', 'name', 'bytes', 'sha256'} and type(a['id']) is int and a['id'] > 0
         and a['name'] == 'analyzer-envelope-host-' + value['revision']
         and type(a['bytes']) is int and 0 < a['bytes'] <= BOUNDS['archive_bytes']
         and re.fullmatch('[0-9a-f]{64}', a['sha256'] or ''), 'Exact future artifact identity')
    blob = raw(artifact, BOUNDS['archive_bytes'])
    need(len(blob) == a['bytes'] and sha(blob) == a['sha256'], 'Root selected exact retained archive')
    evidence = value['evidence']
    need(set(evidence) == {'delivery', 'run', 'job', 'artifact'}, 'All four root metadata bindings')
    delivery, run, job, meta = [bound_json(evidence[k]) for k in ('delivery', 'run', 'job', 'artifact')]
    need(all(type(record['schema']) is int for record in (delivery, run, job, meta))
         and type(delivery['first_matching_run_attempt']) is int
         and all(type(record['attempt']) is int for record in (run, job, meta)), 'Exact normalized metadata integer types')
    need(delivery == {'schema': 1, 'revision': value['revision'], 'git_tree': value['git_tree'],
         'workflow_sha256': PINS['workflow_sha256'], 'event': 'push', 'branch': 'main',
         'first_matching_run_id': value['run_id'], 'first_matching_run_attempt': 1}, 'Root exact delivery/first-run binding')
    need(run == {'schema': 1, 'id': value['run_id'], 'attempt': 1, 'head_sha': value['revision'],
         'event': 'push', 'branch': 'main', 'workflow_path': '.github/workflows/verify.yml',
         'status': 'completed', 'name': 'Owned engine checks'}, 'Exact completed ordinary run metadata')
    steps = ['Bind reviewed envelope and prospective compiler selection',
             'Guarded envelope and prospective compiler adoption controls',
             'Standalone analyzer envelope with prospectively selected compiler',
             'Verify prospective envelope adoption source postflight',
             'Preserve standalone analyzer envelope receipts']
    need(job == {'schema': 1, 'id': value['job_id'], 'run_id': value['run_id'], 'attempt': 1,
         'head_sha': value['revision'], 'name': 'swift', 'status': 'completed',
         'envelope_steps': [{'name': name, 'status': 'completed', 'conclusion': 'success'} for name in steps]},
         'Exact selected Swift job and all envelope step outcomes')
    need(meta == {'schema': 1, 'id': a['id'], 'run_id': value['run_id'], 'attempt': 1,
                 'head_sha': value['revision'], 'name': a['name'], 'bytes': a['bytes'],
                 'sha256': a['sha256'], 'expired': False}, 'Exact artifact run/revision metadata')
    return value, blob


def unpack(blob, out):
    payloads, directories = {}, set()
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        infos = archive.infolist()
        need(0 < len(infos) <= BOUNDS['members'] and len(infos) == len({i.filename for i in infos}),
             'Bounded unique ZIP members')
        need(sum(i.file_size for i in infos) <= BOUNDS['expanded_archive_bytes'], 'Bounded expanded ZIP')
        normalized = set()
        for info in infos:
            is_dir = info.is_dir()
            name = info.filename[:-1] if is_dir else info.filename
            path = canonical(name)
            need(name not in normalized, 'No file/directory ZIP aliases')
            normalized.add(name)
            mode = stat.S_IFMT(info.external_attr >> 16)
            need(mode in ({0, stat.S_IFDIR} if is_dir else {0, stat.S_IFREG})
                 and not info.flag_bits & 1
                 and info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                 and 0 <= info.file_size <= BOUNDS['member_bytes'], 'Regular bounded unencrypted ZIP member')
            data = archive.read(info)  # zipfile verifies the actual CRC, including empty directories.
            need(len(data) == info.file_size and (not is_dir or data == b''), 'ZIP payload length/CRC')
            if is_dir:
                directories.add(name)
            else:
                payloads[name] = data
        need(not any(parent.as_posix() in payloads for name in payloads
                     for parent in PurePosixPath(name).parents if parent.as_posix() != '.'), 'No ZIP file ancestor collision')
    for name, data in payloads.items():
        target = out / canonical(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
        if name.endswith('.json'):
            strict(data)  # Reject duplicate keys before unchanged replay's ordinary JSON reads.
    return payloads, directories


def checked_module(name, relative, expected):
    source = ROOT / relative
    need(sha(raw(source)) == expected, 'Checked-in module fingerprint ' + name)
    spec = importlib.util.spec_from_file_location(name, source)
    need(spec is not None and spec.loader is not None, 'Checked-in module loader')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def target_metadata(identity, actual, layouts):
    # DATA_ONLY: compare retained evidence, never recreate resolver observation.
    need(type(identity) is dict and identity == IDENTITY == actual['identity']
         and actual['sha256'] == COMPILER_SHA, 'Exact actual1.99.1 fingerprint')
    return {'actual_host': identity['host'], 'actual_release': identity['release'],
            'historical_layout_inventory_host': layouts['host'],
            'historical_layout_inventory_release': layouts['rust'],
            'selection_reference': ADOPTION + '/compiler-selection.json',
            'selection_sha256': PINS['compiler_selection_sha256'],
            'scope': 'selected prospective exact compiler; success requires this invocation full fresh checks',
            'other_target_qualification_inferred': False}


def verify_payloads(payloads, directories, out, selected):
    fixture_prefix, workspace_prefix = '_temp/analyzer-envelope/', 'mixer/mixer/'
    fixture, workspace = out / fixture_prefix, out / workspace_prefix
    r, start, finish = [load(fixture / name) for name in ('receipt.json', 'adapter-start.json', 'adapter-result.json')]
    runner = checked_module('data_only_partition', RUNNER, PINS['runner_sha256'])
    replay = checked_module('data_only_replay', ADOPTION + '/terminal_replay.py', PINS['terminal_replay_sha256'])
    # Public facade deliberately omits execute, Commands, select_compiler and load_runner.
    facade = SimpleNamespace(**{name: getattr(runner, name) for name in (
        'sha', 'verify_pack', 'producer_groups', 'verify_methods', 'verify_layouts',
        'verify_negative', 'member_path', 'OUTPUT_CAP', 'TOTAL_OUTPUT_CAP', 'FLAGS', 'PACK')})
    facade.select_host_target = lambda identity, layouts: target_metadata(identity, r['rustc'], layouts)
    layouts = load(fixture / 'pack/inventories/expected-host-layouts.json')
    need(r['rustc']['identity'] == IDENTITY and r['rustc']['sha256'] == COMPILER_SHA
         and runner.rustc_identity(raw(fixture / 'commands/rustc-verbose.stdout').decode()) == IDENTITY
         and r['rustc']['version_verbose'] == raw(fixture / 'commands/rustc-verbose.stdout').decode(),
         'Exact fresh compiler identity/verbose/fingerprint')
    need(r['compiler_target_selection'] == target_metadata(IDENTITY, r['rustc'], layouts), 'Recorded prospective target metadata')
    need(r['revision_before'] == r['revision_after'] == start['revision'] == selected['revision']
         and r['git_tree_before'] == r['git_tree_after'] == selected['git_tree'], 'Exact delivered source revision/tree')
    need(r['active_checks_completed'] is True and r['cleanup']['removed'] is True
         and r['cleanup']['children_and_owned_groups_returned'] is True
         and r['cleanup']['unrelated_process_or_native_discovery'] is False, 'Exact terminal cleanup booleans')
    need(r['cleanup']['identity'] == r['scratch_ownership']['identity']
         and r['cleanup']['marker'] == r['scratch_ownership']['marker']
         and r['output_ownership']['marker'] == load(fixture / 'output-ownership.json'), 'Recorded ownership identity/marker closure')
    for marker, purpose in ((r['cleanup']['marker'], 'mixer-fixture-envelope-ci-scratch'),
                            (r['output_ownership']['marker'], 'mixer-fixture-envelope-ci-output')):
        need(set(marker) == {'purpose', 'token'} and marker['purpose'] == purpose
             and re.fullmatch('[0-9a-f]{32}', marker['token']), 'Recorded owned marker schema')
    expected_snapshots = {
        'executed-adapter.py': ADOPTION + '/adopt_envelope.py',
        'executed-ordinary-policy.py': POLICY,
        'executed-terminal-replay.py': ADOPTION + '/terminal_replay.py',
        'executed-dependencies.json': ADOPTION + '/dependencies.json',
        'executed-adoption-seal.json': ADOPTION + '/seal.json',
        'executed-compiler-selection.json': ADOPTION + '/compiler-selection.json',
        'executed-swift-job.yml': ADOPTION + '/workflow/swift-job.yml',
    }
    need(set(start['source_snapshots']) == set(expected_snapshots), 'Exact seven adapter snapshots')
    for name, relative in {**expected_snapshots, 'executed-runner.py': RUNNER}.items():
        need(raw(fixture / name) == raw(ROOT / relative), 'Executed snapshot ' + name)
        if name in expected_snapshots:
            need(start['source_snapshots'][name] == sha(raw(ROOT / relative)), 'Snapshot admission ' + name)
    need(start['fixture_invocations_admitted'] == 1
         and start['ordinary_functions_reused_exactly'] == {'rustc_identity': True, 'select_compiler': False, 'select_host_target': False}
         and start['prospective_selection_sha256'] == PINS['compiler_selection_sha256'], 'New adapter one-invocation attribution')
    need(finish['fixture_return_status'] == 0 and finish['adapter_exception'] is None
         and finish['errors'] == [] and finish['actual_compiler'] == r['rustc']
         and finish['fixture_status'] == r['status'] and finish['exact_compiler_qualified'] is False
         and finish['prospective_selection_sha256'] == PINS['compiler_selection_sha256'], 'Adapter terminal success without authority')
    dependencies, seal = load(ROOT / ADOPTION / 'dependencies.json'), load(ROOT / ADOPTION / 'seal.json')
    proof = {'schema': 1, 'adoption_seal_sha256': PINS['adoption_seal_sha256'],
             'adoption_tree_sha256': seal['tree_sha256'], 'dependencies_sha256': sha(raw(ROOT / ADOPTION / 'dependencies.json')),
             'workflow_job_sha256': PINS['swift_job_sha256'], 'installed_job_verified': True,
             'prospective_selection_sha256': PINS['compiler_selection_sha256'], 'exact_compiler_qualified': False,
             'compiler_policy': dependencies['compiler_policy'], 'fixture_source': dependencies['fixture_source']}
    need(all(start.get(k) == v for k, v in proof.items()) and finish['source_postflight'] == proof, 'Adapter exact preflight/postflight proof')
    expected_files = set()
    for relative in (ADOPTION, HISTORICAL):
        packet_seal = load(ROOT / relative / 'seal.json')
        for name in [row['path'] for row in packet_seal['members']] + ['seal.json']:
            path = workspace_prefix + relative + '/' + name
            need(payloads.get(path) == raw(ROOT / relative / name), 'Archived immutable packet ' + relative + '/' + name)
            expected_files.add(path)
    need(payloads.get(workspace_prefix + '.github/workflows/verify.yml') == raw(ROOT / '.github/workflows/verify.yml'), 'Archived installed workflow')
    expected_files.add(workspace_prefix + '.github/workflows/verify.yml')
    logs = workspace / ADOPTION / 'logs'
    for label in ('preflight', 'postflight'):
        need(load(logs / (label + '.stdout')) == proof and raw(logs / (label + '.stderr')) == b'', 'Always-run source log ' + label)
    controls, stderr = load(logs / 'controls.stdout'), raw(logs / 'controls.stderr').decode()
    need(controls['tests'] == 33 and controls['passed'] is True and controls['failures'] == controls['errors'] == controls['skipped'] == 0
         and controls['denied_operation_attempts'] == [] and controls['control_scratch_absent'] is True
         and controls['compiler_producer_product_native_runtime_runs'] == 0
         and controls['python'] == r['python']['version'] and controls['interpreter'] == r['python']['path'], 'Actual hosted33synthetic controls attribution')
    expected_controls = [n.name for n in ast.walk(ast.parse(raw(ROOT / ADOPTION / 'test_adoption.py')))
                         if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
    observed_controls = re.findall(r'^(test_\S+) \([^\n]+\) \.\.\. ok$', stderr, re.M)
    need(len(expected_controls) == len(observed_controls) == 33 and sorted(observed_controls) == sorted(expected_controls)
         and len(re.findall(r'^Ran 33 tests in [0-9.]+s$', stderr, re.M)) == 1
         and re.findall(r'^OK$', stderr, re.M) == ['OK'], 'All33hosted control terminals')
    logged = load(logs / 'fixture.stdout')
    need(logged['status'] == r['status'] and logged['errors'] == []
         and logged['receipt'].endswith('/analyzer-envelope/receipt.json') and raw(logs / 'fixture.stderr') == b'', 'Hosted fixture terminal log')
    expected_files.update(workspace_prefix + ADOPTION + '/logs/' + label + '.' + stream
                          for label in ('preflight', 'controls', 'fixture', 'postflight') for stream in ('stdout', 'stderr'))
    terminal = replay.replay(fixture, {'revision': selected['revision'], 'compiler': r['rustc']['path'],
                                     'compiler_sha256': COMPILER_SHA}, facade)
    need(terminal == finish['terminal_replay'], 'Unchanged terminal replay equals hosted result')
    manifest = load(fixture / 'pack/manifest.json')
    manifest_digest = sha(raw(fixture / 'pack/manifest.json'))
    need(r['source_tree_digest'] == manifest['tree_sha256']
         and r['pack_preflight'] == {'manifest_sha256': manifest_digest, 'tree_sha256': manifest['tree_sha256'],
                                    'member_count': 86, 'bytes': 8330464}
         and r['candidate_base_runner_sha256'] == PINS['ordinary_policy_sha256'], 'Recorded immutable source/runner lineage')
    pack_state = {'manifest_sha256': manifest_digest, 'tree_sha256': manifest['tree_sha256'], 'member_count': 86}
    postflight = r['postflight']
    need(all(record['passed'] is True for record in postflight.values()), 'Exact successful postflight booleans')
    for name in ('pack', 'snapshot'):
        need(postflight[name] == {'passed': True, 'observed': pack_state}, 'Recorded pack postflight ' + name)
    snapshot_rows = sorted([*manifest['members'], {'path': 'manifest.json', 'bytes': len(raw(fixture / 'pack/manifest.json')),
                                                  'sha256': manifest_digest}], key=lambda row: row['path'])
    need(postflight['snapshot-observed'] == {'passed': True, 'observed': snapshot_rows}, 'Complete recorded pack snapshot postflight')
    need(postflight['runner'] == {'passed': True, 'observed': {'path': r['runner']['path'], 'sha256': PINS['runner_sha256']}}, 'Recorded executed runner postflight')
    methods = load(fixture / 'pack/inventories/expected-methods.json')
    for lane, key, count, source in (
            ('producer', 'producer', 78, 'source/producer/independent_tests.rs'),
            ('independent', 'independent_exact_source', 14, 'source/independent/source/analyzer.rs')):
        binary = r['test_binaries'][lane]
        need(len(methods[key]['names']) == count and binary['listed'] == binary['executed'] == methods[key]['names']
             and binary['source'] == source and binary['source_pack_tree'] == manifest['tree_sha256'], 'Exact list/execute/source identity ' + lane)
    groups = runner.producer_groups(methods['producer']['names'])
    api = load(fixture / 'pack/inventories/expected-api.json')
    rows = {row['name']: row for row in r['commands']}
    remote_root = rows['revision-before']['cwd']
    remote_out = rows['rustc-verbose']['cwd']
    remote_pack, scratch = remote_out + '/pack', remote_out + '/scratch'
    actual = r['rustc']
    need(r['runner']['path'] == remote_root + '/' + RUNNER
         and postflight['runner-snapshot'] == {'passed': True, 'observed': {'path': remote_out + '/executed-runner.py', 'sha256': PINS['runner_sha256']}}, 'Recorded runner path/snapshot postflight')
    for name, path, digest in [('python', r['python']['resolved_path'], r['python']['sha256']),
                              ('compiler', actual['path'], COMPILER_SHA),
                              ('launcher', actual['launcher_target'], actual['launcher_sha256'])]:
        need(type(path) is str and path.startswith('/') and re.fullmatch('[0-9a-f]{64}', digest)
             and postflight[name] == {'passed': True, 'observed': {'path': path, 'sha256': digest}}, 'Recorded tool postflight ' + name)
    argv = {'revision-before': ['git', 'rev-parse', 'HEAD'], 'git-tree-before': ['git', 'rev-parse', 'HEAD^{tree}'],
            'revision-after': ['git', 'rev-parse', 'HEAD'], 'git-tree-after': ['git', 'rev-parse', 'HEAD^{tree}'],
            'python-version': [r['python']['path'], '--version'],
            'compiler-sysroot-selection': [actual['launcher'], '--print', 'sysroot'],
            'rustc-verbose': [actual['path'], '--version', '--verbose']}
    base = [actual['path'], '--edition=2024', '-Dwarnings']
    argv['library-compile'] = [*base, '--crate-name', 'mixer_absence', '--crate-type=rlib', 'source/library/analyzer.rs', '-o', scratch + '/libmixer_absence.rlib']
    for lane in ('producer', 'independent'):
        argv[lane + '-compile'] = list(map(str, runner.test_compile_argv(actual['path'], lane, scratch + '/' + lane + '-tests')))
        argv[lane + '-list'] = [scratch + '/' + lane + '-tests', '--list']
    argv['independent-execute'] = [scratch + '/independent-tests', '--test-threads=1', '--nocapture']
    for group in groups:
        argv['producer-' + group['name']] = [scratch + '/producer-tests', *group['args'], '--test-threads=1', '--nocapture']
    external = [*base, '--extern', 'mixer_absence=' + scratch + '/libmixer_absence.rlib']
    argv['api-positive'] = [*external, 'api/positive.rs', '-o', scratch + '/api-positive']
    for probe in api['negative']:
        name = Path(probe['path']).stem
        argv['api-negative-' + name] = [*external, '--error-format=json', probe['path'], '-o', scratch + '/api-negative-' + name]
    need(set(argv) == set(rows) and len(rows) == 40, 'Exact original40argv roster')
    for name, row in rows.items():
        expected_cwd = remote_root if name.startswith(('revision-', 'git-tree-')) or name == 'compiler-sysroot-selection' else remote_out if name in {'python-version', 'rustc-verbose'} else remote_pack
        cap = 120 if name.startswith('producer-') and name not in {'producer-compile', 'producer-list'} or name == 'independent-execute' else 60 if name.endswith('-compile') or name.startswith('api-') else 15
        need(row['argv'] == argv[name] and row['cwd'] == expected_cwd, 'Exact command argv/cwd ' + name)
        need(type(row['pid']) is int and row['pid'] > 0 and type(row['owned_pgid']) is int and row['pid'] == row['owned_pgid']
             and all(row[key] is True for key in ('child_returned', 'owned_group_gone'))
             and all(row[key] is False for key in ('timed_out', 'custody_hold', 'output_capped'))
             and all(row['pipe_eof'][key] is True for key in ('stdout', 'stderr'))
             and row.get('owned_group_killed', False) is False and row.get('descendants_outlived_direct_child', False) is False
             and type(row['exit']) is int and type(row['elapsed_seconds']) in {int, float}
             and type(row['timeout_seconds']) in {int, float} and 0 <= row['elapsed_seconds'] < row['timeout_seconds'] <= cap
             and row['per_stream_cap_bytes'] == 8388608 and row['aggregate_cap_bytes'] == 67108864, 'Recorded custody/time/capture bounds ' + name)
        for stream in ('stdout', 'stderr'):
            info = row[stream]
            need(set(info) == {'path', 'bytes', 'sha256'} and type(info['bytes']) is int
                 and info['bytes'] >= 0 and re.fullmatch('[0-9a-f]{64}', info['sha256']), 'Exact capture metadata ' + name + '/' + stream)
        env = row['environment']
        need(row['environment_policy'] == 'allowlist' and row['caller_injection_variables_removed'] == list(runner.REMOVED_ENV)
             and set(env) <= {'PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT', 'RUSTUP_AUTO_INSTALL', 'LC_ALL', 'TMP', 'TEMP',
                              'REVIEW_SCRATCH', 'MIXER_ANALYZER_LIBRARY_HISTORICAL', 'MIXER_ANALYZER_LIBRARY_TEST_SCRATCH', 'MIXER_ENVELOPE_SCRATCH', 'MIXER_REVIEW_SCRATCH'}
             and env['RUSTUP_AUTO_INSTALL'] == '0' and env['LC_ALL'] == 'C', 'Original environment/warnings policy ' + name)
    need(r['fixed_independent_test_lint_selection'] == {
         'reference': 'verification/swift-envelope-ci-root-review/test-lint-selection-amendment.json',
         'sha256': '1684fb9a329809c8c5bb9a4af20bbceaa7e4d68123a77e54a1115e3534277e52',
         'flags': ['-Dwarnings', '-A', 'non_snake_case'],
         'scope': 'independent --test crate only; exact uppercase G method name preserved'}, 'Original fixed independent warning exception')
    for name, value in [('revision-before', selected['revision']), ('revision-after', selected['revision']),
                        ('git-tree-before', selected['git_tree']), ('git-tree-after', selected['git_tree'])]:
        need(raw(fixture / 'commands' / (name + '.stdout')) == (value + '\n').encode(), 'Source command capture ' + name)
    need(raw(fixture / 'commands/compiler-sysroot-selection.stdout').decode().strip() == actual['sysroot']
         and actual['path'] == actual['sysroot'] + '/bin/rustc'
         and actual['requested'] == actual['launcher'] == start['requested_rustc'], 'Original launcher/sysroot resolution data')
    for group in groups:
        env = rows['producer-' + group['name']]['environment']
        owned = scratch + '/producer-partitions/' + group['name']
        need(env['TMPDIR'] == env['TMP'] == env['TEMP'] == owned + '/tmp'
             and env['MIXER_ANALYZER_LIBRARY_TEST_SCRATCH'] == owned + '/framing'
             and env['MIXER_ENVELOPE_SCRATCH'] == owned + '/envelope'
             and env['MIXER_REVIEW_SCRATCH'] == owned + '/review'
             and env['MIXER_ANALYZER_LIBRARY_HISTORICAL'] == remote_pack + '/inputs/historical', 'Separate producer group scratch ' + group['name'])
    need(rows['independent-execute']['environment']['REVIEW_SCRATCH'] == scratch + '/independent-files', 'Independent scratch binding')
    completed = [{'name': g['name'], 'methods': g['methods'], 'command': 'producer-' + g['name'],
                  'stdout': rows['producer-' + g['name']]['stdout']} for g in groups]
    partition = r['producer_partition']
    need(partition['plan'] == groups and partition['completed_groups'] == completed
         and partition['expected_methods'] == methods['producer']['names'] and partition['original_method_order_preserved'] is True
         and partition['complete_disjoint_coverage'] is True
         and partition['binary_sha256'] == r['test_binaries']['producer']['sha256']
         and partition['source_pack_tree'] == manifest['tree_sha256']
         and (partition['per_command_seconds'], partition['aggregate_active_seconds'], partition['per_stream_cap_bytes'], partition['all_command_streams_cap_bytes']) == (120, 480, 8388608, 67108864), 'All18disjoint group records and limits')
    combined = '\n'.join(raw(fixture / 'commands' / ('producer-' + g['name'] + '.stdout')).decode() for g in groups)
    need(r['host_layouts'] == runner.verify_layouts(combined, layouts)
         and r['fresh_candidate_comparisons_against_reused_oracles'] == 21714, 'Recorded32layouts and21714comparisons')
    need(r['api']['positive'] is True and set(r['api']['negative']) == {Path(p['path']).stem for p in api['negative']}, 'Positive and eight negative API records')
    for probe in api['negative']:
        name = Path(probe['path']).stem
        actual_diag = runner.verify_negative(name, raw(fixture / 'commands' / ('api-negative-' + name + '.stderr')).decode(),
            fixture / 'pack' / probe['path'], fixture / 'scratch' / ('api-negative-' + name), rows['api-negative-' + name])
        need(actual_diag == r['api']['negative'][name], 'Recorded intended API diagnostic ' + name)
    retention = load(fixture / 'retention.json')
    need(len(retention['test_files']) == 92 and set(retention['compiler_products']) == {'libmixer_absence.rlib', 'producer-tests', 'independent-tests', 'api-positive'}, '92payloads and four product records')
    original_total = 0
    for name, record in retention['test_files'].items():
        canonical(name)
        expected_path = 'retained/' + name + ('.gz' if record['encoding'] == 'gzip' else '')
        need(set(record) == {'path', 'encoding', 'bytes', 'sha256', 'original_bytes', 'original_sha256'}
             and record['encoding'] in {'identity', 'gzip'} and record['path'] == expected_path
             and type(record['original_bytes']) is int and 0 <= record['original_bytes'] <= BOUNDS['original_retained_single_bytes'], 'Retained payload path/encoding/size')
        data = raw(fixture / canonical(record['path']))
        need(len(data) == record['bytes'] and sha(data) == record['sha256'], 'Encoded retained payload ' + name)
        stream = gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') if record['encoding'] == 'gzip' else io.BytesIO(data)
        count, digest = 0, hashlib.sha256()
        with stream:
            while True:
                block = stream.read(65536)
                if not block:
                    break
                count += len(block)
                need(count <= record['original_bytes'], 'Bounded retained decompression')
                digest.update(block)
        original_total += count
        need(count == record['original_bytes'] and digest.hexdigest() == record['original_sha256']
             and original_total <= BOUNDS['original_retained_total_bytes'], 'Original retained payload ' + name)
    for name, record in retention['compiler_products'].items():
        need(set(record) == {'path', 'bytes', 'sha256'} and record['path'] == name
             and type(record['bytes']) is int and record['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'Compiler product record ' + name)
    need(r['active_deadline_seconds'] == 480 and r['retention_cleanup_allowance_seconds'] == 60
         and r['output_limits'] == {'per_stream_bytes': 8388608, 'all_commands_bytes': 67108864}
         and 0 <= r['active_elapsed_seconds'] < 480 and 0 <= r['elapsed_seconds'] - r['active_elapsed_seconds'] < 60, 'Original active and cleanup budgets')
    expected_files.update(fixture_prefix + name for name in ['receipt.json', 'output-ownership.json', 'adapter-start.json', 'adapter-result.json', 'retention.json', *expected_snapshots, 'executed-runner.py'])
    expected_files.update(fixture_prefix + 'pack/' + name for name in ['manifest.json', *[x['path'] for x in manifest['members']]])
    expected_files.update(fixture_prefix + 'commands/' + name + suffix for name in rows for suffix in ('.json', '.stdout', '.stderr'))
    expected_files.update(fixture_prefix + record['path'] for record in retention['test_files'].values())
    need(set(payloads) == expected_files, 'Exact full archive file closure; no scratch or unreviewed content')
    allowed_dirs = {p.as_posix() for name in expected_files for p in PurePosixPath(name).parents if p.as_posix() != '.'}
    need(directories <= allowed_dirs, 'Only expected archive directories; scratch absent')
    return {'terminal_replay': terminal, 'archive_files': len(payloads), 'retained_original_bytes': original_total,
            'recorded_direct_returns': 40, 'recorded_owned_group_absences': 40, 'recorded_stdout_stderr_eof_pairs': 40}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-binding', type=Path, required=True)
    parser.add_argument('--root-binding-sha256', required=True)
    parser.add_argument('--preparation-seal-sha256', required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.dont_write_bytecode == 1,
         'Isolated no-site/no-bytecode interpreter required')
    seal_bytes = raw(HERE / 'preparation-seal.json')
    need(re.fullmatch('[0-9a-f]{64}', args.preparation_seal_sha256)
         and sha(seal_bytes) == args.preparation_seal_sha256, 'Separately selected auditor source seal')
    guard_row = next(row for row in strict(seal_bytes)['members'] if row['path'] == 'deny_runtime.py')
    need(sha(raw(HERE / 'deny_runtime.py')) == guard_row['sha256'], 'Selected guard source before import')
    # This trusted local guard loads before either checked-in subject, never from ZIP.
    guard_spec = importlib.util.spec_from_file_location('data_only_guard', HERE / 'deny_runtime.py')
    guard = importlib.util.module_from_spec(guard_spec)
    guard_spec.loader.exec_module(guard)
    guard.install(HERE)
    need(args.out.is_absolute() and args.out == args.out.resolve(strict=False)
         and args.out.is_relative_to(HERE / 'local') and not args.out.exists(), 'Fresh owned local audit output')
    need(sha(raw(args.root_binding)) == args.root_binding_sha256
         and re.fullmatch('[0-9a-f]{64}', args.root_binding_sha256), 'Separately selected root binding hash')
    before = source_closure()
    args.out.mkdir(parents=True, exist_ok=False)
    result = {'schema': 1, 'data_checks_passed': False, 'compiler_qualified': False,
              'acceptance_record_written': False, 'runtime_or_release_authority': False,
              'scope': 'DATA_ONLY first ordinary result review; root separately owns actual acceptance',
              'custody_limit': 'Checks recorded runner returns/groups/stream EOF only; no independent kernel trace, provider disposal, transport EOF or external lease closure inferred',
              'python': {'executable': sys.executable, 'version': sys.version},
              'command': sys.argv, 'root_binding_sha256': args.root_binding_sha256,
              'preparation_seal_sha256': args.preparation_seal_sha256}
    try:
        selected, blob = binding(args.root_binding, args.artifact)
        payloads, directories = unpack(blob, args.out / 'extracted')
        result.update(verify_payloads(payloads, directories, args.out / 'extracted', selected))
        result['subject'] = {k: selected[k] for k in ('repository', 'revision', 'git_tree', 'run_id', 'run_attempt', 'job_id', 'artifact', 'pins')}
        result['data_checks_passed'] = True
    except BaseException as error:
        result['failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        try:
            need(source_closure() == before, 'Checked-in source closure unchanged after audit')
            need(guard.DENIED == [], 'Zero active-runtime attempts')
        except BaseException as error:
            result['data_checks_passed'] = False
            result['source_postflight_failure'] = {'type': type(error).__name__, 'message': str(error)}
        result['denied_operations'] = guard.DENIED
        result['checks'] = CHECKS
        (args.out / 'data-audit.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('data_checks_passed', 'compiler_qualified', 'acceptance_record_written', 'denied_operations')}, sort_keys=True))
    return 0 if result['data_checks_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
