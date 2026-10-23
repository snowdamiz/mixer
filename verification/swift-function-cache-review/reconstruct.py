#!/usr/bin/env python3
"""Independent frozen-tree reconstruction; no product mutations or guest run."""
from pathlib import Path
import hashlib, io, json, os, subprocess, tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/swift-function-cache'
EXPECTED = '90d80a9b29aca64f07bcda56196b29523dbf1635fedb8d393f807591e5c43fdd'
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_text())
receipt_bytes = (PRODUCER / 'producer-receipt.json').read_bytes()
assert sha(receipt_bytes) == EXPECTED
receipt = json.loads(receipt_bytes)
freeze = read(PRODUCER / 'source-freeze.json')
assert len(freeze['source_manifest']) == 118
assert len(freeze['overlays']) == 10
assert sha(json.dumps(freeze['source_manifest'], sort_keys=True).encode()) == freeze['source_manifest_sha256'] == receipt['source_manifest_sha256']
bindings = {}
for p, digest in receipt['bindings'].items():
    observed = sha((ROOT / p).read_bytes())
    assert observed == digest, (p, digest, observed)
    bindings[p] = observed
frozen = {}
with tarfile.open(PRODUCER / 'frozen-source.tar.gz', 'r:gz') as archive:
    assert len(archive.getmembers()) == 118
    for item in archive.getmembers():
        assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
        data = archive.extractfile(item).read()
        assert sha(data) == freeze['source_manifest'][item.name], item.name
        frozen[item.name] = data
assert set(frozen) == set(freeze['source_manifest'])
tree = HERE / 'tree'
assert not tree.exists(), 'Preserve prior tree; do not overwrite an independent probe.'
tree.mkdir()
baseline = subprocess.run(['git', 'archive', freeze['baseline_revision']], cwd=ROOT, check=True, capture_output=True).stdout
with tarfile.open(fileobj=io.BytesIO(baseline)) as archive:
    archive.extractall(tree, filter='data')
for p, data in frozen.items():
    baseline_path = tree / p
    before = sha(baseline_path.read_bytes()) if baseline_path.exists() else None
    if p in freeze['overlays']:
        assert before == freeze['overlays'][p]['baseline_sha256'], p
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_bytes(data)
    else:
        assert before == sha(data), p
assert all(sha((tree / p).read_bytes()) == h for p, h in freeze['source_manifest'].items())
live = {p: sha((ROOT / p).read_bytes()) for p in frozen}
assert live == freeze['source_manifest'], 'Bound live source changed after producer freeze.'
env = os.environ | {'PATH': '/opt/homebrew/opt/rustup/bin:' + os.environ['PATH']}
tools = []
for argv in [['rustc','-Vv'], ['cargo','-V'], ['python3','--version'], ['git','--version'], ['uname','-a']]:
    p = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    tools.append({'argv':argv,'stdout':p.stdout,'stderr':p.stderr})
result = {'producer_receipt_sha256':EXPECTED,'baseline_revision':freeze['baseline_revision'],
          'live_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'tree_source_manifest_sha256':freeze['source_manifest_sha256'],
          'source_files':len(frozen),'overlay_files':len(freeze['overlays']),
          'bound_artifacts':bindings,'all_bound_live_source_equal':True,
          'tree':str(tree),'tools':tools,
          'limitations':['No guest instantiation, initialization, invocation, device discovery, publication, or commits.']}
(HERE / 'reconstruction.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['bound_artifacts','tools']},indent=2))
