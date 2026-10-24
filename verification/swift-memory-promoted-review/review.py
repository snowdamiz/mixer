#!/usr/bin/env python3
"""Independent, bounded host review. Writes only this packet and owned scratch."""
from pathlib import Path
import collections, datetime, gzip, hashlib, json, os, re, shutil, subprocess, tarfile, tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-memory-promoted-correction'
enc=lambda obj:(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
digest=lambda obj:hashlib.sha256(enc(obj)).hexdigest()
read=lambda name:json.loads((HERE/name).read_text())

def manifest(root):
 return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and not any(x in {'target','.git','__pycache__'} for x in p.relative_to(root).parts)}

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def run(name,args,source=None,extra=None):
 session=read('session.json');scratch=Path(session['scratch'])
 out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
 for key in ['RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_TARGET_DIR']:env.pop(key,None)
 if source:env['CARGO_TARGET_DIR']=str(scratch/('target-'+source.parent.name))
 if extra:env.update(extra)
 before=manifest(source) if source else None
 if before:(out/'source-manifest.json').write_bytes(enc(before))
 started=now();p=subprocess.run(args,cwd=source or ROOT,env=env,capture_output=True,timeout=900)
 for stream in ['stdout','stderr']:(out/(stream+'.gz')).write_bytes(gzip.compress(getattr(p,stream),mtime=0))
 binaries=[]
 for namepath in re.findall(r'Running[^\n]*\((/[^)]+)\)',p.stderr.decode(errors='replace')):
  path=Path(namepath)
  if path.is_file() and os.access(path,os.X_OK):binaries.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size))
 record=dict(argv=args,cwd=str(source or ROOT),startedUTC=started,completedUTC=now(),environment={k:env[k] for k in ['PATH','PYTHONDONTWRITEBYTECODE','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP'] if k in env},exitCode=p.returncode,sourceClosure=digest(before) if before else None,sourceUnchanged=before==manifest(source) if source else True,executables=binaries,stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),stderrSHA256=hashlib.sha256(p.stderr).hexdigest())
 (out/'receipt.json').write_bytes(enc(record));print(name,p.returncode,flush=True)
 if p.returncode:print(p.stderr.decode(errors='replace')[-6000:],flush=True)
 assert record['sourceUnchanged'];return p

def extract(path,destination):
 destination.mkdir(parents=True,exist_ok=False)
 with tarfile.open(path) as t:
  for m in t.getmembers():
   assert m.isfile() and m.name.startswith('vm/') and '..' not in Path(m.name).parts
   path=destination/m.name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(t.extractfile(m).read())
 return destination/'vm'

def freeze_source(label,root):
 m=manifest(root);(HERE/(label+'-source-manifest.json')).write_bytes(enc(m))
 with tarfile.open(HERE/(label+'-source.tar.gz'),'w:gz') as t:
  for p in sorted(root.rglob('*')):
   if p.is_file() and str(p.relative_to(root)) in m:t.add(p,arcname='vm/'+str(p.relative_to(root)))
 return digest(m)

def setup():
 assert not (HERE/'session.json').exists()
 scratch=Path(tempfile.mkdtemp(prefix='mixer-promoted-independent-review-'))
 (HERE/'session.json').write_bytes(enc(dict(startedUTC=now(),scratch=str(scratch),liveVMEdited=False,native=False,physical=False)))
 shutil.copytree(PRODUCER,HERE/'inputs/producer')
 for name in ['AGENTS.md','docs/swift-memory-promoted-accounting-direction.md','docs/swift-memory-promoted-correction.md','docs/swift-memory-helper-behavior-review.md']:
  target=HERE/'inputs'/Path(name).name;target.write_bytes((ROOT/name).read_bytes())
 for label in ['behavior','candidate']:
  vm=extract(HERE/'inputs/producer'/(label+'-source.tar.gz'),scratch/label)
  assert manifest(vm)==read('inputs/producer/'+label+'-source-manifest.json')
  probe=scratch/('probe-'+label)/'vm';shutil.copytree(vm,probe)
  schema=read('inputs/producer/inventory-schema.json');old=read('inputs/producer/inputs/behavior-inventory-schema.json');oldnames={r['field'] for r in old};added=[r for r in schema if r['field'] not in oldnames]
  code=['#[cfg(test)]','#[test]','fn independent_promoted_review_layout() {',' println!("PR_CLASS active {} {}",size_of::<ActivePositions>(),std::mem::align_of::<ActivePositions>());',' println!("PR_TOTAL active {}",ACTIVE_BYTES);',' println!("PR_TOTAL permanent {}",PERMANENT_BYTES);',' println!("PR_TOTAL frame {}",super::FRAME_OPERATION_BYTES.unwrap());']
  for binding,ty in [('_0',"&'static std::thread::LocalKey<std::cell::Cell<bool>>"),('_1','std::thread::LocalKey<std::cell::Cell<bool>>')]:code.append(f' println!("PR_TYPE {binding} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
  if label=='candidate':
   for r in added:
    # Take an actual field reference as its exact normalized type. This type
    # check is compiler-owned and cannot be met by an equal-sized stand-in.
    code+=[' {',f'  fn typed(value: &ActivePositions) -> &{r["rustType"]} {{ &value.{r["field"]} }}',f'  let _: fn(&ActivePositions) -> &{r["rustType"]} = typed;',f'  println!("PR_FIELD {r["field"]} {{}} {{}} {{}}",std::mem::offset_of!(ActivePositions,{r["field"]}),size_of::<{r["rustType"]}>(),std::mem::align_of::<{r["rustType"]}>());',' }']
  code+=['}'];path=probe/'src/experimental_swift_reactor/memory_operations.rs';path.write_text(path.read_text()+'\n'+'\n'.join(code)+'\n')
  freeze_source('probe-'+label,probe)
 for name,args in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('python',['python3','--version']),('host',['uname','-a']),('revision',['git','rev-parse','HEAD'])]:assert run('tool-'+name,args).returncode==0
 assert run('producer-checker',['python3','-B',str(PRODUCER/'verify.py'),'--live-baseline']).returncode==0
 assert run('collector-regression',['python3','-B',str(PRODUCER/'collector_regression.py')]).returncode==0
 print('setup complete',flush=True)

if __name__=='__main__':setup()
