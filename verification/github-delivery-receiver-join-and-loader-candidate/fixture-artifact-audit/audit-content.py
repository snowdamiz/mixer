#!/usr/bin/env python3
"""Independent raw-output/content audit of the one corrected full invocation."""
from datetime import datetime, timezone
import ast
import gzip
import stat
import types
import zipfile
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).absolute().parent
CANONICAL = HERE / 'sources/verification/swift-cache-state-ci'
RUN_PREFIX = 'runs/ci-40437321290-1'
DATA = {}
class ArchivePath:
    def __init__(self,path=''): self.path = str(path).strip('/')
    def __truediv__(self,other): return ArchivePath(self.path + '/' + str(other))
    def read_bytes(self): return DATA[self.path]
    def read_text(self): return self.read_bytes().decode()
    def stat(self): return types.SimpleNamespace(st_size=len(self.read_bytes()))
    def exists(self): return self.path in DATA or any(p.startswith(self.path + '/') for p in DATA)
    def __str__(self): return self.path
RUN = ArchivePath(RUN_PREFIX)
EXPECTED_RUNNER = 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'
EXPECTED_REVISION = '3e105c206c88e18461feb66bdecc0ddb1f2b0f0a'
EXPECTED_TREE = 'd23017135c7b34cb030c5b515f7da1bd4b870bb8'
APPEND = b'\n#[cfg(test)]\n#[path = "../selected_controls.rs"]\nmod selected_scalar_controls;\n\n#[cfg(test)]\n#[path = "../scalar_cursor_independent.rs"]\nmod scalar_cursor_independent;\n'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def unique(pairs):
    d = {}
    for k, v in pairs:
        assert k not in d
        d[k] = v
    return d

def strict(data):
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def validate_archive():
    archive = HERE / 'fixture-artifact.zip'
    raw = archive.read_bytes()
    metadata = strict((HERE / 'artifact-metadata.stdout').read_bytes())
    name = 'swift-cache-state-fixture-' + EXPECTED_REVISION + '-40437321290-1'
    artifact, = [a for a in metadata['artifacts'] if a['name'] == name]
    assert artifact['digest'] == 'sha256:' + hashlib.sha256(raw).hexdigest()
    assert artifact['workflow_run']['id'] == 40437321290 and artifact['workflow_run']['head_sha'] == EXPECTED_REVISION and not artifact['expired']
    member_rows = []
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            path = info.filename
            p = Path(path)
            assert path and not p.is_absolute() and '..' not in p.parts and '\\' not in path and str(p) == path
            assert path not in DATA and not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16) and not info.flag_bits & 1
            assert info.file_size <= 32 * 1024 * 1024
            data = z.read(info)
            assert len(data) == info.file_size
            DATA[path] = data
            member_rows.append({'path':path, 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()})
    assert sum(r['bytes'] for r in member_rows) <= 128 * 1024 * 1024
    (HERE / 'artifact-members.json').write_text(json.dumps(member_rows,indent=2)+'\n')
    custody = strict((HERE / 'source-custody.json').read_bytes())
    assert custody['source_revision'] == EXPECTED_REVISION
    prefix = 'verification/swift-cache-state-ci/'
    committed = {}
    for row in custody['paths']:
        data = (HERE / row['captured_path']).read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
        assert row['path'].startswith(prefix)
        path = row['path'][len(prefix):]
        assert DATA[path] == data
        committed[row['path']] = row
    assert len(committed) == len(custody['paths']) == 91
    assert len(selection_rows := strict((HERE / 'source-selection.stdout').read_bytes())['canonical_source_members']) == 90
    assert set(committed) - {r['path'] for r in selection_rows} == {prefix + 'README.md'}
    assert not ({r['path'] for r in selection_rows} - set(committed))
    assert not any('/scratch/' in n or n.endswith('/scratch') for n in DATA)
    assert all(n in {p[len(prefix):] for p in committed} or n.startswith('logs/') or n.startswith(RUN_PREFIX + '/') for n in DATA)
    selection = strict((HERE / 'source-selection.stdout').read_bytes())
    local = strict((HERE / 'comparison-final-decision.json').read_bytes())
    assert selection['closed_fixture_CI_integration_selected'] and selection['runner_source_bytes_unchanged']
    assert selection['canonical_runner_sha256'] == local['runner_sha256'] == EXPECTED_RUNNER
    assert selection['pack_manifest_sha256'] == local['pack_manifest_sha256'] == sha(CANONICAL / 'pack/manifest.json')
    assert selection['workflow_sha256'] == sha(HERE / 'source-workflow.stdout')
    assert all({k:committed[r['path']][k] for k in ('path','bytes','sha256')} == r for r in selection['canonical_source_members'])
    assert local['corrected_host_component_accepted'] and not local['full_target_native_or_GA_qualified']
    parsed = ast.parse((CANONICAL / 'check_cache_state.py').read_bytes())
    assignments = {node.targets[0].id:ast.literal_eval(node.value) for node in parsed.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('ACTIVE_SECONDS','CLEANUP_SECONDS','CHILD_SECONDS')}
    assert assignments == {'ACTIVE_SECONDS':600,'CLEANUP_SECONDS':60,'CHILD_SECONDS':60}
    controls_tree = ast.parse((CANONICAL / 'test_runner.py').read_bytes())
    expected_controls = sorted(n.name for c in controls_tree.body if isinstance(c,ast.ClassDef) and c.name == 'RunnerControls' for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
    stderr = DATA['logs/runner-controls.stderr'].decode()
    actual_controls = re.findall(r'^(test_\S+) \(__main__\.RunnerControls\.\1\) \.\.\. ok$',stderr,re.M)
    assert sorted(actual_controls) == expected_controls and len(actual_controls) == len(set(actual_controls)) == selection['focused_runner_controls'] == 29
    elapsed, = re.findall(r'^Ran 29 tests in ([0-9.]+)s$',stderr,re.M)
    assert stderr.endswith('\nOK\n')
    control_records = []
    for phase in ('postflight','retention'):
        record = strict(DATA['logs/deadline-' + phase + '-control.json'])
        receipt = record['receipt']
        assert record['scratch_preserved_at_assertion'] and record['owned_test_directory_removed_by_tearDown']
        assert receipt['status'] == 'failed' and not receipt['commands']
        assert receipt['runner']['sha256'] == EXPECTED_RUNNER
        assert receipt['active_deadline_seconds'] == 600 and receipt['cleanup_allowance_seconds'] == .05 and receipt['per_child_seconds'] == 60
        assert receipt['cleanup']['deadline_expired'] and not receipt['cleanup']['removed'] and receipt['cleanup']['recoverable_scratch'].endswith('/scratch')
        assert receipt['errors'] == [{'message':'Compiler launcher missing','phase':'active','type':'RuntimeError'}, {'message':'Fixed cleanup deadline exhausted','phase':'cleanup','type':'CleanupDeadlineExpired'}]
        assert record['state']['after_delay'] is False and record['state']['cleanup_entered'] is (phase == 'retention')
        if phase == 'postflight': assert receipt['postflight'] == {} and record['state']['pack_calls'] == 3
        assert receipt['cleanup_elapsed_seconds'] < .20
        control_records.append({'phase':phase,'zero_children':True,'terminal_cleanup_expiry_preserved':True,'cleanup_seconds':receipt['cleanup_elapsed_seconds'],'scratch_preservation_and_test_teardown':'Retained control receipt and passing exact test output; no remote filesystem inspection'})
    output = strict(DATA['logs/cache-state.stdout'])
    assert output == {'status':'passed-host-fixture-check','receipt':str(Path('/Users/runner/work/mixer/mixer/verification/swift-cache-state-ci') / RUN_PREFIX / 'receipt.json'),'errors':[]}
    assert DATA['logs/cache-state.stderr'] == DATA['logs/host.stderr'] == b''
    host_lines = DATA['logs/host.stdout'].decode().splitlines()
    assert host_lines[:2] == [EXPECTED_REVISION,EXPECTED_TREE] and host_lines[2].startswith('Python ') and host_lines[3].startswith('Darwin ') and host_lines[3].endswith(' arm64')
    summary = {'id':artifact['id'],'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'members':len(member_rows),'member_bytes':sum(r['bytes'] for r in member_rows),'metadata_digest_verified':True,'exact_committed_source_paths_bound':len(committed),'archive_extracted_or_executed':False}
    return summary, {'tests':len(actual_controls),'seconds':float(elapsed),'names':expected_controls,'deadline_failure_receipts':control_records}


def validate_postflight(receipt,retention,mode_results):
    assert receipt['active_deadline_seconds'] == 600 and receipt['cleanup_allowance_seconds'] == receipt['per_child_seconds'] == 60
    assert receipt['original_full_Debug_timeout_remains_failed'] and not receipt['performance_equivalence_claimed']
    assert receipt['machine'] == 'arm64' and receipt['cleanup']['other_project_or_native_discovery'] is False
    assert receipt['runner']['sha256'] == sha(CANONICAL / 'check_cache_state.py') == sha(RUN / 'executed-runner.py')
    commands = {r['name']:r for r in receipt['commands']}
    compiler = receipt['rustc']; identity = compiler['identity']
    assert identity['host'] == 'aarch64-apple-darwin' and identity['release'] in ('1.98.1','1.99.0')
    text = (RUN / 'commands/compiler-identity.stdout').read_text()
    assert text == compiler['version_verbose']
    assert text.splitlines()[0] == 'rustc ' + identity['release'] + ' (' + identity['commit-hash'][:9] + ' ' + identity['commit-date'] + ')'
    fields = dict(line.split(': ',1) for line in text.splitlines()[1:])
    assert fields == identity and identity['binary'] == 'rustc' and re.fullmatch('[0-9a-f]{40}',identity['commit-hash'])
    assert commands['compiler-sysroot']['argv'] == [compiler['launcher'],'--print','sysroot']
    assert (RUN / 'commands/compiler-sysroot.stdout').read_text().strip() == compiler['sysroot']
    assert commands['compiler-identity']['argv'] == [compiler['path'],'--version','--verbose']
    assert compiler['path'] == compiler['sysroot'] + '/bin/rustc'
    for command in receipt['commands']:
        assert command['new_session'] and command['pgid'] == command['pid'] and 0 < command['effective_timeout_seconds'] <= 60
        if command['name'].endswith('-compile') or command['name'].startswith(('library-','api-')) and not command['name'].endswith('-execute'):
            assert command['argv'][0] == compiler['path']
    for name,expected in [('source-revision',EXPECTED_REVISION),('source-revision-after',EXPECTED_REVISION),('source-tree',EXPECTED_TREE),('source-tree-after',EXPECTED_TREE)]:
        assert (RUN / ('commands/'+name+'.stdout')).read_text().strip() == expected
    manifest = strict((CANONICAL / 'pack/manifest.json').read_bytes())
    manifest_rows = manifest['members']
    assert len(manifest_rows) == len({r['path'] for r in manifest_rows}) == manifest['member_count']
    assert sum(r['bytes'] for r in manifest_rows) == manifest['total_bytes']
    assert hashlib.sha256(json.dumps(manifest_rows,sort_keys=True,separators=(',',':')).encode()).hexdigest() == manifest['tree_sha256'] == receipt['pack_tree_sha256']
    assert receipt['pack_manifest_sha256'] == sha(CANONICAL / 'pack/manifest.json')
    expected_derived = []
    for row in manifest_rows:
        if row['path'].startswith('source/'):
            data = (CANONICAL / 'pack' / row['path']).read_bytes()
            path = row['path'][len('source/'):]
            if path == 'library/cache_state.rs': data += APPEND
            expected_derived.append({'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    for name in ('selected_controls.rs','scalar_cursor_independent.rs'):
        data = (CANONICAL / 'pack/controls' / name).read_bytes()
        expected_derived.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    expected_derived.sort(key=lambda r:r['path'])
    assert expected_derived == receipt['derivative']['source_rows'] and len(expected_derived) == 19
    assert receipt['derivative']['append_utf8'].encode() == APPEND and receipt['derivative']['base_prefix_verified']
    post = receipt['postflight']
    assert set(post) == {'compiler','derived','launcher','output-ownership','pack','python','runner','runner-snapshot','snapshot'}
    wanted = {'pack':manifest['tree_sha256'],'snapshot':manifest['tree_sha256'],'runner':EXPECTED_RUNNER,'runner-snapshot':EXPECTED_RUNNER,'derived':expected_derived,'python':receipt['python']['sha256'],'compiler':compiler['sha256'],'launcher':compiler['launcher_sha256'],'output-ownership':receipt['output_ownership']}
    assert all(post[name] == {'passed':True,'observed':expected} for name,expected in wanted.items())
    assert receipt['output_ownership']['marker'] == strict((RUN / 'ownership.json').read_bytes())
    assert receipt['python']['version'].startswith(DATA['logs/host.stdout'].decode().splitlines()[2][len('Python '):])
    products = retention['compiler_products_hashed_before_removal']
    api = strict((CANONICAL / 'pack/inventories/api-contract.json').read_bytes())
    expected_products = set()
    for mode in ('debug','optimized'):
        expected_products.update(lane+'-'+mode for lane in ('host','producer','independent','controls'))
        expected_products.add('libcache_fixture-'+mode+'.rlib')
        expected_products.update('api-'+p['name'].replace('/','_')+'-'+mode for p in api['probes'] if p['expected_success'])
        assert mode_results[mode] == strict((HERE / 'comparison-final-decision.json').read_bytes())['modes'][mode]
        observed_api = receipt['modes'][mode]['api']
        assert [r['name'] for r in observed_api] == [p['name'] for p in api['probes']]
        for probe,observation in zip(api['probes'],observed_api):
            name='api-'+probe['name'].replace('/','_')+'-'+mode
            assert observation['expected_success'] == probe['expected_success'] and observation['compile_exit'] == commands[name]['exit']
            if probe['expected_success']:
                assert observation['executed'] and observation['binary_sha256'] == next(r['sha256'] for r in products if r['path']==name)
            else:
                pending=[strict(line) for line in (RUN / ('commands/'+name+'.stderr')).read_text().splitlines() if line.strip()];diagnostics=[]
                while pending:
                    d=pending.pop(0);pending.extend(d.get('children',[]))
                    if d.get('level') == 'error' and d.get('code') is not None:
                        diagnostics.append({'code':d['code']['code'],'message':d['message'],'primary':[s for s in d['spans'] if s['is_primary']]})
                assert observation['diagnostics'] == diagnostics
    assert {r['path'] for r in products} == expected_products and len(products) == 14
    assert not ({r['path'] for r in products} & {r['path'] for r in retention['files']})
    assert all(r['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}',r['sha256']) for r in products)
    assert receipt['cleanup']['files_hashed_before_removal'] == len(retention['files']) + len(products) + 1
    assert not any(p.startswith(RUN_PREFIX+'/scratch/') for p in DATA)


def main():
    archive_summary, controls = validate_archive()
    receipt = strict((RUN / 'receipt.json').read_bytes())
    assert receipt['status'] == 'passed-host-fixture-check' and receipt['active_checks_completed'] and receipt['errors'] == []
    assert receipt['source_tree'] == EXPECTED_TREE
    assert receipt['active_elapsed_seconds'] <= 600 and receipt['cleanup_elapsed_seconds'] <= 60 and receipt['elapsed_seconds'] <= 660
    assert receipt['source_revision'] == receipt['source_revision_after'] == EXPECTED_REVISION
    assert receipt['source_tree'] == receipt['source_tree_after'] and re.fullmatch('[0-9a-f]{40}', receipt['source_tree'])
    assert receipt['runner']['sha256'] == sha(RUN / 'executed-runner.py') == EXPECTED_RUNNER
    assert receipt['rustc']['identity']['release'] in ('1.98.1', '1.99.0') and receipt['rustc']['identity']['host'] == 'aarch64-apple-darwin'
    assert all(v['passed'] for v in receipt['postflight'].values()) and len(receipt['postflight']) == 9
    assert receipt['cleanup']['removed'] and receipt['cleanup']['groups_returned'] and not (RUN / 'scratch').exists()
    assert not any(receipt[k] for k in ['storedPrefixValidated', 'fullReplayAccepted', 'semanticMetricsValid', 'GA_qualified', 'model_imported_or_evaluated'])
    pack = RUN / 'pack'
    assert sha(pack / 'manifest.json') == '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'
    manifest = strict((pack / 'manifest.json').read_bytes())
    for row in manifest['members']:
        path = pack / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    methods = strict((pack / 'inventories/methods.json').read_bytes())
    layouts = strict((pack / 'inventories/layouts.json').read_bytes())
    cases = strict((pack / 'inventories/file-cases.json').read_bytes())
    api = strict((pack / 'inventories/api-contract.json').read_bytes())
    markers = strict((pack / 'inventories/control-markers.json').read_bytes())
    assert api == strict((CANONICAL / 'pack/inventories/api-contract.json').read_bytes())
    assert layouts == strict((CANONICAL / 'pack/inventories/layouts.json').read_bytes())
    expected_commands = ['compiler-sysroot', 'compiler-identity', 'source-revision', 'source-tree']
    for mode in ['debug', 'optimized']:
        for lane in ['host', 'producer', 'independent', 'controls']:
            expected_commands += [lane + '-' + mode + '-compile', lane + '-' + mode + '-list']
            groups = methods['producer_debug_partition'] if lane == 'producer' and mode == 'debug' else [{'name': 'all'}]
            expected_commands += [lane + '-' + mode + '-' + g['name'] for g in groups]
        expected_commands.append('library-' + mode)
        for probe in api['probes']:
            name = 'api-' + probe['name'].replace('/', '_') + '-' + mode
            expected_commands.append(name)
            if probe['expected_success']:
                expected_commands.append(name + '-execute')
    expected_commands += ['source-revision-after', 'source-tree-after']
    commands = receipt['commands']
    assert [r['name'] for r in commands] == expected_commands and len(commands) == 103
    by_name = {r['name']: r for r in commands}
    scratch = Path(receipt['commands'][0]['cwd']) / 'scratch'
    for row in commands:
        assert strict((RUN / 'commands' / (row['name'] + '.json')).read_bytes()) == row
        assert row['per_child_limit_seconds'] == 60 and row['per_stream_cap_bytes'] == 8 * 1024 * 1024
        assert row['child_returned'] and row['owned_group_gone'] and not row.get('descendants_outlived_child')
        assert not row['timed_out'] and not row['output_capped'] and row['effective_timeout_seconds'] <= 60
        for stream in ['stdout', 'stderr']:
            path = RUN / 'commands' / (row['name'] + '.' + stream)
            assert sha(path) == row[stream + '_sha256'] and path.stat().st_size <= 8 * 1024 * 1024
        temp = row['environment_overrides']
        assert len({temp[k] for k in ['TMPDIR', 'TMP', 'TEMP']}) == 1
        path = Path(temp['TMPDIR'])
        assert path.is_absolute() and '..' not in path.parts and path.is_relative_to(scratch)
    retention = strict((RUN / 'retention.json').read_bytes())
    retained = {r['path']: r for r in retention['files']}
    assert len(retained) == len(retention['files'])
    def content(row):
        path = RUN / row['content']
        assert sha(path) == row['retained_sha256']
        data = gzip.decompress(path.read_bytes()) if row['encoding'] == 'gzip' else path.read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
        return data
    for row in retention['files']:
        content(row)
    products = retention['compiler_products_hashed_before_removal']
    assert products == receipt['cleanup']['products_hashed_before_removal'] and len(products) == 14
    by_product = {p['path']: p for p in products}
    for row in receipt['derivative']['source_rows']:
        data = content(retained['derived/' + row['path']])
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    assert len(receipt['derivative']['source_rows']) == 19
    assert content(retained['derived/library/cache_state.rs']) == (pack / 'source/library/cache_state.rs').read_bytes() + APPEND
    def output(name, stream='stdout'):
        return (RUN / 'commands' / (name + '.' + stream)).read_text()
    def method_output(text, expected, filtered=None):
        if filtered is None:
            actual = [line[:-6] for line in text.splitlines() if line.endswith(': test')]
            assert re.findall(r'^(\d+) tests, (\d+) benchmarks$', text, re.M) == [(str(len(expected)), '0')]
        else:
            actual = re.findall(r'^test (\S+) \.\.\. ', text, re.M)
            assert re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out; finished in [^\n]+$', text, re.M) == [(str(len(expected)), '0', '0', '0', str(filtered))]
            assert len(re.findall(r'(?:^|\n)ok$| \.\.\. ok$', text, re.M)) == len(expected)
        assert len(actual) == len(set(actual)) == len(expected) and set(actual) == set(expected)
        return actual
    mode_results = {}
    boundaries = dict(zip(['Unavailable', 'ClosedFixtureObserved', 'CapCutUnknownTail', 'Refused', 'AnalysisLimited', 'InternalPoisoned', 'ApplicabilityUnavailable'], range(7)))
    reasons = dict(zip(['Observed', 'Steps', 'FramingUnavailable', 'FramingInvalid', 'EnvelopeRefused', 'EnvelopeUnavailable', 'Identity', 'Resident', 'Plan', 'Victim', 'Bytes', 'Token', 'Nonce', 'Invariant', 'FailureApplicability', 'IncompleteBoundary', 'InternalPoison', 'OutputUnavailable'], range(18)))
    for mode in ['debug', 'optimized']:
        method_invocations = 0; normalized = set(); complete_capture_cases = 0; API_spans = 0
        for lane in ['host', 'producer', 'independent', 'controls']:
            method_output(output(lane + '-' + mode + '-list'), methods[lane])
            groups = methods['producer_debug_partition'] if lane == 'producer' and mode == 'debug' else [{'name': 'all', 'methods': methods[lane], 'args': []}]
            observed = []
            for group in groups:
                name = lane + '-' + mode + '-' + group['name']
                text = output(name)
                observed += method_output(text, group['methods'], len(methods[lane]) - len(group['methods']))
                assert by_name[name]['exit'] == 0
                assert by_name[name]['argv'][1:] == [*group['args'], '--test-threads=1', '--nocapture']
                if lane in ['host', 'controls']:
                    actual_layouts = [{'type': t, 'bytes': int(n), 'align': int(a)} for t, n, a in re.findall(r'ACCOUNTING_LAYOUT (.+?) size=(\d+) align=(\d+)', text)]
                    assert actual_layouts == layouts['layouts'] and len(actual_layouts) == 23
                    prefix = lane + '-' + mode + '-all/cases/'
                    actual_names = {p[len(prefix):].split('/')[0] for p in retained if p.startswith(prefix)}
                    assert actual_names == {c['case'] for c in cases['cases']}
                    for case in cases['cases']:
                        case_prefix = prefix + case['case'] + '/'
                        assert {p[len(case_prefix):] for p in retained if p.startswith(case_prefix)} == {'input-0.bin', 'input-1.bin', 'input-2.bin', 'report.bin', 'result.txt'}
                        for filename, want in case['raw'].items():
                            actual = retained[case_prefix + filename]
                            assert actual['sha256'] == want['sha256'] and actual['bytes'] == want['bytes']
                        lines = content(retained[case_prefix + 'result.txt']).decode().splitlines()
                        assert len(lines) == 2 and lines[0] == case['result_first_line'] and lines[1].startswith('input_stamps_before_and_after=[')
                        match = re.search(r'cache_state: FixtureCacheStateObservationV1 \{ boundary: (\w+), reason: (\w+), extent: \[([^]]+)\]', lines[0])
                        projection = None
                        if match:
                            boundary, reason, extent = match.groups()
                            projection = [boundaries[boundary], reasons[reason]] + [int(v.strip()) for v in extent.split(',')]
                            assert len(projection) == 32
                        assert projection == case['actual_complete32'] and bool(match) == case['aggregate_present']
                        complete_capture_cases += int(match is not None)
                if lane == 'controls':
                    for key, value in markers.items():
                        assert re.findall(re.escape(key) + r'=([^\n]+)', text) == [value]
            assert len(observed) == len(set(observed)) == len(methods[lane]) and set(observed) == set(methods[lane])
            assert receipt['modes'][mode]['methods'][lane]['names'] == sorted(observed)
            assert receipt['modes'][mode]['methods'][lane]['binary_sha256'] == by_product[lane + '-' + mode]['sha256']
            method_invocations += len(observed)
            normalized |= {n.removeprefix('product::') for n in observed}
        assert method_invocations == 384 and len(normalized) == 132 and complete_capture_cases == 58
        for probe in api['probes']:
            name = 'api-' + probe['name'].replace('/', '_') + '-' + mode
            row = by_name[name]
            assert row['exit'] == (0 if probe['expected_success'] else 1)
            if probe['expected_success']:
                assert by_name[name + '-execute']['exit'] == 0 and name in by_product
                continue
            expected = {(p['byte_start'], p['byte_end']) for p in probe['primary_spans']}; seen = set()
            pending = [strict(line) for line in output(name, 'stderr').splitlines() if line.strip()]
            while pending:
                diagnostic = pending.pop()
                assert isinstance(diagnostic, dict) and isinstance(diagnostic.get('children', []), list)
                pending.extend(diagnostic.get('children', []))
                if diagnostic.get('level') != 'error':
                    continue
                code = diagnostic.get('code')
                if code is None:
                    assert re.fullmatch(r'aborting due to \d+ previous errors?(?:; \d+ warnings? emitted)?', diagnostic['message'])
                    continue
                assert code['code'] == probe['code'] and all(t in diagnostic['message'] for t in probe['message_contains'])
                primary = [s for s in diagnostic['spans'] if s['is_primary']]
                assert primary
                for span in primary:
                    pair = (span['byte_start'], span['byte_end'])
                    assert span['file_name'] == probe['source'] and pair in expected and pair not in seen
                    seen.add(pair)
            assert seen == expected
            API_spans += len(seen)
        assert API_spans == 38
        mode_results[mode] = {'method_invocations': method_invocations, 'distinct_methods': len(normalized),
            'lane_counts': {k: len(methods[k]) for k in ['host', 'producer', 'independent', 'controls']},
            'API_dispositions': 25, 'API_negative': 23, 'API_positive_executions': 2, 'API_primary_spans': API_spans,
            'captured_File_instances': 62, 'captured_complete32_instances': complete_capture_cases,
            'distinct_File_cases': 31, 'public_cases': 29, 'public_complete32': 27, 'public_outer_errors': 2,
            'private_poison_cases': 2, 'complete_accounting_layouts': 23}
    assert all(row['exit'] in [0, 1] for row in commands)
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': sha(Path(__file__)), 'runner_sha256': EXPECTED_RUNNER,
        'runner_receipt_sha256': sha(RUN / 'receipt.json'), 'artifact_sha256': archive_summary['sha256'], 'artifact': archive_summary, 'focused_controls': controls,
        'source_revision': EXPECTED_REVISION, 'source_tree': receipt['source_tree'],
        'compiler': receipt['rustc'], 'commands': 103, 'active_elapsed_seconds': receipt['active_elapsed_seconds'],
        'cleanup_elapsed_seconds': receipt['cleanup_elapsed_seconds'], 'elapsed_seconds': receipt['elapsed_seconds'],
        'max_child_seconds': max(r['elapsed_seconds'] for r in commands), 'modes': mode_results,
        'all103children_owned_TMP': True, 'normal_full_invocations': 1,
        'all_command_outputs_and_retained_bytes_hashed': True, 'retained_files_verified': len(retained),
        'derived_source_files_verified': 19, 'compiler_products_hashed_removed': 14,
        'postflight_checks_passed': len(receipt['postflight']), 'scratch_removed': True,
        'passed': True, 'limits': [
            'Actual recorded selected compiler and dedicated Actions host fixture closure only; no local reexecution',
            'Compiler, launcher and Python executable bytes are absent; their hashes and postflight identity checks are receipt claims bound to retained version/command output',
            'Fourteen compiler products were hashed before removal per receipt; binary bytes are absent and were not executed by this audit',
            'Scratch/process-group/temporary-directory cleanup is retained receipt evidence; no remote filesystem or process inspection was performed',
            'Historical full producer Debug60s timeout remains failed; no performance equivalence',
            'Global workflow status is recorded at audit snapshot only; no global CI success claim',
            'The isolated profile row adapter is absent from this canonical fixture and is not qualified by this CI artifact',
            'No general public File admission, canonical runtime, target/native, signing/store, immutable package FieldLog, customer operations or GA qualification']}
    validate_postflight(receipt, retention, mode_results)
    report['actual_compiler_release'] = receipt['rustc']['identity']['release']
    report['retained_logical_bytes_verified'] = sum(r['bytes'] for r in retention['files'])
    report['unique_content_members_verified'] = len({r['content'] for r in retention['files']})
    (HERE / 'full-audit.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'passed': True, 'commands': 103, 'method_invocations_each_mode': 384,
        'distinct_methods_each_mode': 132, 'API_each_mode': 25, 'complete_File_instances_each_mode': 58,
        'elapsed_seconds': receipt['elapsed_seconds'], 'max_child_seconds': report['max_child_seconds']}))

if __name__ == '__main__':
    main()
