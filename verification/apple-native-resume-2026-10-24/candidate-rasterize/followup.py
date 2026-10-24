#!/usr/bin/env python3
import pathlib,subprocess,json,sys,time,datetime,hashlib,shutil
OUT=pathlib.Path(__file__).resolve().parent
sim=json.loads((OUT/'simulator-lifecycle.json').read_text())['ownedSimulator']
logpath=OUT/'followup-commands.json';log=json.loads(logpath.read_text()) if logpath.exists() else []
def run(*argv):
 start=time.time();r=subprocess.run(argv,capture_output=True,text=True)
 log.append(dict(argv=list(argv),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsedSeconds=time.time()-start));logpath.write_text(json.dumps(log,indent=2)+'\n')
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout.strip()
container=pathlib.Path(run('xcrun','simctl','get_app_container',sim,'dev.mixer.verification.appearancev2','data'))
if sys.argv[1]=='installed':
 app=pathlib.Path(run('xcrun','simctl','get_app_container',sim,'dev.mixer.verification.appearancev2','app'))
 manifest=json.loads((OUT/'built-app-manifest.json').read_text())
 hashes={name:hashlib.sha256((app/name).read_bytes()).hexdigest() for name in manifest['files']}
 assert all(manifest['files'][name]['sha256']==digest for name,digest in hashes.items())
 (OUT/'installed-app-receipt.json').write_text(json.dumps(dict(simulator=sim,appPath=str(app),hashes=hashes,matchesRetainedBuiltApp=True,commands=log),indent=2)+'\n')
else:
 stage=sys.argv[1];name=sys.argv[2] if len(sys.argv)>2 else stage
 (container/'Documents/command.txt').write_text(stage)
 log.append(dict(operation='writeNativeHarnessControlFile',stage=stage,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));logpath.write_text(json.dumps(log,indent=2)+'\n')
 for _ in range(100):
  if (container/'Documents/stage.txt').read_text()==stage:break
  time.sleep(.05)
 else:raise RuntimeError('stage timeout '+stage)
 time.sleep(.2)
 shutil.copy2(container/'Documents/observations.json',OUT/(name+'-observations.json'))
 run('xcrun','simctl','io',sim,'screenshot',str(OUT/(name+'.png')))
print(json.dumps(dict(simulator=sim,container=str(container))))
