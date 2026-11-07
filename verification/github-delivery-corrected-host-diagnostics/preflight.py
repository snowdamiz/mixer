"""Fresh read-only bounded delivery preflight; exact root selection remains pending."""
import hashlib
import json
import platform
from pathlib import PurePosixPath

from owned import Commands, OUT, ROOT, now, row, save

BASE = 'c7648ab4aed1b99a6d0a338317bcdbed9e784fa4'
TREE = '3143f5e45b535d525c90cf0df6e9e884c225646c'
PACKETS = {
    'verification/envelope-producer-timeout-experiment': '1b6325654b061d9750e79548c703130a337b7cfb297bb90d195d1bb6a29ca574',
    'verification/envelope-partition-independent-review': '057e500afa3ee57e0469e377c3c4f947053e1fe163f258f52e57ccc80cd5be73',
    'verification/envelope-partition-workflow-context-correction': 'ca2b210b41c082bea7833dfdd9f42cff764b4887af8dd70faecdd4d29b73a5b2',
    'verification/swift-pin-bitmap-lifecycle-correction': 'b3b502ab5027615d1ff6bcb396f893554407e7f4f983ca89c2e3a499b4291ab6',
}
PROTECTED = {
    '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
    'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
}


def check(path, expected):
    actual = row(path)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], str(path)
    return actual


def safe_relative(path):
    p = PurePosixPath(path)
    assert path and not p.is_absolute() and '..' not in p.parts and '\\' not in path, path
    assert not any(x.is_symlink() for x in (ROOT / path).parents), path


packet_paths = []
packet_rows = []
for directory, expected in PACKETS.items():
    path = ROOT / directory
    seal_row = row(path / 'seal.json')
    assert seal_row['sha256'] == expected, directory
    seal = json.loads((path / 'seal.json').read_bytes())
    files = seal.get('files') or {r['path']: r for r in seal['members']}
    members = []
    for name, expected_row in files.items():
        safe_relative(directory + '/' + name)
        members.append(check(path / name, expected_row))
    packet_paths.extend([directory + '/seal.json', *(r['path'] for r in members)])
    packet_rows.append({'directory': directory, 'seal': seal_row, 'members': len(members),
                        'memberBytes': sum(r['bytes'] for r in members)})
assert len(packet_paths) == len(set(packet_paths))
packet_set = set(packet_paths)

# All complete expected packet bytes are checked above. Tracked dependencies are
# bound separately; new candidate packet paths cannot yet be in the index.
dependencies = {}
def dependency(path, expected):
    safe_relative(path)
    check(ROOT / path, expected)
    if path not in packet_set:
        previous = dependencies.setdefault(path, expected)
        assert previous['bytes'] == expected['bytes'] and previous['sha256'] == expected['sha256'], path

bindings = json.loads((ROOT / 'verification/envelope-partition-independent-review/source-bindings.json').read_bytes())
for path, expected in bindings['runtime_and_contract_dependencies'].items():
    dependency(path, expected)
pack_path = ROOT / 'verification/swift-envelope-ci-pack'
pack = json.loads((pack_path / 'manifest.json').read_bytes())
assert len(pack['members']) == 86
for expected in pack['members']:
    dependency('verification/swift-envelope-ci-pack/' + expected['path'], expected)

lifecycle_dir = ROOT / 'verification/swift-pin-bitmap-lifecycle-correction'
lifecycle = json.loads((lifecycle_dir / 'manifest.json').read_bytes())
assert len(lifecycle['baselineCommitParentSupplied']) >= 8 and BASE.startswith(lifecycle['baselineCommitParentSupplied'])
assert lifecycle['baselineGitTreeParentSupplied'] == TREE
for name, expected in lifecycle['baselineFiles'].items():
    dependency('vm/' + name, expected)
baseline = json.loads((lifecycle_dir / 'baseline-bindings.json').read_bytes())
for key in ('frozenSeals', 'sourceDiagnosisInputs'):
    for path, expected in baseline[key].items():
        dependency(path, expected)

protected_rows = {}
for name, expected in PROTECTED.items():
    actual = row(ROOT / name)
    assert actual['sha256'] == expected, name
    protected_rows[name] = actual

c = Commands(210, 12, 'preflight-')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [BASE, TREE]
assert c.run('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
origin_url = c.run('origin-url', ['git', 'remote', 'get-url', 'origin']).decode().strip()
assert origin_url in ('git@github.com:snowdamiz/mixer.git', 'https://github.com/snowdamiz/mixer.git'), origin_url
assert c.run('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert not c.run('index', ['git', 'diff', '--cached', '--name-only', '-z'])
raw_status = c.run('status-collapsed', ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=normal'])


def parse_status(raw):
    result = []
    for entry in raw.split(b'\0'):
        if entry:
            value = entry.decode()
            assert len(value) > 3 and value[2] == ' ' and not ('R' in value[:2] or 'C' in value[:2]), 'Unsupported status record'
            result.append({'status': value[:2], 'path': value[3:]})
    return result


status = parse_status(raw_status)
explicit = parse_status(c.run('selected-packet-status', ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', *sorted(packet_paths)]))
assert {r['path'] for r in explicit}.issubset(packet_set)
versions = {tool: c.run(tool + '-version', [tool, '--version']).decode().strip() for tool in ('git', 'gh')}
raw_index = c.run('dependencies-index', ['git', 'ls-files', '--stage', '-z', '--', *sorted(dependencies)])
index = {}
for entry in raw_index.split(b'\0'):
    if entry:
        meta, path = entry.decode().split('\t')
        mode, oid, stage = meta.split()
        assert mode in ('100644', '100755') and stage == '0'
        index[path] = oid
assert set(index) == set(dependencies), {'missing': sorted(set(dependencies) - set(index))}
tracked_bindings = []
for path in sorted(dependencies):
    raw = (ROOT / path).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert oid == index[path], path
    tracked_bindings.append({**row(ROOT / path), 'gitBlob': oid})
assert not c.run('dependencies-diff', ['git', 'diff', '--name-only', '-z', '--', *sorted(dependencies)])
for name, expected in protected_rows.items():
    assert row(ROOT / name) == expected, name

save('explicit-packet-inventory.json', {'at': now(), 'files': sorted(packet_paths), 'gitStatus': explicit,
     'packets': packet_rows, 'completeForFourFrozenPackets': True,
     'activeLifecycleHostSiblingRead': False, 'finalSelectionPending': True})
save('local-inventory.json', {'at': now(), 'status': status, 'statusRecordCount': len(status),
     'dependencies': tracked_bindings, 'protected': protected_rows,
     'untrackedInventory': 'collapsed directory records only; exact prospective packet members inventoried separately',
     'readOnly': True, 'unrelatedPathsPreserved': True})
save('candidate-paths.json', {'schema': 1, 'at': now(), 'selectionPending': True,
     'sealedPacketPaths': sorted(packet_paths), 'activeLifecycleHostSiblingExcludedUntilRootSelection': True,
     'rootOwnedGlobalsDeferred': True, 'actualResultSmallFilesDeferredUntilRootSelection': True,
     'explicitExclusions': [*PROTECTED, '.wrangler', 'raw CI artifacts', 'local inventories', 'helper outputs', 'FieldLog repository']})
save('preflight.json', {'schema': 1, 'at': now(), 'base': BASE, 'baseTree': TREE, 'branch': 'main',
     'originMain': BASE, 'originURL': origin_url, 'indexEmpty': True, 'packets': packet_rows,
     'unchangedTrackedDependencies': len(tracked_bindings),
     'dependencyBindingsLocalOnly': row(OUT / 'local-inventory.json'),
     'explicitSelectedInventoryLocalOnly': row(OUT / 'explicit-packet-inventory.json'),
     'statusRecordCount': len(status),
     'statusCounts': {s: sum(r['status'] == s for r in status) for s in sorted({r['status'] for r in status})},
     'candidatePaths': row(OUT / 'candidate-paths.json'), 'protectedFiles': protected_rows,
     'tools': {**versions, 'python': platform.python_version()}, 'helper': row(OUT / 'owned.py'),
     'helperDesignReusedOnly': 'verification/github-delivery-reviewed-host-slices/owned.py',
     'priorHelpersOrAdmissionsReplayed': False, 'commands': c.records,
     'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
     'canonicalWritesStagingCommitPushDispatch': 0, 'fieldlogOperations': 0,
     'compilerProductRuntimeNativeUICaptureProcessInventoryHeldProbeStarted': False,
     'holdsPreserved': ['20745', '20770', '20780', '20817', '20842', '20851', '20866', 'oldfetch', 'UnitA', 'broadhosted', 'FieldLog40802230894PGID2424PID2621'],
     'selectionPending': True})
print(json.dumps({'preflight': 'passed', 'commands': len(c.records), 'packetPaths': len(packet_paths),
     'unchangedTrackedDependencies': len(tracked_bindings), 'statusRecordCount': len(status),
     'tools': versions, 'selectionPending': True}))
