from pathlib import Path
import tarfile,json,hashlib,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'verification/swift-cleanup-diagnostic-root-integration'
source=json.loads((BASE/'integrated-source-manifest.json').read_text())
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
assert hashlib.sha256(enc(source)).hexdigest()=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
for name in ['baseline','candidate']:
 p=HERE/name
 if p.exists():continue
 p.mkdir()
 with tarfile.open(BASE/'integrated-source.tar.gz') as t:t.extractall(p,filter='data')
 for rel,d in source.items():assert hashlib.sha256((p/rel).read_bytes()).hexdigest()==d,rel
shutil.copy2(BASE/'integrated-source-manifest.json',HERE/'baseline-manifest.json')
