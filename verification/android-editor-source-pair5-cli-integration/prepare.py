"""Prepare exact isolated CLI source-pair5 inputs; does not run any candidate tool."""
import hashlib, json, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
STAGE=HERE/'source'
assert not STAGE.exists(), 'Initial staging only; preserve the reviewed derivative source tree' 
REBIND=ROOT/'verification/android-editor-source-pair5-rebinding'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst,origin):
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    rows.append({'source':origin,'target':str(dst.relative_to(HERE)),'bytes':dst.stat().st_size,'sha256':sha(dst)})
rows=[]
selection=ROOT/'verification/android-editor-boundary-root-review/source-pair5-integration-selection.json'
assert sha(selection)=='364af243803a30dd0e6dbd66fd23ddb68671a0b0ce494731841a891888248e9e'
for rel,expected in [('verification/android-editor-source-pair5-rebinding/seal.json','088b6dd59bbfd91cd93e7c4cbb16ca1285018b0f6eb6045932b348f7beaf8864'),('verification/android-editor-integration-protocol/seal.json','2338ce170833c7a33d797d46a6d51d50e3b24398ed05b2b8b2129dafb35eb89f')]:
    seal=ROOT/rel; assert sha(seal)==expected
    data=json.loads(seal.read_text())
    for member in data['members']:
        actual=seal.parent/member['path']; assert actual.is_file() and not actual.is_symlink()
        assert actual.stat().st_size==member['bytes'] and sha(actual)==member['sha256'],actual
for amendment in json.loads(selection.read_text())['amendments']:
    assert sha(ROOT/amendment['path'])==amendment['sha256']
# Snapshot tracked first-party inputs only; no build caches or verification harnesses.
paths=subprocess.check_output(['git','ls-files','-z','cli','sdk','updates'],cwd=ROOT).decode().split('\0')
for rel in filter(None,paths):
    copy(ROOT/rel,STAGE/rel,rel)
profile=json.loads((REBIND/'profile5.json').read_text())
for kind,prefix in [('sdk','sdk'),('adapter','native/android')]:
    for rel,identity in profile[kind+'_files'].items():
        destrel=('engine/'+rel if kind=='adapter' and rel.startswith('Sources/') else rel)
        src=REBIND/'sources'/kind/rel
        assert src.stat().st_size==identity['bytes'] and sha(src)==identity['sha256']
        copy(src,STAGE/prefix/destrel,str(src.relative_to(ROOT)))
for src in (REBIND/'canonical-only-inputs').rglob('*'):
    if src.is_file(): copy(src,STAGE/'native/android'/src.relative_to(REBIND/'canonical-only-inputs'),str(src.relative_to(ROOT)))
# Existing Python suite's exact descriptor fixture remains at its established relative identity.
copy(REBIND/'descriptor.json',STAGE/'verification/android-default-appearance-packaging/run-2/created-descriptor.json','verification/android-editor-source-pair5-rebinding/descriptor.json')
(HERE/'inputs.json').write_text(json.dumps({'schema':1,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'selection_sha256':sha(selection),'inputs':rows},indent=2)+'\n')
print(json.dumps({'copied':len(rows),'source':str(STAGE)}))
