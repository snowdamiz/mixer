#!/usr/bin/env python3
"""Run one bounded candidate command in an owned fresh source/dependency copy."""
import hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');HERE=Path(__file__).resolve().parent
NODE=Path('/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return {'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
name,mode=sys.argv[1:3];outdir=HERE/'runs'/name;outdir.mkdir(parents=True,exist_ok=False)
scratch=Path(tempfile.mkdtemp(prefix='mixer-controller-v2-'+name+'-'));project=scratch/'hosted-worker-controller'
records=[{'path':str(p.relative_to(HERE/'candidate')),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted((HERE/'candidate').rglob('*')) if p.is_file()]
digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(outdir/'source-manifest.json').write_text(json.dumps({'tree_sha256':digest,'files':records},indent=2)+'\n')
with tarfile.open(outdir/'source-snapshot.tar.gz','w:gz') as t:
 for e in records:t.add(HERE/'candidate'/e['path'],arcname=e['path'],recursive=False)
shutil.copy2(Path(__file__),outdir/'run-command-source.py')
start=datetime.now(timezone.utc).isoformat();t0=time.monotonic();commands=[];status=0
try:
 shutil.copytree(HERE/'candidate',scratch,dirs_exist_ok=True)
 shutil.copytree(ROOT/'hosted-worker-controller/node_modules',project/'node_modules',symlinks=True)
 deps=json.loads((HERE/'inputs/verification/hosted-worker-controller-implementation/dependency-files.json').read_text())['files']
 for e in deps:
  p=scratch/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256']
 bindings={'scratch':str(scratch),'source_tree_sha256':digest}
 (outdir/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
 env=os.environ.copy();env['PATH']=str(NODE.parent)+os.pathsep+env['PATH'];env['MIXER_CONTROLLER_TEST_REPORT']=str(outdir/'producer-report.json');env['MIXER_V2_RUN_DIR']=str(outdir)
 def run(label,args):
  global status
  argv=[str(NODE)]+args;begin=time.monotonic()
  with (outdir/(label+'.stdout')).open('wb') as out,(outdir/(label+'.stderr')).open('wb') as err:r=subprocess.run(argv,cwd=project,env=env,stdout=out,stderr=err)
  commands.append({'argv':argv,'cwd':str(project),'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-begin,'source_tree_sha256':digest,'stdout':rec(outdir/(label+'.stdout')),'stderr':rec(outdir/(label+'.stderr'))})
  status=r.returncode or status;print(json.dumps(commands[-1]),flush=True)
  return r.returncode
 if mode=='build':
  shutil.rmtree(project/'dist',ignore_errors=True)
  if run('build',['build.mjs'])==0:
   shutil.copytree(project/'dist',HERE/'candidate/hosted-worker-controller/dist',dirs_exist_ok=True)
 elif mode=='producer':run('producer',['test/run.mjs'])
 elif mode in ['regressions','noncooperative','closure']:
  fixture=HERE/'inputs/verification/hosted-worker-controller-implementation-independent-review'/({'regressions':'regressions.mjs','noncooperative':'noncooperative.mjs','closure':'closure.mjs'}[mode])
  shutil.copy2(fixture,outdir/fixture.name)
  if mode=='noncooperative':
   original=project/'test/worker.ts';shutil.copy2(HERE/'inputs/verification/hosted-worker-controller-implementation-independent-review/noncooperative-worker.ts',original);shutil.copy2(original,outdir/'fixture-worker.ts')
   run('build-fixture',['build.mjs'])
  run(mode,[str(outdir/fixture.name)])
 elif mode=='focused':
  shutil.copy2(HERE/'focused.mjs',outdir/'focused.mjs');run('focused',[str(outdir/'focused.mjs')])
 elif mode=='inventory':
  shutil.copy2(HERE/'inventory.mjs',outdir/'inventory.mjs');run('inventory',[str(outdir/'inventory.mjs')])
 else:raise RuntimeError('unknown_mode')
 # Save actual compiled module bytes for provenance (including fixture outputs).
 compiled=[]
 for p in sorted((project/'dist').rglob('*')):
  if p.is_file():compiled.append({'path':str(p.relative_to(project)),'bytes':p.stat().st_size,'sha256':sha(p)})
 (outdir/'compiled.json').write_text(json.dumps(compiled,indent=2)+'\n')
finally:
 cleanup=[]
 for p in outdir.glob('*report.json'):
  report=json.loads(p.read_text())
  for e in report.get('cleanup',[]):
   if 'persist' in e:assert not Path(e['persist']).exists(),e
   cleanup.append(e)
 executable=str(project/'node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd')
 ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True,check=True)
 matching=[line.strip() for line in ps.stdout.splitlines() if line.strip().endswith(executable)]
 assert not matching,matching
 shutil.rmtree(scratch)
 result={'start_utc':start,'elapsed_seconds':time.monotonic()-t0,'exit_code':status,'source_tree_sha256':digest,'source_snapshot':rec(outdir/'source-snapshot.tar.gz'),'commands':commands,'environment':{'MIXER_CONTROLLER_TEST_REPORT':env['MIXER_CONTROLLER_TEST_REPORT'] if 'env' in globals() else None,'MIXER_V2_RUN_DIR':str(outdir)},'cleanup':{'actions':cleanup,'owned_workerd_executable':executable,'matching_owned_workerd':matching,'scratch':str(scratch),'scratch_removed':not scratch.exists(),'other_processes_modified':False}}
 (outdir/'command.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'run':name,'exit_code':status,'cleanup':len(cleanup),'scratch_removed':not scratch.exists()}),flush=True)
sys.exit(status)
