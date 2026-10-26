#!/usr/bin/env python3
"""Custody gate for only the exact root-released frozen correction."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/android-editor-replacement-implementation'
OUT=HERE/'actual-review'


def sha(data):return hashlib.sha256(data).hexdigest()


def verify_members(directory,seal):
    total=0
    for row in seal['members']:
        relative=Path(row['path']);assert not relative.is_absolute() and '..' not in relative.parts
        path=directory/relative;assert not path.is_symlink() and path.resolve().is_relative_to(directory.resolve())
        data=path.read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'],str(relative)
        total+=len(data)
    return total


def main():
    preaccess=(HERE/'preaccess-seal.json').read_bytes();assert sha(preaccess)=='dec2610cb92d635322866d650ed52ab82263db198e203eb49c88b5bfd9592161'
    prior=json.loads(preaccess);assert len(prior['members'])==66
    assert verify_members(HERE,prior)==3030527
    root_path=ROOT/'verification/android-editor-boundary-root-review/replacement-implementation-review-custody.json'
    root_bytes=root_path.read_bytes();assert sha(root_bytes)=='0760629db35457f75a6cf235ee91e5005d90693f9353ed08d422bf13bb41a554'
    root=json.loads(root_bytes);assert root['review_access_released'] is True
    seal_bytes=(PRODUCER/'seal.json').read_bytes();assert sha(seal_bytes)=='4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3'
    seal=json.loads(seal_bytes);assert len(seal['members'])==4986
    assert verify_members(PRODUCER,seal)==22035582
    OUT.mkdir(exist_ok=True);copied=[]
    for row in seal['members']:
        relative=Path(row['path'])
        if relative.parts[0]=='runs':continue
        data=(PRODUCER/relative).read_bytes();target=OUT/'frozen'/relative
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);copied.append(row)
    (OUT/'producer-seal.json').write_bytes(seal_bytes);(OUT/'root-custody.json').write_bytes(root_bytes)
    receipt={'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),'argv':sys.argv,'python':sys.version,
             'script_sha256':sha(Path(__file__).read_bytes()),
             'root_custody_sha256':sha(root_bytes),'producer_seal_sha256':sha(seal_bytes),
             'producer_members_verified':4986,'producer_bytes_verified':22035582,
             'preaccess_members_verified_unchanged':66,'preaccess_bytes_verified_unchanged':3030527,
             'copied_current_and_historical_nonrun_members':copied,
             'product_tree':seal['product_source_tree_digest'],'host_tree':seal['complete_host_closure_tree_digest'],
             'historical_run_members_hashed_not_imported_or_executed':True,
             'candidate_product_executions_at_admission':0,
             'scope':'Independent complete actual-source review only; no integration/native/GA acceptance',
             'source_revision_context_only':'db6332d4c27efec4f9e22b9adc43000d48c591a1'}
    (OUT/'admission-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'verified_members':4986,'verified_bytes':22035582,'copied_nonrun_members':len(copied),'preaccess_members_unchanged':66,'candidate_product_executions':0}))


if __name__=='__main__':main()
