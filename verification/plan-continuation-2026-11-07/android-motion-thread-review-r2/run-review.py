"""One strict focused Java compile/JVM suite, then normal/-O source admission."""
import datetime, hashlib, json, os, resource, shutil, signal, subprocess, sys, time
from pathlib import Path
OUT=Path(__file__).resolve().parent
CAND=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-7764d3ec')
E=CAND/'verification/plan-continuation-2026-11-07/android-motion-thread-fix-r2'
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home').resolve()
START=time.monotonic(); LIMIT=4*1024*1024
records=[]; outputs=[]
def ident(p):
    b=p.read_bytes(); return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(name,v): (OUT/name).write_text(json.dumps(v,indent=2)+'\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for k in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS','CLASSPATH','JAVA_OPTS'):env.pop(k,None)
def bounds(): resource.setrlimit(resource.RLIMIT_FSIZE,(LIMIT,LIMIT))
def run(label,args,seconds=30,environment=None,cwd=OUT):
    out=OUT/(label+'.stdout'); err=OUT/(label+'.stderr'); outputs.extend([out,err]); start=time.monotonic(); stop=None
    with out.open('wb') as o,err.open('wb') as e:
        p=subprocess.Popen([str(a) for a in args],cwd=cwd,env=environment or env,stdout=o,stderr=e,start_new_session=True,preexec_fn=bounds)
        try:
            while p.poll() is None:
                if time.monotonic()-start>seconds or time.monotonic()-START>600:stop='time-limit'
                if sum(x.stat().st_size for x in outputs)>LIMIT:stop='aggregate-output-limit'
                if stop:os.killpg(p.pid,signal.SIGKILL);break
                time.sleep(.05)
        finally:
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
            p.wait()
    try:os.killpg(p.pid,0); absent=False
    except ProcessLookupError:absent=True
    if not absent:os.killpg(p.pid,signal.SIGKILL)
    records.append({'label':label,'argv':[str(a) for a in args],'cwd':str(cwd),'exit':p.returncode,'limitSeconds':seconds,'seconds':time.monotonic()-start,'stop':stop,'ownedPIDPGID':p.pid,'reaped':True,'ownedGroupAbsent':absent,'stdout':ident(out),'stderr':ident(err)})
    save('commands.json',records)
    if p.returncode or stop:raise RuntimeError(label+' failed; inspect retained streams')
scratch=OUT/'scratch'; scratch.mkdir(); classes=scratch/'classes'; classes.mkdir(); empty=scratch/'empty'; empty.mkdir()
receipt={'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FAILED','limits':{'reviewMinutes':15,'executionSeconds':600,'jobs':2,'actualParallelJobs':1,'outputBytes':LIMIT,'javaCompileSuites':1,'fullB':0,'sixConsumers':0},'python':sys.version,'tools':{str(JDK/'bin'/n):ident(JDK/'bin'/n) for n in ['java','javac','javap']},'scope':'strict Java17 host leaves and admission only; no native/runtime'}
try:
    mapping=json.loads((E/'environment-final/source-map.json').read_text()); inputs=OUT/'inputs'; inputs.mkdir()
    for path,expected in mapping.items():
        if ident(CAND/path)!=expected:raise RuntimeError('source drift '+path)
        target=inputs/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(CAND/path,target)
    save('source-map.json',mapping)
    sources=[inputs/p for p in mapping if p.endswith('.java')]
    run('java-version',[JDK/'bin/java','-version'])
    run('javac-version',[JDK/'bin/javac','-version'])
    run('compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources],60)
    save('classes.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
    for name in ['NativeEnvironmentV2ObserverHostTests','NativeEnvironmentPlatformV2HostTests']:
        run(name,[JDK/'bin/java','-ea','-Xmx128m','-cp',classes,'dev.mixer.android.'+name],30)
    for name in ['dev.mixer.android.NativeEnvironmentPlatformV2$Api33','dev.mixer.android.NativeEnvironmentV2ObserverHostTests','dev.mixer.android.ObserverHostProbe','android.animation.ValueAnimator']:
        run('javap-'+name.rsplit('.',1)[-1],[JDK/'bin/javap','-p','-c','-v','-classpath',classes,name])
    dump=(OUT/'javap-NativeEnvironmentPlatformV2$Api33.stdout').read_text()
    exchanges=[line.strip() for line in dump.splitlines() if 'invokevirtual' in line and 'AtomicBoolean.getAndSet:' in line]
    if len(exchanges)!=2 or any('invokevirtual' in l and 'AtomicBoolean.compareAndSet:' in l for l in dump.splitlines()):raise RuntimeError('compiled exchanges mismatch')
    receipt['compiledExchangeInstructions']=exchanges
    # Relocate hard-coded /tmp test fixtures into the sole review-owned namespace.
    driver=OUT/'run-admission.py'
    driver.write_text('import pathlib,runpy,sys,tempfile\nroot=pathlib.Path(__file__).resolve().parent/"scratch"\noriginal=tempfile.TemporaryDirectory\ndef owned(*a,**kw):\n kw["dir"]=str(root); return original(*a,**kw)\ntempfile.TemporaryDirectory=owned\nsys.argv=[sys.argv[1]]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n')
    test=CAND/'cli/build-tests/test_android_sdk_compatibility.py'
    run('admission',[sys.executable,'-B',driver,test],90)
    run('admission-O',[sys.executable,'-B','-O',driver,test],90,dict(env,PYTHONOPTIMIZE='1'))
    receipt['admissionFixtureRelocation']='Only TemporaryDirectory dir rerouted into owned scratch; candidate test bytes unchanged; subprocess optimization inherited.'
    receipt['sourceStable']=all(ident(CAND/p)==v for p,v in mapping.items())
    if not receipt['sourceStable']:raise RuntimeError('source drift')
    receipt['status']='PASS'
finally:
    shutil.rmtree(scratch)
    receipt['cleanup']={'ownedScratchRemoved':not scratch.exists(),'allChildrenReaped':all(r['reaped'] for r in records),'ownedGroupsAbsent':all(r['ownedGroupAbsent'] for r in records),'heldProcessesTouched':False}
    receipt['totalOutputBytes']=sum(x.stat().st_size for x in outputs)
    receipt['seconds']=time.monotonic()-START
    save('replay-result.json',receipt)
print(json.dumps({'status':receipt['status'],'seconds':receipt['seconds'],'outputBytes':receipt['totalOutputBytes'],'compileSuites':1}))
