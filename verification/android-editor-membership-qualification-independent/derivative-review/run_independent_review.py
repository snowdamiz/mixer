#!/usr/bin/env python3
import argparse,datetime,hashlib,importlib.util,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True,type=Path);ap.add_argument('--jdk-home',required=True,type=Path);ap.add_argument('--mode',choices=['first','corrected'],required=True);ap.add_argument('--descriptor',type=Path);ap.add_argument('--full-replay',action='store_true');a=ap.parse_args();packet=a.input.resolve();root=HERE/('run-'+a.mode);root.mkdir();scratch=root/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();logs=[];status='failed';environment=dict(os.environ)
 for key in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):environment.pop(key,None)
 def run(label,argv):
  start=time.monotonic();out=root/(label+'.stdout');err=root/(label+'.stderr')
  with out.open('wb') as stdout,err.open('wb') as stderr:
   child=subprocess.Popen([str(x) for x in argv],cwd=HERE,stdout=stdout,stderr=stderr,env=environment,start_new_session=True)
   timeout=False
   try:child.wait(timeout=60)
   except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
  row={'name':label,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed':time.monotonic()-start,'stdout':ident(out),'stderr':ident(err)};logs.append(row);save(root/'commands.json',logs);print(label,child.returncode,flush=True);assert child.returncode==0 and not timeout,row
  return out.read_bytes()
 try:
  sources=sorted((packet/'inputs/source').glob('*.java'))+sorted((packet/'inputs/host-leaves').rglob('*.java'))+sorted((packet/'inputs/tests').glob('*.java'))+[packet/'ProbeOutcomeControls.java',packet/'LeafBranchWitness.java',HERE/'IndependentProbeReviewControls.java']
  save(root/'source-closure.json',{'sources':[{'path':str(p),**ident(p)} for p in sources],'runner':ident(Path(__file__)),'tools':{name:ident(a.jdk_home/name) for name in ('bin/java','bin/javac','bin/javap','lib/modules','lib/server/libjvm.dylib')}})
  run('java-version',[a.jdk_home/'bin/java','-version']);run('javac-version',[a.jdk_home/'bin/javac','-version'])
  run('compile',[a.jdk_home/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
  shutil.copytree(classes,root/'classes')
  for mode in ('positive','lifetime-reset-witness','audit-sink-witness' if a.mode=='first' else 'no-audit-sink'):
   run(mode,[a.jdk_home/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentProbeReviewControls',mode])
  run('producer-passive-controls',[a.jdk_home/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ProbeOutcomeControls'])
  if a.full_replay:
   assert a.descriptor and a.descriptor.is_file()
   original=json.loads((packet/'run-1/commands.json').read_bytes())
   for command in original:
    if not command['label'].startswith('original-'):continue
    old=command['argv'];cp=old.index('-cp');tail=[str(a.descriptor.resolve()) if str(x).endswith('/descriptor.json') else x for x in old[cp+3:]]
    run(command['label'],[a.jdk_home/'bin/java','-ea','-Xmx256m','-cp',classes,old[cp+2],*tail])
  spec=importlib.util.spec_from_file_location('independent_classfile',HERE.parent/'preaccess/interface-v3/classfile.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  refs=json.loads((HERE.parent/'preaccess/interface-v3/reference-obligations.json').read_bytes())['exact16_source_map']
  actual_sources={p.name:ident(p) for p in (packet/'inputs/source').glob('*.java')};assert actual_sources==refs
  products={p.relative_to(classes).as_posix():ident(p) for p in classes.rglob('*.class') if mod.parse(p.read_bytes())['source_file'] in refs}
  contextid=hashlib.sha256(json.dumps({'source_map':refs,'class_map':products},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert len(products)==209 and contextid=='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
  save(root/'exact-product-context.json',{'source_map':refs,'class_map':products,'context_id':contextid,'product_classes':len(products)})
  status='host-instrumentation-controls-completed; acceptance determined in review'
 finally:
  shutil.rmtree(scratch);save(root/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'commands':logs,'all_children_reaped':all(c['reaped'] for c in logs),'scratch_removed':not scratch.exists(),'native_UI_capture_or_process_inventory':False,'scope':'Independent host-instrumentation review only; no full matrix, native, OTA or GA acceptance'})
if __name__=='__main__':main()
