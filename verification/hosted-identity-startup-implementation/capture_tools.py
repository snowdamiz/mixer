#!/usr/bin/env python3
import datetime,hashlib,json,shutil,subprocess
from pathlib import Path
O=Path(__file__).resolve().parent
items=[]
for name,argv in [('python',['python3','--version']),('mix',['mix','--version']),('docker',['docker','--version']),('openssl',['openssl','version']),('kernel',['uname','-a'])]:
 r=subprocess.run(argv,capture_output=True,text=True);p=O/('tool-'+name+'.log');p.write_text(r.stdout+r.stderr);exe=Path(shutil.which(argv[0])).resolve()
 items.append({'argv':argv,'exitCode':r.returncode,'output':p.name,'outputSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':str(exe),'executableSHA256':hashlib.sha256(exe.read_bytes()).hexdigest()})
(O/'tool-versions.json').write_text(json.dumps({'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':items},indent=2)+'\n')
