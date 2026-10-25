"""Independent read-only verification of frozen review inputs and source diff."""
import difflib
import hashlib
import io
import json
import pathlib
import tarfile

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / 'verification/apple-settings-failure-instrumentation'
EXPECTED = 'd637e80716b9407028f059dd44673e09cd74f536d7bec2909fa02a0da5b40190'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def bound(data, row):
    assert len(data) == row['bytes'] and sha(data) == row['sha256']

def main():
    handoff_data = (PACKET / 'handoff.json').read_bytes()
    assert sha(handoff_data) == EXPECTED
    handoff = json.loads(handoff_data)
    inputs = json.loads((BASE / 'inputs.json').read_text())
    for name, row in inputs['files'].items():
        bound((ROOT / name).read_bytes(), row)
    for name, row in handoff['members'].items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink()
        bound(path.read_bytes(), row)
    expected = {name for name in handoff['members'] if name.startswith(str(PACKET.relative_to(ROOT)) + '/')}
    actual = {str(path.relative_to(ROOT)) for path in PACKET.rglob('*') if path.is_file() and path.name not in ['handoff.json', 'handoff.sha256']}
    assert expected == actual
    provenance = json.loads((PACKET / 'provenance.json').read_text())
    for name, row in provenance['acceptedInputs'].items():
        bound((ROOT / name).read_bytes(), row)
    acceptance = json.loads((ROOT / 'verification/apple-settings-bridge-timeout-root-review/acceptance.json').read_text())
    assert acceptance['handoffSHA256'] == handoff['diagnosisHandoffSHA256'] == '162ffcc666e601263a70a6226289eab833e6335d84fa9a36b89c91426e248209'
    assert acceptance['nativeRetrySelected'] is False and acceptance['gaAccepted'] is False
    bindings = json.loads((PACKET / 'source-bindings.json').read_text())['sources']
    for row in bindings:
        archive = (ROOT / row['archive']).read_bytes()
        assert sha(archive) == row['archiveSHA256']
        with tarfile.open(fileobj=io.BytesIO(archive)) as outer:
            nested = outer.extractfile(row['nestedMember']).read()
        assert sha(nested) == row['nestedSHA256']
        with tarfile.open(fileobj=io.BytesIO(nested)) as inner:
            source = inner.extractfile(row['member']).read()
        bound(source, row)
        assert source == (PACKET / row['copy']).read_bytes()
    old = (PACKET / 'original/ToggleUITests.swift').read_text()
    new = (PACKET / 'derivative/ToggleUITests.swift').read_text()
    assert old[old.index('    func start()'):] == new[new.index('    func start()'):]
    addition = '    private let firstFailureDiagnostic = SettingsFirstFailureDiagnostic()\n'
    assert new.count(addition) == 1
    assert old[:old.index('    private func post(')] == new[:new.index('    private func post(')].replace(addition, '')
    assert (PACKET / 'original/DiagnosticTransport.swift').read_bytes() == (PACKET / 'derivative/DiagnosticTransport.swift').read_bytes()
    patch = ''
    for name in ['DiagnosticTransport.swift', 'ToggleUITests.swift', 'SettingsFailureDiagnostic.swift']:
        a, b = PACKET / 'original' / name, PACKET / 'derivative' / name
        patch += ''.join(difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [], b.read_text().splitlines(keepends=True),
            fromfile='original/' + name if a.exists() else '/dev/null', tofile='derivative/' + name))
    assert patch == (PACKET / 'source.patch').read_text()
    source_tree = sha((json.dumps(provenance['derivativeSources'], sort_keys=True, separators=(',', ':')) + '\n').encode())
    assert source_tree == handoff['derivativeSourceTreeSHA256'] == provenance['derivativeSourceTreeSHA256']
    for name, row in provenance['derivativeSources'].items():
        bound((PACKET / name).read_bytes(), row)
    print(json.dumps({'schema': 1, 'verified': True, 'handoffSHA256': EXPECTED, 'sealedMembers': len(handoff['members']),
        'frozenOriginalArchiveMembersCompared': len(bindings), 'exactPatchReconstructed': True, 'sourceBoundaryVerified': True,
        'derivativeSourceTreeSHA256': source_tree, 'producerPacketUnchanged': True, 'writesPerformed': 0,
        'nativeRuntimeExecuted': False, 'excludedLanesReadImportedOrExecuted': False}, sort_keys=True))

if __name__ == '__main__':
    main()
