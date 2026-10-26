#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
D=Path(__file__).resolve().parent
R=D/'controls-extra';R.mkdir(exist_ok=False);S=R/'source';S.mkdir();shutil.copyfile(D/'AdditionalFocusAuditControls.java',S/'AdditionalFocusAuditControls.java')
C=R/'classes';C.mkdir();E=R/'empty-source';E.mkdir();CP=D/'frozen/runs/host-1/classes';J=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
env={key:value for key,value in os.environ.items() if key not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVA_OPTIONS','JAVA_OPTS','JDK_JAVAC_OPTIONS'}}
commands=[]
def run(name,args):
    argv=[str(arg) for arg in args];item={'name':name,'argv':argv,'timeout_seconds':60};commands.append(item);child=subprocess.Popen(argv,cwd=D,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:out,err=child.communicate(timeout=60)
    except BaseException:
        child.kill();out,err=child.communicate();raise
    finally:item['reaped']=child.poll() is not None
    (R/(name+'.stdout')).write_bytes(out);(R/(name+'.stderr')).write_bytes(err);item['exit_code']=child.returncode;print(name,child.returncode,out.decode(errors='replace').strip(),flush=True);return child.returncode==0
try:
    okay=run('compile',[J/'javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',E,'-classpath',CP,'-d',C,S/'AdditionalFocusAuditControls.java'])
    if okay:
        for case in ['multiple-with-active-B','event-provenance']:okay=run(case,[J/'java','-ea','-Xmx256m','-cp',str(C)+os.pathsep+str(CP),'dev.mixer.android.AdditionalFocusAuditControls',case,D/'frozen/descriptor.json']) and okay
finally:
    E.rmdir();(R/'receipt.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'source_sha256':hashlib.sha256((S/'AdditionalFocusAuditControls.java').read_bytes()).hexdigest(),'scope':'Actual complete source with unchanged authored host leaves; no native runtime','cleanup':{'children_reaped':all(item['reaped'] for item in commands),'empty_source_removed':not E.exists(),'native_UI_capture_or_process_inventory':False}},indent=2)+'\n')
sys.exit(0 if okay else 1)
