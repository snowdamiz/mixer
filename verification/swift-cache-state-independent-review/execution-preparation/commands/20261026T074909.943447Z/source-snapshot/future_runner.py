"""Future narrow candidate execution, closed until exact root admission.

Importing this module reads no candidate. The current preparation never calls
stage_candidate or execute with a real candidate admission.
"""
import argparse
import json
from pathlib import Path,PurePosixPath
import stat
import struct
from harness import HERE,ROOT,bounded,compare_public,protocol,sha,write_json

PRE=HERE.parent/'preaccess'
PRODUCER='verification/swift-cache-state-implementation/'
GETTER_SHA='80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1'
PREACCESS_SHA='1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c'

def safe_relative(value):
 if not isinstance(value,str): raise ValueError('relative path string')
 p=PurePosixPath(value)
 if p.is_absolute() or '..' in p.parts or not p.parts or '\\' in value: raise ValueError('unsafe relative path')
 return str(p)

def gate(value):
 if not isinstance(value,dict) or value.get('schema')!=1 or value.get('status')!='admitted-independent-cache-state-execution': raise ValueError('no exact root admission')
 if value.get('preaccess_seal_sha256')!=PREACCESS_SHA or value.get('getter_selection_sha256')!=GETTER_SHA: raise ValueError('upstream identity')
 seal=safe_relative(value.get('candidate_seal'))
 entry=safe_relative(value.get('crate_entry'))
 if not seal.startswith(PRODUCER) or not entry.startswith(PRODUCER) or not entry.endswith('.rs'): raise ValueError('candidate closure outside selected producer')
 output=safe_relative(value.get('review_output_directory'))
 if not output.startswith('verification/swift-cache-state-independent-review/implementation-review-'):
  raise ValueError('output must be a separate admitted review phase')
 if value.get('edition') not in ('2021','2024'): raise ValueError('closed compiler edition')
 for field in ['candidate_seal_sha256','rustc_sha256','reviewer_preparation_sha256']:
  v=value.get(field)
  if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v): raise ValueError('exact hash '+field)
 compiler=value.get('rustc')
 if not isinstance(compiler,str) or not Path(compiler).is_absolute(): raise ValueError('exact compiler path')
 if value.get('rustc_version') is None or not isinstance(value['rustc_version'],str): raise ValueError('exact compiler identity')
 if not isinstance(value.get('source_members'),list) or not value['source_members']: raise ValueError('closed source member map')
 for name in value['source_members']:
  if not safe_relative(name).startswith(PRODUCER) or not name.endswith('.rs'): raise ValueError('source outside selected Rust closure')
 if entry not in value['source_members']: raise ValueError('entry not in admitted source map')
 return value

def read_root_admission(path,expected_sha):
 # Only the receipt is read before gate(); no candidate path is traversed.
 receipt=Path(path)
 if not receipt.is_absolute(): receipt=ROOT/receipt
 if receipt.parent!=ROOT/'verification/swift-semantic-adapter-root-review': raise ValueError('receipt must be root-owned review metadata')
 raw=receipt.read_bytes()
 if sha(raw)!=expected_sha: raise ValueError('root admission receipt hash')
 return gate(json.loads(raw))

def verify_preparation_and_preaccess(value):
 for seal,expected,allowed in [(HERE/'seal.json',value['reviewer_preparation_sha256'],
   ('verification/swift-cache-state-independent-review/execution-preparation/','docs/swift-cache-state-execution-review-preparation.md')),
  (PRE/'seal.json',PREACCESS_SHA,('verification/swift-cache-state-independent-review/preaccess/','docs/swift-cache-state-implementation-review-plan.md'))]:
  raw=seal.read_bytes()
  if sha(raw)!=expected: raise ValueError('reviewer immutable tooling/input seal')
  data=json.loads(raw); seen=set()
  for m in data['members']:
   name=safe_relative(m['path'])
   if name in seen or not (name.startswith(allowed[0]) or name==allowed[1]): raise ValueError('reviewer closed member map')
   seen.add(name); b=(ROOT/name).read_bytes()
   if sha(b)!=m['sha256'] or len(b)!=m['bytes']: raise ValueError('reviewer/input member changed')
  if len(seen)!=data['member_count'] or sum(m['bytes'] for m in data['members'])!=data['member_bytes']: raise ValueError('reviewer seal totals')

def stage_candidate(admission,work):
 value=gate(admission)
 verify_preparation_and_preaccess(value)
 raw=(ROOT/value['candidate_seal']).read_bytes()
 if sha(raw)!=value['candidate_seal_sha256']: raise ValueError('candidate seal binding')
 seal=json.loads(raw); mapping={}
 for m in seal['members']:
  name=safe_relative(m['path'])
  if not (name.startswith(PRODUCER) or name=='docs/swift-cache-state-implementation.md'): raise ValueError('member outside selected closure')
  if name in mapping: raise ValueError('duplicate candidate member')
  p=ROOT/name
  if not stat.S_ISREG(p.lstat().st_mode) or p.is_symlink(): raise ValueError('candidate regular member only')
  cursor=ROOT
  for part in PurePosixPath(name).parts:
   cursor=cursor/part
   if cursor.is_symlink(): raise ValueError('candidate symlink ancestor')
  b=p.read_bytes()
  if len(b)!=m['bytes'] or sha(b)!=m['sha256']: raise ValueError('candidate member mismatch')
  mapping[name]=m
  if name in value['source_members']:
   target=work/'source'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b)
 if set(value['source_members'])-set(mapping): raise ValueError('admitted source absent from seal')
 if len(mapping)!=seal['member_count'] or sum(m['bytes'] for m in mapping.values())!=seal['member_bytes']: raise ValueError('candidate totals')
 compiler=Path(value['rustc'])
 if sha(compiler.read_bytes())!=value['rustc_sha256']: raise ValueError('compiler binary hash')
 write_json(work/'candidate-custody.json',{'candidate_seal_sha256':sha(raw),'members':list(mapping.values()),
  'source_members':value['source_members'],'stage':'exact admitted Rust bytes; no producer model/harness import'})
 driver=work/'public_driver.rs'; driver.write_bytes((HERE/'public_driver.rs').read_bytes())
 return work/'source'/value['crate_entry']

def packed(words): return struct.pack('<'+'Q'*len(words),*words)

def materialize_variant(records,config,profile_rows):
 # Independently encoded here from sealed raw data; no sealed Python imported.
 n=len(records); cap=max(n,1); h=[0]*64
 h[:10]=[0x315244524F58494D,1,512,128,512,cap,80000,64,512,33]
 h[16:32]=list(range(101,117)); foot=[0]*64
 foot[:10]=[0x31444E454F58494D,1,n,n+1,1,n,records[-1][4] if n else 0,
  records[-1][5] if n else 0,max((r[3] for r in records if r[1]==1),default=0),1]
 foot[10:12]=foot[6:8]; foot[14]=(1<<64)-1; foot[15]=33; foot[33]=5; foot[35]=cap; foot[36:44]=h[16:24]
 c=[0]*1024; c[:16]=[int.from_bytes(b'MIXFIX01','little'),1,8192,1,cap,33,config['extent'],config['types'],
  config['slots'],config['pins'],1,config['base'],config['capacity'],config['entry'],0,0]
 c[16:24]=list(range(101,109)); c[40:48]=list(range(109,117))
 p=[0]*64; p[:16]=[int.from_bytes(b'MIXPRF01','little'),1,512,32,80000,config['extent'],config['types'],
  config['slots'],config['pins'],1,config['base'],config['capacity'],config['entry'],0,0,0]
 p[16:24]=c[40:48]; p[28:32]=c[20:24]
 row_default=packed([((1<<32)-1)<<32,(1<<64)-1,0,0]); body=bytearray(row_default*80000)
 for f,row in profile_rows.items():
  i=int(f)*32; body[i:i+32]=packed([1+(row[2]<<32),row[0],row[1],0])
 return packed(h)+b''.join(packed(r) for r in records)+packed(foot),packed(p)+body,packed(c)

def cases(kind,start,count):
 if kind not in ('basics','words','transitions','sequences') or not 0<count<=64 or start<0: raise ValueError('bounded closed case batch')
 names={'basics':'cases.json','words':'word-mutations.json','transitions':'stage-transitions.json','sequences':'sequence-variants.json'}
 data=json.loads((PRE/'fixtures'/names[kind]).read_text())
 selected=data[start:start+count]
 if not selected: raise ValueError('empty selected batch')
 schema=json.loads((PRE/'fixtures/schema.json').read_text())
 for case in selected:
  if kind=='basics':
   payload=[(PRE/'fixtures'/case[k]).read_bytes() for k in ['stream','profile','context']]
  else:
   records=case.get('raw_records',case.get('prefix_records',[])+[case['raw_record']] if 'raw_record' in case else [])
   payload=materialize_variant(records,schema['config'],schema['profile_rows'])
  yield {'id':case['id'],'payload':payload,'expected_words':case['expected_words'],
   'coverage_layer':'public actual-File; no private seeds/snapshot/fault instrumentation'}

def _execute(value,kind,start,count):
 value=gate(value); output=ROOT/value['review_output_directory']
 if output.exists(): raise ValueError('review output already exists; preserve evidence')
 output.mkdir(parents=True); work=output/'work'; work.mkdir()
 entry=stage_candidate(value,work); rustc=value['rustc']; commands=output/'commands'
 version=bounded([rustc,'--version','--verbose'],ROOT,commands,'compiler-version')
 actual=Path(version['stdout']).read_text()
 if version['exit_code']!=0 or actual!=value['rustc_version']: raise ValueError('exact compiler version differs')
 library=work/'libmixer_fixture_cache_state.rlib'; driver=work/'public-driver'
 steps=[('library',[rustc,'--edition='+value['edition'],'--crate-name','mixer_fixture_cache_state','--crate-type','rlib',str(entry),'-o',str(library)]),
  ('driver',[rustc,'--edition=2021',str(work/'public_driver.rs'),'--extern','mixer_fixture_cache_state='+str(library),'-o',str(driver)])]
 for name,argv in steps:
  r=bounded(argv,ROOT,commands,name)
  if r['exit_code']!=0 or r['timed_out'] or r['output_truncated']: raise ValueError('compilation failure retained')
 results=[]
 for index,case in enumerate(cases(kind,start,count)):
  directory=output/'cases'/f'{index:02}-{case["id"]}'; directory.mkdir(parents=True)
  paths=[]; before=[]
  for name,b in zip(['stream','profile','context'],case['payload']):
   p=directory/(name+'.bin'); p.write_bytes(b); paths.append(p); before.append(sha(b))
  report=directory/'report.bin'
  run=bounded([str(driver),*[str(p) for p in paths],str(report)],ROOT,directory,'driver')
  failures=[]; diagnostic=None
  if run['exit_code']!=0 or run['timed_out'] or run['output_truncated']: failures.append('driver/harness execution failure')
  else:
   try:
    diagnostic=protocol(Path(run['stdout']).read_bytes())
    failures+=compare_public(diagnostic,case['expected_words'],report.read_bytes(),case['payload'][2],case['payload'][0])
   except (ValueError,OSError) as problem: failures.append('driver/report protocol error: '+str(problem)[:256])
  after=[sha(p.read_bytes()) for p in paths]
  if before!=after: failures.append('input bytes changed')
  item={'case':case['id'],'expected_words':case['expected_words'],'diagnostic':diagnostic,
   'input_sha256_before':before,'input_sha256_after':after,'report_sha256':sha(report.read_bytes()) if report.exists() else None,
   'failures':failures,'layer':case['coverage_layer'],'actual_candidate_executed':True}
  write_json(directory/'result.json',item); results.append(item)
 write_json(output/'public-summary.json',{'candidate_seal_sha256':value['candidate_seal_sha256'],
  'case_set':kind,'start':start,'count':len(results),'failures':sum(bool(r['failures']) for r in results),
  'private_candidate_controls':0,'source_proof_accepted':False,'GA_qualified':False,
  'scope':'public actual-File finite execution only; independent private/source/debit/lifetime gates remain separate'})
 # Retain compiler/driver binaries as exact bounded review evidence. There are
 # no running owned children here; cleanup/disposal requires a later scoped task.
 return output

def execute(value,kind,start,count):
 value=gate(value)
 if kind not in ('basics','words','transitions','sequences') or not 0<count<=64 or start<0: raise ValueError('bounded closed case batch')
 already_present=(ROOT/value['review_output_directory']).exists()
 try: return _execute(value,kind,start,count)
 except Exception as problem:
  output=ROOT/value['review_output_directory']
  if not already_present and output.exists(): write_json(output/'preparation-or-execution-failure.json',{
   'type':type(problem).__name__,'message':str(problem)[:1024],
   'candidate_seal_sha256':value['candidate_seal_sha256'],
   'candidate_execution_count':'consult retained command/case receipts; unrun cases remain pending',
   'cleanup':'bounded runner joins/kills only its sole owned process group; evidence retained'})
  raise

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--admission',required=True); parser.add_argument('--admission-sha256',required=True)
 parser.add_argument('--case-set',choices=['basics','words','transitions','sequences'],default='basics')
 parser.add_argument('--start',type=int,default=0); parser.add_argument('--count',type=int,default=39)
 args=parser.parse_args(); value=read_root_admission(args.admission,args.admission_sha256)
 print(execute(value,args.case_set,args.start,args.count))

if __name__=='__main__': main()
