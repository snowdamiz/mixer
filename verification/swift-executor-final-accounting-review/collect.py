from pathlib import Path
import subprocess,os,json,hashlib,time
O=Path(__file__).resolve().parent;T=O/'tree/vm';B=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin');E=dict(os.environ,PATH=str(B)+':'+os.environ['PATH']);L=O/'logs';L.mkdir(exist_ok=True)
R=[]
def run(name,args):
 st=time.monotonic();p=subprocess.run(args,cwd=T,env=E,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);q=L/(name+'.log');q.write_text(p.stdout);R.append({'name':name,'argv':args,'cwd':str(T),'exit_code':p.returncode,'duration_seconds':round(time.monotonic()-st,3),'output':str(q.relative_to(O)),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()});(O/'commands.json').write_text(json.dumps(R,indent=2)+'\n');print(name,p.returncode,flush=True)
 if p.returncode:raise SystemExit(p.stdout)
for n,a in [('rustc-version',[str(B/'rustc'),'-Vv']),('cargo-version',[str(B/'cargo'),'-V']),('host',['uname','-a'])]:run(n,a)
for n,flags in [('debug',[]),('release',['--release'])]:run(n,[str(B/'cargo'),'test','--locked','--manifest-path',str(T/'Cargo.toml'),*flags,'--lib','--features','experimental-swift-reactor','independent_final_accounting_shapes','--','--nocapture','--test-threads=1'])
for n,flags in [('candidate-debug',[]),('candidate-release',['--release'])]:run(n,[str(B/'cargo'),'test','--locked','--manifest-path',str(T/'Cargo.toml'),*flags,'--lib','--features','experimental-swift-reactor','independent_proposed_final_foundation_const_formula','--','--nocapture','--test-threads=1'])
files={str(p.relative_to(T)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(T.rglob('*')) if p.is_file() and 'target' not in p.relative_to(T).parts};(O/'derived-manifest.json').write_text(json.dumps({'files':files,'digest':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()},indent=2)+'\n')
