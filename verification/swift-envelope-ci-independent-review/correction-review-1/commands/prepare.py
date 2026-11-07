#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROUND=Path(__file__).resolve().parents[1]
REPO=ROUND.parents[2]
WORK=ROUND/'portable-root'
PACK=REPO/'verification/swift-envelope-ci-pack'
EXPECTED={
    'scripts/ci/check-analyzer-envelope.py':'4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c',
    'scripts/ci/tests/test_analyzer_envelope_runner.py':'95adb99fd9f4dff39cf732414e8a287a5f301fe5860aa504e2ba394ccf33a8f1',
    'verification/swift-envelope-ci-root-review/correction-1-candidate-admission.json':'cd01af248cabe4e1ddab30998b395a8e4cabf39aaf1293e05a58c567e1ed939a',
    'verification/swift-envelope-ci-root-review/runner-correction-1-selection.json':'376589fa85f8da663e1f2ae4232ee28471e86cf9603a55ef0bb912381fb9bd7c',
    'verification/swift-envelope-ci-root-review/api-span-correction-targets.json':'24c4d9f7bea9e863a4af917c9ea422005448b39521d14672b3e56349c32a9852',
    'verification/swift-envelope-ci-pack/manifest.json':'4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a',
    'verification/swift-envelope-ci-runner-correction/seal.json':'853d2af30d63e4a6941625871d9b3787f1c6ab304c2bf7625d2d278bfdda8739',
}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(65536),b''):h.update(b)
    return h.hexdigest()


bindings=[]
for relative,digest in EXPECTED.items():
    p=REPO/relative
    if sha(p)!=digest:raise RuntimeError('admitted binding differs: '+relative)
    bindings.append({'path':relative,'bytes':p.stat().st_size,'sha256':digest})
manifest=json.loads((PACK/'manifest.json').read_bytes())
members=[]
for p in sorted(PACK.rglob('*')):
    if p.is_symlink():raise RuntimeError('pack link')
    if p.is_file() and p!=PACK/'manifest.json':members.append({'path':p.relative_to(PACK).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
if members!=manifest['members']:raise RuntimeError('pack members differ')
originals=json.loads((PACK/'inventories/selected-input-manifest.json').read_bytes())['inputs']
for item in originals:
    for name in item['packed_destinations']:
        p=PACK/name
        if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise RuntimeError('original destination differs')
derived=json.loads((PACK/'inventories/proposed-layout.json').read_bytes())['derived_test_only_files']
for item in derived:
    origin=next(r for r in originals if r['path']==item['original']['path'])
    data=(PACK/origin['packed_destinations'][0]).read_bytes()+item['appendix_utf8'].encode()
    if (PACK/item['packed_path']).read_bytes()!=data or hashlib.sha256(data).hexdigest()!=item['sha256']:raise RuntimeError('derived bytes differ')
(WORK/'scripts/ci').mkdir(parents=True)
(WORK/'verification').mkdir()
(WORK/'runs').mkdir()
shutil.copyfile(REPO/'scripts/ci/check-analyzer-envelope.py',WORK/'scripts/ci/check-analyzer-envelope.py')
shutil.copytree(PACK,WORK/'verification/swift-envelope-ci-pack')
audit={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python_executable':sys.executable,'python_version':sys.version,'git_version':subprocess.check_output(['git','--version'],cwd=REPO,text=True).strip(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'committed_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=REPO,text=True).strip(),'os':platform.platform(),'machine':platform.machine(),'bindings_verified':bindings,'pack_members_verified':members,'selected_originals_verified':len(originals),'selected_original_bytes':sum(r['bytes'] for r in originals),'derived_constructions_verified':derived,'scope':'Independent corrected byte-identical portable root; producer tests were hashed only and never loaded/executed; no model/native/capture execution.'}
with (ROUND/'input-audit.json').open('x') as stream:json.dump(audit,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'status':'prepared','pack_members':len(members),'originals':len(originals),'derived':len(derived),'runner_sha256':sha(WORK/'scripts/ci/check-analyzer-envelope.py')},sort_keys=True))
