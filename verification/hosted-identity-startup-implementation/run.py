#!/usr/bin/env python3
import datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
O=Path(__file__).resolve().parent; R=O.parents[1]; state=json.loads((O/'state.json').read_text()); S=Path(state['scratch']).resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(O/'state.json').write_text(json.dumps(state,indent=2)+'\n')
def run(label,argv,env=None,timeout=300):
    log=O/(label+'.log'); start=time.monotonic(); now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open('wb') as f:
      try: code=subprocess.run(argv,cwd=S/'hosted',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
      except subprocess.TimeoutExpired: f.write(b'\nCOLLECTOR TIMEOUT\n'); code=124
    state['commands'].append({'label':label,'argv':list(map(str,argv)),'cwd':str(S/'hosted'),'exitCode':code,'elapsedSeconds':time.monotonic()-start,'observedUTC':now,'output':log.name,'outputSHA256':sha(log),'environment':{k:v for k,v in (env or {}).items() if k in ['MIX_ENV','MIXER_TEST_DATABASE_PORT','MIXER_TEST_IDENTITY_EVIDENCE']}});save(); print(json.dumps(state['commands'][-1]),flush=True); return code
if sys.argv[1]=='apply':
    for p in (O/'overlay').rglob('*'):
      if p.is_file():
        dst=S/p.relative_to(O/'overlay');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
    print(S)
elif sys.argv[1]=='format':
    run('format-attempt-'+sys.argv[2],['mix','format'])
    for p in (O/'overlay').rglob('*'):
      if p.is_file():shutil.copy2(S/p.relative_to(O/'overlay'),p)
elif sys.argv[1]=='unit':
    env=dict(os.environ,MIX_ENV='test')
    run('unit-attempt-'+sys.argv[2],['mix','test','--warnings-as-errors','--seed','0','test/mixer_hosted/identity/startup_config_test.exs'],env)
elif sys.argv[1]=='host':
    env=dict(os.environ,MIX_ENV='test',GIT_DIR=subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=R,text=True).strip(),GIT_WORK_TREE=str(S))
    run('host-suite-attempt-'+sys.argv[2],['python3','scripts/test-local.py','--output',str(O/('host-suite-'+sys.argv[2]))],env,timeout=300)
