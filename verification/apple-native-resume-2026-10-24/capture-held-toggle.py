#!/usr/bin/env python3
"""Observe the actual native state during a separately authorized CUA held click."""
import pathlib,subprocess,time,json,datetime,sys,shutil
out=pathlib.Path(sys.argv[1]);container=pathlib.Path(sys.argv[2]);sim=sys.argv[3]
log={'scope':'Native state/compositor observation during CUA Simulator click durationMs12000; no synthesized native touch API','startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[]}
# Wait for the actual public native observer instead of assuming tool latency.
nonce=str(time.time_ns())
for poll in range(160):
 stage='held-poll-'+nonce+'-'+str(poll)
 (container/'Documents/command.txt').write_text(stage)
 for _ in range(60):
  if (container/'Documents/stage.txt').read_text()==stage:break
  time.sleep(.02)
 data=json.loads((container/'Documents/observations.json').read_text())
 if data['observations'][-1]['after']['nodes']['toggle'].get('authoredPressed'):break
 time.sleep(.1)
else:raise RuntimeError('No actual native held observer state within bounded observation')
for stage in ['held-toggle-1','held-toggle-2','disable-held-toggle']:
 (container/'Documents/command.txt').write_text(stage)
 for _ in range(100):
  if (container/'Documents/stage.txt').read_text()==stage:break
  time.sleep(.05)
 if stage == 'disable-held-toggle':time.sleep(.25)
 args=['xcrun','simctl','io',sim,'screenshot',str(out/(stage+'.png'))]
 r=subprocess.run(args,text=True,capture_output=True)
 log['commands'].append(dict(argv=args,exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 shutil.copy2(container/'Documents/observations.json',out/(stage+'-observations.json'))
 time.sleep(.5)
(out/'held-toggle-capture.json').write_text(json.dumps(log,indent=2)+'\n')
