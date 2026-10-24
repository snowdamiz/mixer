#!/usr/bin/env python3
"""Isolated, uncalled compiler composition contract. Never edits live VM/tracker/Git."""
import gzip, hashlib, json, os, shutil, signal, subprocess, tarfile, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'verification/swift-cleanup-diagnostic-root-integration'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def put(name,data):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else enc(data))
def manifest(path):
 return {str(p.relative_to(path)):sha(p.read_bytes()) for p in sorted(path.rglob('*')) if p.is_file()}
def group_members(group):
 output=subprocess.check_output(['ps','-axo','pid=,pgid=,command='],text=True)
 return [row.strip() for row in output.splitlines() if len(row.split(None,2))>=2 and row.split(None,2)[1]==str(group)]
def pack(path,dest):
 with tarfile.open(HERE/dest,'w:gz') as out:
  for rel in manifest(path):out.add(path/rel,arcname=rel,recursive=False)
def main():
 attempt=HERE/'attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');attempt.mkdir(parents=True)
 scratch=Path(tempfile.mkdtemp(prefix='mixer-calls-contract-')).resolve();tree=scratch/'source';tree.mkdir()
 source=json.loads((BASE/'integrated-source-manifest.json').read_text())
 assert len(source)==128
 assert sha(enc(source))=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
 for rel,digest in source.items():
  data=(ROOT/'vm'/rel).read_bytes();assert sha(data)==digest,rel
  p=tree/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 pack(tree,str(attempt.relative_to(HERE)/'baseline-source.tar.gz'))
 before=dict(source);commands=[];artifacts=[]
 def run(label,argv,cwd=tree,target=None,expected=0):
  start=datetime.now(timezone.utc).isoformat();source_before=manifest(tree)
  env=os.environ.copy();env['CARGO_INCREMENTAL']='0';env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH']
  if target:env['CARGO_TARGET_DIR']=str(target)
  p=subprocess.Popen(argv,cwd=cwd,env=env,start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  timed=False
  try:output,_=p.communicate(timeout=120)
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(p.pid,signal.SIGKILL);output,_=p.communicate()
  leftovers=group_members(p.pid)
  if leftovers:
   os.killpg(p.pid,signal.SIGTERM);time.sleep(.1)
   if group_members(p.pid):os.killpg(p.pid,signal.SIGKILL)
  row={'label':label,'argv':argv,'cwd':str(cwd),'target':str(target) if target else None,'exitCode':p.returncode,'expectedExitCode':expected,'timedOut':timed,'startedUTC':start,'finishedUTC':datetime.now(timezone.utc).isoformat(),'sourceBeforeSHA256':sha(enc(source_before)),'sourceAfterSHA256':sha(enc(manifest(tree))),'sourceUnchanged':source_before==manifest(tree),'group':p.pid,'remainingGroup':group_members(p.pid),'outputSHA256':sha(output),'log':str(attempt.relative_to(HERE)/(label+'.log.gz'))}
  put(row['log'],gzip.compress(output,mtime=0));commands.append(row)
  put(str(attempt.relative_to(HERE)/'commands.json'),commands)
  assert not timed and not row['remainingGroup'] and row['sourceUnchanged'],row
  if expected==0:assert p.returncode==0,output.decode(errors='replace')[-14000:]
  else:assert p.returncode!=0,output.decode(errors='replace')[-2000:]
  return output
 try:
  for label,argv in [('rustc',['rustc','--version','--verbose']),('cargo',['cargo','--version']),('host',['uname','-a']),('python',['python3','--version']),('revision',['git','rev-parse','HEAD'])]:run(label,argv,ROOT)
  probe=(HERE/'composition_probe.rs').read_bytes();(tree/'src/experimental_swift_reactor/calls_contract_probe.rs').write_bytes(probe)
  frame=tree/'src/experimental_swift_reactor/frame_operations.rs'
  frame.write_bytes(frame.read_bytes()+b'\n#[path="calls_contract_probe.rs"]\nmod calls_contract_probe;\n')
  witness=manifest(tree);put(str(attempt.relative_to(HERE)/'witness-manifest.json'),witness);pack(tree,str(attempt.relative_to(HERE)/'witness-source.tar.gz'))
  for features in ['experimental-swift-reactor','all']:
   for release in [False,True]:
    for unit in [False,True]:
     label=('all' if features=='all' else 'swift')+('-release' if release else '-debug')+('-unit' if unit else '-production')
     target=scratch/('target-'+label)
     argv=['cargo','rustc','--lib','--locked','--offline','--no-default-features']+(['--all-features'] if features=='all' else ['--features',features])+(['--release'] if release else [])+['--','--emit=mir']+(['--test'] if unit else [])
     run(label,argv,target=target)
     mirs=list(target.rglob('*.mir'));assert len(mirs)==1,[str(x) for x in mirs]
     data=mirs[0].read_bytes();name=str(attempt.relative_to(HERE)/(label+'.mir.gz'));put(name,gzip.compress(data,mtime=0))
     text=data.decode();headers=[]
     lines=text.splitlines();i=0
     while i<len(lines):
      if lines[i].startswith('fn '):
       start=i;header=lines[i];i+=1
       while not header.rstrip().endswith('{') and i<len(lines):header+='\n'+lines[i];i+=1
       if 'calls_contract_probe' in header or any(header.startswith('fn '+name+'(') or header.startswith('fn '+name+'::') for name in ['pop_checked','typed_i32','call_defined','call_selected','indirect','fetch','local_slot','step','run','complete']):headers.append({'line':start+1,'header':header})
      else:i+=1
     assert all(any(h['header'].startswith('fn '+name+'(') or h['header'].startswith('fn calls_contract_probe::'+name+'(') for h in headers) for name in ['pop_checked','typed_i32','call_defined','call_selected','indirect','fetch','local_slot','step','run','complete']),(label,headers)
     artifacts.append({'label':label,'path':name,'sha256':sha(data),'bytes':len(data),'headers':headers,'sourceSHA256':sha(enc(witness))})
  put(str(attempt.relative_to(HERE)/'mir-artifacts.json'),artifacts)
  negatives={
   'view-enter':'''fn bad(phase:&mut FrameOperationPhase<'_>)->Result<usize,SwiftRunFailure>{ let frame=phase.phase.parts.frames.last().unwrap();let view=phase.phase.parts.cache.view(&frame.pin,phase.phase.operation.control,Some(&*phase.phase.operation.wasi))?;phase.enter(34)?;Ok(view.instructions.len()) }''',
   'arguments-truncate':'''fn bad(phase:&mut FrameOperationPhase<'_>)->usize{let args=&phase.phase.parts.values[..];phase.phase.parts.values.truncate(0);args.len()}''',
   'growth-whole-instance':'''fn bad(instance:&mut SwiftReactorInstance,cursor:Cursor)->Result<(),SwiftRunFailure>{let(mut phase,context)=instance.prepare_growth(cursor)?;let _other=instance.prepare_frames(cursor)?;phase.enter(34)?;drop(context);Ok(())}''',
   'growth-ticket-alias':'''fn bad<'a>(phase:&mut FrameOperationPhase<'a>,context:&mut SwiftGrowthContext<'a>,pending:&mut SwiftGrowthStorage)->Result<(),SwiftRunFailure>{let ticket=context.memory_ticket.as_mut().unwrap();let mut outcome=None;growth::growth_operation(phase,context,pending,Operation::MemoryGrow,&mut outcome)?;let _=ticket.matches_layout(SwiftReservationCategory::State,0);Ok(())}''',
  }
  for name,body in negatives.items():
   file=tree/'src/experimental_swift_reactor/calls_contract_probe.rs';file.write_bytes(probe+b'\n'+body.encode()+b'\n')
   put(str(attempt.relative_to(HERE)/('negative-'+name+'.rs')),file.read_bytes())
   put(str(attempt.relative_to(HERE)/('negative-'+name+'-manifest.json')),manifest(tree))
   output=run('negative-'+name,['cargo','check','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor'],target=scratch/('target-negative-'+name),expected=1)
   assert b'error[E0502]' in output or b'error[E0499]' in output or b'error[E0500]' in output,output
   file.write_bytes(probe)
  assert manifest(tree)==witness

  put(str(attempt.relative_to(HERE)/'status.json'),{'status':'passed-uncalled-type-composition','baselineSHA256':sha(enc(before)),'witnessSHA256':sha(enc(witness)),'runtimeExecutions':0,'accountingAccepted':False})
 except BaseException as error:
  put(str(attempt.relative_to(HERE)/'failure.json'),{'type':type(error).__name__,'message':str(error)})
  raise
 finally:
  # Only this scratch and process groups created above are ever touched.
  holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True,text=True)
  put(str(attempt.relative_to(HERE)/'holders.log'),(holders.stdout+holders.stderr).encode())
  assert holders.returncode==1 and not holders.stdout,holders.stdout
  count=sum(p.is_file() for p in scratch.rglob('*'));bytes_=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file())
  shutil.rmtree(scratch)
  put(str(attempt.relative_to(HERE)/'cleanup.json'),{'scratch':str(scratch),'ownedScratchRemoved':not scratch.exists(),'holderCheckEmpty':True,'filesRemoved':count,'logicalBytesRemoved':bytes_,'nativeInstancesCreated':0,'remainingCommandGroups':sum(bool(r['remainingGroup']) for r in commands)})
 print(attempt)
if __name__=='__main__':main()
