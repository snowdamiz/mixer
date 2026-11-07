#!/usr/bin/env python3
"""Externally reviewed root: this file and its pinning parent are outside descendant manifest."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,signal,subprocess,sys,tempfile,shutil,time
sys.dont_write_bytecode=True
# Draft pin intentionally cannot authorize product replay. Final pin selected only by root review.
SELECTED_EXECUTION_MANIFEST_SHA256='UNSELECTED-FULL-EXECUTION-CLOSURE'
def need(ok,message):
 if not ok:raise ValueError(message)
def identity(p):
 p=Path(p);need(p.is_file() and not p.is_symlink(),'nonregular bootstrap input');b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def snapshot(root,symlinks=False):
 root=Path(root);need(root.is_dir() and not root.is_symlink(),'nonregular bootstrap root');result={}
 for p in sorted(root.rglob('*')):
  rel=str(p.relative_to(root));need(not p.is_symlink() or symlinks,'payload symlink')
  if p.is_symlink():need(p.resolve().is_relative_to(root.resolve()),'tool symlink escape');result[rel]={'kind':'symlink','target':os.readlink(p)}
  elif p.is_file():result[rel]={'kind':'file',**identity(p)}
  else:need(p.is_dir(),'non-file execution artifact')
 return result
def load_selected_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def execute(args):
 need(sys.flags.isolated==1 and sys.flags.dont_write_bytecode,"trusted bootstrap requires isolated -I -B Python entry")
 # Standard library only until the complete selected descendant source tree has been rehashed.
 need(identity(args.execution_manifest)['sha256']==SELECTED_EXECUTION_MANIFEST_SHA256,'unselected execution manifest at trusted bootstrap entry');m=json.loads(args.execution_manifest.read_bytes());need(m.get('schema')=='mixer.android.execution-closure.v1' and m.get('root_selected') is True,'execution closure remains draft');need(snapshot(args.execution_root)==m['payload_tree'],'changed/missing/extra payload at bootstrap entry');need(snapshot(args.jdk_home,True)==m['jdk_tree'],'changed/missing/extra tool at bootstrap entry');need(identity(Path(sys.executable).resolve())==m['python_executable'],'changed trusted interpreter at bootstrap entry')
 need(m['compile']['flags']==['--release','17','-Xlint:all','-Werror','-proc:none'] and m['compile']['classpath']=='empty' and m['compile']['sourcepath']=='empty','unselected compile argv/search paths');need(m['environment']=={'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'},'unselected environment policy')
 need(type(m['compile']['sources']) is list and len(set(m['compile']['sources']))==len(m['compile']['sources']),'duplicate compiler input')
 for source in m['compile']['sources']:need(type(source) is str and source in m['payload_tree'] and source.endswith('.java') and not Path(source).is_absolute() and '..' not in Path(source).parts,'unselected compiler source')
 need(m['checker'] in m['payload_tree'] and m['producer'] in m['payload_tree'],'unselected checker/producer')
 commands=[];work=Path(tempfile.mkdtemp(prefix='owned-qualified-matrix-',dir=args.output.parent));classes=work/'classes';classes.mkdir();empty=work/'empty';empty.mkdir();temporary=work/'tmp';temporary.mkdir();matrix=work/'matrix.json'
 env={**m['environment'],'JAVA_HOME':str(args.jdk_home),'PATH':str(args.jdk_home/'bin')+':/usr/bin:/bin','TMPDIR':str(temporary),'TMP':str(temporary),'TEMP':str(temporary)}
 def run(label,argv):
  start=time.monotonic()
  with (work/(label+'.stdout')).open('wb') as out,(work/(label+'.stderr')).open('wb') as err:
   p=subprocess.Popen([str(v) for v in argv],env=env,cwd=work,stdout=out,stderr=err,start_new_session=True);timed=False
   try:p.wait(timeout=60)
   except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
  commands.append({'label':label,'argv':[str(v) for v in argv],'exit':p.returncode,'timeout':timed,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'stdout':identity(work/(label+'.stdout')),'stderr':identity(work/(label+'.stderr')),'reaped':True});need(p.returncode==0 and not timed,'bounded '+label+' failed')
 try:
  run('compile',[args.jdk_home/'bin/javac',*m['compile']['flags'],'-classpath',empty,'-sourcepath',empty,'-d',classes,*[args.execution_root/s for s in m['compile']['sources']]])
  need(snapshot(classes)==m['class_tree'],'changed/missing/extra fresh support/product classes before producer');need(snapshot(args.execution_root)==m['payload_tree'] and snapshot(args.jdk_home,True)==m['jdk_tree'],'execution closure changed before producer')
  # Producer receives only fixed selected arguments and freshly compiled classes; it cannot select its trust root.
  cases=m['replay_cases'];need(type(cases) is list and cases and len(cases)==len(set(cases)) and all(type(case) is str and case and all(c.isalnum() or c in '-_' for c in case) for case in cases),'unselected replay case roster');case_root=work/'cases';case_root.mkdir()
  producer=[sys.executable,'-I','-B',args.execution_root/m['producer'],'--execution-manifest',args.execution_manifest,'--execution-root',args.execution_root,'--classes',classes,'--java',args.jdk_home/'bin/java']
  for case in cases:
   run('producer-case-'+case,[*producer,'--case',case,'--output',case_root/(case+'.json')])
   need(snapshot(args.execution_root)==m['payload_tree'] and snapshot(classes)==m['class_tree'] and snapshot(args.jdk_home,True)==m['jdk_tree'],'execution closure changed after selected replay case')
  run('producer-assemble',[*producer,'--assemble',case_root,'--output',matrix])
  need(snapshot(args.execution_root)==m['payload_tree'] and snapshot(classes)==m['class_tree'] and snapshot(args.jdk_home,True)==m['jdk_tree'],'execution closure changed before certificate acceptance');need(identity(args.execution_manifest)['sha256']==SELECTED_EXECUTION_MANIFEST_SHA256,'selection changed during replay')
  sys.path.insert(0,str(args.execution_root));checker=load_selected_module(args.execution_root/m['checker'],'selected_matrix_checker');result=checker.check_bootstrapped(args.execution_manifest,SELECTED_EXECUTION_MANIFEST_SHA256,args.execution_root,classes,args.jdk_home,matrix)
  result.update({'trusted_entry':'external reviewed default bootstrap and pinning parent','execution_manifest_sha256':SELECTED_EXECUTION_MANIFEST_SHA256,'fresh_commands':commands});shutil.copy2(matrix,args.output.with_suffix('.matrix.json'));return result
 finally:
  # Reaped children and owned scratch only. Failed command diagnostics are retained adjacent to output.
  for p in work.glob('*.stdout'):shutil.copy2(p,args.output.parent/(args.output.stem+'.'+p.name))
  for p in work.glob('*.stderr'):shutil.copy2(p,args.output.parent/(args.output.stem+'.'+p.name))
  (args.output.parent/(args.output.stem+'.commands.json')).write_text(json.dumps(commands,indent=2)+'\n');shutil.rmtree(work)
def main():
 p=argparse.ArgumentParser();p.add_argument('--execution-manifest',required=True,type=Path);p.add_argument('--execution-root',required=True,type=Path);p.add_argument('--jdk-home',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 for name in ('execution_manifest','execution_root','jdk_home','output'):setattr(a,name,getattr(a,name).resolve())
 try:r=execute(a);code=0
 except (ValueError,KeyError,TypeError,OSError,AssertionError) as failure:r={'status':'refused-at-trusted-execution-bootstrap','reason':str(failure),'product_policy_or_behavior_accepted':False,'native_OTA_GA_authorized':False};code=2
 a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(code)
if __name__=='__main__':main()
