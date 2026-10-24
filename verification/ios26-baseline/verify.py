#!/usr/bin/env python3
"""Verify iOS26 deployment defaults without launching an app or device."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import plistlib
import subprocess
import tarfile
import tempfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKAGES = ['', 'sdk', 'activation', 'runtime', 'updates', 'capability-activation',
            'runtime-identity', 'experimental-capability-runtime', 'capabilities']
SCRIPTS = ['runtime/build-vm.py', 'experimental-capability-runtime/build-vm.py',
           'experimental-capability-runtime/build-verification/run.py',
           'native/apple/appearance-v2/build-check.py', 'native/apple/appearance-v2/run.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = BASE / 'candidate-1'
    out.mkdir()
    work = Path(tempfile.mkdtemp(prefix='mixer-ios26-baseline-'))
    files = {ROOT / package / 'Package.swift' for package in PACKAGES}
    files.update(ROOT / name for name in SCRIPTS)
    files.update([ROOT / 'cli/Package.swift', ROOT / 'mixer-product-plan.md', Path(__file__)])
    for package in ['cli', 'sdk', 'updates']:
        for kind in ['Sources', 'Tests']:
            files.update(p for p in (ROOT / package / kind).rglob('*') if p.is_file())
    source = {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}
    (out / 'source-manifest.json').write_text(json.dumps(source, indent=2) + '\n')
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        for name in source:
            archive.add(ROOT / name, arcname=name)
    commands = []

    def run(name, argv):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        (out / (name + '.stdout')).write_text(result.stdout)
        (out / (name + '.stderr')).write_text(result.stderr)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'exitCode': result.returncode,
                         'stdoutSHA256': sha(out / (name + '.stdout')),
                         'stderrSHA256': sha(out / (name + '.stderr'))})
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert result.returncode == 0, (name, result.stderr[-1500:])
        return result.stdout

    receipt = {'status': 'failed', 'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'nativeExecuted': False, 'guiExecuted': False, 'physicalExecuted': False,
               'scope': 'Package declarations, host CLI tests, actual generated unsigned iOS app cross-build. No runtime or GA acceptance.'}
    try:
        run('swift-version', ['xcrun', 'swift', '--version'])
        run('xcode-version', ['xcodebuild', '-version'])
        for index, package in enumerate(PACKAGES):
            data = json.loads(run(f'package-{index}', ['xcrun', 'swift', 'package', '--package-path', str(ROOT / package), 'dump-package']))
            versions = [p['version'] for p in data['platforms'] if p['platformName'] == 'ios']
            assert versions == ['26.0'], (package, versions)
        for name in SCRIPTS:
            ast.parse((ROOT / name).read_text(), filename=name)
        scratch = str(work / 'cli')
        run('cli-tests', ['xcrun', 'swift', 'test', '--package-path', 'cli', '--scratch-path', scratch])
        binary = work / 'cli/debug/mixer'
        assert binary.is_file()
        project = work / 'IOS26Probe'
        run('create', [str(binary), 'create', 'IOS26Probe', '--directory', str(project),
                       '--application', 'com.example.mixer.ios26probe', '--sdk-path', str(ROOT / 'sdk')])
        generated = json.loads(run('generated-package', ['xcrun', 'swift', 'package', '--package-path', str(project), 'dump-package']))
        assert [p['version'] for p in generated['platforms'] if p['platformName'] == 'ios'] == ['26.0']
        run('generated-ios-build', [str(binary), 'build', '--platform', 'ios', '--directory', str(project)])
        app = project / '.mixer/ios-build/Build/Products/Debug-iphonesimulator/IOS26Probe.app'
        info = plistlib.loads((app / 'Info.plist').read_bytes())
        assert info['MinimumOSVersion'] == '26.0'
        output = run('generated-mach-o', ['xcrun', 'vtool', '-show-build', str(app / 'IOS26Probe')])
        assert 'platform IOSSIMULATOR' in output and 'minos 26.0' in output
        with tarfile.open(out / 'generated-app.tar.gz', 'w:gz') as archive:
            archive.add(app, arcname=app.name)
        preserved = ['Package.swift', 'mixer.yml', 'mixer.lock', 'Platforms/iOS/IOS26Probe.xcodeproj/project.pbxproj', 'Platforms/iOS/IOS26ProbeApp.swift']
        for name in preserved:
            dest = out / 'generated' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((project / name).read_bytes())
        assert all(sha(ROOT / name) == digest for name, digest in source.items()), 'source changed'
        receipt.update(status='passed-ios26-deployment-build-baseline', packages=9,
                       sourceUnchanged=True, generatedMinimumOSVersion=info['MinimumOSVersion'],
                       cliSHA256=sha(binary), appExecutableSHA256=sha(app / 'IOS26Probe'))
    finally:
        receipt['observedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt['sourceManifestSHA256'] = sha(out / 'source-manifest.json')
        receipt['sourceArchiveSHA256'] = sha(out / 'source.tar.gz')
        receipt['commandsSHA256'] = sha(out / 'commands.json')
        receipt['artifacts'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ['artifacts']}))


if __name__ == '__main__':
    main()
