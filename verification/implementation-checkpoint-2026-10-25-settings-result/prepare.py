#!/usr/bin/env python3
import datetime,hashlib,json,stat,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(BASE/n).write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def run(n,argv):
 r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60);(BASE/(n+'.stdout')).write_bytes(r.stdout);(BASE/(n+'.stderr')).write_bytes(r.stderr);assert r.returncode==0,(n,r.stderr)
 return {'argv':argv,'exitCode':r.returncode,'stdoutSHA256':sha(BASE/(n+'.stdout')),'stderrSHA256':sha(BASE/(n+'.stderr'))}
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT)
commands=[run('native-verify',['python3','-B','verification/apple-settings-instrumented-native/verify_result.py']),run('linux-artifact-verify',['python3','-B','verification/github-ci-4a4d8b73-controller/review_artifact.py'])]
names={'PLAN.md','STATUS.md','work-graph.json','docs/hosted-worker-pending-registry-engine-correction.md','docs/hosted-worker-pending-registry-engine-correction-review.md'}
packets=[('verification/apple-settings-instrumented-runtime-preparation/handoff.json','ca361bde1632c4ad4bbaf517817b9d8a5a9426a25d462738a9e03eeeb1786a3c'),('verification/apple-settings-instrumented-runtime-review/handoff.json','dbfcd7c074acbe63b27bd26a94d77f72c494fa4fdc8b0f9b6792aa2d83da049f'),('verification/apple-settings-instrumented-native/handoff.json','3e068b73e1a5ee88227657f0708477e6e1feb3a99d20cfb95c0c9ca0e2339a53')]
for n,h in packets:
 p=ROOT/n;assert sha(p)==h;names.add(n)
 for member,row in json.loads(p.read_text())['members'].items():
  q=ROOT/member;assert sha(q)==row['sha256'] and q.stat().st_size==row['bytes'],member;names.add(member)
names.add('verification/apple-settings-instrumented-runtime-preparation/dispatch-attempts/4c0ed51e-8060-4646-83a5-873b875d4d30.json')
dirs=['hosted-worker-pending-registry-engine-correction','hosted-worker-pending-registry-engine-correction-review','github-ci-29b33e40-engine','github-ci-4a4d8b73-controller','github-delivery-registry-components']
for d in dirs:
 for p in (ROOT/'verification'/d).rglob('*'):
  assert not p.is_symlink(),p
  if p.is_file():names.add(str(p.relative_to(ROOT)))
for n,h in [('hosted-worker-pending-registry-engine-correction','3af44bc2353edab386ba20b30e647a71a2b70301c3e37ba2aea50de100a381f1'),('hosted-worker-pending-registry-engine-correction-review','c1c53d5437854fb9fb0aa24fabd19cc5cb9053f4c40ca29393801da1abe4ce29')]:
 p=ROOT/'verification'/n/'receipt.json';assert sha(p)==h
 for item in json.loads(p.read_text())['artifacts']:
  q=ROOT/item['path'];assert sha(q)==item['sha256'] and q.stat().st_size==item['bytes'],q
for n in names:
 p=ROOT/n;s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size<50000000,p
 assert not {'node_modules','owned-build','owned-source','owned-review','target','tmp'}.intersection(p.relative_to(ROOT).parts),p
 assert 'native-run-v6-' not in n,'Raw native artifacts stay local: '+n
save('verification.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parentRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':commands,'nativeMembers':48,'nativeRawFilesVerified':2257,'scope':'One failed native attempt with safe first-failure diagnostic, complete cleanup, frozen failed worker correction review and accepted Linux host CI. Active lane implementations excluded.','gaAccepted':False})
names.update(str(p.relative_to(ROOT)) for p in BASE.iterdir() if p.is_file())
names.update([str(BASE.relative_to(ROOT)/'selected-files.json'),str(BASE.relative_to(ROOT)/'source-hashes.json')]);names=sorted(names)
save('selected-files.json',names)
save('source-hashes.json',{n:sha(ROOT/n) for n in names if n not in [str(BASE.relative_to(ROOT)/'selected-files.json'),str(BASE.relative_to(ROOT)/'source-hashes.json')]})
print(json.dumps({'selectedFiles':len(names),'bytes':sum((ROOT/n).stat().st_size for n in names)}))
