"""Read-only verification of this frozen implementation packet and current owned source."""
import hashlib,json,pathlib,stat
BASE=pathlib.Path(__file__).resolve().parent;REPO=BASE.parents[1]
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
control={'members.json','seal.sha256'}
manifest=json.loads((BASE/'members.json').read_text())
expected=(BASE/'seal.sha256').read_text().split()[0]
assert hashlib.sha256((BASE/'members.json').read_bytes()).hexdigest()==expected
actual={p.relative_to(BASE).as_posix() for p in BASE.rglob('*') if p.is_file()}
assert actual==set(manifest)|control,(actual-set(manifest)-control,set(manifest)-actual)
for relative,row in manifest.items():
 path=BASE/relative
 assert stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink(),relative
 assert identity(path.read_bytes())==row,relative
for relative,row in json.loads((BASE/'owned-source-manifest.json').read_text()).items():
 assert identity((REPO/relative).read_bytes())==row,relative
assert identity((REPO/'docs/android-copied-sdk-appearance-implementation.md').read_bytes())==identity((BASE/'implementation.md').read_bytes())
print('Verified',len(manifest),'frozen members and current owned product/doc bytes')
