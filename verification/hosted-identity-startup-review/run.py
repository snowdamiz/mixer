#!/usr/bin/env python3
"""Independent review command collector. Never writes producer or live sources."""
import datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];s=json.loads((O/'state.json').read_text());S=Path(s['scratch'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(label,argv,env=None,timeout=300):
    log=O/(label+'.log'); started=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
    with log.open('wb') as f:
        try:code=subprocess.run(argv,cwd=S/'hosted',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:f.write(b'\nREVIEW COLLECTOR TIMEOUT\n');code=124
    s['commands'].append({'label':label,'argv':argv,'cwd':str(S/'hosted'),'exitCode':code,'observedUTC':started,'elapsedSeconds':time.monotonic()-t,'output':log.name,'outputSHA256':sha(log),'environment':{k:v for k,v in (env or {}).items() if k in ['MIX_ENV','MIXER_TEST_IDENTITY_EVIDENCE']}})
    (O/'state.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s['commands'][-1]),flush=True)
    return code
env=dict(os.environ,MIX_ENV='test',GIT_DIR=subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=R,text=True).strip(),GIT_WORK_TREE=str(S))
if sys.argv[1]=='tools':
    for n,a in [('elixir',['elixir','--version']),('mix',['mix','--version']),('python',['python3','--version']),('openssl',['openssl','version']),('docker',['docker','version']),('kernel',['uname','-a'])]:run('tool-'+n,a)
elif sys.argv[1]=='host':sys.exit(run('host-suite',['python3','scripts/test-local.py','--output',str(O/'host-suite')],env))
elif sys.argv[1]=='adversarial':
    env['MIXER_TEST_IDENTITY_EVIDENCE']=str(O/'adversarial-metrics');Path(env['MIXER_TEST_IDENTITY_EVIDENCE']).mkdir(exist_ok=True)
    sys.exit(run('adversarial',['mix','test','--warnings-as-errors','--seed','0','--trace','test/mixer_hosted/identity/review_startup_adversarial_test.exs'],env))

elif sys.argv[1]=='endpoint-probe':sys.exit(run('endpoint-probe',['mix','run','--no-start',str(O/'endpoint_probe.exs')],env))

elif sys.argv[1]=='endpoint-regression':sys.exit(run('endpoint-regression',['mix','test','--warnings-as-errors','--seed','0','--trace','test/mixer_hosted/identity/endpoint_regression_test.exs'],env))
