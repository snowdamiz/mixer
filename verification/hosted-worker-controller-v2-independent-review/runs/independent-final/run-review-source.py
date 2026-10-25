#!/usr/bin/env python3
"""Run copied frozen sources with copied pinned dependencies; retain all output."""
import hashlib,json,os,shutil,signal,subprocess,sys,tarfile,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');HERE=ROOT/'verification/hosted-worker-controller-v2-independent-review';B=json.loads((HERE/'bindings.json').read_text());OWN=Path(B['scratch']);F=HERE/'frozen/verification/hosted-worker-controller-v2';NODE=Path('/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def digest(es):return hashlib.sha256(json.dumps(es,sort_keys=True,separators=(',',':')).encode()).hexdigest()
name,mode=sys.argv[1:3];out=HERE/'runs'/name;out.mkdir(parents=True,exist_ok=False);scratch=OWN/name;scratch.mkdir(exist_ok=False);project=scratch/'hosted-worker-controller';baseline=mode=='baseline'
archive=(F/'inputs/verification/hosted-worker-controller-implementation/source-snapshot.tar.gz')if baseline else F/'source-snapshot.tar.gz'
manifest=json.loads(((F/'inputs/verification/hosted-worker-controller-implementation/source-manifest.json')if baseline else F/'source-manifest.json').read_text())
commands=[];cleanup=[];status=0;start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
with tarfile.open(archive)as t:
 entries=t.getmembers();assert len(entries)==len(manifest['files']);expected={e['path']:e for e in manifest['files']};assert {x.name for x in entries}==set(expected)
 for x in entries:
  assert x.isfile()and not Path(x.name).is_absolute()and '..'not in Path(x.name).parts
  data=t.extractfile(x).read();e=expected[x.name];assert len(data)==e['bytes']and hashlib.sha256(data).hexdigest()==e['sha256'];p=scratch/x.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(x.mode)
shutil.copytree(OWN/'deps/hosted-worker-controller/node_modules',project/'node_modules',symlinks=True)
deps=json.loads((F/'inputs/verification/hosted-worker-controller-implementation/dependency-files.json').read_text())['files']
for e in deps:p=scratch/e['path'];assert p.stat().st_size==e['bytes']and sha(p)==e['sha256']
(out/'bindings.json').write_text(json.dumps({'scratch':str(scratch),'source_tree_sha256':manifest['tree_sha256']},indent=2)+'\n')
shutil.copy2(archive,out/'source-snapshot.tar.gz');shutil.copy2(Path(__file__),out/'run-review-source.py')
env=os.environ.copy();env['PATH']=str(NODE.parent)+os.pathsep+env['PATH'];env['MIXER_CONTROLLER_TEST_REPORT']=str(out/'producer-report.json');env['MIXER_V2_RUN_DIR']=str(out)
def run(label,args):
 global status
 argv=[str(NODE)]+args;t=time.monotonic()
 with (out/(label+'.stdout')).open('wb')as a,(out/(label+'.stderr')).open('wb')as b:
  proc=subprocess.Popen(argv,cwd=project,env=env,stdout=a,stderr=b)
  try:code=proc.wait(timeout=300)
  except subprocess.TimeoutExpired:proc.kill();code=proc.wait();status=124
 commands.append({'argv':argv,'cwd':str(project),'node_pid':proc.pid,'exit_code':code,'elapsed_seconds':time.monotonic()-t,'stdout':rec(out/(label+'.stdout')),'stderr':rec(out/(label+'.stderr'))});status=code or status;print(json.dumps({'run':name,**commands[-1]}),flush=True);return code
try:
 if mode=='build':
  shutil.rmtree(project/'dist');assert run('build',['build.mjs'])==0
  comparisons=[]
  for e in manifest['files']:
   if e['path'].startswith('hosted-worker-controller/dist/'):
    p=scratch/e['path'];assert p.stat().st_size==e['bytes']and sha(p)==e['sha256'],e['path'];comparisons.append(e)
  (out/'rebuilt-match.json').write_text(json.dumps({'status':'passed','files':comparisons},indent=2)+'\n')
 elif mode=='producer':run('producer',['test/run.mjs'])
 elif mode in ['baseline','regressions','noncooperative','closure']:
  fixture=F/'inputs/verification/hosted-worker-controller-implementation-independent-review'/({'baseline':'regressions.mjs','regressions':'regressions.mjs','noncooperative':'noncooperative.mjs','closure':'closure.mjs'}[mode]);shutil.copy2(fixture,out/fixture.name)
  if mode=='noncooperative':
   shutil.copy2(F/'inputs/verification/hosted-worker-controller-implementation-independent-review/noncooperative-worker.ts',project/'test/worker.ts');shutil.copy2(project/'test/worker.ts',out/'fixture-worker.ts');assert run('build-fixture',['build.mjs'])==0
   # Fixture replacement may alter only excluded compiled/test outputs.
   for e in manifest['files']:
    if e['path'].startswith('hosted-worker-controller/src/')or e['path'].startswith('hosted-worker-controller/dist/src/'):
     p=scratch/e['path'];assert p.stat().st_size==e['bytes']and sha(p)==e['sha256']
  run(mode,[str(out/fixture.name)])
 elif mode in ['focused','inventory']:
  shutil.copy2(F/(mode+'.mjs'),out/(mode+'.mjs'));run(mode,[str(out/(mode+'.mjs'))])
 elif mode in ['independent','ast']:
  shutil.copy2(HERE/(mode+'.mjs'),out/(mode+'.mjs'));run(mode,[str(out/(mode+'.mjs'))])
 else:raise RuntimeError(mode)
 compiled=[{'path':str(p.relative_to(project)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted((project/'dist').rglob('*'))if p.is_file()];(out/'compiled.json').write_text(json.dumps(compiled,indent=2)+'\n')
finally:
 for p in out.glob('*report.json'):
  report=json.loads(p.read_text())
  for e in report.get('cleanup',[]):
   if 'persist'in e:
    if Path(e['persist']).exists():shutil.rmtree(e['persist']);e['removed_by_outer_finally']=True
    assert not Path(e['persist']).exists()
   cleanup.append(e)
 exe=str(project/'node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd');scan=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True,check=True)
 matching=[line.strip()for line in scan.stdout.splitlines()if line.strip().endswith(exe)]
 for line in matching:
  pid=int(line.split()[0]);os.kill(pid,signal.SIGKILL);cleanup.append({'ownedPid':pid,'executable':exe,'signal':'SIGKILL','reason':'outer-finally-exact-owned-executable'})
 shutil.rmtree(scratch)
 result={'mode':mode,'start_utc':start,'elapsed_seconds':time.monotonic()-tick,'exit_code':status,'source_tree_sha256':manifest['tree_sha256'],'source_archive':rec(out/'source-snapshot.tar.gz'),'commands':commands,'environment':{'MIXER_CONTROLLER_TEST_REPORT':env['MIXER_CONTROLLER_TEST_REPORT'],'MIXER_V2_RUN_DIR':str(out)},'cleanup':{'actions':cleanup,'owned_workerd_executable':exe,'scratch':str(scratch),'scratch_removed':not scratch.exists(),'matching_before_outer_cleanup':matching,'other_projects_modified':False}}
 (out/'command.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'run':name,'exit_code':status,'cleanup_actions':len(cleanup),'scratch_removed':not scratch.exists()}),flush=True)
sys.exit(status)
