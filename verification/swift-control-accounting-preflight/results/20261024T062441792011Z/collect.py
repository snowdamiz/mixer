#!/usr/bin/env python3
"""Host-only source/layout/MIR preflight; no control algorithm is invoked."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,tarfile,difflib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('builder',HERE/'build_overlay.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
spec=importlib.util.spec_from_file_location('inventory',HERE/'inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');OUT=HERE/'results'/STAMP;BUILD=Path('/tmp')/('mixer-control-preflight-'+STAMP);OUT.mkdir(parents=True);BUILD.mkdir(parents=True)
enc=builder.enc;sha=builder.sha;digest=lambda x:hashlib.sha256(enc(x)).hexdigest();commands=[];layouts=[];mir_inventory=[];status='failed-preflight';BASE=builder.files(ROOT/'vm');assert digest(BASE)=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
def save(name,x):(OUT/name).write_bytes(enc(x))
def closure(path):return builder.files(path)
def copy_vm(dest,label):
 for name in BASE:
  d=dest/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'vm'/name,d)
 if label=='candidate':
  for p in (HERE/'overlay').rglob('*'):
   if p.is_file():d=dest/p.relative_to(HERE/'overlay');d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
 return closure(dest)
def run(name,args,cwd=ROOT,target=None,source=None,extra=None,allowed=False):
 assert closure(ROOT/'vm')==BASE,('live drift',name)
 if source:assert closure(cwd)==source,('overlay drift before',name)
 used=dict(env)
 if target:used['CARGO_TARGET_DIR']=str(target)
 if extra:used.update(extra)
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=cwd,env=used,capture_output=True,timeout=600)
 for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
 commands.append(dict(name=name,argv=args,cwd=str(cwd),target=str(target) if target else None,startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,extraEnvironment=extra or {},sourceTreeSHA256=digest(source) if source else None,baselineTreeSHA256=digest(BASE),stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))))
 print(name,p.returncode,flush=True)
 if source:assert closure(cwd)==source,('overlay drift after',name)
 assert closure(ROOT/'vm')==BASE,('live drift after',name)
 if p.returncode and not allowed:raise RuntimeError((name,p.stderr.decode(errors='replace')[-9000:]))
 return p.stdout.decode(errors='replace'),p.stderr.decode(errors='replace'),p.returncode

def archive(label,vm,source):
 save(label+'-manifest.json',source)
 with tarfile.open(OUT/(label+'-source.tar.gz'),'w:gz') as t:
  for name in source:t.add(vm/name,arcname='vm/'+name,recursive=False)

def literal_function(text,name):return builder.method(text[text.index('impl SpanInstance {'):],name)

def metadata_source(vm,label):
 frame=vm/'src/experimental_swift_reactor/frame_operations.rs'
 common=['pub(crate) fn accounting_preflight_metadata(){']
 if label=='candidate':common+=['let _: fn(&mut FrameOperationPhase<\'static>, Operation, Option<u32>) -> Result<bool, SwiftRunFailure> = FrameOperationPhase::control_operation;']
 named={'Control':'Control','SwiftFrame':'SwiftFrame','FrameOperationPhase':"FrameOperationPhase<'static>",'FrameOperationStorage':"FrameOperationStorage<'static>",'CompletionDropTuple':"(ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>)",'Preparation':"Option<Result<FrameOperationPhase<'static>, SwiftRunFailure>>",'Controlled':"Option<Result<bool, SwiftRunFailure>>",'Failure':'SwiftRunFailure','PermanentPositions':'PermanentPositions','ActivePositions':'ActivePositions','ImplementationPermanentPositions':'ImplementationPermanentPositions','ImplementationActivePositions':'ImplementationActivePositions'}
 for name,ty in named.items():common.append(f'println!("CPI_TYPE {name} {{}} {{}}", size_of::<{ty}>(), std::mem::align_of::<{ty}>());')
 for name,expr in {'frame_permanent':'PERMANENT_BYTES','frame_active':'ACTIVE_BYTES','frame_bound':'FRAME_OPERATION_BYTES.unwrap()','value_bound':'value_operations::VALUE_OPERATION_BYTES.unwrap()','header':'execution_header_bytes().unwrap()','construction':'construction_bytes().unwrap()','default_combined':'SwiftRunBudget::default().combined_bytes'}.items():common.append(f'println!("CPI_TOTAL {name} {{}}", {expr});')
 existing=[]
 for schema,classes in [('verification/swift-active-frame-contract/inventory-schema.json',{'permanent':'PermanentPositions','active':'ActivePositions'}),('verification/swift-active-frames-implementation/implementation-inventory-schema.json',{'permanent':'ImplementationPermanentPositions','active':'ImplementationActivePositions'})]:
  p=ROOT/schema
  if not p.exists():continue
  for row in json.loads(p.read_text()):
   if 'FrameOperationStorage' not in row['rustType']:continue
   cls=classes[row['envelope']];prefix='#[cfg(test)] ' if row.get('config')=='unit' else ''
   common.append(prefix+f'println!("CPI_CONTAINING {cls}.{row["field"]} {{}} {{}}",std::mem::offset_of!({cls},{row["field"]}),size_of::<{row["rustType"]}>());')
   existing.append(dict(row,ownerClass=cls))
 common+=['}']
 if label=='candidate':common[-2:-2]=['control_operations::accounting_layout_metadata();']
 common+=['#[cfg(test)] #[test] fn control_accounting_preflight_metadata_only(){accounting_preflight_metadata();}']
 frame.write_text(frame.read_text()+'\n'+'\n'.join(common)+'\n')
 # Production calls the same metadata function through an instrumented route.
 m=vm/'src/experimental_swift_reactor/mod.rs';m.write_text(m.read_text()+'\npub(crate) fn accounting_preflight_route(){execution::frame_operations::accounting_preflight_metadata();}\n')
 l=vm/'src/lib.rs';l.write_text(l.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn accounting_preflight_route(){experimental_swift_reactor::accounting_preflight_route();}\n')
 (vm/'src/bin').mkdir(exist_ok=True);(vm/'src/bin/control_accounting_layout.rs').write_text('fn main(){mixer_vm::accounting_preflight_route();}\n')
 # Frozen header formula is measured directly in its own private owner module.
 owner=vm/'src/experimental/execution/mod.rs';frozen='''
#[cfg(feature="experimental-span-execution")]
pub(crate) fn frozen_accounting_metadata(){
 println!("CPI_TOTAL frozen_header {}",size_of::<SpanInstance>()-size_of::<FunctionCache>()+3*size_of::<ExecutionFailure>()+2*size_of::<CacheFailure>()+size_of::<super::cache::DecodedInstruction>()+size_of::<Control>()+size_of::<ScalarReader<'_>>()+512);
}
'''
 owner.write_text(owner.read_text()+frozen)
 # Append after earlier function; route is scalar/layout only.
 frame.write_text(frame.read_text().replace('pub(crate) fn accounting_preflight_metadata(){','pub(crate) fn accounting_preflight_metadata(){\n#[cfg(feature="experimental-span-execution")] crate::experimental::execution::frozen_accounting_metadata();',1))
 if label=='candidate':
  rows=json.loads((HERE/'inventory-schema.json').read_text());groups={};code=['pub(super) fn accounting_layout_metadata(){']
  for row in rows:
   groups.setdefault(row['ownerClass'],[]).append(row)
  owner_code=['#[cfg(feature="experimental-swift-reactor")] pub(crate) fn private_accounting_layout_metadata(){']
  for cls,group in groups.items():
   private='SwiftControlPrivatePositions' in cls;target=owner_code if private else code
   target.append(f'println!("CPI_CLASS {cls} {{}} {{}}", std::mem::size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
   for row in group:
    prefix='#[cfg(test)] ' if row.get('config')=='unit' else ''
    target.append(prefix+f'println!("CPI_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({cls},{row["field"]}),std::mem::size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
  code+=['crate::experimental::execution::private_accounting_layout_metadata();','println!("CPI_TOTAL new_permanent {}",PERMANENT_BYTES);','println!("CPI_TOTAL new_active {}",ACTIVE_BYTES);','}'];owner_code+=['}']
  child=vm/'src/experimental_swift_reactor/control_operations.rs';child.write_text(child.read_text()+'\n'+'\n'.join(code)+'\n');owner.write_text(owner.read_text()+'\n'+'\n'.join(owner_code)+'\n')
 return existing

def parse_layout(output):
 fields={};classes={};types={};totals={};containing={}
 for line in output.splitlines():
  at=line.find('CPI_')
  if at<0:continue
  parts=line[at:].split();kind,name=parts[:2];values=list(map(int,parts[2:]))
  if kind=='CPI_FIELD':assert name not in fields;fields[name]=dict(offset=values[0],bytes=values[1],alignment=values[2])
  elif kind=='CPI_CLASS':classes[name]=dict(bytes=values[0],alignment=values[1])
  elif kind=='CPI_TYPE':types[name]=dict(bytes=values[0],alignment=values[1])
  elif kind=='CPI_TOTAL':totals[name]=values[0]
  elif kind=='CPI_CONTAINING':containing[name]=dict(offset=values[0],bytes=values[1])
 return dict(fields=fields,classes=classes,types=types,totals=totals,containing=containing)

try:
 for name,args in [('revision',['git','rev-parse','HEAD']),('rustc-version',['rustc','-vV']),('cargo-version',['cargo','-V']),('rustfmt-version',['rustfmt','--version']),('python-version',['python3','--version']),('host',['uname','-a'])]:run(name,args)
 for file in ['collect.py','build_overlay.py','inventory.py','inventory-schema.json','function-manifest.json','production.mir','unit.mir','changed-files.json']:
  shutil.copyfile(HERE/file,OUT/file)
 sources={}
 for label in ['baseline','candidate']:
  vm=BUILD/label/'vm';src=copy_vm(vm,label);sources[label]=(vm,src);archive(label,vm,src)
 candidate,csrc=sources['candidate'];assert csrc==json.loads((HERE/'candidate-manifest.json').read_text())
 run('candidate-format',['cargo','fmt','--all','--','--check'],candidate,source=csrc)
 for config,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:run(config+('-release' if release else '-debug')+'-check',['cargo','check','--locked','--offline','--lib',*flags,*(['--release'] if release else [])],candidate,BUILD/'check-target',csrc)
 # Compiler-expanded equality covers source call boundaries/work order, not only tokens.
 expansions={}
 for label,(vm,src) in sources.items():
  output,_,_=run(label+'-expanded',['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],vm,BUILD/(label+'-expanded-target'),src,{'RUSTC_BOOTSTRAP':'1'})
  expansions[label]={name:literal_function(output,name) for name in ['pop32','close_control','branch','run']};save(label+'-frozen-bodies.json',expansions[label])
 assert expansions['baseline']==expansions['candidate'];save('frozen-identity.json',{name:dict(identical=True,sha256=hashlib.sha256(body.encode()).hexdigest()) for name,body in expansions['candidate'].items()})
 # Actual uninstrumented source MIR in all feature/profile and production/unit combinations.
 for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   for unit in [False,True]:
    name=config+('-release' if release else '-debug')+('-unit' if unit else '-production');target=BUILD/(name+'-mir-target')
    args=['cargo','test','--lib','--no-run','--locked','--offline',*flags,*(['--release'] if release else [])] if unit else ['cargo','rustc','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'--','--emit=mir','-Zmir-include-spans=yes']
    extra={'RUSTC_BOOTSTRAP':'1'}
    if unit:extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
    run(name+'-mir',args,candidate,target,csrc,extra)
    profile='release' if release else 'debug';paths=list((target/profile/'deps').glob('*.mir'))
    chosen=[p for p in paths if ('control_operations::' in p.read_text()) and (('::af01_real_nested_recursive_entry_and_parameter_ownership(' in p.read_text())==unit)]
    assert len(chosen)==1,(name,paths)
    dest=OUT/(name+'.mir');shutil.copyfile(chosen[0],dest)
    rows,functions=inv.inventory(dest,name.replace('-','_'));save(name+'-mir-inventory.json',dict(rows=rows,functions=functions))
    mir_inventory.append(dict(config=config,profile=profile,unit=unit,path=dest.name,sha256=sha(dest),rows=len(rows),functions=len(functions)))
 # Metadata copies bind to production source archives plus explicit instrumentation.
 for label,(vm,src) in sources.items():
  meta=BUILD/(label+'-metadata')/'vm';shutil.copytree(vm,meta);existing=metadata_source(meta,label);msrc=closure(meta);archive(label+'-metadata',meta,msrc)
  if label=='candidate':save('enlarged-existing-containing-rows.json',existing)
  for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
   for release in [False,True]:
    for unit in [False,True]:
     name=label+'-'+config+('-release' if release else '-debug')+('-unit' if unit else '-production');target=BUILD/'metadata-target'/label
     args=['cargo','test','--lib',*flags,*(['--release'] if release else []),'control_accounting_preflight_metadata_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--bin','control_accounting_layout',*flags,*(['--release'] if release else [])]
     output,_,_=run(name+'-metadata',args,meta,target,msrc)
     layout=parse_layout(output);assert layout['types']['Controlled']['bytes']==1096
     if config=='all':assert layout['totals']['frozen_header']==2912
     if label=='candidate':
      expected=[r for r in json.loads((HERE/'inventory-schema.json').read_text()) if unit or r.get('config')!='unit'];assert set(layout['fields'])=={r['field'] for r in expected}
      seen={}
      for row in sorted(expected,key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
       field=layout['fields'][row['field']];cls=row['ownerClass'];assert field['offset']%field['alignment']==0;assert field['offset']+field['bytes']<=layout['classes'][cls]['bytes']
       if field['bytes']:assert field['offset']>=seen.get(cls,0);seen[cls]=field['offset']+field['bytes']
      assert layout['totals']['new_permanent']==layout['classes']['PermanentPositions']['bytes']
      assert layout['totals']['new_active']==layout['classes']['ActivePositions']['bytes']
      assert layout['totals']['frame_bound']==layout['totals']['frame_active']+layout['totals']['value_bound']+layout['totals']['new_active']
     layouts.append(dict(label=label,config=config,profile='release' if release else 'debug',unit=unit,sourceTreeSHA256=digest(msrc),**layout))
 save('layouts.json',layouts)
 comparisons=[]
 for config in ['swift','all']:
  for profile in ['debug','release']:
   for unit in [False,True]:
    b=next(x for x in layouts if (x['label'],x['config'],x['profile'],x['unit'])==('baseline',config,profile,unit));c=next(x for x in layouts if (x['label'],x['config'],x['profile'],x['unit'])==('candidate',config,profile,unit))
    assert c['types']['FrameOperationStorage']['bytes']-b['types']['FrameOperationStorage']['bytes']==1096
    assert c['totals']['default_combined']==b['totals']['default_combined']
    header_delta=c['totals']['header']-b['totals']['header'];frame_perm_delta=c['totals']['frame_permanent']-b['totals']['frame_permanent'];frame_active_delta=c['totals']['frame_active']-b['totals']['frame_active']
    assert header_delta==frame_perm_delta+c['totals']['new_permanent']
    assert c['totals']['frame_bound']-b['totals']['frame_bound']==frame_active_delta+c['totals']['new_active']
    comparisons.append(dict(config=config,profile=profile,unit=unit,storageDelta=1096,headerDelta=header_delta,existingPermanentDelta=frame_perm_delta,existingActiveDelta=frame_active_delta,newPermanent=c['totals']['new_permanent'],newActive=c['totals']['new_active'],exactHeader=c['totals']['header'],exactFrameBound=c['totals']['frame_bound'],headerBoundaryBelow=c['totals']['header']-1,headerBoundaryAt=c['totals']['header'],phaseBoundaryBelow=c['totals']['construction']+c['totals']['frame_bound']-1,phaseBoundaryAt=c['totals']['construction']+c['totals']['frame_bound'],ceilingUnchanged=True))
 save('baseline-comparisons.json',comparisons)
 status='passed-actual-source-metadata-preflight-pending-root-accounting-review-and-control-execution'
finally:
 save('receipt.json',dict(schema=1,status=status,sourceRevision=(OUT/'revision.stdout').read_text().strip() if (OUT/'revision.stdout').exists() else None,baselineTreeSHA256=digest(BASE),candidateTreeSHA256=digest(sources['candidate'][1]) if 'sources' in globals() and 'candidate' in sources else None,commands=commands,mirInventory=mir_inventory,layouts='layouts.json' if (OUT/'layouts.json').exists() else None,liveVMUnchanged=closure(ROOT/'vm')==BASE,controlMethodsExecuted=False,sc01Through12Passed=False,accountingAccepted=False,implementationAccepted=False,nativeRuntime=False,physicalRuntime=False,gaAcceptance=False))
 # Keep only compact immutable source and diagnostic evidence, not build trees.
 shutil.rmtree(BUILD)
 save('cleanup.json',dict(ownedBuildScratch=str(BUILD),removed=not BUILD.exists(),nativeInstancesStarted=False,otherProjectProcessesTouched=False))
 print(OUT/'receipt.json',flush=True)
