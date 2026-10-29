"""Independent filesystem/data-only review; never imports or executes subjects."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/github-delivery-axis-binding-stage-recovery'
OWN = OUT / 'review/inspection-actual'
OLD = ROOT / 'verification/github-delivery-axis-binding-followup'
READS = {}
CHECKS = []


def check(name, condition):
    if condition is not True:
        raise AssertionError(name)
    CHECKS.append(name)


def payload(path):
    path = Path(path)
    s = path.lstat()
    check('regular nonlink: ' + str(path.relative_to(ROOT)), stat.S_ISREG(s.st_mode) and not path.is_symlink())
    value = path.read_bytes()
    READS[str(path.relative_to(ROOT))] = {'path': str(path.relative_to(ROOT)), 'bytes': len(value),
                                         'sha256': hashlib.sha256(value).hexdigest()}
    return value


def row(path):
    payload(path)
    return READS[str(Path(path).relative_to(ROOT))]


def pinned(expected):
    check('pinned row: ' + expected['path'], row(ROOT / expected['path']) == expected)


def load(path):
    return json.loads(payload(path))


def fingerprint(path, identity=False):
    file = ROOT / path.rstrip('/')
    s = file.lstat()
    result = {'path': path, 'mode': stat.S_IMODE(s.st_mode), 'type': stat.S_IFMT(s.st_mode)}
    if identity or not stat.S_ISREG(s.st_mode) and not stat.S_ISLNK(s.st_mode):
        result.update(inode=s.st_ino, device=s.st_dev)
    elif stat.S_ISREG(s.st_mode):
        b = payload(file)
        result.update(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
    else:
        result['target'] = os.readlink(file)
    return result


def parse_raw(b):
    tokens = b.split(b'\0')
    check('raw complete nul framing', tokens[-1] == b'' and len(tokens) % 2 == 1)
    result = []
    for pos in range(0, len(tokens)-1, 2):
        meta, path = tokens[pos].decode(), tokens[pos+1].decode()
        fields = meta.split(' ')
        check('raw fixed fields ' + path, len(fields) == 5 and fields[0].startswith(':') and
              all(len(v) == 6 and set(v) <= set('01234567') for v in [fields[0][1:], fields[1]]) and
              all(len(v) == 40 and set(v) <= set('0123456789abcdef') for v in fields[2:4]) and
              fields[4] in ['A', 'M', 'D', 'T'])
        check('raw safe path ' + path, not path.startswith(('/', '-', ':')) and
              all(p not in ['', '.', '..'] for p in path.split('/')))
        result.append({'path': path, 'gitRaw': meta})
    check('raw unique paths', len(result) == len({x['path'] for x in result}))
    return result


def parse_index(b):
    tokens = b.split(b'\0')
    check('index complete nul framing', tokens[-1] == b'')
    result = {}
    for token in tokens[:-1]:
        meta, path = token.split(b'\t')
        mode, oid, stage = meta.decode().split(' ')
        path = path.decode()
        check('index exact selected stage0 object ' + path, path in expected_objects and
              path not in result and stage == '0' and mode == '100644' and
              len(oid) == 40 and set(oid) <= set('0123456789abcdef'))
        result[path] = {'oid': oid, 'mode': mode}
    return result


def parse_status(b):
    tokens = b.split(b'\0')
    check('status complete nul framing', tokens[-1] == b'')
    result = []
    for token in tokens[:-1]:
        text = token.decode()
        check('status simple entry', len(text) > 3 and text[2] == ' ' and not any(x in text[:2] for x in 'RCU'))
        result.append({'status': text[:2], 'path': text[3:]})
    check('status unique paths', len(result) == len({x['path'] for x in result}))
    return result


def time(value):
    return datetime.datetime.fromisoformat(value)


PINS = {
    'authority-exact-inspection.json': (2569, '3501509455e9d92d8694eded31788c895032236b6ce969bb0809929132e72ba8'),
    'inspect_stage_recovery.py': (18195, 'f5bdfa9131eaf1d45c857b6d056153b2fa01ee1c0016e2ede68cc2c8b12bcac8'),
    'owned.py': (29385, '34f1991509d7b156f00b5cc50fcd82ebae81fb414da904c19dcdca70c3eeb987'),
    'inputs.json': (68698, '347f021a32fe4243d0f4cd8f6d3a5b6011d23273b2a96599e4a11548a37b3e15'),
    'argv-inspection.json': (27686, '5ce2d87212340532eceeff653b233aeb156046723ff7824fa0c8297e0956a9f9'),
    'review/inspection-source/source-review.json': (11516, '0f7b7a97dd43f089162ddef19bd15616d43f52169f09333bc98e65a318df2385'),
    'review/inspection-source/seal.json': (1597, 'fac7a2c988733cb5a09881d60ec6a0bb480e5a2af369ca9c5fc54d671712fcb7'),
}
for name, (size, pin_digest) in PINS.items():
    actual = row(OUT / name)
    check('root supplied exact pin: ' + name, (actual['bytes'], actual['sha256']) == (size, pin_digest))
authority = load(OUT / 'authority-exact-inspection.json')
check('actual authority unchanged', payload(OUT / 'authority.json') == payload(OUT / 'authority-exact-inspection.json'))
inputs = load(OUT / 'inputs.json')
manifest = load(OUT / 'argv-inspection.json')
receipt = load(OUT / 'inspection-receipt.json')
data = load(OUT / 'inspection-data.json')
once = load(OUT / 'inspection-once.json')
source_review = load(OUT / 'review/inspection-source/source-review.json')
source_seal = load(OUT / 'review/inspection-source/seal.json')
check('root exact inspection-only authority', authority['authorized'] is True and
      authority['purpose'] == 'fresh-stage-recovery-inspection-only' and authority['phaseLimit'] == 1 and
      authority['repository'] == 'snowdamiz/mixer' and authority['branch'] == 'main' and
      authority['originalAttemptReplayAllowed'] is False and authority['allExistingHoldsUntouched'] is True and
      authority['rootAuthority'] == 'Root authorizes exactly one ten-command read-only stage-recovery inspection after exact v2 source review and actual original17 closure evidence. No stage, commit, push, workflow submission, retry of the original attempt, or held-process action.')
check('all four mutation allowances zero', all(authority[k] == manifest[k] == 0 for k in
      ['stageLimit', 'commitLimit', 'nonforcePushLimit', 'manualWorkflowDispatchLimit']))
for key in ['source', 'helper', 'inputs', 'argvApproval', 'sourceReview', 'failedAttemptReviewSeal', 'selection']:
    pinned(authority[key])
check('source review accepted exact source pins', source_review['decision'] == source_seal['decision'] ==
      'accept-exact-stage-recovery-inspection-source' and source_seal['report'] == row(OUT / 'review/inspection-source/source-review.json') and
      all(source_review[k] == authority[k] == source_seal[k] for k in ['source', 'helper', 'inputs', 'argvApproval']))
for key in ['report', 'readSet']:
    pinned(source_seal[key])
check('source review grants no authority', all(source_seal[k] is False for k in ['authorityGranted', 'continuationAuthorized']))
check('exclusive once marker binds authority', once == {'phase': 'stage-recovery-inspection', 'source': authority['source'],
      'authority': row(OUT / 'authority-exact-inspection.json'), 'retryAllowed': False, 'originalAttemptReplayed': False, 'commandLimit': 10})
check('receipt data pin exact', receipt['data'] == row(OUT / 'inspection-data.json'))
for a,b in [('selection','selection'),('source','source'),('helper','helper'),('argv','argvApproval'),('inputs','inputs'),('failedAttemptReviewSeal','failedAttemptReviewSeal')]:
    check('receipt pin ' + a, receipt[a] == authority[b])
check('receipt authority pin', receipt['authority'] == row(OUT / 'authority-exact-inspection.json'))

for expected in inputs['rows']:
    pinned(expected)
preservation = load(ROOT / data['originalPreservation']['path'])
pinned(data['originalPreservation'])
check('historical 17 phase counts', inputs['originalCommandCount'] == len(inputs['originalCommands']) == 17 and
      inputs['originalPreflightCount'] == 9 and inputs['originalDeliveryCount'] == 8)
old_labels = set()
for suffix in ['.plan.json', '.started.json', '.admission.json', '.command.json']:
    labels = {p.name[:-len(suffix)] for p in OLD.glob('*' + suffix)}
    check('historical exact label set ' + suffix, labels == {x['label'] for x in inputs['originalCommands']})
    old_labels |= labels

CLOSURE_TRUE = ['admitted', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF',
                'signalAuthorityRetired', 'separateOutputPipes', 'finalReapAttempted',
                'implicitPopenReapingDisabled', 'noSignalAfterFinalReapOrLostAuthority']


def verify_command(label, directory, argv, ordinal, auth_sha, expected_exit):
    plan, started, admission, terminal = [load(directory / (label + suffix)) for suffix in
                                         ['.plan.json', '.started.json', '.admission.json', '.command.json']]
    check('command argv and ordinal ' + label, plan['argv'] == admission['argv'] == terminal['argv'] == argv and
          plan['ordinal'] == ordinal and plan['cwd'] == str(ROOT))
    pid = terminal['ownedPID']
    identity = {'pid': pid, 'pgid': pid, 'sid': pid}
    check('command startup and admitted identity ' + label, started['ownedPID'] == pid and started['targetReleased'] is False and
          terminal['ownedPGID'] == pid and terminal['identity'] == admission['identity'] == identity and
          admission['parentObservedPGID'] == admission['parentObservedSID'] == pid and
          admission['targetReleasedOnlyAfterPersistedAdmission'] is True)
    check('command exact raw kernel reap ' + label, terminal['rawWaitPID'] == pid and
          terminal['exit'] == expected_exit and terminal['rawWaitStatus'] == expected_exit*256)
    check('command closure facts ' + label, all(terminal[k] is True for k in CLOSURE_TRUE) and
          terminal['postReapAbsenceProbeCount'] == 1 and terminal['signals'] == [] and
          terminal['signalAuthorityLost'] is None and terminal['stopReason'] is None and terminal['failure'] is None and
          terminal['sensitiveOutputRejected'] is False and terminal['postReapProbeSuccessOrEPERMHeldWithoutRetry'] is False)
    check('command authority and time order ' + label, terminal['authoritySHA256'] == auth_sha and
          time(plan['at']) < time(started['at']) < time(admission['at']) < time(terminal['at']))
    for stream in ['stdout', 'stderr']:
        pinned(terminal[stream])
        check('command observed stream length ' + label + ' ' + stream, terminal[stream+'ObservedBytes'] == terminal[stream]['bytes'])
    return plan, started, admission, terminal


original = []
for expected in inputs['originalCommands']:
    for record in expected['records'].values():
        pinned(record)
    parts = verify_command(expected['label'], OLD, expected['effectiveArgv'], expected['ordinal'],
                           expected['authoritySHA256'], expected['exit'])
    terminal = parts[-1]
    check('historical stream row binding ' + expected['label'], all(terminal[k] == expected['records'][k] for k in ['stdout','stderr']))
    check('only historical stage failed ' + expected['label'], expected['exit'] == (1 if expected['label'] == 'delivery-followup-stage' else 0))
    original.append({'label': expected['label'], 'ordinal': expected['ordinal'], 'ownedPID': terminal['ownedPID'],
                     'exit': terminal['exit'], 'rawWaitStatus': terminal['rawWaitStatus'], 'signals': 0,
                     'separateStreams': [terminal['stdout'], terminal['stderr']], 'allClosureFacts': True})
for name in inputs['originalAbsent']:
    check('historical required absence ' + name, not (OLD / name).exists() and not (OLD / name).is_symlink())
failed_seal = load(ROOT / inputs['failedReviewSeal']['path'])
failed_report = load(ROOT / inputs['failedReviewReport']['path'])
check('failed attempt remains closed without retry', failed_seal['decision'] == 'accept-failed-delivery-prefix-evidence-no-completion-or-retry' and
      failed_seal['report'] == inputs['failedReviewReport'] and failed_seal['noRetryOrRecoveryAuthorityGranted'] is True and
      failed_report['attemptedCommands'] == 8 and failed_report['successfulCommands'] == 7 and
      failed_report['failure']['exit'] == 1 and failed_report['failure']['rawWaitStatus'] == 256 and
      failed_report['failure']['ignoredSelectedPaths'] == inputs['ignoredSelectedPaths'] and
      failed_report['commitPushDispatchObserved'] == {'commit':False,'push':False,'dispatch':False})

selection = load(ROOT / inputs['selection']['path'])
pinned(inputs['selection'])
selected_rows = selection['selectedRows'] + [{**inputs['selection'], 'mode':'100644'}]
check('selected exact cardinality and bytes', len(selected_rows) == len({x['path'] for x in selected_rows}) == 123 and
      sum(x['bytes'] for x in selected_rows) == 4897969)
objects = []
for expected in sorted(selected_rows, key=lambda x:x['path']):
    pinned({k:expected[k] for k in ['path','bytes','sha256']})
    file = ROOT / expected['path']
    check('selected git regular nonexecutable mode ' + expected['path'], expected['mode'] == '100644' and
          stat.S_ISREG(file.lstat().st_mode) and not stat.S_IMODE(file.lstat().st_mode)&0o111 and
          not any(p.is_symlink() for p in file.parents))
    b = payload(file)
    objects.append({'path':expected['path'],'oid':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':'100644'})
object_digest = hashlib.sha256(json.dumps(objects,separators=(',',':')).encode()).hexdigest()
check('all 123 full Git blobs independently reconstructed', objects == inputs['expectedObjects'] and object_digest ==
      inputs['allSelectedObjectDigestSHA256'] == data['allSelectedObjectDigestSHA256'] ==
      '8c59481511bc90e907c76f6b18cbfc41b12568706c60d47b9f507c51347554bd')
expected_objects = {x['path']:{'oid':x['oid'],'mode':x['mode']} for x in objects}
selected = set(expected_objects)
for expected in preservation['tracked'] + preservation['protectedSnapshots']:
    check('outside tracked filesystem hash mode ' + expected['path'], fingerprint(expected['path']) == expected)
check('wrangler exact identity', fingerprint('.wrangler') == preservation['wrangler'] ==
      {'path':'.wrangler','mode':493,'type':16384,'inode':134689423,'device':16777233})
check('artifact store absence', not (ROOT/'hosted/lib/mixer_hosted/artifacts/store.ex').exists() and
      not (ROOT/'hosted/lib/mixer_hosted/artifacts/store.ex').is_symlink())
for expected in preservation['untrackedCollapsed']:
    check('prior collapsed identity ' + expected['path'], fingerprint(expected['path'], True) == expected)
check('fresh recovery exact directory identity', fingerprint(inputs['newRecoveryDirectoryIdentity']['path'], True) ==
      inputs['newRecoveryDirectoryIdentity'] == {'path':'verification/github-delivery-axis-binding-stage-recovery/',
      'mode':493,'type':16384,'inode':167208059,'device':16777233})

names = ['git-version','head','branch','origin','push-url','remote-main','index-raw','index-selected','worktree-raw','collapsed-status']
check('manifest exact ten names and bounded session', [x['name'] for x in manifest['commands']] == names and
      manifest['session'] == {'seconds':240,'count':10,'prefix':'stage-recovery-inspection-'} and manifest['commandOrderRequired'] is True)
check('manifest finite 123 paths', manifest['commands'][7]['argv'] == ['git','ls-files','--stage','-z','--',*sorted(selected)])
exact_read_argv = [
    ['git','--version'], ['git','rev-parse','HEAD','HEAD^{tree}','HEAD^'], ['git','branch','--show-current'],
    ['git','remote','get-url','origin'], ['git','remote','get-url','--push','--all','origin'],
    ['git','ls-remote','origin','refs/heads/main'], ['git','diff','--cached','--raw','--no-abbrev','--no-renames','-z'],
    ['git','ls-files','--stage','-z','--',*sorted(selected)], ['git','diff','--raw','--no-abbrev','--no-renames','-z'],
    ['git','status','--porcelain=v1','-z','--untracked-files=normal']]
new_commands, streams, aggregate = [], {}, 0
prior_terminal_at = None
for ordinal, (name, approved, exact) in enumerate(zip(names,manifest['commands'],exact_read_argv),1):
    label = 'stage-recovery-inspection-' + name
    effective = ['git','-c','gc.auto=0','-c','maintenance.auto=false',*exact[1:]]
    check('manifest exact allowed read ' + name, approved['argv'] == exact and approved['effectiveArgv'] == effective and approved['kind'] == 'read')
    plan, started, admission, terminal = verify_command(label, OUT, effective, ordinal,
                                                        row(OUT/'authority-exact-inspection.json')['sha256'],0)
    check('new plan custody limits ' + name, all(plan[k] == v for k,v in {'activeSeconds':25,'admissionSeconds':5,'cleanupSeconds':6,
          'streamCapEachBytes':8388608,'aggregateCapBytes':33554432,'sessionCommandLimit':10,'freshSessionRequired':True,
          'targetReleaseAfterPersistedAdmissionOnly':True,'isolatedNoSiteBytecodeDisabled':True}.items()))
    check('new admission exact limits ' + name, all(admission[k] == v for k,v in
          {'activeSeconds':25,'cleanupSeconds':6,'streamCapEachBytes':8388608}.items()))
    check('new record WNOWAIT terminal status ' + name, terminal['wnowaitSupported'] is True and terminal['terminalObservedWithoutReap'] is True and
          terminal['terminalObservation'] == [1,0] and terminal['unresolvedChildRetainedUntilIsolatedDriverExit'] is True and
          terminal['interpreterExitIsNotCustodyEvidence'] is True)
    check('new sequential dispatch ' + name, prior_terminal_at is None or time(plan['at']) > time(prior_terminal_at))
    prior_terminal_at = terminal['at']
    aggregate += terminal['stdout']['bytes'] + terminal['stderr']['bytes']
    check('new cumulative output accounting ' + name, terminal['aggregateOutputBytes'] == aggregate)
    streams[name] = payload(ROOT/terminal['stdout']['path'])
    summary = {'name':label,'exit':0,'admitted':True,'stopReason':None,'directChildReaped':True,'ownedGroupAbsent':True,
               'stdoutEOF':True,'stderrEOF':True,'sensitiveOutputRejected':False}
    check('receipt command row ' + name, receipt['commands'][ordinal-1] == summary)
    new_commands.append({'label':label,'ordinal':ordinal,'ownedPID':terminal['ownedPID'],'exit':0,'rawWaitStatus':0,
                         'allClosureFacts':True,'postReapAbsenceProbeCount':1,'signals':0,
                         'plan':row(OUT/(label+'.plan.json')),'started':row(OUT/(label+'.started.json')),
                         'admission':row(OUT/(label+'.admission.json')),'terminal':row(OUT/(label+'.command.json')),
                         'stdout':terminal['stdout'],'stderr':terminal['stderr']})
for suffix in ['.plan.json','.started.json','.admission.json','.command.json']:
    check('exact ten new labels ' + suffix, {p.name[:-len(suffix)] for p in OUT.glob('stage-recovery-inspection-*'+suffix)} ==
          {'stage-recovery-inspection-'+x for x in names})
check('no other actual command labels in fresh namespace', {p.name[:-len('.command.json')] for p in OUT.glob('*.command.json')} ==
      {'stage-recovery-inspection-'+x for x in names})
check('exact ten receipt rows', len(receipt['commands']) == 10)

base = {'head':'2cea1013151ccc38bb635fb4755793cd25a0bd1b','tree':'830e859979d2ea95335d8cb8ea28ac8caaa0614b'}
head = streams['head'].decode().splitlines()
check('base exact head tree parent and branch', head == [base['head'],base['tree'],'c89b4d1657fc46581d8788169f9c961a2413c4f4'] and
      authority['baseline'] == inputs['baseline'] == base and selection['baseline'] == {'revision':base['head'],'tree':base['tree']} and
      streams['branch'] == b'main\n' and [data[k] for k in ['head','tree','parent']] == head)
check('exact fetch push and remote main', streams['origin'] == streams['push-url'] == b'https://github.com/snowdamiz/mixer.git\n' and
      streams['remote-main'] == (base['head']+'\trefs/heads/main\n').encode())
check('exact recorded git version', streams['git-version'] == b'git version 2.56.0\n' and receipt['tools']['git'] == 'git version 2.56.0')
cached = parse_raw(streams['index-raw'])
index = parse_index(streams['index-selected'])
pending = {}
for item in cached:
    path, fields = item['path'], item['gitRaw'].split(' ')
    check('cached complete selected exact new object ' + path, path in selected and fields[4] in ['A','M'] and
          {'oid':fields[3],'mode':fields[1]} == expected_objects[path] == index[path])
    if fields[4] == 'A':
        check('cached added path has absent baseline object ' + path, fields[0] == ':000000' and fields[2] == '0'*40)
    else:
        check('cached modified path has regular baseline object ' + path, fields[0] == ':100644' and fields[2] != '0'*40)
    pending[path] = {'oid':fields[3],'mode':fields[1]}
check('all selected index matches expected sources', all(v == expected_objects[p] for p,v in index.items()))
matching = sorted(index)
remaining = sorted(selected-set(index))
check('exact 66 staged and exact 57 known ignored remainder', len(cached) == len(index) == len(pending) == 66 and
      set(pending) == set(index) and len(remaining) == 57 and remaining == sorted(inputs['ignoredSelectedPaths']))
check('data exact cached index and classification', data['cachedRawRows'] == cached and data['selectedIndexObjects'] == index and
      data['pendingChangedObjects'] == pending and data['matchingSourceIndexPaths'] == matching and data['remainingSourceIndexPaths'] == remaining)
worktree = parse_raw(streams['worktree-raw'])
check('complete worktree exact outside two changes', worktree == preservation['otherDirtyTracked'] == data['completeWorktreeRawRows'] and len(worktree) == 2)
status = parse_status(streams['collapsed-status'])
check('data exact full collapsed status', status == data['collapsedStatus'])
before = preservation['statusCollapsed']
outside_before = [x for x in before if x['status'] != '??' and x['path'] not in selected]
outside_after = [x for x in status if x['status'] != '??' and x['path'] not in selected]
check('outside tracked collapsed statuses unchanged', outside_before == outside_after)
prior_scopes = [x['path'] for x in before if x['status'] == '??']
new_scopes = [x['path'] for x in status if x['status'] == '??']
projection = lambda value: any(p == value.rstrip('/') or p.startswith(value.rstrip('/')+'/') for p in selected)
covered = lambda value, old: value == old or old.endswith('/') and value.startswith(old)
additions = [p for p in new_scopes if p not in prior_scopes]
removals = [p for p in prior_scopes if p not in new_scopes]
for path in new_scopes:
    check('new collapsed scope confined ' + path, projection(path) or path == inputs['newRecoveryDirectoryIdentity']['path'] or
          any(covered(path,p) for p in prior_scopes))
for path in prior_scopes:
    check('prior nonselected collapsed scope still represented ' + path, projection(path) or any(covered(x,path) or covered(path,x) for x in new_scopes))
check('literal removed scopes all selected projections', all(projection(p) for p in removals))
check('collapsed proof scope exact', data['collapsedStatusProof'] == {'outsideTrackedStatusUnchanged':True,
      'newUntrackedEntriesConfinedToPriorCollapsedScopesOrExactRecoveryDirectory':True,
      'removedCollapsedEntriesConfinedToSelectedProjections':True,'newRecoveryDirectoryIdentity':inputs['newRecoveryDirectoryIdentity'],
      'recursiveUntrackedContentProof':False})
check('no inferred completion or continuation', receipt['decision'] == 'ten-read-inspection-complete-pending-independent-actual-review' and
      receipt['pendingChangedPaths'] == receipt['matchingSourceIndexPaths'] == 66 and receipt['remainingSourceIndexPaths'] == 57 and
      all(receipt[k] is False for k in ['stageCommitPushDispatchPerformed','originalAttemptReplayed','continuationAuthorized']) and
      all(receipt[k] is True for k in ['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF','allExistingHoldsUntouched']) and
      data['unrelatedStagedPaths'] == 0 and data['remainingConfinedToKnownIgnored57'] is True and
      data['allCleanTrackedFilesIndependentlyHashed'] is False)
for name, (size, pin_digest) in PINS.items():
    actual = row(OUT / name)
    check('final root supplied exact pin: ' + name, (actual['bytes'], actual['sha256']) == (size, pin_digest))

OWN.mkdir(parents=True,exist_ok=True)
readset = {'schema':1,'files':sorted(READS.values(),key=lambda x:x['path'])}
(OWN/'read-set.json').write_text(json.dumps(readset,indent=2)+'\n')
report = {
    'schema':1,'decision':'accept-exact-ten-read-stage-recovery-inspection-result',
    'reviewer':'/root/axis_binding_stage_inspection_actual_review',
    'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope':'Independent actual filesystem and retained-record/data audit only. No continuation authority.',
    'authority':row(OUT/'authority-exact-inspection.json'),'receipt':row(OUT/'inspection-receipt.json'),'data':row(OUT/'inspection-data.json'),
    'source':authority['source'],'helper':authority['helper'],'inputs':authority['inputs'],'argv':authority['argvApproval'],
    'independentSourceReview':row(OUT/'review/inspection-source/seal.json'),
    'baseline':base,'branch':'main','remote':'https://github.com/snowdamiz/mixer.git',
    'checkCount':len(CHECKS),'checks':CHECKS,'findings':[],
    'actualCommands':new_commands,'closedCommands':10,'aggregateNewStreamBytes':aggregate,
    'originalCommands':original,'historicalPreflightCount':9,'historicalDeliveryCount':8,'historicalSuccessfulCommands':16,
    'historicalFailedStage':{'exit':1,'rawWaitStatus':256,'noReplay':True},
    'selectedFilesystem':{'paths':123,'bytes':4897969,'mode':'100644','fullBlobDigestSHA256':object_digest,'unchanged':True},
    'indexClassification':{'completeCachedRawRows':66,'selectedIndexRows':66,'pendingChangedPaths':66,'remainingPaths':57,
                           'remainingExactlyKnownIgnoredPaths':True,'unrelatedStagedPaths':0,'failedAddAtomicityAssumed':False},
    'preservation':{'outsideDirtyTrackedPaths':2,'protectedSnapshots':4,'priorCollapsedIdentities':len(preservation['untrackedCollapsed']),
                    'wrangler':preservation['wrangler'],'artifactStoreAbsent':True,'newRecoveryDirectoryIdentity':inputs['newRecoveryDirectoryIdentity'],
                    'beforeCollapsedRows':len(before),'afterCollapsedRows':len(status),'addedUntrackedScopes':additions,
                    'removedUntrackedScopes':removals,'recursiveUntrackedContentsVerified':False,'allCleanTrackedFilesIndependentlyHashed':False},
    'readSet':row(OWN/'read-set.json'),
    'reviewExecution':{'command':'python3 -I -S -B verification/github-delivery-axis-binding-stage-recovery/review/inspection-actual/audit_data.py',
                      'python':sys.version,'interpreter':sys.executable,'subjectImports':0,'subjectOrHelperExecutions':0,
                      'gitGhCompilerNetworkProcessProbeSignalNativeUIActions':0,
                      'writesConfinedTo':'verification/github-delivery-axis-binding-stage-recovery/review/inspection-actual/'},
    'limitations':[
        'Kernel waits, group absence, stream EOF and admission are verified from retained exact records; this review performs no live process probing.',
        'The root outer tool cell 58542 completion is supplied by root; this reviewer has no independent access to that parent tool session.',
        'Complete raw diff and declared baseline/tree retain the clean tracked scope; no independent whole-tree content hash is claimed.',
        'Preexisting untracked scopes retain identity and mode checks only, with no recursive content inventory.',
        'The result classifies an existing partial index after a failed add. The original delivery attempt remains consumed.',
        'No stage, force-add, commit, push, workflow dispatch, original-attempt replay or continuation is authorized by this report.',
        'All existing native, UI/capture, device, compiler, process, custody and operational holds remain in force.'
    ],
    'stageCommitPushDispatchPerformedByReviewedInspection':False,'originalAttemptReplayed':False,
    'authorityGranted':False,'continuationAuthorized':False,'allExistingHoldsUntouched':True,
}
report['checks'] = list(CHECKS)
report['checkCount'] = len(report['checks'])
(OWN/'actual-review.json').write_text(json.dumps(report,indent=2)+'\n')
seal = {'schema':1,'decision':report['decision'],'reviewer':report['reviewer'],
        'report':row(OWN/'actual-review.json'),'readSet':row(OWN/'read-set.json'),
        'auditMethod':row(OWN/'audit_data.py'),'authority':report['authority'],'receipt':report['receipt'],'data':report['data'],
        'findings':0,'closedCommands':10,'pendingChangedPaths':66,'remainingSourceIndexPaths':57,
        'authorityGranted':False,'continuationAuthorized':False,'allExistingHoldsUntouched':True}
(OWN/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'decision':report['decision'],'checks':report['checkCount'],'readFiles':len(readset['files']),
                  'seal':row(OWN/'seal.json'),'report':seal['report'],'readSet':seal['readSet']},indent=2))
