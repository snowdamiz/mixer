#!/usr/bin/env python3
"""Compile actual Observer plus a frozen, explicit independently authored leaf list."""
import argparse
import datetime
import os
from pathlib import Path
import sys
from environment_host_commands import HostCommands, PROFILE, SUPPORT, STRIP, check, freeze_sources, ident, save

REPOSITORY = Path(__file__).resolve().parents[3]
BASE = 'native/android/tests/NativeEnvironmentV2ObserverHostLeaves/'
LEAVES = (
    'android/animation/ValueAnimator.java','android/app/Activity.java', 'android/app/UiModeManager.java',
    'android/content/ComponentCallbacks.java', 'android/content/ContentResolver.java',
    'android/content/Context.java', 'android/content/res/Configuration.java',
    'android/content/res/Resources.java', 'android/database/ContentObserver.java',
    'android/graphics/Insets.java', 'android/net/Uri.java', 'android/os/Build.java',
    'android/os/Handler.java', 'android/os/LocaleList.java', 'android/os/Looper.java',
    'android/provider/Settings.java', 'android/util/DisplayMetrics.java',
    'android/util/TypedValue.java', 'android/view/View.java', 'android/view/ViewTreeObserver.java',
    'android/view/Window.java', 'android/view/WindowInsets.java',
    'android/view/accessibility/AccessibilityManager.java', 'android/widget/FrameLayout.java',
    'dev/mixer/android/AppearanceDescriptorV2.java', 'dev/mixer/android/AppearanceGeometryV2.java',
    'dev/mixer/android/AppearanceResolverV2.java', 'dev/mixer/android/NativeRenderer.java',
    'dev/mixer/android/ObserverHostProbe.java',
)
SOURCES = (PROFILE, 'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java',
           'native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java',
           'native/android/tests/NativeEnvironmentV2ObserverHostTests.java') + tuple(BASE + p for p in LEAVES)

SELF = 'native/android/tests/run-environment-observer-host.py'

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--jdk',type=Path,default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
    parser.add_argument('--active-seconds',type=float,default=240)
    args=parser.parse_args(argv)
    check(0 < args.active_seconds <= 240, 'finite active budget required')
    evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
    scratch=evidence/'scratch';scratch.mkdir()
    env=dict(os.environ)
    stripped={key:key in env for key in STRIP}
    for key in STRIP:env.pop(key,None)
    env.update(TMPDIR=str(scratch),PYTHONDONTWRITEBYTECODE='1')
    commands=HostCommands(evidence,scratch,env,active_seconds=args.active_seconds)
    receipt={'schema':2,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':list(argv) if argv is not None else sys.argv[1:],'python':sys.version,'scope':'Java17 host execution of actual Observer with faulting Android/renderer leaves; no native behavior','status':'failed','ci_revision':os.environ.get('GITHUB_SHA'),'environment':{'platform':os.uname().sysname,'machine':os.uname().machine,'stripped_implicit_jvm_variables':stripped},'native_or_capture_processes_started_or_queried':False,'new_dependencies':[]}
    frozen={}
    try:
        frozen,fqcn=freeze_sources(REPOSITORY,SOURCES)
        for source in (SELF,*SUPPORT):frozen[source]=(REPOSITORY/source).read_bytes()
        freeze={'ci_revision':os.environ.get('GITHUB_SHA'),'revision_query':'no subprocess; exact frozen bytes below','files':{s:ident(data) for s,data in frozen.items()}}
        save(evidence/'source-freeze.json',freeze)
        save(evidence/'source-closure.json',{'sources':SOURCES,'fqcn':fqcn})
        for source,data in frozen.items():
            target=evidence/'inputs'/source;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir()
        jdk=args.jdk.resolve(strict=True)
        tools={name:(jdk/'bin'/name).resolve(strict=True) for name in ('java','javac')}
        env['JAVA_HOME']=str(jdk)
        plans={name+'-version':([tool,'-version'],10) for name,tool in tools.items()}
        plans['compile']=([tools['javac'],'-J-Xmx256m','-J-XX:ActiveProcessorCount=2','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*[evidence/'inputs'/s for s in SOURCES]],60)
        plans['host']=([tools['java'],'-ea','-Xmx128m','-XX:ActiveProcessorCount=2','-cp',classes,'dev.mixer.android.NativeEnvironmentV2ObserverHostTests'],30)
        commands.prepare(frozen,tools,plans)
        receipt['status']='PREPARED';save(evidence/'receipt.json',receipt)
        for name in tools:commands.run(name+'-version')
        commands.run('compile')
        receipt['classes']={str(p.relative_to(classes)):ident(p.read_bytes()) for p in sorted(classes.rglob('*.class'))}
        result=commands.run('host');check(result.startswith(b'PASS '),'missing explicit host success')
        receipt['host_stdout']=result.decode().strip();receipt['status']='passed-host-only';print(result.decode().strip())
    except BaseException as error:
        receipt['failure']={'type':type(error).__name__,'message':str(error)};receipt['status']='failed'
    finally:
        receipt['pending']=['Native Android runtime and final phones','Public V2 integration','GA qualification']
        commands.finalize(REPOSITORY,frozen,receipt,success_statuses=('passed-host-only',))
    return 0 if receipt['status']=='passed-host-only' else 1

if __name__=='__main__':sys.exit(main())
