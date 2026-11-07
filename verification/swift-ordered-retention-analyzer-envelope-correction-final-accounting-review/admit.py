#!/usr/bin/env python3
"""Exact final-source/archive/stream admission, with no producer execution."""
import hashlib,json,tarfile,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
PACKET=ROOT/'verification/swift-ordered-retention-analyzer-envelope-correction'
SEAL='4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1'
SELECTION=ROOT/'verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json'
SELECTION_SHA='199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c'
ARCHIVE_SHA='ca52e81504a95461806bec51ffb495bb57ec27456a3f7b266364cc2fa92c50e2'
OLD={
 'verification/swift-ordered-retention-analyzer-envelope/seal.json':'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae',
 'verification/swift-ordered-retention-analyzer-envelope-accounting-review/seal.json':'225d35ccd2c76c6306f7be21d3931c57a47ba6263897ba1847bfe7995226bf7f',
 'verification/swift-ordered-retention-analyzer-envelope-review/seal.json':'03c1986c3a19ae6464ac96cabe7743f6a562118bcb4a05689026df0de2165476',
 'verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review/seal.json':'f4b5136a8b513ca208e2f914acfea559d40edfe53a2cfb52a92129c82ec841d0',
 'verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review-2/seal.json':'c500c43ee55db92bd7a4bcaf62a90224761ee08dfbba80457069eebd7c8fd9ce',
}
def sha(data):return hashlib.sha256(data).hexdigest()
def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def verify_final():
 raw=(PACKET/'seal.json').read_bytes();assert sha(raw)==SEAL
 members=json.loads(raw)['members'];total=0
 for item in members:
  path=ROOT/item['path'];assert path.resolve().is_relative_to(ROOT.resolve())
  data=path.read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path'];total+=len(data)
 assert len(members)==306 and total==44895898
 assert sha(SELECTION.read_bytes())==SELECTION_SHA
 return {'seal_sha256':SEAL,'members':306,'bytes':total}
def verify_old():
 result=[]
 for relative,expected in OLD.items():
  raw=(ROOT/relative).read_bytes();assert sha(raw)==expected
  seal=json.loads(raw);total=0
  for item in seal['members']:
   data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path'];total+=len(data)
  result.append({'path':relative,'sha256':expected,'members':len(seal['members']),'bytes':total})
 for name,expected in [('operation-ledger-proposal-1','f3567bdae0835d7f024fcf7e759e197c44a7b4571204b37c80fb6c596e5bc23d'),('operation-ledger-proposal-2','58b2fccf992baade1eee51dfdd9f5e3bd5c039cfa5b52a3a25fef8d97ff034e5')]:
  base=PACKET/'commands'/name;raw=(base/'manifest.json').read_bytes();assert sha(raw)==expected
  d=json.loads(raw);total=0
  for m in d['members']:
   data=(base/m['path']).read_bytes();assert len(data)==m['bytes'] and sha(data)==m['sha256'];total+=len(data)
  result.append({'path':str((base/'manifest.json').relative_to(ROOT)),'sha256':expected,'members':len(d['members']),'bytes':total})
 return result
def main():
 name=sys.argv[1];assert name.startswith('admission-') and '/' not in name and '..' not in name
 run=OWN/'commands'/name;run.mkdir(parents=True,exist_ok=False)
 before=verify_final();old_before=verify_old();archive=PACKET/'selected-source-test-model.tar.gz'
 assert sha(archive.read_bytes())==ARCHIVE_SHA
 manifest=json.loads((PACKET/'source-test-model-manifest.json').read_bytes());expected={m['path']:m for m in manifest['members']}
 assert len(expected)==85
 manifest_raw=(PACKET/'source-test-model-manifest.json').read_bytes()
 expected['source-test-model-manifest.json']={'path':'source-test-model-manifest.json','bytes':len(manifest_raw),'sha256':sha(manifest_raw)}
 copied=[];dest=run/'archive';dest.mkdir()
 with tarfile.open(archive,'r:gz') as tf:
  members=tf.getmembers();assert len(members)==86;seen=set()
  for member in members:
   assert member.isfile() and member.name in expected and member.name not in seen
   target=dest/member.name;assert target.resolve().is_relative_to(dest.resolve())
   data=tf.extractfile(member).read();m=expected[member.name]
   assert len(data)==m['bytes']==member.size and sha(data)==m['sha256']
   assert data==(PACKET/member.name).read_bytes(),member.name
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);seen.add(member.name)
   copied.append({'path':member.name,'bytes':len(data),'sha256':sha(data)})
 assert seen==set(expected) and sum(m['bytes'] for m in copied)==20283818
 run_receipt=json.loads((PACKET/'commands/selected-run-1/receipt.json').read_bytes())
 raw_dest=run/'raw';raw_dest.mkdir();streams=[]
 for command in run_receipt['commands']:
  for side in ['stdout','stderr']:
   path=PACKET/'commands/selected-run-1'/command[side];data=path.read_bytes()
   assert sha(data)==command[side+'_sha256']
   (raw_dest/command[side]).write_bytes(data)
   streams.append({'command':command['name'],'stream':side,'path':command[side],'bytes':len(data),'sha256':sha(data)})
 assert len(run_receipt['commands'])==15 and len(streams)==30
 extras=['final-receipt.json','implementation-delta.json','selected-contract-delta.json','source-test-model-manifest.json','step-inventory.json','complete-transfer-edge-inventory.json','finalization-funding-table.json','logical-inventory.json','actual-complete-layouts.json','framing22-crosswalk.json','seal.json','seal.sha256','commands/selected-run-1/receipt.json']
 extra_dest=run/'metadata';extra_dest.mkdir()
 for relative in extras:
  data=(PACKET/relative).read_bytes();target=extra_dest/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 (extra_dest/'root-numeric-selection.json').write_bytes(SELECTION.read_bytes())
 preflight=ROOT/'verification/swift-ordered-retention-analyzer-envelope-root-review/selected-correction-preflight.json'
 (extra_dest/'root-selected-preflight.json').write_bytes(preflight.read_bytes())
 # Pin the actual source snapshots and alternate compiler entry, without running them.
 build_copies=[]
 for root_name in ['commands/selected-run-1/sources','commands/selected-run-1/build']:
  for path in sorted((PACKET/root_name).rglob('*')):
   if not path.is_file():continue
   relative=path.relative_to(PACKET);data=path.read_bytes();target=run/'compiled-inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
   build_copies.append({'path':str(relative),'bytes':len(data),'sha256':sha(data)})
 after=verify_final();old_after=verify_old();assert before==after and old_before==old_after
 commands=[]
 for name,argv in [('revision',['git','rev-parse','HEAD']),('python-version',[sys.executable,'--version'])]:
  p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,check=False)
  (run/(name+'.stdout.txt')).write_text(p.stdout);(run/(name+'.stderr.txt')).write_text(p.stderr);assert p.returncode==0
  commands.append({'name':name,'argv':argv,'exit_code':p.returncode})
 tool=Path(sys.executable).resolve()
 result={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,'status':'selected-final-source-closure-admitted-for-accounting',
  'before':before,'after':after,'old_before':old_before,'old_after':old_after,'selection_sha256':SELECTION_SHA,
  'archive_sha256':ARCHIVE_SHA,'archive_members':copied,'archive_members_equal_live_sealed_files':True,
  'raw_streams':streams,'compiled_input_copies':build_copies,'bookkeeping_commands':commands,
  'python_tool':{'path':str(tool),'bytes':tool.stat().st_size,'sha256':sha(tool.read_bytes())},
  'producer_or_frozen_runner_executed':False,'runtime_tests_or_layout_compile_run':False,'native_capture_process_or_device_discovery':False,
  'cleanup':'Only own regular-file copies extracted after strict archive verification. No producer/target executable, native/capture/device work; synchronous bookkeeping children returned/reaped.'}
 write_json(run/'receipt.json',result)
 out=json.dumps({'status':result['status'],'members':306,'archive_members':86,'raw_streams':30,'compiled_input_copies':len(build_copies)},sort_keys=True)+'\n'
 (run/'stdout.txt').write_text(out);(run/'stderr.txt').write_text('');print(out,end='')
if __name__=='__main__':main()
