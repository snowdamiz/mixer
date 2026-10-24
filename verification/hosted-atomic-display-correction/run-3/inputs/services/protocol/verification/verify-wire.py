#!/usr/bin/env python3
"""Local strict-v1 wire and v2 regression; no device, real-DB or hosted qualification."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source():
    files = []
    for name in ['services', 'updates', 'sdk', 'cli', 'capabilities']:
        files += [path for path in (ROOT/name).rglob('*') if path.is_file()
                  and not any(part in {'.build', '__pycache__', '.git'} for part in path.relative_to(ROOT).parts)
                  and path.suffix not in {'.pyc', '.log'}
                  and not ('verification' in path.parts and 'receipt' in path.name)]
    files += [ROOT/'contracts/release-v1.json', ROOT/'contracts/release-v2.json']
    rows = [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path)} for path in sorted(set(files))]
    return {'algorithm': 'SHA256 of compact sorted JSON file path/hash array',
            'sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'files': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swift', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, GOTOOLCHAIN='go1.26.4', TOOLCHAINS='com.apple.dt.toolchain.XcodeDefault')
    environment['PATH'] = str(args.swift.resolve().parent) + os.pathsep + environment['PATH']
    receipt = {'schema': 1, 'status': 'running', 'scope': __doc__,
               'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'testedSource': source(), 'commands': [],
               'limitations': ['Host-only local checkout dependencies, not immutable published consumer adoption.',
                   'Real PostgreSQL integration is excluded because this run does not select the postgres_integration build tag; no real-DB pass is claimed.',
                   'No physical devices, native imports, HTTP v2 delivery, OTA policy or production qualification.',
                   'Strict transport shape is not signature, scope, compatibility or execution authorization.']}

    def run(name, command, cwd=ROOT, timeout=180):
        command = [str(value) for value in command]
        log = output/(name+'.log')
        start = time.monotonic()
        timed_out = False
        with log.open('wb') as stream:
            try:
                result = subprocess.run(command, cwd=cwd, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
                code = result.returncode
            except subprocess.TimeoutExpired:
                timed_out, code = True, None
        item = {'name': name, 'command': command, 'workingDirectory': str(cwd), 'exitCode': code,
                'timedOut': timed_out, 'elapsedSeconds': round(time.monotonic()-start, 3),
                'outputPath': str(log), 'outputBytes': log.stat().st_size, 'outputSHA256': sha(log)}
        receipt['commands'].append(item)
        print(json.dumps(item), flush=True)
        if timed_out or code != 0 or log.stat().st_size > 8_388_608:
            raise RuntimeError('Command failed, timed out or exceeded output bound: '+name)
        return log.read_text()

    try:
        nested = output/'v2-regression'
        run('v2-existing-qualification', [sys.executable, ROOT/'services/protocol/verification/verify-v2.py',
            '--swift', args.swift, '--output-dir', nested], timeout=900)
        v2 = json.loads((nested/'receipt.json').read_text())
        if v2.get('status') != 'passed-local-host-protocol-scope':
            raise RuntimeError('Existing protocol qualification did not pass')
        receipt['v2Regression'] = {'receiptPath': str(nested/'receipt.json'), 'receiptSHA256': sha(nested/'receipt.json'),
            **{name: v2[name] for name in ['swift', 'swiftSHA256', 'swiftFrontendSHA256', 'xcode', 'go', 'goSHA256',
                'developerDirectory', 'goTests', 'swiftUpdatesDebug', 'swiftUpdatesRelease', 'fixturesReproducedByteExactly',
                'policyConsumer', 'externalAuthorityConstructorsDenied']}}
        run('services-vet', ['go', 'vet', './...'], ROOT/'services')
        result = run('services-race', ['go', 'test', '-count=1', '-race', '-json', './...'], ROOT/'services', timeout=300)
        events = [json.loads(line) for line in result.splitlines() if line.startswith('{')]
        receipt['servicesTests'] = {
            'passedExecutions': sum(event.get('Action') == 'pass' and 'Test' in event for event in events),
            'failed': [event for event in events if event.get('Action') == 'fail'],
            'skippedTests': [{'package': event['Package'], 'test': event['Test']}
                            for event in events if event.get('Action') == 'skip' and event.get('Test')],
            'packagesWithoutTests': [event['Package'] for event in events if event.get('Action') == 'skip' and not event.get('Test')],
            'packagePasses': [event['Package'] for event in events if event.get('Action') == 'pass' and 'Test' not in event]}
        if receipt['servicesTests']['failed']:
            raise RuntimeError('Go service regression failure')
        run('legacy-wire-fuzz', ['go', 'test', './protocol', '-run', '^$', '-fuzz', '^FuzzLegacySignedWireNeverPanics$',
            '-fuzztime=15s', '-parallel=2'], ROOT/'services', timeout=60)
        result = run('cli-regression', [args.swift, 'test', '--package-path', 'cli'], timeout=600)
        summary = re.findall(r'Test run with (\d+) tests[^\n]*', result)
        if not summary:
            raise RuntimeError('CLI summary absent')
        receipt['cliTests'] = {'passedFunctions': int(summary[-1])}
        reproduction = output/'wire-fixture-reproduction'
        relative_paths = ['services/protocol/testdata', 'updates/Tests/MixerUpdatesTests/Fixtures']
        for relative in relative_paths:
            (reproduction/relative).mkdir(parents=True)
        run('wire-fixture-generator', ['go', 'run', './protocol/testdata/generate-v1-wire.go', '--test-fixtures-only',
            '--repository', reproduction], ROOT/'services')
        fixture_name = 'legacy-v1-wire-cases.json'
        for relative in relative_paths:
            if (reproduction/relative/fixture_name).read_bytes() != (ROOT/relative/fixture_name).read_bytes():
                raise RuntimeError('Wire fixture reproduction mismatch: '+relative)
        corpus = json.loads((ROOT/relative_paths[0]/fixture_name).read_text())
        receipt['legacyWireCorpus'] = {'documents': len(corpus['documents']),
            'accepted': sum(item['accepted'] for item in corpus['documents']),
            'rejected': sum(not item['accepted'] for item in corpus['documents']),
            'bothGoEntryPoints': ['protocol.DecodeJSON', 'encoding/json.Unmarshal'],
            'swiftEntryPoints': ['ReleaseVerifier.verifyArtifact', 'ReleaseVerifier.verifyAssignment', 'StrictJSON.decode for host/root'],
            'byteExactReproduction': True, 'artifactSHA256': corpus['artifact_sha256']}
        immutable = ['services/protocol/testdata/signed-release-v1.json', 'services/protocol/testdata/signed-release-v2.json',
                     'services/protocol/testdata/capability-grant-cases-v1.json']
        receipt['preservedPriorFixtures'] = []
        for relative in immutable:
            prior = subprocess.check_output(['git', 'show', '3aade1f3c61acc78e399b0c2c6ee36d73c1bf11f:'+relative], cwd=ROOT)
            if prior != (ROOT/relative).read_bytes():
                raise RuntimeError('Previously signed fixture changed: '+relative)
            receipt['preservedPriorFixtures'].append({'path': relative, 'sha256': sha(ROOT/relative)})
        if source() != receipt['testedSource']:
            raise RuntimeError('Tested source changed during qualification; rerun against stable source')
        receipt['status'] = 'passed-local-host-wire-parity'
    except Exception as error:
        receipt['status'], receipt['failure'] = 'failed', str(error)
        raise
    finally:
        (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
