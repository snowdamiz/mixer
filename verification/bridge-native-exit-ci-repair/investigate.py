#!/usr/bin/env python3
"""Isolated, retained host diagnostics for CI26943ac; never release evidence."""
from pathlib import Path
import argparse, datetime, hashlib, io, json, os, subprocess, tarfile, time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REV = "26943ac8a6d17f59cb8a8323609d9e90a0268542"
ENV = os.environ | {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer",
                    "PATH": "/opt/homebrew/opt/rustup/bin:" + os.environ['PATH']}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def manifest(source):
    return {str(p.relative_to(source)): sha(p.read_bytes()) for p in sorted(source.rglob('*'))
            if p.is_file() and not {'.build', '.swiftpm', '__pycache__'}.intersection(p.relative_to(source).parts)}

def freeze(name):
    source = OUT / name / "source"
    source.mkdir(parents=True, exist_ok=False)
    paths = ["sdk/Package.swift", "sdk/Sources", "sdk/Tests", "experimental-capability-runtime/Package.swift",
             "experimental-capability-runtime/Sources", "experimental-capability-runtime/Tests",
             "experimental-capability-runtime/verification/with-loopback.py"]
    raw = subprocess.check_output(['git', 'archive', REV, *paths], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(source, filter='data')
    return source

def run(name, command, cwd=ROOT, timeout=1200):
    start = time.monotonic()
    result = subprocess.run(command, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    log = OUT / (name + '.log'); log.parent.mkdir(parents=True, exist_ok=True); log.write_bytes(result.stdout)
    record = {'command': command, 'cwd': str(cwd), 'environment': {'DEVELOPER_DIR': ENV['DEVELOPER_DIR']},
              'exitCode': result.returncode, 'elapsedSeconds': time.monotonic()-start, 'log': str(log.relative_to(OUT)),
              'logSHA256': sha(result.stdout)}
    (OUT / (name + '.json')).write_text(json.dumps(record, indent=2)+'\n')
    print(name, result.returncode, record['elapsedSeconds'], flush=True)
    return record

parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['native', 'baseline', 'preflight', 'baseline-full', 'baseline-stress', 'candidate', 'candidate-stress', 'candidate-stress-v2']); args = parser.parse_args()
if args.action == 'native':
    for name, command in [('swift-version', ['swift', '--version']), ('xcode-version', ['xcodebuild', '-version']),
                          ('rust-version', ['rustc', '--version']), ('python-version', ['python3', '--version']), ('host-version', ['uname', '-a'])]:
        run(name, command)
    run('native-build', ['python3', str(ROOT/'experimental-capability-runtime/build-vm.py'), '--revision', REV,
        '--target', 'host', '--output', str(OUT/'native-26943ac'), '--cache', str(OUT/'.build/native-26943ac')])
    raise SystemExit()
source = freeze(args.action)
if args.action.startswith('candidate'):
    for name in ['Sources/MixerExperimentalCapabilityRuntime/Session.swift', 'Tests/MixerExperimentalCapabilityRuntimeTests/HTTPTests.swift']:
        relative = 'experimental-capability-runtime/' + name
        (source/relative).write_bytes((ROOT/relative).read_bytes())
if 'stress' in args.action:
    (source/'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/PublicationProbe.swift').write_bytes((OUT/'PublicationProbe.swift').read_bytes())
if args.action == 'preflight':
    path = source/'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/HTTPTests.swift'
    text = path.read_text()
    text = text.replace('private final class BridgeWeakSession {', '''private final class BridgePreflightClock: @unchecked Sendable {
    private let reads = Locked(0)
    private let initial = ContinuousClock.now
    func now() -> ContinuousClock.Instant {
        reads.withLock { count in count += 1; return count <= 2 ? initial : initial.advanced(by: .seconds(60)) }
    }
    var clock: HTTPTransportClock { HTTPTransportClock(now: { self.now() }, sleepUntil: { _ in try await Task.sleep(for: .seconds(60)) }) }
}
private final class BridgeWeakSession {''')
    old = 'protocolClasses: [BridgeInterceptedProtocol.self], beforeInvalidation: { gate.hold() })'
    text = text.replace(old, 'protocolClasses: [BridgeInterceptedProtocol.self], clock: BridgePreflightClock().clock, beforeInvalidation: { gate.hold() })', 1)
    text = text.replace('try await bridgeEventually { gate.entered && transport.activeRequests == 1 }', '''try await bridgeEventually { try await session!.invoke("stage").value == .i32(5) }
        print("PREFLIGHT_OBSERVATION gate=\\(gate.entered) active=\\(transport.activeRequests) exits=\\(session!.status.retainedExits)")
        #expect(!gate.entered && transport.activeRequests == 0)
        try await bridgeEventually { gate.entered && transport.activeRequests == 1 }''', 1)
    path.write_text(text)
before = manifest(source)
(OUT/args.action/'source-manifest.json').write_text(json.dumps(before, indent=2)+'\n')
stage = OUT/'native-26943ac'
modes = [('debug', []), ('release', ['-c', 'release']), ('tsan', ['--sanitize', 'thread'])] if args.action == 'candidate' else [('tsan', ['--sanitize', 'thread'])]
records = []
for mode, extra in modes:
    command = ['swift', 'test', '--package-path', str(source/'experimental-capability-runtime'), '--scratch-path', str(OUT/'.build'/args.action/mode)] + extra
    if args.action in ['candidate', 'baseline-full']:
        command = ['python3', '-B', str(source/'experimental-capability-runtime/verification/with-loopback.py'), '--output', str(OUT/args.action/(mode+'-tls')), '--'] + command
        command += ['-Xswiftc', '-DMIXER_EXPERIMENTAL_LOCAL_TLS_TEST']
    else:
        command += ['--filter', 'publicationProbe' if 'stress' in args.action else 'publicOwnerDeinitRetainsActualNativeExitAndConstructionBudget']
    command += ['-Xcc', '-I'+str(stage/'include'), '-Xlinker', '-L'+str(stage/'lib'), '-Xswiftc', '-warnings-as-errors']
    records.append(run(args.action+'/'+mode+'-filtered', command, source))
record = {'commands': records, 'sourceRevision': REV, 'sourceTree': subprocess.check_output(['git','rev-parse',REV+'^{tree}'],cwd=ROOT,text=True).strip(),
    'sourceManifestSHA256': sha(json.dumps(before,sort_keys=True).encode()), 'snapshotUnchanged': before==manifest(source),
    'scope': 'Local host diagnostics, different toolchain from hosted CI; archive is not Swift TSan instrumented; no devices/release/GA claim'}
(OUT/args.action/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
