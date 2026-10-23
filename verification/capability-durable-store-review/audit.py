#!/usr/bin/env python3
"""Seal final source/artifact/evidence bindings for the independent store review."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
owner_path = ROOT / 'verification/capability-durable-store/2026-10-23-candidate-2/receipt.json'
owner = load(owner_path)
assert owner['status'] == 'scoped private store/pool checks passed; independent review pending'
source = Path(owner['export'])
for name, digest in owner['source_files'].items(): assert sha(source / name) == digest, name
for name, digest in owner['owned_files'].items(): assert sha(ROOT / name) == digest, name
for name, digest in owner['baseline_files'].items():
    assert hashlib.sha256(subprocess.check_output(['git', 'show', owner['dependency_revision'] + ':' + name], cwd=ROOT)).hexdigest() == digest
manifest = owner_path.parent / 'source-manifest.sha256'
assert sha(manifest) == owner['source_manifest_sha256']
for row in owner['commands']:
    assert row['exit_code'] == row['expected_exit'], row['name']
    assert sha(ROOT / row['log']) == row['sha256'], row['log']
    if 'expected_tests' in row: assert row['observed_tests'] == [row['expected_tests']]
retained_count = 0
for mode, retained in owner['retained_products'].items():
    for name, digest in retained['files'].items():
        assert sha(Path(retained['directory']) / name) == digest, name
        retained_count += 1
artifact_count = 0
for target, artifacts in owner['artifacts'].items():
    for item in artifacts:
        assert sha(Path(item['path'])) == item['sha256'], target
        artifact_count += 1
for name, digest in owner['native_files'].items(): assert sha(Path(owner['native_copy']) / name) == digest
review_path = OWN / '2026-10-23-candidate-2/receipt.json'
review = load(review_path)
assert review['status'] == 'passed' and review['observedProbeExecutions'] == 24
assert review['sourceManifestSHA256'] == owner['source_manifest_sha256']
for row in review['commands']:
    assert row['exitCode'] == 0 and row['fragmentPresent']
    assert sha(review_path.parent / row['log']) == row['logSHA256']
product_bindings = 0
for mode, products in review['products'].items():
    for name, digest in products.items():
        assert sha(Path(name)) == digest, name
        product_bindings += 1
for item in review['binaries'].values(): assert sha(Path(item['path'])) == item['sha256']
for name, digest in review['programInputs'].items(): assert sha(ROOT / name) == digest, name
assert review['sourceUnchanged'] and review['nativeUnchanged'] and review['programsUnchanged']

negative_one = load(OWN / 'negative-concurrent-retirement/receipt.json')
negative_two = load(OWN / 'negative-ingress-tail/receipt.json')
assert negative_one['run']['exitCode'] == 1 and negative_two['run']['exitCode'] == 1
assert sha(OWN / 'negative-concurrent-retirement/RetirementProbe.swift.txt') == negative_one['probeSHA256']
assert sha(OWN / 'negative-concurrent-retirement/run.log') == negative_one['run']['logSHA256']
assert sha(OWN / 'negative-ingress-tail/base-CapabilityRecoveryStore.swift.txt') == negative_two['baseStoreSHA256']
assert sha(OWN / 'negative-ingress-tail/derived-CapabilityRecoveryStore.swift.txt') == negative_two['derivedStoreSHA256']
assert sha(OWN / 'negative-ingress-tail/test-only.patch') == negative_two['patchSHA256']
assert sha(OWN / 'negative-ingress-tail/run.log') == negative_two['run']['logSHA256']

prior = {}
for name in ['verification/capability-durable-io/final-receipt.json', 'verification/capability-durable-io-review/final-receipt.json', 'verification/release-v3-durable-spi/final-receipt.json', 'verification/release-v3-durable-spi-root-review/receipt.json']:
    prior[name] = sha(ROOT / name)
io_manifest = ROOT / 'verification/capability-durable-io/source-manifest.sha256'
io = dict(line.split('  ', 1)[::-1] for line in io_manifest.read_text().splitlines())
shared_sources = {}
for name in ['capability-activation/Sources/MixerCapabilityActivation/CapabilityDurableDirectory.swift', 'capability-activation/Sources/MixerCapabilityDurableIO/lock.c', 'capability-activation/Sources/MixerCapabilityDurableIO/include/MixerCapabilityDurableIO.h']:
    assert owner['source_files'][name] == io[name]
    shared_sources[name] = io[name]
v3 = 'updates/Sources/MixerUpdates/VerifierV3.swift'
assert owner['source_files'][v3] == load(ROOT / 'verification/release-v3-durable-spi/final-receipt.json')['production_source_sha256']
shared_sources[v3] = owner['source_files'][v3]

instrumentation = {}
work = source.parent
for mode, path in [('debug', work / 'retained-debug/products/libMixerCapabilityActivation.a'), ('release', work / 'retained-release/products/libMixerCapabilityActivation.a'), ('tsan', work / 'host/out/Products/Debug/libMixerCapabilityActivation.a')]:
    command = ['nm', str(path)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = [line.decode() for line in result.stdout.splitlines() if b'___tsan_' in line]
    assert result.returncode == 0
    if mode == 'tsan': assert lines
    instrumentation[mode] = {'path': str(path), 'sha256': sha(path), 'command': command, 'exitCode': result.returncode,
        'tsanReferenceLines': len(lines), 'nmOutputSHA256': hashlib.sha256(result.stdout).hexdigest(), 'sample': lines[:5]}

skip = {'final-receipt.json', 'evidence-manifest.sha256', 'audit.log', 'retirement-probe'}
evidence = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OWN.rglob('*')) if p.is_file() and not {'.build', '__pycache__'}.intersection(p.relative_to(OWN).parts) and p.name not in skip}
evidence_manifest = ''.join(digest + '  ' + name + '\n' for name, digest in evidence.items())
(OWN / 'evidence-manifest.sha256').write_text(evidence_manifest)
receipt = {'status': 'independent source/artifact audit and24 original probe executions passed; two reported defects fixed',
    'sealedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'auditCommand': ['python3', '-B', str(Path(__file__).relative_to(ROOT))], 'auditOutput': 'verification/capability-durable-store-review/audit.log',
    'auditPythonVersion': sys.version,
    'ownerReceipt': {'path': str(owner_path.relative_to(ROOT)), 'sha256': sha(owner_path)},
    'sourceManifestSHA256': owner['source_manifest_sha256'], 'sourceInputsVerified': len(owner['source_files']),
    'reviewedProduction': {name: digest for name, digest in owner['owned_files'].items() if '/Sources/' in name},
    'ownerCommandsVerified': len(owner['commands']), 'retainedOwnerFilesVerified': retained_count, 'ownerArtifactsVerified': artifact_count,
    'reviewReceipt': {'path': str(review_path.relative_to(ROOT)), 'sha256': sha(review_path)},
    'probeExecutions': 24, 'modes': ['debug', 'release', 'tsan'], 'reviewProductBindingsVerified': product_bindings,
    'sourceAndProductsUnchanged': True, 'nativeFiles': owner['native_files'],
    'resolvedFindings': [
        {'problem': 'Concurrent store/adapter retirement released outer slot while prior retained-owner destructor was blocked',
         'negativeReceipt': 'verification/capability-durable-store-review/negative-concurrent-retirement/receipt.json',
         'fix': 'Per-kind retiring flags join both owner releases and reject replacement during adapter destruction',
         'finalProbeCases': ['retirement-store-first', 'retirement-adapter-first', 'retirement-replacement']},
        {'problem': 'Actual actor I/O close released outer slot before owned ordinary ingress snapshot frame returned',
         'negativeReceipt': 'verification/capability-durable-store-review/negative-ingress-tail/receipt.json',
         'fix': 'Owned inner helper return plus control join of actual I/O close and ordinary/cancellation tails',
         'finalProbeCases': ['ingress-derived']}],
    'openActionableFindings': [], 'reusedEvidence': prior, 'sharedSupportingSourcesVerified': shared_sources,
    'instrumentationReferenceObservation': instrumentation,
    'evidenceFiles': evidence, 'evidenceManifestSHA256': hashlib.sha256(evidence_manifest.encode()).hexdigest(),
    'scope': 'Private durable metadata/download and outer16 foundation on frozen3bdf dependencies; no coordinator or execution authority',
    'limitations': review['limitations'] + ['Prior I/O/sealed SPI evidence reused after matching supporting source hashes; not rerun here', 'Candidate1 positives are historical; final qualification targets candidate2 closed-state clearing', 'Source review of closed state is structural/identity validation; future selected/healthy execution must independently revalidate signed evidence', 'Observer/lifecycle SPI and execution-policy composition are not qualified by this foundation review']}
(OWN / 'final-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'receiptSHA256': sha(OWN / 'final-receipt.json'), 'evidenceFiles': len(evidence), 'sourceInputs': len(owner['source_files']), 'reviewExecutions': 24}))
