#!/usr/bin/env python3
"""Admit immutable proposal2; execute only own bookkeeping."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OWN=Path(__file__).resolve().parent
PACKET=ROOT/'verification/swift-ordered-retention-analyzer-envelope-correction/commands/operation-ledger-proposal-2'
MANIFEST='58b2fccf992baade1eee51dfdd9f5e3bd5c039cfa5b52a3a25fef8d97ff034e5'
OLD={
 'verification/swift-ordered-retention-analyzer-envelope/seal.json':'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae',
 'verification/swift-ordered-retention-analyzer-envelope-accounting-review/seal.json':'225d35ccd2c76c6306f7be21d3931c57a47ba6263897ba1847bfe7995226bf7f',
 'verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review/seal.json':'f4b5136a8b513ca208e2f914acfea559d40edfe53a2cfb52a92129c82ec841d0',
}
def sha(data):return hashlib.sha256(data).hexdigest()
def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def verify_proposal():
 raw=(PACKET/'manifest.json').read_bytes();assert sha(raw)==MANIFEST
 d=json.loads(raw);total=0
 for item in d['members']:
  path=PACKET/item['path'];assert path.resolve().is_relative_to(PACKET.resolve())
  data=path.read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path'];total+=len(data)
 assert len(d['members'])==42 and total==633148
 return {'manifest_sha256':MANIFEST,'members':42,'bytes':total}
def verify_old():
 result=[]
 for relative,expected in OLD.items():
  raw=(ROOT/relative).read_bytes();assert sha(raw)==expected
  seal=json.loads(raw);total=0
  for item in seal['members']:
   data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path'];total+=len(data)
  result.append({'path':relative,'sha256':expected,'members':len(seal['members']),'bytes':total})
 return result
def main():
 run=OWN/'commands/admission-1';run.mkdir(parents=True,exist_ok=False)
 before=verify_proposal();old_before=verify_old();dest=run/'inputs';dest.mkdir()
 d=json.loads((PACKET/'manifest.json').read_bytes());copies=[]
 for name in [x['path'] for x in d['members']]+['manifest.json']:
  data=(PACKET/name).read_bytes();out=dest/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
  copies.append({'path':name,'bytes':len(data),'sha256':sha(data)})
 commands=[]
 for name,argv in [('revision',['git','rev-parse','HEAD']),('python-version',[sys.executable,'--version'])]:
  p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,check=False)
  (run/(name+'.stdout.txt')).write_text(p.stdout);(run/(name+'.stderr.txt')).write_text(p.stderr)
  commands.append({'name':name,'argv':argv,'exit_code':p.returncode});assert p.returncode==0
 after=verify_proposal();old_after=verify_old();assert before==after and old_before==old_after
 tool=Path(sys.executable).resolve()
 receipt={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,'status':'proposal2-admitted-no-numeric-selection',
  'before':before,'after':after,'old_before':old_before,'old_after':old_after,'copies':copies,
  'copied_tree_sha256':sha(json.dumps(copies,sort_keys=True,separators=(',',':')).encode()),'commands':commands,
  'python_tool':{'path':str(tool),'bytes':tool.stat().st_size,'sha256':sha(tool.read_bytes())},
  'producer_scripts_or_tests_executed':False,'runtime_probes_executed':False,'numeric_selection':False,
  'native_capture_process_or_device_discovery':False,'cleanup':'Only immutable copies/bookkeeping outputs created; synchronous bookkeeping children returned/reaped. No product/runtime/compile/native/capture work.'}
 write_json(run/'receipt.json',receipt)
 out=json.dumps({'status':receipt['status'],'members':42,'bytes':633148,'old_members_unchanged':sum(x['members'] for x in old_after)},sort_keys=True)+'\n'
 (run/'stdout.txt').write_text(out);(run/'stderr.txt').write_text('');print(out,end='')
if __name__=='__main__':main()
