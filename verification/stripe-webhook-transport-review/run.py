"""Fresh isolated BEAM transport runs; only this lane and identity-marked temp are written."""
import hashlib,json,os,platform,shutil,signal,socket,subprocess,sys,tarfile,tempfile,time,uuid
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def main():
 n=1
 while (HERE/f'run-{n}').exists(): n+=1
 result=HERE/f'run-{n}';result.mkdir()
 scratch=Path(tempfile.mkdtemp(prefix='mixer-webhook-transport-'))
 ident=(scratch.stat().st_dev,scratch.stat().st_ino);token=str(uuid.uuid4())
 write(scratch/'owned.json',{'pid':os.getpid(),'token':token,'identity':ident})
 commands=[];failure=None;cleanup={};integration={};pins={}
 def run(label,args,env=None,timeout=150):
  started=time.monotonic();p=subprocess.Popen(args,cwd=scratch,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
  timed=False
  try: out,_=p.communicate(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed=True
   if os.getpgid(p.pid)==p.pid:os.killpg(p.pid,signal.SIGTERM)
   try:out,_=p.communicate(timeout=3)
   except subprocess.TimeoutExpired:
    if os.getpgid(p.pid)==p.pid:os.killpg(p.pid,signal.SIGKILL)
    out,_=p.communicate(timeout=3)
  (result/f'{label}.log').write_bytes(out)
  commands.append({'label':label,'argv':args,'cwd':str(scratch),'pid':p.pid,'processGroup':p.pid,'exitCode':p.returncode,'timedOut':timed,'elapsedSeconds':round(time.monotonic()-started,3),'output':f'{label}.log','sha256':sha(result/f'{label}.log'),'environmentOverrides':{k:v for k,v in (env or {}).items() if k.startswith(('TRANSPORT_','CAPTURE_'))}})
  write(result/'commands.json',commands)
  if p.returncode or timed:raise RuntimeError(f'{label} failed; retained original source/output')
  return out.decode().strip()
 try:
  selected=json.loads((REPO/'verification/stripe-webhook-transport-root-review/selection.json').read_text())
  assert len(selected['bindings'])==228
  for name,digest in selected['bindings'].items():assert sha(REPO/name)==digest,name
  integration=json.loads((REPO/'verification/stripe-raw-body-integration/acceptance.json').read_text())
  assert integration['sourceDigest']=='ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc'
  for name,digest in integration['sourceInputs'].items():assert sha(REPO/name)==digest,name
  pins=json.loads((REPO/'verification/stripe-raw-body-capture/pinned-dependency-identity.json').read_text())
  assert sha(REPO/'hosted/mix.lock')==pins['lockSHA256']
  for name,digest in pins['source'].items():assert sha(REPO/'hosted/deps'/name)==digest,name
  for name,digest in pins['beams'].items():assert sha(REPO/'hosted/_build/test/lib'/name)==digest,name
  for name,value in pins['toolchain'].items():assert sha(Path(name))==value['sha256'],name
  source=scratch/'source';source.mkdir()
  names=list(integration['sourceInputs'])+['AGENTS.md','mixer-product-plan.md','docs/stripe-webhook-transport-contract.md','docs/stripe-webhook-transport-direction.md','verification/stripe-webhook-transport-root-review/selection.json','verification/stripe-webhook-transport-contract/matrix.json','verification/stripe-raw-body-capture/matrix.json','verification/stripe-raw-body-integration/acceptance.json']
  for name in sorted(set(names)):
   target=source/'inputs'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/name,target)
  shutil.copytree(HERE/'candidate',source/'candidate');shutil.copytree(HERE/'tests',source/'tests')
  shutil.copyfile(HERE/'run.py',source/'run.py')
  for name in ['component','clock','wire']:shutil.copyfile(source/f'tests/baseline-{name}.exs',source/f'tests/{name}.exs')
  capture=source/'candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex';shutil.copyfile(source/'inputs/hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex',capture)
  manifest={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
  write(result/'source-inputs.json',manifest)
  with tarfile.open(result/'source-closure.tar.gz','w:gz') as a:
   for name in manifest:a.add(source/name,arcname=name,recursive=False)
  write(result/'accepted-inputs.json',integration['sourceInputs'])
  write(result/'dependency-source-inputs.json',pins['source']);write(result/'dependency-beam-inputs.json',pins['beams'])
  write(result/'retained-dependency-closure.json',{'path':'verification/stripe-raw-body-capture/run-9/dependency-source-closure.tar.gz','sha256':sha(REPO/'verification/stripe-raw-body-capture/run-9/dependency-source-closure.tar.gz'),'reuse':'pinned original retained; no duplicate dependency archive'})
  cache=scratch/'dependency-cache'
  for app in sorted((REPO/'hosted/_build/test/lib').iterdir()):
   if app.name!='mixer_hosted' and (app/'ebin').is_dir():shutil.copytree(app/'ebin',cache/app.name/'ebin')
  run('elixir-version',['elixir','--version']);run('python-version',['python3','--version']);run('os-version',['uname','-a'])
  otp=run('otp-root',['elixir','-e','IO.puts(:code.root_dir())'])
  binaries=[Path(sys.executable).resolve(),Path(shutil.which('elixir')).resolve(),Path(shutil.which('erl')).resolve()]+sorted(Path(otp).glob('erts-*/bin/beam.smp'))
  write(result/'toolchain-executables.json',{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in binaries})
  args=['elixir']
  for path in sorted(cache.glob('*/ebin')):args+=['-pa',str(path)]
  phases=['baseline-component','baseline-wire','composed-wire','adversarial','stream-negative']
  if os.environ.get('TRANSPORT_RUN_PHASES'):phases=os.environ['TRANSPORT_RUN_PHASES'].split(',')
  for phase in phases:
   directory=result/phase;directory.mkdir()
   env=dict(os.environ,CAPTURE_SOURCE_DIR=str(source),CAPTURE_RESULT_DIR=str(directory),TRANSPORT_SOURCE=str(source))
   if phase.startswith('baseline-'):
    env['CAPTURE_PHASE']=phase.removeprefix('baseline-');boot=source/'tests/baseline-boot.exs'
   else:
    env['TRANSPORT_PHASE']=phase;boot=source/'tests/boot.exs'
   run(phase,args+[str(boot)],env,timeout=180)
 except BaseException as exc:failure={'type':type(exc).__name__,'message':str(exc)}
 finally:
  groups={v['processGroup'] for v in commands};proc=subprocess.run(['ps','-axo','pid=,pgid=,command='],capture_output=True,text=True,timeout=10)
  remaining=[l for l in proc.stdout.splitlines() if len(z:=l.split(None,2))>=2 and z[1].isdigit() and int(z[1]) in groups]
  write(result/'owned-process-groups.json',{'groups':sorted(groups),'remaining':remaining,'exitCode':proc.returncode})
  ports=[]
  for f in result.rglob('listener.json'):
   port=json.loads(f.read_text())['port']
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):refused=False
   except ConnectionRefusedError:refused=True
   except OSError:refused=False
   ports.append({'port':port,'connectionRefused':refused})
  holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True,text=True,timeout=30)
  (result/'scratch-holders.log').write_text(holders.stdout+holders.stderr)
  matched=(scratch.stat().st_dev,scratch.stat().st_ino)==ident and json.loads((scratch/'owned.json').read_text())['token']==token
  cleanup={'scratch':str(scratch),'identity':ident,'identityMatched':matched,'openHolders':bool(holders.stdout.strip()),'lsofExitCode':holders.returncode,'ownedProcessGroupsEmpty':not remaining,'ports':ports,'lsofCommand':['lsof','-nP','+D',str(scratch)],'processInventoryCommand':['ps','-axo','pid=,pgid=,command=']}
  if matched and not remaining and holders.returncode==1 and not holders.stdout.strip() and all(v['connectionRefused'] for v in ports):shutil.rmtree(scratch)
  cleanup['scratchRemoved']=not scratch.exists()
  if not cleanup['scratchRemoved']:failure=failure or {'type':'CleanupFailure','message':'owned scratch retained'}
  write(result/'receipt.json',{'schema':1,'observedUTC':datetime.now(timezone.utc).isoformat(),'host':platform.platform(),'sourceDigest':integration.get('sourceDigest'),'sourceRevision':integration.get('sourceParent'),'failure':failure,'cleanup':cleanup,'commands':commands,'freshCandidateCompilation':True,'freshDependencyCompilation':False,'captureSourceUnchanged':True,'dependencySourceFiles':len(pins.get('source',{})),'dependencyBeamFiles':len(pins.get('beams',{})),'publicAdmissionAccepted':False,'gaAccepted':False,'productionChanged':False,'providerContacted':False,'nativeStarted':False})
  write(result/'seal.json',{str(p.relative_to(result)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(result.rglob('*')) if p.is_file() and p.name!='seal.json'})
 print(json.dumps({'run':result.name,'failure':failure,'cleanup':cleanup},sort_keys=True))
 if failure:raise SystemExit(1)
if __name__=='__main__':main()
