#!/usr/bin/env python3
"""Read-only sealed producer replay. Does not require a retained scratch checkout."""
import difflib,gzip,hashlib,io,json,re,tarfile,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sha=lambda x:hashlib.sha256(x).hexdigest()
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def read(name):return json.loads((H/name).read_text())
def archive(manifest_name):
 m=read(manifest_name);p=H/manifest_name.replace('-source-manifest.json','-source.tar.gz');result={}
 with tarfile.open(p)as t:
  for e in t:
   assert e.isfile()and e.name in m and not Path(e.name).is_absolute()and'..'not in Path(e.name).parts
   body=t.extractfile(e).read();assert sha(body)==m[e.name];assert e.name not in result;result[e.name]=body
 assert set(result)==set(m);return result

def main():
 seal=read('seal.json');actual={str(p.relative_to(H))for p in H.rglob('*')if p.is_file()and p.name!='seal.json'};assert actual==set(seal['files'])
 for name,h in seal['files'].items():assert sha((H/name).read_bytes())==h,name
 for name,h in seal['externalBindings'].items():assert sha((ROOT/name).read_bytes())==h,name
 inputs=read('input-bindings.json')
 for name,h in inputs.items():assert sha((ROOT/name).read_bytes())==h,name
 receipt=read('receipt.json');assert receipt['status']=='isolated-producer-candidate-independent-review-pending'
 assert not any(receipt[k]for k in ['liveIntegrated','rootAccepted','g08Accepted','fullSwiftAccepted','publicInvocation','fullDispatcher','nativeAccepted','gaAccepted'])
 for name,h in receipt['bindings'].items():assert sha((H/name).read_bytes())==h,name
 baseline=archive('baseline-source-manifest.json');candidate=archive('candidate-source-manifest.json');assert len(baseline)==len(candidate)==128
 assert sha(enc(read('baseline-source-manifest.json')))==receipt['acceptedBaselineSourceSHA256']=='7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329'
 source=sha(enc(read('candidate-source-manifest.json')));assert source==receipt['candidateSourceSHA256']=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
 patch=''
 changed=read('changed-files.json')
 for name in changed:patch+=''.join(difflib.unified_diff(baseline[name].decode().splitlines(True),candidate[name].decode().splitlines(True),fromfile='a/vm/'+name,tofile='b/vm/'+name))
 assert patch==(H/'candidate.patch').read_text()
 assert {n for n in baseline if baseline[n]!=candidate[n]}==set(changed)
 manifests={}
 for p in H.glob('*-source-manifest.json'):
  t=p.with_name(p.name.replace('-source-manifest.json','-source.tar.gz'))
  if t.exists():archive(p.name);manifests.setdefault(sha(p.read_bytes()),[]).append(p.name)
 commands=read('commands.json');assert len(commands)==len(list((H/'commands').glob('*/receipt.json')))
 for row in commands:
  saved=read(row['receipt']);assert all(saved[k]==v for k,v in row.items()if k!='receipt')
  assert row['sourceUnchanged']and row['sourceTreeBeforeSHA256']==row['sourceTreeAfterSHA256']and row['sourceTreeBeforeSHA256']in manifests
  assert not row['timedOut']and not row['groupCleanup']['after']
  d=H/Path(row['receipt']).parent
  for stream in ['stdout','stderr']:assert sha(gzip.decompress((d/(stream+'.gz')).read_bytes()))==row[stream+'SHA256']
  assert read(str(Path(row['receipt']).parent/'source-manifest.json'))
 for p in(H/'artifacts').glob('*/identity.json'):
  row=json.loads(p.read_text());body=gzip.decompress((p.parent/'executable.gz').read_bytes());assert sha(body)==row['executableSHA256']and len(body)==row['executableBytes']
  for key in ['executableAfterListSHA256','executableAfterRunSHA256']:
   if row.get(key)is not None:assert row[key]==row['executableSHA256']
  assert row['cargoArtifactFresh']is False and row['targetCreatedEmpty']
 runtime=read('runtime-results.json');assert [x['passed']for x in runtime]==[252,252,282,282]
 assert sum(x['passed']for x in runtime)==1068 and all(x['sourceTreeSHA256']==source and len(x['selectedTests'])==17 for x in runtime)
 for r in runtime:
  name='final-runtime-'+r['features']+'-'+r['profile'];tests=read('artifacts/'+name+'/test-list.json');assert len(tests)==r['passed']
  for mode,count in [('execute',r['passed']),('probe',17)]:
   row=read('commands/'+mode+'-'+name+'/receipt.json');assert row['exitCode']==0 and row['sourceTreeBeforeSHA256']==source
   output=gzip.decompress((H/'commands'/ (mode+'-'+name)/'stdout.gz').read_bytes()).decode();assert re.search(r'test result: ok\. '+str(count)+r' passed; 0 failed;',output)
 frozen=read('frozen-runtime-results.json');assert len(frozen)==4 and sum(x['passed']for x in frozen)==64
 for r in frozen:assert r['sourceTreeSHA256']==(source if r['label']=='candidate'else receipt['acceptedBaselineSourceSHA256'])
 assert read('frozen-identity.json')['methodCount']==39
 assert read('compiler-checks.json')['sourceSHA256']==source
 assert read('cleanup.json')['ownedScratchRemoved']and read('cleanup.json')['holderCheckEmpty']and not read('cleanup.json')['survivingOwnedGroups']
 # Final canonical MIR is required to include free functions as well as methods.
 import inventory
 schema=read('inventory-schema.json');observed=[];functions=[]
 for config in ['production','unit']:
  rows,fn,captures=inventory.canonical(config,'final-qualified-mir');observed+=rows;functions+=fn
 stable=lambda r:{k:v for k,v in r.items()if k not in ['ownerClass','mirLine']}
 assert list(map(stable,observed))==list(map(stable,[r for r in schema if r['config']!='source']))
 assert len(schema)==5516 and len(functions)==32
 for config in ['production','unit']:
  names=[r['function']for r in functions if r['config']==config]
  for n in ['remove_live_at_with_wasi','primitive_pop','primitive_numeric','control_remove','remove_live_at','finish_inner','host_operation_inner']:
   assert any(re.search(r'(?:^|::)'+n+r'(?=$|::)',name)for name in names),(config,n)
 q=read('accounting-qualification.json');assert q['sourceSHA256']==source and q['positions']==5516 and len(q['legacyMIR'])==24
 layouts=read('qualified-layouts.json');assert len(layouts)==16
 for r in layouts:
  assert r['layout']['totals']['ticket_max']==86 and r['layout']['totals']['state_limit']==134217728 and r['layout']['totals']['combined_limit']==268435456
  if r['label']=='candidate':
   b=next(x for x in layouts if x['label']=='baseline'and all(x[k]==r[k]for k in ['features','profile','unit']))
   assert b['layout']['types']==r['layout']['types']and b['layout']['owners']==r['layout']['owners']
 from validate import mir_bodies,item
 for config in ['production','unit']:
  old=mir_bodies(gzip.decompress((H/('baseline-mir-'+config+'.mir.gz')).read_bytes()).decode());new=mir_bodies(gzip.decompress((H/('final-qualified-mir-'+config+'.mir.gz')).read_bytes()).decode())
  for n in ['remove_live_with_wasi','cleanup_fault','cleanup_fault_with_wasi','record_cleanup','fail','refund_with_wasi','end_construction_phase_with_wasi','finish_owned_cleanup']:
   keys=[k for k in old if 'control::'in k and k.endswith('::'+n)];assert len(keys)==1;key=keys[0];assert old[key]==new[key]and sha(new[key].encode())==q['legacyMIR'][config+':'+n]
  keys=[k for k in old if ('frame_operations::'in k and k.endswith('::remove_live'))or k=='primitive_clear'or k.endswith('::release_pending')or ('cache::'in k and k.endswith('::remove_live'))]
  assert len(keys)==4
  for key in keys:assert old[key]==new[key]and sha(new[key].encode())==q['legacyMIR'][config+':'+key]
 assert item(baseline['src/experimental_swift_reactor/control.rs'].decode(),'pub(crate) fn remove_live_with_wasi(')==item(candidate['src/experimental_swift_reactor/control.rs'].decode(),'pub(crate) fn remove_live_with_wasi(')
 from layouts import verify_fields
 for r in layouts:
  if r['label']=='candidate':verify_fields(r['layout'],schema,r['unit'])
 from type_layouts import parse
 full=read('complete-owned-type-layout-replay.json');assert full['pairedContexts']==8
 for r in full['records']:
  observed={}
  for label in ['baseline','candidate']:
   name='build-qualified-'+label+'-'+r['features']+'-'+r['profile']+'-'+r['config'];text=''.join(gzip.decompress((H/'commands'/name/(stream+'.gz')).read_bytes()).decode()for stream in ['stdout','stderr']);observed[label]=parse(text)
  for name,layout in r['layouts'].items():
   assert observed['baseline'][name]==observed['candidate'][name]
   assert all(layout[k]==observed['baseline'][name][k]for k in ['bytes','alignment','detail'])
 assert len(read('repair-group-results.json'))==17
 print('PASS sealed isolated cleanup diagnostic:',len(seal['files']),'files;',len(inputs),'bound inputs;1068 library/68 diagnostic/64 Frozen executions;5516 positions;review pending;G08/native/GA false')
if __name__=='__main__':main()
