"""One exact root-selected commit and nonforce push. Helper evidence stays local."""
import hashlib
import json
from pathlib import PurePosixPath
from owned import Commands, OUT, ROOT, now, row, save

SELECTION = 'verification/host-slice-selection-2026-10-29/selection.json'
SELECTION_SHA = '48c02d1231ad81f13320ac914ac636f90b7f84eda2e97ecaaf3c096deaa941b6'
assert row(ROOT / SELECTION)['sha256'] == SELECTION_SHA
s = json.loads((ROOT / SELECTION).read_bytes())
pre = json.loads((OUT / 'preflight.json').read_bytes())
inventory = json.loads((OUT / 'local-inventory.json').read_bytes())
assert not (OUT / 'delivery-once.json').exists(), 'One commit/push reservation already consumed'
assert s['baseline'] == {'head': pre['base'], 'tree': pre['baseTree']}
assert s['authorizedDelivery'] == {
    'repository': 'snowdamiz/mixer', 'remote': 'origin', 'branch': 'main', 'force': False,
    'automaticEngineCI': True, 'manualWorkflowDispatch': 'exactly one pin-bitmap-v1 on the delivered head',
    'canonicalVMSourceEdits': False, 'FieldLogActions': False, 'publicationTagsOrReleases': False,
}
expected_seals = {p['directory']: p['seal']['sha256'] for p in pre['packets']}
assert set(s['publishPackets']) == set(expected_seals)
selected = set(s['publishSmallFiles'] + s['publishCanonical'])
for directory in s['publishPackets']:
    d = ROOT / directory
    assert row(d / 'seal.json')['sha256'] == expected_seals[directory]
    seal = json.loads((d / 'seal.json').read_bytes())
    files = seal.get('files') or {r['path']: r for r in seal['members']}
    selected.add(directory + '/seal.json')
    for name, expected in files.items():
        p = d / name
        actual = row(p)
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], str(p)
        selected.add(actual['path'])
assert len(selected) == 69
assert all(not p.startswith(('vm/', '.wrangler', 'verification/github-delivery-reviewed-host-slices/')) for p in selected)
assert not any(p in s['preservation']['protectedLocalFiles'] for p in selected)
for path in selected:
    parts = PurePosixPath(path)
    assert not parts.is_absolute() and '..' not in parts.parts and '\\' not in path, path
    for ancestor in (ROOT / path).parents:
        assert not ancestor.is_symlink(), str(ancestor)
        if ancestor == ROOT:
            break

assert row(ROOT / s['pinBitmap']['workflow'])['sha256'] == s['pinBitmap']['workflowSHA256']
assert (ROOT / s['pinBitmap']['workflow']).read_bytes() == (ROOT / 'verification/swift-pin-bitmap-host-binding-correction/workflow.yml').read_bytes()
assert row(ROOT / s['sharedFixture']['installedWorkflow'])['sha256'] == s['sharedFixture']['installedSHA256']
protected = s['preservation']['protectedLocalFiles']
for path, expected in protected.items():
    actual = row(ROOT / path)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
gate = json.loads((ROOT / 'gates/ga.json').read_bytes())
assert {status: sum(g['status'] == status for g in gate['gates']) for status in ('running', 'planned', 'verified')} == s['gates']
dependencies = inventory['dependencies']
for expected in dependencies:
    actual = row(ROOT / expected['path'])
    assert all(actual[k] == expected[k] for k in ('path', 'bytes', 'sha256')), expected['path']
rows = [row(ROOT / p) for p in sorted(selected)]
assert sum(r['bytes'] for r in rows) < 8 * 1024 * 1024
save('manifest.json', {
    'schema': 1, 'at': now(), 'selection': row(ROOT / SELECTION), 'base': s['baseline'],
    'members': rows, 'selectedMembers': len(rows), 'selectedBytes': sum(r['bytes'] for r in rows),
    'helperRawOutputInventoryArtifactIncluded': False, 'canonicalVMInstallation': False,
    'tools': pre['tools'], 'ownedHelper': row(OUT / 'owned.py'),
})
paths = [r['path'] for r in rows]
with (OUT / 'paths.nul').open('xb') as f:
    f.write(b''.join(p.encode() + b'\0' for p in paths))
c = Commands(240, 18, 'delivery-')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [s['baseline']['head'], s['baseline']['tree']]
assert c.run('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert c.run('remote-before', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == s['baseline']['head']
assert not c.run('index-before', ['git', 'diff', '--cached', '--name-only', '-z'])
raw = c.run('dependency-index', ['git', 'ls-files', '--stage', '-z', '--', *sorted(r['path'] for r in dependencies)])
index = {}
for entry in raw.split(b'\0'):
    if entry:
        meta, path = entry.decode().split('\t')
        mode, oid, stage = meta.split()
        assert mode in ('100644', '100755') and stage == '0'
        index[path] = oid
assert set(index) == {r['path'] for r in dependencies}
for expected in dependencies:
    raw = (ROOT / expected['path']).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert oid == index[expected['path']] == expected['gitBlob'], expected['path']
assert not c.run('dependency-diff', ['git', 'diff', '--name-only', '-z', '--', *sorted(index)])
save('delivery-once.json', {
    'schema': 1, 'at': now(), 'selection': row(ROOT / SELECTION), 'manifest': row(OUT / 'manifest.json'),
    'oneCommitAndNonforcePushAuthorizedByRoot': True, 'retryOnUnknownOutcome': False,
})
c.run('stage', ['git', 'add', '--force', '--pathspec-from-file=' + str(OUT / 'paths.nul'), '--pathspec-file-nul'])
for expected in rows:
    assert row(ROOT / expected['path']) == expected
assert set(filter(None, c.run('index-selected', ['git', 'diff', '--cached', '--name-only', '--no-renames', '-z']).decode().split('\0'))) == selected
c.run('authored-check', ['git', 'diff', '--cached', '--check', '--', *s['publishCanonical'], *s['publishSmallFiles']])
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
                 'commit', '-m', 'Adopt shared fixture CI and admit reviewed pin bitmap host regression'])
head, tree, parent = c.run('committed-head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^']).decode().splitlines()
assert parent == s['baseline']['head']
assert set(filter(None, c.run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--no-renames', '--name-only', '-r', '-z', 'HEAD']).decode().split('\0'))) == selected
assert c.run('remote-prepush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == parent
c.run('push', ['git', '-c', 'core.hooksPath=/dev/null', 'push', 'origin', 'HEAD:refs/heads/main'], seconds=45)
assert c.run('remote-postpush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head
assert not c.run('index-after', ['git', 'diff', '--cached', '--name-only', '-z'])
for path, expected in protected.items():
    assert row(ROOT / path)['sha256'] == expected['sha256']
for expected in rows:
    assert row(ROOT / expected['path']) == expected
save('receipt.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent, 'pushed': True, 'force': False,
    'manifest': row(OUT / 'manifest.json'), 'selection': row(ROOT / SELECTION), 'selectedPaths': len(rows),
    'commands': c.records, 'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'protectedFilesPreserved': True, 'rootGlobalsUnchangedAfterSelection': True,
    'helperRawOutputInventoryArtifactCommitted': False, 'indexEmpty': True,
    'canonicalVMInstalled': False, 'localCompilerProductRuntimeNativeUICaptureHeldProbeStarted': False,
    'fieldlogOperations': 0, 'releaseTagOrGAPromotion': False, 'manualDispatchPending': True,
})
print(json.dumps({'head': head, 'tree': tree, 'pushed': True, 'paths': len(rows), 'commands': len(c.records)}))

