#!/usr/bin/env python3
"""Freeze this producer packet; root owns integration and acceptance."""
import datetime,difflib,hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];I=json.loads((O/'inputs.json').read_text());S=Path(json.loads((O/'state.json').read_text())['scratch']);F=R/I['frozenPacket']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(files):return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
A=json.loads((O/'overlay-manifest.json').read_text());T=json.loads((O/'tested-source-manifest.json').read_text());H=json.loads((O/'host-1/receipt.json').read_text());L=json.loads((O/'linux-1-receipt.json').read_text())
assert H['status']==L['status']=='passed'
assert 'Result: 93 passed, 2 skipped' in (O/'host-1/tests.log').read_text()
assert 'Result: 95 passed' in (O/'linux-1-tests.log').read_text()
assert 'Result: 10/14 passed' in (O/'focused-baseline.log').read_text() and 'Failed: 4 tests' in (O/'focused-baseline.log').read_text()
assert 'Result: 14 passed' in (O/'focused-corrected.log').read_text()
assert all(H['cleanup'].values()) and all(L['cleanup'].values())
assert sha(F/'receipt.json')==I['frozenReceiptSHA256'] and sha(F/'tested-source.tar.gz')==I['frozenArchiveSHA256']
assert all(sha(F/'overlay'/p)==h==A['files'][p] for p,h in I['frozenOverlay'].items())
assert sha(O/'implementation.patch')==A['patchSHA256'] and sha(O/'correction-vs-frozen.patch')==A['correctionDeltaSHA256']
assert all(sha(S/p)==h for p,h in T['files'].items())
deps={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted/deps').rglob('*')) if p.is_file() and '_build' not in p.relative_to(S).parts};assert deps==I['dependencies']
live={str(p.relative_to(R)):sha(p) for p in sorted((R/'hosted').rglob('*')) if p.is_file() and not {'deps','_build','__pycache__','cover'}.intersection(p.relative_to(R).parts) and p.name!='erl_crash.dump'}
assert live==I['liveHosted'],'live source changed before freeze'
# Validate archives independently of the remaining owned source scratch.
with tarfile.open(O/'tested-source.tar.gz') as t:
 archive={m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers()}
assert archive==T['files'] and digest(archive)==T['digest']
assert all(h==T['files'][p] for p,h in H['inputs'].items())
linux_inputs=json.loads((O/'linux-1-inputs.json').read_text())
assert all(linux_inputs[p]==h for p,h in T['files'].items() if p.startswith('hosted/'))
assert {p:h for p,h in linux_inputs.items() if p.startswith('hosted/deps/')}==I['dependencies']
M=json.loads((O/'linux-1-metrics/startup-production-network.json').read_text())
assert M['startupDNSQueries']==M['startupConnections']==M['productionPolicyBypasses']==0
assert M['coldTokenAdmitted'] and M['oldLeaseRejectedAfterRestart'] and M['restartColdAdmission'] and M['shutdownInflightCancelled'] and M['allThreeConnectionsClosed'] and M['fixtureKeyDirectoryRemoved']
# Capture collector lineage: test-local is exactly frozen; the Linux adapter is
# the original collector with only owned scratch/name/helper location changes.
original=F/'run_linux.py';adapter=O/'run_linux.py'
(O/'linux-collector-vs-original.patch').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),adapter.read_text().splitlines(True),fromfile=str(original.relative_to(R)),tofile=str(adapter.relative_to(R)))))
assert sha(O/'linux_netns_setup.exs')==sha(R/'verification/hosted-key-owner-implementation/linux_netns_setup.exs')
save('collector-lineage.json',{'hostCollector':{'source':'verification/hosted-identity-startup-implementation/overlay/hosted/scripts/test-local.py','sha256':sha(F/'overlay/hosted/scripts/test-local.py'),'candidateSHA256':sha(S/'hosted/scripts/test-local.py'),'unchanged':True},'linuxCollector':{'source':'verification/hosted-identity-startup-implementation/run_linux.py','sourceSHA256':sha(original),'adapter':'run_linux.py','adapterSHA256':sha(adapter),'delta':'linux-collector-vs-original.patch','deltaSHA256':sha(O/'linux-collector-vs-original.patch'),'changes':'platform-selected unique temporary directory, unique owned container prefix, packet-local unchanged namespace helper'},'namespaceHelper':{'source':'verification/hosted-key-owner-implementation/linux_netns_setup.exs','sha256':sha(O/'linux_netns_setup.exs'),'unchanged':True},'metrics':'Fresh outputs under host-1/identity-metrics and linux-1-metrics; no frozen outputs reused'})
# Only the known unique source scratch is removed. Observe open handles first.
check=subprocess.run(['lsof','-nP','+D',str(S)],capture_output=True)
(O/'scratch-open-handles.log').write_bytes(check.stdout+check.stderr)
assert check.returncode in [0,1] and not check.stdout, 'scratch still has open handles'
shutil.rmtree(S)
cleanup={'ownedMacSourceScratch':str(S),'openHandles':{'argv':['lsof','-nP','+D',str(S)],'exitCode':check.returncode,'output':'scratch-open-handles.log','outputSHA256':sha(O/'scratch-open-handles.log'),'observedOpenHandles':False},'ownedMacSourceScratchRemoved':not S.exists(),'macPostgres':H['cleanup'],'linux':L['cleanup'],'scope':'Only unique producer-owned scratch, PostgreSQL fixtures and containers. Other projects, physical/native instances and live hosted source untouched.'}
save('cleanup.json',cleanup)
outputs={str(p.relative_to(O)):sha(p) for p in sorted(O.rglob('*')) if p.is_file() and p.name!='receipt.json'}
receipt={'schema':1,'status':'frozen-for-fresh-independent-and-root-review-not-applied','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':I['revision'],'liveHostedDigest':I['liveHostedDigest'],'frozenSourceDigest':I['frozenSourceDigest'],'testedSourceDigest':T['digest'],'dependencyDigest':I['dependencyDigest'],'sourceArchiveSHA256':sha(O/'tested-source.tar.gz'),'patchSHA256':A['patchSHA256'],'correctionDeltaSHA256':A['correctionDeltaSHA256'],'overlayFiles':A['files'],'allTenFrozenOverlayFilesUnchanged':True,'productionCorrection':'Exactly two Manifest regular expression anchor replacements: ^/$ to \\A/\\z. No transport or startup production change against frozen candidate.','newTests':'Separate manifest_endpoint_test.exs; direct Manifest and configured StartupConfig endpoint regression/valid grammar/boundaries.','originalPacket':{'path':I['frozenPacket'],'receiptSHA256':I['frozenReceiptSHA256'],'archiveSHA256':I['frozenArchiveSHA256'],'unchanged':True},'contract':{'path':'docs/hosted-identity-startup-contract.md','sha256':sha(R/'docs/hosted-identity-startup-contract.md')},'documentation':{'path':'docs/hosted-identity-startup-correction.md','sha256':sha(R/'docs/hosted-identity-startup-correction.md')},'finalResults':{'focusedBaseline':'10/14 passed; 4 expected LF rejection failures on unchanged frozen production source','focusedCorrected':'14 passed','macOS':'93 passed; 2 explicit Linux namespace skips','Linux':'95 passed; zero skips','releaseBuild':'passed','missingConfiguration':'expected exit 1','productionTestOnlyExports':'all four excluded'},'caseEvidence':{'endpointRejection':['focused-baseline.log','focused-corrected.log','overlay/hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs'],'IS01_IS02':['host-1/tests.log','linux-1-tests.log'],'IS03':['host-1/identity-metrics/startup-empty-state.json','host-1/tests.log'],'IS04':['linux-1-metrics/startup-production-network.json','linux-1-tests.log'],'IS05':['host-1/identity-metrics/startup-lifecycle.json','linux-1-metrics/startup-production-network.json'],'IS06':['host-1/receipt.json','host-1/release-build.log','host-1/release-missing-config.log','host-1/release-test-exclusion.log','linux-1-receipt.json']},'failedAttempts':[{'evidence':'focused-baseline.log','expected':True,'reason':'Regression demonstration against the original frozen production source: terminal-LF host and path accepted by both direct Manifest and configured startup. Identical tests then pass with only both anchor replacements.'}],'unexpectedFailedAttempts':[],'limitations':['Fresh independent correction review and root source/evidence acceptance still required.','Configuration acceptance defect observed; no unsafe network request, request smuggling, SSRF or successful transport exploit claimed.','Development evidence only; no GA gate closed.','Synthetic loopback PostgreSQL has no TLS; production database TLS options are tested configuration only.','Synthetic CA roots reach only the pure constructor in tests; production roots remain OTP standard source.','No real identity provider, authenticated HTTP routes, membership, permissions, discovery, native or physical-phone qualification.','No production publication, customer operation or credential change.'],'cleanup':cleanup,'bindings':outputs}
save('receipt.json',receipt)
print(json.dumps({'status':receipt['status'],'sourceDigest':T['digest'],'overlayFiles':len(A['files']),'boundOutputs':len(outputs),'cleanup':cleanup}))
