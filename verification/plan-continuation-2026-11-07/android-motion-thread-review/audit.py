import hashlib,json,os,subprocess,sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
PARENT=OUT.parents[2]
CAND=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-9ff4db6c')
E=CAND/'verification/plan-continuation-2026-11-07/android-motion-thread-fix'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=20)
def digest(m):return hashlib.sha256(''.join(p+'\0'+v['sha256']+'\n' for p,v in sorted(m.items())).encode()).hexdigest()
mapping=json.loads((E/'final-source-map.json').read_text())
assert all(ident(CAND/p)==v==ident(E/'final-inputs'/p) for p,v in mapping.items())
patch=(E/'implementation.patch').read_bytes()
assert patch==git(CAND,'diff','--binary','--',*mapping)
applied=subprocess.run(['git','-C',str(PARENT),'apply','--check',str(E/'implementation.patch')],capture_output=True,timeout=20)
assert applied.returncode==0,applied.stderr
assert all(git(PARENT,'show','HEAD:'+p)==git(CAND,'show','HEAD:'+p) for p in mapping)
assert all((PARENT/p).read_bytes()==git(PARENT,'show','HEAD:'+p) for p in mapping)
canonical=json.loads((E/'canonical-source-inputs-final.json').read_text())
assert len(canonical['files'])==101
assert all(ident(CAND/p)==v for p,v in canonical['files'].items())
assert digest(canonical['files'])==canonical['sha256']
policy=(CAND/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
profile=json.loads(policy.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
for kind,root,count in [('sdk','sdk',22),('adapter','native/android',24)]:
 assert len(profile[kind+'_files'])==count
 assert digest(profile[kind+'_files'])==profile[kind+'_compatibility_sha256']
 for p,v in profile[kind+'_files'].items():
  source=CAND/root/p
  if kind=='adapter' and (p.startswith('Sources/') or p=='Package.swift'):source=CAND/root/'engine'/p
  assert ident(source)==v,(kind,p)
assert profile['id']=='mixer.android-source-pair.9'
unchanged={p:ident(CAND/p) for p in ['native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java','native/android/app/src/dev/mixer/android/NativeRenderer.java','native/android/tests/private-owner-barrier-map.json']}
for p in unchanged:assert (CAND/p).read_bytes()==(PARENT/p).read_bytes()==git(CAND,'show','HEAD:'+p)
old=git(CAND,'show','HEAD:native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java').decode()
new=(CAND/'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java').read_text()
checks=json.loads((E/'instrumentation-preservation.json').read_text())
assert len(checks['originalSmokeChecks'])==11 and all(s in old and s in new for s in checks['originalSmokeChecks'])
start=old.index('    private void awaitPresentation(');end=old.index('    private static byte[] retained(',start)
assert old[start:end] in new
assert all(new.count(s)==1 for s in checks['originalReadinessCalls'])
baseline={}
for p,v in json.loads((E/'baseline-custody.json').read_text()).items():
 source=Path(p)
 assert ident(source)==v
 baseline[p]=v
 # Parent preserves renamed/selected evidence: verify same-named copies when present.
 copy=PARENT/'verification/plan-continuation-2026-11-07/runtime-followup-observation/motion-callback'/source.name
 if copy.exists():assert ident(copy)==v
result={'status':'PASS','python':sys.version,'parentHead':git(PARENT,'rev-parse','HEAD').decode().strip(),'candidateBase':git(CAND,'rev-parse','HEAD').decode().strip(),'patch':ident(E/'implementation.patch'),'changedFiles':mapping,'parentApplyCheck':{'exit':applied.returncode,'stdout':applied.stdout.decode(),'stderr':applied.stderr.decode()},'candidateAndFrozenInputsMatch':True,'parentChangedPathsUnmodifiedFromCandidateBase':True,'profile':{'id':profile['id'],'sdkCount':22,'adapterCount':24,'sdkSHA256':profile['sdk_compatibility_sha256'],'adapterSHA256':profile['adapter_compatibility_sha256']},'canonical':{'count':101,'sha256':canonical['sha256']},'unchangedGuardsLedgerBarrierMap':unchanged,'original11SmokeChecksAnd3ReadinessBudgetsPreserved':True,'baselineCustody':baseline,'scope':'pure source/hash/patch checks; no product edits, native, build, or release qualification'}
(OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS source/hash/profile/101 canonical inputs/parent patch check/11 smoke assertions/3 unchanged readiness budgets/baseline custody')
