from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/hosted-worker-pending-registry-engine-correction'
ORIGINAL = ROOT / 'verification/hosted-worker-pending-registry-engine'
REVIEW = ROOT / 'verification/hosted-worker-pending-registry-engine-review'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def entry(path, base=ROOT):
    data = path.read_bytes()
    return {'path': str(path.relative_to(base)), 'sha256': sha(data), 'bytes': len(data)}

checks = []
def expect(path, expected, label):
    observed = sha(path.read_bytes())
    assert observed == expected, (label, observed, expected)
    checks.append({'check': label, 'path': str(path.relative_to(ROOT)), 'sha256': observed})

expect(PRODUCER/'receipt.json', '3af44bc2353edab386ba20b30e647a71a2b70301c3e37ba2aea50de100a381f1', 'root-supplied correction receipt')
expect(PRODUCER/'correction.patch', '04203b53a6c22b252b781adca727511d977ec5a3e64b83ece2f60dce3f3653d7', 'root-supplied correction patch')
expect(REVIEW/'receipt.json', '3476e3e26845e4b3b21cf0208aac883908660fa5e3ae8c83392ec3859c824de0', 'root-supplied failed independent review')
expect(ORIGINAL/'receipt.json', '71190f11b04f1693135d4539a6ed0c0c36bf0cf9dfa058550af28549b06f5c76', 'original producer receipt')

for packet in [PRODUCER, ORIGINAL, REVIEW]:
    receipt = json.loads((packet/'receipt.json').read_text())
    for item in receipt['artifacts']:
        path = ROOT/item['path']
        assert str(path.resolve()).startswith(str(ROOT))
        expect(path, item['sha256'], 'receipt artifact')
    manifest_path = packet/'input-manifest.json'
    if manifest_path.exists():
        for item in json.loads(manifest_path.read_text())['entries']:
            expect(packet/item['path'], item['sha256'], 'packet immutable input')

for packet, run, expected in [
    (PRODUCER, '20261025T050031192Z', 'ee330a270f6151dfff96ed561a8b654ca1cc753026d03583cea99aee4276d811'),
]:
    manifest=json.loads((packet/'runs'/run/'source-manifest.json').read_text())
    assert manifest['sourceDigest'] == expected
    encoded = ''.join(f"{i['path']}\0{i['sha256']}\0{i['bytes']}\n" for i in manifest['entries'])
    assert sha(encoded.encode()) == expected
    for item in manifest['entries']:
        expect(packet/'candidate'/item['path'], item['sha256'], 'frozen producer candidate source')
        expect(packet/'runs'/run/'source'/item['path'], item['sha256'], 'frozen executed source')

production = []
for source in sorted((PRODUCER/'candidate/src').rglob('*')):
    if source.is_file():
        relative = source.relative_to(PRODUCER/'candidate')
        expect(OWN/'candidate'/relative, sha(source.read_bytes()), 'review production byte identity')
        original = ORIGINAL/'candidate'/relative
        production.append({'path': str(relative), 'originalSHA256':sha(original.read_bytes()),'correctionSHA256':sha(source.read_bytes()),'changed':source.read_bytes()!=original.read_bytes()})
assert [p['path'] for p in production if p['changed']] == ['src/engine.ts']

inputs=[]
for packet in [PRODUCER, ORIGINAL, REVIEW]:
    for path in sorted(packet.rglob('*')):
        if path.is_file() and 'dist' not in path.relative_to(packet).parts:
            inputs.append(entry(path))
for name in ['hosted-worker-pending-registry-engine-correction.md','hosted-worker-pending-registry-engine-review.md']:
    inputs.append(entry(ROOT/'docs'/name))
for path in [ROOT/'hosted-worker-controller/test/owned-workerd-identity.mjs',ROOT/'verification/hosted-worker-controller-contract/vectors.json',ROOT/'AGENTS.md']:
    inputs.append(entry(path))
snapshot={'schema':1,'files':inputs,'productionDelta':production,'checks':checks}
target=OWN/('input-verification-after.json' if '--after' in sys.argv else 'input-verification-before.json')
if '--after' in sys.argv:
    before=json.loads((OWN/'input-verification-before.json').read_text())
    assert before==snapshot, 'frozen input snapshot changed'
target.write_text(json.dumps(snapshot,indent=2)+'\n')
print(json.dumps({'status':'passed','checks':len(checks),'frozenFiles':len(inputs),'onlyProductionDelta':'src/engine.ts','beforeAfterEqual':'--after' in sys.argv}))
