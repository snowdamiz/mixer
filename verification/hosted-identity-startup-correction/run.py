#!/usr/bin/env python3
import datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];state=json.loads((O/'state.json').read_text());S=Path(state['scratch']).resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(O/'state.json').write_text(json.dumps(state,indent=2)+'\n')
def run(label,argv,env=None,timeout=300):
 log=O/(label+'.log');assert not log.exists();t=time.monotonic();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with log.open('wb') as f:
  try:code=subprocess.run(argv,cwd=S/'hosted',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
  except subprocess.TimeoutExpired:f.write(b'\nCOLLECTOR TIMEOUT\n');code=124
 command={'label':label,'argv':list(map(str,argv)),'cwd':str(S/'hosted'),'exitCode':code,'elapsedSeconds':time.monotonic()-t,'observedUTC':now,'output':log.name,'outputSHA256':sha(log),'environment':{k:v for k,v in (env or {}).items() if k in ['MIX_ENV','GIT_DIR','GIT_WORK_TREE','MIXER_TEST_IDENTITY_EVIDENCE']}}
 state['commands'].append(command);save();print(json.dumps(command),flush=True);return code
mode=sys.argv[1];attempt=sys.argv[2]
if mode=='apply':
 for p in (O/'overlay').rglob('*'):
  if p.is_file():
   dst=S/p.relative_to(O/'overlay');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
elif mode=='format':
 code=run('format-'+attempt,['mix','format','test/mixer_hosted/identity/manifest_endpoint_test.exs'])
 shutil.copy2(S/'hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs',O/'overlay/hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs');sys.exit(code)
elif mode=='focused':
 sys.exit(run('focused-'+attempt,['mix','test','--warnings-as-errors','--seed','0','test/mixer_hosted/identity/manifest_endpoint_test.exs','test/mixer_hosted/identity/startup_config_test.exs'],dict(os.environ,MIX_ENV='test')))
elif mode=='host':
 env=dict(os.environ,MIX_ENV='test',GIT_DIR=subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=R,text=True).strip(),GIT_WORK_TREE=str(S))
 sys.exit(run('host-'+attempt,['python3','scripts/test-local.py','--output',str(O/('host-'+attempt))],env,timeout=300))
