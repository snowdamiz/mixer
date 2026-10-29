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
import stat
from pathlib import Path
from datetime import datetime

REPO = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = REPO / 'verification/github-delivery-axis-canonical-followup'
BASE = '2c751cbbc300efc9aa766b5d4add648610ca0341'
BASE_TREE = 'f2df6833ee8e9ce85306210b63dc35d45747fa0d'
HEAD = '3da0d01bd05565a6aad905997beddf6805826241'
TREE = '89297f81773cad23c94ebba1560deccda99c551f'
URL = 'https://github.com/snowdamiz/mixer.git'
CACHE, READ_ROWS = {}, {}
TOTAL = 0

def read(path):
    global TOTAL
    path = Path(path)
    key = str(path)
    if key not in CACHE:
        st = path.lstat()
        assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), key
        with path.open('rb') as handle:
            raw = handle.read(2_000_001)
        assert len(raw) <= 2_000_000, key
        TOTAL += len(raw)
        assert TOTAL <= 32_000_000
        CACHE[key] = raw
        READ_ROWS[key] = {'path': str(path.relative_to(REPO)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return CACHE[key]

def identity(path):
    read(path)
    return READ_ROWS[str(Path(path))]

def pairs_unique(pairs):
    result = {}
    for k, v in pairs:
        assert k not in result, ('duplicate JSON key', k)
        result[k] = v
    return result

def load_json(path):
    return json.loads(read(path), object_pairs_hook=pairs_unique)

def exact(row):
    assert identity(REPO / row['path']) == row, row['path']
    return row

def at(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))

def raw_rows(raw):
    parts = raw.split(b'\0')
    assert len(parts) % 2 == 1 and parts[-1] == b''
    result = []
    for i in range(0, len(parts)-1, 2):
        meta, path = parts[i].decode(), parts[i+1].decode()
        fields = meta.split()
        assert len(fields) == 5 and fields[0].startswith(':')
        assert fields[-1] in ('A','M','D','T')
        result.append({'path': path, 'gitRaw': meta})
    return result

def changed_objects(raw):
    result = {}
    for item in raw_rows(raw):
        fields = item['gitRaw'].split()
        assert fields[-1] in ('A','M') and item['path'] in SELECTED and item['path'] not in result
        result[item['path']] = {'oid':fields[3], 'mode':fields[1]}
    return result

def collapsed(raw):
    result = []
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        text = entry.decode()
        assert len(text) > 3 and text[2] == ' ' and not any(c in text[:2] for c in 'RC')
        result.append({'status':text[:2], 'path':text[3:]})
    return result

review = load_json(OUT / 'review/final-source-review.json')
assert identity(OUT / 'review/final-source-review.json') == {
 'path':'verification/github-delivery-axis-canonical-followup/review/final-source-review.json',
 'bytes':6893,'sha256':'26c7f6209217b67b2df879ec717d751637d1c9189977d49581adb6052e898aa8'}
assert review['decision'] == 'accept-exact-axis-canonical-delivery-source-and-argv'
assert review['authorityGranted'] is False
exact(review['selection'])
exact(review['helper'])
for row in [*review['driverSources'], *review['argvApprovals'].values()]:
    exact(row)
    if row in review['driverSources']:
        ast.parse(read(REPO / row['path']), filename=row['path'])
S = load_json(REPO / review['selection']['path'])
rows = list(S['selectedRows'])
for expected in rows:
    raw = read(REPO / expected['path'])
    actual = dict(identity(REPO / expected['path']))
    actual['mode'] = '100755' if stat.S_IMODE((REPO / expected['path']).lstat().st_mode) & 0o111 else '100644'
    actual['oid'] = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert actual == expected, expected['path']
selection_raw = read(REPO / review['selection']['path'])
self_row = {**review['selection'], 'mode':'100755' if stat.S_IMODE((REPO / review['selection']['path']).lstat().st_mode) & 0o111 else '100644',
 'oid':hashlib.sha1(b'blob '+str(len(selection_raw)).encode()+b'\0'+selection_raw).hexdigest()}
rows.append(self_row)
SELECTED = {r['path'] for r in rows}
AUTHORED = sorted(SELECTED)
EXPECTED_OBJECTS = {r['path']:{'oid':r['oid'],'mode':r['mode']} for r in rows}
assert len(rows) == len(SELECTED) == 227
assert hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest() == review['validation']['selectedRowsIncludingSelfSHA256']
assert sum(r['bytes'] for r in rows) == 12914000

receipts = {
 'canonical-preflight':load_json(OUT / 'preflight-canonical.json'),
 'canonical-delivery':load_json(OUT / 'delivery-canonical-receipt.json'),
 'canonical-engine-ci-binding':load_json(OUT / 'engine-ci-canonical-binding.json')}
expected_receipt_rows = {
 'canonical-preflight':('preflight-canonical.json',4775,'06f2254810bdad3d655b1400141b34df392a9a0134391401363b3628c9aa2af4'),
 'canonical-delivery':('delivery-canonical-receipt.json',32829,'0f985a713d5ad1fc8bd35cb2acf4f1a70d375c82088a993bf8e160ea877fc1f1'),
 'canonical-engine-ci-binding':('engine-ci-canonical-binding.json',3539,'5cf18926f783e344197122793c695ac5ebd61ed209e73950d6ce0216ef7f65cc')}
for phase, (name,size,sha) in expected_receipt_rows.items():
    assert identity(OUT/name) == {'path':str((OUT/name).relative_to(REPO)),'bytes':size,'sha256':sha}
phase_specs = {
 'canonical-preflight':(10,210,2873,'7fc89cb705256d1ad05fb0cc7e3e4391931f2ceb06d473ff5a6eca5b87e55af5'),
 'canonical-delivery':(23,240,3800,'65079873090760d9b195c4d616489f84ed74bceab276be5717a08b58e7460715'),
 'canonical-engine-ci-binding':(5,180,4006,'c4919e88bb0b8bcb877ef7c56ee0646c600c521278bf4312e312a53081c42249')}
names = set(os.listdir(OUT))
artifacts = {}
phase_summaries = {}
all_pids = []
all_mutations = []
admission_hash_rows = []
for phase, (count,seconds,authority_bytes,authority_sha) in phase_specs.items():
    authority_path = OUT / ('authority-snapshot-'+phase+'.json')
    authority_row = identity(authority_path)
    assert authority_row['bytes'] == authority_bytes and authority_row['sha256'] == authority_sha
    authority = load_json(authority_path)
    manifest = load_json(REPO/review['argvApprovals'][phase]['path'])
    assert authority['schema'] == 1 and authority['authorized'] is True
    assert authority['phase'] == phase and authority['phaseLimit'] == 1
    assert authority['baseline'] == {'head':BASE,'tree':BASE_TREE}
    assert authority['repository'] == 'snowdamiz/mixer' and authority['branch'] == 'main'
    assert authority['selection'] == review['selection'] and authority['selectedPathsIncludingSelf'] == 227
    assert authority['helper'] == review['helper'] and authority['driverSources'] == review['driverSources']
    assert exact(authority['sourceReview']) == identity(OUT/'review/final-source-review.json')
    assert authority['argvApproval'] == review['argvApprovals'][phase]
    assert authority['manualWorkflowDispatchLimit'] == 0
    assert authority['stageLimit'] == authority['commitLimit'] == authority['nonforcePushLimit'] == int(phase=='canonical-delivery')
    assert authority['retryRerunFallbackAllowed'] is authority['oldDriverReplayAllowed'] is False
    assert authority['admissionAdapter'] == {'exactReadOnlyException':['git','remote','get-url','--push','--all','origin'],
     'allOtherVectorsUseUnchangedHelperValidation':True,'strictManifestEqualityBeforeAdapter':True,
     'custodyStartupKernelWaitEOFSignalLogicChanged':False}
    assert manifest['session'] == {'seconds':seconds,'count':count,'prefix':phase+'-'}
    approved = manifest['commands']
    assert len(approved) == count
    expected_labels = [phase+'-'+item['name'] for item in approved]
    for suffix in ('.plan.json','.started.json','.admission.json','.command.json','.stdout','.stderr'):
        assert {n for n in names if n.startswith(phase+'-') and n.endswith(suffix)} == {label+suffix for label in expected_labels}, (phase,suffix)
    aggregate = 0
    compact = []
    first_at, final_at = None, None
    command_digest_rows = []
    for ordinal, item in enumerate(approved,1):
        label = phase+'-'+item['name']
        record = load_json(OUT/(label+'.command.json'))
        plan = load_json(OUT/(label+'.plan.json'))
        started = load_json(OUT/(label+'.started.json'))
        admission = load_json(OUT/(label+'.admission.json'))
        effective = [token.replace('{COMMITTED_SHA}',HEAD).replace('{DELIVERED_SHA}',HEAD) for token in item['effectiveArgv']]
        assert record['argv'] == plan['argv'] == admission['argv'] == effective
        assert not any('{COMMITTED_SHA}' in t or '{DELIVERED_SHA}' in t for t in effective)
        assert plan['cwd'] == str(REPO) and plan['ordinal'] == ordinal and plan['sessionCommandLimit'] == count
        assert 0 < plan['activeSeconds'] <= (45 if item['name']=='push' else 25)
        assert plan['admissionSeconds'] == 5 and plan['cleanupSeconds'] == 6
        assert plan['streamCapEachBytes'] == 8*1024*1024 and plan['aggregateCapBytes'] == 32*1024*1024
        assert plan['freshSessionRequired'] is plan['targetReleaseAfterPersistedAdmissionOnly'] is plan['isolatedNoSiteBytecodeDisabled'] is True
        assert plan['nativeSIGCHLD'] == {'platform':'darwin-64','handler':None,'flags':0,'SA_NOCLDWAIT':32,'sigactionBytes':16,'readOnly':True}
        pid = record['ownedPID']
        assert type(pid) is int and pid > 0
        all_pids.append(pid)
        assert started['ownedPID'] == pid and started['targetReleased'] is False
        ident = {'pid':pid,'pgid':pid,'sid':pid}
        assert record['identity'] == admission['identity'] == ident
        assert record['ownedPGID'] == admission['parentObservedPGID'] == admission['parentObservedSID'] == pid
        assert admission['targetReleasedOnlyAfterPersistedAdmission'] is True
        assert admission['activeSeconds'] == plan['activeSeconds'] and admission['cleanupSeconds'] == 6
        assert admission['streamCapEachBytes'] == plan['streamCapEachBytes']
        assert at(plan['at']) <= at(started['at']) <= at(admission['at']) <= at(record['at'])
        if first_at is None: first_at = at(plan['at'])
        final_at = at(record['at'])
        for field in ('admitted','directChildReaped','ownedGroupAbsent','wnowaitSupported','terminalObservedWithoutReap',
                      'signalAuthorityRetired','finalReapAttempted','implicitPopenReapingDisabled',
                      'unresolvedChildRetainedUntilIsolatedDriverExit','interpreterExitIsNotCustodyEvidence',
                      'noSignalAfterFinalReapOrLostAuthority','stdoutEOF','stderrEOF','separateOutputPipes'):
            assert record[field] is True,(label,field)
        assert record['exit'] == record['rawWaitStatus'] == 0 and record['rawWaitPID'] == pid
        assert record['terminalObservation'] == [1,0]
        assert record['postReapAbsenceProbeCount'] == 1 and record['postReapProbeSuccessOrEPERMHeldWithoutRetry'] is False
        assert record['signalAuthorityLost'] is record['stopReason'] is record['failure'] is None
        assert record['signals'] == [] and record['sensitiveOutputRejected'] is False
        assert record['authoritySHA256'] == authority_sha
        for stream in ('stdout','stderr'):
            assert record[stream]['path'] == str((OUT/(label+'.'+stream)).relative_to(REPO))
            exact(record[stream])
            raw = read(REPO/record[stream]['path'])
            assert len(raw) == record[stream+'ObservedBytes'] <= plan['streamCapEachBytes']
            assert not any(marker in raw.lower() for marker in (b'x-amz-signature=',b'x-goog-signature=',b'ghp_',b'github_pat_',b'authorization: bearer ',b'-----begin private key-----'))
            aggregate += len(raw)
        assert record['aggregateOutputBytes'] == aggregate <= plan['aggregateCapBytes']
        compact.append({'name':label,**{k:record[k] for k in ('exit','admitted','stopReason','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF','sensitiveOutputRejected')}})
        artifacts[(phase,item['name'])] = record
        if item['kind'] == 'mutation': all_mutations.append(label)
        command_digest_rows.append(identity(OUT/(label+'.command.json')))
        admission_hash_rows.extend(identity(OUT/(label+suffix)) for suffix in ('.plan.json','.started.json','.admission.json','.command.json','.stdout','.stderr'))
    assert len(compact) == count and receipts[phase]['commands'] == compact
    assert (final_at-first_at).total_seconds() < seconds
    assert receipts[phase]['authoritySnapshot'] == authority_row
    assert receipts[phase]['selection'] == review['selection']
    phase_summaries[phase] = {
     'commands':count,'authority':authority_row,'allExitZeroAndKernelWaitStatusZero':True,
     'allOwnedGroupsAbsentAndSeparateEOFAfterDirectReap':True,'allSignalAuthorityRetired':True,'signals':0,
     'aggregateOutputBytes':aggregate,'recordedSpanSeconds':(final_at-first_at).total_seconds(),
     'commandRecordsSHA256':hashlib.sha256(json.dumps(command_digest_rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
assert len(all_pids) == len(set(all_pids)) == 38
assert all_mutations == ['canonical-delivery-stage','canonical-delivery-commit','canonical-delivery-push']
assert len([n for n in names if n.startswith('authority-snapshot-canonical-') and n.endswith('.json')]) == 3

def output(phase,name,stream='stdout'):
    return read(REPO/artifacts[(phase,name)][stream]['path'])

pre = receipts['canonical-preflight']
delivery = receipts['canonical-delivery']
engine_receipt = receipts['canonical-engine-ci-binding']
preservation = load_json(OUT/'preservation-canonical-local.json')
after = load_json(OUT/'preservation-canonical-after-local.json')
manifest_receipt = load_json(OUT/'manifest-canonical.json')
root_pre = load_json(OUT/'preflight-canonical-root-review.json')
assert root_pre['decision'] == 'accept-exact-fresh-canonical-preflight' and root_pre['authorityGranted'] is False
delivery_authority = load_json(OUT/'authority-snapshot-canonical-delivery.json')
engine_authority = load_json(OUT/'authority-snapshot-canonical-engine-ci-binding.json')
binding = delivery_authority['acceptedPreflight']
exact(binding['seal'])
for row in binding['rows']: exact(row)
assert root_pre['rows'] == binding['rows']
assert engine_authority['acceptedPreflight'] == binding
assert engine_authority['acceptedDelivery'] == identity(OUT/'delivery-canonical-receipt.json')
exact(engine_authority['actualDeliveryReview'])
for phase in ('canonical-preflight','canonical-delivery'):
    a = load_json(OUT/('authority-snapshot-'+phase+'.json'))
    marker = load_json(REPO/exact(a['pendingGitOperationMarkerCheck'])['path'])
    assert len(marker['markers']) == 6 and all(row['exists'] is False for row in marker['markers'])
assert manifest_receipt['members'] == rows and manifest_receipt['paths'] == 227 and manifest_receipt['bytes'] == 12914000
assert output('canonical-preflight','head').decode().splitlines() == [BASE,BASE_TREE]
assert output('canonical-preflight','branch') == b'main\n'
assert output('canonical-preflight','origin').decode().strip() == pre['origin'] == URL
assert output('canonical-preflight','push-url').decode().splitlines() == [URL]
assert output('canonical-preflight','remote-main').decode().split() == [BASE,'refs/heads/main']
assert output('canonical-preflight','index-raw') == b''
assert output('canonical-preflight','git-version').decode().strip() == pre['tools']['git'] == 'git version 2.56.0'
assert output('canonical-preflight','gh-version').decode().strip() == pre['tools']['gh']
assert pre['tools']['gh'].startswith('gh version 2.102.0 ')
assert pre['tools']['python'].startswith('3.14.8 ')
pre_raw = output('canonical-preflight','complete-raw-diff')
assert raw_rows(pre_raw) == preservation['completeWorktreeRawRows']
assert len(raw_rows(pre_raw)) == 12 and hashlib.sha256(pre_raw).hexdigest() == preservation['completeWorktreeRawSHA256']
other = [item for item in raw_rows(pre_raw) if item['path'] not in SELECTED]
assert len(other) == 2 and other == preservation['otherDirtyTracked']
assert {item['path'] for item in other} == {item['path'] for item in preservation['protectedSnapshots']}
assert collapsed(output('canonical-preflight','collapsed-status')) == preservation['statusCollapsed']
assert len(preservation['untrackedCollapsed']) == 2425
assert preservation['tracked'] == preservation['protectedSnapshots'] and len(preservation['tracked']) == 2
for row in preservation['tracked']:
    actual = identity(REPO/row['path'])
    assert {key:row[key] for key in ('path','bytes','sha256')} == actual
    assert row['mode'] == stat.S_IMODE((REPO/row['path']).lstat().st_mode) == 0o644
    assert row['type'] == stat.S_IFMT((REPO/row['path']).lstat().st_mode) == stat.S_IFREG
assert preservation['wrangler'] == {'path':'.wrangler','mode':493,'type':16384,'inode':134689423,'device':16777233}
assert pre['indexEmpty'] is True and pre['selectedPaths'] == 227

assert output('canonical-delivery','head').decode().splitlines() == [BASE,BASE_TREE]
assert output('canonical-delivery','branch') == b'main\n'
assert output('canonical-delivery','origin').decode().strip() == pre['origin']
for name in ('push-url-before-stage','push-url-prepush','push-url-postpush'):
    assert output('canonical-delivery',name).decode().splitlines() == [URL]
for name in ('remote-before','remote-prepush'):
    assert output('canonical-delivery',name).decode().split() == [BASE,'refs/heads/main']
assert output('canonical-delivery','remote-postpush').decode().split() == [HEAD,'refs/heads/main']
for name in ('index-before','index-after'):
    assert output('canonical-delivery',name) == b''
assert output('canonical-delivery','before-diff') == pre_raw
for name in ('staged-diff','after-diff'):
    assert raw_rows(output('canonical-delivery',name)) == other
index_objects = {}
for entry in output('canonical-delivery','index-selected').split(b'\0'):
    if not entry: continue
    metadata, path = entry.split(b'\t',1)
    fields, path = metadata.decode().split(), path.decode()
    assert len(fields)==3 and fields[2]=='0' and path in SELECTED and path not in index_objects
    index_objects[path]={'mode':fields[0],'oid':fields[1]}
assert index_objects == EXPECTED_OBJECTS
assert load_json(OUT/'selected-index-objects-canonical-local.json') == index_objects
cached_raw = output('canonical-delivery','staged-objects')
parent_raw = output('canonical-delivery','committed-objects')
assert changed_objects(cached_raw) == changed_objects(parent_raw) == EXPECTED_OBJECTS
assert cached_raw == parent_raw
assert load_json(OUT/'changed-index-objects-canonical-local.json') == EXPECTED_OBJECTS
assert load_json(OUT/'committed-objects-canonical.json') == EXPECTED_OBJECTS
assert output('canonical-delivery','committed-head').decode().splitlines() == [HEAD,TREE,BASE]
assert artifacts[('canonical-delivery','committed-head')]['argv'][-1] == 'HEAD^@'
assert output('canonical-delivery','authored-check') == output('canonical-delivery','authored-check','stderr') == b''
formatting = [p for p in AUTHORED if p not in {row['path'] for row in S['formattingExclusions']}]
assert len(formatting)==222
format_argv = artifacts[('canonical-delivery','authored-check')]['argv']
assert format_argv[format_argv.index('--')+1:] == formatting
assert delivery['whitespaceCheckScope']['checkedPaths'] == formatting
assert delivery['immutableEvidenceFormattingExclusions'] == S['formattingExclusions']
assert delivery['whitespaceCheckedPaths'] == 222
assert read(OUT/'paths-canonical.nul') == b''.join(p.encode()+b'\0' for p in AUTHORED)
path_admission = load_json(OUT/'canonical-pathspec-admission.json')
assert path_admission['selection'] == review['selection'] and path_admission['paths'] == 227
assert path_admission['fixedNULAllowlistOnly'] is path_admission['forceAddOnly'] is True
exact(path_admission['pathspec'])
once = load_json(OUT/'canonical-delivery-once.json')
assert once['selection'] == review['selection'] and once['paths']==227 and once['retryOnUnknownOutcome'] is False
for key in ('stageReservation','commitReservation','pushReservation'):
    exact(delivery[key])
stage_res = load_json(REPO/delivery['stageReservation']['path'])
commit_res = load_json(REPO/delivery['commitReservation']['path'])
push_res = load_json(REPO/delivery['pushReservation']['path'])
assert stage_res['stageLimit'] == commit_res['commitLimit'] == 1
assert stage_res['retryAllowed'] is commit_res['retryAllowed'] is False
assert commit_res['parentMustEqual'] == BASE
assert push_res['head'] == HEAD and push_res['tree'] == TREE and push_res['parent'] == BASE
assert push_res['remote'] == 'origin' and push_res['ref'] == 'refs/heads/main'
assert push_res['force'] is False and push_res['reservationConsumedBeforeSubmit'] is True
assert push_res['retryOnUnknownOutcome'] is False
assert delivery['head'] == HEAD and delivery['tree']==TREE and delivery['parent']==BASE
assert delivery['pushed'] is True and delivery['force'] is False and delivery['indexEmpty'] is True
assert delivery['selectedPaths'] == delivery['changedSelectedPaths'] == 227 and delivery['unchangedSelectedPaths'] == 0
assert delivery['manualDispatchesPerformed'] == delivery['manualWorkflowDispatchesAuthorized'] == 0
assert after['statusCollapsed'] == collapsed(output('canonical-delivery','collapsed-status-after'))
assert len(after['untrackedCollapsed']) == 2425
before_untracked = {row['path']:row for row in preservation['untrackedCollapsed']}
after_untracked = {row['path']:row for row in after['untrackedCollapsed']}
common_untracked = before_untracked.keys() & after_untracked.keys()
assert len(before_untracked) == len(after_untracked) == 2425
assert len(common_untracked) == 2413
assert all(before_untracked[p] == after_untracked[p] for p in common_untracked)
for expected in preservation['untrackedCollapsed']:
    st = (REPO / expected['path'].rstrip('/')).lstat()
    assert {'path':expected['path'], 'mode':stat.S_IMODE(st.st_mode), 'type':stat.S_IFMT(st.st_mode),
            'inode':st.st_ino,'device':st.st_dev} == expected
def selected_projection(path):
    path = path.rstrip('/')
    return any(p == path or p.startswith(path + '/') for p in SELECTED)
def covered(path, prior):
    return path == prior or prior.endswith('/') and path.startswith(prior)
prior_paths = list(before_untracked)
current_paths = list(after_untracked)
assert all(selected_projection(p) or any(covered(p, old) for old in prior_paths) for p in current_paths)
assert all(selected_projection(old) or any(covered(p,old) or covered(old,p) for p in current_paths) for old in prior_paths)
assert len(before_untracked.keys() - after_untracked.keys()) == 12
assert len(after_untracked.keys() - before_untracked.keys()) == 12
before_tracked = [r for r in preservation['statusCollapsed'] if r['status']!='??' and r['path'] not in SELECTED]
after_tracked = [r for r in after['statusCollapsed'] if r['status']!='??' and r['path'] not in SELECTED]
assert before_tracked == after_tracked and len(after_tracked)==2
assert {r['path'] for r in preservation['statusCollapsed'] if r['status']=='??'} == set(before_untracked)
assert {r['path'] for r in after['statusCollapsed'] if r['status']=='??'} == set(after_untracked)
assert len(after['statusCollapsed'])==2427 and len(preservation['statusCollapsed'])==2437
assert delivery['collapsedStatusProof']['recursiveUntrackedContentProof'] is False
assert preservation['allCleanTrackedFilesIndependentlyHashed'] is False
assert delivery['allCleanTrackedFilesIndependentlyHashed'] is False

assert output('canonical-engine-ci-binding','head').decode().splitlines() == [HEAD,TREE]
assert output('canonical-engine-ci-binding','remote-main').decode().split() == [HEAD,'refs/heads/main']
content = json.loads(output('canonical-engine-ci-binding','engine-workflow-content'))
registration = json.loads(output('canonical-engine-ci-binding','engine-workflow-registration'))
runs = json.loads(output('canonical-engine-ci-binding','engine-run'))
workflow_path = S['ordinaryHost']['workflow']
workflow = read(REPO/workflow_path)
workflow_oid = hashlib.sha1(b'blob '+str(len(workflow)).encode()+b'\0'+workflow).hexdigest()
assert content == {'sha':workflow_oid,'size':31363,'path':workflow_path,'type':'file'}
assert registration == {'id':393488255,'path':workflow_path,'state':'active','name':'Owned engine checks'}
assert len(runs)==1
run=runs[0]
assert run['id']==40960463690 and run['head_sha']==HEAD and run['event']=='push' and run['run_attempt']==1
assert run['workflow_id']==registration['id'] and run['path']==workflow_path and run['name']==registration['name']
assert run['status']=='in_progress' and run['conclusion'] is None
assert engine_receipt['content']==content and engine_receipt['registration']==registration and engine_receipt['engine']==run
assert engine_receipt['delivery']==identity(OUT/'delivery-canonical-receipt.json')
assert engine_receipt['engineExpectedJobs']==6 and engine_receipt['manualDispatchesPerformed']==0
assert engine_receipt['actualJobResultsRead'] is engine_receipt['runtimeResultsAccepted'] is engine_receipt['artifactDownloaded'] is False
history = load_json(REPO/S['historicalClosure']['path'])
exact(S['historicalClosure'])
assert history['closedCommandSeries']['total']==71 and history['closedCommandSeries']['originalLastDeliveryExit']==1
assert history['closedCommandSeries']['originalLastDeliveryRawWaitStatus']==256 and history['closedCommandSeries']['allOtherExits']==0
for row in history['rows']: exact(row)
auditor = identity(OUT/'local/closure-auditor-source.js')
assert auditor['bytes']==1853 and auditor['sha256']=='4b7bbe4476b0723031699c4c7b4bd004635bd4c0d330e3a8e624c8801ba3c08e'
root_delivery = load_json(OUT/'root-delivery-actual-review.json')
assert root_delivery['decision']=='accept-exact-canonical-delivery-actual-result'
assert root_delivery['head']==HEAD and root_delivery['tree']==TREE and root_delivery['soleParent']==BASE
assert root_delivery['selectedIndexData']==identity(OUT/'canonical-delivery-index-selected.stdout')
assert root_delivery['committedRawData']==identity(OUT/'canonical-delivery-committed-objects.stdout')

summary = {
 'status':'PASS_INDEPENDENT_ACTUAL_DATA_REVIEW',
 'decision':'accept-exact-canonical-preflight-delivery-and-ordinary-engine-binding-actual-data',
 'head':HEAD,'tree':TREE,'soleParent':BASE,'selection':review['selection'],
 'selectedPaths':227,'selectedBytesIncludingSelection':12914000,
 'phaseSummaries':phase_summaries,'newCommands':38,'newExitZero':38,'newRawKernelWaitStatusZero':38,
 'newOwnedDirectChildrenDistinct':38,'signals':0,
 'onlyMutations':all_mutations,'manualWorkflowCommands':0,'replaysOrUnmanifestedCurrentCommands':0,
 'finiteIndexObjects':len(index_objects),'wholeCachedDiffObjects':len(changed_objects(cached_raw)),
 'wholeParentDiffObjects':len(changed_objects(parent_raw)),
 'allSelectedSHA256BytesOIDsAndGitModesMatch':True,'allSelectedChangedAndNoOutsideCommittedPaths':True,
 'exactSingleParentByHEADAllParentsOutputCardinality':True,'nonforceExactSHARefPushAndRemoteURLChecksMatch':True,
 'initialAndFinalIndexOutputsEmpty':True,'defaultWhitespaceCheckedPaths':222,'exactImmutableWhitespaceExceptions':5,
 'preflightCompleteRawRows':12,'outsideSelectedRawRows':2,'protectedByteModesMatch':True,
 'originalCollapsedUntrackedIdentitiesPreserved':2425,
 'commonStoredCollapsedPathsWithIdenticalIdentityModes':2413,
 'priorCollapsedScopesNoLongerListedAfterSelection':12,'newlyExposedEntriesWithinPriorScopes':12,
 'collapsedTransitionsConformToSelectedProjectionsAndPriorScopes':True,
 'original2425EntryIdentitiesAlsoMatchPointInReviewFilesystemMetadata':True,
 'recursiveUntrackedContentInventory':False,
 'allCleanTrackedFilesIndependentlyHashed':False,
 'engine':run,'ordinaryWorkflowContentMatchesDeliveredBlob':True,'ordinaryWorkflowExpectedJobs':6,
 'runtimeCompilerArtifactOrCIResultAccepted':False,
 'historicalClosedCommandsPinnedAsData':71,'historicalExitZero':70,'historicalOriginalStageExit':1,
 'historicalOriginalStageRawWaitStatus':256,
 'combinedLocalCommands':109,'combinedExitZero':108,'combinedHistoricalClosedStageExitOne':1,
 'actualReceiptRows':{phase:identity(OUT/spec[0]) for phase,spec in expected_receipt_rows.items()},
 'sourceReview':identity(OUT/'review/final-source-review.json'),
 'rootPreflightAcceptance':identity(OUT/'preflight-canonical-root-review.json'),
 'rootDeliveryActualReview':identity(OUT/'root-delivery-actual-review.json'),
 'auditArtifactRowsSHA256':hashlib.sha256(json.dumps(sorted(admission_hash_rows,key=lambda r:r['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'readSetRowsSHA256':hashlib.sha256(json.dumps(sorted(READ_ROWS.values(),key=lambda r:r['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'readFiles':len(READ_ROWS),'readBytes':TOTAL,'readFileBoundBytes':2000000,'readAggregateBoundBytes':32000000,
 'checkerPython':sys.version,'checkerInterpreter':sys.executable,
 'reviewerTargetCommandsExecuted':0,'reviewerSubjectOrHelperImportedOrExecuted':False,
 'reviewerGitGhCompilerProductOracleNetworkProcessProbeSignalNativeCaptureUIActions':0,
 'authorityGranted':False}
print(json.dumps(summary,indent=2))

