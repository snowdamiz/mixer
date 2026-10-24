#!/usr/bin/env python3
"""Audit retained deployment evidence; no app execution or device access."""
from pathlib import Path
import datetime
import hashlib
import json
import plistlib
import platform
import subprocess
import tarfile
import tempfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
CANDIDATE = BASE / 'candidate-1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    bindings = {}

    def check(path, expected):
        actual = digest(path.read_bytes())
        assert actual == expected, str(path)
        bindings[str(path.relative_to(ROOT))] = actual

    receipt = json.loads((CANDIDATE / 'receipt.json').read_text())
    assert receipt['status'] == 'passed-ios26-deployment-build-baseline'
    assert all(receipt[k] is False for k in ['nativeExecuted', 'guiExecuted', 'physicalExecuted'])
    for name, expected in receipt['artifacts'].items():
        check(CANDIDATE / name, expected)
    source = json.loads((CANDIDATE / 'source-manifest.json').read_text())
    with tarfile.open(CANDIDATE / 'source.tar.gz') as archive:
        files = {m.name: m for m in archive.getmembers() if m.isfile()}
        assert set(files) == set(source)
        for name, expected in source.items():
            assert digest(archive.extractfile(files[name]).read()) == expected, name
            check(ROOT / name, expected)
    commands = json.loads((CANDIDATE / 'commands.json').read_text())
    for command in commands:
        assert command['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            check(CANDIDATE / (command['name'] + '.' + stream), command[stream + 'SHA256'])
    for name in [f'package-{n}' for n in range(9)] + ['generated-package']:
        parsed = json.loads((CANDIDATE / (name + '.stdout')).read_text())
        assert [p['version'] for p in parsed['platforms'] if p['platformName'] == 'ios'] == ['26.0']
    assert 'Test run with 19 tests in 0 suites passed' in (CANDIDATE / 'cli-tests.stdout').read_text()
    cli_command = next(c for c in commands if c['name'] == 'cli-tests')
    scratch = Path(cli_command['argv'][-1])
    assert digest((scratch / 'debug/mixer').read_bytes()) == receipt['cliSHA256']
    dependency_pins = []
    for checkout in sorted((scratch / 'checkouts').iterdir()):
        revision = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        dependency_pins.append({'name': checkout.name, 'revision': revision})
    assert {p['name'] for p in dependency_pins} == {'swift-asn1', 'swift-crypto'}
    with tarfile.open(CANDIDATE / 'generated-app.tar.gz') as archive:
        info = plistlib.loads(archive.extractfile('IOS26Probe.app/Info.plist').read())
        executable = archive.extractfile('IOS26Probe.app/IOS26Probe').read()
    assert info['MinimumOSVersion'] == '26.0'
    assert digest(executable) == receipt['appExecutableSHA256']
    with tempfile.TemporaryDirectory(prefix='mixer-ios26-inspect-') as temporary:
        binary = Path(temporary) / 'IOS26Probe'
        binary.write_bytes(executable)
        process = subprocess.run(['xcrun', 'vtool', '-show-build', str(binary)], capture_output=True, text=True)
        assert process.returncode == 0, process.stderr
        assert process.stdout.count('platform IOSSIMULATOR') == 2
        assert process.stdout.count('minos 26.0') == 2
        assert 'architecture arm64' in process.stdout and 'architecture x86_64' in process.stdout
    (BASE / 'review-mach-o.txt').write_text(process.stdout)
    bindings[str(Path(__file__).relative_to(ROOT))] = digest(Path(__file__).read_bytes())
    bindings[str((CANDIDATE / 'receipt.json').relative_to(ROOT))] = digest((CANDIDATE / 'receipt.json').read_bytes())
    result = {
        'status': 'accepted-deployment-configuration-and-cross-build-only',
        'reviewer': 'root integrator',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': ['python3', str(Path(__file__).relative_to(ROOT))],
        'pythonVersion': platform.python_version(),
        'minimumIOS': '26.0', 'supportedMajorPolicy': '26, 27 and later',
        'packages': 9, 'hostCLITests': 19, 'generatedAppArchitectures': ['arm64', 'x86_64'],
        'sourceFilesVerified': len(source), 'retainedArtifactsVerified': len(receipt['artifacts']),
        'observedCLIDependencies': dependency_pins,
        'archiveInspectionCommand': ['xcrun', 'vtool', '-show-build', '<temporary archived executable>'],
        'archiveInspectionSHA256': digest(process.stdout.encode()),
        'bindings': bindings,
        'limitations': [
            'No simulator, device, app, GUI or capture executed.',
            'Private appearance runtime gate remains 26.5 only; broader runtime qualification is pending.',
            'Rust native archive default changed but no Rust iOS rebuild is claimed by this receipt.',
            'Historical iOS17 compiler receipts and signed protocol fixtures are preserved.',
            'No GA, store, physical-device or FieldLog release qualification.'
        ]
    }
    (BASE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'bindings'}))


if __name__ == '__main__':
    main()
