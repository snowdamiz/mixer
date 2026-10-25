"""Bounded host controls; compile exact derivative post, no native runtime or sockets."""
import datetime
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SWIFTC = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
CASES = ['success', 'deadline', 'request-limit', 'timeout', 'foundation-error', 'http-rejection',
         'invalid-response', 'oversized-response', 'empty-response', 'body-limit', 'configuration',
         'post-concurrency', 'metadata-redaction', 'sink-failure', 'concurrency', 'nonfinite',
         'start-identity', 'mark-identity', 'budget-controls']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def stable(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'

def main():
    attempts = BASE / 'attempts'
    attempts.mkdir(exist_ok=True)
    attempt = attempts / f'host-{len(list(attempts.glob("host-*"))) + 1}'
    attempt.mkdir()
    scratch = BASE / 'scratch'
    assert not scratch.exists(), 'Owned scratch must be absent before a run'
    scratch.mkdir()
    shutil.copyfile(BASE / 'controls/HostControls.swift', attempt / 'controls-source.swift')
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'python': sys.version, 'platform': platform.platform(), 'swiftToolSHA256': sha(SWIFTC),
               'sourceHashes': {str(p.relative_to(BASE)): sha(p) for p in sorted((BASE / 'derivative').glob('*.swift'))},
               'hostControlSourceSHA256': sha(BASE / 'controls/HostControls.swift'),
               'scope': 'Host-only exact derivative Settings POST prefix plus synthetic controls; custom URLProtocol scheme, no sockets/listeners/native runtime',
               'nativeVerificationProcessesStarted': 0, 'networkListenersStarted': 0, 'commands': []}
    def run(argv, limit):
        result = subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=limit, check=False)
        row = {'argv': [str(x) for x in argv], 'exitCode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        receipt['commands'].append(row)
        (attempt / 'receipt.json').write_text(stable(receipt))
        if result.returncode:
            raise RuntimeError(f'Command failed; retained {attempt / "receipt.json"}')
        return row
    try:
        run([SWIFTC, '--version'], 10)
        run(['/usr/bin/xcodebuild', '-version'], 10)
        run(['/usr/bin/git', '-C', ROOT, 'rev-parse', 'HEAD'], 10)
        source = (BASE / 'derivative/ToggleUITests.swift').read_text()
        prefix = source[source.index('private final class SettingsTelemetry:'):source.index('    func start()')]
        program = 'import Foundation\n' + prefix + '}\n' + (BASE / 'controls/HostControls.swift').read_text()
        main_path = scratch / 'main.swift'
        main_path.write_text(program)
        (attempt / 'host-assembly.swift').write_text(program)
        receipt['exactPostHostAssemblySHA256'] = sha(main_path)
        run([SWIFTC, '-target', 'arm64-apple-macosx26.0', '-sdk', SDK, '-module-cache-path', scratch / 'module-cache',
             BASE / 'derivative/DiagnosticTransport.swift', BASE / 'derivative/SettingsFailureDiagnostic.swift', main_path, '-o', scratch / 'host-controls'], 60)
        rows = []
        for case in CASES:
            row = run([scratch / 'host-controls', case], 10)
            assert 'SECRET' not in row['stdout'], 'Diagnostic disclosure in host stdout'
            controls = [json.loads(x.removeprefix('HOST_CONTROL ')) for x in row['stdout'].splitlines() if x.startswith('HOST_CONTROL ')]
            diagnostics = [json.loads(x.removeprefix('MIXER_SETTINGS_FIRST_FAILURE ')) for x in row['stdout'].splitlines() if x.startswith('MIXER_SETTINGS_FIRST_FAILURE ')]
            assert len(controls) == 1 and controls[0]['passed'] is True
            assert len(diagnostics) == (0 if case == 'success' else 1)
            if case in ['deadline', 'request-limit', 'body-limit', 'configuration']:
                assert controls[0]['protocolRequests'] == 0
            if case in ['success', 'timeout', 'post-concurrency', 'foundation-error', 'http-rejection', 'invalid-response', 'oversized-response', 'empty-response']:
                assert controls[0]['protocolRequests'] == 1
            if case in ['timeout', 'post-concurrency']:
                d = diagnostics[0]
                assert d['branch'] == 'semaphore-expiration' and d['taskIdentifier'] > 0 and d['requestOrdinal'] == 1
                assert 0 < d['actualAllowanceSeconds'] <= 0.025 and d['overallDeadlineClipped'] is True
                assert d['status'] is None and d['errorCode'] is None
            if case == 'foundation-error':
                assert diagnostics[0]['errorCode'] == -1001 and diagnostics[0]['branch'] == 'foundation-error'
            if case == 'http-rejection':
                assert diagnostics[0]['status'] == 503 and diagnostics[0]['branch'] == 'http-rejection'
            if case in ['invalid-response', 'oversized-response', 'empty-response']:
                assert diagnostics[0]['branch'] == 'invalid-response'
            if case == 'metadata-redaction':
                assert all(diagnostics[0][key] is None for key in ['kind', 'generation', 'sequence', 'stage', 'slot', 'chunkIndex', 'chunkCount'])
            if case == 'start-identity':
                assert diagnostics[0]['start'] is True and diagnostics[0]['sequence'] == 0 and diagnostics[0]['generation'] is None
            if case == 'mark-identity':
                assert diagnostics[0]['stage'] == 'switch-action' and diagnostics[0]['sequence'] == 118
            if case not in ['metadata-redaction', 'start-identity', 'mark-identity', 'success']:
                d = diagnostics[0]
                assert d['kind'] == 'chunk' and d['generation'] == '12345678-1234-4234-8234-1234567890ab'
                assert d['sequence'] == 221 and d['slot'] == 'settings-0195-png' and d['chunkIndex'] == 21 and d['chunkCount'] == 71
            if case == 'nonfinite':
                assert all(diagnostics[0][key] is None for key in ['beginUptime', 'endUptime', 'absoluteDeadlineUptime', 'actualAllowanceSeconds', 'overallDeadlineClipped'])
            if case == 'budget-controls':
                assert diagnostics[0]['overallDeadlineClipped'] is True
            if diagnostics:
                assert len(row['stdout'].splitlines()[0].encode()) <= 2078
            rows.append({'case': case, 'result': controls[0], 'diagnostics': diagnostics})
        receipt['controls'] = rows
        receipt['passed'] = True
        receipt['passedControls'] = len(rows)
    finally:
        shutil.rmtree(scratch)
        receipt['scratchRemoved'] = not scratch.exists()
        (attempt / 'receipt.json').write_text(stable(receipt))
        (BASE / 'cleanup.json').write_text(stable({'schema': 1, 'scratchRemoved': not scratch.exists(),
            'removedOwnedPath': str(scratch), 'nativeInstancesCreated': 0, 'nativeQueriesPerformed': 0,
            'networkListenersStarted': 0, 'otherProjectsTouched': False}))
    if receipt.get('passed'):
        (BASE / 'host-controls.json').write_text(stable(receipt))
    print(json.dumps({'passedControls': len(CASES), 'attempt': str(attempt.relative_to(ROOT)), 'nativeExecution': False}))

if __name__ == '__main__':
    main()
