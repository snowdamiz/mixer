#!/usr/bin/env python3
"""Root selects exactly one reviewed simulator dispatch and records ownership."""
import datetime,hashlib,json,os,stat,subprocess,sys,time,uuid
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
OUT=ROOT/"verification/apple-settings-instrumented-native-root-selection"
PRODUCER=ROOT/"verification/apple-settings-instrumented-runtime-preparation"
REVIEW=ROOT/"verification/apple-settings-instrumented-runtime-review"
PYTHON="/opt/homebrew/opt/python@3.14/bin/python3.14"
DEVELOPER="/Applications/Xcode_26.6.app/Contents/Developer"
PACKET="f7ef1ed54b65a71e666646d1e4b54cef1cea5b7afdfee804810ffaf2c65eaeb6"
ENV={**os.environ,"DEVELOPER_DIR":DEVELOPER,"PYTHONDONTWRITEBYTECODE":"1"}
COMMANDS=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (OUT/n).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write("\n")
def verify_handoff(p,expected):
 assert sha(p)==expected,p
 d=json.loads(p.read_bytes())
 for n,row in d['members'].items():
  q=ROOT/n;s=q.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not q.is_symlink(),q
  actual={'bytes':s.st_size,'sha256':sha(q),'kind':'file','mode':stat.S_IMODE(s.st_mode)}
  assert all(actual[k]==v for k,v in row.items()),q
 return len(d['members'])
def cmd(n,argv,filter_frontends=False):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat(); stamp=time.monotonic()
 c=subprocess.Popen(argv,cwd=ROOT,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:out,err=c.communicate(timeout=60)
 except subprocess.TimeoutExpired:
  c.kill();out,err=c.communicate(timeout=5);raise RuntimeError('Precreation command timed out: '+n)
 if filter_frontends:
  ending=DEVELOPER+'/Applications/Simulator.app/Contents/MacOS/Simulator'
  out=('\n'.join(line.strip() for line in out.decode().splitlines() if line.strip().endswith(ending))+'\n').encode()
 (OUT/(n+'.stdout')).write_bytes(out);(OUT/(n+'.stderr')).write_bytes(err)
 ps=subprocess.run(['/bin/ps','-axo','pid=,pgid='],capture_output=True,check=True,timeout=10)
 remaining=[line.strip() for line in ps.stdout.decode().splitlines() if int(line.split()[1])==c.pid]
 row={'name':n,'argv':argv,'startedUTC':start,'elapsedSeconds':time.monotonic()-stamp,'PID':c.pid,'processGroup':c.pid,'exitCode':c.returncode,'stdoutSHA256':sha(OUT/(n+'.stdout')),'stderrSHA256':sha(OUT/(n+'.stderr')),'bothEOF':True,'ownedProcessGroupAbsent':not remaining,'stdoutFilteredToPinnedSimulatorFrontends':filter_frontends}
 COMMANDS.append(row)
 (OUT/'commands.json').write_text(json.dumps(COMMANDS,indent=2,sort_keys=True)+'\n')
 assert c.returncode==0 and not remaining,(n,c.returncode,err.decode())
 return out
OUT.mkdir()
counts={'producer':verify_handoff(PRODUCER/'handoff.json','ca361bde1632c4ad4bbaf517817b9d8a5a9426a25d462738a9e03eeeb1786a3c'),'review':verify_handoff(REVIEW/'handoff.json','dbfcd7c074acbe63b27bd26a94d77f72c494fa4fdc8b0f9b6792aa2d83da049f')}
assert sha(PRODUCER/'packet.json')==PACKET
review=json.loads((REVIEW/'review.json').read_text());assert review['status']=='source-and-host-packaging-accepted' and not review['blockingFindings'] and review['hostTests']['passed']==19 and review['actualV5AndFreshV6All13ApplicationRowsMatch']
baseline=json.loads((REVIEW/'baseline-reconciliation.json').read_text())
for n,row in baseline['actualV5RetainedApplication'].items():assert sha(ROOT/n)==row['sha256'] and (ROOT/n).stat().st_size==row['bytes']
cmd('prepare-verify',[PYTHON,'-B',str(PRODUCER/'prepare.py'),'verify'])
cmd('handoff-verify',[PYTHON,'-B',str(PRODUCER/'seal.py'),'verify'])
save('root-review.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'accepted-for-one-fresh-bounded-native-attempt','memberCounts':counts,'packetSHA256':PACKET,'independentReviewSHA256':sha(REVIEW/'handoff.json'),'actualV5AppRowsReverified':13,'staleTemplateResolved':True,'hostTestsAccepted':19,'nativePassClaimed':False,'gaAccepted':False,'phones':'disconnected-deferred'})
# Native inventory is simulator-only. No phone enumeration or physical-device command.
before=json.loads(cmd('precreation-devices',['/usr/bin/xcrun','simctl','list','devices','--json']))
runtimes=json.loads(cmd('precreation-runtimes',['/usr/bin/xcrun','simctl','list','runtimes','--json']))
front=cmd('precreation-frontends',['/bin/ps','-axo','pid=,lstart=,comm='],True).decode().splitlines();front=[v for v in front if v]
runtime='com.apple.CoreSimulator.SimRuntime.iOS-26-5'
chosen=[v for v in runtimes['runtimes'] if v['identifier']==runtime];assert len(chosen)==1 and chosen[0]['isAvailable'] and chosen[0]['buildversion']=='23F77'
assert not any(v['name'].startswith('MixerFocusReferenceV6-') for rows in before['devices'].values() for v in rows),'Existing owned V6 instance needs reconciliation first'
run=str(uuid.uuid4());name='MixerFocusReferenceV6-'+run[:8]
save('creation-intent.json',{'schema':1,'runID':run,'name':name,'runtime':runtime,'deviceType':'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro','before':before,'beforeFrontends':front,'cleanupOwner':'selected runtime; root emergency recovery','oneAttemptOnly':True})
udid=cmd('create',['/usr/bin/xcrun','simctl','create',name,'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',runtime]).decode().strip();assert str(uuid.UUID(udid)).upper()==udid
save('created-identity.json',{'runID':run,'name':name,'udid':udid,'runtime':runtime,'build':'23F77'})
after=json.loads(cmd('postcreation-devices',['/usr/bin/xcrun','simctl','list','devices','--json']))
matches=[v for v in after['devices'][runtime] if v['udid']==udid];assert len(matches)==1 and matches[0]['name']==name and matches[0]['state']=='Shutdown'
selected=datetime.datetime.now(datetime.timezone.utc).isoformat()
selection={'schema':'mixer.apple-focus-reference-root-selection.6','runID':run,'packetSHA256':PACKET,'selectedAtUTC':selected,'ownedSimulatorIdentity':{'udid':udid,'name':name,'runtime':runtime,'build':'23F77'},'sourceTreeSHA256':review['sourceTreeSHA256'],'productArchiveSHA256':review['productArchiveSHA256'],'developerDirectory':DEVELOPER,'baselineDevices':before,'baselineFrontends':front}
save('selection.json',selection)
argv=[PYTHON,'-B',str(BASE/'observe_dispatch.py'),'--root-selection',str(OUT/'selection.json'),'--root-selection-sha256',sha(OUT/'selection.json')]
save('execution-selection.json',{'schema':1,'selectedUTC':selected,'rootSelectionSHA256':sha(OUT/'selection.json'),'selectedCommand':argv,'driverSHA256':sha(BASE/'observe_dispatch.py'),'selectionDriverSHA256':sha(Path(__file__)),'independentReviewHandoffSHA256':sha(REVIEW/'handoff.json'),'attemptsAuthorized':1,'phones':'disconnected-deferred','cleanupOwner':'selected runner; root emergency recovery'})
print(json.dumps({'selectedRunID':run,'ownedSimulator':udid,'command':argv}),flush=True)
os.execve(PYTHON,argv,ENV)
