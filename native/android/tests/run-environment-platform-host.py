#!/usr/bin/env python3
"""Bounded actual-source host and Java/D8 closures. No Git, native runtime or capture."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
from environment_host_commands import HostCommands, PROFILE, SUPPORT, STRIP, check, freeze_sources, ident, save
ROOT=Path(__file__).resolve().parents[3]
PLATFORM='native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'
ENV='native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java'
SELF='native/android/tests/run-environment-platform-host.py'
SELECTION='verification/android-environment-platform-root-review/selection.json'
ROSTER='native/android/tests/private-owner-host-roster.json'
LEAF='native/android/tests/NativeEnvironmentV2ObserverHostLeaves/'
# Deliberately finite leaf closure. Shared descriptor/resolver/geometry/profile are actual sources.
LEAVES=('android/animation/ValueAnimator.java','android/app/Activity.java','android/app/UiModeManager.java','android/content/ComponentCallbacks.java','android/content/ContentResolver.java','android/content/Context.java','android/content/res/Configuration.java','android/content/res/Resources.java','android/database/ContentObserver.java','android/graphics/Insets.java','android/net/Uri.java','android/os/Build.java','android/os/Handler.java','android/os/LocaleList.java','android/os/Looper.java','android/provider/Settings.java','android/util/DisplayMetrics.java','android/util/TypedValue.java','android/view/View.java','android/view/ViewTreeObserver.java','android/view/Window.java','android/view/WindowInsets.java','android/view/accessibility/AccessibilityManager.java','android/widget/FrameLayout.java','dev/mixer/android/NativeRenderer.java','dev/mixer/android/ObserverHostProbe.java')

def source_closure(closure, roster):
    if closure=='environment':
        return [ENV,PLATFORM,PROFILE]+['native/android/app/src/dev/mixer/android/'+n+'.java' for n in ('AppearanceDescriptorV2','AppearanceResolverV2','AppearanceGeometryV2','Json','UiPacket')]+[LEAF+s for s in LEAVES]+['native/android/tests/NativeEnvironmentV2ObserverHostTests.java','native/android/tests/NativeEnvironmentPlatformV2HostTests.java']
    selected=roster['closures']['A-orchestration' if closure=='A' else 'B-concrete-renderer-views']
    sources=selected['actual_production_sources']+[PLATFORM]
    if closure=='cross':
        return sources+['native/android/app/src/dev/mixer/android/NativeBridge.java']
    return sources+[s['source'] for s in selected['substitutes']]+selected['test_support_sources']+[selected['test_source']]

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--closure',choices=('environment','A','B','cross'),default='environment')
    parser.add_argument('--jdk',type=Path,default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
    parser.add_argument('--active-seconds',type=float,default=240)
    args=parser.parse_args(argv)
    check(0 < args.active_seconds <= 240, 'finite active budget required')
    # A/B keep the accepted installed dynamic-BCI harness and its admission/custody controls.
    if args.closure in ('A','B'):
        spec=importlib.util.spec_from_file_location('environment_private_owner',ROOT/'native/android/tests/run-private-owner-host.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        return runner.main(['--evidence',str(args.evidence),'--closure',args.closure,'--jdk',str(args.jdk),'--active-seconds',str(args.active_seconds)])
    evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
    scratch=evidence/'scratch';scratch.mkdir()
    env=dict(os.environ)
    for key in STRIP:env.pop(key,None)
    env.update(TMPDIR=str(scratch),PYTHONDONTWRITEBYTECODE='1')
    commands=HostCommands(evidence,scratch,env,active_seconds=args.active_seconds)
    receipt={'schema':2,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':list(argv) if argv is not None else sys.argv[1:],'python':sys.version,'closure':args.closure,'status':'failed','scope':'actual Java source host leaves' if args.closure!='cross' else 'official SDK unsigned Java/D8 crosscompile only','native_or_capture_processes_started_or_queried':False,'new_dependencies':[]}
    frozen={}
    try:
        roster=json.loads((ROOT/ROSTER).read_bytes());selection=json.loads((ROOT/SELECTION).read_bytes())
        sources=source_closure(args.closure,roster)
        frozen,fqcn=freeze_sources(ROOT,sources)
        auxiliary=[SELF,SELECTION,ROSTER,*SUPPORT]
        for source in auxiliary:frozen[source]=(ROOT/source).read_bytes()
        for source,data in frozen.items():
            target=evidence/'inputs'/source;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        save(evidence/'source-map.json',{s:ident(data) for s,data in frozen.items()})
        save(evidence/'source-closure.json',{'sources':sources,'auxiliary':auxiliary,'fqcn':fqcn})
        receipt['context_revision']=selection['context_revision'];receipt['context_revision_is_inherited_not_live_git']=True
        receipt['ci_revision']=os.environ.get('GITHUB_SHA')
        classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir();classpath=empty
        jdk=args.jdk.resolve(strict=True)
        tools={name:(jdk/'bin'/name).resolve(strict=True) for name in ('java','javac','javap')}
        env['JAVA_HOME']=str(jdk)
        plans={name+'-version':([tool,'-version'],10) for name,tool in tools.items()}
        if args.closure=='cross':
            sdk=Path('/opt/homebrew/share/android-commandlinetools');classpath=sdk/'platforms/android-37.0/android.jar'
            tools['d8']=(sdk/'build-tools/37.0.0/d8').resolve(strict=True)
            receipt['official_android_tools']={str(t):ident(t.read_bytes()) for t in (classpath,tools['d8'])}
            env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
            plans['d8-version']=([tools['d8'],'--version'],10)
        plans['compile']=([tools['javac'],'-J-Xmx256m','-J-XX:ActiveProcessorCount=2','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',classpath,'-sourcepath',empty,'-d',classes,*[evidence/'inputs'/s for s in sources]],60)
        # One javap invocation inspects all and only the two emitted environment class families.
        # Expected nested names are unknown until compilation; seal bytecode admission after compilation.
        commands.prepare(frozen,tools,plans)
        receipt['status']='PREPARED';save(evidence/'receipt.json',receipt)
        for name in tools:commands.run(name+'-version')
        commands.run('compile')
        classfiles=sorted(classes.rglob('*.class'))
        save(evidence/'classes.json',{str(f.relative_to(classes)):ident(f.read_bytes()) for f in classfiles})
        names=[str(f.relative_to(classes)).removesuffix('.class').replace('/','.') for f in classfiles if f.stem in ('NativeEnvironmentV2','NativeEnvironmentPlatformV2') or f.name.startswith(('NativeEnvironmentV2$','NativeEnvironmentPlatformV2$'))]
        check(bool(names),'environment classes absent')
        bytecode=[tools['javap'],'-J-Xmx256m','-J-XX:ActiveProcessorCount=2','-v','-c','-p','-classpath',classes,*names]
        commands.add_plan('bytecode',bytecode,30)
        dump=commands.run('bytecode').decode();(evidence/'bytecode.txt').write_text(dump)
        # javap ThisClass headers delimit complete constant-pool/code/signature dumps.
        sections=dump.split('Classfile ')[1:]
        inspection={}
        for section in sections:
            header=section.splitlines()[0]
            matched=[name for name in names if header.endswith('/'+name.replace('.','/')+'.class')]
            check(len(matched)==1,'ambiguous emitted environment class')
            inspection[matched[0]]=section
        check(set(inspection)==set(names),'incomplete emitted environment inspection')
        forbidden=('android/animation/ValueAnimator','DurationScaleChangeListener','android/graphics/Insets','android/view/WindowInsets$Type','fontWeightAdjustment','ContrastChangeListener','HighContrastTextStateChangeListener','getContrast:','isHighContrastTextEnabled:','getInsets:')
        isolated=[]
        for name,text in inspection.items():
            if '$Api' in name:continue
            for symbol in forbidden:check(symbol not in text,'later API leaked into '+name+': '+symbol)
            isolated.append(name)
        save(evidence/'isolation.json',{'checked_emitted_classes':isolated,'forbidden_later_symbols':forbidden,'status':'passed-constant-pool-code-signature-inspection','native_verifier_class_loading':'pending'})
        if args.closure=='cross':
            dex=scratch/'dex';dex.mkdir()
            commands.add_plan('dex',[tools['d8'],'--min-api','28','--lib',classpath,'--output',dex,*classfiles],60)
            commands.run('dex');save(evidence/'dex.json',{str(f.relative_to(dex)):ident(f.read_bytes()) for f in sorted(dex.rglob('*')) if f.is_file()})
            receipt['status']='passed-crosscompile-only'
        else:
            receipt['host_stdout']={}
            for name in ('NativeEnvironmentV2ObserverHostTests','NativeEnvironmentPlatformV2HostTests'):
                commands.add_plan(name,[tools['java'],'-ea','-Xmx128m','-XX:ActiveProcessorCount=2','-cp',classes,'dev.mixer.android.'+name],30)
                result=commands.run(name);check(result.startswith(b'PASS '),'missing PASS '+name)
                receipt['host_stdout'][name]=result.decode().strip();print(result.decode().strip())
            receipt['status']='passed-host-only'
    except BaseException as error:
        receipt['failure']={'type':type(error).__name__,'message':str(error)};receipt['status']='failed'
    finally:
        receipt['pending']=['native API28..36 class loading/runtime','public V2 routing','physical-phone acceptance','immutable separate-repository FieldLog packages','OTA/signing/store/operations/GA']
        commands.finalize(ROOT,frozen,receipt,success_statuses=('passed-host-only','passed-crosscompile-only'))
    print(json.dumps({'status':receipt['status'],'failure':receipt.get('failure'),'receipt':str(evidence/'receipt.json')}))
    return 0 if receipt['status'] in ('passed-host-only','passed-crosscompile-only') else 1

if __name__=='__main__':sys.exit(main())
