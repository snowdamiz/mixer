"""One exact frozen-path commit and nonforce origin/main push; no retries."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('axis_expression_delivery_common', Path(__file__).with_name('selection_common_axis_expression.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
import hashlib
import json
import stat
for name in ('StrictCommands','BASE','TREE','S','SELECTION','ROWS','SELECTED','PROTECTED','ROOT','OUT','now','row','save','fingerprint','preserved_entry','raw_rows','collapsed','check_sources','accepted_preflight','ACCEPTED_PREFLIGHT_SEAL','ACCEPTED_PREFLIGHT_ROWS','selected_row'): globals()[name] = getattr(common,name)
# Exact frozen selection drives every staged path and all-object proof.
AUTHORED = sorted(SELECTED)
assert 0 < len(AUTHORED) <= 1024
WHITESPACE_SCOPE_ROW = {'path': 'verification/android-axis-expression-selection-2026-10-29/immutable-formatting-scope.json', 'bytes': 997, 'sha256': 'cd646afc34bea5acd9f1b7c7f3fb4aa9953164e9a0032315ab3b9fe71a467b68'}
assert S['formatting']['scope'] == WHITESPACE_SCOPE_ROW
assert S['formatting']['allContentModeAndObjectProofRetained'] is True
assert row(ROOT / WHITESPACE_SCOPE_ROW['path']) == WHITESPACE_SCOPE_ROW
WHITESPACE_SCOPE = json.loads((ROOT / WHITESPACE_SCOPE_ROW['path']).read_bytes())
assert WHITESPACE_SCOPE['schema'] == 1 and WHITESPACE_SCOPE['status'] == 'one-immutable-evidence-formatting-exception'
assert WHITESPACE_SCOPE['allOtherSelectedPathsMustPassGitDiffCheck'] is True
assert WHITESPACE_SCOPE['normalizationPerformed'] is False
assert WHITESPACE_SCOPE['target'] == {'path': 'verification/android-view-api-package-runtime-actual-review/ACTUAL-REVIEW.md', 'bytes': 8149, 'sha256': 'de6ca8aafe867b871ce3825af5eb987d5656d722a3005da9358c7e8e8f5875a9'}
assert WHITESPACE_SCOPE['sourceSeal'] == {'path': 'verification/android-view-api-package-runtime-actual-review/seal.json', 'bytes': 3290, 'sha256': 'ae86302f253f040a2900c579b76e60c314c7c291330e5210c03c60c2edaf9d7d'}
assert row(ROOT / WHITESPACE_SCOPE['sourceSeal']['path']) == WHITESPACE_SCOPE['sourceSeal']
assert S['formatting']['excludeImmutablePaths'] == [WHITESPACE_SCOPE['target']['path']]
IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS = [next(value for value in ROWS if value['path'] == WHITESPACE_SCOPE['target']['path'])]
for expected in IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS:
    assert selected_row(expected) == expected
FORMATTING = sorted(SELECTED - {value['path'] for value in IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS})
assert len(IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS) == 1 and len(FORMATTING) == 173
assert len(SELECTED) == 174 and set(FORMATTING) | {WHITESPACE_SCOPE['target']['path']} == SELECTED
pre, preservation = accepted_preflight()
assert pre['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF']
assert pre['head'] == BASE and pre['tree'] == TREE and pre['selectedPaths'] == len(SELECTED)
assert not (OUT / 'delivery-followup-once.json').exists()
with (OUT / 'paths-followup.nul').open('xb') as handle:
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


c = StrictCommands('delivery-followup')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [BASE, TREE]
assert c.run('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert c.run('origin', ['git', 'remote', 'get-url', 'origin']).decode().strip() == pre['origin']
assert c.run('push-url-before-stage', ['git', 'remote', 'get-url', '--push', '--all', 'origin']).decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
assert c.run('remote-before', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert not c.run('index-before', ['git', 'diff', '--cached', '--name-only', '-z'])
check_preservation(c, 'before')
save('delivery-followup-once.json', {'at': now(), 'selection': row(ROOT / SELECTION), 'paths': len(SELECTED),
    'oneCommitNonforcePushAuthorized': True, 'retryOnUnknownOutcome': False})
c.run('stage', ['git', 'add', '--pathspec-from-file=' + str(OUT / 'paths-followup.nul'), '--pathspec-file-nul'])
entries = c.run('index-selected', ['git', 'ls-files', '--stage', '-z', '--', *AUTHORED]).split(b'\0')
objects = {}
for entry in entries:
    if not entry:
        continue
    meta, value = entry.split(b'\t', 1)
    fields, value = meta.decode().split(), value.decode()
    assert len(fields) == 3 and fields[2] == '0' and value in SELECTED and value not in objects
    payload = (ROOT / value).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    mode = '100755' if stat.S_IMODE((ROOT / value).stat().st_mode) & 0o111 else '100644'
    assert fields[0] == mode and fields[1] == oid, value
    objects[value] = {'oid': oid, 'mode': mode}
assert set(objects) == SELECTED
selected_object_rows = [{'path': value, **objects[value]} for value in sorted(objects)]
selected_object_digest = hashlib.sha256(json.dumps(selected_object_rows, separators=(',', ':')).encode()).hexdigest()
expected_object_rows = []
for expected in sorted(ROWS, key=lambda value: value['path']):
    payload = (ROOT / expected['path']).read_bytes()
    expected_object_rows.append({'path': expected['path'], 'oid': hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest(), 'mode': expected['mode']})
assert selected_object_rows == expected_object_rows
assert selected_object_digest == hashlib.sha256(json.dumps(expected_object_rows, separators=(',', ':')).encode()).hexdigest()
save('staged-followup-all-index-objects-local.json', objects)
parts = c.run('staged-objects', ['git', 'diff', '--cached', '--raw', '--no-abbrev', '--no-renames', '-z']).split(b'\0')
assert len(parts) % 2 == 1
changed_objects = {}
for index in range(0, len(parts) - 1, 2):
    fields, value = parts[index].decode().split(), parts[index + 1].decode()
    assert len(fields) == 5 and fields[-1] in ('A', 'M') and value in SELECTED and value not in changed_objects
    assert {'oid': fields[3], 'mode': fields[1]} == objects[value], value
    changed_objects[value] = objects[value]
assert changed_objects and set(changed_objects).issubset(SELECTED)
save('staged-followup-changed-objects-local.json', changed_objects)
c.run('authored-check', ['git', 'diff', '--cached', '--check', '--',
    *FORMATTING])
check_preservation(c, 'staged')
c.run('commit', ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
    'commit', '-m', 'Deliver corrected Android axis workflow expression and reviewed host outcomes'])
head, tree, parent = c.run('committed-head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^']).decode().splitlines()
assert parent == BASE
c.bind_committed_sha(head)
save('committed-followup.json', {'at': now(), 'head': head, 'tree': tree, 'parent': parent, 'paths': len(SELECTED)})
committed_raw = c.run('committed-objects', ['git', 'diff-tree', '--no-commit-id', '--raw', '--no-abbrev', '--no-renames', '-r', '-z', BASE, head])
committed_parts = committed_raw.split(b'\0')
assert len(committed_parts) % 2 == 1
committed_objects = {}
for index in range(0, len(committed_parts) - 1, 2):
    fields, value = committed_parts[index].decode().split(), committed_parts[index + 1].decode()
    assert len(fields) == 5 and fields[-1] in ('A', 'M') and value in SELECTED and value not in committed_objects
    committed_objects[value] = {'oid': fields[3], 'mode': fields[1]}
assert committed_objects == changed_objects, 'Committed diff differs from the verified changed-selected subset'
assert set(committed_objects).issubset(SELECTED)
save('committed-followup-objects.json', committed_objects)
check_sources()
assert c.run('remote-prepush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert c.run('push-url-prepush', ['git', 'remote', 'get-url', '--push', '--all', 'origin']).decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
save('push-followup-once.json', {'at': now(), 'head': head, 'tree': tree, 'parent': parent,
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
save('preservation-followup-after-local.json', {'at': now(), 'statusCollapsed': after, 'untrackedCollapsed': after_untracked,
    'allPreexistingCollapsedEntryIdentityModesPreserved': True})
c.complete()
save('delivery-followup-receipt.json', {'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent,
    'pushed': True, 'force': False, 'selectedPaths': len(SELECTED), 'selection': row(ROOT / SELECTION),
    'manifest': row(OUT / 'manifest-followup.json'), 'preflight': ACCEPTED_PREFLIGHT_ROWS[0],
    'preservationBefore': ACCEPTED_PREFLIGHT_ROWS[1], 'preflightSeal': ACCEPTED_PREFLIGHT_SEAL,
    'committedChangedObjects': row(OUT / 'committed-followup-objects.json'),
    'selectedIndexObjectsLocal': row(OUT / 'staged-followup-all-index-objects-local.json'),
    'allSelectedIndexBlobModesVerified': True, 'selectedIndexBlobModeDigestSHA256': selected_object_digest,
    'changedSelectedPaths': len(changed_objects), 'unchangedSelectedPaths': len(SELECTED) - len(changed_objects),
    'unchangedSelectedMembersBoundByParentTreeAndExactCommittedDiff': True,
    'pushURL': 'https://github.com/snowdamiz/mixer.git', 'explicitNoTagsSigningOrSubmodulePush': True,
    'protected': PROTECTED, 'protectedByteModesUnchanged': True,
    'cleanTrackedBoundByBaselineTreeAndCompleteRawDiff': True,
    'allCleanTrackedFilesIndependentlyHashed': False,
    'outsideSelectionDirtyByteModeSnapshotsPreserved': len(preservation['tracked']),
    'preexistingCollapsedEntryIdentityModesPreserved': len(preservation['untrackedCollapsed']),
    'afterCollapsedUntrackedEntries': len(after_untracked), 'collapsedSelectedTransitions': {'removed': len(removed), 'added': len(added)},
    'wranglerUntouched': True, 'artifactsStoreAbsent': True, 'indexEmpty': True, 'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row,
    'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
    'whitespaceCheckScope': WHITESPACE_SCOPE_ROW, 'whitespaceCheckedPaths': len(FORMATTING),
    'immutableEvidenceFormattingExclusions': IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS,
    'unchangedContentAndBlobModeProofPaths': len(SELECTED),
    'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
    'rawHelperInventoriesCommitted': False, 'manualDispatchesPending': 1, 'manualWorkflowDispatchesAuthorized': 0, 'separatelySelectedManualDispatchCeiling': 1, 'manualHostKeys': ['axis'],
    'canonicalAndroidChanges': 0, 'productionDefaultsChanged': False, 'allExistingHoldsUntouched': True,
    'runtimeCompilerNativeUICaptureProcessInventoryHeldProbesStarted': False,
    'fieldlogRepositoryOperations': 0, 'releaseTagOrGAPromotion': False})
print(json.dumps({'head': head, 'tree': tree, 'parent': parent, 'pushed': True,
                  'paths': len(SELECTED), 'closedCommands': len(c.records)}))
