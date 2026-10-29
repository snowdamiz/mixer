"""Bounded filesystem/data audit only; never imports or invokes subject code."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import json
import os
import stat
from datetime import datetime, timezone

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
BASE = ROOT / 'verification/github-delivery-axis-binding-followup'
OUT = BASE / 'review/delivery-actual-review'
BASELINE = '2cea1013151ccc38bb635fb4755793cd25a0bd1b'
BASELINE_TREE = '830e859979d2ea95335d8cb8ea28ac8caaa0614b'
EXPECTED_OBJECT_DIGEST = '8c59481511bc90e907c76f6b18cbfc41b12568706c60d47b9f507c51347554bd'
checks = []
inputs = {}

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def row(path):
    path = ROOT / path if not isinstance(path, Path) else path
    st = path.lstat()
    check('regular-file:' + str(path.relative_to(ROOT)), stat.S_ISREG(st.st_mode))
    payload = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}

def load(path):
    path = ROOT / path if not isinstance(path, Path) else path
    value = row(path)
    inputs[value['path']] = value
    return json.loads(path.read_bytes())

def pin(expected):
    actual = row(ROOT / expected['path'])
    check('pin:' + expected['path'], all(actual[k] == expected[k] for k in ('path', 'bytes', 'sha256') if k in expected))
    inputs[actual['path']] = actual
    return actual

def fingerprint(value):
    p = ROOT / value.rstrip('/')
    try:
        st = p.lstat()
    except FileNotFoundError:
        return {'path': value, 'missing': True}
    result = {'path': value, 'mode': stat.S_IMODE(st.st_mode), 'type': stat.S_IFMT(st.st_mode)}
    if stat.S_ISREG(st.st_mode):
        payload = p.read_bytes()
        result.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    elif stat.S_ISLNK(st.st_mode):
        result['target'] = os.readlink(p)
    else:
        result.update(inode=st.st_ino, device=st.st_dev)
    return result

def collapsed_identity(value):
    st = (ROOT / value.rstrip('/')).lstat()
    return {'path': value, 'mode': stat.S_IMODE(st.st_mode), 'type': stat.S_IFMT(st.st_mode),
            'inode': st.st_ino, 'device': st.st_dev}

def raw_rows(payload):
    parts = payload.split(b'\0')
    check('raw-terminal-NUL-and-even-pairs', len(parts) % 2 == 1 and parts[-1] == b'')
    result = []
    for i in range(0, len(parts) - 1, 2):
        meta, name = parts[i].decode(), parts[i + 1].decode()
        fields = meta.split()
        check('raw-five-fields:' + name, len(fields) == 5 and fields[-1] in ('M', 'D', 'T', 'A'))
        result.append({'path': name, 'gitRaw': meta})
    return result

authority_path = BASE / 'authority-snapshot-delivery-followup.json'
pin({'path': str(authority_path.relative_to(ROOT)), 'bytes': 6309,
     'sha256': '27e506c361b2dddee4c38b304685c66c44285180dba6094e4bbc616f48bb5826'})
authority = load(authority_path)
authority_hash = inputs[str(authority_path.relative_to(ROOT))]['sha256']
check('delivery-authority-baseline', authority['baseline'] == {'head': BASELINE, 'tree': BASELINE_TREE})
check('delivery-authority-limits', authority['commitLimit'] == authority['nonforcePushLimit'] == 1
      and authority['manualWorkflowDispatchLimit'] == 0 and authority['retryRerunFallbackAllowed'] is False)
for value in authority['driverSources']:
    pin(value)
for key in ('selection', 'helper', 'driverPacketSeal', 'driverReviewSeal', 'formattingScope'):
    pin(authority[key])
for value in authority['selectionReview'].values():
    pin(value)
pin(authority['acceptedPreflight']['seal'])
for value in authority['acceptedPreflight']['rows']:
    pin(value)
source_seal = load(ROOT / authority['driverReviewSeal']['path'])
for value in source_seal['reports']:
    pin(value)
pre = load(BASE / 'preflight-followup.json')
preservation = load(BASE / 'preservation-followup-local.json')
pre_seal = load(BASE / 'preflight-followup-root-review.json')
check('accepted-preflight-sealed-decision', pre_seal['decision'] == 'accept-exact-nine-command-preflight-result')
check('preflight-baseline-and-initial-index', pre['head'] == BASELINE and pre['tree'] == BASELINE_TREE
      and pre['indexEmpty'] is True and pre['originMain'] == BASELINE)
check('preflight-two-dirty-and-collapsed-counts', len(preservation['tracked']) == 2
      and len(preservation['otherDirtyTracked']) == 2 and len(preservation['untrackedCollapsed']) == 2416)

selection = load(ROOT / authority['selection']['path'])
selected_rows = selection['selectedRows'] + [{**authority['selection'], 'mode': '100644'}]
selected_paths = {v['path'] for v in selected_rows}
check('selection-122-payload-plus-self-123', len(selection['selectedRows']) == 122 and len(selected_paths) == 123)
check('selection-payload-order', [v['path'] for v in selection['selectedRows']] == sorted(v['path'] for v in selection['selectedRows']))
check('selection-no-formatting-exclusions', selection['formatting']['excludeImmutablePaths'] == [])
manifest = load(BASE / 'manifest-followup.json')
check('manifest-order-and-members', manifest['members'] == selected_rows and manifest['paths'] == 123)
check('selected-total-bytes', sum(v['bytes'] for v in selected_rows) == manifest['bytes'] == 4897969)
object_rows = []
for expected in selected_rows:
    pin(expected)
    p = ROOT / expected['path']
    check('selected-file-mode:' + expected['path'], expected['mode'] == '100644' and stat.S_IMODE(p.lstat().st_mode) == 0o644)
    payload = p.read_bytes()
    object_rows.append({'path': expected['path'], 'oid': hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest(), 'mode': '100644'})
object_rows.sort(key=lambda v: v['path'])
object_digest = hashlib.sha256(json.dumps(object_rows, separators=(',', ':')).encode()).hexdigest()
check('current-selected-expected-blob-mode-digest', object_digest == EXPECTED_OBJECT_DIGEST)

argv = load(BASE / 'argv-delivery-axis-binding.json')
pin(authority['argvApprovals']['delivery-followup'])
check('argv-phase-and-count', argv['phase'] == 'delivery-followup' and argv['session']['count'] == len(argv['commands']) == 22)
prefix = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']
check('effective-Git-prefix', argv['gitEffectivePrefix'] == prefix)
for command in argv['commands']:
    check('approved-vector:' + command['name'], all(type(t) is str for t in command['argv'])
          and command['argv'][0] == 'git' and command['effectiveArgv'] == prefix + command['argv'][1:])
check('typed-binding-only-future-committed-SHA', list(argv['typedBindings']) == ['COMMITTED_SHA'])
expected_names = [v['name'] for v in argv['commands']]
attempted_names = expected_names[:8]
actual_names = sorted(p.name[len('delivery-followup-'):-len('.command.json')]
                      for p in BASE.glob('delivery-followup-*.command.json'))
check('exact-eight-command-record-inventory', actual_names == sorted(attempted_names))
command_results = []
aggregate = 0
last_end = None
for ordinal, approved in enumerate(argv['commands'][:8], 1):
    name = 'delivery-followup-' + approved['name']
    plan = load(BASE / (name + '.plan.json'))
    started = load(BASE / (name + '.started.json'))
    admission = load(BASE / (name + '.admission.json'))
    command = load(BASE / (name + '.command.json'))
    check('exact-effective-vector:' + name, plan['argv'] == admission['argv'] == command['argv'] == approved['effectiveArgv'])
    check('ordered-session-plan:' + name, plan['ordinal'] == ordinal and plan['sessionCommandLimit'] == 22
          and plan['cwd'] == str(ROOT) and plan['activeSeconds'] == 25
          and plan['admissionSeconds'] == 5 and plan['cleanupSeconds'] == 6)
    check('source-isolated-admission:' + name, plan['freshSessionRequired'] is True
          and plan['isolatedNoSiteBytecodeDisabled'] is True and plan['targetReleaseAfterPersistedAdmissionOnly'] is True)
    check('record-chronology:' + name, plan['at'] <= started['at'] <= admission['at'] <= command['at']
          and (last_end is None or last_end <= plan['at']))
    last_end = command['at']
    pid = command['ownedPID']
    check('exact-admitted-identity:' + name, type(pid) is int and pid > 0
          and command['identity'] == admission['identity'] == {'pid': pid, 'pgid': pid, 'sid': pid}
          and started['ownedPID'] == admission['parentObservedPGID'] == admission['parentObservedSID'] == command['ownedPGID'] == pid
          and started['targetReleased'] is False and admission['targetReleasedOnlyAfterPersistedAdmission'] is True)
    expected_exit = 1 if ordinal == 8 else 0
    check('exact-terminal-status:' + name, command['exit'] == expected_exit and command['admitted'] is True
          and command['rawWaitPID'] == pid and command['rawWaitStatus'] == expected_exit << 8
          and command['terminalObservation'] == [1, expected_exit]
          and command['directChildReaped'] is True and command['ownedGroupAbsent'] is True)
    check('custody-retirement-and-EOF:' + name, command['wnowaitSupported'] is True
          and command['terminalObservedWithoutReap'] is True and command['signalAuthorityRetired'] is True
          and command['signalAuthorityLost'] is None and command['finalReapAttempted'] is True
          and command['implicitPopenReapingDisabled'] is True and command['postReapAbsenceProbeCount'] == 1
          and command['noSignalAfterFinalReapOrLostAuthority'] is True
          and command['postReapProbeSuccessOrEPERMHeldWithoutRetry'] is False
          and command['stdoutEOF'] is True and command['stderrEOF'] is True
          and command['separateOutputPipes'] is True and command['signals'] == [])
    check('command-authority-and-output-clean:' + name, command['authoritySHA256'] == authority_hash
          and command['sensitiveOutputRejected'] is False and command['stopReason'] is None and command['failure'] is None)
    for stream in ('stdout', 'stderr'):
        actual = pin(command[stream])
        check('full-stream-retained:' + name + ':' + stream, actual['bytes'] == command[stream + 'ObservedBytes']
              and actual['bytes'] <= plan['streamCapEachBytes'])
        aggregate += actual['bytes']
    check('aggregate-output:' + name, command['aggregateOutputBytes'] == aggregate <= plan['aggregateCapBytes'])
    command_results.append({'ordinal': ordinal, 'name': name, 'command': row(BASE / (name + '.command.json')),
                            'argvExact': True, 'exit': expected_exit, 'ownedPID': pid,
                            'rawWaitPID': pid, 'rawWaitStatus': expected_exit << 8,
                            'directChildReaped': True, 'ownedGroupAbsent': True, 'postReapAbsenceProbeCount': 1,
                            'stdoutEOF': True, 'stderrEOF': True, 'signals': [], 'signalAuthorityRetired': True,
                            'stdout': command['stdout'], 'stderr': command['stderr']})

def stdout(name):
    return (BASE / ('delivery-followup-' + name + '.stdout')).read_bytes()

check('observed-baseline-head-tree', stdout('head').decode().splitlines() == [BASELINE, BASELINE_TREE])
check('observed-branch', stdout('branch') == b'main\n')
check('observed-fetch-and-push-URL', stdout('origin') == stdout('push-url-before-stage') == b'https://github.com/snowdamiz/mixer.git\n')
check('observed-remote-main-baseline', stdout('remote-before').decode().split() == [BASELINE, 'refs/heads/main'])
check('observed-initial-empty-index', stdout('index-before') == b'')
raw_before = stdout('before-diff')
pre_raw_path = BASE / 'preflight-followup-complete-raw-diff.stdout'
pin(pre_seal['commands'][-1]['command'])
pre_raw_command = load(BASE / 'preflight-followup-complete-raw-diff.command.json')
pin(pre_raw_command['stdout'])
check('complete-raw-diff-unchanged-before-stage', raw_before == pre_raw_path.read_bytes())
raw = raw_rows(raw_before)
outside = [v for v in raw if v['path'] not in selected_paths]
check('complete-outside-dirty-raw-diff-match', outside == preservation['otherDirtyTracked'])
for expected in preservation['tracked'] + preservation['protectedSnapshots']:
    check('outside-current-byte-mode-preserved:' + expected['path'], fingerprint(expected['path']) == expected)
check('wrangler-current-identity-preserved', fingerprint('.wrangler') == preservation['wrangler'])
check('artifacts-store-absent', not (ROOT / 'hosted/lib/mixer_hosted/artifacts/store.ex').exists())
for expected in preservation['untrackedCollapsed']:
    check('collapsed-current-identity:' + expected['path'], collapsed_identity(expected['path']) == expected)
check('baseline-clean-tracked-proof-bound', preservation['cleanTrackedSnapshot']['head'] == BASELINE
      and preservation['cleanTrackedSnapshot']['tree'] == BASELINE_TREE)

once = load(BASE / 'delivery-followup-once.json')
stage_plan = load(BASE / 'delivery-followup-stage.plan.json')
check('once-reserved-before-stage', once['oneCommitNonforcePushAuthorized'] is True and once['retryOnUnknownOutcome'] is False
      and once['paths'] == 123 and once['selection'] == authority['selection'] and once['at'] <= stage_plan['at'])
pathspec_admission = load(BASE / 'stage-followup-pathspec-admission.json')
pathspec_row = pin(pathspec_admission['pathspec'])
pathspec = (ROOT / pathspec_row['path']).read_bytes()
check('exact-stage-selected-NUL-allowlist', pathspec == b''.join(v.encode() + b'\0' for v in sorted(selected_paths))
      and pathspec_admission['paths'] == 123 and pathspec_admission['selection'] == authority['selection'])
stage_stderr = (BASE / 'delivery-followup-stage.stderr').read_text()
lines = stage_stderr.splitlines()
ignored = [line for line in lines if line.startswith('verification/')]
check('explicit-ignore-failure', lines[0] == 'The following paths are ignored by one of your .gitignore files:'
      and len(ignored) > 0 and 'hint: Use -f if you really want to add them.' in lines)
check('all-rejected-ignore-subjects-within-selected', all(v in selected_paths or any(p.startswith(v + '/') for p in selected_paths) for v in ignored))
ignored_selected = sorted(p for p in selected_paths if any(p == v or p.startswith(v + '/') for v in ignored))
ignore_policy = row(ROOT / 'verification/github-delivery-axis-expression-followup/.gitignore')
inputs[ignore_policy['path']] = ignore_policy
missing = []
for approved in argv['commands'][8:]:
    for suffix in ('.plan.json', '.started.json', '.admission.json', '.command.json', '.stdout', '.stderr'):
        p = BASE / ('delivery-followup-' + approved['name'] + suffix)
        check('unstarted-suffix-absent:' + p.name, not p.exists())
    missing.append(approved['name'])
for name in ('delivery-followup-receipt.json', 'committed-followup.json', 'committed-followup-objects.json',
             'staged-followup-all-index-objects-local.json', 'staged-followup-changed-objects-local.json',
             'push-followup-once.json', 'preservation-followup-after-local.json', 'CUSTODY-UNRESOLVED.json'):
    check('later-result-absent:' + name, not (BASE / name).exists())

report = {
    'schema': 1, 'decision': 'accept-failed-delivery-prefix-evidence-no-completion-or-retry',
    'at': datetime.now(timezone.utc).isoformat(), 'reviewer': '/root/axis_binding_delivery_actual_review',
    'scope': 'Independent pure filesystem/data audit of exact attempted eight-command prefix; no subject code imported or executed.',
    'authoritySnapshot': inputs[str(authority_path.relative_to(ROOT))], 'argvManifest': inputs[str((BASE / 'argv-delivery-axis-binding.json').relative_to(ROOT))],
    'baseline': {'head': BASELINE, 'tree': BASELINE_TREE},
    'newHead': None, 'newTree': None, 'parentTreeOrCommittedDiffVerified': False,
    'attemptedCommands': 8, 'successfulCommands': 7, 'failedCommands': 1, 'approvedTotal': 22,
    'commands': command_results, 'aggregateStreamBytes': aggregate,
    'terminalClosure': {'exactKernelWaitMatchesAllEight': True, 'ownedGroupsRecordedAbsent': 8,
                        'bothSeparateEOF': 8, 'absenceProbes': 8, 'signals': 0,
                        'authorityRetired': 8, 'noUnresolvedCustodyMarker': True},
    'failure': {'ordinal': 8, 'name': 'stage', 'exit': 1, 'rawWaitStatus': 256,
                'stderr': command_results[-1]['stderr'], 'ignoredSubjects': ignored,
                'ignoredSubjectCount': len(ignored), 'selectedFilesCoveredByIgnoredSubjects': len(ignored_selected),
                'ignoredSelectedPaths': ignored_selected, 'ignorePolicy': ignore_policy,
                'onceMarkerConsumedBeforeStage': True, 'noRetryAuthorized': True},
    'selection': {'row': authority['selection'], 'paths': 123, 'payloadRows': 122, 'bytes': 4897969,
                  'allCurrentHashesAndModesMatch': True, 'allModes': '100644',
                  'currentExpectedBlobModeDigestSHA256': object_digest,
                  'stagedBlobMapVerified': False, 'changedSelectedSubsetVerified': False,
                  'actualWhitespaceCommandRan': False, 'formattingExclusions': []},
    'preservation': {'beforeRawDiffEqualsAcceptedPreflight': True, 'outsideDirtyRawDiffRows': outside,
                     'outsideDirtyCurrentByteModesPreserved': 2, 'protectedCurrentByteModesPreserved': 2,
                     'wranglerIdentity': preservation['wrangler'], 'artifactsStoreAbsent': True,
                     'preexistingCollapsedCurrentIdentitiesPreserved': 2416,
                     'postStageIndexState': 'unknown; stage may have partially populated it',
                     'postStageIndexEmptyVerified': False, 'postStageCompleteRawDiffOrCollapsedStatusAvailable': False,
                     'cleanTrackedIndependentFullHashWalkPerformed': False},
    'notExecutedSuffix': missing, 'commitPushDispatchObserved': {'commit': False, 'push': False, 'dispatch': False},
    'limitations': [
        'Eight admitted command records prove seven successes and one explicit Git add failure; they do not prove delivery completion.',
        'No selected index enumeration, staged object map, whitespace check, committed head/tree/diff, push, final index, or post-stage status command ran.',
        'Current selected filesystem blob hashes are expected input objects, not evidence of staged object equality.',
        'Initial index was empty; its state after failed Git add is unknown. No cleanup or reset was attempted.',
        'No new head/tree is available. Baseline is the last recorded head/tree observation; no fresh Git observation was performed.',
        'Preexisting collapsed entries are checked for identity/mode only, without recursively hashing their contents.',
        'Helper custody evidence applies only to the eight local owned commands, never to held processes or external execution.',
        'No remote CI binding or manual dispatch result, native/UI/capture, physical-device, release, dogfood, or GA acceptance is inferred.'
    ],
    'reviewExecution': {'command': 'python3 -I -B -S verification/github-delivery-axis-binding-followup/review/delivery-actual-review/audit_actual_failure.py',
                        'pythonVersion': sys.version, 'pythonExecutable': sys.executable,
                        'subjectImports': 0, 'gitGhCommands': 0, 'networkActions': 0,
                        'processProbes': 0, 'signals': 0, 'nativeUICaptureActions': 0,
                        'writesConfinedTo': str(OUT.relative_to(ROOT))},
    'checkCount': len(checks), 'checks': checks, 'inputRows': sorted(inputs.values(), key=lambda v: v['path'])
}
OUT.mkdir(parents=True, exist_ok=True)
report_path = OUT / 'actual-failure-report.json'
with report_path.open('x') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
seal = {'schema': 1, 'decision': report['decision'], 'report': row(report_path), 'auditSource': row(Path(__file__)),
        'findings': 1, 'finding': 'Actual delivery failed at Git add; completion not accepted.',
        'checkCount': report['checkCount'], 'newHead': None, 'newTree': None,
        'noRetryOrRecoveryAuthorityGranted': True}
with (OUT / 'seal.json').open('x') as handle:
    json.dump(seal, handle, indent=2)
    handle.write('\n')
print(json.dumps({'decision': report['decision'], 'checks': report['checkCount'], 'attempted': 8,
                  'successful': 7, 'ignoredSubjects': len(ignored), 'ignoredSelected': len(ignored_selected),
                  'report': seal['report'], 'seal': row(OUT / 'seal.json')}))
