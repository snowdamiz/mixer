#!/usr/bin/env python3
"""Compile uncalled candidate2 functions to generate the positive typed map."""
from pathlib import Path
import datetime, hashlib, importlib.util, json, os, shutil, subprocess, tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name):
 spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
b=module('build_overlay');iv=module('inventory');enc=b.enc;sha=b.sha;digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');OUT=HERE/'bootstrap'/stamp;BUILD=Path('/tmp')/('mixer-control-candidate2-bootstrap-'+stamp);vm=BUILD/'vm';OUT.mkdir(parents=True);BUILD.mkdir();base=b.files(ROOT/'vm');commands=[];status='failed';env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],RUSTC_BOOTSTRAP='1');env.pop('RUSTFLAGS',None)
def save(name,x):(OUT/name).write_bytes(enc(x))
def run(name,args,extra=None):
 used=dict(env,CARGO_TARGET_DIR=str(BUILD/name));used.update(extra or {});source=b.files(vm) if vm.exists() else None;start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=vm if vm.exists() else ROOT,env=used,capture_output=True,timeout=600)
 for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
 commands.append(dict(name=name,argv=args,cwd=str(vm if vm.exists() else ROOT),sourceTreeSHA256=digest(source) if source else None,extraEnvironment=extra or {},startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))));save('commands.json',commands);print(name,p.returncode,flush=True);assert p.returncode==0,p.stderr.decode()[-5000:]
try:
 assert digest(base)=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
 for name in base:
  p=vm/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'vm'/name,p)
 for p in (HERE/'overlay').rglob('*'):
  if p.is_file():q=vm/p.relative_to(HERE/'overlay');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 run('rustc-version',['rustc','-vV']);run('cargo-version',['cargo','-V']);run('source-format',['cargo','fmt','--all'])
 save('seed-manifest.json',b.files(vm))
 with tarfile.open(OUT/'seed-source.tar.gz','w:gz') as t:
  for name in b.files(vm):t.add(vm/name,arcname='vm/'+name,recursive=False)
 for config,unit in [('production',False),('unit',True)]:
  args=['cargo','test','--lib','--no-run','--locked','--offline','--features','experimental-swift-reactor'] if unit else ['cargo','rustc','--lib','--locked','--offline','--features','experimental-swift-reactor','--','--emit=mir','-Zmir-include-spans=yes']
  run(config,args,{'RUSTFLAGS':'--emit=mir,link -Zmir-include-spans=yes'} if unit else None)
  paths=list((BUILD/config/'debug/deps').glob('*.mir'));chosen=[p for p in paths if 'control_operations::' in p.read_text() and (('::af01_real_nested_recursive_entry_and_parameter_ownership(' in p.read_text())==unit)];assert len(chosen)==1
  shutil.copyfile(chosen[0],HERE/(config+'.mir'));shutil.copyfile(chosen[0],OUT/(config+'.mir'))
 iv.render(HERE,vm);run('inventory-format',['cargo','fmt','--all'])
 for name in json.loads((HERE/'changed-files.json').read_text()):shutil.copyfile(vm/name,HERE/'overlay'/name)
 (HERE/'baseline-manifest.json').write_bytes(enc(base));(HERE/'candidate-manifest.json').write_bytes(enc(b.files(vm)))
 save('generated-map.json',dict(candidateTreeSHA256=digest(b.files(vm)),fields=len(json.loads((HERE/'inventory-schema.json').read_text())),functions=len(json.loads((HERE/'function-manifest.json').read_text()))))
 status='passed-uncalled-source-and-canonical-map-generation'
finally:
 assert b.files(ROOT/'vm')==base;shutil.rmtree(BUILD);save('receipt.json',dict(status=status,commands=commands,liveVMUnchanged=True,controlMethodsExecuted=False,nativeInstancesStarted=False));save('cleanup.json',dict(ownedScratch=str(BUILD),removed=not BUILD.exists(),nativeInstancesStarted=False,otherProjectProcessesTouched=False))
