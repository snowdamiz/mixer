#!/usr/bin/env python3
"""Independent frozen-overlay adversarial review. All writes are review-owned."""
import datetime,hashlib,io,json,os,pathlib,re,shutil,subprocess,tarfile,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
PROD=ROOT/'verification/hosted-artifact-admission-implementation'
BASE='4586bb901b980e9beeca5f7bb826f8b62140a3b4'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(p.read_bytes())
def main():
 n=1
 while (OUT/f'run-{n}').exists(): n+=1
 output=OUT/f'run-{n}';output.mkdir()
 scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-artifact-review-',dir='/private/tmp'))
 commands=[];deps=[];inputs={};status='failed';failure=None
 def run(label,argv,cwd,env=None,timeout=300):
  log=output/(label+'.log');start=time.monotonic()
  with log.open('wb') as stream:
   try: code=subprocess.run(argv,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout).returncode
   except subprocess.TimeoutExpired: stream.write(b'REVIEW: deadline exceeded\n');code=124
  commands.append(dict(label=label,argv=list(map(str,argv)),cwd=str(cwd),environment={k:env[k] for k in ['MIX_ENV','HEX_OFFLINE','GOPROXY','GOSUMDB','GOTOOLCHAIN'] if env and k in env},exitCode=code,elapsedSeconds=time.monotonic()-start,output=log.name,outputSHA256=digest(log)))
  print(f'{label}: exit {code}',flush=True)
  if code:raise RuntimeError(f'{label} failed with {code}')
 try:
  run('producer-integrity',['python3',str(PROD/'verify.py')],ROOT)
  archive=subprocess.check_output(['git','archive',BASE],cwd=ROOT)
  with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(scratch,filter='data')
  subprocess.run(['git','init','-q',str(scratch)],check=True)
  objects=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-path','objects'],cwd=ROOT,text=True).strip()
  (scratch/'.git/objects/info/alternates').write_text(objects+'\n')
  subprocess.run(['git','-C',str(scratch),'update-ref','refs/heads/main',BASE],check=True)
  subprocess.run(['git','-C',str(scratch),'symbolic-ref','HEAD','refs/heads/main'],check=True)
  overlays=sorted(p for p in (PROD/'overlay').rglob('*') if p.is_file());assert len(overlays)==4
  for p in overlays:
   rel=p.relative_to(PROD/'overlay');dest=scratch/rel;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
  # Independently rebuild precisely the sealed 91-file closure, from Git and overlay.
  producer=json.loads((PROD/'run-2/receipt.json').read_text())
  for name,want in producer['sourceInputs'].items():
   assert digest(scratch/name)==want,name
   inputs[name]=want
  tree=sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode());assert tree==producer['sourceTreeSHA256']
  with tarfile.open(output/'source.tar.gz','w:gz') as tar:
   for name in sorted(inputs):tar.add(scratch/name,arcname=name,recursive=False)
  lock=(scratch/'hosted/mix.lock').read_text()
  for line in lock.splitlines():
   match=re.fullmatch(r'  "([^\"]+)": \{:hex, :[^,]+, "([^\"]+)".*"([0-9a-f]{64})"\},',line)
   if not match:continue
   name,version,want=match.groups();p=pathlib.Path.home()/'.hex/packages/hexpm'/f'{name}-{version}.tar';assert digest(p)==want
   with tarfile.open(p) as t:contents=t.extractfile('contents.tar.gz').read()
   dest=scratch/'hosted/deps'/name;dest.mkdir(parents=True)
   with tarfile.open(fileobj=io.BytesIO(contents),mode='r:gz') as t:t.extractall(dest,filter='data')
   deps.append(dict(name=name,version=version,archiveSHA256=want,archive=str(p)))
  assert len(deps)==20
  env=dict(os.environ,MIX_ENV='test',HEX_OFFLINE='1',ERL_CRASH_DUMP_SECONDS='0',ERL_CRASH_DUMP=str(scratch/'erl_crash.dump'))
  goenv=dict(env,GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local')
  run('versions',['sh','-c','elixir --version\ngo version\npython3 --version\nuname -a'],scratch,env)
  run('locked-offline-dependencies',['mix','deps.get','--check-locked'],scratch/'hosted',env)
  run('producer-focused-tests',['mix','test','test/mixer_hosted/protocol/artifact_admission_test.exs','--warnings-as-errors','--trace'],scratch/'hosted',env)
  run('go-protocol-regression',['go','test','./protocol','-count=1'],scratch/'services',goenv)
  # Public-input parity collector remains immutable; review observations are separate.
  shutil.copyfile(PROD/'compare.go',scratch/'services/producer_compare.go')
  shutil.copyfile(PROD/'collect.exs',scratch/'producer_collect.exs')
  run('original-go-vector-parity',['go','run','./producer_compare.go','protocol/testdata/signed-release-v3.json','protocol/testdata/release-v3-cases.json',str(output/'original-go.json')],scratch/'services',goenv)
  run('original-elixir-vector-parity',['mix','run','--no-start',str(scratch/'producer_collect.exs'),str(scratch/'services/protocol/testdata/signed-release-v3.json'),str(scratch/'services/protocol/testdata/release-v3-cases.json'),str(output)],scratch/'hosted',env)
  assert json.loads((output/'original-go.json').read_text())==json.loads((output/'elixir-results.json').read_text())
  shutil.copyfile(OUT/'adversarial.exs',scratch/'adversarial_review.exs')
  run('independent-adversarial-cases',['mix','run','--no-start',str(scratch/'adversarial_review.exs'),str(scratch/'services/protocol/testdata/signed-release-v3.json'),str(output)],scratch/'hosted',env)
  shutil.copyfile(OUT/'oracle.go',scratch/'services/review_oracle.go')
  run('independent-go-oracle',['go','run','./review_oracle.go',str(output)],scratch/'services',goenv)
  run('accepted-hosted-full-suite',['python3','scripts/test-local.py','--output',str(output/'hosted')],scratch/'hosted',env)
  assert all(digest(scratch/name)==want for name,want in inputs.items())
  status='passed'
 except BaseException as e:
  failure=repr(e);raise
 finally:
  if (scratch/'erl_crash.dump').exists():(scratch/'erl_crash.dump').unlink()
  shutil.rmtree(scratch)
  helpers={str(p.relative_to(ROOT)):digest(p) for p in [OUT/'run.py',OUT/'adversarial.exs',OUT/'oracle.go'] if p.exists()}
  receipt=dict(schema=1,status=status,failure=failure,baseRevision=BASE,sourceTreeSHA256=sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()),sourceArchiveSHA256=digest(output/'source.tar.gz') if (output/'source.tar.gz').exists() else None,sourceInputs=inputs,reviewHelpers=helpers,dependencies=deps,commands=commands,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scratchPath=str(scratch),cleanup=dict(isolatedSourceRemoved=not scratch.exists(),ephemeralPrivateKeysPersisted=False,existingProcessesAndDevicesTouched=False),scope='Frozen artifact component only. No live source, producer packet, tracker, gate, HTTP, auth, storage, device, publication or GA change.')
  (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
