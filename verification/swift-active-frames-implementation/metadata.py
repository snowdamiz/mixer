#!/usr/bin/env python3
"""Exact archived-source typed-MIR replay and compiled field offsets; host only."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
FREEZE=HERE/'source-freeze'
if (FREEZE/'latest.json').exists():FREEZE=FREEZE/json.loads((FREEZE/'latest.json').read_text())['directory']
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');OUT=HERE/'metadata'/STAMP;BUILD=HERE/'build'/('metadata-'+STAMP);OUT.mkdir(parents=True);BUILD.mkdir(parents=True)
encoded=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(encoded(x)).hexdigest()
def manifest(path):return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
ENV=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);ENV.pop('RUSTC_BOOTSTRAP',None);ENV.pop('RUSTFLAGS',None)
COMMANDS=[];LAYOUTS=[];ARTIFACTS=[];VARIANTS=[];MIR=[];status='failed-metadata-replay'
def save(name,x):(OUT/name).write_bytes(encoded(x))
def command(name,args,cwd,target,closure=None,extra=None):
 if closure is not None:assert manifest(cwd)==closure
 env=dict(ENV,CARGO_TARGET_DIR=str(target));env.update(extra or {})
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,timeout=1200)
 for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
 if closure is not None:assert manifest(cwd)==closure
 COMMANDS.append(dict(name=name,argv=args,cwd=str(cwd),target=str(target),exitCode=p.returncode,sourceTreeSHA256=digest(closure) if closure else None,extraEnvironment=extra or {},stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))));print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-5000:])
 return p.stdout.decode(errors='replace')
def extract(label):
 path=BUILD/label
 with tarfile.open(FREEZE/'candidate-source.tar.gz') as t:t.extractall(path,filter='data')
 return path/'vm'
try:
 shutil.copyfile(HERE/'inventory.py',OUT/'inventory.py')
 spec=importlib.util.spec_from_file_location('inventory',HERE/'inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
 for config,extra,args in [('production',{},['cargo','rustc','--locked','--offline','--lib','--features','experimental-swift-reactor','--','--emit=mir']),('unit',{'RUSTFLAGS':'--emit=mir,link'},['cargo','test','--locked','--offline','--lib','--features','experimental-swift-reactor','--no-run'])]:
  vm=extract('mir-'+config);closure=manifest(vm);target=BUILD/('mir-'+config+'-target');command('mir-'+config,args,vm,target,closure,extra)
  paths=list(target.rglob('*.mir'));assert len(paths)==1,(config,paths);shutil.copyfile(paths[0],OUT/(config+'.mir'))
  actual=inv.typed_rows(paths[0],config);saved=[row for row in json.loads((HERE/'implementation-inventory-schema.json').read_text()) if row['config']==config and row['field'].startswith('mir_')]
  # Global emitted-MIR line numbers shift when unrelated preceding CTFE
  # blocks change length. Exact function/local/source-name/type/capture roles
  # must match; retain fresh global line locations separately for lookup.
  comparable=lambda rows:[{k:v for k,v in row.items() if k!='mirLine'} for row in rows]
  assert comparable(actual)==comparable(saved),(config,'typed source/return/capture position drift')
  save(config+'-typed-roles.json',actual)
  MIR.append(dict(config=config,path=config+'.mir',sha256=sha(OUT/(config+'.mir')),positions=len(actual),exactSavedTypedRolesEqual=True,sourceTreeSHA256=digest(closure)))
 # Uncalled metadata-only helper lives in separate derived source. Complete
 # concrete field offsets/types are generated as a const table, not one opaque
 # total or a layout alias. Every unit-only row keeps its cfg lifetime.
 rows=[]
 for row in json.loads((HERE/'frozen-inventory-schema.json').read_text()):
  rows.append(dict(row,config='frozen',owner='PermanentPositions' if row['envelope']=='permanent' else 'ActivePositions'))
 for row in json.loads((HERE/'implementation-inventory-schema.json').read_text()):
  rows.append(dict(row,owner='ImplementationPermanentPositions' if row['envelope']=='permanent' else 'ImplementationActivePositions'))
 probe=['pub(super) fn af_layout_probe() {','const ROWS: &[(&str, &str, usize, usize, usize)] = &[']
 for row in rows:
  if row['config']=='unit':probe.append('#[cfg(test)]')
  probe.append('("'+row['owner']+'", "'+row['field']+'", std::mem::offset_of!('+row['owner']+', '+row['field']+'), size_of::<'+row['rustType']+'>(), std::mem::align_of::<'+row['rustType']+'>()),')
 probe+= ['];','for (owner,field,offset,size,align) in ROWS {println!("AF_FIELD|{}|{}|{}|{}|{}",owner,field,offset,size,align);}',
 'println!("AF_BOUNDS|{}|{}|{}|{}|{}|{}|{}|{}|{}",FROZEN_PERMANENT_BYTES,FROZEN_ACTIVE_BYTES,PERMANENT_BYTES,ACTIVE_BYTES,FRAME_OPERATION_BYTES.unwrap(),value_operations::VALUE_OPERATION_BYTES.unwrap(),execution_header_bytes().unwrap(),construction_bytes().unwrap(),size_of::<SwiftExecutionState>());',
 'println!("AF_SIZES|{}|{}|{}|{}",size_of::<PermanentPositions>(),size_of::<ActivePositions>(),size_of::<ImplementationPermanentPositions>(),size_of::<ImplementationActivePositions>());',
 'println!("AF_STATE|{}|{}|{}|{}",std::mem::offset_of!(SwiftExecutionState,frame_cleanup),size_of::<FrameCleanupState>(),size_of::<SwiftReactorInstance>(),size_of::<EntryGuard>());','}']
 (OUT/'layout-probe.rs.txt').write_text('\n'.join(probe)+'\n')
 vm=extract('layout');p=vm/'src/experimental_swift_reactor/frame_operations.rs';p.write_text(p.read_text()+'\n'+(OUT/'layout-probe.rs.txt').read_text())
 p=vm/'src/experimental_swift_reactor/execution.rs';p.write_text(p.read_text()+'\npub(super) fn af_layout_probe(){frame_operations::af_layout_probe();}\n#[cfg(test)] #[test] fn af_layout_only(){frame_operations::af_layout_probe();}\n')
 p=vm/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn af_layout_probe(){execution::af_layout_probe();}\n')
 p=vm/'src/lib.rs';p.write_text(p.read_text()+'\npub fn af_layout_probe(){experimental_swift_reactor::af_layout_probe();}\n')
 (vm/'examples').mkdir(exist_ok=True);(vm/'examples/af-layout.rs').write_text('fn main(){mixer_vm::af_layout_probe();}\n')
 closure=manifest(vm);save('layout-source-manifest.json',closure)
 with tarfile.open(OUT/'layout-source.tar.gz','w:gz') as t:
  for name in closure:t.add(vm/name,arcname='vm/'+name,recursive=False)
 VARIANTS.append(dict(label='layout',sourceTreeSHA256=digest(closure),archive='layout-source.tar.gz',archiveSHA256=sha(OUT/'layout-source.tar.gz')))
 for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   for mode in ['production','unit']:
    name=feature+('-release' if release else '-debug')+'-'+mode;target=BUILD/(name+'-target')
    args=['cargo','build' if mode=='production' else 'test','--locked','--offline','--message-format=json',*flags,*(['--release'] if release else []),*(['--example','af-layout'] if mode=='production' else ['--lib','--no-run'])]
    output=command(name+'-build',args,vm,target,closure);binaries=[]
    for line in output.splitlines():
     try:item=json.loads(line)
     except ValueError:continue
     if item.get('reason')=='compiler-artifact' and item.get('executable') and (mode=='production' or item.get('profile',{}).get('test')):binaries.append(Path(item['executable']))
    assert len(binaries)==1,(name,binaries);binary=binaries[0]
    run=command(name+'-run',[str(binary),*(['experimental_swift_reactor::execution::af_layout_only','--exact','--nocapture','--test-threads=1'] if mode=='unit' else [])],vm,target,closure)
    records=[]
    for line in run.splitlines():
     at=line.find('AF_')
     if at>=0:records.append(line[at:])
    assert len([v for v in records if v.startswith('AF_FIELD|')])==len([r for r in rows if mode=='unit' or r['config']!='unit'])
    fields={};intervals={}
    for row in records:
     if not row.startswith('AF_FIELD|'):continue
     _,owner,field,offset,size,align=row.split('|');offset=int(offset);size=int(size);align=int(align);assert offset%align==0
     assert (owner,field) not in fields;fields[(owner,field)]=(offset,size,align)
     if size:intervals.setdefault(owner,[]).append((offset,offset+size,field))
    for owner,spans in intervals.items():
     ordered=sorted(spans)
     assert all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:])),(name,owner,'overlap')
    LAYOUTS.append(dict(label=name,mode=mode,feature=feature,profile='release' if release else 'debug',binarySHA256=sha(binary),fieldCount=len(fields),records=records))
    ARTIFACTS.append(dict(label=name,path=str(binary),sha256=sha(binary),buildCommand=name+'-build',runCommand=name+'-run'))
 status='passed-exact-typed-mir-and-compiled-positive-layouts-pending-independent-source-completeness-review'
finally:
 save('receipt.json',dict(status=status,sourceFreeze=json.loads((FREEZE/'freeze.json').read_text()),commands=COMMANDS,variants=VARIANTS,typedMIR=MIR,layouts=LAYOUTS,artifacts=ARTIFACTS,hostOnly=True,nativeRuntime=False))
 members=[]
 with tarfile.open(OUT/'qualifying-artifacts.tar.gz','w:gz') as t:
  for item in ARTIFACTS:
   member=item['label']+'-'+Path(item['path']).name;t.add(item['path'],arcname=member,recursive=False);members.append(dict(member=member,sha256=item['sha256'],label=item['label']))
 save('qualifying-artifacts.json',dict(archiveSHA256=sha(OUT/'qualifying-artifacts.tar.gz'),members=members));print(OUT,flush=True)
