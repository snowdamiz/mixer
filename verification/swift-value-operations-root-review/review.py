#!/usr/bin/env python3
"""Root acceptance of source-bound private value operations and independent review."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-executor-operations'
INDEPENDENT = ROOT / 'verification/swift-value-operations-independent-review'
RESULT = ROOT / 'verification/swift-executor-operations/results/20261024T013344529137Z'
REVIEW = Path(sys.argv[1]).resolve()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
encode = lambda x: (json.dumps(x, sort_keys=True, indent=2)+'\n').encode()
bindings = {}
commands = []

def bind(path, expected=None):
    path = Path(path)
    actual = sha(path)
    if expected is not None: assert actual == expected, str(path)
    bindings[str(path.relative_to(ROOT))] = actual
    return actual

def run(name, argv, cwd=ROOT):
    p = subprocess.run(list(map(str, argv)), cwd=cwd, capture_output=True, text=True, timeout=120)
    log = HERE / (name+'.log')
    log.write_text(p.stdout+p.stderr)
    commands.append(dict(name=name, argv=list(map(str,argv)), cwd=str(cwd), exitCode=p.returncode,
                         log=str(log.relative_to(ROOT)), sha256=sha(log)))
    assert p.returncode == 0, (name,p.stdout[-2000:],p.stderr[-2000:])
    return p.stdout

producer_seal = json.loads((PRODUCER/'seal.json').read_text())
bind(PRODUCER/'seal.json')
for name, expected in producer_seal['files'].items(): bind(ROOT/name, expected)
source = json.loads((RESULT/'candidate-manifest.json').read_text())
assert len(source) == 116
assert hashlib.sha256(encode(source)).hexdigest() == producer_seal['sourceTreeSHA256']
with tarfile.open(RESULT/'candidate-source.tar.gz') as archive:
    for name, expected in source.items():
        assert hashlib.sha256(archive.extractfile('vm/'+name).read()).hexdigest() == expected
        bind(ROOT/'vm'/name,expected)
run('producer-evidence', ['python3','-B',PRODUCER/'verify.py',RESULT])
run('independent-evidence', ['python3','-B',INDEPENDENT/'verify.py',REVIEW])
independent = json.loads((REVIEW/'receipt.json').read_text())
assert independent['status'] == 'passed-selected-native-outcomes-accounting-review-separate'
assert independent['sourceTreeSHA256'] == producer_seal['sourceTreeSHA256']
assert independent['producerSealSHA256'] == sha(PRODUCER/'seal.json')
for p in sorted(REVIEW.rglob('*')):
    if p.is_file(): bind(p)
bind(ROOT/'docs/swift-value-operations-independent-review.md')
bind(INDEPENDENT/'seal.json')
review_seal = json.loads((INDEPENDENT/'seal.json').read_text())
assert review_seal['status'] == 'INDEPENDENT_REVIEW_NO_BLOCKING_FINDINGS_FOR_PRIVATE_ZERO_FRAME_VALUE_OPERATIONS'
assert review_seal['sourceTreeSHA256'] == producer_seal['sourceTreeSHA256']
bind(INDEPENDENT/'decision.json',review_seal['decisionSHA256'])
for name, expected in review_seal['files'].items(): bind(ROOT/name,expected)
audit = json.loads((REVIEW/'accounting-audit.json').read_text())
assert audit['sourceTreeSHA256'] == producer_seal['sourceTreeSHA256']
assert (audit['fields'],audit['typedPositions']) == (227,561)
assert len(independent['binaries']) == 8
assert sum(b['passed'] for b in independent['binaries']) == 92
for index,b in enumerate(independent['binaries']):
    path = Path(b['path'])
    assert sha(path) == b['sha256']
    listed = run('independent-binary-'+str(index)+'-list',[path,'--list'])
    assert [s[:-6] for s in listed.splitlines() if s.endswith(': test')] == b['listedTests']
    assert b['passed'] == (11 if b['kind']=='derived-independent-tests' else 12)
    assert b['ignored'] == 0
summary = json.loads((RESULT/'verified-summary.json').read_text())
for row in summary['layouts']:
    assert row['after']['permanent'] == 82184 and row['after']['active'] == 103248
    assert row['after']['phase'] == 119576
    assert row['before']['construction'] == row['after']['construction']
run('policy',['python3','scripts/check-policy.py'])
# Verifiers may only regenerate byte-identical derived records under these seals.
for name, expected in bindings.items(): assert sha(ROOT/name) == expected, name
decision = dict(schema=1,status='accepted-private-original-owner-zero-frame-value-operations',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    sourceTreeSHA256=producer_seal['sourceTreeSHA256'],reviewer='root after independent source and native-host review',
    producerResults=str(RESULT.relative_to(ROOT)),independentResults=str(REVIEW.relative_to(ROOT)),
    bindingCount=len(bindings),bindings=bindings,commands=commands,
    evidence=dict(producerCommands=131,producerProductBinaries=48,ownerLayoutComparisons=8,
                  typedFields=227,typedPositions=561,independentProductSelectedExecutions=48,
                  independentDerivedTestExecutions=44,permanentBytes=82184,activeBytes=103248,
                  operationBytes=119576,frozenReservationBytes=2912,broadClippyExistingDiagnostics=26),
    decision='The corrected positive inventory, original-owner operation ordering and fixed caller return-storage contract are accepted for this private zero-frame slice. Old accounting and collector failures remain retained. Metadata probes are not product tests.',
    limitations=['Selected host matrices, not the full product suite; six prior ignored development oracles remain ignored.',
                 'Named logical/requested storage, not physical stack, RSS or arbitrary caller storage.',
                 'No instruction loop, initialize/invoke, function/control flow, active-frame unwind, growth or host dispatch.',
                 'An abandoned phase deliberately retains its construction reservation through final diagnostic cleanup.',
                 'No native mobile execution, immutable published FieldLog package, signed release, store or GA pass.'])
(HERE/'acceptance.json').write_bytes(encode(decision))
print(json.dumps(dict(status=decision['status'],bindings=len(bindings),sourceTreeSHA256=decision['sourceTreeSHA256']),indent=2))
