#!/usr/bin/env python3
"""Local signed-grants protocol qualification; no device, HTTP v2 or OTA claim."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1_048_576), b''):
            value.update(block)
    return value.hexdigest()


def source(paths):
    files = [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path)} for path in sorted(set(paths))]
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'algorithm': 'SHA256 of compact sorted JSON file path/hash array', 'sha256': digest, 'files': files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path, help='Fresh directory outside source for logs and receipt')
    parser.add_argument('--swift', required=True, type=Path, help='Actual trusted installed Swift executable (6.2 or newer)')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, GOTOOLCHAIN='go1.26.4', TOOLCHAINS='com.apple.dt.toolchain.XcodeDefault')
    environment['PATH'] = str(args.swift.resolve().parent) + os.pathsep + environment['PATH']
    receipt = {'schema': 1, 'status': 'running', 'scope': __doc__, 'pythonVersion': platform.python_version(),
               'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'commands': [], 'limitations': ['Local checkout dependencies, not immutable published consumer adoption.',
                   'Test-only signing roots and non-executable fixture payloads; never product authorities.',
                   'No service HTTP v2 acceptance, device run, native capability execution, OTA or production qualification.',
                   'Installed fingerprint/configuration composition and VM import authorization remain separate host responsibilities.']}
    dependency_paths = [ROOT/name for name in subprocess.check_output(['git', 'ls-files', 'sdk', 'updates/Sources', 'updates/Package.swift', 'updates/Package.resolved'], cwd=ROOT, text=True).splitlines()]
    receipt['testedDependencySource'] = source(dependency_paths)

    def run(name, command, cwd=ROOT, expected=0, timeout=180):
        command = [str(value) for value in command]
        log = output / (name + '.log')
        start = time.monotonic()
        timed_out = False
        with log.open('wb') as stream:
            try:
                result = subprocess.run(command, cwd=cwd, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
                code = result.returncode
            except subprocess.TimeoutExpired:
                timed_out, code = True, None
        item = {'name': name, 'command': command, 'workingDirectory': str(cwd), 'exitCode': code,
                'expectedExitCode': expected, 'timedOut': timed_out, 'elapsedSeconds': round(time.monotonic()-start, 3),
                'outputPath': str(log), 'outputBytes': log.stat().st_size, 'outputSHA256': sha(log)}
        receipt['commands'].append(item)
        print(json.dumps(item), flush=True)
        if timed_out or code != expected or log.stat().st_size > 8_388_608:
            raise RuntimeError('Command failed, timed out or exceeded output bound: ' + name)
        return log.read_text()

    try:
        swift = args.swift.absolute()
        receipt['swift'] = run('swift-version', [swift, '--version'])
        match = re.search(r'Swift version (\d+)\.(\d+)(?:\.(\d+))?(?=\s|$)', receipt['swift'])
        if not match or tuple(int(n or 0) for n in match.groups()) < (6, 2, 0):
            raise RuntimeError('Swift 6.2 or newer required')
        receipt['swiftSHA256'] = sha(swift.resolve())
        receipt['swiftFrontendSHA256'] = sha(swift.parent/'swift-frontend')
        receipt['xcode'] = run('xcode-version', ['/usr/bin/xcodebuild', '-version'])
        receipt['go'] = run('go-version', ['go', 'version'], ROOT/'services')
        goroot = run('go-root', ['go', 'env', 'GOROOT'], ROOT/'services').strip()
        receipt['goSHA256'] = sha(Path(goroot)/'bin/go')
        sdk = run('macos-sdk', ['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path']).strip()
        receipt['developerDirectory'] = environment.get('DEVELOPER_DIR')
        run('go-vet', ['go', 'vet', './protocol'], ROOT/'services')
        go_tests = run('go-race', ['go', 'test', '-count=1', '-race', '-json', './protocol'], ROOT/'services')
        events = [json.loads(line) for line in go_tests.splitlines() if line.startswith('{')]
        receipt['goTests'] = {'passedExecutions': sum(event.get('Action') == 'pass' and 'Test' in event for event in events),
                              'failed': sum(event.get('Action') == 'fail' for event in events), 'skipped': sum(event.get('Action') == 'skip' for event in events)}
        run('go-v2-fuzz', ['go', 'test', './protocol', '-run', '^$', '-fuzz', '^FuzzV2SignedManifestTransport$', '-fuzztime=15s', '-parallel=2'], ROOT/'services', timeout=60)
        for configuration in ['debug', 'release']:
            result = run('swift-updates-'+configuration, [swift, 'test', '--package-path', 'updates', '-c', configuration], timeout=600)
            summary = re.findall(r'Test run with (\d+) tests[^\n]*', result)
            if not summary:
                raise RuntimeError('Swift test summary absent')
            functions = int(summary[-1])
            parameter_cases = [int(value) for value in re.findall(r'with (\d+) test cases passed', result)]
            receipt['swiftUpdates'+configuration.title()] = {'passedFunctions': functions, 'passedExecutions': functions + sum(value-1 for value in parameter_cases)}
        reproduction = output/'fixture-reproduction'
        (reproduction/'contracts').mkdir(parents=True)
        shutil.copy2(ROOT/'contracts/release-v2.json', reproduction/'contracts/release-v2.json')
        for relative in ['services/protocol/testdata', 'updates/Tests/MixerUpdatesTests/Fixtures']:
            (reproduction/relative).mkdir(parents=True)
        run('fixture-generator', ['go', 'run', './protocol/testdata/generate-v2.go', '--test-fixtures-only', '--repository', reproduction], ROOT/'services')
        for relative in ['services/protocol/testdata', 'updates/Tests/MixerUpdatesTests/Fixtures']:
            for name in ['signed-release-v2.json', 'capability-grant-cases-v1.json']:
                if (reproduction/relative/name).read_bytes() != (ROOT/relative/name).read_bytes():
                    raise RuntimeError('Fixture reproduction mismatch: '+relative+'/'+name)
        receipt['fixturesReproducedByteExactly'] = True
        package = ROOT/'services/protocol/verification/policy-consumer'
        scratch = output/'policy-build'
        result = run('public-policy-consumer', [swift, 'run', '--package-path', package, '--scratch-path', scratch,
            'grant-policy-check', ROOT/'services/protocol/testdata'], timeout=600)
        receipt['policyConsumer'] = json.loads(result.strip().splitlines()[-1])
        if receipt['policyConsumer'].get('status') != 'passed' or receipt['policyConsumer'].get('signedCases') != 115:
            raise RuntimeError('Public policy consumer evidence absent')
        binpath = Path(run('consumer-bin-path', [swift, 'build', '--package-path', package, '--scratch-path', scratch, '--show-bin-path']).strip())
        command = [swift.with_name('swiftc'), '-typecheck', ROOT/'services/protocol/verification/authority-constructor-negative.swift',
                   '-target', binpath.parent.name+'14.0', '-sdk', sdk, '-I', binpath/'Modules']
        for module in sorted(binpath.glob('*.build/module.modulemap')):
            command += ['-Xcc', '-fmodule-map-file='+str(module)]
        negative = run('external-constructor-negative', command, expected=1)
        for name in ['VerifiedCapabilityGrant', 'VerifiedCapabilityGrants', 'VerifiedArtifact']:
            if "'"+name+"' initializer is inaccessible" not in negative:
                raise RuntimeError('Expected inaccessible constructor diagnostic absent: '+name)
        if 'missing required module' in negative or 'unable to load standard library' in negative:
            raise RuntimeError('Unrelated compile failure cannot satisfy the negative check')
        receipt['externalAuthorityConstructorsDenied'] = True
        if source(dependency_paths) != receipt['testedDependencySource']:
            raise RuntimeError('Dependency source changed during qualification; rerun against a stable tree')
        receipt['status'] = 'passed-local-host-protocol-scope'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = str(error)
        raise
    finally:
        paths = [ROOT/'contracts/release-v2.json', ROOT/'updates/Sources/MixerUpdates/Verifier.swift', ROOT/'updates/Tests/MixerUpdatesTests/VerifierV2Tests.swift']
        paths += [path for path in (ROOT/'services/protocol').rglob('*') if path.is_file() and '.build' not in path.parts and path.suffix not in ['.pyc'] and path.name not in ['receipt-2026-10-22.json']]
        paths += list((ROOT/'updates/Tests/MixerUpdatesTests/Fixtures').glob('*.json'))
        receipt['ownedSource'] = source(paths)
        (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
