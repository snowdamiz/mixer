#!/usr/bin/env python3
"""Complete copied sources; JVM controlled leaves or unsigned pinned SDK cross compilation."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,tempfile,datetime,time
D=Path(__file__).resolve().parents[1];R=D.parents[1]
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
mode=sys.argv[1];runs=D/'runs';runs.mkdir(exist_ok=True);idx=1
while (runs/f'{mode}-{idx}').exists():idx+=1
E=runs/f'{mode}-{idx}';E.mkdir();commands=[];status='failed'
env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');sdk=Path('/opt/homebrew/share/android-commandlinetools');jar=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8'
env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
scratch=Path(tempfile.mkdtemp(prefix='editor-implementation-',dir=E));classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
def run(name,argv):
 start=time.monotonic()
 with (E/(name+'.stdout')).open('wb') as out,(E/(name+'.stderr')).open('wb') as err:
  p=subprocess.Popen([str(a) for a in argv],cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
  try:p.wait(timeout=60)
  except BaseException:p.kill();p.wait();raise
 commands.append({'name':name,'argv':[str(a) for a in argv],'exit':p.returncode,'elapsed':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr')),'reaped':True});save(E/'commands.json',commands)
 if p.returncode:raise RuntimeError(name+' failed; '+str(E/(name+'.stderr')))
 return (E/(name+'.stdout')).read_text()
try:
 for folder in ('source','host-leaves','tests','scripts','cross-source'):shutil.copytree(D/folder,E/'inputs'/folder)
 files=sorted((E/'inputs/source').glob('*.java'))
 if mode=='host':files+=sorted((E/'inputs/host-leaves').rglob('*.java'))+sorted((E/'inputs/tests').glob('*.java'))
 if mode=='cross':files=[p for p in files if p.name!='NativeBridge.java'];files.append(E/'inputs/cross-source/NativeBridge.java')
 save(E/'source-map.json',{str(p.relative_to(E/'inputs')):ident(p) for p in sorted((E/'inputs').rglob('*')) if p.is_file()})
 run('javac-version',[jdk/'bin/javac','-version']);run('java-version',[jdk/'bin/java','-version'])
 run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty if mode=='host' else jar,'-sourcepath',empty,'-d',classes,*files])
 shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 if mode=='host':print(run('host',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.EditorImplementationTests',R/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json']).strip())
 if mode=='cross':
  run('d8-version',[d8,'--version']);run('sdk-descriptors',[jdk/'bin/javap','-p','-s','-classpath',jar,'android.view.inputmethod.InputConnection']);dex=scratch/'dex';dex.mkdir();run('dex',[d8,'--min-api','28','--lib',jar,'--output',dex,*sorted(classes.rglob('*.class'))]);shutil.copytree(dex,E/'dex');save(E/'dex-map.json',{str(p.relative_to(dex)):ident(p) for p in sorted(dex.rglob('*')) if p.is_file()})
 run('descriptors',[jdk/'bin/javap','-p','-s','-c','-classpath',classes,'dev.mixer.android.NativeEditorConnectionV2$Base','dev.mixer.android.NativeEditorConnectionV2$Api31','dev.mixer.android.NativeEditorConnectionV2$Api33','dev.mixer.android.NativeEditorConnectionV2$Api34'])
 status='passed-'+mode+'-only';print(status,str(E.relative_to(R)))
finally:
 shutil.rmtree(scratch)
 save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'scope':'complete-source Java with controlled authored Android/JNI leaves' if mode=='host' else 'unsigned Java/D8 only','commands':len(commands),'tools':{str(p):ident(p.resolve()) for p in (jdk/'bin/javac',jdk/'bin/java',jar,d8)},'cleanup':{'scratch_removed':not scratch.exists(),'children_reaped':all(c['reaped'] for c in commands),'native_or_capture_processes_started_or_queried':False}})
