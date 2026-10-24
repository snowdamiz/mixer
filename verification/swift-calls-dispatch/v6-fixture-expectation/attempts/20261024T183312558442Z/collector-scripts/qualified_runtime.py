"""Reviewed execution plan with per-launch source/tool pins and immutable collection.
The imported collector is unchanged except its nested packet ROOT path. The small
subprocess facade adds a fail-closed prelaunch check; all compile/list/run archive,
timeout, process-group and owned-target cleanup remains in that collector.
No execution occurs without an explicit root runtime-selection receipt hash.
"""
from pathlib import Path
import sys,os,json,datetime,subprocess,hashlib,shutil,gzip,argparse,traceback,signal
sys.dont_write_bytecode=True
import collect as c
REAL=subprocess
FROZEN=['span_control_extraction','span_numeric_extraction','span_execution','span_execution_allocations','span_execution_oracle','span_function_cache','span_function_cache_allocations']
PREFIXES=[f'swift_dispatch_cd{i:02}_'for i in range(1,25)]

def plan():
 rows=[]
 for features in ['swift','all']:
  for profile in ['debug','release']:
   flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])+(['--release']if profile=='release'else[])
   rows.append({'id':f'library-{features}-{profile}','argv':['cargo','test','--lib','--no-run','--locked','--offline',*flags,'--message-format=json-render-diagnostics'],'post':{'target':'mixer_vm','prefixes':PREFIXES,'args':['--nocapture','--test-threads=1']}})
 for target in FROZEN:
  for profile in ['debug','release']:
   rows.append({'id':f'frozen-{target}-{profile}','argv':['cargo','test','--no-run','--locked','--offline','--no-default-features','--features','experimental-span-execution','--test',target,*(['--release']if profile=='release'else[]),'--message-format=json-render-diagnostics'],'post':{'target':target,'args':['--nocapture','--test-threads=1']}})
 for feature in ['default','span']:
  for profile in ['debug','release']:
   rows.append({'id':f'check-{feature}-{profile}','argv':['cargo','check','--lib','--locked','--offline',*(['--no-default-features','--features','experimental-span-execution']if feature=='span'else[]),*(['--release']if profile=='release'else[])]})
 for feature in ['swift','all']:
  for profile in ['debug','release']:
   rows.append({'id':f'clippy-{feature}-{profile}','argv':['cargo','clippy','--lib','--locked','--offline','--no-default-features',*(['--features','experimental-swift-reactor']if feature=='swift'else['--all-features']),*(['--release']if profile=='release'else[]),'--','-D','warnings']})
 rows.append({'id':'format-new-sources','argv':['rustfmt','--check','--edition','2021','src/experimental_swift_reactor/call_dispatch.rs','src/experimental_swift_reactor/call_dispatch_tests.rs']})
 return rows

class Prelaunch:
 def __init__(self,root,seal,selection):
  self.root=root;self.seal=seal;self.selection=selection;self.events=[];self.children=[];self.kill_events=[]
  q=c.read_json(c.HERE/'exact-query-swift-debug-production.json');self.expected=c.read_json(c.HERE/q['attempt']/'tools.json')
  self.expected_source=c.manifest(c.HERE/'candidate');assert c.sha(c.enc(self.expected_source))==seal['candidateSourceClosure']
 def __getattr__(self,name):return getattr(REAL,name)
 def Popen(self,argv,*args,**kwargs):
  assert kwargs.get('start_new_session')is True
  event={'cargoTargetDir':kwargs['env']['CARGO_TARGET_DIR'],'startNewSession':True,'argv':list(argv),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceClosure':self.seal['candidateSourceClosure'],'producerSealSHA256':c.sha((c.HERE/'review-seal.json').read_bytes()),'rootSelectionSHA256':self.selection,'launched':False}
  dest=self.root/'prelaunch'/f'{len(self.events):03}.json';self.events.append(event)
  try:
   assert c.manifest(c.HERE/'candidate')==self.expected_source,'candidate source drift'
   env=kwargs['env'];assert env.get('RUSTC_BOOTSTRAP')is None and env.get('RUSTFLAGS')is None and env.get('RUSTC_WRAPPER')is None
   assert not env.get('RUSTC')and not env.get('RUSTC_WORKSPACE_WRAPPER')and not env.get('CARGO_ENCODED_RUSTFLAGS')
   sysroot=Path(REAL.check_output(['/opt/homebrew/opt/rustup/bin/rustc','--print','sysroot'],cwd=c.HERE/'candidate',env=env,text=True).strip());expected=self.expected['actualCompiler'];assert str(sysroot)==expected['sysroot']
   actual={str(p.relative_to(sysroot)):c.sha(p.read_bytes())for group in ['bin','lib']for p in sorted((sysroot/group).rglob('*'))if p.is_file()}
   assert actual==expected['sysrootCompilerFiles']and c.sha(c.enc(actual))==expected['sysrootCompilerFilesSHA256'],'actual compiler/sysroot byte drift'
   assert c.sha((sysroot/'bin/rustc').read_bytes())==expected['sha256']
   for tool in ['rustc','cargo','rustfmt']:
    t=self.expected[tool];assert shutil.which(tool,path=env['PATH'])==t['executable']and c.sha(Path(t['executable']).read_bytes())==t['executableSHA256'],tool
   if Path(argv[0]).is_absolute()and '/target/'in str(argv[0]):
    assert Path(argv[0]).is_relative_to(Path(env['CARGO_TARGET_DIR']))
    event['executableSHA256']=c.sha(Path(argv[0]).read_bytes())
   event.update(actualCompilerSHA256=expected['sha256'],sysrootCompilerFilesSHA256=expected['sysrootCompilerFilesSHA256'],sourceAndToolPinsPassed=True)
   c.save(dest,event)
   child=REAL.Popen(argv,*args,**kwargs);self.children.append(child);event.update(launched=True,group=child.pid);c.save(dest,event);return child
  except BaseException:
   event.update(error=traceback.format_exc(),sourceAndToolPinsPassed=False);c.save(dest,event);raise

class OwnedOS:
 """Never use a completed numeric PGID as authority for killing processes."""
 def __init__(self,facade):self.facade=facade
 def __getattr__(self,name):return getattr(os,name)
 def killpg(self,group,sig):
  event={'group':group,'signal':int(sig),'killed':False}
  try:
   children=[p for p in self.facade.children if p.pid==group];assert len(children)==1,'unknown owned child'
   child=children[0]
   # Popen.poll uses waitpid on our actual child. None means that child has not
   # been reaped, so its PID cannot have been reused. A completed/reaped numeric
   # identifier never authorizes a kill, even if a same-PGID process now exists.
   assert child.poll()is None,'completed child PGID is ambiguous; no kill authorized'
   assert os.getpgid(child.pid)==child.pid,'owned child left its original new-session group'
   os.killpg(group,sig);event['killed']=True
  except BaseException:
   event['failure']=traceback.format_exc();raise
  finally:
   self.facade.kill_events.append(event)
   c.save(self.facade.root/'owned-kill-events.json',self.facade.kill_events)

def independent_cleanup(root,facade,owned_os,prior_attempts):
 """Try every resource independently; one failure must not suppress another."""
 processes=[];targets=[];errors=[]
 def save(name,value):
  try:c.save(root/name,value)
  except BaseException:errors.append({'save':name,'failure':traceback.format_exc()})
 def members():
  raw=REAL.check_output(['ps','-axo','pid=,pgid=,command='],text=True)
  return [line for line in raw.splitlines()if len(line.split(None,2))>=2]
 for child in facade.children:
  row={'group':child.pid,'cleanupComplete':False,'killAttempted':False}
  try:
   if child.poll()is None:
    row['killAttempted']=True;owned_os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
   remaining=[line for line in members()if line.split(None,2)[1]==str(child.pid)]
   row.update(exitCode=child.returncode,remainingAfterOwnedKillOrCompletion=remaining,cleanupComplete=not remaining)
   if remaining:row['failure']='Completed numeric group has surviving/possibly reused members; fail closed without killing ambiguous processes.'
  except BaseException:row['failure']=traceback.format_exc()
  processes.append(row);save('independent-process-cleanup.json',processes)
 try:new_attempts=sorted(set((c.HERE/'attempts').iterdir())-prior_attempts)
 except BaseException:new_attempts=[];errors.append({'attemptInventory':traceback.format_exc()})
 owned_targets={event['cargoTargetDir']for event in facade.events}
 for attempt in new_attempts:
  row={'attempt':str(attempt.relative_to(c.HERE)),'cleanupComplete':False}
  try:
   command=c.read_json(attempt/'command.json');target=command['environment']['CARGO_TARGET_DIR'];scratch=Path(target).parent
   assert target in owned_targets,'target not bound to a prelaunch event'
   assert scratch.name.startswith('mixer-calls-dispatch-')and scratch.parent==Path(__import__('tempfile').gettempdir())
   row.update(scratch=str(scratch),normalCleanupPresent=(attempt/'cleanup.json').exists())
   if scratch.exists():
    holders=REAL.run(['lsof','-nP','+D',str(scratch)],capture_output=True);c.save(attempt/'recovery-holders.log',holders.stdout+holders.stderr);assert not holders.stdout,'owned target is still in use; preserved'
    preserved=[]
    for p in sorted(scratch.rglob('*')):
     if p.is_file()and(p.suffix in ['.mir','.ll']or(p.parent.name=='deps'and p.stat().st_mode&0o111 and p.suffix=='')):
      raw=p.read_bytes();name='recovery-artifacts/'+str(p.relative_to(scratch))+'.gz';c.save(attempt/name,gzip.compress(raw,mtime=0));preserved.append({'path':name,'sha256':c.sha(raw),'bytes':len(raw)})
    c.save(attempt/'recovery-artifacts.json',preserved);shutil.rmtree(scratch)
    c.save(attempt/'recovery-cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'holderCheckEmpty':True,'reason':'collector did not reach normal cleanup; existing executable/MIR bytes retained before cleanup','nativeInstancesCreated':0})
   row.update(independentlyAbsent=not scratch.exists(),cleanupComplete=not scratch.exists(),recoveryCleanupPresent=(attempt/'recovery-cleanup.json').exists())
  except BaseException:row['failure']=traceback.format_exc()
  targets.append(row);save('independent-target-cleanup.json',targets)
 # Requery after every kill/cleanup attempt. A failure here is retained without
 # suppressing any resource attempt already made above.
 final={'queried':False,'remainingKnownNumericGroups':None}
 try:
  owned={str(p.pid)for p in facade.children};remaining=[line for line in members()if line.split(None,2)[1]in owned]
  final.update(queried=True,remainingKnownNumericGroups=remaining,allKnownGroupsActuallyEmpty=not remaining)
 except BaseException:final['failure']=traceback.format_exc()
 save('final-process-requery.json',final)
 complete=bool(final.get('allKnownGroupsActuallyEmpty'))and not errors and all(r['cleanupComplete']for r in processes+targets)and len(targets)==len(new_attempts)
 result={'cleanupComplete':complete,'processes':processes,'targets':targets,'finalProcessRequery':final,'recordingErrors':errors,'ambiguousCompletedPGIDsNeverKilled':True,'nativeInstancesCreated':0}
 save('independent-cleanup.json',result)
 if errors:result['cleanupComplete']=False
 return result

def observations(attempt,row):
 if not row['id'].startswith('library-'):return {}
 tests=c.read_json(attempt/'test-list.json');assert len(tests)==len(set(tests));selected={p:[t for t in tests if p in t]for p in PREFIXES};assert all(selected.values())and sum(map(len,selected.values()))==60
 out=gzip.decompress((attempt/'execute-stdout.gz').read_bytes()).decode();err=gzip.decompress((attempt/'execute-stderr.gz').read_bytes()).decode()
 # Values are independent expected constants; fixture checks bind full storage and
 # counter traces. The historical fixture label diagnosticUnqualified remains raw.
 required=['CD22_WARM attempts=0 alloc=0 realloc=0 frame=30028176 header=4867456 ticketsMax=86','CD22_COLD growth=false attempts=1 alloc=1 bytes=80 realloc=0',f'CD22_COLD growth=true attempts=1 alloc=1 bytes={585*65536} realloc=0','CD24_TRACE diagnosticUnqualified=true result=20 memoryI32=20 argcWriteAt=20 pages=585 imports=34 table=46713 instructions=21 hostCalls=1 pins=0']
 checks={x:x in out for x in required};assert all(checks.values()),checks
 assert '0 ignored;'in out and '0 filtered out;'in out,'full library harness was filtered or ignored'
 return {'listedTests':len(tests),'cdPrefixes':selected,'independentExpectedTraces':checks,'fixtureDiagnosticLabelPreserved':True,'expectedCaughtPanicStderrRetained':bool(err)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',action='store_true');ap.add_argument('--root-runtime-selection',type=Path);ap.add_argument('--selection-sha256');ap.add_argument('--producer-seal-sha256');args=ap.parse_args()
 rows=plan()
 if args.plan:
  print(c.enc({'schema':1,'commands':rows,'compileTimeoutSeconds':900,'eachExecutableTimeoutSeconds':900,'concurrentCargoAttempts':1,'nativeInstancesCreated':0,'requiresRootRuntimeSelection':True}).decode(),end='');return 0
 assert args.root_runtime_selection and args.selection_sha256 and args.producer_seal_sha256,'explicit reviewed root selection/seal hashes required'
 selection_raw=args.root_runtime_selection.read_bytes();assert c.sha(selection_raw)==args.selection_sha256;selection=json.loads(selection_raw);seal_raw=(c.HERE/'review-seal.json').read_bytes();assert c.sha(seal_raw)==args.producer_seal_sha256;seal=json.loads(seal_raw)
 assert selection['qualifiedExecutionSelected']is True and selection['producerSealSHA256']==args.producer_seal_sha256 and selection['candidateSourceClosure']==seal['candidateSourceClosure']
 assert selection['qualificationDriverSHA256']==c.sha(Path(__file__).read_bytes())and selection['qualificationPlanSHA256']==c.sha(c.enc(rows))
 for rel,b in seal['bindings'].items():
  raw=(c.HERE/rel).read_bytes();assert c.sha(raw)==b['sha256']and len(raw)==b['bytes'],rel
 root=c.HERE/'qualification'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');root.mkdir(parents=True);c.save(root/'root-selection.json',selection_raw);c.save(root/'plan.json',rows);c.save(root/'driver.py',Path(__file__).read_bytes());c.save(root/'producer-seal.json',seal_raw)
 results=[];prior_attempts=set((c.HERE/'attempts').iterdir());facade=Prelaunch(root,seal,args.selection_sha256);owned_os=OwnedOS(facade);original_collector_os=c.os;c.subprocess=facade;c.os=owned_os;cleanup={'cleanupComplete':False}
 try:
  for row in rows:
   code,attempt,out,err=c.run(row['argv'],label='qualified-'+row['id'],post=row.get('post'));entry={'id':row['id'],'attempt':str(attempt.relative_to(c.HERE)),'exitCode':code,'sourceClosure':seal['candidateSourceClosure']};results.append(entry)
   try:
    if code==0:entry['observations']=observations(attempt,row)
   except BaseException:entry.update(observationFailure=traceback.format_exc(),exitCode=-1)
   tools=c.read_json(attempt/'tools.json');assert tools['actualCompiler']==facade.expected['actualCompiler'];assert c.read_json(attempt/'cleanup.json')['removed']
   c.save(root/'results.json',results)
  for rel,b in seal['bindings'].items():
   raw=(c.HERE/rel).read_bytes();assert c.sha(raw)==b['sha256']and len(raw)==b['bytes'],rel
 except BaseException:
  c.save(root/'driver-failure.log',traceback.format_exc().encode());raise
 finally:
  c.subprocess=REAL;c.os=original_collector_os
  cleanup=independent_cleanup(root,facade,owned_os,prior_attempts)
  c.save(root/'results.json',results)
  c.save(root/'receipt.json',{'sourceClosure':seal['candidateSourceClosure'],'producerSealSHA256':args.producer_seal_sha256,'selectionSHA256':args.selection_sha256,'driverSHA256':c.sha(Path(__file__).read_bytes()),'planSHA256':c.sha(c.enc(rows)),'plannedCommands':len(rows),'completedCommands':len(results),'allCommandsPassed':len(results)==len(rows)and all(r['exitCode']==0 for r in results),'cleanupComplete':cleanup['cleanupComplete'],'prelaunchPinChecks':len(facade.events),'qualifiedExecutionSelected':True,'nativeInstancesCreated':0,'liveProductIntegrated':False,'fullSwiftReadyFieldLogOTAGAQualified':False,'rootAggregateAcceptancePending':True})
 print(root)
 return 0 if len(results)==len(rows)and all(r['exitCode']==0 for r in results)and cleanup['cleanupComplete']else 1
if __name__=='__main__':raise SystemExit(main())
