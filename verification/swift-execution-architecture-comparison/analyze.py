#!/usr/bin/env python3
"""Read-only source/evidence comparison. Never compiles or executes a guest.

The only writes are findings.json in this owned directory. Source text checks
bind an architecture discussion, never validation/release authority.
"""
import hashlib
import json
from pathlib import Path
import platform
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V1 = ROOT / "verification/swift-cache-capacity-campaign-v1"
R1 = ROOT / "verification/github-delivery-blocker-campaign/cache-campaign-review"
R2 = ROOT / "verification/github-delivery-binary-export-and-ui/cache-deadline-review"
QUALIFIED = ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/receipt.json"
EXPECTED = {
    R1 / "seal.json": "4dcf3f8bf9533d0234a5966d111b1d3373299cbfb816ab871d0764c0a1024cec",
    R2 / "seal.json": "c6bde1201697149bfa84d2f31b112d14d8c1e35ac005fc908a16433941f23df8",
    V1 / "inputs/source.tar.gz": "cdbf6b5826a354fa7796d3f4e4573b2fe62a213e4f3f5adf944cc2d2e44fbf18",
    V1 / "inputs/harness.rs": "8c7730239b38250671f7dc23cc46859ffd5b4b9253f1eabaf34f161c061ec078",
    V1 / "inputs/native-observation.json": "bcced25887996c717597a91dd0f6d48fbdf6277ca0c46bb12bfb0b049aa96e2c",
}


def identity(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_text())


def require(value, message):
    if not value:
        raise ValueError(message)


def one_event(result, name):
    matches = [x["payload"] for x in result["events"] if x["event"] == name]
    require(len(matches) == 1, "missing or duplicate event " + name)
    return matches[0]


bindings = []
for path, expected in EXPECTED.items():
    item = identity(path)
    require(item["sha256"] == expected, "changed binding " + str(path))
    bindings.append(item)

members = ["Cargo.toml", "src/experimental/policy.rs", "src/experimental/metadata.rs", "src/experimental/cache/borrowed.rs",
           "src/experimental_swift_reactor/cache.rs", "src/experimental_swift_reactor/cache_tests.rs",
           "src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/call_dispatch.rs",
           "src/experimental_swift_reactor/frame_operations.rs"]
sources = {}
with tarfile.open(V1 / "inputs/source.tar.gz", "r:gz") as archive:
    for name in members:
        member = archive.getmember(name)
        # The sealed dispatcher includes a large explicit lifetime inventory.
        require(member.isfile() and member.size < 16 * 1024 * 1024, "unexpected source member")
        payload = archive.extractfile(member).read()
        sources[name] = payload.decode()
        bindings.append({"archive": "verification/swift-cache-capacity-campaign-v1/inputs/source.tar.gz",
                         "member": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})

require('overflow-checks = true' in sources['Cargo.toml'], 'overflow policy changed')
require('Self::SwiftReactorExperimentV1 => 80_000' in sources['src/experimental/policy.rs'], 'function ceiling changed')
require('s.count(policy.functions().saturating_sub(m.imports.len()), meter)?' in sources['src/experimental/metadata.rs'], 'absolute function index bound changed')
control = sources['src/experimental_swift_reactor/control.rs']
require('self.charge_fuel_with_wasi(1, cursor, wasi)?;' in control, 'instruction metering changed')
require('if Instant::now() >= self.deadline' in control, 'deadline check changed')
require('let now = Instant::now();' in control, 'usage snapshot clock changed')
require('CURRENT_ATTRIBUTION.with(|x| x.borrow_mut().work(n,c,e))' in sources['src/experimental_swift_reactor/cache_tests.rs'], 'observer path changed')

profiles = []
for name in ('deadline-60-work-64m', 'deadline-60-work-128m'):
    base = R2 / 'artifact' / name
    result = read(base / 'result.json')
    build = read(base / 'build/receipt.json')
    require('--release' in build['argv'] and build['exitCode'] == 0, 'unoptimized or failed build')
    require('RUSTFLAGS' not in build['environment'], 'unreviewed compiler flag override')
    require(not result['complete'] and not result['hostFeasibility'], 'campaign status changed')
    require('corpus_2' not in result['phaseOrder'], 'unexpected corpus 2')
    require(result['telemetry']['status'] == 'valid', 'attribution invalid')
    failure = result['firstFailure']['payload']
    totals = result['telemetry']['snapshots'][-1]['payload']
    require(sum(totals['credits']) == failure['at_failure']['cache_work'], 'credit sum mismatch')
    cleanup = one_event(result, 'final_cleanup_usage')
    require(cleanup['cleanup_invariant'] is None, 'cleanup invariant')
    require(cleanup['reservations']['live_tickets'] == 0, 'live tickets')
    require(all(v['current'] == 0 for v in cleanup['reservations'].values() if isinstance(v, dict)), 'live reservation')
    require(all(v['current'] == 0 for v in cleanup['live'].values()), 'live resource')
    usage = failure['at_failure']
    chain, pins = totals['credits'][3], totals['credits'][2]
    profiles.append({
        'name': name, 'firstResource': failure['resource'], 'attempted': failure['attempted'], 'limit': failure['limit'],
        'elapsedMicros': usage['elapsed_micros'], 'guestInstructions': usage['instructions'],
        'instructionFuel': usage['instruction_fuel'], 'bulkFuelDifference': usage['instruction_fuel'] - usage['instructions'],
        'executionWork': usage['execution_work'], 'cacheWork': usage['cache_work'],
        'residentChainCredits': chain, 'freePinSearchCredits': pins,
        'chainAndPinFractionOfCacheCredits': (chain + pins) / usage['cache_work'],
        'cacheWorkCalls': sum(totals['calls']), 'completedDecodes': totals['completed'],
        'distinctDecodes': totals['distinct'], 'repeatedDecodes': totals['repeated'],
        'complete': False, 'finalLogicalResourcesEmpty': True,
        'hostReleaseBuild': True, 'overflowChecks': True,
        'cpuAttributionUnavailable': True, 'vmAttributableRSSUnavailable': True,
    })
    bindings.extend(identity(base / p) for p in ('result.json', 'build/receipt.json', 'full/receipt.json'))

qualified = read(QUALIFIED)
guest_builds = [x for x in qualified['commands'] if x['name'] in ('wasm-model-compile', 'wasm-reactor-build')]
require(len(guest_builds) == 2, 'guest build evidence missing')
for command in guest_builds:
    require(command['exitCode'] == 0 and all(x in command['command'] for x in ('-Osize', '-gnone', '-whole-module-optimization')), 'guest optimization evidence changed')
guest = qualified['candidateArtifactsBeforeOracle']['reactor']
require(guest['bytes'] == 53_777_114 and guest['sha256'] == '24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994', 'guest artifact differs')
oracle = read(V1 / 'inputs/native-observation.json')
require(len(oracle) == 11, 'oracle narrowed')
bindings.append(identity(QUALIFIED))

findings = {
    'schema': 1,
    'scope': 'Offline architecture comparison and candidate source preparation; no compiler, guest, native, process-custody or CI execution',
    'reviewer': {'model': 'gpt-6-astra', 'reasoning': 'xhigh', 'freshContext': True},
    'observedRepositoryRevision': '56ff14c925168284761c5aca4f0bd4129cf3c995',
    'command': 'python3 -B verification/swift-execution-architecture-comparison/analyze.py',
    'toolVersion': {'python': platform.python_version(), 'implementation': platform.python_implementation()},
    'bindings': bindings,
    'profiles': profiles,
    'guestOptimization': ['-Osize', '-gnone', '-whole-module-optimization'],
    'guest': {'bytes': guest['bytes'], 'sha256': guest['sha256']},
    'nativeOracle': oracle,
    'denseIndexPayload': {'key': 'absolute validated function ID; imports rejected before cache lookup',
                          'actualDefinedFunctions': 79_832, 'actualImportedFunctions': 34,
                          'maximumImportsPlusDefinedFunctions': 80_000, 'allocatedMapBytes': 160_000,
                          'freePinBitmapBytes': 8, 'overheadsStillRequireActualCandidateEnvelope': True},
    'candidateSelection': 'Root selected guarded dense resident map and pin bitmap plus shared finite whole-owner profile; source prepared, runtime dispatch unselected',
    'candidateImplemented': True,
    'candidateCompiled': False,
    'runtimeAttemptsThisReview': 0,
    'requiredMilestonePassed': False,
    'claims': ['Release build is already optimized',
               'Cache optimizations cannot eliminate original guest fuel demand',
               'Attribution credits are not CPU sample shares',
               'Instrumentation overhead is visible in source but its elapsed-time contribution is not measured'],
}
(HERE / 'findings.json').write_text(json.dumps(findings, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': 'offline bindings and derivations verified', 'profiles': len(profiles),
                  'sourceMembers': len(members), 'oracleFields': len(oracle),
                  'candidateSourcePrepared': True, 'candidateCompiled': False, 'runtimeAttempts': 0}, sort_keys=True))
