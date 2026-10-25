#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
scratch=Path(json.loads((HERE/'bindings.json').read_text())['scratch'])
node=Path('/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node')
name=sys.argv[1]
argv=[str(node)]+sys.argv[2:]
env=os.environ.copy();env['PATH']=str(node.parent)+os.pathsep+env['PATH']
env['MIXER_CONTROLLER_TEST_REPORT']=str(HERE/'producer-replay-report.json')
start=datetime.now(timezone.utc).isoformat();t=time.monotonic()
with (HERE/(name+'.stdout')).open('wb') as out,(HERE/(name+'.stderr')).open('wb') as err:
    r=subprocess.run(argv,cwd=scratch/'hosted-worker-controller',env=env,stdout=out,stderr=err)
def record(path):return {'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
meta={'argv':argv,'cwd':str(scratch/'hosted-worker-controller'),'start_utc':start,'elapsed_seconds':time.monotonic()-t,'exit_code':r.returncode,'environment':{'MIXER_CONTROLLER_TEST_REPORT':env['MIXER_CONTROLLER_TEST_REPORT']},'frozen_source_tree_sha256':json.loads((HERE/'bindings.json').read_text())['source_tree_sha256'],'stdout':record(HERE/(name+'.stdout')),'stderr':record(HERE/(name+'.stderr'))}
(HERE/(name+'.command.json')).write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta));sys.exit(r.returncode)
