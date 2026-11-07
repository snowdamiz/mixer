#!/usr/bin/env python3
"""One owned emulator attempt using the unchanged current-source APK already built."""
import datetime,hashlib,json,os,pathlib,shutil,signal,socket,subprocess,tempfile,time,traceback
P=pathlib.Path;OUT=P(__file__).resolve().parent;ROOT=OUT.parents[2]
SDK=P('/opt/homebrew/share/android-commandlinetools');JDK=P('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');ADB=SDK/'platform-tools/adb'
BUILD=json.loads((OUT/'build-receipt.json').read_text());LOCK=json.loads((OUT/'source-lock.json').read_text());APK=OUT/'canonical-smoke.apk'
WORK=P(tempfile.mkdtemp(prefix='mixer-20261107-android-runtime-',dir='/tmp'))
ENV=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'],ANDROID_HOME=str(SDK),ANDROID_SDK_ROOT=str(SDK))
# One authoritative Android preferences location; avoid conflicting compatibility roots.
ENV.pop('ANDROID_PREFS_ROOT',None);ENV.pop('ANDROID_SDK_HOME',None)
for name in ['avds','android','tmp']:(WORK/name).mkdir()
ENV.update(ANDROID_AVD_HOME=str(WORK/'avds'),ANDROID_USER_HOME=str(WORK/'android'),ANDROID_EMULATOR_HOME=str(WORK/'android'),TMPDIR=str(WORK/'tmp'),ADB_LIBUSB='0')
R={'schema':1,'status':'preflight','startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scratch':str(WORK),'buildReceiptSHA256':hashlib.sha256((OUT/'build-receipt.json').read_bytes()).hexdigest(),'sourceRevision':BUILD['sourceRevision'],'sourceClosureSHA256':BUILD['sourceClosureSHA256'],'apkSHA256':BUILD['apkSHA256'],'descriptorSHA256':BUILD['descriptorSHA256'],'commands':[],'nativeInstancesStarted':0,'physicalTargetsQueried':False,'runtime':{},'cleanup':{},'nativeAcceptance':False,'gaAcceptance':False,'scope':BUILD['scope'],'limitations':BUILD['limitations'],'launcherCorrection':'reuse sole current build; set one Android preference location and omit unsupported emulator flag; no product or oracle change'}
START=time.monotonic();DEADLINE=START+650;OWNED=[];SOCKETS=[];EMU=None;SERVER=None;PORT=None

def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def save(p,v):P(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def flush():save(OUT/'runtime-receipt.json',R)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def stop(p):
 d={'pid':p.pid,'pgid':p.pid,'signals':[]}
 for sig in [signal.SIGTERM,signal.SIGKILL]:
  p.poll()
  try:os.killpg(p.pid,0)
  except ProcessLookupError:break
  os.killpg(p.pid,sig);d['signals'].append(sig.name)
  until=time.monotonic()+3
  while time.monotonic()<until:
   p.poll()
   try:os.killpg(p.pid,0)
   except ProcessLookupError:break
   time.sleep(.1)
 p.poll()
 try:os.killpg(p.pid,0);d['groupAbsent']=False
 except ProcessLookupError:d['groupAbsent']=True
 return d

def launch(name,args):
 args=list(map(str,args));log=OUT/(name+'.log');f=log.open('wb');p=subprocess.Popen(args,cwd=WORK,env=ENV,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);f.close()
 e={'name':name,'argv':args,'cwd':str(WORK),'pid':p.pid,'pgid':p.pid,'startedUTC':now(),'output':log.name};R['commands'].append(e);OWNED.append((p,e,log));flush();return p,e,log

def run(name,args,timeout=45,allowed=(0,)):
 p,e,log=launch(name,args);limit=min(time.monotonic()+timeout,DEADLINE);reason=None
 while p.poll() is None:
  if time.monotonic()>limit:reason='bounded deadline';break
  if log.stat().st_size>16*1024*1024:reason='16MiB output cap';break
  time.sleep(.2)
 e['processCleanup']=stop(p);e.update(exitCode=p.wait(timeout=5),finishedUTC=now(),sha256=sha(log));flush();print(name+': '+str(e['exitCode']),flush=True)
 if reason or e['exitCode'] not in allowed or not e['processCleanup']['groupAbsent']:raise RuntimeError(name+' failed: '+str(reason or e['exitCode']))
 return log.read_text(errors='replace').strip()

def adb(name,args,timeout=45,allowed=(0,)):return run(name,[ADB,'-P',R['adbServerPort'],'-s',R['targetSerial'],*args],timeout,allowed)
def bind(port):
 s=socket.socket();s.bind(('127.0.0.1',port));s.listen(1);SOCKETS.append(s);return s.getsockname()[1]

flush()
try:
 assert sha(APK)==R['apkSHA256'],'retained APK changed'
 changed=[p for p,h in LOCK['files'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
 assert not changed,'current sources changed: '+repr(changed)
 R['sourceStableAtStart']=True
 for candidate in range(5570,5584,2):
  n=len(SOCKETS)
  try:bind(candidate);bind(candidate+1);PORT=candidate;break
  except OSError:
   for s in SOCKETS[n:]:s.close()
   del SOCKETS[n:]
 assert PORT is not None,'no free emulator pair'
 serverport=bind(0);R.update(adbServerPort=str(serverport),emulatorPort=PORT,targetSerial='emulator-'+str(PORT))
 ENV.update(ANDROID_ADB_SERVER_PORT=str(serverport),ADB_SERVER_PORT=str(serverport))
 name='mixer_20261107_android_'+WORK.name.rsplit('-',1)[-1];avd=WORK/'avds'/str(name+'.avd');R['avd']={'name':name,'path':str(avd)}
 run('runtime-create-owned-avd',[SDK/'cmdline-tools/latest/bin/avdmanager','--verbose','create','avd','--name',name,'--path',avd,'--package','system-images;android-37.0;google_apis;arm64-v8a','--device','pixel_6'],120)
 with (avd/'config.ini').open('a') as f:f.write('\nhw.cpu.ncore=2\nhw.ramSize=2048\ndisk.dataPartition.size=2G\n')
 save(OUT/'runtime-owned-avd-config.json',{'config':(avd/'config.ini').read_text(),'ini':(WORK/'avds'/str(name+'.ini')).read_text(),'environment':{k:v for k,v in ENV.items() if k.startswith(('ANDROID_','ADB_'))}})
 for s in SOCKETS:s.close()
 SOCKETS.clear()
 SERVER=launch('runtime-private-adb-server',[ADB,'-P',serverport,'-s',R['targetSerial'],'--one-device',R['targetSerial'],'server','nodaemon'])
 time.sleep(1)
 assert SERVER[0].poll() is None,'private adb server failed'
 EMU=launch('runtime-owned-emulator',[SDK/'emulator/emulator','-avd',name,'-port',PORT,'-no-window','-no-audio','-no-boot-anim','-no-snapshot','-cores','2','-memory','2048','-gpu','swiftshader','-no-metrics','-no-sim'])
 R['nativeInstancesStarted']=1;R['status']='booting';flush();bootlimit=min(time.monotonic()+240,DEADLINE-150);ready=False
 for i in range(80):
  if time.monotonic()>bootlimit or EMU[0].poll() is not None:break
  text=adb('runtime-boot-'+str(i),['shell','getprop','sys.boot_completed'],8,(0,1))
  if text=='1':ready=True;break
  time.sleep(2)
 assert ready,'owned emulator failed its single bounded boot attempt'
 for prop in ['ro.kernel.qemu','ro.boot.qemu.avd_name','ro.build.version.sdk','ro.build.version.release','ro.product.cpu.abi','ro.build.fingerprint','ro.product.model']:
  R['runtime'][prop]=adb('runtime-target-'+prop,['shell','getprop',prop])
 assert R['runtime']['ro.kernel.qemu']=='1' and R['runtime']['ro.boot.qemu.avd_name']==name,'emulator ownership mismatch'
 assert int(R['runtime']['ro.build.version.sdk'])>=36 and R['runtime']['ro.product.cpu.abi']=='arm64-v8a','unsupported emulator API/ABI'
 adb('runtime-install-canonical-apk',['install','--no-streaming','--no-incremental',APK],100)
 R['installedPath']=adb('runtime-installed-package',['shell','pm','path','dev.mixer.android.coordinator.test'])
 text=adb('runtime-canonical-instrumentation',['shell','am','instrument','-w','-r','dev.mixer.android.coordinator.test/dev.mixer.android.NativeCoordinatorV2IntegrationInstrumentation'],120)
 passed='INSTRUMENTATION_CODE: -1' in text and 'failure=' not in text and 'cleanupFailure=' not in text
 R.update(status='passed-smoke' if passed else 'failed-smoke',instrumentationOutput=text,smokePassed=passed)
 adb('runtime-logcat',['logcat','-d','-v','threadtime','-t','1800'],45)
except BaseException as e:
 R.update(status='failed',failure=str(e));(OUT/'runtime-failure.log').write_text(traceback.format_exc());print('FAILED: '+str(e),flush=True)
finally:
 if EMU and EMU[0].poll() is None:
  try:adb('runtime-stop-only-owned-emulator',['emu','kill'],15,(0,1))
  except BaseException as e:R['cleanup']['gracefulStopError']=str(e)
 groups=[]
 for p,e,log in reversed(OWNED):
  d=stop(p);e.update(exitCode=p.poll(),finishedUTC=now(),sha256=sha(log),processCleanup=d);groups.append(d)
 for s in SOCKETS:s.close()
 ports={}
 if PORT is not None:
  for port in [PORT,PORT+1,int(R['adbServerPort'])]:
   s=socket.socket()
   try:s.bind(('127.0.0.1',port));ports[str(port)]='released'
   except OSError as e:ports[str(port)]=str(e)
   finally:s.close()
 changed={p:{'before':h,'after':sha(ROOT/p) if (ROOT/p).is_file() else None} for p,h in LOCK['files'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h}
 R['sourceStable']=not changed;save(OUT/'runtime-source-postflight.json',{'changedInputs':changed,'inputCount':len(LOCK['files'])})
 R['cleanup'].update(groups=groups,allOwnedGroupsClosed=all(g['groupAbsent'] for g in groups),ports=ports)
 if R['cleanup']['allOwnedGroupsClosed']:shutil.rmtree(WORK);R['cleanup']['scratchRemoved']=not WORK.exists()
 else:R['cleanup']['scratchRemoved']=False
 R.update(finishedUTC=now(),elapsedSeconds=round(time.monotonic()-START,2));flush()
 summary=dict(BUILD);summary.update(status=R['status'],runtimeReceipt='runtime-receipt.json',runtime=R['runtime'],runtimeOutcome={k:R.get(k) for k in ['smokePassed','failure','instrumentationOutput']},nativeInstancesStarted=R['nativeInstancesStarted'],sourceStable=BUILD['sourceStable'] and R['sourceStable'],cleanup={'build':BUILD['cleanup'],'runtime':R['cleanup']},finishedUTC=R['finishedUTC'],buildCount=1,emulatorAttemptCount=R['nativeInstancesStarted']);save(OUT/'receipt.json',summary)
 print(json.dumps({k:R.get(k) for k in ['status','failure','smokePassed','elapsedSeconds','sourceStable','nativeInstancesStarted']}),flush=True)
