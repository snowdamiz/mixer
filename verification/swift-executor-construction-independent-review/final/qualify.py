#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,json,hashlib,re,datetime,difflib
out=Path(__file__).resolve().parent
logs=out/'logs';logs.mkdir(exist_ok=True)
env=dict(os.environ);env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env['CARGO_TARGET_DIR']=str(out/'target')
records=[]
def run(name,args):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();proc=subprocess.run(args,cwd=out/'tree/vm',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log=logs/(name+'.log');log.write_text(proc.stdout)
 tests=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out',proc.stdout)
 item={'name':name,'argv':args,'cwd':'tree/vm','started_utc':started,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':proc.returncode,'output':str(log.relative_to(out)),'output_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'test_results':tests,'wired_bounds':{k:int(v) for k,v in re.findall(r'finalbound\|([^|]+)\|(\d+)',proc.stdout)}}
 records.append(item);(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps({k:item[k]for k in ['name','exit_code','test_results','wired_bounds']}),flush=True)
 if proc.returncode:print(proc.stdout[-5000:]);raise SystemExit(proc.returncode)
 if 'test' in args and (len(tests)!=1 or int(tests[0][1])==0):raise SystemExit('zero or missing test count')
run('rustc-version',['rustc','-Vv']);run('cargo-version',['cargo','-V'])
for label,features in [('minimal','experimental-swift-reactor'),('combined','experimental-swift-reactor,experimental-span-execution')]:
 for profile in ['debug','release']:
  release=[] if profile=='debug' else ['--release']
  for filter_name in ['independent_construction_review_','swift_construction_','swift_executor_layout_','independent_positive_accounting_probe']:
   run(label+'-'+profile+'-'+filter_name,['cargo','test','--locked','--offline','--lib','--features',features,*release,filter_name,'--','--nocapture','--test-threads=1'])
  run(label+'-'+profile+'-production-layout',['cargo','run','--locked','--offline','--features',features,*release,'--example','positive-accounting'])
# Freeze exact derived metadata/test-only differences and manifest after builds.
rows=[];patch=[]
for p in sorted((out/'tree/vm').rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(out/'tree');b=p.read_bytes();rows.append({'path':str(rel),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
 original=out/'inputs'/rel
 if not original.exists() or original.read_bytes()!=b:
  patch.extend(difflib.unified_diff(original.read_text().splitlines(True)if original.exists()else[],b.decode().splitlines(True),fromfile='a/'+str(rel),tofile='b/'+str(rel)))
(out/'derived-manifest.json').write_text(json.dumps({'files':rows,'tree_digest_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()},indent=2)+'\n')
(out/'measurement-test-overlay.patch').write_text(''.join(patch))
