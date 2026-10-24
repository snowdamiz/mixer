"""Root acceptance of bounded constructor code and corrected host evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = ROOT / 'verification/swift-executor-construction/candidate-4'
I = ROOT / 'verification/swift-executor-construction-independent-review'
S = I / 'supplemental-product-artifacts'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
bindings = {}

def bind(path, digest=None):
    path = path if path.is_absolute() else ROOT / path
    actual = sha(path)
    if digest is not None:
        assert actual == digest, str(path)
    bindings[str(path.relative_to(ROOT))] = actual

producer = read(P / 'receipt.json')
manifest = read(P / 'source-manifest.json')
for rel, digest in manifest.items():
    bind(ROOT / 'vm' / rel, digest)
bind(P / producer['archive']['path'], producer['archive']['sha256'])
for command in producer['commands']:
    bind(Path(command['log']), command['sha256'])
for rel, digest in producer['artifact_hashes'].items():
    bind(P / rel, digest)
for entry in read(I / 'seal.json')['files']:
    bind(I / entry['path'], entry['sha256'])
verified = subprocess.run(['python3', str(S / 'verify.py')], cwd=ROOT,
                          capture_output=True, text=True, check=True)
(HERE / 'independent-seal-verification.log').write_text(verified.stdout)
decision = read(S / 'decision.json')
assert decision['status'] == 'PASS_SUPERSEDING_SCOPED_RECOMMENDATION_TO_ROOT'
replacement = decision['replacement_product_regression']
bind(Path(replacement['receipt']), replacement['receipt_sha256'])
clean = read(ROOT / replacement['receipt'])
assert clean['status'] == 'passed-uninstrumented-full-host-regression'
assert clean['sourceTreeSHA256'] == producer['source_tree_digest']
for c in clean['commands']:
    assert c['exit'] == 0 and c['sourceBeforeAfterVerified']
    bind(Path(c['log']), c['sha256'])
for profile, counts in clean['counts'].items():
    assert counts == dict(passed=366, failed=0, ignored=9, suites=35,
                          uninstrumentedLibraryPassed=151)
    binary = clean['unitBinaries'][profile]
    assert sha(Path(binary['path'])) == binary['sha256']
    listing = (HERE / 'candidate4-clean' / ('unit-list-' + profile + '.log')).read_text()
    assert 'frozen_construction_metadata' not in listing
original = read(I / 'decision.json')
assert original['typed_classes'] == 615 and original['typed_positions'] == 5004
assert original['unresolved_accounting_roles'] == []
bind(ROOT / 'vm/src/experimental_swift_reactor/execution.rs', original['final_execution_sha256'])
bind(ROOT / 'docs/swift-executor-construction.md', original['final_document_sha256'])
directories = [
    'verification/swift-cache-owner-preflight',
    'verification/swift-executor-construction',
    'verification/swift-executor-construction-independent-review',
    'verification/swift-executor-construction-root-review',
]
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others',
                                '--exclude-standard', '--', *directories],
                               cwd=ROOT, text=True).splitlines()
for rel in paths:
    if rel == str((HERE / 'acceptance.json').relative_to(ROOT)):
        continue
    assert '/build/' not in rel and '__pycache__' not in rel
    bind(Path(rel))
result = dict(
    schema=1, status='accepted-private-uninitialized-construction-and-zero-frame-cleanup',
    reviewer='root', observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=producer['revision'], sourceTreeSHA256=producer['source_tree_digest'],
    scope='Retained-descriptor fixed State initialization, original control/cache/WASI composition, deferred error-return authority and zero-frame consuming cleanup. No interpreter or Ready reactor.',
    typedClasses=615, namedTypedPositions=5004, unitHookPositions=15,
    productionBounds=original['bounds']['production'],
    unitBounds=original['bounds']['unit'],
    independentDerivedLibraryProbeExecutions=434, independentLayoutConfigurations=8,
    cleanProductTestsPerMode=clean['counts'],
    supersedingIndependentDecision=str((S / 'decision.json').relative_to(ROOT)),
    historicalEvidence=['Candidate1 accounting findings retained.',
                        'Candidate2 captured old cwd; its main behavior checks do not qualify candidate2.',
                        'Root candidate2 full run failed category-before-combined diagnostic expectation; corrected exact expectation retained.',
                        'Candidate3 actual-source Clippy failure retained; candidate4 only adds documented targeted annotations.',
                        'Candidate4 metadata cache contaminated later full runs; 367-test claims invalidated and replaced with fresh isolated 366-test regression.'],
    limits=['Nine ordinary ignored host tests per profile remain excluded.',
            'Logical named-object accounting is not physical stack, allocator overhead or RSS.',
            'No active-frame interpreter, operation/growth/unwind or exhaustive interruption acceptance.',
            'No full Swift target instantiate/initialize/invoke or public route.',
            'No native parity, device, immutable published FieldLog, signing/store/customer/operational or GA qualification.'],
    bindings=dict(sorted(bindings.items())))
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': result['status'], 'bindings': len(bindings),
                  'cleanProductTests': clean['counts']}))
