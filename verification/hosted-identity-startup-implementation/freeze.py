#!/usr/bin/env python3
import datetime,difflib,hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];state=json.loads((O/'state.json').read_text());S=Path(state['scratch']).resolve();inp=json.loads((O/'source-inputs.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
assert json.loads((O/'host-suite-4/receipt.json').read_text())['status']=='passed'
assert json.loads((O/'linux-3-receipt.json').read_text())['status']=='passed'
assert 'Result: 85 passed, 2 skipped' in (O/'host-suite-4/tests.log').read_text()
assert 'Result: 87 passed' in (O/'linux-3-tests.log').read_text()
for p in (O/'overlay').rglob('__pycache__'):shutil.rmtree(p)
files={str(p.relative_to(O/'overlay')):sha(p) for p in sorted((O/'overlay').rglob('*')) if p.is_file()}
assert all(sha(S/p)==h for p,h in files.items())
patch=[];changes={}
for path,h in files.items():
 base=R/path; old=base.read_text() if base.exists() else ''
 if base.exists():assert sha(base)==inp['source'][path],path+' live source drift'
 new=(O/'overlay'/path).read_text()
 patch+=difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path if base.exists() else '/dev/null',tofile='b/'+path)
 changes[path]={'baseSHA256':sha(base) if base.exists() else None,'resultSHA256':h}
(O/'implementation.patch').write_text(''.join(patch))
check=subprocess.run(['git','apply','--check',str(O/'implementation.patch')],cwd=R,capture_output=True,text=True)
(O/'patch-apply-check.log').write_text(check.stdout+check.stderr)
save('patch-apply-check.json',{'argv':['git','apply','--check',str(O/'implementation.patch')],'cwd':str(R),'exitCode':check.returncode,'outputSHA256':sha(O/'patch-apply-check.log')})
assert check.returncode==0
save('overlay-manifest.json',{'files':files,'patchSHA256':sha(O/'implementation.patch'),'changes':changes})
source={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted').rglob('*')) if p.is_file() and not {'deps','_build','__pycache__'}.intersection(p.relative_to(S).parts) and p.name!='erl_crash.dump'}
for p in sorted((S/'services/protocol/testdata').rglob('*')):
 if p.is_file():source[str(p.relative_to(S))]=sha(p)
deps={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted/deps').rglob('*')) if p.is_file() and '_build' not in p.relative_to(S).parts}
assert deps==inp['dependencies']
save('tested-source-manifest.json',{'files':source,'digest':hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'dependencyDigest':inp['dependencyDigest']})
with tarfile.open(O/'tested-source.tar.gz','w:gz') as t:
 for path in source:t.add(S/path,arcname=path,recursive=False)
# Commands and test outputs are immutable at this point. Cleanup the sole owned
# Mac scratch only after its archive and exact overlay have been bound.
shutil.rmtree(S)
cleanup={'ownedMacScratchRemoved':not S.exists(),'macPostgres':json.loads((O/'host-suite-4/receipt.json').read_text())['cleanup'],'linux':json.loads((O/'linux-3-receipt.json').read_text())['cleanup'],'scope':'Only unique collector-owned scratch, PostgreSQL and containers; no physical/native/UI work or other-project cleanup'}
save('cleanup.json',cleanup)
outputs={str(p.relative_to(O)):sha(p) for p in sorted(O.rglob('*')) if p.is_file() and p.name not in ['receipt.json']}
receipt={'schema':1,'status':'frozen-for-root-review-not-applied','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':inp['revision'],'baseSourceDigest':inp['sourceDigest'],'testedSourceDigest':json.loads((O/'tested-source-manifest.json').read_text())['digest'],'dependencyDigest':inp['dependencyDigest'],'overlayFiles':files,'patchSHA256':sha(O/'implementation.patch'),'sourceArchiveSHA256':sha(O/'tested-source.tar.gz'),'contract':'docs/hosted-identity-startup-contract.md','contractSHA256':sha(R/'docs/hosted-identity-startup-contract.md'),'documentationSHA256':sha(R/'docs/hosted-identity-startup-implementation.md'),'cases':{'IS01':{'status':'observed','evidence':['host-suite-4/tests.log','linux-3-tests.log']},'IS02':{'status':'observed','evidence':['host-suite-4/tests.log','linux-3-tests.log','otp-ca-source.json']},'IS03':{'status':'observed-actual-application-endpoint','evidence':['host-suite-4/identity-metrics/startup-empty-state.json','host-suite-4/tests.log']},'IS04':{'status':'observed-production-DNS-HTTPS-public-adapter','evidence':['linux-3-metrics/startup-production-network.json','linux-3-tests.log','linux-3-receipt.json']},'IS05':{'status':'observed-actual-application-lifecycle','evidence':['host-suite-4/identity-metrics/startup-lifecycle.json','linux-3-metrics/startup-production-network.json'],'reused':'Existing accepted component TLS resource and shutdown tests were replayed unchanged with the root-owned portability/metrics repair; changed application wiring has its own actual lifecycle tests.'},'IS06':{'status':'observed','evidence':['host-suite-4/receipt.json','host-suite-4/release-build.log','host-suite-4/release-missing-config.log','host-suite-4/release-test-exclusion.log','linux-3-receipt.json']}},'finalResults':{'macOS':'85 passed, 2 Linux-only tests skipped','Linux':'87 passed; zero skips','releaseBuild':'passed','missingConfiguration':'expected exit 1','productionTestOnlyExports':'all excluded'},'failedAttempts':[{'evidence':'unit-attempt-1.log','reason':'Standard OTP CA source produced combined-cert triples; corrected runtime normalization while preserving strict constructor DER inputs.'},{'evidence':'host-suite-1/receipt.json','reason':'Copied scratch had no git metadata; collector rerun received explicit read-only GIT_DIR/GIT_WORK_TREE binding to source revision.'}],'additionalFailedAttempts':[{'evidence':['host-suite-3/receipt.json','linux-2-receipt.json'],'reason':'New processor integration test compared normalized Oban queue keyword options with integer shorthand; corrected assertion to inspect effective limit. Runtime behavior passed and was unchanged.'}], 'supersededPassedAttempts':['unit-attempt-2.log','host-suite-2/receipt.json','linux-1-receipt.json'],'limitations':['Development slice, no GA gate accepted.','Synthetic loopback PostgreSQL uses no TLS; production database TLS settings are tested configuration only.','Synthetic CA material reaches only the pure constructor in tests; production runtime roots come solely from the existing OTP source.','No real identity provider, authenticated HTTP route, membership, permission, discovery, native or physical-device qualification.','No production publication or customer operations.'],'cleanup':cleanup,'bindings':outputs}
save('receipt.json',receipt)
print(json.dumps({'status':receipt['status'],'overlayFiles':len(files),'testedSourceDigest':receipt['testedSourceDigest'],'patchSHA256':receipt['patchSHA256'],'boundOutputs':len(outputs)}))
