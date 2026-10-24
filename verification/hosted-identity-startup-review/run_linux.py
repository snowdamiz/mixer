#!/usr/bin/env python3
"""Independent network-none Linux replay; all resources have unique review ownership."""
import datetime,hashlib,json,shutil,subprocess,tempfile,time
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];S=Path(json.loads((O/'state.json').read_text())['scratch'])
L=Path(tempfile.mkdtemp(prefix='mixer-identity-startup-review-linux-',dir='/private/tmp')).resolve()
shutil.copytree(S/'hosted',L/'hosted',ignore=shutil.ignore_patterns('_build','__pycache__','erl_crash.dump','review_startup_adversarial_test.exs'))
shutil.copytree(S/'services',L/'services')
shutil.copytree(Path.home()/'.mix/archives/hex-2.5.1',L/'mix/archives/hex-2.5.1')
shutil.copy2(Path.home()/'.mix/elixir/1-20-otp-29/rebar3',L/'rebar3')
shutil.copy2(R/'verification/hosted-key-owner-implementation/linux_netns_setup.exs',L/'linux_netns_setup.exs')
name='mixer-identity-startup-review-'+L.name.rsplit('-',1)[1];pg=name+'-pg';commands=[];cleanup={};status='failed';advcode=None
image='hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde'
pgimage='postgres@sha256:c961aa287d8698297cb26cdfadfbe9fd2cbaf77e53cfffe9636e8d8a1e4d842c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest():return {str(p.relative_to(L)):sha(p) for p in sorted(L.rglob('*')) if p.is_file() and not {'_build','__pycache__','mix'}.intersection(p.relative_to(L).parts) and p.name not in ['erl_crash.dump','rebar3']}
def run(label,argv,check=True,timeout=300):
 log=O/f'linux-{label}.log';t=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with log.open('wb') as f:
  try:code=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
  except subprocess.TimeoutExpired:f.write(b'\nREVIEW COLLECTOR TIMEOUT\n');code=124
 commands.append({'label':label,'argv':argv,'exitCode':code,'observedUTC':started,'elapsedSeconds':time.monotonic()-t,'output':log.name,'outputSHA256':sha(log)})
 print(json.dumps(commands[-1]),flush=True)
 if check and code:raise RuntimeError(label+' failed')
 return code
base=manifest();(O/'linux-source-inputs.json').write_text(json.dumps(base,indent=2)+'\n')
try:
 for n in [name,pg]:assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+n+'$'],text=True).strip()
 run('image-inspect',['docker','image','inspect',image,pgimage])
 run('container-start',['docker','run','--rm','-d','--name',name,'--network','none','--cap-add','NET_ADMIN','--memory','1g','--cpus','4','-v',str(L)+':/workspace','-v',str(O)+':/evidence','-w','/workspace/hosted','-e','MIX_HOME=/workspace/mix','-e','MIX_REBAR3=/workspace/rebar3','-e','MIXER_ISOLATED_NETNS=1','-e','MIX_ENV=test','-e','MIXER_TEST_DATABASE_PORT=5432','-e','MIXER_TEST_IDENTITY_EVIDENCE=/evidence/linux-metrics',image,'sleep','infinity'])
 run('postgres-start',['docker','run','--rm','-d','--name',pg,'--network','container:'+name,'--memory','256m','-e','POSTGRES_USER=mixer_fixture','-e','POSTGRES_DB=mixer_foundation_test','-e','POSTGRES_HOST_AUTH_METHOD=trust',pgimage,'-c','listen_addresses=127.0.0.1'])
 for _ in range(100):
  if subprocess.run(['docker','exec',pg,'pg_isready','-U','mixer_fixture'],capture_output=True).returncode==0:break
  time.sleep(.2)
 else:raise RuntimeError('owned postgres readiness timeout')
 run('startup-createdb',['docker','exec',pg,'createdb','-U','mixer_fixture','mixer_startup_test'])
 (O/'linux-metrics').mkdir()
 run('netns',['docker','exec',name,'elixir','/workspace/linux_netns_setup.exs'])
 for label,args in [('elixir',['elixir','--version']),('mix',['mix','--version']),('openssl',['openssl','version']),('kernel',['uname','-a'])]:run('tool-'+label,['docker','exec',name]+args)
 run('format',['docker','exec',name,'mix','format','--check-formatted'])
 run('tests',['docker','exec',name,'mix','test','--warnings-as-errors','--seed','0','--trace'])
 assert manifest()==base
 shutil.copy2(O/'review_startup_adversarial_test.exs',L/'hosted/test/mixer_hosted/identity/review_startup_adversarial_test.exs')
 advcode=run('adversarial',['docker','exec',name,'mix','test','--warnings-as-errors','--seed','0','--trace','test/mixer_hosted/identity/review_startup_adversarial_test.exs'],check=False)
 run('fixture-cleanup',['docker','exec',name,'elixir','-e','values = Enum.filter(File.ls!(System.tmp_dir!()), &String.starts_with?(&1, "mixer-key-owner-tls-")); IO.inspect(values, label: "retained_fixture_key_directories"); [] = values'])
 status='normal-suite-passed-adversarial-finding' if advcode else 'passed'
finally:
 for n in [pg,name]:
  run('cleanup-'+n,['docker','rm','-f',n],check=False)
  cleanup[n]=not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+n+'$'],text=True).strip()
 shutil.rmtree(L);cleanup['ownedScratchRemoved']=not L.exists()
 (O/'linux-receipt.json').write_text(json.dumps({'schema':1,'status':status,'scratch':str(L),'images':[image,pgimage],'network':'none; PostgreSQL shares owned namespace; no host mutation','commands':commands,'normalInputs':'linux-source-inputs.json','normalInputDigest':hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'adversarialTestSHA256':sha(O/'review_startup_adversarial_test.exs'),'adversarialExitCode':advcode,'cleanup':cleanup,'scope':'Independent full hosted replay and separately authored adversarial tests. Actual Application/Endpoint/PG, production DNS53+HTTPS443 and public ConfiguredVerifier cold admission; synthetic namespace, CA and identity. No real provider, Neon, native, physical, GA qualification.'},indent=2)+'\n')
