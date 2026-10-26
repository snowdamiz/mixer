#!/usr/bin/env python3
"""Independent finite actual-source JVM/crosscompile review; no Git/native/UI."""
import datetime, hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OWN=Path(__file__).resolve().parent
def ident(data): return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def identity(path): return ident(path.read_bytes())
PRODUCER='verification/android-environment-platform-implementation/'
SELECTION='verification/android-environment-platform-root-review/selection.json'
LEAF='native/android/tests/NativeEnvironmentV2ObserverHostLeaves/'
LEAVES=('android/app/Activity.java','android/app/UiModeManager.java','android/content/ComponentCallbacks.java','android/content/ContentResolver.java','android/content/Context.java','android/content/res/Configuration.java','android/content/res/Resources.java','android/database/ContentObserver.java','android/graphics/Insets.java','android/net/Uri.java','android/os/Build.java','android/os/Handler.java','android/os/LocaleList.java','android/os/Looper.java','android/provider/Settings.java','android/util/DisplayMetrics.java','android/util/TypedValue.java','android/view/View.java','android/view/ViewTreeObserver.java','android/view/Window.java','android/view/WindowInsets.java','android/view/accessibility/AccessibilityManager.java','android/widget/FrameLayout.java','dev/mixer/android/NativeRenderer.java','dev/mixer/android/ObserverHostProbe.java')
PRODUCTION='native/android/app/src/dev/mixer/android/'
HOST=[PRODUCTION+n+'.java' for n in ('NativeEnvironmentV2','NativeEnvironmentPlatformV2','AppearanceDescriptorV2','AppearanceResolverV2','AppearanceGeometryV2','Json','UiPacket')]
CROSS=[PRODUCTION+n+'.java' for n in ('NativeOwnerV2','OwnerLifecycleV2','NativeCoordinatorV2','NativeRenderer','NativeEnvironmentV2','NativeAppearanceViewsV2','InstalledAppearanceV2','UiPacket','Json','AppearanceDescriptorV2','AppearanceGeometryV2','AppearanceResolverV2','AppearanceNativePathsV2','AuthoredToggleInputV2','NativeEnvironmentPlatformV2','NativeBridge')]
def main():
    attempt=sys.argv[1] if len(sys.argv)>1 else 'attempt-1'
    evidence=OWN/attempt;evidence.mkdir(exist_ok=False)
    selection=ROOT/SELECTION;manifest=ROOT/(PRODUCER+'manifest.json')
    assert identity(selection)['sha256']=='55214c11fcf73b9a788421e70a99546f696a72b76183001ad3ed93e3639c6ba7'
    assert identity(manifest)['sha256']=='161c47daa9c07cd01252327f31b814ed3a3f708587f2ed84adaee81b902cfacf'
    candidate=json.loads(manifest.read_text())
    # This exact manifest names the bounded native packet, not a hosted harness.
    checked={p:{'expected':v,'actual':identity(ROOT/p)} for p,v in candidate['files'].items()}
    assert all(v['expected']==v['actual'] for v in checked.values())
    preserve=json.loads((ROOT/(PRODUCER+'canonical-preservation.json')).read_text())
    protected={p:{'expected':v['expected'],'actual':identity(ROOT/p)} for p,v in preserve['checked'].items()}
    # Independently compare native JNI/Swift/core bridge bytes to the accepted C5 frozen map.
    c5_path='verification/android-private-owner-independent-review/implementation-review-4/candidate-5/source-map.json'
    c5=json.loads((ROOT/c5_path).read_text());c5files=c5.get('files',c5)
    for p,v in c5files.items():
        if p.startswith(('native/android/bridge/','native/android/engine/Sources/','sdk/Sources/')) or p==PRODUCTION+'NativeBridge.java':
            protected[p]={'expected':v,'actual':identity(ROOT/p)}
    assert all(v['expected']==v['actual'] for v in protected.values()),'protected drift'
    save(evidence/'custody.json',{'selection':identity(selection),'producer_manifest':identity(manifest),'producer_members':len(checked),'all_producer_members_match':True,'protected':protected,'c5_baseline':{'path':c5_path,**identity(ROOT/c5_path)},'CLI_read_or_hashed':False})
    aux=[SELECTION,PRODUCER+'manifest.json',PRODUCER+'canonical-preservation.json','verification/android-api28-v2-support-prerequisite/contract.json','verification/android-api28-v2-support-prerequisite-independent/acceptance.json','verification/android-private-owner-integration-implementation/barrier-map.json','verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json']
    test=str((OWN/'IndependentEnvironmentTests.java').relative_to(ROOT));runner=str(Path(__file__).relative_to(ROOT))
    frozen={p:(ROOT/p).read_bytes() for p in dict.fromkeys(HOST+CROSS+[LEAF+p for p in LEAVES]+aux+[test,runner])}
    for p,b in frozen.items():
        dst=evidence/'inputs'/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
    # Two independent per-instance manager leaves expose fresh-read versus retained-listener targets.
    # Other framework leaves are the candidate's finite fault/reentry support, not Android execution.
    mode='''package android.app;
public final class UiModeManager {
 public float local;
 public interface ContrastChangeListener { void onContrastChanged(float contrast); }
 public void addContrastChangeListener(java.util.concurrent.Executor executor,ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.executors[5]=executor;dev.mixer.android.ObserverHostProbe.add(5,this,listener); }
 public void removeContrastChangeListener(ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(5,this,listener); }
 public float getContrast() { dev.mixer.android.ObserverHostProbe.read("contrast",34);return local+dev.mixer.android.ObserverHostProbe.contrast; }
}
'''
    high='''package android.view.accessibility;
public final class AccessibilityManager {
 public boolean local;
 public interface HighContrastTextStateChangeListener { void onHighContrastTextStateChanged(boolean enabled); }
 public void addHighContrastTextStateChangeListener(java.util.concurrent.Executor executor,HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.executors[6]=executor;dev.mixer.android.ObserverHostProbe.add(6,this,listener); }
 public void removeHighContrastTextStateChangeListener(HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(6,this,listener); }
 public boolean isHighContrastTextEnabled() { dev.mixer.android.ObserverHostProbe.read("high",36);return local||dev.mixer.android.ObserverHostProbe.highContrast; }
}
'''
    overrides={LEAF+'android/app/UiModeManager.java':mode,LEAF+'android/view/accessibility/AccessibilityManager.java':high}
    override_paths={}
    for p,s in overrides.items():
        dst=evidence/'independent-leaves'/p.removeprefix(LEAF);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(s);override_paths[p]=dst
    save(evidence/'source-map.json',{p:ident(b) for p,b in frozen.items()})
    save(evidence/'substitutions.json',{p:{'original':ident(frozen[p]),'independent_leaf':identity(dst),'purpose':'per-instance public manager read with finite add/remove/fault hooks'} for p,dst in override_paths.items()})
    env=dict(os.environ)
    for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
    jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home').resolve(strict=True)
    java,javac,javap=[jdk/'bin'/p for p in ('java','javac','javap')]
    sdk=Path('/opt/homebrew/share/android-commandlinetools');android=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8'
    env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
    tools=[java,javac,javap,jdk/'release',jdk/'lib/modules',android,d8,d8.parent/'lib/d8.jar',sdk/'platforms/android-37.0/data/api-versions.xml']
    commands=[];scratch=Path(tempfile.mkdtemp(prefix='independent-owned-',dir=evidence));receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'python':sys.version,'tools':{str(p):identity(p) for p in tools},'context_revision':candidate['context_revision'],'context_revision_inherited_not_live_Git':True,'status':'failed','scope':'independent actual source JVM tests, official SDK Java/D8 compile and emitted class inspection only','native_capture_UI_process_inventory_or_Git':False,'CLI_read_or_hashed':False}
    def run(name,argv,timeout=60):
        start=time.monotonic();out=evidence/(name+'.stdout');err=evidence/(name+'.stderr');timed=overflow=False
        with out.open('wb') as o,err.open('wb') as e:
            child=subprocess.Popen([str(v) for v in argv],cwd=ROOT,env=env,stdout=o,stderr=e,start_new_session=True)
            try:
                while child.poll() is None:
                    timed=time.monotonic()-start>timeout;overflow=max(out.stat().st_size,err.stat().st_size)>8_000_000
                    if timed or overflow:os.killpg(child.pid,signal.SIGKILL);break
                    time.sleep(.025)
            finally:
                if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
                child.wait()
        record={'name':name,'argv':[str(x) for x in argv],'exit':child.returncode,'seconds':time.monotonic()-start,'timed_out':timed,'overflow':overflow,'owned_child_reaped':True,'stdout':identity(out),'stderr':identity(err)}
        commands.append(record);save(evidence/'commands.json',commands)
        if child.returncode or timed or overflow:raise RuntimeError(name+' failed; see retained output')
        return out.read_text()
    try:
        for name,tool in [('java',java),('javac',javac),('javap',javap),('d8',d8)]:run(name+'-version',[tool,'--version' if name=='d8' else '-version'])
        empty=scratch/'empty';empty.mkdir();classes=scratch/'host';classes.mkdir()
        host=HOST+[LEAF+p for p in LEAVES]+[test]
        sourcepaths=[override_paths.get(p,evidence/'inputs'/p) for p in host]
        run('host-compile',[javac,'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sourcepaths])
        result=run('independent-host',[java,'-ea','-Xmx128m','-XX:ActiveProcessorCount=2','-cp',classes,'dev.mixer.android.IndependentEnvironmentTests'])
        assert result.startswith('PASS '),result
        cross=scratch/'cross';cross.mkdir();run('official-crosscompile',[javac,'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',android,'-sourcepath',empty,'-d',cross,*[evidence/'inputs'/p for p in CROSS]])
        save(evidence/'classes.json',{str(p.relative_to(cross)):identity(p) for p in sorted(cross.rglob('*.class'))})
        inspected=[]
        forbidden=('android/graphics/Insets','android/view/WindowInsets$Type','fontWeightAdjustment','ContrastChangeListener','HighContrastTextStateChangeListener','getContrast:','isHighContrastTextEnabled:','getInsets:')
        for p in sorted(cross.rglob('NativeEnvironment*.class')):
            name=str(p.relative_to(cross)).removesuffix('.class').replace('/','.')
            dump=run('inspect-'+p.stem,[javap,'-v','-c','-p','-classpath',cross,name])
            if '$Api' not in name:
                assert all(s not in dump for s in forbidden),name
                inspected.append(name)
        save(evidence/'isolation.json',{'classes_checked':inspected,'forbidden':forbidden,'result':'passed emitted constant pools, signatures and code; native verifier pending'})
        dex=scratch/'dex';dex.mkdir();run('official-dex',[d8,'--min-api','28','--lib',android,'--output',dex,*sorted(cross.rglob('*.class'))])
        save(evidence/'dex.json',{str(p.relative_to(dex)):identity(p) for p in dex.rglob('*') if p.is_file()})
        receipt['status']='passed-independent-host-crosscompile-and-inspection-only';receipt['host_output']=result.strip();print(result.strip())
    except BaseException as e:receipt['failure']={'type':type(e).__name__,'message':str(e)};raise
    finally:
        shutil.rmtree(scratch);receipt['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':all(c['owned_child_reaped'] for c in commands),'native_capture_or_UI_instances_started':False}
        receipt['frozen_inputs_stable']=all((ROOT/p).read_bytes()==b for p,b in frozen.items())
        receipt['pending']=['Android API28..36 class loading/runtime and whole-library compatibility','public V2 routing','TalkBack/design parity/final physical phones','separate repository FieldLog immutable packages','OTA/signing/store/operations/accountable GA','separate source-profile4 CLI review']
        save(evidence/'receipt.json',receipt)
if __name__=='__main__':main()
