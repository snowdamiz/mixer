#!/usr/bin/env python3
import datetime,hashlib,json,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];ART=BASE/'artifact';HEAD='4a4d8b7301351247318424ed71a89ab41f0db2ca'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
r=load(ART/'receipt.json');assert r['status']=='passed' and r['revision']==HEAD and r['platform']=='linux' and r['node']=='v22.23.3' and r['failure'] is None
sources=load(ART/'source-manifest.json')
for name,h in sources.items():
 assert sha(ART/'source'/name)==h,name
 raw=subprocess.check_output(['git','show',HEAD+':'+name],cwd=ROOT);assert hashlib.sha256(raw).hexdigest()==h,name
commands=[]
for q in sorted(ART.glob('*/command.json')):
 d=load(q);assert d['exitCode']==0 and d['processGroupEmpty'] and d['eofObserved'] and d['directChildTerminal'] and d['scratchRemoved'] and not d['timedOut'] and not d['signals'] and not d['processManagementErrors'] and d['sourceDigest']==r['sourceDigest'],q
 for n in ['stdout','stderr']:assert sha(q.parent/n)==d[n+'SHA256'],q
 commands.append(d['name'])
assert len(commands)==6
counts={};cleanups=[]
for n in ['original-report.json','regressions-fixture/regression-report.json','focused-fixture/focused-report.json']:
 d=load(ART/n);assert d['status']=='passed' and all(v['status']=='passed' for v in d['results']);counts[n]=len(d['results']);cleanups.extend(d['cleanup'])
assert list(counts.values())==[28,7,36]
stores=[v for v in cleanups if 'persist' in v];kills=[v for v in cleanups if v.get('signal')=='SIGKILL']
assert len(stores)==153 and all(v['disposed'] and v['storageRemoved'] for v in stores) and len(kills)==8 and all(v['parentRechecked'] for v in kills)
text=(ART/'owned-process-identity/stdout').read_text();assert all(line in text for line in ['# tests 20\n','# pass 20\n','# fail 0\n','# skipped 0\n'])
closure=load(ART/'production-closure.json');local=load(ROOT/'verification/hosted-worker-pending-registry-components-root-integration/live-check/production-closure.json');assert closure['status']=='passed' and closure['files']==local['files'] and len(closure['files'])==9
manifest={str(p.relative_to(BASE)):sha(p) for p in sorted(ART.rglob('*')) if p.is_file()}
result={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':HEAD,'runID':40164349437,'url':'https://github.com/snowdamiz/mixer/actions/runs/40164349437','status':'accepted-Linux-controller-host-regression','platform':r['platform'],'architecture':r['architecture'],'node':r['node'],'sourceFilesVerifiedAgainstCommit':len(sources),'sourceDigest':r['sourceDigest'],'processIdentityControlsPassed':20,'controllerGroupsPassed':counts,'actualWorkerdSIGKILLRecoveries':len(kills),'ownedCommandGroupsCleaned':len(commands),'persistentFixturesRemoved':len(stores),'compiledProductionClosureFilesMatchedLocal':len(closure['files']),'artifactManifest':manifest,'scope':'Existing production-entry/controller regressions only. Newly compiled registry/audit classes remain outside deployed entry; separate retained component tests cover them. No native, provider, clock, restore, deployed or GA qualification.'}
(BASE/'artifact-review.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['sourceFilesVerifiedAgainstCommit','processIdentityControlsPassed','controllerGroupsPassed','persistentFixturesRemoved','status']}))
