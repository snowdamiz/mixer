from pathlib import Path
import hashlib,json,shutil,subprocess,os,tarfile
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; SCRATCH=Path('/tmp/mixer-swift-control-behavior-20261024'); VM=SCRATCH/'vm'
def files(root):
 names=[root/'Cargo.toml',root/'Cargo.lock']
 for sub in ['src','tests','include']: names+=sorted(p for p in (root/sub).rglob('*') if p.is_file())
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in names}
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
base=files(ROOT/'vm')
using_archive=hashlib.sha256(enc(base)).hexdigest()!='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
if using_archive:
 base=json.loads((HERE/'baseline-manifest.json').read_text());assert (HERE/'baseline-source.tar.gz').exists()
assert hashlib.sha256(enc(base)).hexdigest()=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
if not VM.exists():
 for name in base:
  dst=VM/name;dst.parent.mkdir(parents=True,exist_ok=True)
  if using_archive:
   with tarfile.open(HERE/'baseline-source.tar.gz') as archive:dst.write_bytes(archive.extractfile('vm/'+name).read())
  else:shutil.copyfile(ROOT/'vm'/name,dst)
 for p in (ROOT/'verification/swift-control-accounting-candidate-2/overlay').rglob('*'):
  if p.is_file():dst=VM/p.relative_to(ROOT/'verification/swift-control-accounting-candidate-2/overlay');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 assert hashlib.sha256(enc(files(VM))).hexdigest()=='e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d'
 (HERE/'starting-candidate-manifest.json').write_bytes(enc(files(VM)))
 (HERE/'baseline-manifest.json').write_bytes(enc(base))
owned={str(p.relative_to(HERE/'overlay')) for p in (HERE/'overlay').rglob('*') if p.is_file()}
expected=dict(base)
for p in (ROOT/'verification/swift-control-accounting-candidate-2/overlay').rglob('*'):
 if p.is_file():expected[str(p.relative_to(ROOT/'verification/swift-control-accounting-candidate-2/overlay'))]=hashlib.sha256(p.read_bytes()).hexdigest()
observed=files(VM)
assert all(observed.get(name)==digest for name,digest in expected.items() if name not in owned), 'unowned scratch source drift'
assert set(observed).issubset(set(expected)|owned), 'unexpected scratch source'
for p in (HERE/'overlay').rglob('*'):
 if p.is_file(): dst=VM/p.relative_to(HERE/'overlay');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
print(VM)
