#!/usr/bin/env python3
"""Bounded owned simulator lifecycle and state/compositor collection.

Native user input is supplied through CUA, never through this script. Install
must be invoked only while simulator runtime testing is authorized and the Mac
is available for the actual CUA qualification. No physical-device discovery.
"""
import argparse,pathlib,subprocess,json,datetime,time,shutil,sys
PACKET=pathlib.Path(__file__).resolve().parent
OUT=PACKET/'runtime';OUT.mkdir(exist_ok=True)
LIFECYCLE=OUT/'lifecycle.json'
COMMANDS=OUT/'commands.json'
commands=json.loads(COMMANDS.read_text()) if COMMANDS.exists() else []
def run(args,check=True):
 r=subprocess.run(list(map(str,args)),text=True,capture_output=True)
 commands.append(dict(argv=list(map(str,args)),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 COMMANDS.write_text(json.dumps(commands,indent=2)+'\n')
 if check and r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout.strip()
def lifecycle():return json.loads(LIFECYCLE.read_text())
def save(data):LIFECYCLE.write_text(json.dumps(data,indent=2)+'\n')
def container():return pathlib.Path(lifecycle()['container'])
def state():return json.loads((container()/'Documents/observations.json').read_text())
def command(value):
 (container()/'Documents/command.txt').write_text(value)
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  if (container()/'Documents/stage.txt').exists() and (container()/'Documents/stage.txt').read_text()==value:return
  time.sleep(.03)
 raise RuntimeError('No app command acknowledgement: '+value)
def capture(name):
 run(['xcrun','simctl','io',lifecycle()['ownedSimulator'],'screenshot',OUT/(name+'.png')])
 shutil.copy2(container()/'Documents/observations.json',OUT/(name+'-observations.json'))
 print(json.dumps(dict(capture=name,state=state()['state']),indent=2))
parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['install','command','capture','held','collect','cleanup']);parser.add_argument('value',nargs='?');parser.add_argument('--after-held-command');args=parser.parse_args()
if args.operation=='install':
 if LIFECYCLE.exists() and not lifecycle().get('cleanedUp'):raise RuntimeError('One owned simulator already exists; reuse it')
 before=json.loads(run(['xcrun','simctl','list','devices','--json']))
 runtimes=json.loads(run(['xcrun','simctl','list','runtimes','--json']))['runtimes']
 runtime=next(x for x in runtimes if x.get('isAvailable') and x['version']=='26.5')
 sim=run(['xcrun','simctl','create','MixerAuthoredToggleQualification','com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',runtime['identifier']])
 data=dict(ownedSimulator=sim,runtime={k:runtime[k] for k in ['identifier','version','buildversion','bundlePath'] if k in runtime},before=before,startedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='One disposable iOS26.5 simulator; four existing iOS27 devices preserved; no Android or physical device use')
 save(data)
 try:
  run(['xcrun','simctl','boot',sim]);run(['xcrun','simctl','bootstatus',sim,'-b'])
  run(['xcrun','simctl','status_bar',sim,'override','--time','9:41','--dataNetwork','wifi','--wifiMode','active','--wifiBars','3','--batteryState','charged','--batteryLevel','100'])
  run(['xcrun','simctl','install',sim,PACKET/'build/MixerAuthoredToggle.app'])
  data['container']=run(['xcrun','simctl','get_app_container',sim,'dev.mixer.verification.authoredtoggle','data']);save(data)
  run(['xcrun','simctl','launch',sim,'dev.mixer.verification.authoredtoggle'])
  deadline=time.monotonic()+25
  while time.monotonic()<deadline:
   if (container()/'Documents/observations.json').exists():break
   time.sleep(.1)
  else:raise RuntimeError('App did not record initial state')
  capture('initial')
 except Exception:
  run(['xcrun','simctl','shutdown',sim],False);run(['xcrun','simctl','delete',sim],False)
  data['cleanedUp']=True;data['failureCleanup']=True;save(data);raise
elif args.operation=='command':
 command(args.value);print(json.dumps(state()['state'],indent=2))
elif args.operation=='capture':capture(args.value)
elif args.operation=='held':
 deadline=time.monotonic()+18
 while time.monotonic()<deadline:
  if state()['state']['highlighted'] and state()['state']['tracking']:break
  time.sleep(.03)
 else:raise RuntimeError('No actual UIKit highlighted/tracking hold within 18 seconds')
 capture(args.value+'-held')
 if args.after_held_command:
  command(args.after_held_command);capture(args.value+'-'+args.after_held_command)
elif args.operation=='collect':
 shutil.copy2(container()/'Documents/observations.json',OUT/'observations.json')
 print(json.dumps(dict(checks=state()['checks'],state=state()['state']),indent=2))
elif args.operation=='cleanup':
 data=lifecycle();sim=data['ownedSimulator']
 if not data.get('cleanedUp'):
  if 'container' in data and (container()/'Documents/observations.json').exists():shutil.copy2(container()/'Documents/observations.json',OUT/'observations.json')
  run(['xcrun','simctl','shutdown',sim],False);run(['xcrun','simctl','delete',sim],False)
  data['cleanedUp']=True
 data['after']=json.loads(run(['xcrun','simctl','list','devices','--json']))
 before_ids={d['udid']:d['state'] for ds in data['before']['devices'].values() for d in ds}
 after_ids={d['udid']:d['state'] for ds in data['after']['devices'].values() for d in ds}
 data['preservedExistingDeviceIDsAndStates']=all(after_ids.get(k)==v for k,v in before_ids.items())
 data['ownedDeviceAbsent']=sim not in after_ids
 data['endedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(data)
 print(json.dumps(data,indent=2))
