"""Read-only bounded preflight; no staging, canonical writes or remote mutations."""
import hashlib
import json
import platform
from pathlib import Path
from owned import Commands, OUT, ROOT, now, row, save

BASE = '00e087210c24406aff49bcf3563bd4226e76660b'
TREE = '8ffa6120f3173815ff12fdcb094554f000410ffc'
PACKETS = {
    'verification/swift-dense512-product-integration': '290909956b188ed46c73c2c73541c8ed60a80788f0d51f9adbca0940579a54f2',
    'verification/swift-pin-bitmap-independent': '84b2cc15c97f951d850904a733ec747fbbb0b17ee23fe8f0b19a8da285c5dfaa',
    'verification/swift-pin-bitmap-host-binding-correction': 'f44236c30b0a789b86171d864cf997537d7055a4a32543243854871081b2ab3f',
    'verification/shared-fixture-default-ci-adoption': 'c648504f9b26fb66daf7685e1e506df9282c3a300a22c3299e2adf56815929c6',
}


def check(path, expected):
    actual = row(path)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], str(path)
    return actual


packet_paths = []
packet_rows = []
for directory, expected in PACKETS.items():
    path = ROOT / directory
    seal_row = row(path / 'seal.json')
    assert seal_row['sha256'] == expected, directory
    seal = json.loads((path / 'seal.json').read_bytes())
    files = seal.get('files') or {r['path']: r for r in seal['members']}
    members = [check(path / name, expected_row) for name, expected_row in files.items()]
    packet_paths.extend([directory + '/seal.json', *(r['path'] for r in members)])
    packet_rows.append({'directory': directory, 'seal': seal_row, 'members': len(members)})

manifest = json.loads((ROOT / 'verification/swift-dense512-product-integration/manifest.json').read_bytes())
dependencies = {}
for name, expected in manifest['baselineFiles'].items():
    path = 'vm/' + name
    check(ROOT / path, expected)
    dependencies[path] = expected
for name, expected in manifest['protectedFiles'].items():
    check(ROOT / name, expected)
    if name not in ('.github/workflows/hosted.yml', 'hosted/lib/mixer_hosted/browser_auth/store.ex'):
        dependencies[name] = expected
consumer = json.loads((ROOT / 'verification/swift-pin-bitmap-independent/consumer-bindings.json').read_bytes())
for name, expected in consumer['files'].items():
    check(ROOT / name, expected)
    dependencies[name] = expected
fixture = json.loads((ROOT / 'verification/shared-fixture-default-ci-adoption/dependencies.json').read_bytes())
for expected in fixture['members']:
    check(ROOT / expected['path'], expected)
    dependencies[expected['path']] = expected

prior_records = []
def closed_previous(name, expected_stop=None):
    label = 'preflight-' + name
    result = json.loads((OUT / (label + '.command.json')).read_bytes())
    assert result['admitted'] and result['directChildReaped'] and result['ownedGroupAbsent'] is True
    assert result['stdoutEOF'] and result['stderrEOF'] and result['stopReason'] == expected_stop
    for key in ('stdout', 'stderr'):
        check(ROOT / result[key]['path'], result[key])
    if expected_stop is None:
        assert result['exit'] == 0 and result['failure'] is None
    prior_records.append({'name': label, **{k: result[k] for k in ('exit', 'admitted', 'stopReason', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF')}})
    return (OUT / (label + '.stdout')).read_bytes()
assert closed_previous('head').decode().splitlines() == [BASE, TREE]
assert closed_previous('branch').decode().strip() == 'main'
assert not closed_previous('index')
closed_previous('status', 'stream-cap')
c = Commands(150, 8, 'preflight2-')
raw_status = c.run('status-collapsed', ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=normal'])
status = []
for entry in raw_status.split(b'\0'):
    if entry:
        text = entry.decode()
        assert len(text) > 3 and text[2] == ' ', 'Rename or unsupported status format'
        status.append({'status': text[:2], 'path': text[3:]})
assert c.run('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == BASE
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
bindings = []
for name in sorted(dependencies):
    raw = (ROOT / name).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert oid == index[name], name
    bindings.append({**row(ROOT / name), 'gitBlob': oid})
assert not c.run('dependencies-diff', ['git', 'diff', '--name-only', '-z', '--', *sorted(dependencies)])

protected = {
    '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
    'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
}
for name, expected in protected.items():
    assert row(ROOT / name)['sha256'] == expected
explicit_status = c.run('packet-status', ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', *sorted(PACKETS)])
save('explicit-packet-inventory.json', {'at': now(), 'status': explicit_status.decode().split('\0'), 'completeForFourPackets': True})
save('local-inventory.json', {'at': now(), 'status': status, 'statusRecordCount': len(status),
                              'dependencies': bindings, 'readOnly': True})
save('candidate-paths.json', {
    'schema': 1, 'at': now(), 'selectionPending': True,
    'sealedPacketPaths': sorted(packet_paths),
    'rootOwnedPossiblePaths': ['.github/workflows/verify.yml', '.github/workflows/swift-pin-bitmap-host-admission.yml',
        'PLAN.md', 'STATUS.md', 'work-graph.json',
        'verification/github-delivery-fixture-context-v4/sanitized-result.json',
        'verification/github-delivery-fixture-context-v4/sanitized-result-seal.json',
        'verification/host-diagnostic-checkpoint-2026-10-29/checkpoint.json',
        'verification/host-diagnostic-checkpoint-2026-10-29/fieldlog-output-held.json'],
    'explicitExclusions': [*protected, '.wrangler', 'raw CI artifacts', 'local inventories', 'helper command outputs'],
})
save('preflight.json', {
    'schema': 1, 'at': now(), 'base': BASE, 'baseTree': TREE, 'branch': 'main',
    'originMain': BASE, 'indexEmpty': True, 'packets': packet_rows,
    'unchangedTrackedDependencies': len(bindings), 'dependencyBindingsLocalOnly': row(OUT / 'local-inventory.json'),
    'statusRecordCount': len(status), 'statusCounts': {s: sum(x['status'] == s for x in status) for s in sorted({x['status'] for x in status})},
    'candidatePaths': row(OUT / 'candidate-paths.json'), 'protectedFiles': protected,
    'tools': {**versions, 'python': platform.python_version()},
    'helper': row(OUT / 'owned.py'), 'commands': prior_records + c.records, 'preservedBoundedInventoryFailure': 'preflight-status.command.json', 'inventoryCorrection': 'collapsed untracked directories plus complete explicit packet paths; 1MiB cap unchanged',
    'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'canonicalWritesStagingCommitPushDispatch': 0,
    'compilerProductRuntimeNativeUICaptureInventoryHeldProbeStarted': False,
    'fieldlogOperations': 0, 'selectionPending': True,
})
print(json.dumps({'preflight': 'passed', 'commands': len(prior_records) + len(c.records), 'sealedPacketPaths': len(packet_paths),
                  'unchangedTrackedDependencies': len(bindings), 'statusRecordCount': len(status),
                  'tools': versions, 'selectionPending': True}))
