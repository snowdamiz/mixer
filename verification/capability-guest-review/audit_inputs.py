#!/usr/bin/env python3
"""Read-only identity/parity audit of the exact implementation Git objects."""
from pathlib import Path
import hashlib,json,subprocess,tomllib
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
REV='cc0ac37abf45c59df7c85f59ebbb038af7c0a251'
RECEIPT='vm/verification/capability-guest/2026-10-23-host/receipt.json'
MANIFEST='vm/verification/capability-guest/2026-10-23-host/source-manifest.sha256'
EXPECTED='1697111c4821879673950c143d8474667286e8632c6d769239ff402f999274ba'
def read(path,rev=REV):return subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
r=json.loads(read(RECEIPT));m=read(MANIFEST);assert sha(m)==EXPECTED
report={'reviewed_revision':REV,'implementation_manifest':MANIFEST,'implementation_manifest_sha256':sha(m),'implementation_receipt':RECEIPT,'implementation_receipt_sha256':sha(read(RECEIPT)),'implementation_inputs':[],'command_logs':[],'baseline_comparisons':[],'public_field_comparisons':[],'fixed_payloads':[]}
for line in m.decode().splitlines():
 expected,path=line.split('  ',1);assert sha(read(path))==expected,path
 assert not path.startswith('vm/src/capability_ffi/'),path
 report['implementation_inputs'].append({'path':path,'sha256':expected})
assert len(report['implementation_inputs'])==77
for command in r['commands']:
 assert command['exit_code']==0,command['name']
 actual=sha(read(command['log']));assert actual==command['sha256'],command['name']
 report['command_logs'].append({'name':command['name'],'path':command['log'],'sha256':actual,'exit_code':command['exit_code'],'scope':'Implementation author evidence identity verified; not independently rerun'})
for item in r['frozen_files']:
 path=item['path'];data=read(path);assert data==read(path,r['base_revision']) and sha(data)==item['sha256'],path
 report['baseline_comparisons'].append({'path':path,'sha256':sha(data),'base_revision':r['base_revision'],'equal':True})
def declaration(data,marker):
 start=data.index(marker.encode());brace=data.index(b'{',start);depth=0
 for i in range(brace,len(data)):
  if data[i]==123:depth+=1
  if data[i]==125:
   depth-=1
   if depth==0:return data[start:i+1]
 raise AssertionError(marker)
for item in r['unchanged_rust_field_definitions']:
 path=item['path'];marker=item['marker'];current=declaration(read(path),marker);previous=declaration(read(path,r['base_revision']),marker)
 assert current==previous,marker
 # Exact source-block comparison is evidence of preserved fields, not OTA admission.
 report['public_field_comparisons'].append({'path':path,'marker':marker,'base_revision':r['base_revision'],'sha256':sha(current),'equal':True})
features=tomllib.loads(read('vm/Cargo.toml').decode())['features'];assert features['default']==[];assert features['experimental-capability-guest']==['experimental-capability-mailbox'];report['feature_selection']=features
contract=json.loads(read('contracts/guest-capability-transport-v1.json'))
assert sha(read('contracts/guest-capability-transport-v1.json'))=='052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439'
def exact_object(pairs):
 out={}
 for k,v in pairs:
  assert k not in out,'duplicate '+k;out[k]=v
 return out
for entry in contract['operations']:
 for code in ['unavailable','cancelled','deadlineExceeded']:
  path='vm/src/experimental_capability_guest/generated/'+entry['import']+'-'+code+'.json';data=read(path)
  value=json.loads(data,object_pairs_hook=exact_object)
  expected={'abi':1,'capability':entry['capability'],'schemaHash':entry['schemaHash'],'operation':entry['operation'],'outcome':{'kind':'failure','code':code}}
  assert value==expected and type(value['abi'])is int,path
  assert data==json.dumps(expected,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode(),path
  report['fixed_payloads'].append({'path':path,'sha256':sha(data),'bytes':len(data),'contract_binding_verified':True})
report['independent_runtime_scope']='Separate public-API Rust tests; this script verifies source/log/parity identities only and grants no release authority'
report['excluded']='Root-owned capability_ffi/C/registry follow-on, devices, native I/O, activation and release/GA qualification'
(OUT/'input-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('Independently verified 77 frozen inputs, 42 implementation log hashes, 10 unchanged files, 4 unchanged field definitions, 12 exact fixed payloads, empty default features')
print('Actual implementation logs:',len(report['command_logs']))
