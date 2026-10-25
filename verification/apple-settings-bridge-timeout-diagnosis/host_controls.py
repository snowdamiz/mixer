"""Two bounded offline controls over exact retained source; never launches native tools."""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent
SCRATCH = BASE / 'scratch'
SWIFTC = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, limit):
    result = subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=limit, check=False)
    row = {'argv': [str(x) for x in argv], 'exitCode': result.returncode,
           'stdout': result.stdout, 'stderr': result.stderr}
    if result.returncode:
        (BASE / 'host-control-failure.json').write_text(json.dumps(row, indent=2, sort_keys=True) + '\n')
        raise RuntimeError(json.dumps(row))
    return row


def main():
    source = SCRATCH / 'DiagnosticTransport.swift'
    assert sha(source) == '7714d426ef268aeae9b7f24340e87dba269348a28e20979318df58c50aa4415c'
    control = r'''
var ample = DiagnosticTransportState()
ample.deadline = 129.0
let ampleBudget = try ample.begin(now: 100.0)
precondition(ampleBudget == 2.0)
var clipped = DiagnosticTransportState()
clipped.deadline = 939365.989950875 + 29.0
let actual = try clipped.begin(now: 939394.9777934167)
precondition(abs(actual - 0.01215745834633708) < 0.000000001)
var expired = DiagnosticTransportState()
expired.deadline = 129.0
do { _ = try expired.begin(now: 129.0); fatalError("deadline admitted") }
catch DiagnosticTransportFailure.deadline { precondition(expired.requests == 0) }
var poisoned = DiagnosticTransportState()
poisoned.deadline = 129.0
let first = poisoned.latch(.network("request timeout within existing2second budget"))
precondition(poisoned.latch(.network("later")) == first)
do { _ = try poisoned.begin(now: 101.0); fatalError("poisoned transport admitted") }
catch DiagnosticTransportFailure.priorFailure(let reason) { precondition(reason == first.description && poisoned.requests == 0) }
let result: [String: Any] = ["passedAssertions": 5, "ampleBudgetSeconds": 2.0,
    "clippedExampleSeconds": actual, "deadlineRejectedWithoutRequest": true,
    "firstFailurePreserved": true, "priorFailureRejectedWithoutRequest": true,
    "scope": "Original DiagnosticTransportState only; no URLSession, native process or device"]
print(String(data: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
'''
    program = SCRATCH / 'TransportControl.swift'
    program.write_text(source.read_text() + '\n' + control)
    binary = SCRATCH / 'transport-control'
    version = run([SWIFTC, '--version'], 10)
    compile_result = run([SWIFTC, '-target', 'arm64-apple-macosx26.0',
                          '-sdk', '/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',
                          '-module-cache-path', SCRATCH / 'module-cache', program, '-o', binary], 60)
    execute = run([binary], 10)

    disk_source = SCRATCH / 'durable_settings.py'
    assert sha(disk_source) == 'dcace8143b55c3d55e5eb89733bf79cd36e897271709b6aa0e7defe874e7ebc4'
    spec = importlib.util.spec_from_file_location('_bounded_original_durable_settings', disk_source)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    folder = SCRATCH / 'transaction-control'
    folder.mkdir()
    trace = []

    class TraceIO(original.DiskIO):
        def write(self, path, payload, role):
            trace.append(['write-fsync', role])
            return super().write(path, payload, role)

        def sync(self, path, role):
            trace.append(['directory-fsync', role])
            return super().sync(path, role)

        def publish(self, staged, final, role):
            trace.append(['hard-link', role])
            return super().publish(staged, final, role)

        def unlink(self, path, role):
            trace.append(['unlink', role])
            return super().unlink(path, role)

    store = original.TransactionStore(folder, {'syntheticHostControl': True})
    store.io = TraceIO()
    store.commit(('settings-0000', {'receivedUptime': 0, 'record': {'kind': 'synthetic-host-only'}}), [])
    assert not original.unresolved(folder)
    assert store.retirement_pending is False and store.uncertain is False
    assert sum(x[0] in ['write-fsync', 'directory-fsync'] for x in trace) == 8
    outcomes = list((folder / '.settings-attempts').glob('*/outcome.json'))
    assert len(outcomes) == 1 and json.loads(outcomes[0].read_text())['outcome'] == 'committed'
    receipt = {'schema': 1, 'python': sys.version, 'swiftToolSHA256': sha(SWIFTC),
               'originalSources': {str(source): sha(source), str(disk_source): sha(disk_source)},
               'version': version, 'compile': compile_result, 'execute': execute,
               'transport': json.loads(execute['stdout']),
               'transaction': {'scope': 'One synthetic journal commit using original TransactionStore and DiskIO; no server or runtime replay',
                               'trace': trace, 'fsyncCallsBeforeCommitReturns': 8,
                               'outcome': 'committed', 'guardAbsent': True},
               'nativeVerificationProcessesStarted': 0, 'networkListenersStarted': 0,
               'limitation': 'These are functional host controls, not latency measurements or native qualification.'}
    (BASE / 'host-controls.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'transportAssertionsPassed': 5, 'syntheticTransactionPassed': True,
                      'fsyncCallsBeforeCommitReturns': 8, 'nativeVerificationProcessesStarted': 0}))


if __name__ == '__main__':
    main()
