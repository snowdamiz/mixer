#!/usr/bin/env python3
"""Bounded actual-source host and Java/D8 closures. No Git, native runtime or capture."""
import argparse, datetime, hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PLATFORM='native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'
ENV='native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java'
SELF='native/android/tests/run-environment-platform-host.py'
SELECTION='verification/android-environment-platform-root-review/selection.json'
ROSTER='verification/android-private-owner-effect-roster-amendment/required-host-roster.json'
LEAF='native/android/tests/NativeEnvironmentV2ObserverHostLeaves/'
# Deliberately finite leaf closure. The shared descriptor/resolver/geometry are actual sources.
LEAVES=('android/app/Activity.java','android/app/UiModeManager.java','android/content/ComponentCallbacks.java','android/content/ContentResolver.java','android/content/Context.java','android/content/res/Configuration.java','android/content/res/Resources.java','android/database/ContentObserver.java','android/graphics/Insets.java','android/net/Uri.java','android/os/Build.java','android/os/Handler.java','android/os/LocaleList.java','android/os/Looper.java','android/provider/Settings.java','android/util/DisplayMetrics.java','android/util/TypedValue.java','android/view/View.java','android/view/ViewTreeObserver.java','android/view/Window.java','android/view/WindowInsets.java','android/view/accessibility/AccessibilityManager.java','android/widget/FrameLayout.java','dev/mixer/android/NativeRenderer.java','dev/mixer/android/ObserverHostProbe.java')
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--closure',choices=('environment','A','B','cross'),default='environment');p.add_argument('--jdk',type=Path,default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'));a=p.parse_args()
 evidence=a.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
 roster=json.loads((ROOT/ROSTER).read_text());selection=json.loads((ROOT/SELECTION).read_text())
 if a.closure=='environment':
  sources=[ENV,PLATFORM]+['native/android/app/src/dev/mixer/android/'+n+'.java' for n in ('AppearanceDescriptorV2','AppearanceResolverV2','AppearanceGeometryV2','Json','UiPacket')]+[LEAF+s for s in LEAVES]+['native/android/tests/NativeEnvironmentV2ObserverHostTests.java','native/android/tests/NativeEnvironmentPlatformV2HostTests.java']
 else:
  closure=roster['closures']['A-orchestration' if a.closure=='A' else 'B-concrete-renderer-views'];sources=closure['actual_production_sources']+[PLATFORM]
  if a.closure=='cross':sources+=['native/android/app/src/dev/mixer/android/NativeBridge.java']
  else:sources += [s['source'] for s in closure['substitutes']]+closure['test_support_sources']+[closure['test_source']]
 auxiliary=[SELF,SELECTION,ROSTER,'verification/android-private-owner-integration-implementation/barrier-map.json','verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json']
 if len(sources)!=len(set(sources)):raise RuntimeError('duplicate finite source')
 frozen={s:(ROOT/s).read_bytes() for s in sources+auxiliary}
 for s,b in frozen.items():
  target=evidence/'inputs'/s;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 save(evidence/'source-map.json',{s:ident(b) for s,b in frozen.items()})
 save(evidence/'source-closure.json',{'sources':sources,'auxiliary':auxiliary})
 env=dict(os.environ);strip=('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS')
 for name in strip:env.pop(name,None)
 commands=[];scratch=Path(tempfile.mkdtemp(prefix='environment-platform-owned-',dir=evidence))
 receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'context_revision':selection['context_revision'],'context_revision_is_inherited_not_live_git':True,'closure':a.closure,'status':'failed','scope':'actual Java source host leaves' if a.closure!='cross' else 'official SDK unsigned Java/D8 crosscompile only','native_or_capture_processes_started_or_queried':False,'new_dependencies':[]}
 def run(label,argv,timeout=60):
  outpath=evidence/(label+'.stdout');errpath=evidence/(label+'.stderr');start=time.monotonic();timed=overflow=False
  with outpath.open('wb') as out,errpath.open('wb') as err:
   child=subprocess.Popen([str(v) for v in argv],cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
   try:
    while child.poll() is None:
     timed=time.monotonic()-start>timeout;overflow=max(outpath.stat().st_size,errpath.stat().st_size)>8_000_000
     if timed or overflow:os.killpg(child.pid,signal.SIGKILL);break
     time.sleep(.05)
   finally:
    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
    child.wait()
  commands.append({'label':label,'argv':[str(v) for v in argv],'exit':child.returncode,'seconds':time.monotonic()-start,'timeout':timed,'output_limit_exceeded':overflow,'child_reaped':True,'stdout':ident(outpath.read_bytes()),'stderr':ident(errpath.read_bytes())});save(evidence/'commands.json',commands)
  if child.returncode or timed or overflow:raise RuntimeError(label+' failed; retained '+str(evidence))
  return outpath.read_bytes()
 try:
  jdk=a.jdk.resolve(strict=True);java=jdk/'bin/java';javac=jdk/'bin/javac';javap=jdk/'bin/javap'
  receipt['tools']={str(t):ident(t.resolve().read_bytes()) for t in (java,javac,javap)}
  run('java-version',[java,'-version']);run('javac-version',[javac,'-version']);run('javap-version',[javap,'-version'])
  classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir();classpath=empty
  if a.closure=='cross':
   sdk=Path('/opt/homebrew/share/android-commandlinetools');classpath=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8';receipt['official_android_tools']={str(t):ident(t.read_bytes()) for t in (classpath,d8)}
   env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','');run('d8-version',[d8,'--version'])
  run('compile',[javac,'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',classpath,'-sourcepath',empty,'-d',classes,*[evidence/'inputs'/s for s in sources]])
  classfiles=sorted(classes.rglob('*.class'));save(evidence/'classes.json',{str(f.relative_to(classes)):ident(f.read_bytes()) for f in classfiles})
  # Full constant pools, code and signatures of every emitted environment class.
  inspection={}
  for f in classfiles:
   if f.name.startswith(('NativeEnvironmentV2','NativeEnvironmentPlatformV2')):
    name=str(f.relative_to(classes)).removesuffix('.class').replace('/','.')
    inspection[name]=run('javap-'+f.stem,[javap,'-v','-c','-p','-classpath',classes,name]).decode()
  forbidden=('android/graphics/Insets','android/view/WindowInsets$Type','fontWeightAdjustment','ContrastChangeListener','HighContrastTextStateChangeListener','getContrast:','isHighContrastTextEnabled:','getInsets:')
  isolated=[]
  for name,dump in inspection.items():
   if '$Api' in name:continue
   for symbol in forbidden:
    if symbol in dump:raise RuntimeError('later API leaked into '+name+': '+symbol)
   isolated.append(name)
  save(evidence/'isolation.json',{'checked_emitted_classes':isolated,'forbidden_later_symbols':forbidden,'status':'passed-constant-pool-code-signature-inspection','native_verifier_class_loading':'pending'})
  if a.closure=='cross':
   dex=scratch/'dex';dex.mkdir();run('dex',[d8,'--min-api','28','--lib',classpath,'--output',dex,*classfiles]);save(evidence/'dex.json',{str(f.relative_to(dex)):ident(f.read_bytes()) for f in sorted(dex.rglob('*')) if f.is_file()});receipt['status']='passed-crosscompile-only';print('PASS official JDK/SDK Java/D8 min-api28 crosscompile; runtime/linkage pending')
  else:
   if a.closure=='environment':
    names=['NativeEnvironmentV2ObserverHostTests','NativeEnvironmentPlatformV2HostTests']
    for name in names:
     result=run(name,[java,'-ea','-Xmx128m','-cp',classes,'dev.mixer.android.'+name]);
     if not result.startswith(b'PASS '):raise RuntimeError('missing PASS '+name)
     print(result.decode().strip())
   else:
    descriptor=evidence/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json';mapping=evidence/'inputs/verification/android-private-owner-integration-implementation/barrier-map.json'
    name='NativeOwnerV2'+('Concrete' if a.closure=='B' else '')+'HostTests'
    result=run('host',[java,'-ea','-Xmx256m','-cp',classes,'dev.mixer.android.'+name,descriptor,evidence/'observed-sites.txt',mapping,evidence/'barrier-cases.json'],300)
    if not result.startswith(b'PASS '):raise RuntimeError('missing PASS')
    print(result.decode().strip())
   receipt['status']='passed-host-only'
 except BaseException as failure:receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
 finally:
  shutil.rmtree(scratch);receipt['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':all(c['child_reaped'] for c in commands),'native_or_capture_instances_created':False};receipt['source_stable']=all((ROOT/s).read_bytes()==b for s,b in frozen.items());receipt['pending']=['native API28..36 class loading/runtime','public V2 routing','physical-phone acceptance','immutable separate-repository FieldLog packages','OTA/signing/store/operations/GA'];save(evidence/'receipt.json',receipt)
if __name__=='__main__':main()
