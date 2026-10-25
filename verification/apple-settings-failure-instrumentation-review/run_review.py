"""Focused independent offline/host review; writes only this review directory."""
import datetime
import difflib
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / 'verification/apple-settings-failure-instrumentation'
EXPECTED = 'd637e80716b9407028f059dd44673e09cd74f536d7bec2909fa02a0da5b40190'
SWIFTC = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def binding(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha(data)}

def write(name, value):
    (BASE / name).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')

def main():
    handoff = PACKET / 'handoff.json'
    assert sha(handoff.read_bytes()) == EXPECTED
    packet = json.loads(handoff.read_text())
    inputs = {name: binding(ROOT / name) for name in packet['members']}
    assert inputs == packet['members']
    inputs[str(handoff.relative_to(ROOT))] = binding(handoff)
    acceptance = 'verification/apple-settings-bridge-timeout-root-review/acceptance.json'
    inputs[acceptance] = binding(ROOT / acceptance)
    write('inputs.json', {'schema': 1, 'expectedHandoffSHA256': EXPECTED, 'files': inputs,
        'sourceRevisionContextOnly': json.loads((PACKET / 'provenance.json').read_text())['sourceRevision'],
        'derivativeSourceTreeSHA256': packet['derivativeSourceTreeSHA256']})
    scratch = BASE / 'scratch'
    assert not scratch.exists()
    scratch.mkdir()
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python': sys.version, 'platform': platform.platform(), 'scope': 'Frozen packet verification and five focused independent host groups; no native execution or queries',
        'swiftTool': {'path': str(SWIFTC), **binding(SWIFTC)}, 'sdk': {'path': str(SDK), 'settings': binding(SDK / 'SDKSettings.json')},
        'reviewSource': binding(BASE / 'IndependentControls.swift'), 'runnerSource': binding(BASE / 'run_review.py'),
        'commands': [], 'controls': [], 'assemblies': {}}

    def run(argv, timeout=60):
        result = subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=timeout)
        row = {'argv': [str(x) for x in argv], 'exitCode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        receipt['commands'].append(row)
        write('host-receipt.json', receipt)
        assert result.returncode == 0, row
        return row

    try:
        verified = run([sys.executable, PACKET / 'verify.py', '--expected-handoff-sha256', EXPECTED], 30)
        receipt['packetVerification'] = json.loads(verified['stdout'])
        run([SWIFTC, '--version'], 10)
        controls = (BASE / 'IndependentControls.swift').read_text()
        for variant in ['original', 'derivative']:
            source = (PACKET / variant / 'ToggleUITests.swift').read_text()
            prefix = source[source.index('private final class SettingsTelemetry:'):source.index('    func start()')]
            assembly = 'import Foundation\n' + prefix + '}\n' + controls
            folder = scratch / variant
            folder.mkdir()
            path = folder / 'main.swift'
            path.write_text(assembly)
            receipt['assemblies'][variant] = binding(path)
            argv = [SWIFTC, '-target', 'arm64-apple-macosx26.0', '-sdk', SDK, '-module-cache-path', scratch / 'module-cache']
            if variant == 'derivative':
                argv += ['-D', 'INSTRUMENTED', PACKET / variant / 'SettingsFailureDiagnostic.swift']
            argv += [PACKET / variant / 'DiagnosticTransport.swift', path, '-o', folder / 'controls']
            run(argv)
            cases = ['completed-callback', 'clipped-timeout'] + (['identity-boundaries', 'sink-failure-before-output', 'reentrant-sink'] if variant == 'derivative' else [])
            for case in cases:
                row = run([folder / 'controls', case], 10)
                assert 'REVIEW_SECRET' not in row['stdout']
                reports = [json.loads(x.removeprefix('REVIEW_CONTROL ')) for x in row['stdout'].splitlines() if x.startswith('REVIEW_CONTROL ')]
                diagnostics = [json.loads(x.removeprefix('MIXER_SETTINGS_FIRST_FAILURE ')) for x in row['stdout'].splitlines() if x.startswith('MIXER_SETTINGS_FIRST_FAILURE ')]
                assert len(reports) == 1 and reports[0]['passed']
                assert len(diagnostics) == int(variant == 'derivative' and case == 'clipped-timeout')
                if diagnostics:
                    d = diagnostics[0]
                    assert d['branch'] == 'semaphore-expiration' and d['requestOrdinal'] == 10 and d['sequence'] == 9
                    assert 0 < d['actualAllowanceSeconds'] <= 0.02 and d['overallDeadlineClipped'] is True
                    assert d['status'] is None and d['errorCode'] is None and d['taskIdentifier'] > 0
                    assert d['slot'] == 'settings-2500-png' and d['chunkIndex'] == 651 and d['chunkCount'] == 652
                receipt['controls'].append({'variant': variant, 'case': case, 'result': reports[0], 'diagnostics': diagnostics})
        old = (PACKET / 'original/ToggleUITests.swift').read_text()
        new = (PACKET / 'derivative/ToggleUITests.swift').read_text()
        assert old[old.index('    func start()'):] == new[new.index('    func start()'):]
        assert (PACKET / 'original/DiagnosticTransport.swift').read_bytes() == (PACKET / 'derivative/DiagnosticTransport.swift').read_bytes()
        receipt['passed'] = True
        receipt['focusedGroups'] = 5
        receipt['executions'] = 7
    finally:
        shutil.rmtree(scratch)
        write('cleanup.json', {'schema': 1, 'removedOwnedPath': str(scratch), 'scratchAbsent': not scratch.exists(),
            'nativeQueriesPerformed': 0, 'nativeRuntimeProcessesStarted': 0, 'networkListenersStarted': 0,
            'nativeInstancesCreated': 0, 'otherProjectsTouched': False, 'producerPacketUnchanged': all(binding(ROOT / name) == value for name, value in inputs.items())})
        receipt['scratchAbsent'] = not scratch.exists()
        write('host-receipt.json', receipt)
    print(json.dumps({'passed': receipt['passed'], 'focusedGroups': 5, 'executions': 7, 'scratchAbsent': receipt['scratchAbsent']}))

if __name__ == '__main__':
    main()
