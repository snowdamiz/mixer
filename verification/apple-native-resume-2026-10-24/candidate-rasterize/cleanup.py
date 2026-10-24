#!/usr/bin/env python3
import pathlib,json,subprocess,datetime
OUT=pathlib.Path(__file__).resolve().parent
lifecycle=json.loads((OUT/'simulator-lifecycle.json').read_text());sim=lifecycle['ownedSimulator'];commands=[]
def run(*argv,check=True):
 r=subprocess.run(argv,text=True,capture_output=True);commands.append(dict(argv=list(argv),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 (OUT/'cleanup.json').write_text(json.dumps(dict(ownedSimulator=sim,commands=commands,allOwnedSimulatorsRetired=False),indent=2)+'\n')
 if check and r.returncode:raise RuntimeError(r.stderr)
 return r
before=json.loads(run('xcrun','simctl','list','devices','--json').stdout)
matching=[d for ds in before['devices'].values() for d in ds if d['udid']==sim]
assert len(matching)==1 and matching[0]['name']=='MixerAppearanceV2Resume20261024'
try:run('xcrun','simctl','terminate',sim,'dev.mixer.verification.appearancev2')
finally:
 try:run('xcrun','simctl','shutdown',sim)
 finally:run('xcrun','simctl','delete',sim)
after=json.loads(run('xcrun','simctl','list','devices','--json').stdout)
assert sim not in {d['udid'] for ds in after['devices'].values() for d in ds}
preserved={d['udid'] for ds in lifecycle['before']['devices'].values() for d in ds}
assert preserved.issubset({d['udid'] for ds in after['devices'].values() for d in ds})
receipt=dict(ownedSimulator=sim,commands=commands,allOwnedSimulatorsRetired=True,before=before,after=after,preservedOtherSimulatorIDs=sorted(preserved),physicalDeviceDiscovery=False,frontend='pending separate CUA quit of frontend launched by this lane at 01:56:13 local')
(OUT/'cleanup.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(allOwnedSimulatorsRetired=True,preservedOtherSimulatorCount=len(preserved))))
