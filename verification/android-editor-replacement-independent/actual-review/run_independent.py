#!/usr/bin/env python3
"""Bounded controls over admitted complete-source classes; no Android runtime."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, datetime
D=Path(__file__).resolve().parent
P=D.parent
R=D/('independent-controls'+('-'+sys.argv[1] if len(sys.argv)>1 else ''))
R.mkdir(exist_ok=False)
S=R/'source';S.mkdir()
sources=[P/'ReplacementReviewControls.java', P.parent/'android-editor-implementation-independent/DescriptorClosure.java']
if len(sys.argv)>1 and sys.argv[1] in {'4','5','6'}: sources.append(D/'AdditionalReplacementControls.java')
for src in sources:
    shutil.copyfile(src,S/src.name)
control=S/'ReplacementReviewControls.java'
control.write_text(control.read_text().replace('"two-field fixture publication"','"two-field fixture publication: "+owner.cleanupLedger().primary()'))
if len(sys.argv)>1 and sys.argv[1]!='2':
    control.write_text(control.read_text().replace('Json.map("id","a","generation",new Json.Num("1"))','Json.map("id","a","generation",new Json.Num("2"))').replace('Json.map("id","b","generation",new Json.Num("1"))','Json.map("id","b","generation",new Json.Num("3"))'))
J=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
C=D/'frozen/runs/host-1/classes'
env={k:v for k,v in os.environ.items() if k not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVA_OPTIONS'}}
commands=[]
def run(name,args):
    command=[str(v) for v in args]
    record={'name':name,'command':command,'timeout_seconds':60}
    commands.append(record)
    child=subprocess.Popen(command,cwd=D,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try: out,err=child.communicate(timeout=60)
    except BaseException:
        child.kill();out,err=child.communicate();record['killed_and_reaped']=True;raise
    finally: record['reaped']=child.poll() is not None
    (R/(name+'.stdout')).write_bytes(out);(R/(name+'.stderr')).write_bytes(err)
    record['exit_code']=child.returncode
    print(name,child.returncode,out.decode(errors='replace').strip(),flush=True)
    return child.returncode==0
classes=R/'classes';classes.mkdir()
empty=R/'empty-source';empty.mkdir()
try:
    run('javac-version',[J/'javac','-version']);run('java-version',[J/'java','-version'])
    okay=run('compile',[J/'javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',C,'-d',classes,*sorted(S.glob('*.java'))])
    if okay:
        cp=str(classes)+os.pathsep+str(C)
        if len(sys.argv)>1 and sys.argv[1] in {'4','5','6'}:
            cases={'4':['final-balance','tuple-after-getter','captured-target'],'5':['focus-history-observation'],'6':['blurred-A-replacement','focused-B-echo-after-A-blur']}[sys.argv[1]]
            for case in cases:
                okay=run(case,[J/'java','-ea','-cp',cp,'dev.mixer.android.AdditionalReplacementControls',case,D/'frozen/runs/host-1/inputs/descriptor.json']) and okay
        else:
            for case in ['admission-order','positive-values','foreign-dispatch','selection-postevent','annotation-mutable-bundle','snapshot-reservation']:
                okay=run(case,[J/'java','-ea','-cp',cp,'dev.mixer.android.ReplacementReviewControls',case,D/'frozen/runs/host-1/inputs/descriptor.json']) and okay
            okay=run('descriptor-closure',[J/'java','-ea','-cp',cp,'DescriptorClosure','dev.mixer.android.NativeEditorConnectionV2$Api34']) and okay
finally:
    empty.rmdir()
    receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'scope':'JVM actual complete-source classes with authored Android/JNI leaves; no Android runtime','source':{str(p.relative_to(R)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in S.glob('*.java')},'children_reaped':all(v.get('reaped') for v in commands),'native_or_capture_started_or_queried':False,'preaccess_source_modified':False}
    (R/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
sys.exit(0 if okay else 1)
