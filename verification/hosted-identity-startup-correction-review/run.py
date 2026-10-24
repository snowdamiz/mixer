#!/usr/bin/env python3
import datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];s=json.loads((O/'state.json').read_text());S=Path(s['scratch'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(label,argv,env=None,timeout=300):
 log=O/(label+'.log');assert not log.exists();t=time.monotonic();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with log.open('wb') as f:
  try:code=subprocess.run(argv,cwd=S/'hosted',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
  except subprocess.TimeoutExpired:f.write(b'\nREVIEW TIMEOUT\n');code=124
 c={'label':label,'argv':argv,'cwd':str(S/'hosted'),'observedUTC':now,'elapsedSeconds':time.monotonic()-t,'exitCode':code,'output':log.name,'outputSHA256':sha(log),'environment':{'MIX_ENV':env.get('MIX_ENV')} if env else {}}
 s['commands'].append(c);(O/'state.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(c),flush=True);return code
mode=sys.argv[1];env=dict(os.environ,MIX_ENV='test')
if mode=='tools':
 for label,argv in [('elixir',['elixir','--version']),('mix',['mix','--version']),('python',['python3','--version']),('openssl',['openssl','version']),('kernel',['uname','-a'])]:assert run('tool-'+label,argv)==0
elif mode in ['boundary-format','boundary-format-2']:
 shutil.copy2(O/'review_endpoint_boundary_test.exs',S/'hosted/test/mixer_hosted/identity/review_endpoint_boundary_test.exs')
 assert run(mode,['mix','format','test/mixer_hosted/identity/review_endpoint_boundary_test.exs'],env)==0
 shutil.copy2(S/'hosted/test/mixer_hosted/identity/review_endpoint_boundary_test.exs',O/'review_endpoint_boundary_test.exs')
else:
 selections={'old-adversarial':['review_startup_adversarial_test.exs'],'old-minimal':['endpoint_regression_test.exs'],'correction-focused':['manifest_endpoint_test.exs','startup_config_test.exs'],'independent-boundary':['review_endpoint_boundary_test.exs'],'independent-boundary-2':['review_endpoint_boundary_test.exs']}
 sys.exit(run(mode,['mix','test','--warnings-as-errors','--seed','0','--trace']+['test/mixer_hosted/identity/'+p for p in selections[mode]],env))
