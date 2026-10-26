#!/usr/bin/env python3
"""Seal the bounded CI integration review. No product commands are executed."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def load(path):return json.loads(path.read_text())
def save(path,data):path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def check(value,message):
    if not value:raise RuntimeError(message)

receipt=load(BASE/'receipt.json')
check(receipt['status']=='passed-bounded-CI-integration-review-conditional-on-complete-delivery-and-remote-CI','review disposition')
check(receipt['script']==identity((BASE/'review.py').read_bytes()),'review source identity')
for name,value in load(BASE/'input-binding.json').items():check(identity((ROOT/name).read_bytes())==value,'current review input changed '+name)
check(identity((BASE/'workflow.yml').read_bytes())==load(BASE/'input-binding.json')['.github/workflows/verify.yml'],'retained workflow')
for folder in (BASE/'commands').iterdir():
    entry=load(folder/'receipt.json')
    for stream in ('stdout','stderr'):check(identity((folder/stream).read_bytes())==entry[stream],'command stream')
    check(entry['exit']==0,'audit command failed')
for lane in ('orchestration','renderer','observer'):
    folder=BASE/'local-receipts'/lane
    for entry in load(folder/'commands.json'):
        for stream in ('stdout','stderr'):check(identity((folder/(entry['label']+'.'+stream)).read_bytes())==entry[stream],'retained local raw stream')
        check(entry['exit']==0,'historical host command failed')
original=load(BASE/'local-receipts/root-receipt.json')
fix=load(BASE/'workflow-message-fix-disposition.json')
check(original['source_bindings']['.github/workflows/verify.yml']==fix['original_local_recipe_workflow'],'historical workflow disposition')
check(fix['current_repaired_workflow']==identity((ROOT/'.github/workflows/verify.yml').read_bytes()),'fixed workflow identity')
members={}
for path in sorted(BASE.rglob('*')):
    if path.is_file() and path not in (BASE/'manifest.json',BASE/'seal-receipt.json'):
        check(not path.is_symlink(),'symlink in packet')
        members[path.relative_to(BASE).as_posix()]=identity(path.read_bytes())
save(BASE/'manifest.json',{'schema':1,'members':len(members),'bytes':sum(v['bytes'] for v in members.values()),'files':members})
save(BASE/'seal-receipt.json',{'schema':1,'status':'sealed-bounded-CI-glue-review-awaiting-complete-delivery-and-remote-CI',
 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':[sys.executable,*sys.argv],
 'python_version':sys.version,'python_executable':{'path':str(Path(sys.executable).resolve()),**identity(Path(sys.executable).resolve().read_bytes())},
 'seal_script':identity(Path(__file__).read_bytes()),'manifest':identity((BASE/'manifest.json').read_bytes()),
 'members':len(members),'bytes':sum(v['bytes'] for v in members.values()),'audit_commands':13,
 'historical_raw_host_commands_audited':17,'product_behavior_reruns':0,
 'remote_CI_passed':False,'native_or_GA_accepted':False})
print(json.dumps({'manifest':identity((BASE/'manifest.json').read_bytes()),
 'seal':identity((BASE/'seal-receipt.json').read_bytes()),'members':len(members),'bytes':sum(v['bytes'] for v in members.values())}))
