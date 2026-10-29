"""One exact frozen-path commit and nonforce origin/main push; no retries."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_selection_common', Path(__file__).with_name('selection_common_delivery.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
import hashlib
import json
import stat
for name in ('StrictCommands','BASE','TREE','S','SELECTION','ROWS','SELECTED','PROTECTED','ROOT','OUT','now','row','save','fingerprint','preserved_entry','raw_rows','collapsed','check_sources','accepted_preflight','ACCEPTED_PREFLIGHT_SEAL','ACCEPTED_PREFLIGHT_ROWS'): globals()[name] = getattr(common,name)
AUTHORED = [".github/workflows/android-view-api-jdk-data-observation.yml","PLAN.md","STATUS.md","gates/ga.json","verification/android-jdk-data-observation-selection-2026-10-29/.gitignore","verification/android-jdk-data-observation-selection-2026-10-29/README.md","verification/android-jdk-data-observation-selection-2026-10-29/helper-review.json","verification/android-jdk-data-observation-selection-2026-10-29/pure-checks.json","verification/android-jdk-data-observation-selection-2026-10-29/pure-execution.json","verification/android-jdk-data-observation-selection-2026-10-29/root-review.json","verification/android-jdk-data-observation-selection-2026-10-29/selection.json","verification/android-view-api-focused-actual-review/.gitignore","verification/android-view-api-focused-actual-review/ACTUAL-REVIEW.md","verification/android-view-api-focused-actual-review/CHECKLIST.md","verification/android-view-api-focused-actual-review/PREPARATION.md","verification/android-view-api-focused-actual-review/actual-review-seal.json","verification/android-view-api-focused-actual-review/actual-review.json","verification/android-view-api-focused-actual-review/audit_archive_actual.py","verification/android-view-api-focused-actual-review/audit_data.py","verification/android-view-api-focused-actual-review/audit_failure_actual.py","verification/android-view-api-focused-actual-review/binding-required.json","verification/android-view-api-focused-actual-review/check_data.py","verification/android-view-api-focused-actual-review/guarded_inspector.py","verification/android-view-api-focused-actual-review/jdk-observation-preparation/SOURCE-REVIEW.md","verification/android-view-api-focused-actual-review/jdk-observation-preparation/bootstrap.py","verification/android-view-api-focused-actual-review/jdk-observation-preparation/check_data.js","verification/android-view-api-focused-actual-review/jdk-observation-preparation/contract.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/expected-runtime-members.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/observe_jdk.py","verification/android-view-api-focused-actual-review/jdk-observation-preparation/preparation-errors.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/root-selection-template.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/source-manifest.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/synthetic-checks.json","verification/android-view-api-focused-actual-review/jdk-observation-preparation/workflow-draft.yml","verification/android-view-api-focused-actual-review/jdk-observation-review/REVIEW.md","verification/android-view-api-focused-actual-review/jdk-observation-review/independent-data-checks.json","verification/android-view-api-focused-actual-review/jdk-observation-review/interim-review.json","verification/android-view-api-focused-actual-review/jdk-observation-review/pure-function-preparation/PREPARATION.md","verification/android-view-api-focused-actual-review/jdk-observation-review/pure-function-preparation/check_observer_pure.py","verification/android-view-api-focused-actual-review/jdk-observation-review/pure-function-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-observation-review/pure-function-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-observation-review/review-seal.json","verification/android-view-api-focused-actual-review/jdk-observation-review/review.json","verification/android-view-api-focused-actual-review/jdk-observation-review/reviewed-preparation.json","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/REPORT.md","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/receipt.json","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/seal.json","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources.json","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/adoptium-common-rules.txt","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/adoptium-installation-doc.txt","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/adoptium-packaging-readme.txt","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/runner-install.txt","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/runner-readme.txt","verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/runner-toolset.txt","verification/android-view-api-focused-actual-review/preparation.json","verification/android-view-api-focused-outcome-2026-10-29/.gitignore","verification/android-view-api-focused-outcome-2026-10-29/README.md","verification/android-view-api-focused-outcome-2026-10-29/ordinary-ci.json","verification/android-view-api-focused-outcome-2026-10-29/receipt.json","verification/android-view-api-focused-outcome-2026-10-29/seal.json","verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/DocumentSession.swift.diff","verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/README.md","verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/manifest.json","verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/receipt.json","verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/source/MixerAndroidRuntime/DocumentSession.swift","verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/tests/AndroidTextFieldAxisRefusalTests.swift","verification/android-view-api-source-pair-reconciliation/axis-refusal-review/findings.md","verification/android-view-api-source-pair-reconciliation/axis-refusal-review/receipt.json","verification/android-view-api-source-pair-reconciliation/manifest.json","verification/android-view-api-source-pair-reconciliation/proposal.md","verification/android-view-api-source-pair-reconciliation/receipt.json","work-graph.json"]
pre, preservation = accepted_preflight()
assert pre['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF']
assert pre['head'] == BASE and pre['tree'] == TREE and pre['selectedPaths'] == len(SELECTED)
assert not (OUT / 'delivery-selected-once.json').exists()
with (OUT / 'paths-selected.nul').open('xb') as handle:
    handle.write(b''.join(value.encode() + b'\0' for value in sorted(SELECTED)))


def check_preservation(commands, label):
    check_sources()
    for expected in preservation['tracked']:
        assert fingerprint(expected['path']) == expected, expected['path']
    for expected in preservation['protectedSnapshots']:
        assert fingerprint(expected['path']) == expected, expected['path']
    assert fingerprint('.wrangler') == preservation['wrangler']
    assert not (ROOT / 'hosted/lib/mixer_hosted/artifacts/store.ex').exists()
    raw = raw_rows(commands.run(label + '-diff', ['git', 'diff', '--raw', '--no-abbrev', '--no-renames', '-z']))
    outside = [value for value in raw if value['path'] not in SELECTED]
    assert outside == preservation['otherDirtyTracked'], 'Dirty tracked diff outside selection changed'
    for expected in preservation['untrackedCollapsed']:
        assert preserved_entry(expected['path']) == expected, expected['path']


c = StrictCommands('delivery-selected')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [BASE, TREE]
assert c.run('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert c.run('origin', ['git', 'remote', 'get-url', 'origin']).decode().strip() == pre['origin']
assert c.run('push-url-before-stage', ['git', 'remote', 'get-url', '--push', '--all', 'origin']).decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
assert c.run('remote-before', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert not c.run('index-before', ['git', 'diff', '--cached', '--name-only', '-z'])
check_preservation(c, 'before')
save('delivery-selected-once.json', {'at': now(), 'selection': row(ROOT / SELECTION), 'paths': len(SELECTED),
    'oneCommitNonforcePushAuthorized': True, 'retryOnUnknownOutcome': False})
c.run('stage', ['git', 'add', '--pathspec-from-file=' + str(OUT / 'paths-selected.nul'), '--pathspec-file-nul'])
assert set(filter(None, c.run('index-selected', ['git', 'diff', '--cached', '--name-only', '--no-renames', '-z']).decode().split('\0'))) == SELECTED
parts = c.run('staged-objects', ['git', 'diff', '--cached', '--raw', '--no-abbrev', '--no-renames', '-z']).split(b'\0')
assert len(parts) % 2 == 1
objects = {}
for index in range(0, len(parts) - 1, 2):
    fields, value = parts[index].decode().split(), parts[index + 1].decode()
    assert len(fields) == 5 and value in SELECTED and fields[-1] in ('A', 'M')
    payload = (ROOT / value).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    mode = '100755' if stat.S_IMODE((ROOT / value).stat().st_mode) & 0o111 else '100644'
    assert fields[3] == oid and fields[1] == mode, value
    objects[value] = {'oid': oid, 'mode': mode}
assert set(objects) == SELECTED
save('staged-selected-objects-local.json', objects)
c.run('authored-check', ['git', 'diff', '--cached', '--check', '--',
    *AUTHORED])
check_preservation(c, 'staged')
c.run('commit', ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
    'commit', '-m', 'Prepare separately selected Android JDK file data observation'])
head, tree, parent = c.run('committed-head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^']).decode().splitlines()
assert parent == BASE
c.bind_committed_sha(head)
save('committed-selected.json', {'at': now(), 'head': head, 'tree': tree, 'parent': parent, 'paths': len(SELECTED)})
committed_raw = c.run('committed-objects', ['git', 'diff-tree', '--no-commit-id', '--raw', '--no-abbrev', '--no-renames', '-r', '-z', BASE, head])
committed_parts = committed_raw.split(b'\0')
assert len(committed_parts) % 2 == 1
committed_objects = {}
for index in range(0, len(committed_parts) - 1, 2):
    fields, value = committed_parts[index].decode().split(), committed_parts[index + 1].decode()
    assert len(fields) == 5 and fields[-1] in ('A', 'M') and value in SELECTED and value not in committed_objects
    committed_objects[value] = {'oid': fields[3], 'mode': fields[1]}
assert committed_objects == objects, 'Committed selected object IDs/modes differ from the verified selected map'
save('committed-selected-objects.json', committed_objects)
check_sources()
assert c.run('remote-prepush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert c.run('push-url-prepush', ['git', 'remote', 'get-url', '--push', '--all', 'origin']).decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
save('push-selected-once.json', {'at': now(), 'head': head, 'tree': tree, 'parent': parent,
    'remote': 'origin', 'ref': 'refs/heads/main', 'force': False,
    'reservationConsumedBeforeSubmit': True, 'retryOnUnknownOutcome': False})
c.run('push', ['git', '-c', 'core.hooksPath=/dev/null', 'push', '--signed=false', '--no-follow-tags', '--recurse-submodules=no', 'origin', head + ':refs/heads/main'], seconds=45)
assert c.run('remote-postpush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [head, 'refs/heads/main']
assert not c.run('index-after', ['git', 'diff', '--cached', '--name-only', '-z'])
check_preservation(c, 'after')
after = collapsed(c.run('collapsed-status-after', ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=normal']))
after_untracked = [preserved_entry(value['path']) for value in after if value['status'] == '??']
before_paths = {value['path'] for value in preservation['untrackedCollapsed']}
after_paths = {value['path'] for value in after_untracked}
removed = sorted(before_paths - after_paths)
added = sorted(after_paths - before_paths)
for value in removed:
    assert any(p == value.rstrip('/') or p.startswith(value) for p in SELECTED), ('Unrelated collapsed entry disappeared', value)
for value in added:
    assert any(prior.endswith('/') and value.startswith(prior) for prior in before_paths), ('Unrelated collapsed entry appeared', value)
save('preservation-selected-after-local.json', {'at': now(), 'statusCollapsed': after, 'untrackedCollapsed': after_untracked,
    'selectedTrackingCollapsedTransitions': {'removed': removed, 'added': added},
    'allPreexistingCollapsedEntryIdentityModesPreserved': True})
save('delivery-selected-receipt.json', {'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent,
    'pushed': True, 'force': False, 'selectedPaths': len(SELECTED), 'selection': row(ROOT / SELECTION),
    'manifest': row(OUT / 'manifest-selected.json'), 'preflight': ACCEPTED_PREFLIGHT_ROWS[0],
    'preservationBefore': ACCEPTED_PREFLIGHT_ROWS[1], 'preflightSeal': ACCEPTED_PREFLIGHT_SEAL,
    'committedObjects': row(OUT / 'committed-selected-objects.json'),
    'pushURL': 'https://github.com/snowdamiz/mixer.git', 'explicitNoTagsSigningOrSubmodulePush': True,
    'protected': PROTECTED, 'protectedByteModesUnchanged': True,
    'cleanTrackedBoundByBaselineTreeAndCompleteRawDiff': True,
    'allCleanTrackedFilesIndependentlyHashed': False,
    'outsideSelectionDirtyByteModeSnapshotsPreserved': len(preservation['tracked']),
    'preexistingCollapsedEntryIdentityModesPreserved': len(preservation['untrackedCollapsed']),
    'afterCollapsedUntrackedEntries': len(after_untracked), 'collapsedSelectedTransitions': {'removed': len(removed), 'added': len(added)},
    'wranglerUntouched': True, 'artifactsStoreAbsent': True, 'indexEmpty': True, 'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row,
    'argvManifest': row(OUT / 'argv-delivery-selected.json'), 'commands': c.records,
    'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
    'rawHelperInventoriesCommitted': False, 'manualDispatchesPending': 1, 'manualWorkflowDispatchesAuthorized': 1,
    'canonicalAndroidChanges': 0, 'productionDefaultsChanged': False, 'allExistingHoldsUntouched': True,
    'runtimeCompilerNativeUICaptureProcessInventoryHeldProbesStarted': False,
    'fieldlogRepositoryOperations': 0, 'releaseTagOrGAPromotion': False})
print(json.dumps({'head': head, 'tree': tree, 'parent': parent, 'pushed': True,
                  'paths': len(SELECTED), 'closedCommands': len(c.records)}))
