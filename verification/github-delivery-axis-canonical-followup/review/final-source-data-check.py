import sys
ROOT = '/Users/andreyyurlov/Documents/dev/mixer/verification/github-delivery-axis-canonical-followup/'
def guard(event, args):
    if event == 'import' and args[0].split('.')[0] in ('subprocess', 'socket', 'ctypes', 'signal', 'select', 'selectors', 'asyncio', 'multiprocessing', 'threading', 'pty', 'http', 'urllib', 'ssl', 'resource', 'mmap'):
        raise RuntimeError('DENY active module import: ' + args[0])
    if event.startswith('os.') and event not in ('os.listdir', 'os.scandir', 'os.walk'):
        raise RuntimeError('DENY active OS audit API: ' + event)
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, int):
            raise RuntimeError('DENY fd open')
        p = str(path)
        write = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & 3 != 0)
        if write:
            raise RuntimeError('DENY file mutation')
        if not (p.startswith(ROOT) or (p.startswith('/Users/andreyyurlov/Documents/dev/mixer/') and '/.git/' not in p) or p.startswith(sys.base_prefix + '/lib/') or p.startswith('/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/') or p.startswith('/Library/Frameworks/Python.framework/')):
            raise RuntimeError('DENY file read: ' + p)
    if event.startswith(('subprocess.', 'socket.', 'ctypes.', 'pty.', 'ssl.', 'http.', 'urllib.')) or event in ('os.system','os.fork','os.forkpty','os.posix_spawn','os.spawn','os.exec','os.kill','os.killpg','os.startfile','os.chdir','os.fchdir','os.remove','os.unlink','os.rename','os.rmdir','os.mkdir','os.link','os.symlink','os.truncate','os.chmod','os.chown','os.utime','os.putenv','os.unsetenv','signal.signal','signal.pthread_kill','mmap.__new__'):
        raise RuntimeError('DENY active API: ' + event)
    if event == 'exec':
        filename = args[0].co_filename
        if not (filename.startswith(sys.base_prefix + '/lib/') or filename.startswith('/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/') or filename.startswith('/Library/Frameworks/Python.framework/') or filename.startswith('<frozen ') or (filename == '<string>' and sys._getframe(1).f_code.co_filename.startswith(sys.base_prefix + '/lib/') and sys._getframe(1).f_code.co_name == 'namedtuple')):
            raise RuntimeError('DENY source execution: ' + filename)
sys.addaudithook(guard)

import ast
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

REPO = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = REPO / 'verification/github-delivery-axis-canonical-followup'
SELECTION_PATH = 'verification/android-axis-canonical-selection-2026-10-29/selection.json'
SELECTION_SHA = '97268470779866b15ee22eea2ffd9e66a01cb266ad9980ef652ca6ade2b8d91b'
BASE = '2c751cbbc300efc9aa766b5d4add648610ca0341'
TREE = 'f2df6833ee8e9ce85306210b63dc35d45747fa0d'
REFUSAL = b'raise SystemExit("UNBOUND SOURCE TEMPLATE: exact source/argv review and root materialization are required")\n'
CACHE = {}
TOTAL = 0

def data(path):
    global TOTAL
    path = Path(path)
    key = str(path)
    if key not in CACHE:
        with path.open('rb') as handle:
            raw = handle.read(2_000_001)
        assert len(raw) <= 2_000_000, ('file bound', key)
        TOTAL += len(raw)
        assert TOTAL <= 32_000_000, 'aggregate source/data bound'
        CACHE[key] = raw
    return CACHE[key]

def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, ('duplicate JSON key', key)
        result[key] = value
    return result

def value(path):
    return json.loads(data(path), object_pairs_hook=unique)

def identity(path):
    path = Path(path)
    st = path.lstat()
    assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), str(path)
    raw = data(path)
    return {'path': str(path.relative_to(REPO)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def exact(row):
    assert identity(REPO / row['path']) == row
    return row

def constants(tree):
    return {target.id: node.value for node in tree.body if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)}

def functions(tree):
    return {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}

def source(tree_text, node):
    return ast.get_source_segment(tree_text, node)

selection_row = identity(REPO / SELECTION_PATH)
assert selection_row == {'path': SELECTION_PATH, 'bytes': 73463, 'sha256': SELECTION_SHA}
S = value(REPO / SELECTION_PATH)
assert S['schema'] == 1 and S['baseline'] == {'head': BASE, 'tree': TREE}
assert S['repository'] == 'snowdamiz/mixer' and S['branch'] == 'main'
assert S['selectedPathsIncludingSelf'] == 227 and S['selectionFileIncludedByDriver'] is True
payload_rows = S['selectedRows']
assert len(payload_rows) == 226 and sum(row['bytes'] for row in payload_rows) == 12840537
assert [row['path'] for row in payload_rows] == sorted(row['path'] for row in payload_rows)
assert len({row['path'] for row in payload_rows}) == 226 and SELECTION_PATH not in {row['path'] for row in payload_rows}
rows = []
for expected in payload_rows:
    assert set(expected) == {'path', 'bytes', 'sha256', 'mode', 'oid'}
    p = expected['path']
    pure = PurePosixPath(p)
    assert type(p) is str and p and '\0' not in p and not pure.is_absolute()
    assert str(pure) == p and all(part not in ('', '.', '..', '.git') for part in pure.parts)
    assert not p.startswith(('-', ':')) and not any(c in p for c in '*?[]\\')
    path = REPO / p
    for ancestor in path.parents:
        if ancestor == REPO:
            break
        st = ancestor.lstat()
        assert stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode), str(ancestor)
    raw = data(path)
    actual = identity(path)
    mode = stat.S_IMODE(path.lstat().st_mode)
    actual.update(mode='100755' if mode & 0o111 else '100644',
                  oid=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())
    assert actual == expected, p
    rows.append(actual)
raw_selection = data(REPO / SELECTION_PATH)
rows.append({**selection_row, 'mode': '100755' if stat.S_IMODE((REPO / SELECTION_PATH).lstat().st_mode) & 0o111 else '100644',
             'oid': hashlib.sha1(b'blob ' + str(len(raw_selection)).encode() + b'\0' + raw_selection).hexdigest()})
SELECTED = {row['path'] for row in rows}
AUTHORED = sorted(SELECTED)
assert len(rows) == len(SELECTED) == 227

materialization_row = identity(OUT / 'materialization.json')
assert materialization_row == {'path': str((OUT / 'materialization.json').relative_to(REPO)),
                              'bytes': 5137, 'sha256': '9fc30b188286a0aebaeed566c820be818a3cfe5d0c8ca90db7d063923ed4ab46'}
M = value(OUT / 'materialization.json')
assert M['selection'] == selection_row and M['selectedPaths'] == 227 and M['formattingPaths'] == 222
assert M['sourceOrHelperInvocations'] == M['commands'] == 0 and M['authorityGranted'] is False
for change in M['sourceChanges']:
    exact(change['source'])
    exact(change['output'])
    before = data(REPO / change['source']['path'])
    assert before.startswith(REFUSAL)
    expected = before[len(REFUSAL):]
    for sub in change['substitutions']:
        assert expected.count(sub['before'].encode()) == 1
        expected = expected.replace(sub['before'].encode(), sub['after'].encode())
    assert data(REPO / change['output']['path']) == expected
    ast.parse(expected, filename=change['output']['path'])
assert [row['path'].rsplit('/', 1)[-1] for row in M['driverSources']] == [
    'selection_common_axis_canonical.py', 'preflight_axis_canonical.py',
    'deliver_axis_canonical.py', 'bind_engine_ci_axis_canonical.py']
assert M['driverSources'] == [change['output'] for change in M['sourceChanges']]
for row in M['driverSources']:
    exact(row)
    assert row['path'] not in SELECTED

common_text = data(OUT / 'selection_common_axis_canonical.py').decode()
ct = ast.parse(common_text)
c = constants(ct)
f = functions(ct)
for key, expected in [('SELECTION', SELECTION_PATH), ('SELECTION_BYTES', 73463),
                      ('SELECTION_SHA', SELECTION_SHA), ('SELECTED_COUNT', 227)]:
    assert ast.literal_eval(c[key]) == expected
C2_text = data(OUT / 'correction-2/selection_common_axis_canonical.py.template').decode()
C3_text = data(OUT / 'correction-3/selection_common_axis_canonical.py.template').decode()
C4_text = data(OUT / 'correction-4/selection_common_axis_canonical.py.template').decode()
C2, C3, C4 = ast.parse(C2_text), ast.parse(C3_text), ast.parse(C4_text)
f2, f3, f4 = functions(C2), functions(C3), functions(C4)
assert set(f2) == set(f3) == set(f4) == set(f)
for name in f:
    assert ast.dump(f[name]) == ast.dump(f4[name])
    assert ast.dump(f4[name]) == ast.dump(f3[name])
    if name != 'check_sources':
        assert ast.dump(f3[name]) == ast.dump(f2[name]), name
assert ast.dump(f['phase_vectors']) == ast.dump(f2['phase_vectors'])
assert ast.dump(f['StrictCommands']) == ast.dump(f2['StrictCommands'])
for name in ('PHASES', 'HELPER_SHA', 'PUSH_URL_READ_EXCEPTION', 'DRIVERS', 'PROTECTED'):
    assert ast.dump(c[name]) == ast.dump(constants(C2)[name]), name
new_check = source(C3_text, f3['check_sources'])
added = "    assert row(ROOT / PUBLIC_CONTROL_OUTPUTS_DECISION_ROW['path']) == PUBLIC_CONTROL_OUTPUTS_DECISION_ROW\n    for expected in PUBLIC_CONTROL_OUTPUTS:\n        assert row(ROOT / expected['path']) == expected\n"
assert new_check.count(added) == 1
assert new_check.replace(added, '') == source(C2_text, f2['check_sources'])
public_block = C3_text[C3_text.index('PUBLIC_CONTROL_OUTPUTS_DECISION_ROW ='):C3_text.index('def safe(value):')]
prior = C3_text.replace(public_block, '')
prior = prior.replace("PUBLIC_CONTROL_OUTPUT_PATHS = {value['path'] for value in PUBLIC_CONTROL_OUTPUTS}\nassert len(PUBLIC_CONTROL_OUTPUT_PATHS) == 10 and PUBLIC_CONTROL_OUTPUT_PATHS.issubset(SELECTED)\n", '')
prior = prior.replace("    assert not p.endswith(('.zip', '.nul', '.plan.json', '.started.json', '.admission.json', '.command.json', '-once.json'))", "    assert not p.endswith(('.zip', '.stdout', '.stderr', '.nul', '.plan.json', '.started.json', '.admission.json', '.command.json', '-once.json'))")
prior = prior.replace("    assert not p.endswith(('.stdout', '.stderr')) or p in PUBLIC_CONTROL_OUTPUT_PATHS\n", '')
prior = prior.replace(added, '')
assert prior == C2_text, 'correction-3 has an undeclared source difference'
prior = C4_text
for variable in ('FORMATTING_DECISION_ROW', 'FORMATTING_EXCLUSIONS'):
    old_node = next(n for n in C3.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets))
    new_node = next(n for n in C4.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets))
    old_segment, new_segment = source(C3_text, old_node), source(C4_text, new_node)
    assert prior.count(new_segment) == 1
    prior = prior.replace(new_segment, old_segment)
prior = prior.replace('len(FORMATTING_EXCLUDED_PATHS) == 5', 'len(FORMATTING_EXCLUDED_PATHS) == 3')
prior = prior.replace('len(SELECTED) - 5', 'len(SELECTED) - 3')
assert prior == C3_text, 'correction-4 has an undeclared source difference'
run_source = source(common_text, next(n for n in f['StrictCommands'].body if isinstance(n, ast.FunctionDef) and n.name == 'run'))
assert 'self.check_bindings(); check_sources()' in run_source
assert run_source.index('self.check_bindings(); check_sources()') < run_source.index('self.commands.run(')
assert 'assert self.manifest' in source(common_text, f['StrictCommands'])
assert "review['driverSources'] == a['driverSources']" in source(common_text, f['StrictCommands'])
assert "review['argvApprovals'][self.phase] == self.manifest_row" in source(common_text, f['StrictCommands'])

format_decision = ast.literal_eval(c['FORMATTING_DECISION_ROW'])
public_decision = ast.literal_eval(c['PUBLIC_CONTROL_OUTPUTS_DECISION_ROW'])
exceptions = ast.literal_eval(c['FORMATTING_EXCLUSIONS'])
outputs = ast.literal_eval(c['PUBLIC_CONTROL_OUTPUTS'])
exact(format_decision)
exact(public_decision)
F = value(REPO / format_decision['path'])
P = value(REPO / public_decision['path'])
assert len(exceptions) == 5 and len(outputs) == 10
assert [{k: row[k] for k in ('path', 'bytes', 'sha256')} for row in F['files']] == exceptions == S['formattingExclusions']
assert P['files'] == outputs == S['publicControlOutputs']
assert F['selected'] is P['selected'] is True
assert F['authorityGranted'] is P['authorityGranted'] is False
assert S['formattingDecision'] == format_decision
excluded = {row['path'] for row in exceptions}
public_paths = {row['path'] for row in outputs}
assert len(excluded) == 5 and excluded.issubset(SELECTED)
assert len(public_paths) == 10 and public_paths.issubset(SELECTED)
assert sum(row['bytes'] for row in outputs) == 7872
FORMATTING = [p for p in AUTHORED if p not in excluded]
assert len(FORMATTING) == 222
for expected in [*exceptions, *outputs]:
    exact(expected)
for item in F['files']:
    raw = data(REPO / item['path'])
    whitespace = [i for i, line in enumerate(raw.splitlines(), 1) if line.endswith((b' ', b'\t'))]
    assert whitespace == item['firstLines'] and len(whitespace) == item['whitespaceLineCount']
    assert len(raw) - len(raw.rstrip(b'\n')) == item['terminalNewlines']
for p in SELECTED:
    assert not p.startswith(('.wrangler', '.git/'))
    assert not any(part in ('raw', 'local', 'state', 'streams') for part in PurePosixPath(p).parts)
    assert not p.endswith(('.zip', '.nul', '.plan.json', '.started.json', '.admission.json', '.command.json', '-once.json'))
    assert not p.endswith(('.stdout', '.stderr')) or p in public_paths
assert {p for p in SELECTED if p.endswith(('.stdout', '.stderr'))} == public_paths
for p in FORMATTING:
    raw = data(REPO / p)
    assert not any(line.endswith((b' ', b'\t')) for line in raw.splitlines()), ('trailing whitespace', p)
    assert not raw.endswith(b'\n\n'), ('extra EOF blank lines', p)
    for line in raw.splitlines():
        prefix = line[:len(line) - len(line.lstrip(b' \t'))]
        assert b' \t' not in prefix, ('space before tab in indentation', p)

g = lambda *v: ['git', *v]
RAW = ['--raw', '--no-abbrev', '--no-renames', '-z']
url = ['git', 'remote', 'get-url', '--push', '--all', 'origin']
api = lambda endpoint, query: ['gh', 'api', 'repos/snowdamiz/mixer/' + endpoint, '--hostname', 'github.com', '--jq', query]
vectors = {
 'canonical-preflight': [
  ('git-version', g('--version')), ('gh-version', ['gh', '--version']),
  ('head', g('rev-parse', 'HEAD', 'HEAD^{tree}')), ('branch', g('branch', '--show-current')),
  ('origin', g('remote', 'get-url', 'origin')), ('push-url', url),
  ('remote-main', g('ls-remote', 'origin', 'refs/heads/main')),
  ('index-raw', g('diff', '--cached', *RAW)),
  ('collapsed-status', g('status', '--porcelain=v1', '-z', '--untracked-files=normal')),
  ('complete-raw-diff', g('diff', *RAW))],
 'canonical-delivery': [
  ('head', g('rev-parse', 'HEAD', 'HEAD^{tree}')), ('branch', g('branch', '--show-current')),
  ('origin', g('remote', 'get-url', 'origin')), ('push-url-before-stage', url),
  ('remote-before', g('ls-remote', 'origin', 'refs/heads/main')), ('index-before', g('diff', '--cached', *RAW)),
  ('before-diff', g('diff', *RAW)),
  ('stage', g('add', '--force', '--pathspec-from-file=' + str(OUT / 'paths-canonical.nul'), '--pathspec-file-nul')),
  ('index-selected', g('ls-files', '--stage', '-z', '--', *AUTHORED)),
  ('staged-objects', g('diff', '--cached', *RAW)), ('authored-check', g('diff', '--cached', '--check', '--', *FORMATTING)),
  ('staged-diff', g('diff', *RAW)),
  ('commit', g('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-m', S['commitMessage'])),
  ('committed-head', g('rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^@')),
  ('committed-objects', g('diff-tree', '--no-commit-id', *RAW[:-1], '-r', '-z', BASE, '{COMMITTED_SHA}')),
  ('remote-prepush', g('ls-remote', 'origin', 'refs/heads/main')), ('push-url-prepush', url),
  ('push', g('-c', 'core.hooksPath=/dev/null', 'push', '--signed=false', '--no-follow-tags', '--recurse-submodules=no', 'origin', '{COMMITTED_SHA}:refs/heads/main')),
  ('remote-postpush', g('ls-remote', 'origin', 'refs/heads/main')), ('push-url-postpush', url),
  ('index-after', g('diff', '--cached', *RAW)), ('after-diff', g('diff', *RAW)),
  ('collapsed-status-after', g('status', '--porcelain=v1', '-z', '--untracked-files=normal'))],
 'canonical-engine-ci-binding': [
  ('head', g('rev-parse', 'HEAD', 'HEAD^{tree}')), ('remote-main', g('ls-remote', 'origin', 'refs/heads/main')),
  ('engine-workflow-content', api('contents/.github/workflows/verify.yml?ref={DELIVERED_SHA}', '{sha,size,path,type}')),
  ('engine-workflow-registration', api('actions/workflows/verify.yml', '{id,path,state,name}')),
  ('engine-run', api('actions/workflows/verify.yml/runs?event=push&head_sha={DELIVERED_SHA}&per_page=5',
   '[.workflow_runs[]|{id,name,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}]'))]
}
phases = ast.literal_eval(c['PHASES'])
assert set(vectors) == set(phases) == set(M['argvApprovals'])
for phase, pairs in vectors.items():
    approved = M['argvApprovals'][phase]
    exact(approved)
    assert approved['path'] not in SELECTED
    manifest = value(REPO / approved['path'])
    expected_commands = [{'name': name, 'argv': argv,
      'effectiveArgv': ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *argv[1:]] if argv[0] == 'git' else argv,
      'kind': 'mutation' if name in ('stage', 'commit', 'push') else 'read'} for name, argv in pairs]
    assert manifest['commands'] == expected_commands, phase
    assert manifest['schema'] == 1 and manifest['phase'] == phase and manifest['selection'] == selection_row
    assert manifest['session'] == {'seconds': phases[phase][0], 'count': phases[phase][1], 'prefix': phase + '-'}
    assert len(expected_commands) == len({row['name'] for row in expected_commands}) == phases[phase][1]
    assert manifest['manualWorkflowDispatchLimit'] == 0 and manifest['preparationOnly'] is False
    assert manifest['unboundFields'] == []
    assert manifest['helper'] == S['helper']
    assert manifest['interpreter'] == {'flags': ['-I','-B','-S'], 'wrapper': S['helper']['path']}
    for row in expected_commands:
        assert all(type(token) is str and token and '\0' not in token for token in row['argv'])
        assert row['argv'][:2] != ['gh', 'workflow']
        if row['name'] != 'stage':
            assert not any(token == '-f' or token.startswith('--force') for token in row['argv'])
assert sum(len(v) for v in vectors.values()) == 38

for phase, template_name in [('canonical-preflight','argv-canonical-preflight.template.json'),
                             ('canonical-delivery','correction-2/argv-canonical-delivery.template.json'),
                             ('canonical-engine-ci-binding','argv-canonical-engine-ci-binding.template.json')]:
    template = value(OUT / template_name)
    expanded = []
    for command in template['commands']:
        command = dict(command)
        for key in ('argv','effectiveArgv'):
            argv = []
            for token in command[key]:
                if token == '{SELECTED_PATHS_EXPAND_HERE}':
                    argv.extend(AUTHORED)
                elif token == '{FORMATTING_PATHS_EXPAND_HERE}':
                    argv.extend(FORMATTING)
                elif token == '{ROOT_FINAL_COMMIT_MESSAGE}':
                    argv.append(S['commitMessage'])
                else:
                    argv.append(token)
            command[key] = argv
        expanded.append(command)
    assert expanded == value(REPO / M['argvApprovals'][phase]['path'])['commands']

helper = exact(S['helper'])
assert helper['bytes'] == 29385 and helper['sha256'] == '2ed27bc68ade5b38e4cae1268d7b2eb8606417b2948227236d9da3d38fb60711'
old_helper = data(REPO / 'verification/github-delivery-axis-binding-stage-recovery/owned.py')
assert hashlib.sha256(old_helper).hexdigest() == '34f1991509d7b156f00b5cc50fcd82ebae81fb414da904c19dcdca70c3eeb987'
current_helper = data(REPO / helper['path'])
before_lines, after_lines = old_helper.splitlines(keepends=True), current_helper.splitlines(keepends=True)
assert len(before_lines) == len(after_lines)
assert [i + 1 for i, (a,b) in enumerate(zip(before_lines, after_lines)) if a != b] == [111]
assert b''.join(after_lines[:110] + [before_lines[110]] + after_lines[111:]) == old_helper
history_row = exact(S['historicalClosure'])
assert history_row['sha256'] == '77642caf7143b3aed323cf80c91a20660cc754030a787e3acad774007c94ef6b'
history = value(REPO / history_row['path'])
assert history['closedCommandSeries'] == {
 'originalPreflight':9,'originalDelivery':8,'freshStageRecoveryInspection':10,'freshStageRecoveryDelivery':23,
 'ordinaryEngineBinding':5,'axisBinding':5,'axisDispatch':7,'lateAxisBinding':4,'total':71,
 'originalLastDeliveryExit':1,'originalLastDeliveryRawWaitStatus':256,'allOtherExits':0}
assert len(history['rows']) == 5
for row in history['rows']:
    exact(row)
protected = []
for row in ast.literal_eval(c['PROTECTED']):
    actual = identity(REPO / row['path'])
    assert actual['sha256'] == row['sha256'] and row['path'] not in SELECTED
    protected.append({**actual, 'mode': stat.S_IMODE((REPO / row['path']).lstat().st_mode)})
wrangler = (REPO / '.wrangler').lstat()
assert (wrangler.st_ino, wrangler.st_dev) == (134689423,16777233)
try:
    (REPO / 'hosted/lib/mixer_hosted/artifacts/store.ex').lstat()
except FileNotFoundError:
    pass
else:
    raise AssertionError('artifacts store unexpectedly present')
workflow = exact(S['ordinaryHost']['source'])
assert workflow == {'path': '.github/workflows/verify.yml', 'bytes':31363,
 'sha256':'5ce51236f178080e3301289513fa3f5a8313e3a3969b0bab3f2b1cd4668de7f5'}
assert workflow['path'] in SELECTED
assert S['ordinaryHost'] == {'workflow':workflow['path'],'source':workflow,'name':'Owned engine checks','expectedJobs':6}
workflow_text = data(REPO / workflow['path']).decode()
assert workflow_text.count('\njobs:\n') == 1
jobs_source = workflow_text.split('\njobs:\n', 1)[1]
job_names = [line[:-1].strip() for line in jobs_source.splitlines() if re.fullmatch(r'  [A-Za-z0-9_-]+:',line)]
assert len(job_names) == 6
assert workflow_text.startswith('name: Owned engine checks\n')

delivery_text = data(OUT / 'deliver_axis_canonical.py').decode()
assert "head, tree, parent = c.run('committed-head').decode().splitlines()" in delivery_text
assert 'assert parent == BASE' in delivery_text
assert 'assert objects == expected_objects' in delivery_text
assert "changed_map(c.run('staged-objects'), objects)" in delivery_text
assert "changed_map(c.run('committed-objects'), objects)" in delivery_text
assert "assert committed == changed" in delivery_text
assert "assert c.run('index-after') == b''" in delivery_text
assert "'whitespaceCheckedPaths': len(FORMATTING)" in delivery_text
assert "'immutableEvidenceFormattingExclusions': FORMATTING_EXCLUSIONS" in delivery_text
preflight_text = data(OUT / 'preflight_axis_canonical.py').decode()
assert "assert c.run('index-raw') == b''" in preflight_text
binding_text = data(OUT / 'bind_engine_ci_axis_canonical.py').decode()
assert "assert len(runs) == 1" in binding_text
assert "engine['event'] == 'push'" in binding_text
assert "'actualJobResultsRead': False" in binding_text
assert "'runtimeResultsAccepted': False" in binding_text
excluded_runtime = S['runtimeMaterializationExcludedFromPayload']
assert excluded_runtime['dynamicAuthoritiesReceiptsStateAndFinalReviewExcluded'] is True
for row in [*M['driverSources'], *M['argvApprovals'].values()]:
    assert row['path'] not in SELECTED
for name in ('authority.json','paths-canonical.nul','preflight-canonical.json','delivery-canonical-receipt.json',
             'engine-ci-canonical-binding.json','review/final-source-review.json',
             'review/final-source-data-check.py','materialization.json'):
    assert str((OUT / name).relative_to(REPO)) not in SELECTED
assert data(OUT / '.gitignore') == b'*\n'
assert not (OUT / 'authority.json').exists()
markers_row = identity(OUT / 'root-git-markers-before-selection.json')
assert markers_row == {'path':str((OUT / 'root-git-markers-before-selection.json').relative_to(REPO)),
 'bytes':1240,'sha256':'d79c203fc9c1565289c3df2131112b2264723ccdd3fc8ea8cc6abb480da2fde0'}
markers = value(REPO / markers_row['path'])
assert len(markers['markers']) == 6 and all(row['exists'] is False for row in markers['markers'])
assert markers['correctsEarlierTimingClaim'] is False
metadata = value(OUT / 'correction-1/metadata-correction.json')
assert metadata['correctedValue'] is False and metadata['corrects']['recordedValue'] is True

summary = {
 'status':'PASS_SOURCE_DATA_ONLY_NO_AUTHORITY',
 'selection':selection_row,
 'selectedPayloadFiles':len(payload_rows),'selectedPathsIncludingSelf':len(rows),
 'selectedPayloadBytes':sum(row['bytes'] for row in payload_rows),
 'selectedRowsIncludingSelfSHA256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'allSelectedSHA256BytesGitBlobOIDsAndModesMatch':True,
 'safeRegularFilesAndParentsNoSymlinks':True,
 'runtimeMaterializationExactGuardAndFourCommonConstantsOnly':True,
 'driverSources':M['driverSources'],'argvApprovals':M['argvApprovals'],'helper':helper,
 'typedCommandCounts':{phase:len(pairs) for phase,pairs in vectors.items()},
 'phaseVectorsASTMatchesPreviouslyReviewedCorrection2':True,
 'manifestVectorsExactlyMatchIndependentFiniteExpansionAndTemplates':True,
 'sourceAndArgvBindingBeforeEveryCommand':True,
 'soleBaselineParentProof':True,
 'formattingDefaultPaths':len(FORMATTING),'formattingExceptions':exceptions,
 'publicOutputPaths':len(outputs),'publicOutputBytes':sum(row['bytes'] for row in outputs),
 'allOtherRawLocalStateStreamsAndOutputBansPreserved':True,
 'historyCommands':71,'historyExitZero':70,'historyOriginalStageExit':1,'historyOriginalStageRawWait':256,
 'fiveHistoricalClosureRowsVerified':True,
 'protectedObservedRows':protected,
 'wranglerObserved':{'inode':wrangler.st_ino,'device':wrangler.st_dev,'mode':stat.S_IMODE(wrangler.st_mode)},
 'artifactsStoreAbsent':True,
 'ordinaryWorkflow':workflow,'workflowJobsObservedFromSource':job_names,
 'freshRootGitMarkerRecheckBeforeAdmissionStillRequired':True,
 'subjectSourceImportedOrExecuted':False,
 'gitGhCompilerProductOracleNetworkProcessProbeSignalNativeCaptureUIActions':0,
 'actualAuthorityCreated':False,
 'checker':{'python':sys.version,'interpreter':sys.executable,'flags':['-I','-B','-S'],
            'uniqueSourceDataReadBytes':TOTAL,'fileBoundBytes':2000000,'aggregateBoundBytes':32000000}
}
print(json.dumps(summary,indent=2))

