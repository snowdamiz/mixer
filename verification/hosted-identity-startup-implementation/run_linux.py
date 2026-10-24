#!/usr/bin/env python3
import datetime,hashlib,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];state=json.loads((O/'state.json').read_text());S=Path(state['scratch']).resolve();attempt=sys.argv[1]
L=Path(tempfile.mkdtemp(prefix='mixer-identity-startup-linux-',dir='/private/tmp')).resolve()
shutil.copytree(S/'hosted',L/'hosted',ignore=shutil.ignore_patterns('_build','__pycache__','erl_crash.dump'))
shutil.copytree(S/'services',L/'services')
shutil.copytree(Path.home()/'.mix/archives/hex-2.5.1',L/'mix/archives/hex-2.5.1')
shutil.copy2(Path.home()/'.mix/elixir/1-20-otp-29/rebar3',L/'rebar3')
shutil.copy2(R/'verification/hosted-key-owner-implementation/linux_netns_setup.exs',L/'linux_netns_setup.exs')
name='mixer-identity-startup-'+L.name.rsplit('-',1)[1];pg=name+'-pg';commands=[];cleanup={};status='failed'
image='hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde'
pgimage='postgres@sha256:c961aa287d8698297cb26cdfadfbe9fd2cbaf77e53cfffe9636e8d8a1e4d842c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(label,argv,check=True,timeout=300):
 log=O/f'linux-{attempt}-{label}.log';t=time.monotonic()
 with log.open('wb') as f:
  try:code=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
  except subprocess.TimeoutExpired:f.write(b'\nCOLLECTOR TIMEOUT\n');code=124
 commands.append({'label':label,'argv':argv,'exitCode':code,'elapsedSeconds':time.monotonic()-t,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'output':log.name,'outputSHA256':sha(log)})
 print(json.dumps(commands[-1]),flush=True)
 if check and code:raise RuntimeError(label+' failed')
 return code
try:
 for n in [name,pg]:
  assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+n+'$'],text=True).strip()
 run('image-inspect',['docker','image','inspect',image,pgimage])
 run('container-start',['docker','run','--rm','-d','--name',name,'--network','none','--cap-add','NET_ADMIN','--memory','1g','--cpus','4','-v',str(L)+':/workspace','-v',str(O)+':/evidence','-w','/workspace/hosted','-e','MIX_HOME=/workspace/mix','-e','MIX_REBAR3=/workspace/rebar3','-e','MIXER_ISOLATED_NETNS=1','-e','MIX_ENV=test','-e','MIXER_TEST_DATABASE_PORT=5432','-e','MIXER_TEST_IDENTITY_EVIDENCE=/evidence/linux-'+attempt+'-metrics',image,'sleep','infinity'])
 run('postgres-start',['docker','run','--rm','-d','--name',pg,'--network','container:'+name,'--memory','256m','-e','POSTGRES_USER=mixer_fixture','-e','POSTGRES_DB=mixer_foundation_test','-e','POSTGRES_HOST_AUTH_METHOD=trust',pgimage,'-c','listen_addresses=127.0.0.1'])
 for i in range(50):
  ready=subprocess.run(['docker','exec',pg,'pg_isready','-U','mixer_fixture'],capture_output=True)
  if ready.returncode==0:break
  time.sleep(.2)
 else:raise RuntimeError('owned postgres readiness timeout')
 run('startup-createdb',['docker','exec',pg,'createdb','-U','mixer_fixture','mixer_startup_test'])
 (O/('linux-'+attempt+'-metrics')).mkdir()
 run('netns',['docker','exec',name,'elixir','/workspace/linux_netns_setup.exs'])
 run('tools',['docker','exec',name,'bash','-c','elixir --version; mix --version; openssl version; uname -a'])
 run('format',['docker','exec',name,'mix','format','--check-formatted'])
 run('tests',['docker','exec',name,'mix','test','--warnings-as-errors','--seed','0','--trace'])
 run('fixture-cleanup',['docker','exec',name,'elixir','-e','values = Enum.filter(File.ls!(System.tmp_dir!()), &String.starts_with?(&1, "mixer-key-owner-tls-")); IO.inspect(values, label: "retained_fixture_key_directories"); [] = values'])
 status='passed'
finally:
 for n in [pg,name]:
  run('cleanup-'+n,['docker','rm','-f',n],check=False)
  cleanup[n]=not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+n+'$'],text=True).strip()
 # Keep all attempt source manifests even if tests fail; remove only owned temp.
 files={str(p.relative_to(L)):sha(p) for p in sorted((L/'hosted').rglob('*')) if p.is_file() and not {'_build','__pycache__'}.intersection(p.relative_to(L).parts) and p.name!='erl_crash.dump'}
 (O/f'linux-{attempt}-inputs.json').write_text(json.dumps(files,indent=2)+'\n')
 shutil.rmtree(L);cleanup['ownedScratchRemoved']=not L.exists()
 (O/f'linux-{attempt}-receipt.json').write_text(json.dumps({'schema':1,'status':status,'source':str(S),'linuxScratch':str(L),'images':[image,pgimage],'network':'none; PostgreSQL shares owned namespace; no host mutation','capabilitiesAdded':['NET_ADMIN'],'commands':commands,'cleanup':cleanup,'scope':'Full hosted suite including actual configured application/endpoint, production DNS+HTTPS signed-token admission. Synthetic PostgreSQL without TLS; production DB TLS configuration only. No physical/native/GA qualification.'},indent=2)+'\n')
