from pathlib import Path
import hashlib,importlib.util,json,os,shutil,sys,time
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;ROOT=O.parents[2];F=O.parent/'store-journal-integrity-fix';S=O/'source';A=O/'attempt-1'
A.mkdir();scratch=O/'scratch';scratch.mkdir();(scratch/'tmp').mkdir()
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,j):p.write_text(json.dumps(j,sort_keys=True,indent=2)+'\n')
def size(p):return sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink())
def hashes(p):return {str(f.relative_to(p)):h(f) for f in sorted(p.rglob('*')) if f.is_file()}
pre=json.loads((O/'preflight.json').read_text());remaining=pre['deadline']-time.time();assert remaining>30
controller=O/'cleanup_control.py';assert h(controller)=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
spec=importlib.util.spec_from_file_location('custody',controller);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
swift=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
env={k:os.environ[k] for k in ['PATH','HOME','USER','LOGNAME','LANG','LC_ALL','SHELL'] if k in os.environ}
env.update(DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',SDKROOT='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk',TMPDIR=str(scratch/'tmp')+'/',MIXER_STORE_TEST_CLI=str(scratch/'build/debug/mixer'))
c=m.Commands(A,env,deadline=time.monotonic()+remaining,output_bytes=4194304,total_output_bytes=33554432,cleanup_seconds=5)
sources=hashes(S);save(A/'source-hashes.json',sources)
r={'sourceHashes':sources,'sourceDigest':hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'candidateDigest':'e51c7700f9346318a8dc15709601e324677725f66bee35168572c3ba621c4f84','environment':env,'TOOLCHAINS':'unset','swiftSHA256':h(swift),'controllerSHA256':h(controller),'driverSHA256':h(Path(__file__)),'peakScratch':0,'bounds':{'wallSeconds':720,'swiftInvocations':2,'swiftTestCommands':1,'perTestSeconds':600,'jobs':2,'ownedScratchBytes':1073741824,'commandCombinedBytes':4194304,'aggregateBytes':33554432,'cleanupSeconds':5}}
save(A/'receipt.json',r)
try:
 r['parentHEAD']=c.run('head',['git','rev-parse','HEAD'],ROOT);assert r['parentHEAD']=='62ce9b76840b2fa56306736fc4c4fe2962780adf'
 manifest=json.loads((F/'patch-manifest.json').read_text());paths=list(manifest['files']);r['patchApplication']={}
 for label,patch,baseline in [('full','implementation.patch',None),('increment','campaign-increment.patch',O.parent/'store-credential-index-campaign/candidate')]:
  check=scratch/label;check.mkdir()
  for i,p in enumerate(paths):
   if baseline is None:
    c.run('base-'+str(i),['git','show',manifest['base']+':'+p],ROOT,allowed=(0,128))
    rec=c.records[-1];data=Path(rec['logs']['stdout']).read_bytes() if rec['exit_code']==0 else None
   else:data=(baseline/p).read_bytes()
   if data is not None:
    dst=check/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
  for flags in [['--check'],[]]:
   c.run('apply-'+label+'-'+str(len(flags)),['git','apply',*flags,'--directory='+str(check.relative_to(ROOT)),F/patch],ROOT)
  matches={p:h(check/p)==manifest['files'][p]['sha256'] for p in paths};assert all(matches.values());r['patchApplication'][label]=matches
 r['swiftVersion']=c.run('swift-version',[swift,'--version'],S)
 r['xcodeVersion']=c.run('xcode-version',['/usr/bin/xcodebuild','-version'],S)
 r['sdkVersion']=c.run('sdk-version',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-version'],S)
 save(A/'receipt.json',r)
 item=c.start('swift-tests',[swift,'test','--package-path',S/'cli','--scratch-path',scratch/'build','--disable-automatic-resolution','--skip-update','-j','2','--filter','StoreSubmissionReconciliationTests'],S)
 until=min(time.monotonic()+600,c.deadline-5);next_size=0
 while not c.hold:
  if time.monotonic()>=until:item['record']['stop']='timeout';break
  c.pump(.02)
  if c.hold or c.limit:break
  if time.monotonic()>next_size:
   r['peakScratch']=max(r['peakScratch'],size(scratch));next_size=time.monotonic()+1
   if r['peakScratch']>=1073741824:item['record']['stop']='scratch-limit';break
  if c.reaped(item) and item['record']['stdout_eof'] and item['record']['stderr_eof']:break
 c.stop(item);c.persist(item)
 r['passed']=item['record']['exit_code']==0 and item['record']['terminal_custody'] and not item['record']['stop'] and not c.hold and not c.limit
except BaseException as error:r['error']=repr(error)
finally:
 r['sourceStable']=hashes(S)==sources
 r['cleanup']=c.cleanup(scratch);r['commands']=c.records
 r['logHashes']={p.name:h(p) for p in A.iterdir() if p.suffix in ['.stdout','.stderr']}
 protected=json.loads((O/'protected-baseline.json').read_text())
 r['protectedPostflight']={p:(h(ROOT/p) if (ROOT/p).exists() else None)==digest for p,digest in protected.items()}
 r['elapsedSeconds']=time.time()-pre['started'];r['finishedEpoch']=time.time()
 save(A/'receipt.json',r)
 print(json.dumps({k:r.get(k) for k in ['passed','error','sourceStable','cleanup','peakScratch','elapsedSeconds','sourceDigest']}),flush=True)
