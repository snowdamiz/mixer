#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
D=Path(__file__).resolve().parent
P=D.parent
attempt=sys.argv[1] if len(sys.argv)>1 else '1'
R=D/('controls-'+attempt);R.mkdir(exist_ok=False);S=R/'source';S.mkdir()
for path in sorted((P/'foundation').glob('*.java')):shutil.copyfile(path,S/path.name)
source=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else P/'FocusHistoryControls.java'
shutil.copyfile(source,S/'FocusHistoryControls.java')
CP=D/'frozen/runs/host-1/classes';J=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
classes=R/'classes';classes.mkdir();empty=R/'empty-source';empty.mkdir();commands=[]
env={key:value for key,value in os.environ.items() if key not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVA_OPTIONS','JAVA_OPTS','JDK_JAVAC_OPTIONS'}}
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def run(name,args):
    argv=[str(arg) for arg in args];item={'name':name,'argv':argv,'timeout_seconds':60};commands.append(item)
    child=subprocess.Popen(argv,cwd=D,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:out,err=child.communicate(timeout=60)
    except BaseException:
        child.kill();out,err=child.communicate();item['killed_and_reaped']=True;raise
    finally:item['reaped']=child.poll() is not None
    (R/(name+'.stdout')).write_bytes(out);(R/(name+'.stderr')).write_bytes(err);item['exit_code']=child.returncode
    print(name,child.returncode,out.decode(errors='replace').strip()[-1500:],flush=True);return child.returncode==0
try:
    okay=run('compile',[J/'javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',CP,'-d',classes,*sorted(S.glob('*.java'))])
    if okay:
        cp=str(classes)+os.pathsep+str(CP);descriptor=D/'frozen/descriptor.json'
        cases=sys.argv[3:] if len(sys.argv)>3 else ['prior-focus-values','coexistence','eligible-restore','lost-original-restore','foreign-token-restore','loss-phases','settled-loss-phases','observed-hooks','event-reentry','event-postgetter','scope-imbalance','exhaustion']
        for case in cases:okay=run(case,[J/'java','-ea','-Xmx256m','-cp',cp,'dev.mixer.android.FocusHistoryControls',case,descriptor]) and okay
finally:
    empty.rmdir();receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'source':{path.name:row(path) for path in S.glob('*.java')},'scope':'Independent controls against exact admitted full source classes and unchanged authored host leaves; no native runtime','cleanup':{'children_reaped':all(item['reaped'] for item in commands),'empty_source_removed':not empty.exists(),'native_UI_capture_or_process_inventory':False}}
    (R/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
sys.exit(0 if okay else 1)
