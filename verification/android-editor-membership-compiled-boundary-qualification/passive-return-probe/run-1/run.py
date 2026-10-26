from pathlib import Path
import os,sys,subprocess,json,hashlib,time,signal,shutil,tempfile,datetime
D=Path(__file__).resolve().parent;Q=D.parent;R=Q.parents[1];jdk=Path(json.loads((Q/'state-qualification/jdk17-download-receipt.json').read_bytes())['jdk_home']);env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
i=1
while (D/f'run-{i}').exists():i+=1
E=D/f'run-{i}';E.mkdir();commands=[];scratch=Path(tempfile.mkdtemp(prefix='owned-passive-return-',dir=E));classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();temp=scratch/'tmp';temp.mkdir();env.update({'TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp)});status='failed'
def run(label,argv):
 start=time.monotonic()
 with (E/(label+'.stdout')).open('wb') as o,(E/(label+'.stderr')).open('wb') as e:
  p=subprocess.Popen([str(x) for x in argv],stdout=o,stderr=e,cwd=R,env=env,start_new_session=True);timeout=False
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 commands.append({'label':label,'argv':[str(x) for x in argv],'exit':p.returncode,'timeout':timeout,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(label+'.stdout')),'stderr':ident(E/(label+'.stderr')),'reaped':True});save(E/'commands.json',commands);print(label,'exit',p.returncode,flush=True);return p.returncode
try:
 if not (D/'inputs').exists():
  for folder in ('source','host-leaves','tests'):shutil.copytree(Q/'inputs/accepted'/folder,D/'inputs'/folder)
  for f in (D/'leaves').rglob('*.java'):
   rel=f.relative_to(D/'leaves');orig=D/'inputs/host-leaves'/rel;original=D/'original'/rel;original.parent.mkdir(parents=True,exist_ok=True)
   shutil.copy2(Q/'inputs/instrumentation/ConcreteHostProbe.java' if rel.name=='ConcreteHostProbe.java' else orig,original);shutil.copy2(f,orig)
  shutil.copy2(D/'NativeOutcomeProbe.java',D/'inputs/host-leaves/dev/mixer/android/NativeOutcomeProbe.java')
 sources=sorted((D/'inputs/source').glob('*.java'))+sorted((D/'inputs/host-leaves').rglob('*.java'))+sorted((D/'inputs/tests').glob('*.java'))+[D/'ProbeOutcomeControls.java',D/'LeafBranchWitness.java']
 for f in ('run.py','NativeOutcomeProbe.java','ProbeOutcomeControls.java','LeafBranchWitness.java','selected-return-sites.json'):shutil.copy2(D/f,E/f)
 save(E/'source-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':[{'path':str(p.relative_to(R)),**ident(p)} for p in sources],'runner':ident(E/'run.py'),'exact_product_tree':'a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4','compiler_flags':['--release','17','-Xlint:all','-Werror','-proc:none','-classpath','<empty>','-sourcepath','<empty>'],'JDK17_tools':{str(p.relative_to(jdk)):ident(p) for p in (jdk/'bin/java',jdk/'bin/javac',jdk/'bin/javap',jdk/'lib/modules')}})
 assert run('java-version',[jdk/'bin/java','-version'])==0;assert run('javac-version',[jdk/'bin/javac','-version'])==0;assert run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources])==0
 shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 assert run('passive-outcome-controls',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ProbeOutcomeControls'])==0
 assert run('branch-witness-derivative',[jdk/'bin/java','-ea','-cp',classes,'dev.mixer.android.LeafBranchWitness'])==0
 witness=scratch/'witness';witness.mkdir();assert run('branch-witness-baseline-compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',Q/'state-qualification/context17-1/classes','-d',witness,D/'LeafBranchWitness.java'])==0
 assert run('branch-witness-baseline',[jdk/'bin/java','-ea','-cp',str(witness)+os.pathsep+str(Q/'state-qualification/context17-1/classes'),'dev.mixer.android.LeafBranchWitness'])==0;assert (E/'branch-witness-derivative.stdout').read_bytes()==(E/'branch-witness-baseline.stdout').read_bytes(),'branch/hit/hook/exception outcome drift';save(E/'branch-equivalence.json',{'same_original_and_derivative_witness_output':True,'original':ident(E/'branch-witness-baseline.stdout'),'derivative':ident(E/'branch-witness-derivative.stdout')})
 original=json.loads((Q/'selected-original-command-roster.json').read_bytes())
 for c in original:
  args=c['argv']
  if '-cp' not in args or not (c['name'] in ('producer-52','descriptors-38') or c['name'].startswith(('prepared-','independent-','focus-','actual-','audit-','completion-','membership-'))):continue
  cp=args.index('-cp');main=args[cp+2];tail=[str(Q/'inputs/accepted/descriptor.json') if x.endswith('/inputs/descriptor.json') else x for x in args[cp+3:]];assert run('original-'+c['name'],[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,main,*tail])==0
 sys.path.insert(0,str(Q));from classfile import parse
 products={str(p.relative_to(classes)):ident(p) for p in classes.rglob('*.class') if parse(p.read_bytes())['source_file'] in {p.name for p in (D/'inputs/source').glob('*.java')}};expected=json.loads((Q/'state-qualification/context17-1/product-context.json').read_bytes())['class_map'];assert products==expected,'product class changed';save(E/'product-class-equality.json',{'exact209_product_class_map_equal':True,'product_class_map':products,'source_product_tree':'a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4','root_independent_derivative_acceptance_pending':True});status='passed-preparation-host-controls; independent-derivative-review-pending'
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'commands':commands,'all_commands_passed':all(c['exit']==0 and not c['timeout'] for c in commands),'scope':'Isolated passive source/leaf derivative preparation only; no qualified matrix or product integration credit until independent review','cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'native_UI_capture_or_process_inventory':False}})
