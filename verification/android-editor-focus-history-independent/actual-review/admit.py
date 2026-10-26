#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,shutil,sys
D=Path(__file__).resolve().parent
P=D.parent
ROOT=P.parents[1]
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def verify(directory,seal):
    size=0
    for item in seal['members']:
        relative=Path(item['path']);assert not relative.is_absolute() and '..' not in relative.parts
        path=directory/relative;assert not path.is_symlink() and path.resolve().is_relative_to(directory.resolve())
        assert row(path)=={key:item[key] for key in ['bytes','sha256']},str(relative);size+=item['bytes']
    return size
pre=P/'preaccess-seal.json';assert row(pre)['sha256']=='169a0f581e0871e1ac273b88f653dc4d87381628fb8a39b8b2ec4bf7c80dbc62';assert verify(P,json.loads(pre.read_text()))==660205
custody=ROOT/'verification/android-editor-boundary-root-review/focus-history-implementation-review-custody.json';assert row(custody)['sha256']=='89bf40f503c2302e957e2a64426323a978cd3a3514768a4c2e456231004f56ea'
producer=ROOT/'verification/android-editor-focus-history-correction';sealpath=producer/'seal.json';assert row(sealpath)['sha256']=='2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8'
seal=json.loads(sealpath.read_text());assert len(seal['members'])==5325 and verify(producer,seal)==24030540
frozen=D/'frozen';frozen.mkdir(exist_ok=False);copied=[]
for item in seal['members']:
    relative=Path(item['path'])
    if relative.parts[0]=='runs':continue
    target=frozen/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(producer/relative,target);copied.append(item)
shutil.copyfile(custody,D/'root-custody.json');shutil.copyfile(sealpath,D/'producer-seal.json')
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'producer_seal':row(sealpath),'root_custody':row(custody),'preaccess_seal':row(pre),'producer_members_verified':5325,'producer_bytes_verified':24030540,'preaccess_members_verified_unchanged':71,'preaccess_bytes_verified_unchanged':660205,'copied_nonrun_members':copied,'historical_producer_runs_hashed_not_imported_or_executed':True,'product_executions_at_admission':0,'scope':'Released frozen complete-source correction review only; no canonical/native/GA acceptance'}
(D/'admission-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'members_verified':5325,'bytes_verified':24030540,'copied_nonrun_members':len(copied),'preaccess_members_unchanged':71,'product_executions':0}))
