"""One exact root-selected commit and nonforce push; no helper/raw outputs staged."""
import hashlib
import json
from pathlib import PurePosixPath

from owned import Commands, OUT, ROOT, now, row, save

SELECTION = 'verification/next-host-diagnostics-selection-2026-10-29/selection.json'
SELECTION_SHA = '60ab18bb4ebfd736c64f8a56f9ca597086309f1c7bc49ccaa242f42f4d37511c'
assert row(ROOT / SELECTION)['sha256'] == SELECTION_SHA
s = json.loads((ROOT / SELECTION).read_bytes())
pre = json.loads((OUT / 'preflight.json').read_bytes())
inventory = json.loads((OUT / 'local-inventory.json').read_bytes())
assert not (OUT / 'delivery-once.json').exists(), 'One commit/push reservation consumed'
assert s['base'] == {'head': pre['base'], 'tree': pre['baseTree']}
assert s['authorization'] == {
    'repository': 'snowdamiz/mixer', 'nonforcePush': 'origin/main',
    'commitScope': 'exact seal members and seals for listed packets, plus listed canonical and small paths',
    'automaticEngineCI': True, 'manualInvocations': 2, 'noRetryOnUnknownOutcome': True,
    'canonicalVMInstallation': False, 'FieldLogActions': False, 'releasesOrTags': False,
}
assert len(s['canonicalPaths']) == 6 and len(s['smallPaths']) == 6 and len(s['packets']) == 5


def check(path, expected):
    actual = row(path)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], str(path)
    return actual


def checked_seal(directory, expected_sha):
    d = ROOT / directory
    assert row(d / 'seal.json')['sha256'] == expected_sha
    seal = json.loads((d / 'seal.json').read_bytes())
    files = seal.get('files') or {r['path']: r for r in seal['members']}
    result = [row(d / 'seal.json')]
    for name, expected in files.items():
        result.append(check(d / name, expected))
    return result


selected = set(s['canonicalPaths'] + s['smallPaths'])
packet_rows = []
for packet in s['packets']:
    members = checked_seal(packet['path'], packet['sealSHA256'])
    selected.update(r['path'] for r in members)
    packet_rows.append({'directory': packet['path'], 'sealSHA256': packet['sealSHA256'],
                        'membersIncludingSeal': len(members)})
assert len(selected) == 85
assert SELECTION in selected
assert all(not p.startswith(('vm/', '.wrangler', str(OUT.relative_to(ROOT)) + '/')) for p in selected)
assert not any(p in s['protectedPaths'] for p in selected)
for path in selected:
    p = PurePosixPath(path)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in path, path
    assert all(not parent.is_symlink() for parent in (ROOT / path).parents), path

check(ROOT / s['rootReview']['path'], s['rootReview'] | {'bytes': (ROOT / s['rootReview']['path']).stat().st_size})
assert row(ROOT / 'verification/reviewed-host-slice-actual-results/sanitized-result.json')['sha256'] == '94446f42e998af489f91d6f7a3e24a1bd0419570e97f68a552e78894ad3ae121'
assert row(ROOT / 'verification/reviewed-host-slice-actual-results/seal.json')['sha256'] == 'db5948863b9314229821726db2f9e7ca4821371b82442a6a3fde1fe048a952a4'
for dispatch in s['dispatches']:
    path = '.github/workflows/' + dispatch['workflow']
    assert path in selected and row(ROOT / path)['sha256'] == dispatch['workflowSHA256']
assert (ROOT / '.github/workflows/envelope-partition-diagnostic.yml').read_bytes() == (ROOT / 'verification/envelope-partition-workflow-context-correction/workflow-proposal.yml').read_bytes()
assert (ROOT / '.github/workflows/swift-pin-bitmap-lifecycle-admission.yml').read_bytes() == (ROOT / 'verification/swift-pin-bitmap-lifecycle-host-admission/workflow.yml').read_bytes()
for path, expected in s['protectedPaths'].items():
    check(ROOT / path, expected)
gate = json.loads((ROOT / 'gates/ga.json').read_bytes())
assert {status: sum(g['status'] == status for g in gate['gates']) for status in ('running', 'planned', 'verified')} == s['gates']

dependencies = {}
def dependency(expected):
    check(ROOT / expected['path'], expected)
    if expected['path'] not in selected:
        previous = dependencies.setdefault(expected['path'], expected)
        assert previous['bytes'] == expected['bytes'] and previous['sha256'] == expected['sha256']
for expected in inventory['dependencies']:
    dependency(expected)
basis = json.loads((ROOT / 'verification/swift-pin-bitmap-lifecycle-host-admission/source-basis.json').read_bytes())
for seal_path, expected in basis['frozenSeals'].items():
    for expected_row in checked_seal(seal_path.rsplit('/', 1)[0], expected['sha256']):
        dependency(expected_row)
manifest = json.loads((ROOT / basis['source']['manifest']['path']).read_bytes())
assert len(manifest['candidateFiles']) == 136
for logical, expected in manifest['candidateFiles'].items():
    dependency({'path': manifest['materializationPaths'][logical], **expected})
rows = [row(ROOT / p) for p in sorted(selected)]
assert sum(r['bytes'] for r in rows) < 8 * 1024 * 1024
save('manifest.json', {
    'schema': 1, 'at': now(), 'selection': row(ROOT / SELECTION), 'base': s['base'],
    'members': rows, 'selectedMembers': len(rows), 'selectedBytes': sum(r['bytes'] for r in rows),
    'packets': packet_rows, 'helperRawOutputInventoryArtifactIncluded': False,
    'canonicalVMInstallation': False, 'tools': pre['tools'], 'ownedHelper': row(OUT / 'owned.py'),
})
save('delivery-dependency-inventory.json', {'at': now(), 'members': [dependencies[k] for k in sorted(dependencies)],
     'scope': 'tracked dependencies only; complete selected packet bytes independently checked'})
paths = [r['path'] for r in rows]
with (OUT / 'paths.nul').open('xb') as f:
    f.write(b''.join(p.encode() + b'\0' for p in paths))

c = Commands(240, 18, 'delivery-')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [s['base']['head'], s['base']['tree']]
assert c.run('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert c.run('remote-before', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [s['base']['head'], 'refs/heads/main']
assert not c.run('index-before', ['git', 'diff', '--cached', '--name-only', '-z'])
raw = c.run('dependency-index', ['git', 'ls-files', '--stage', '-z', '--', *sorted(dependencies)])
index = {}
for entry in raw.split(b'\0'):
    if entry:
        meta, path = entry.decode().split('\t')
        mode, oid, stage = meta.split()
        assert mode in ('100644', '100755') and stage == '0'
        index[path] = oid
assert set(index) == set(dependencies)
for path, expected in dependencies.items():
    raw_file = (ROOT / path).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(raw_file)).encode() + b'\0' + raw_file).hexdigest()
    assert oid == index[path] and ('gitBlob' not in expected or oid == expected['gitBlob']), path
assert not c.run('dependency-diff', ['git', 'diff', '--name-only', '-z', '--', *sorted(index)])
for expected in rows:
    assert row(ROOT / expected['path']) == expected
for path, expected in s['protectedPaths'].items():
    check(ROOT / path, expected)
save('delivery-once.json', {
    'schema': 1, 'at': now(), 'selection': row(ROOT / SELECTION), 'manifest': row(OUT / 'manifest.json'),
    'oneCommitAndNonforcePushAuthorizedByRoot': True, 'retryOnUnknownOutcome': False,
})
c.run('stage', ['git', 'add', '--force', '--pathspec-from-file=' + str(OUT / 'paths.nul'), '--pathspec-file-nul'])
for expected in rows:
    assert row(ROOT / expected['path']) == expected
assert set(filter(None, c.run('index-selected', ['git', 'diff', '--cached', '--name-only', '--no-renames', '-z']).decode().split('\0'))) == selected
c.run('authored-check', ['git', 'diff', '--cached', '--check', '--', *s['canonicalPaths'], *s['smallPaths']])
raw = c.run('staged-objects', ['git', 'diff', '--cached', '--raw', '--no-abbrev', '--no-renames', '-z']).split(b'\0')
assert len(raw) % 2 == 1
objects = {}
for i in range(0, len(raw) - 1, 2):
    fields = raw[i].decode().split()
    path = raw[i + 1].decode()
    assert len(fields) == 5 and path in selected and fields[-1] in ('A', 'M')
    assert fields[1] in ('100644', '100755')
    raw_file = (ROOT / path).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(raw_file)).encode() + b'\0' + raw_file).hexdigest()
    assert fields[3] == oid
    objects[path] = oid
assert set(objects) == selected
c.run('commit', ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                 'commit', '-m', 'Admit corrected lifecycle and envelope host diagnostics'])
head, tree, parent = c.run('committed-head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^']).decode().splitlines()
assert parent == s['base']['head']
save('committed.json', {'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent,
     'pushAttempted': False, 'selectedPaths': len(rows), 'selection': row(ROOT / SELECTION)})
assert set(filter(None, c.run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--no-renames', '--name-only', '-r', '-z', 'HEAD']).decode().split('\0'))) == selected
assert c.run('remote-prepush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [parent, 'refs/heads/main']
save('push-once.json', {'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent,
     'remote': 'origin', 'ref': 'refs/heads/main', 'force': False,
     'reservationConsumedBeforeSubmit': True, 'retryOnUnknownOutcome': False})
c.run('push', ['git', '-c', 'core.hooksPath=/dev/null', 'push', 'origin', 'HEAD:refs/heads/main'], seconds=45)
assert c.run('remote-postpush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [head, 'refs/heads/main']
assert not c.run('index-after', ['git', 'diff', '--cached', '--name-only', '-z'])
for path, expected in s['protectedPaths'].items():
    check(ROOT / path, expected)
for expected in rows:
    assert row(ROOT / expected['path']) == expected
save('receipt.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent, 'pushed': True, 'force': False,
    'manifest': row(OUT / 'manifest.json'), 'selection': row(ROOT / SELECTION), 'selectedPaths': len(rows),
    'trackedDependenciesUnchanged': len(dependencies), 'commands': c.records,
    'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'protectedFilesPreserved': True, 'rootGlobalsUnchangedAfterSelection': True,
    'helperRawOutputInventoryArtifactCommitted': False, 'indexEmpty': True,
    'canonicalVMInstalled': False, 'localCompilerProductRuntimeNativeUICaptureHeldProbeStarted': False,
    'fieldlogOperations': 0, 'releaseTagOrGAPromotion': False, 'manualDispatchesPending': 2,
})
print(json.dumps({'head': head, 'tree': tree, 'pushed': True, 'paths': len(rows),
                  'unchangedTrackedDependencies': len(dependencies), 'commands': len(c.records)}))
