"""Data-only tracking edit and readback. No subject module is imported or run."""
import copy
import difflib
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'verification/pair7-host-fix-tracking-checkpoint'
PREFIX = 'verification/pair7-host-fix-tracking-checkpoint/'
GUARD = 'verification/rust-1991-actual-audit-preparation-v2/deny_runtime.py'
GUARD_SHA = '69873787132f3c8d8f29977c87101e5c3d0337ae8429104bb49f1658b102cb74'
guard_bytes = (ROOT / GUARD).read_bytes()
assert hashlib.sha256(guard_bytes).hexdigest() == GUARD_SHA
guard = {}
exec(compile(guard_bytes, GUARD, 'exec'), guard)
guard['install'](ROOT)

FILES = ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']
HEAD = 'a3967100c5773685bbaedb964aa6e5de9838cb8a'
TREE = '69178bebcc6f73680b28e920d798c032a51037f6'
PARENT = '3da0d01bd05565a6aad905997beddf6805826241'
checks = []


def check(label, condition):
    checks.append({'label': label, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def row(path):
    data = (ROOT / path).read_bytes()
    return {'path': path, 'bytes': len(data), 'sha256': sha(data)}


def load(path):
    return json.loads((ROOT / path).read_bytes())


def write_bytes(path, data):
    check('Selected write ' + path, path in FILES or path.startswith(PREFIX))
    (ROOT / path).write_bytes(data)


def save(path, value):
    write_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


POLICY_FIELDS = ['currentAndroidHostFollowup', 'priorAndroidHostFollowupBeforePair7HostFixtureFix']
ENTRY_FIELDS = {
    'W02': ['axisRefusalHostEvidence', 'currentCanonicalSourcePair', 'pair7HostFixtureFix', 'evidence'],
    'W05': ['axisRefusalCandidate', 'currentCanonicalSourcePair', 'currentCheckpoint', 'latestCI',
            'nextImplementation', 'pair7HostFixtureFix', 'evidence',
            'priorLatestCIBeforePair7HostFixtureFix', 'priorCurrentCheckpointBeforePair7HostFixtureFix'],
    'G02': ['currentCheckpoint', 'latestCI', 'pair7HostFixtureFix', 'evidence',
            'priorLatestCIBeforePair7HostFixtureFix', 'priorCurrentCheckpointBeforePair7HostFixtureFix'],
    'G06': ['androidAxisRefusalCandidate', 'currentCanonicalSourcePair', 'currentCheckpoint',
            'latestCI', 'pair7HostFixtureFix', 'evidence',
            'priorLatestCIBeforePair7HostFixtureFix', 'priorCurrentCheckpointBeforePair7HostFixtureFix'],
}


def invariant_document(document):
    result = copy.deepcopy(document)
    for key in POLICY_FIELDS:
        result['executionPolicy'].pop(key, None)
    for entry in result.get('packages', result.get('gates', [])):
        for key in ENTRY_FIELDS.get(entry['id'], []):
            entry.pop(key, None)
    return result


def entry_rows(document):
    return [{k: e[k] for k in ('id', 'name', 'state', 'status', 'owner', 'reviewer',
                             'deliverables', 'dependencies', 'acceptance', 'requirement') if k in e}
            for e in document.get('packages', document.get('gates', []))]


def verify():
    frozen = load(PREFIX + 'after.json')
    for path in FILES:
        check('Frozen after row ' + path, row(path) == frozen['files'][path])
    structural = load(PREFIX + 'structural-invariants.json')
    for path in ['work-graph.json', 'gates/ga.json']:
        value = load(path)
        check('Unchanged fields digest ' + path,
              sha(encoded(invariant_document(value))) == structural['unmodifiedFieldDigests'][path])
        check('Scope states owners reviewers ' + path,
              entry_rows(value) == structural['scopeStatesOwnersReviewers'][path])
    observed = load(PREFIX + 'observed-checkpoint.json')
    for binding in observed['dependencies']:
        check('Dependency still frozen ' + binding['path'], row(binding['path']) == binding)
    for binding in observed['installedPair7Rows'] + [observed['axisSession']]:
        actual = row(binding['path'])
        check('Original installed source unchanged ' + binding['path'],
              all(actual[k] == binding[k] for k in ['path', 'bytes', 'sha256']))
    for binding in observed['hostFixtureFix']['sourceFiles']:
        actual = row(binding['path'])
        check('Host fixture selection unchanged ' + binding['path'], actual == binding)
    work = load('work-graph.json')
    gates = load('gates/ga.json')
    check('W01-W18 remain required', [e['id'] for e in work['packages']] == [f'W{i:02}' for i in range(1, 19)])
    check('G01-G38 remain required', [e['id'] for e in gates['gates']] == [f'G{i:02}' for i in range(1, 39)])
    check('Gate counts unchanged', Counter(e['status'] for e in gates['gates']) == {'planned': 30, 'running': 8})
    check('Work states unchanged', Counter(e['state'] for e in work['packages']) == {'in_progress': 16, 'ready': 2})
    policy = work['executionPolicy']['currentAndroidHostFollowup']
    check('Current policy agrees across JSON files', policy == gates['executionPolicy']['currentAndroidHostFollowup'])
    check('Controller failure remains distinct',
          policy['delivery']['originalController']['outerExitCode'] == 1
          and policy['delivery']['originalController']['succeeded'] is False
          and policy['delivery']['combinedTargetCommands'] == {'total': 147, 'exitZero': 146, 'historicalClosedStageExitOne': 1})
    check('Pair7 latest CI failure retained', policy['latestEngineCI']['conclusion'] == 'failure')
    check('Fix still source only', policy['hostFixtureFix']['compilerInvocations'] == 0
          and policy['hostFixtureFix']['addedBehavioralCasesExecuted'] is False
          and policy['hostFixtureFix']['delivered'] is False)
    check('No denied data APIs', guard['DENIED'] == [])
    summary = {'schema': 1, 'command': 'python3 -I -B -S ' + PREFIX + 'build_checkpoint.py --verify',
               'python': sys.version, 'passed': len(checks), 'failed': 0,
               'guard': {'path': GUARD, 'sha256': GUARD_SHA, 'denied': guard['DENIED']},
               'subjectImports': 0, 'productRuntimeCompilerGitNetworkNativeUIOrProcessActions': 0,
               'checks': checks}
    save(PREFIX + 'final-readback.json', summary)
    print(json.dumps({'mode': 'verify', 'passed': summary['passed'], 'failed': 0,
                      'trackingRows': frozen['files'], 'subjectImports': 0, 'denied': guard['DENIED']}))


def build():
    check('Isolated data-only startup', sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode)
    check('Ownership namespace exists before build', (PACKET / 'OWNERSHIP.md').is_file())
    check('New checkpoint not already built', not (PACKET / 'after.json').exists())
    before_bytes = {path: (ROOT / path).read_bytes() for path in FILES}
    before_rows = {path: row(path) for path in FILES}
    prior = load('verification/pair7-tracking-checkpoint/seal.json')
    for path in FILES:
        check('Baseline equals prior sealed tracking ' + path, before_rows[path] == prior['trackingFiles'][path])
    documents = {path: json.loads(before_bytes[path]) for path in ['work-graph.json', 'gates/ga.json']}
    originals = copy.deepcopy(documents)
    field_scope = {'schema': 1, 'allowedFiles': FILES, 'JSONPolicyFields': POLICY_FIELDS,
                   'JSONEntryFields': ENTRY_FIELDS,
                   'markdownScope': 'Prepend a3967100 current checkpoint and relabel former current3da checkpoint. Preserve all former current body and older suffix bytes.',
                   'otherJSONFieldsChanged': 0, 'scopeStatesOwnersReviewersChanged': 0}
    save(PREFIX + 'field-scope.json', field_scope)
    save(PREFIX + 'before.json', {'schema': 1, 'files': before_rows,
         'sourceRevision': HEAD, 'sourceTree': TREE, 'soleParent': PARENT,
         'provenance': 'Retained delivery receipts and root handoff, without a new Git or remote probe.',
         'python': sys.version, 'guard': {'path': GUARD, 'sha256': GUARD_SHA}, 'subjectImports': 0})
    before_fields = {}
    for path, value in originals.items():
        before_fields[path] = {'executionPolicy': {k: value['executionPolicy'].get(k) for k in POLICY_FIELDS},
                              'entries': {e['id']: {k: e.get(k) for k in ENTRY_FIELDS[e['id']]}
                                          for e in value.get('packages', value.get('gates', [])) if e['id'] in ENTRY_FIELDS}}
    save(PREFIX + 'before-fields.json', before_fields)
    dependency_paths = [
        'AGENTS.md', 'mixer-product-plan.md', 'verification/pair7-tracking-checkpoint/seal.json',
        'verification/github-delivery-android-pair7/root-closed-command-series.json',
        'verification/github-delivery-android-pair7/post-push-recovery-decision.json',
        'verification/github-delivery-android-pair7/delivery-pair7-receipt.json',
        'verification/github-delivery-android-pair7/post-push-controller-failure.json',
        'verification/github-delivery-android-pair7/review/post-push-preservation/seal.json',
        'verification/android-broader-pair7-integration/ci-failure/failure-summary.json',
        'verification/android-broader-pair7-integration/ci-failure/diagnostics.json',
        'verification/android-broader-pair7-integration/host-fixture-fix/source-only-receipt.json',
        'verification/android-broader-pair7-integration/host-fixture-fix/live-roster/source-only-receipt.json',
        'verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/source-only-receipt.json',
        'verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/final-source-selection.json',
        'verification/android-broader-pair7-integration/host-fixture-fix/root-review/review.json',
        'verification/android-broader-pair7-integration/application-receipt.json',
        'verification/android-axis-canonical-host-acceptance/receipt.json',
        'verification/rust-1991-first-actual-result/refusal-receipt.json',
        'verification/rust-1991-first-actual-result/review-actual/seal.json', GUARD,
    ]
    dependencies = [row(path) for path in dependency_paths]
    rows = {r['path']: r for r in dependencies}
    series_path = 'verification/github-delivery-android-pair7/root-closed-command-series.json'
    selection_path = 'verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/final-source-selection.json'
    check('Root command series exact handoff hash', rows[series_path]['sha256'] == '93533d71d880ee66a3cb77cc3daee40bab256d90f4520347dfd0f4469ffcf745')
    check('Final source selection exact handoff hash', rows[selection_path]['sha256'] == '7369c59b0e20e90a3649a4fd647c2419f4ddfc11c5be0c338636c9f7f6b2bd37')
    series = load(series_path)
    recovery = load('verification/github-delivery-android-pair7/post-push-recovery-decision.json')
    delivery_receipt = load('verification/github-delivery-android-pair7/delivery-pair7-receipt.json')
    failure = load('verification/android-broader-pair7-integration/ci-failure/failure-summary.json')
    selection = load(selection_path)
    base = load('verification/android-broader-pair7-integration/host-fixture-fix/source-only-receipt.json')
    live = load('verification/android-broader-pair7-integration/host-fixture-fix/live-roster/source-only-receipt.json')
    leaves = load('verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/source-only-receipt.json')
    root_review_path = 'verification/android-broader-pair7-integration/host-fixture-fix/root-review/review.json'
    root_review = load(root_review_path)
    check('Root source review exact handoff row', rows[root_review_path]['bytes'] == 8263
          and rows[root_review_path]['sha256'] == '4585a995bf826049d67a9a9f832fc043bec7b4258e7c0346934b83878be9508b')
    check('Root accepts source only for fresh ordinary CI', root_review['decision'] == 'accept-source-only-host-fixture-correction-for-fresh-ordinary-CI'
          and root_review['sourceDataOnly'] is True and root_review['compilerInvocations'] == 0
          and root_review['subjectTestsRun'] == 0 and root_review['hostAcceptance'] is False)
    for key, expected in [('head', HEAD), ('tree', TREE), ('parent', PARENT), ('totalTargetCommands', 38),
                          ('targetExitZero', 38), ('signals', 0), ('originalDeliveryControllerExit', 1),
                          ('originalDeliveryControllerSucceeded', False), ('combinedTargetCommands', 147),
                          ('combinedTargetExitZero', 146), ('historicalClosedStageExitOne', 1)]:
        check('Closed command series ' + key, series[key] == expected)
    check('Recovery retains original failed controller', recovery['originalDriverSucceeded'] is False
          and recovery['gitEffectsVerified'] is True and recovery['retryOrReplayAllowed'] is False)
    for key, expected in [('head', HEAD), ('tree', TREE), ('parent', PARENT), ('selectedPaths', 202),
                          ('changedSelectedPaths', 202), ('force', False), ('pushed', True), ('indexEmpty', True),
                          ('outsideSelectionDirtyByteModeSnapshotsPreserved', 2),
                          ('preexistingCollapsedEntryIdentityModesPreserved', 2435)]:
        check('Recovered Git effects ' + key, delivery_receipt[key] == expected)
    check('Recovery makes no recursive content claim', delivery_receipt['collapsedStatusProof']['recursiveUntrackedContentProof'] is False)
    for key, expected in [('sourceRevision', HEAD), ('sourceTree', TREE), ('runID', 40968793326),
                          ('runAttempt', 1), ('workflowID', 393488255), ('jobID', 123779983605),
                          ('jobName', 'android-owner-host'), ('runConclusion', 'failure'),
                          ('completedJobs', {'success': 5, 'failure': 1}),
                          ('productionRendererDeclaresBothMethods', True), ('pair7HostAcceptance', False)]:
        check('Retained CI failure ' + key, failure[key] == expected)
    for path, value in [('base', base), ('live-roster', live), ('adapter-leaves', leaves)]:
        check('Source-only receipt has no compiler ' + path, value['compiler_invocations'] == 0)
        check('Source-only receipt has no product tests ' + path, value['product_tests_run'] == 0)
        check('Source-only receipt has no helper execution ' + path, value['subject_helpers_executed'] == 0)
    check('Nine new cases remain unexecuted', base['source_checks']['added_host_cases'] == 9
          and base['source_checks']['added_host_cases_executed'] is False)
    check('Final canonical fix has ten test files', selection['files_count'] == 10 and len(selection['files']) == 10
          and all(r['path'].startswith('native/android/tests/') for r in selection['files']))
    for binding in selection['files']:
        check('Live canonical test row ' + binding['path'], row(binding['path']) == binding)
    check('Final live roster selected counts', leaves['selected_sources']['A-orchestration']['sources'] == 87
          and leaves['selected_sources']['B-concrete-renderer-views']['sources'] == 96)
    check('Final B selects five independent types', len(leaves['live_roster_semantic_changes_from_frozen']['B_substitutes_added']) == 5)
    check('Final B selects actual editor connection', leaves['live_roster_semantic_changes_from_frozen']['B_production_added']
          == ['native/android/app/src/dev/mixer/android/NativeEditorConnectionV2.java'])
    check('Runner freezes roster bytes', live['runner_observation']['same_exact_roster_bytes_in_frozen_map'] is True
          and live['runner_observation']['roster_read_once_as_bytes'] is True)
    old_policy = originals['work-graph.json']['executionPolicy']['currentAndroidHostFollowup']
    original_source = old_policy['currentSourcePair']
    check('Exact SDK22 adapter24 source tuple', original_source['SDK_members'] == 22
          and original_source['adapter_members'] == 24 and original_source['namedSourceMembers'] == 46
          and original_source['namedSourceBytes'] == 661583
          and original_source['SDK_digest'] == 'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0'
          and original_source['adapter_digest'] == 'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e')
    for binding in original_source['targets'] + [original_source['axisSessionUnchanged']]:
        check('Pair7 original installed row ' + binding['path'], all(row(binding['path'])[k] == binding[k] for k in ['path', 'bytes', 'sha256']))
    latest_ci = {'head': HEAD, 'tree': TREE, 'run': 40968793326, 'attempt': 1, 'workflow': 393488255,
                 'status': 'completed', 'conclusion': 'failure', 'jobsPassed': 5, 'jobsFailed': 1,
                 'failedJob': {'name': 'android-owner-host', 'id': 123779983605},
                 'failureSummary': rows['verification/android-broader-pair7-integration/ci-failure/failure-summary.json'],
                 'compileOutcome': 'Closure A javac failed before any host test main. Closure B and later environment steps were skipped.',
                 'failureCause': 'Controlled renderer substitute omitted completeFailedV2 and editorDisposalBusyV2. Both methods already exist in production.',
                 'evidenceScope': 'Retained terminal job metadata and canonical javac failure artifact. Five successful jobs do not establish pair.7 host acceptance.',
                 'remoteTools': failure['remoteTools'],
                 'reportedRemoteCleanup': failure['reportedRemoteCleanup'],
                 'pair7HostAccepted': False, 'nativePublishedFieldLogOrGAQualified': False}
    host_fix = {'status': 'source-only-ten-canonical-test-files-root-review-accepted-delivery-and-new-CI-pending',
                'selection': rows[selection_path], 'sourceFiles': selection['files'],
                'receipts': [rows[p] for p in dependency_paths if 'host-fixture-fix/' in p and p.endswith('source-only-receipt.json')],
                'changedCanonicalTestFiles': 10, 'productionSourceChanged': False,
                'originalNinePair7RowsAndAxisSessionUnchanged': True,
                'addedBehavioralCases': 9, 'addedBehavioralCasesExecuted': False,
                'liveExplicitRoster': {'A': 87, 'B': 96, 'actualNativeEditorConnectionV2InB': True,
                                       'additionalIndependentControlledAndroidTypes': 5,
                                       'runnerFreezesExactRosterBytes': True, 'immutableVerificationRosterUnchanged': True},
                'compilerInvocations': 0, 'hostAssertionsRun': 0, 'subjectHelpersExecuted': 0,
                'freshIndependentSourceReview': {'status': 'accepted-source-only-for-fresh-ordinary-CI',
                                                 'reviewer': root_review['reviewer'], 'receipt': rows[root_review_path]},
                'delivered': False, 'newOrdinaryCI': 'pending',
                'generatedJavaCIProposal': 'Separate source proposal/review in progress. Not installed or included in this delivery claim.',
                'nextHostedCommands': leaves['next_hosted_commands'],
                'nextCommandsScope': 'Fresh ordinary Engine CI after source review and coherent delivery. No rerun of failed workflow or held full-owner v5 startup.',
                'nativeRuntimeReleaseOrGAAccepted': False}
    delivery = {'status': delivery_receipt['status'], 'receipt': rows['verification/github-delivery-android-pair7/delivery-pair7-receipt.json'],
                'rootClosedCommandSeries': rows[series_path],
                'independentPostPushReview': rows['verification/github-delivery-android-pair7/review/post-push-preservation/seal.json'],
                'recoveryDecision': rows['verification/github-delivery-android-pair7/post-push-recovery-decision.json'],
                'selectedPaths': 202, 'selectedPathsAllChanged': True, 'pushed': True, 'force': False, 'indexEmpty': True,
                'soleParent': PARENT,
                'newTargetCommands': {'preflight': 10, 'delivery': 23, 'engineBinding': 5, 'total': 38,
                                      'exitZero': 38, 'signals': 0, 'allClosed': True},
                'combinedTargetCommands': {'total': 147, 'exitZero': 146, 'historicalClosedStageExitOne': 1},
                'originalController': {'outerExitCode': 1, 'succeeded': False, 'strictComparatorPassed': False,
                                       'completionTailReached': False, 'producedReceipt': False,
                                       'reason': 'One root-delegated review namespace became nonempty after preflight.',
                                       'failureDistinctFromHistoricalTargetStageExitOne': True},
                'outsideProtectedDirtyFilesPreserved': 2, 'originalCollapsedEntryIdentitiesAndModesPreserved': 2435,
                'acceptedConcurrentNamespace': recovery['exactConcurrentNamespace']['path'],
                'recursiveUntrackedContentProof': False, 'retryOrReplayAllowed': False}
    source_pair = copy.deepcopy(original_source)
    source_pair.update({'status': 'delivered-pair7-ordinary-CI-host-compile-failed-source-only-fixture-correction-pending',
                        'deliveredHead': HEAD, 'deliveredTree': TREE, 'workingTreeChangesNotYetCommitted': False,
                        'sourceInstallationCountsRemainHistorical': True,
                        'canonicalCI': '40968793326 attempt1 failed closureA javac; no pair.7 host acceptance',
                        'latestOrdinaryCI': latest_ci, 'hostFixtureFixSelection': rows[selection_path],
                        'hostFixtureFixAffectsProductionTuple': False,
                        'generatedDebugReleaseRelocatedExportedConsumerEvidence': 'pending fresh actual compilations at pair.7 source'})
    checkpoint = (
        'Mixer a3967100 delivered the exact 202-path pair.7 slice, SDK22/adapter24, 46 members and 661,583 bytes. '
        'All 38 new target commands closed with exit zero. The original delivery controller separately exited one after push '
        'because a root-delegated review namespace appeared after preflight. Independent post-push review and explicit data recovery '
        'accepted the Git effects while retaining that controller failure, both protected files and 2,435 collapsed identities. '
        'The historical target series totals 147 commands, 146 exit-zero results and one older closed staging failure. '
        'Engine CI40968793326 attempt1 fails android-owner-host closureA javac before host assertions because its controlled renderer '
        'omitted completeFailedV2 and editorDisposalBusyV2, which production already declares. Five jobs pass. Later closureB and environment '
        'steps are skipped. Ten canonical test files now hold a source-only correction with nine unrun behavioral cases, live explicit '
        'rosters A87/B96, actual NativeEditorConnectionV2 and five independent controlled Android types/signatures. '
        'The runner freezes roster bytes. Original nine pair.7 bindings and axis DocumentSession remain unchanged. '
        'Root independent source review accepts only this correction for fresh ordinary CI. Correction delivery and new ordinary CI remain pending. Generated Java CI proposal/review is separate and '
        'not installed. Prior 3da0d01b canonical pair.6 host acceptance remains historical. Rust1.99.1 remains unqualified after the '
        'observed1.98.1 artifact refusal, with no retry selected. Native/UI/capture, API28-35 fullV2, immutable published FieldLog, '
        'D0-D8, signing, store, customer and GA holds remain.'
    )
    observed = {'schema': 1, 'status': 'tracking-only-delivered-pair7-CI-failure-and-source-only-host-fixture-correction',
                'sourceRevision': HEAD, 'sourceTree': TREE, 'soleParent': PARENT,
                'sourceProvenance': 'Retained recovered delivery and CI receipts; no new Git/network query.',
                'checkpoint': checkpoint, 'delivery': delivery, 'latestCI': latest_ci,
                'sourcePair': source_pair, 'hostFixtureFix': host_fix,
                'installedPair7Rows': original_source['targets'], 'axisSession': original_source['axisSessionUnchanged'],
                'priorCanonicalPair6HostAcceptance': old_policy['canonicalAxisHostAcceptance'],
                'rust1991FirstActualResult': old_policy['rust1991FirstActualResult'],
                'holds': old_policy['holds'], 'GA': {'verified': 0, 'running': 8, 'planned': 30},
                'dependencies': dependencies, 'scope': 'Tracking only. No new executable or GA acceptance.',
                'localProductCompilerNativeUICaptureGitNetworkProcessOrSignalActions': 0, 'subjectImports': 0}
    save(PREFIX + 'observed-checkpoint.json', observed)
    policy = copy.deepcopy(old_policy)
    policy.update({'outcome': row(PREFIX + 'observed-checkpoint.json'), 'checkpoint': checkpoint,
                   'deliveredHead': HEAD, 'deliveredTree': TREE, 'delivery': delivery,
                   'latestEngineCI': latest_ci, 'currentSourcePair': source_pair, 'hostFixtureFix': host_fix})
    evidence_paths = [series_path, 'verification/github-delivery-android-pair7/post-push-recovery-decision.json',
                      'verification/github-delivery-android-pair7/delivery-pair7-receipt.json',
                      'verification/github-delivery-android-pair7/review/post-push-preservation/seal.json',
                      'verification/android-broader-pair7-integration/ci-failure/failure-summary.json',
                      'verification/android-broader-pair7-integration/host-fixture-fix/source-only-receipt.json',
                      'verification/android-broader-pair7-integration/host-fixture-fix/live-roster/source-only-receipt.json',
                      'verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/source-only-receipt.json',
                      selection_path, root_review_path, PREFIX + 'observed-checkpoint.json']
    for path, value in documents.items():
        value['executionPolicy']['priorAndroidHostFollowupBeforePair7HostFixtureFix'] = copy.deepcopy(value['executionPolicy']['currentAndroidHostFollowup'])
        value['executionPolicy']['currentAndroidHostFollowup'] = copy.deepcopy(policy)
        for entry in value.get('packages', value.get('gates', [])):
            if entry['id'] not in ENTRY_FIELDS:
                continue
            entry['pair7HostFixtureFix'] = copy.deepcopy(host_fix)
            entry['evidence'].extend(p for p in evidence_paths if p not in entry['evidence'])
            if 'currentCanonicalSourcePair' in entry:
                entry['currentCanonicalSourcePair'] = copy.deepcopy(source_pair)
            if 'currentCheckpoint' in entry:
                entry['priorCurrentCheckpointBeforePair7HostFixtureFix'] = entry['currentCheckpoint']
                entry['currentCheckpoint'] = checkpoint
            if 'latestCI' in entry:
                entry['priorLatestCIBeforePair7HostFixtureFix'] = entry['latestCI']
                entry['latestCI'] = copy.deepcopy(latest_ci)
            if 'axisRefusalHostEvidence' in entry:
                entry['axisRefusalHostEvidence']['state'] = 'historical-pair6-host-acceptance-pair7-ordinary-CI-compile-failed-fixture-fix-pending'
            for candidate_key in ['axisRefusalCandidate', 'androidAxisRefusalCandidate']:
                if candidate_key in entry:
                    candidate = entry[candidate_key]
                    candidate['state'] = 'historical-pair6-host-acceptance-pair7-ordinary-CI-compile-failed-fixture-fix-pending'
                    candidate['currentPair7SourceIntegration'] = copy.deepcopy(source_pair)
            if 'nextImplementation' in entry:
                entry['nextImplementation'] = (
                    'Deliver the ten-file source-only host correction accepted by root independent source review, '
                    'then inspect fresh ordinary Engine CI closureA and closureB compilation and assertions. No failed-workflow rerun '
                    'or held full-owner v5 retry is selected. Generated Java CI source proposal/review remains separate and uninstalled. '
                    'Require fresh generated Android Debug/Release, relocated/exported consumer and all eighteen product plus actual '
                    'generated Java closure evidence. Preserve both below-36 guards and API28-35 fullV2 refusal, prior API28 proof '
                    'non-inheritance, Rust1.99.1 refusal without retry, native/UI/capture and physical-phone pauses, all custody holds, '
                    'immutable published FieldLog and D0-D8/signing/store/customer/GA requirements.'
                )
        check('Only selected JSON fields changed ' + path,
              invariant_document(value) == invariant_document(originals[path]))
        check('All package/gate contracts unchanged ' + path, entry_rows(value) == entry_rows(originals[path]))
        save(path, value)
    prose = '''Mixer `a3967100` delivered the exact 202-path `mixer.android-source-pair.7` slice. [The command record](verification/github-delivery-android-pair7/root-closed-command-series.json) closes all 38 new target commands with exit zero and zero signals. The original delivery controller separately exited 1 after push because one root-delegated review namespace became nonempty after preflight. [Independent post-push review](verification/github-delivery-android-pair7/review/post-push-preservation/seal.json) and [explicit data recovery](verification/github-delivery-android-pair7/post-push-recovery-decision.json) verified the 202 changed objects, sole parent, non-force remote result and empty index while retaining that controller failure. Both protected files and all 2,435 prior collapsed identities remain preserved. This establishes no recursive untracked-content proof. The historical target-command series totals 147 commands, with 146 exit-zero results and one older closed staging failure. The new outer controller failure is separate.

[Engine CI 40968793326](https://github.com/snowdamiz/mixer/actions/runs/40968793326), attempt 1 at `a3967100`, completes with five successful jobs and a failed `android-owner-host` job, `123779983605`. [The canonical failure summary](verification/android-broader-pair7-integration/ci-failure/failure-summary.json) binds the retained artifact and javac diagnostics. Closure A failed before any host test main because the controlled renderer substitute omitted `completeFailedV2` and `editorDisposalBusyV2`. Production already declares both methods. Closure B and later environment steps were skipped. Pair.7 host acceptance remains pending.

The [source-only correction](verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/final-source-selection.json) selects ten canonical test files. Its three receipts cover nine new behavioral cases, a live explicit roster with A87 and B96 sources, actual `NativeEditorConnectionV2` in B, and five independent controlled Android types with required signatures. The runner freezes the exact roster bytes. [Root independent source review](verification/android-broader-pair7-integration/host-fixture-fix/root-review/review.json) accepts the correction for fresh ordinary CI. No compiler or host assertion has run for this correction. Coherent delivery and new ordinary CI remain pending. The separate generated Java CI proposal and review are in progress. That proposal is not installed or included in this delivery claim.

The delivered pair.7 tuple remains SDK22 `bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0` and adapter24 `ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e`, covering 46 named members and 661,583 bytes. The original nine installed source bindings, axis `DocumentSession`, wire tuple and 9,587-byte default descriptor remain unchanged. The prior `3da0d01b` six-job canonical pair.6 host acceptance stays historical. The [first Rust 1.99.1 actual-data audit](verification/rust-1991-first-actual-result/refusal-receipt.json) retains its refusal of the observed 1.98.1 artifact. Rust 1.99.1 remains unqualified, with no retry, reprofile, install or fallback selected.

Generated Android Debug/Release, relocated and exported actual consumers, all 18 product Java files and actual generated Java still need fresh compilation evidence. Both below-36 guards retain the API28-35 full V2 refusal. Prior API28 collection proof is not inherited. These source and host records establish no Android UI or runtime acceptance.

Public FieldLog `00c8fe04` host run `40820029857` remains historical with 39 accepted tests. Immutable published SDK consumption, full native owners, D0-D8, physical devices, signing, store, customer and GA acceptance remain pending. Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture and local compiler/custody holds remain, phones are disconnected, all seven held local groups and FieldLog run `40802230894` / PGID `2424` / PID `2621` stay untouched, and the v5 startup is not retried. [This tracking checkpoint](verification/pair7-host-fix-tracking-checkpoint/observed-checkpoint.json) records the exact retained evidence and pending work.

'''
    for path in ['PLAN.md', 'STATUS.md']:
        before_text = before_bytes[path].decode()
        marker = '## Current delivered checkpoint\n\n'
        check('One current markdown heading ' + path, before_text.count(marker) == 1)
        prefix, old_body = before_text.split(marker, 1)
        after_text = prefix + marker + prose + '## Previous delivered checkpoint at 3da0d01b\n\n' + old_body
        check('Former current and full historical suffix preserved ' + path,
              after_text.split('## Previous delivered checkpoint at 3da0d01b\n\n', 1)[1] == old_body)
        write_bytes(path, after_text.encode())
    patch = ''.join(''.join(difflib.unified_diff(before_bytes[path].decode().splitlines(keepends=True),
                                               (ROOT / path).read_text().splitlines(keepends=True),
                                               fromfile='a/' + path, tofile='b/' + path, n=0)) for path in FILES)
    write_bytes(PREFIX + 'tracking.patch', patch.encode())
    structural = {'schema': 1, 'sourceRevision': HEAD, 'sourceTree': TREE,
                  'unmodifiedFieldDigests': {path: sha(encoded(invariant_document(value))) for path, value in originals.items()},
                  'scopeStatesOwnersReviewers': {path: entry_rows(value) for path, value in originals.items()},
                  'markdownHistoricalSuffixDigests': {path: sha(before_bytes[path].split(b'## Current delivered checkpoint\n\n', 1)[1]) for path in ['PLAN.md', 'STATUS.md']},
                  'fullProductPlanUnchanged': rows['mixer-product-plan.md'],
                  'W01_W18_G01_G38_D0_D8ScopePreserved': True,
                  'GA': {'verified': 0, 'running': 8, 'planned': 30},
                  'allUnselectedTopLevelAndEntryFieldsUnchanged': True, 'checks': copy.deepcopy(checks),
                  'runtimeOrCompilerTestsExecuted': 0, 'subjectImports': 0, 'denied': guard['DENIED']}
    save(PREFIX + 'structural-invariants.json', structural)
    after = {'schema': 1, 'sourceRevision': HEAD, 'sourceTree': TREE,
             'sourceRevisionScope': 'Last retained delivered revision. This tracking edit and fixture correction are working-tree data, not newly delivered.',
             'files': {path: row(path) for path in FILES}}
    save(PREFIX + 'after.json', after)
    receipt = {'schema': 1, 'status': 'tracking-only-source-evidence-updated-no-GA-promotion',
               'command': 'python3 -I -B -S ' + PREFIX + 'build_checkpoint.py --build',
               'python': sys.version, 'sourceRevision': HEAD, 'sourceTree': TREE, 'soleParent': PARENT,
               'sourceRevisionEvidence': rows['verification/github-delivery-android-pair7/delivery-pair7-receipt.json'],
               'guard': {'path': GUARD, 'sha256': GUARD_SHA, 'installedBeforeSubjectImports': True, 'denied': guard['DENIED']},
               'subjectImports': 0, 'subjectHelperExecutions': 0, 'localCompilerOrProductTests': 0,
               'nativeUICaptureGitGhNetworkProcessProbesSignalsOrHeldActions': 0,
               'trackingFiles': after['files'], 'structuralChecksPassed': len(structural['checks']),
               'limitations': ['No compiler, host behavioral assertions, native runtime, UI or physical test ran in this lane.',
                               'Retained CI failure and recovered Git effects were read as data, not reexecuted or queried remotely.',
                               'Original delivery controller remains failed. Root source review accepts only the correction source; delivery and ordinary CI are pending.',
                               'Source/text and JSON consistency cannot establish compilation, Android parity, API-floor safety, release or GA acceptance.',
                               'Generated Java CI proposal/review remains separate, in progress and uninstalled.',
                               'All original product scope, state, owner, reviewer, native/process/custody and release holds remain.'],
               'cleanup': 'No subject children, compiler scratch, native instances or capture processes were created or queried. Other projects and held groups were untouched.',
               'commitOrDeliveryPerformed': False}
    save(PREFIX + 'receipt.json', receipt)
    print(json.dumps({'mode': 'build', 'structuralChecksPassed': receipt['structuralChecksPassed'],
                      'trackingRows': after['files'], 'subjectImports': 0, 'denied': guard['DENIED']}))


if sys.argv[1:] == ['--build']:
    build()
elif sys.argv[1:] == ['--verify']:
    verify()
else:
    raise SystemExit('Select exactly --build or --verify. Both modes are data only.')
