#!/usr/bin/env python3
"""Independent, host-only prerequisite collector. No interpreter entry is called."""
import concurrent.futures,datetime,gzip,hashlib,json,os,pathlib,re,shutil,subprocess,tarfile,tempfile
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]; UP=ROOT/'verification/swift-memory-helper-contract'
def encode(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,x):(HERE/n).write_bytes(encode(x))
def manifest(p):return {str(f.relative_to(p)):sha(f.read_bytes()) for f in sorted(p.rglob('*')) if f.is_file() and (f.parts[len(p.parts)] in ['src','tests','include'] or f.name in ['Cargo.toml','Cargo.lock'])}
def command(name,argv,cwd=None,extra=None):
 d=HERE/'commands'/name;d.mkdir(parents=True,exist_ok=False);env=dict(os.environ);env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
 if cwd:env['CARGO_TARGET_DIR']=str(SCRATCH/('target-'+name))
 env.update(extra or {});cwd=cwd or ROOT;before=manifest(cwd) if cwd!=ROOT else None
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=900);after=manifest(cwd) if before else None
 r={'argv':argv,'cwd':str(cwd),'environment':{k:env[k] for k in ['PATH','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP'] if k in env},'startedUTC':start,'completedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':p.returncode,'sourceTreeSHA256':sha(encode(before)) if before else None,'sourceUnchanged':before==after}
 if before:(d/'source-manifest.json').write_bytes(encode(before))
 for stream in ['stdout','stderr']:
  b=getattr(p,stream);(d/(stream+'.gz')).write_bytes(gzip.compress(b,mtime=0));r[stream+'SHA256']=sha(b)
 (d/'receipt.json').write_bytes(encode(r));print(name,p.returncode,flush=True)
 assert before==after,(name,'source drift');assert p.returncode==0,(name,p.stderr.decode(errors='replace')[-2000:]);return p

def members(s,name):
 m=re.search(r'(?m)^(?:pub(?:\([^\n]*?\))? )?struct '+re.escape(name)+r"(?:<'[^\n]*?>)?\s*\{",s);assert m,name
 start=m.end();depth=1;i=start
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[m.start():i]
def instrument(label,schema):
 vm=SCRATCH/('layout-'+label);shutil.copytree(SCRATCH/label,vm)
 types={'State':'SwiftExecutionState','Instance':'SwiftReactorInstance','SwiftFrame':'SwiftFrame','Control':'Control','Phase':"FrameOperationPhase<'static>",'ExecutionPhase':"ExecutionOperationPhase<'static>",'Storage':"FrameOperationStorage<'static>",'DropTuple':"(ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>)",'Preparation':"Option<Result<FrameOperationPhase<'static>,SwiftRunFailure>>",'MemoryResult':'Result<(),SwiftRunFailure>','MemorySlot':'Option<Result<(),SwiftRunFailure>>','Failure':'SwiftRunFailure','Cursor':'Cursor','Operation':'Operation','Instruction':'DecodedInstruction','Value':'Value','FrameCleanupState':'FrameCleanupState','RuntimeControl':'RuntimeControl','Cache':'SwiftFunctionCache','Pin':'SwiftFunctionPin','Wasi':'AccountedWasi','Ticket':'ReservationTicket','FramePermanent':'PermanentPositions','FrameActive':'ActivePositions','FrameImplementationPermanent':'ImplementationPermanentPositions','FrameImplementationActive':'ImplementationActivePositions'}
 owners={'SwiftExecutionState':['memory','table','globals','values','controls','frames','buffers','execution_header','frame_cleanup'],'SwiftReactorInstance':['control','cache','wasi','state','lifecycle'],'SwiftFrame':['function','pc','base','operands','controls','result','pin'],"FrameOperationPhase<'static>":['phase','cleanup','lifecycle'],"ExecutionOperationPhase<'static>":['parts','operation','previous_bound'],"FrameOperationStorage<'static>":['preparation','entry','returned','drained','controlled'],'FrameCleanupState':['disposition','bound','unvisited','nested_restore','live_unreconciled','entry_attempted','entry']}
 lines=['pub(crate) fn independent_memory_layout(){']
 for n,t in types.items():lines.append(f'println!("IR_TYPE {n} {{}} {{}}",size_of::<{t}>(),std::mem::align_of::<{t}>());')
 for t,fs in owners.items():
  for f in fs:lines.append(f'println!("IR_OWNER {t}.{f} {{}}",std::mem::offset_of!({t},{f}));')
 for n,e in {'header':'execution_header_bytes().unwrap()','construction':'construction_bytes().unwrap()','frame':'FRAME_OPERATION_BYTES.unwrap()','frame_permanent':'PERMANENT_BYTES','frame_active':'ACTIVE_BYTES','control_permanent':'control_operations::PERMANENT_BYTES','control_active':'control_operations::ACTIVE_BYTES','value':'value_operations::VALUE_OPERATION_BYTES.unwrap()','state_limit':'SwiftRunBudget::default().state_bytes','combined_limit':'SwiftRunBudget::default().combined_bytes'}.items():lines.append(f'println!("IR_TOTAL {n} {{}}",{e});')
 lines.append('#[cfg(feature="experimental-span-execution")] crate::experimental::execution::independent_frozen_layout();')
 if label=='candidate':lines.append('memory_operations::independent_memory_layout();')
 lines.extend(['}','#[cfg(test)] #[test] fn independent_memory_layout_only(){independent_memory_layout();}'])
 p=vm/'src/experimental_swift_reactor/frame_operations.rs';p.write_text(p.read_text()+'\n'+'\n'.join(lines)+'\n')
 if label=='candidate':
  p=vm/'src/experimental_swift_reactor/memory_operations.rs';lines=['pub(super) fn independent_memory_layout(){',"let _: fn(&mut FrameOperationPhase<'static>,Operation,&mut Option<Result<(),SwiftRunFailure>>) -> Result<(),SwiftRunFailure> = FrameOperationPhase::memory_operation;", "let _: fn(&mut FrameOperationPhase<'static>,&mut FrameOperationStorage<'static>) -> Result<(),SwiftRunFailure> = memory_pinned_caller_prerequisite;"]
  for cls in ['PermanentPositions','ActivePositions']:lines.append(f'println!("IR_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
  for row in schema:lines.append(('#[cfg(test)] ' if row['config']=='unit' else '')+f'println!("IR_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({row["ownerClass"]},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
  lines+=['println!("IR_TOTAL memory_permanent {}",PERMANENT_BYTES);','println!("IR_TOTAL memory_active {}",ACTIVE_BYTES);','}'];p.write_text(p.read_text()+'\n'+'\n'.join(lines)+'\n')
 p=vm/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn independent_memory_layout_route(){execution::frame_operations::independent_memory_layout();}\n')
 p=vm/'src/lib.rs';p.write_text(p.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn independent_memory_layout_route(){experimental_swift_reactor::independent_memory_layout_route();}\n')
 p=vm/'src/bin/independent_memory_layout.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::independent_memory_layout_route();}\n')
 p=vm/'src/experimental/execution/mod.rs';p.write_text(p.read_text()+'''\n#[cfg(feature="experimental-span-execution")] pub(crate) fn independent_frozen_layout(){println!("IR_TOTAL frozen_header {}",size_of::<SpanInstance>()-size_of::<FunctionCache>()+3*size_of::<ExecutionFailure>()+2*size_of::<CacheFailure>()+size_of::<super::cache::DecodedInstruction>()+size_of::<Control>()+size_of::<ScalarReader<'_>>()+512);println!("IR_TYPE FrozenOwner {} {}",size_of::<SpanInstance>(),std::mem::align_of::<SpanInstance>());println!("IR_TYPE FrozenFrame {} {}",size_of::<Frame>(),std::mem::align_of::<Frame>());println!("IR_TYPE FrozenControl {} {}",size_of::<Control>(),std::mem::align_of::<Control>());}\n''')
 archive(vm,'layout-'+label);return vm

def archive(p,n):
 m=manifest(p);write(n+'-source-manifest.json',m)
 with tarfile.open(HERE/(n+'-source.tar.gz'),'w:gz') as t:
  for f in m:t.add(p/f,arcname='vm/'+f)
 with tarfile.open(HERE/(n+'-source.tar.gz'),'r:gz') as t:assert {x.name[3:]:sha(t.extractfile(x).read()) for x in t.getmembers()}==m
 return sha(encode(m))

def parse(data):
 out={x:{} for x in ['types','owners','totals','classes','fields']}
 for line in data.decode().splitlines():
  at=line.find('IR_')
  if at<0:continue
  k,n,*v=line[at:].split();v=list(map(int,v));key={'IR_TYPE':'types','IR_OWNER':'owners','IR_TOTAL':'totals','IR_CLASS':'classes','IR_FIELD':'fields'}[k];assert n not in out[key];out[key][n]=v if len(v)>1 else v[0]
 return out

if __name__=='__main__':
 assert sha((UP/'receipt.json').read_bytes())=='57685ea8486d7387ef708d00427bb21e0fdb61c4f97559b31ec6f03b038b20fa'
 r=json.loads((UP/'receipt.json').read_text());binding={p:sha((ROOT/p).read_bytes()) for p in r['bindings']};assert binding==r['bindings'] and len(binding)==319;write('producer-bindings-verified.json',binding)
 SCRATCH=pathlib.Path(tempfile.mkdtemp(prefix='mixer-memory-independent-'));write('session.json',{'scratch':str(SCRATCH),'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producerReceiptSHA256':sha((UP/'receipt.json').read_bytes())})
 for label in ['baseline','candidate']:
  p=SCRATCH/label;p.mkdir()
  with tarfile.open(UP/(label+'-source.tar.gz'),'r:gz') as t:
   for x in t.getmembers():
    assert x.isfile() and x.name.startswith('vm/') and '..' not in pathlib.Path(x.name).parts
    q=p/x.name[3:];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(t.extractfile(x).read())
  assert manifest(p)==json.loads((UP/(label+'-source-manifest.json')).read_text());archive(p,label)
 for n,a in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('python',['python3','--version']),('host',['uname','-a']),('git',['git','rev-parse','HEAD'])]:command('tool-'+n,a)
 schema=json.loads((UP/'inventory-schema.json').read_text());mem=(SCRATCH/'candidate/src/experimental_swift_reactor/memory_operations.rs').read_text()
 # Parse actual named field declarations afresh, do not trust schema for existence/types.
 declared={}
 for cls in ['ActivePositions','PermanentPositions']:
  for field,ty in re.findall(r'^    (\w+): (.+),$',members(mem,cls),re.M):assert field not in declared;declared[field]=(cls,ty)
 assert declared=={x['field']:(x['ownerClass'],x['rustType']) for x in schema};write('actual-field-declarations.json',declared)
 for label in ['baseline','candidate']:instrument(label,schema)
 for label in ['baseline','candidate']:
  command('expanded-'+label,['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],SCRATCH/label,{'RUSTC_BOOTSTRAP':'1'})
 for unit in [False,True]:
  n='unit' if unit else 'production';args=['cargo','test','--lib','--no-run','--locked','--offline','--all-features'] if unit else ['cargo','rustc','--lib','--locked','--offline','--all-features','--','--emit=mir','-Zmir-include-spans=yes'];env={'RUSTC_BOOTSTRAP':'1'}
  if unit:env['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
  command(n+'-mir',args,SCRATCH/'candidate',env)
  paths=[p for p in (SCRATCH/('target-'+n+'-mir')/'debug/deps').glob('*.mir') if '::memory_operation(' in p.read_text()];assert len(paths)==1;(HERE/(n+'.mir.gz')).write_bytes(gzip.compress(paths[0].read_bytes(),mtime=0))
 layouts=[];executables={}
 for label in ['baseline','candidate']:
  for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
   for release in [False,True]:
    for unit in [False,True]:
     name='layout-'+label+'-'+feature+('-release' if release else '-debug')+('-unit' if unit else '-production');args=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'independent_memory_layout_only','--','--exact','--nocapture','--test-threads=1'] if unit else ['cargo','run','--locked','--offline','--bin','independent_memory_layout',*flags,*(['--release'] if release else [])]
     # Unit test is nested: omit --exact and assert exactly one real matching test executes.
     if unit:args.remove('--exact')
     p=command(name,args,SCRATCH/('layout-'+label));layout=parse(p.stdout);assert not unit or re.search(rb'1 passed; 0 failed; 0 ignored;',p.stdout)
     layout.update(label=label,feature=feature,profile='release' if release else 'debug',unit=unit);layouts.append(layout);write('layouts.json',layouts)
     target=SCRATCH/('target-'+name)/('release' if release else 'debug');bins=[p for p in (target/'deps').glob('mixer_vm-*') if p.is_file() and p.stat().st_mode&0o111] if unit else [target/'independent_memory_layout'];assert len(bins)==1,(name,bins);executables[name]={str(x.relative_to(SCRATCH)):sha(x.read_bytes()) for x in bins};write('executables.json',executables)
 for feature,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:command('check-'+feature+('-release' if release else '-debug'),['cargo','check','--lib','--locked','--offline',*flags,*(['--release'] if release else [])],SCRATCH/'candidate')
 print('COLLECTION COMPLETE',flush=True)
