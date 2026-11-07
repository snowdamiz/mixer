"""Actual v4 bootstrap/checker controls with synthetic selected trust roots; no product acceptance."""
from pathlib import Path
import shutil,json,hashlib,sys,subprocess,os,signal,time,tempfile
D=Path(__file__).resolve().parent;Q=D.parent;R=Q.parents[1];jdk=Path(json.loads((D/'jdk17-tool-context.json').read_bytes())['jdk_home'])
sys.dont_write_bytecode=True;sys.path.insert(0,str(D/'payload'));from execution_closure import tree,identity
F=D/'replay-inputs'
i=1
while (D/('integrity-controls-'+str(i))).exists():i+=1
E=D/('integrity-controls-'+str(i));E.mkdir();scratch=Path(tempfile.mkdtemp(prefix='owned-bootstrap-control-',dir=E));commands=[];controls=[]
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run(name,argv):
 start=time.monotonic();env={'PATH':str(jdk/'bin')+':/usr/bin:/bin','LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'}
 if name=='inherited-tool-option-injection-is-cleared':env.update({'JAVA_TOOL_OPTIONS':'-javaagent:/foreign/agent.jar','_JAVA_OPTIONS':'-XunknownInjection','JDK_JAVA_OPTIONS':'--class-path /foreign','CLASSPATH':'/foreign','PYTHONPATH':'/foreign','PYTHONHOME':'/foreign'})
 with (E/(name+'.stdout')).open('wb') as out,(E/(name+'.stderr')).open('wb') as err:
  child=subprocess.Popen([str(x) for x in argv],stdout=out,stderr=err,cwd=scratch,env=env,start_new_session=True);timed=False
  try:child.wait(timeout=60)
  except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
 entry={'name':name,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timed,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'reaped':True,'stdout':identity(E/(name+'.stdout')),'stderr':identity(E/(name+'.stderr'))};commands.append(entry);save(E/'commands.json',commands);return entry
def fixture(name,adversary=''):
 root=scratch/name;root.mkdir();payload=root/'payload';shutil.copytree(D/'payload',payload)
 for file in ('policy.json','context.json','reference-obligations.json','approved-policy-binding.json','matrix.json'):shutil.copy2(F/file,payload/file)
 shutil.copytree(F/'sources',payload/'sources')
 # Local synthetic independent policy pins from the sealed finding, retaining actual checker logic.
 checker=(payload/'check_qualified_matrix.py').read_text();import re
 checker=re.sub("APPROVED_BINDING_SHA256='[^']+'","APPROVED_BINDING_SHA256='"+identity(payload/'approved-policy-binding.json')['sha256']+"'",checker);checker=re.sub("REFERENCE_OBLIGATIONS_SHA256='[^']+'","REFERENCE_OBLIGATIONS_SHA256='"+identity(payload/'reference-obligations.json')['sha256']+"'",checker);(payload/'check_qualified_matrix.py').write_text(checker)
 producer='''from pathlib import Path
import argparse,json,hashlib,subprocess,os
p=argparse.ArgumentParser()
for key in ('execution-manifest','execution-root','classes','java','output'):p.add_argument('--'+key,required=True,type=Path)
p.add_argument('--case');p.add_argument('--assemble',type=Path)
a=p.parse_args();root=a.execution_root
# Synthetic certificate values are parser/integrity fixtures, not product behavioral evidence.
m=json.loads((root/'matrix.json').read_bytes());m['execution_manifest_sha256']=hashlib.sha256(a.execution_manifest.read_bytes()).hexdigest()
'''+adversary+'''
a.output.write_text(json.dumps(m))
print('synthetic selected producer executed')
'''
 (payload/'run_qualified_matrix.py').write_text(producer)
 classes=root/'expected-classes';classes.mkdir();empty=root/'empty';empty.mkdir();assert run('compile-'+name,[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sorted((payload/'sources').glob('*.java'))])['exit']==0
 manifest={'schema':'mixer.android.execution-closure.v1','root_selected':True,'payload_tree':tree(payload),'class_tree':tree(classes),'jdk_tree':tree(jdk,True),'python_executable':identity(Path(sys.executable).resolve()),'compile':{'flags':['--release','17','-Xlint:all','-Werror','-proc:none'],'sources':['sources/Subject.java','sources/Support.java'],'classpath':'empty','sourcepath':'empty'},'environment':{'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'},'checker':'check_qualified_matrix.py','producer':'run_qualified_matrix.py','replay_cases':['synthetic'],'checker_inputs':{'policy':'policy.json','map':'context.json','source_root':'sources'},'scope':'explicitly synthetic selected-policy execution-integrity fixture; no product authority'}
 save(root/'execution-manifest.json',manifest);bootstrap=(D/'default_qualification_bootstrap.py').read_text().replace("SELECTED_EXECUTION_MANIFEST_SHA256='UNSELECTED-FULL-EXECUTION-CLOSURE'","SELECTED_EXECUTION_MANIFEST_SHA256='"+identity(root/'execution-manifest.json')['sha256']+"'");(root/'bootstrap.py').write_text(bootstrap);return root,payload
def invoke(name,root,wanted,tool_root=None):
 result=run(name,[sys.executable,'-I','-B',root/'bootstrap.py','--execution-manifest',root/'execution-manifest.json','--execution-root',root/'payload','--jdk-home',tool_root or jdk,'--output',root/'receipt.json']);receipt=json.loads((root/'receipt.json').read_bytes());assert result['exit']==wanted,(name,receipt);controls.append({'name':name,'exit':result['exit'],'receipt':receipt,'expected_refusal':wanted==2});shutil.copy2(root/'receipt.json',E/(name+'.receipt.json'))
 for p in root.glob('receipt.*.json'):shutil.copy2(p,E/(name+'.'+p.name))
try:
 root,payload=fixture('positive');invoke('positive-selected-exact-closure',root,0);invoke('inherited-tool-option-injection-is-cleared',root,0)
 for name,mutate in [
  ('changed-support-source',lambda r,p:(p/'sources/Support.java').write_text('package example; public class Support { public int changed(){return 9;} }\n')),
  ('changed-producer-source',lambda r,p:(p/'run_qualified_matrix.py').write_text('raise SystemExit(0)\n')),
  ('changed-checker-helper',lambda r,p:(p/'structured_rows.py').write_text('raise RuntimeError("foreign")\n')),
  ('missing-support-source',lambda r,p:(p/'sources/Support.java').unlink()),
  ('extra-support-source',lambda r,p:(p/'sources/Extra.java').write_text('class Extra {}\n')),
  ('coherent-manifest-and-certificate-replacement',lambda r,p:(save(r/'execution-manifest.json',{**json.loads((r/'execution-manifest.json').read_bytes()),'root_selected':True,'payload_tree':{}}),save(p/'matrix.json',{'status':'passed','execution_manifest_sha256':identity(r/'execution-manifest.json')['sha256']})))]:
  root,payload=fixture(name);mutate(root,payload);invoke(name,root,2);assert not list(root.glob('receipt.producer*.stdout')),'producer ran after entry corruption'
 # Tool replacement is checked against complete installation tree without touching the shared official installation.
 root,payload=fixture('changed-tool');tool_copy=scratch/'owned-tool-copy';shutil.copytree(jdk,tool_copy,copy_function=os.link,symlinks=True)
 changed_java=tool_copy/'bin/java';replacement=tool_copy/'bin/java.changed';replacement.write_bytes(changed_java.read_bytes()+b'foreign appended identity');replacement.replace(changed_java);invoke('changed-current-tool-without-trust-root-edit',root,2,tool_copy)

 for name,adversary in [
  ('missing-support-class',"(a.classes/'example/Support.class').unlink()"),
  ('extra-support-class',"(a.classes/'example/Extra.class').write_bytes((a.classes/'example/Support.class').read_bytes())"),
  ('changed-support-class',"(a.classes/'example/Support.class').write_bytes(b'foreign emitted bytes')"),
  ('coherent-support-class-and-claimed-metadata',"(a.classes/'example/Support.class').write_bytes(b'foreign emitted bytes');m['execution_scaffolding']={'status':'reviewed','class_sha256':'self-asserted'}"),
  ('changed-payload-after-producer',"(root/'sources/Support.java').write_text('foreign after selected compile')")]:
  root,payload=fixture(name,adversary);invoke(name,root,2)
 save(E/'controls.json',{'status':'passed-synthetic-bootstrap-integrity-controls','controls':controls,'all_expected_refusals':all(c['exit']==2 for c in controls if c['expected_refusal']),'product_behavior_accepted':False,'native_OTA_GA_authorized':False})
 # Retain one exact accepted synthetic graph for independent reproduction; children already reaped.
 shutil.copytree(scratch/'positive',E/'retained-positive-fixture')
finally:
 shutil.rmtree(scratch);save(E/'cleanup.json',{'owned_scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'commands':len(commands),'no_native_capture_or_process_inventory':True})
print('PASS actual bootstrap controls',len(controls))
