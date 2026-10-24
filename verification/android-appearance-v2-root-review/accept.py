from pathlib import Path
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/android-appearance-v2-data'
REVIEW = ROOT / 'verification/android-appearance-v2-independent-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
bindings = {}

def bind(rel, digest=None):
    p = ROOT / rel
    actual = sha(p)
    if digest is not None:
        assert actual == digest, rel
    bindings[rel] = actual

commands = []
for name, script, args in [
    ('producer-seal', PRODUCER / 'scripts/verify-seal.py', []),
    ('independent-seal', REVIEW / 'verify-review.py', ['--with-binaries']),
]:
    argv = ['python3', str(script), *args]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    log = HERE / (name + '.log')
    log.write_text(result.stdout + result.stderr)
    assert result.returncode == 0
    commands.append(dict(argv=argv, cwd=str(ROOT), exit=result.returncode,
                         log=str(log.relative_to(ROOT)), sha256=sha(log)))
seal = read(PRODUCER / 'seal.json')
for rel, digest in seal['bindings'].items():
    bind(rel, digest)
producer = read(PRODUCER / 'candidate-3/receipt.json')
for rel, digest in producer['inputManifest'].items():
    bind(rel, digest)
    bind('verification/android-appearance-v2-data/candidate-3/inputs/' + rel, digest)
for command in producer['commands']:
    assert command['exit'] == 0
    for stream in ['stdout', 'stderr']:
        bind(command[stream], command[stream + 'SHA256'])
for rel, digest in producer['unchangedV1Bindings'].items():
    bind(rel, digest)
independent = read(REVIEW / 'acceptance.json')
assert independent['status'] == 'recommended-data-only' and not independent['findings']
for key in ['bindings', 'productBindings']:
    for rel, digest in independent[key].items():
        bind(rel, digest)
for rel, digest in independent['receipts'].items():
    bind('verification/android-appearance-v2-independent-review/' + rel, digest)
assert independent['producerReceiptSHA256'] == sha(PRODUCER / 'candidate-3/receipt.json')
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '--',
    str(PRODUCER.relative_to(ROOT)), str(REVIEW.relative_to(ROOT)), str(HERE.relative_to(ROOT))],
    cwd=ROOT, text=True).splitlines()
for rel in paths:
    if rel == str((HERE / 'acceptance.json').relative_to(ROOT)):
        continue
    assert '/build/' not in rel and '__pycache__' not in rel
    bind(rel)
out = dict(schema=1, status='accepted-android-v2-host-data', reviewer='root',
           observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           sourceRevision=producer['sourceRevision'], inputTreeSHA256=producer['inputTreeSHA256'],
           producerCases=dict(descriptor=1453, geometry=1881, retainedV1=7147),
           independentCases=dict(descriptor=6165, accepted=1055, rejected=5110,
                                 javaGeometry=100989, swiftGeometry=100976,
                                 parserLimits=13, ownership=3, completeByteBoundaries=3),
           executionModes=['JVM default', 'JVM -Xint', 'Swift -Onone', 'Swift -O'],
           completeByteBoundaryOutcomes={'65535':'accept','65536':'accept','65537':'reject'},
           sourceReview='Closed ASCII grammar and semantic admission, immutable owned bytes/lists/paths, no maintained Java default theme, fixed authored shapes and boundary rounding reviewed by independent lane and root.',
           limits=['Host data only; no Android framework, resource installation, fonts or native support authority.',
                   'No resolver/native consumers, display health, interaction/accessibility or physical design parity.',
                   'No signed V2, OTA, immutable published FieldLog or GA acceptance.',
                   '13 Java signed-domain geometry cases have no Swift unsigned counterpart; counts remain separate.'],
           retainedFailures='Producer initial probe compile and independent preflight/log-field and depth-vs-value harness mistakes preserved; corrected isolated snapshots qualify final results.',
           commands=commands, bindings=dict(sorted(bindings.items())))
(HERE / 'acceptance.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status':out['status'],'bindings':len(bindings)}))
