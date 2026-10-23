#!/usr/bin/env python3
"""Attach native-only review archive provenance without rerunning unrelated tests."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
ROOT=Path(__file__).resolve().parents[3]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--name',required=True);a=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+',a.name):p.error('invalid receipt name')
    out=ROOT/'vm/verification/capability-native'/a.name;path=out/'receipt.json';receipt=json.loads(path.read_text())
    rows=(out/'source-manifest.sha256').read_text().splitlines()
    def check():
        for row in rows:
            digest,name=row.split('  ',1)
            if sha(ROOT/name)!=digest:raise RuntimeError('source differs: '+name)
    check();target=Path(receipt['environment']['CARGO_TARGET_DIR'])
    env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ.get('PATH',''),CARGO_TARGET_DIR=str(target))
    provenance={'source_manifest_sha256':receipt['source_manifest_sha256'],'scope':'native-only archive source/build/copy binding; no new test/device claim','script_sha256':sha(Path(__file__)),'commands':[],'archives':{}}
    copies=ROOT/'vm/target/capability-native-review-final-v3'
    for build,flags in [('debug',[]),('release',['--release'])]:
        argv=['cargo','build','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-capability-native',*flags]
        before=time.monotonic();r=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        log=out/('review-archive-'+build+'.log');log.write_text(r.stdout)
        provenance['commands'].append({'argv':argv,'exit_code':r.returncode,'elapsed_host_development_seconds':round(time.monotonic()-before,6),'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
        if r.returncode:raise RuntimeError('native-only build failed')
        archive=target/build/'libmixer_vm.a';copy=copies/build/'libmixer_vm.a'
        if not copy.is_file():
            copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(archive,copy)
        if sha(copy)!=sha(archive):raise RuntimeError('captured copy does not match current build: '+str(copy))
        provenance['archives'][build]={'path':str(copy),'sha256':sha(copy),'matches_native_only_rebuild':True}
        if build=='release':provenance['archives'][build]['matches_primary_native_release']=sha(copy)==receipt['artifacts']['native']['archive_sha256']
    check();provenance['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    sidecar=out/'review-archive-provenance.json';sidecar.write_text(json.dumps(provenance,indent=2)+'\n')
    receipt['additional_review_archive_provenance']={'path':str(sidecar.relative_to(ROOT)),'sha256':sha(sidecar),'script':'vm/verification/capability-native/pin-review-archives.py','script_sha256':sha(Path(__file__))}
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(provenance['archives'],indent=2))
if __name__=='__main__':main()
