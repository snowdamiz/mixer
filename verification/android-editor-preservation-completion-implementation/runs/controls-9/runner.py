#!/usr/bin/env python3
"""Owned bounded runner; freezes the exact explicit closure before compiling it."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,tempfile,datetime,time
D=Path(__file__).resolve().parent;R=D.parents[1]
if (D/'seal.json').exists():raise SystemExit('Frozen packet; use a new explicitly owned derivative')
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
mode=sys.argv[1];assert mode in ('host','controls','cross')
runs=D/'runs';runs.mkdir(exist_ok=True);idx=1
while (runs/f'{mode}-{idx}').exists():idx+=1
E=runs/f'{mode}-{idx}';E.mkdir();commands=[];status='failed'
env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');sdk=Path('/opt/homebrew/share/android-commandlinetools');jar=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8'
env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
scratch=Path(tempfile.mkdtemp(prefix='owned-preservation-completion-',dir=E));classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
def run(name,argv):
 start=time.monotonic()
 with (E/(name+'.stdout')).open('wb') as out,(E/(name+'.stderr')).open('wb') as err:
  p=subprocess.Popen([str(a) for a in argv],cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
  try:p.wait(timeout=60)
  except BaseException:p.kill();p.wait();raise
 commands.append({'name':name,'argv':[str(a) for a in argv],'exit':p.returncode,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr')),'reaped':True});save(E/'commands.json',commands)
 if p.returncode:raise RuntimeError(name+' failed: '+str(E/(name+'.stderr')))
 print(name+': '+(E/(name+'.stdout')).read_text().strip()[-1200:],flush=True)
try:
 for folder in ('source','host-leaves','tests','cross-source'):shutil.copytree(D/folder,E/'inputs'/folder)
 shutil.copy2(D/'descriptor.json',E/'inputs/descriptor.json');shutil.copy2(D/'run.py',E/'runner.py')
 source_map={str(p.relative_to(E/'inputs')):ident(p) for p in sorted((E/'inputs').rglob('*')) if p.is_file()};save(E/'source-map.json',source_map)
 save(E/'source-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete_source_map':ident(E/'source-map.json'),'runner':ident(E/'runner.py'),'frozen_before_compiler':True})
 files=sorted((E/'inputs/source').glob('*.java'))
 if mode!='cross':files+=sorted((E/'inputs/host-leaves').rglob('*.java'))+sorted((E/'inputs/tests').glob('*.java'))
 else:files=[p for p in files if p.name!='NativeBridge.java'];files.append(E/'inputs/cross-source/NativeBridge.java')
 run('javac-version',[jdk/'bin/javac','-version']);run('java-version',[jdk/'bin/java','-version'])
 run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty if mode!='cross' else jar,'-sourcepath',empty,'-d',classes,*files])
 shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 if mode!='cross':
  desc=E/'inputs/descriptor.json'
  if mode=='host':
   run('producer-52',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.EditorImplementationTests',desc])
   for case in ('admission-order','positive-values','foreign-dispatch','selection-postevent','annotation-mutable-bundle','snapshot-reservation'):
    run('prepared-'+case,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ReplacementReviewControls',case,desc])
   for case in ('final-balance','tuple-after-getter','captured-target','blurred-A-replacement','focused-B-echo-after-A-blur'):
    run('independent-'+case,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.AdditionalReplacementControls',case,desc])
   run('descriptors-38',[jdk/'bin/java','-ea','-cp',classes,'DescriptorClosure','dev.mixer.android.NativeEditorConnectionV2$Api34'])
   for case in ('positive-history','entry-loss','stage-loss','other-denials','marker-exhaustion','preservation-callback','first-fatal-busy','restoration','live-exhaustion','event-reentry','multiple-preservations','preservation-balance-fatal','scope-custody'):
    run('focus-'+case,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.FocusHistoryControls',case,desc])
   for case in ('prior-focus-values','coexistence','eligible-restore','lost-original-restore','foreign-token-restore','loss-phases','settled-loss-phases','observed-hooks','event-reentry','event-postgetter','scope-imbalance','exhaustion','post-attach-rollback','cross-renderer-end'):
    run('actual-'+case,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentFocusHistoryControls',case,desc])
   for case in ('multiple-with-active-B','event-provenance'):
    run('audit-'+case,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentAdditionalFocusAuditControls',case,desc])
  for case in (sys.argv[2:] or ('outcomes','refresh','no-scopes','partial-entry','partial-release','chronology','foreign-endpoints','terminal-end','imbalances','getter-loss','begin-accounting','precommit-refusals')):
   run('completion-'+case,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.PreservationCompletionControls',case,desc])
 else:
  run('d8-version',[d8,'--version']);run('sdk-descriptors',[jdk/'bin/javap','-p','-s','-classpath',jar,'android.view.inputmethod.InputConnection'])
  dex=scratch/'dex';dex.mkdir();run('dex',[d8,'--min-api','28','--lib',jar,'--output',dex,*sorted(classes.rglob('*.class'))]);shutil.copytree(dex,E/'dex');save(E/'dex-map.json',{str(p.relative_to(dex)):ident(p) for p in sorted(dex.rglob('*')) if p.is_file()})
 run('completion-bytecode',[jdk/'bin/javap','-p','-c','-classpath',classes,'dev.mixer.android.NativeRenderer'])
 run('adapter-bytecode',[jdk/'bin/javap','-p','-s','-c','-classpath',classes,*[f'dev.mixer.android.NativeEditorConnectionV2${name}' for name in ('Base','Api31','Api33','Api34')]])
 assert source_map=={str(p.relative_to(E/'inputs')):ident(p) for p in sorted((E/'inputs').rglob('*')) if p.is_file()},'frozen source changed'
 status='passed-'+mode+'-only'
finally:
 shutil.rmtree(scratch)
 save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'scope':'Complete source JVM with controlled authored Android/JNI leaves' if mode!='cross' else 'Unsigned SDK37 Java/D8 min-api28 compilation only','commands':len(commands),'source_freeze':ident(E/'source-freeze.json') if (E/'source-freeze.json').exists() else None,'tools':{str(p):ident(p.resolve()) for p in (jdk/'bin/javac',jdk/'bin/java',jar,d8)},'cleanup':{'scratch_removed':not scratch.exists(),'children_reaped':all(c['reaped'] for c in commands),'native_or_capture_processes_started_or_queried':False}})
 print(status,str(E.relative_to(R)),flush=True)
