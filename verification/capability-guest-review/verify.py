#!/usr/bin/env python3
"""Independent tests against a tiny frozen VM export, never a live dependency."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;SCRATCH=ROOT/'.build/capability-guest-review';SOURCE=SCRATCH/'source';HARNESS=SCRATCH/'harness'
parser=argparse.ArgumentParser();parser.add_argument('--revision');parser.add_argument('--preliminary',action='store_true');a=parser.parse_args();assert a.preliminary or a.revision
prefix='preliminary' if a.preliminary else 'frozen'
receipt={'schema':1,'status':'preliminary_not_qualification' if a.preliminary else 'running','reviewed_revision':a.revision,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],'sources':{}}
def sha(b):return hashlib.sha256(b).hexdigest()
if a.revision:
 names=subprocess.check_output(['git','ls-tree','-r','--name-only',a.revision,'--','vm/src','vm/Cargo.toml','vm/Cargo.lock'],cwd=ROOT,text=True).splitlines()
 inputs={p:subprocess.check_output(['git','show',a.revision+':'+p],cwd=ROOT) for p in names}
else:
 paths=[ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']+[p for p in (ROOT/'vm/src').rglob('*') if p.is_file()]
 inputs={str(p.relative_to(ROOT)):p.read_bytes() for p in paths}
 for p,b in inputs.items():assert (ROOT/p).read_bytes()==b,p+' changed while copying'
SOURCE.mkdir(parents=True,exist_ok=True)
for stale in SOURCE.rglob('*'):
 if stale.is_file() and str(stale.relative_to(SOURCE)) not in inputs:
  stale.chmod(0o644);stale.unlink()
for name,data in inputs.items():
 p=SOURCE/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  if p.read_bytes()!=data:p.chmod(0o644);p.write_bytes(data)
 else:p.write_bytes(data)
 p.chmod(0o444);receipt['sources'][name]=sha(data)
manifest=''.join(digest+'  '+p+'\n' for p,digest in sorted(receipt['sources'].items()));(OUT/(prefix+'-source-manifest.sha256')).write_text(manifest);receipt['source_digest']=sha(manifest.encode())
HARNESS.mkdir(parents=True,exist_ok=True);(HARNESS/'tests').mkdir(exist_ok=True);(HARNESS/'tests/adversarial.rs').write_bytes((OUT/'adversarial.rs').read_bytes())
(HARNESS/'Cargo.toml').write_text('[package]\nname="capability-guest-independent-review"\nversion="0.0.0"\nedition="2021"\n[dependencies]\nmixer-vm={path="../source/vm",default-features=false,features=["experimental-capability-guest","experimental-stream-validation"]}\n[profile.release]\noverflow-checks=true\npanic="unwind"\n')
env=dict(os.environ);env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env['CARGO_TARGET_DIR']=str(SCRATCH/'target');env['CARGO_INCREMENTAL']='0';receipt['environment']={x:env[x] for x in ['CARGO_TARGET_DIR','CARGO_INCREMENTAL']};receipt['environment']['PATH_prefix']='/opt/homebrew/opt/rustup/bin';receipt['test_sha256']=sha((OUT/'adversarial.rs').read_bytes());receipt['driver_sha256']=sha(Path(__file__).read_bytes())
receipt_path=OUT/(prefix+'-receipt.json')
def save():receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,args):
 start=time.monotonic();p=subprocess.run(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);path=OUT/(prefix+'-'+name+'.log')
 if path.exists() and path.read_bytes()!=p.stdout:
  n=1
  while path.with_name(path.stem+'.previous-'+str(n)+'.log').exists():n+=1
  path.rename(path.with_name(path.stem+'.previous-'+str(n)+'.log'))
 path.write_bytes(p.stdout);receipt['commands'].append({'name':name,'argv':args,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,6),'log':str(path.relative_to(ROOT)),'log_sha256':sha(p.stdout)});save();print(prefix+'-'+name+': exit '+str(p.returncode),flush=True)
 if p.returncode:print(p.stdout.decode(errors='replace')[-16000:],flush=True);raise SystemExit(p.returncode)
for name,args in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('host',['uname','-a'])]:run('version-'+name,args)
run('format',['rustfmt','--edition','2021','--check',str(OUT/'adversarial.rs')])
run('debug',['cargo','test','--manifest-path',str(HARNESS/'Cargo.toml'),'--test','adversarial','--','--nocapture','--test-threads=1'])
if not a.preliminary:
 run('release',['cargo','test','--release','--manifest-path',str(HARNESS/'Cargo.toml'),'--test','adversarial','--','--nocapture','--test-threads=1'])
 run('clippy',['cargo','clippy','--manifest-path',str(HARNESS/'Cargo.toml'),'--all-targets','--','-D','warnings'])
for name,digest in receipt['sources'].items():assert sha((SOURCE/name).read_bytes())==digest,name
assert {str(p.relative_to(SOURCE)) for p in SOURCE.rglob('*') if p.is_file()}==set(inputs)
assert sha((OUT/'adversarial.rs').read_bytes())==receipt['test_sha256']
receipt['frozen_export_unchanged']=True;receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['status']='preliminary_pass_not_qualification' if a.preliminary else 'independent_frozen_tests_passed';save()
