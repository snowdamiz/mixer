"""Read-only packet verification. No subprocesses, imports of packet code, or writes."""
import argparse
import difflib
import hashlib
import io
import json
import pathlib
import tarfile

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DIAGNOSIS = '162ffcc666e601263a70a6226289eab833e6335d84fa9a36b89c91426e248209'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def checked(path, binding):
    data = path.read_bytes()
    assert len(data) == binding['bytes'] and sha(data) == binding['sha256'], str(path)
    return data

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-handoff-sha256')
    args = parser.parse_args()
    expected = args.expected_handoff_sha256 or (BASE / 'handoff.sha256').read_text().split()[0]
    handoff_data = (BASE / 'handoff.json').read_bytes()
    assert sha(handoff_data) == expected
    handoff = json.loads(handoff_data)
    assert handoff['diagnosisHandoffSHA256'] == DIAGNOSIS and handoff['nativeRetrySelected'] is False
    paths = set()
    for name, binding in handoff['members'].items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink()
        assert path.resolve().is_relative_to(BASE) or name == 'docs/apple-settings-failure-instrumentation.md'
        checked(path, binding)
        paths.add(path.resolve())
    actual = {x.resolve() for x in BASE.rglob('*') if x.is_file() and x.name not in ['handoff.json', 'handoff.sha256']}
    assert actual == {x for x in paths if x.is_relative_to(BASE)}, 'Unsealed/missing packet file'
    provenance = json.loads((BASE / 'provenance.json').read_text())
    for name, binding in provenance['acceptedInputs'].items():
        checked(ROOT / name, binding)
    diagnosis = (ROOT / 'verification/apple-settings-bridge-timeout-diagnosis/handoff.json').read_bytes()
    assert sha(diagnosis) == DIAGNOSIS
    previous = json.loads(diagnosis)
    for name, binding in previous['members'].items():
        checked(ROOT / name, binding)
    acceptance = json.loads((ROOT / 'verification/apple-settings-bridge-timeout-root-review/acceptance.json').read_text())
    assert acceptance['handoffSHA256'] == DIAGNOSIS and acceptance['nativeRetrySelected'] is False
    source_bindings = json.loads((BASE / 'source-bindings.json').read_text())
    for row in source_bindings['sources']:
        archive = (ROOT / row['archive']).read_bytes()
        assert sha(archive) == row['archiveSHA256']
        assert row['archiveSHA256'] == '3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e'
        with tarfile.open(fileobj=io.BytesIO(archive)) as outer:
            nested = outer.extractfile(row['nestedMember']).read()
        assert sha(nested) == row['nestedSHA256']
        with tarfile.open(fileobj=io.BytesIO(nested)) as inner:
            original = inner.extractfile(row['member']).read()
        assert len(original) == row['bytes'] and sha(original) == row['sha256']
        assert (BASE / row['copy']).read_bytes() == original
    ref = provenance['referenceSource']
    archive = (ROOT / ref['archive']).read_bytes()
    assert sha(archive) == ref['archiveSHA256']
    with tarfile.open(fileobj=io.BytesIO(archive)) as source_archive:
        source = source_archive.extractfile(ref['member']).read()
    assert sha(source) == ref['sha256'] and len(source) == ref['bytes']
    for name, binding in provenance['derivativeSources'].items():
        checked(BASE / name, binding)
    source_tree = sha((json.dumps(provenance['derivativeSources'], sort_keys=True, separators=(',', ':')) + '\n').encode())
    assert source_tree == provenance['derivativeSourceTreeSHA256'] == handoff['derivativeSourceTreeSHA256']
    old = (BASE / 'original/ToggleUITests.swift').read_text()
    new = (BASE / 'derivative/ToggleUITests.swift').read_text()
    assert old[old.index('    func start()'):] == new[new.index('    func start()'):]
    property_line = '    private let firstFailureDiagnostic = SettingsFirstFailureDiagnostic()\n'
    assert new.count(property_line) == 1
    assert old[:old.index('    private func post(')] == new[:new.index('    private func post(')].replace(property_line, '')
    assert (BASE / 'original/DiagnosticTransport.swift').read_bytes() == (BASE / 'derivative/DiagnosticTransport.swift').read_bytes()
    patch = ''
    for name in ['DiagnosticTransport.swift', 'ToggleUITests.swift', 'SettingsFailureDiagnostic.swift']:
        a, b = BASE / 'original' / name, BASE / 'derivative' / name
        patch += ''.join(difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],
            b.read_text().splitlines(keepends=True), fromfile='original/' + name if a.exists() else '/dev/null', tofile='derivative/' + name))
    assert patch == (BASE / 'source.patch').read_text()
    receipt = json.loads((BASE / 'host-controls.json').read_text())
    assert receipt['passed'] is True and receipt['passedControls'] == 19 and receipt['scratchRemoved'] is True
    assert all(x['exitCode'] == 0 for x in receipt['commands'])
    assert receipt['nativeVerificationProcessesStarted'] == 0 and receipt['networkListenersStarted'] == 0
    for name, digest in receipt['sourceHashes'].items():
        assert sha((BASE / name).read_bytes()) == digest
    assert sha((BASE / 'controls/HostControls.swift').read_bytes()) == receipt['hostControlSourceSHA256']
    prefix = new[new.index('private final class SettingsTelemetry:'):new.index('    func start()')]
    assembled = 'import Foundation\n' + prefix + '}\n' + (BASE / 'controls/HostControls.swift').read_text()
    assert sha(assembled.encode()) == receipt['exactPostHostAssemblySHA256']
    for n in range(1, 5):
        folder = BASE / f'attempts/host-{n}'
        attempt = json.loads((folder / 'receipt.json').read_text())
        assert sha((folder / 'controls-source.swift').read_bytes()) == attempt['hostControlSourceSHA256']
        assert sha((folder / 'host-assembly.swift').read_bytes()) == attempt['exactPostHostAssemblySHA256']
        assert attempt['scratchRemoved'] is True
        assert bool(attempt.get('passed')) == (n == 4)
    assert (BASE / 'host-controls.json').read_bytes() == (BASE / 'attempts/host-4/receipt.json').read_bytes()
    assert all(x['result']['passed'] for x in receipt['controls'])
    assert len(receipt['controls']) == len({x['case'] for x in receipt['controls']}) == 19
    assert not (BASE / 'scratch').exists()
    print(json.dumps({'schema': 1, 'verified': True, 'handoffSHA256': expected, 'membersVerified': len(paths),
        'acceptedDiagnosisMembersVerified': len(previous['members']), 'hostControlsPassed': 19,
        'retainedAttempts': 4, 'exactSourceBoundaryVerified': True, 'nativeRuntimeExecuted': False,
        'nativeRetrySelected': False, 'gaAccepted': False, 'writesPerformed': 0}, sort_keys=True))

if __name__ == '__main__':
    main()
