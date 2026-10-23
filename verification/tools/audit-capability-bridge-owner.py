#!/usr/bin/env python3
"""Audit the implementer's frozen Swift bridge matrix; not independent test approval."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'experimental-capability-runtime/verification/2026-10-23-candidate-5'
PIN = 'b25e3b7de2391a80d12e7fd75e60903495bec120'
OWNER_SHA = '6194e77ab6119f2d91d18f0a374a04fc99bd018019ae9c1e1a81e6e3e02fd07e'


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    require(sha(BASE / 'receipt.json') == OWNER_SHA, 'owner receipt changed')
    owner = json.loads((BASE / 'receipt.json').read_text())
    require(owner['status'] == 'scoped_checks_passed', 'owner matrix incomplete')
    require(all(owner[k] for k in ('sourceUnchangedDuringRun', 'exportUnchangedDuringRun', 'nativeArtifactsUnchangedDuringRun')), 'matrix drift')
    require(owner['nativeRevision'] == PIN, 'native pin')
    manifest = BASE / 'source-manifest.sha256'
    require(sha(manifest) == owner['sourceManifestSHA256'], 'manifest hash')
    source = dict((path, digest) for digest, path in (line.split('  ', 1) for line in manifest.read_text().splitlines()))
    require(source == owner['source'] and len(source) == 55, 'source inventory')
    export = Path(owner['frozenSourceExport'])
    sdk_inputs = 0
    for path, digest in source.items():
        require(sha(ROOT / path) == digest == sha(export / path), 'source bytes: ' + path)
        if path.startswith('sdk/'):
            committed = subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=ROOT)
            require(hashlib.sha256(committed).hexdigest() == digest, 'SDK prerequisite drift: ' + path)
            sdk_inputs += 1
    stage = Path(owner['stageRoot'])
    archives = {}
    for target, files in owner['nativeArtifacts'].items():
        for name, digest in files.items():
            require(sha(stage / name) == digest, 'native stage bytes: ' + name)
        builder = json.loads((stage / target / 'receipt.json').read_text())
        require(builder['source_revision'] == PIN, 'archive source pin')
        require(builder['feature'] == 'experimental-capability-native', 'archive feature')
        require(builder['source_manifest_sha256'] == '47ecc06679f61be0da8a53839830be72876889bb90c9a8e5834c8661f9312aa6', 'archive source manifest')
        archives[target] = builder['library']['sha256']
    require(set(archives) == {'host', 'ios', 'ios-simulator', 'android'}, 'target inventory')
    tests = {}
    measurements = []
    for command in owner['commands']:
        require(command['exitCode'] == 0, 'command failed: ' + command['name'])
        path = BASE / command['log']
        require(sha(path) == command['logSHA256'], 'command log: ' + command['name'])
        text = path.read_text()
        if command['name'].startswith('bridge-') or command['name'] == 'measurement-filtered':
            counts = [int(n) for n in re.findall(r'Test run with (\d+) tests? in \d+ suites? passed', text)]
            expected = 1 if command['name'] == 'measurement-filtered' else 16
            require(counts == [expected] == command['passedTests'], 'test count: ' + command['name'])
            require('WARNING: ThreadSanitizer' not in text, 'sanitizer diagnostic')
            tests[command['name']] = expected
            if expected == 16:
                require('realWasmNormalTrustRejectsActualLoopbackTLSCertificate' in text, 'TLS case absent')
            records = [json.loads(line) for line in re.findall(r'BRIDGE_MEASUREMENT (.+)', text)]
            require(records == command.get('measurements'), 'measurement parse')
            measurements.append({'command': command['name'], 'observations': records})
    require(len(owner['commands']) == 18, 'command count')
    tls = {}
    for mode in ('debug', 'release', 'tsan'):
        folder = BASE / (mode + '-loopback')
        record = json.loads((folder / 'receipt.json').read_text())
        require(record['exit_code'] == 0 and record['server_stopped'], 'TLS child outcome')
        require(sha(folder / 'command.log') == record['output_sha256'], 'TLS command log')
        observations = record['observations']
        require(observations['tcp_accepts'] >= 1 and observations['tls_failures'] >= 1 and observations['application_requests'] == 0, 'TLS failure observation')
        tls[mode] = {'receipt_sha256': sha(folder / 'receipt.json'), 'observations': observations}
    binaries = {}
    for target, entry in owner['linkedConsumers'].items():
        path = Path(entry['path'])
        require(sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'], 'linked consumer: ' + target)
        binaries[target] = {'sha256': entry['sha256'], 'bytes': entry['bytes'], 'scope': 'Public API empty-module rejection executed' if target == 'host' else 'Compile and link only'}
    require('Expected empty-module rejection: malformed' in (BASE / 'public-host-run.log').read_text(), 'public host consumer outcome')
    report = {
        'schema': 1, 'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'audit_script_sha256': sha(Path(__file__)), 'implementation_receipt_sha256': OWNER_SHA,
        'source_manifest_sha256': owner['sourceManifestSHA256'],
        'matched': {'source_inputs': 55, 'SDK_inputs_unchanged_from_native_pin': sdk_inputs,
                    'command_logs': 18, 'native_archive_sha256': archives, 'linked_consumers': binaries},
        'test_counts': tests, 'normal_trust_TLS_rejection': tls,
        'observational_measurements': measurements,
        'result': 'Implementer frozen source, SDK prerequisite, native archives, logs, test counts and linked-consumer bytes matched.',
        'qualification': 'Implementation evidence audit only; independent public/derived review and active-payload observation are separate prerequisites.',
        'limitations': owner['limitations']}
    output = ROOT / 'verification/capability-bridge-owner-audit-2026-10-23.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'matched': report['matched'], 'test_counts': tests}, indent=2))


if __name__ == '__main__':
    main()
