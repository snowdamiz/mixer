from pathlib import Path
import json,hashlib,subprocess,os,shutil,gzip,datetime,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SCRATCH=Path('/tmp/mixer-swift-control-behavior-20261024');VM=SCRATCH/'vm';BASE=SCRATCH/'baseline-vm';OUT=HERE/'source-checks'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');OUT.mkdir(parents=True)
spec=importlib.util.spec_from_file_location('builder',ROOT/'verification/swift-control-accounting-candidate-2/build_overlay.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
if not BASE.exists():
 for name in json.loads((HERE/'baseline-manifest.json').read_text()):
  p=BASE/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'vm'/name,p)
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None);commands=[]
def run(name,args,cwd,extra=None):
 used=dict(env,CARGO_TARGET_DIR=str(SCRATCH/(name.split('-')[0]+'-source-target')))
 if extra:used.update(extra)
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=cwd,env=used,capture_output=True)
 for stream in ['stdout','stderr']:
  with gzip.open(OUT/(name+'.'+stream+'.gz'),'wb') as f:f.write(getattr(p,stream))
 commands.append(dict(name=name,argv=args,cwd=str(cwd),sourceTreeSHA256=hashlib.sha256(builder.enc(builder.files(cwd))).hexdigest() if (cwd/'Cargo.toml').exists() else None,startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,extraEnvironment=extra or {},stdout=name+'.stdout.gz',stderr=name+'.stderr.gz'));(OUT/'commands.json').write_bytes(builder.enc(commands));print(name,p.returncode,flush=True);return p
for label,source in [('baseline',BASE),('candidate',VM)]:
 p=run(label+'-expanded',['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],source,{'RUSTC_BOOTSTRAP':'1'});assert p.returncode==0,p.stderr.decode()[-3000:];expanded=p.stdout.decode();span=expanded[expanded.index('impl SpanInstance {'):];bodies={name:builder.method(span,name) for name in ['pop32','close_control','branch','run']};(OUT/(label+'-frozen-bodies.json')).write_bytes(builder.enc(bodies))
 if label=='baseline':baseline=bodies
 else:assert bodies==baseline
(OUT/'frozen-identity.json').write_bytes(builder.enc({name:dict(identical=True,sha256=hashlib.sha256(body.encode()).hexdigest(),reservationBytes=2912) for name,body in baseline.items()}))
p=run('candidate-library-clippy',['cargo','clippy','--lib','--all-features','--locked','--offline','--','-D','warnings'],VM)
for label,source in [('baseline',BASE),('candidate',VM)]:run(label+'-broad-clippy',['cargo','clippy','--all-targets','--all-features','--keep-going','--message-format=json','--locked','--offline','--','-D','warnings'],source)
for name,args in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('rustfmt',['rustfmt','--version']),('python',['python3','--version']),('host',['uname','-a']),('revision',['git','rev-parse','HEAD'])]:run('tool-'+name,args,ROOT)
print(OUT,flush=True)
