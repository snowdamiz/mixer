#!/usr/bin/env python3
"""Assess bound cumulative receipts without duplicating unchanged normal matrix."""
import hashlib,json,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=R/'verification/hosted-identity-startup-correction';V=R/'verification/hosted-identity-startup-review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
source=json.loads((C/'tested-source-manifest.json').read_text())['files'];inputs=json.loads((C/'inputs.json').read_text());h=json.loads((C/'host-1/receipt.json').read_text());l=json.loads((C/'linux-1-receipt.json').read_text())
# Host collector records all hosted sources plus only the two protocol fixtures it consumes.
consumed={p:v for p,v in source.items() if p.startswith('hosted/') or p in ['services/protocol/testdata/signed-release-v3.json','services/protocol/testdata/release-v3-cases.json']}
assert h['inputs']==consumed and digest(consumed)==h['source_tree_sha256']
assert sha(C/'host-1/source.tar.gz')==h['source_archive_sha256']
with tarfile.open(C/'host-1/source.tar.gz') as t:
 archive={m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}
assert archive==consumed
linux=json.loads((C/'linux-1-inputs.json').read_text());assert linux==({**{p:v for p,v in source.items() if p.startswith('hosted/')},**inputs['dependencies']})
for x in h['commands']:
 assert sha(C/'host-1'/x['log'])==x['sha256']
 assert x['exit_code']==x.get('expected_exit_code',0)
for x in l['commands']:
 assert sha(C/x['output'])==x['outputSHA256'];assert x['exitCode']==0
for n,expected in [('host-1/tests.log','Result: 93 passed, 2 skipped'),('linux-1-tests.log','Result: 95 passed'),('focused-corrected.log','Result: 14 passed'),('focused-baseline.log','Result: 10/14 passed')]:assert expected in (C/n).read_text()
for n,expected in [('old-adversarial.log','Result: 9 passed'),('old-minimal.log','Result: 4 passed'),('correction-focused.log','Result: 14 passed'),('independent-boundary-2.log','Result: 4 passed')]:assert expected in (O/n).read_text()
metrics={n:json.loads((C/n).read_text()) for n in ['host-1/identity-metrics/startup-empty-state.json','host-1/identity-metrics/startup-lifecycle.json','linux-1-metrics/startup-production-network.json']}
a=metrics['host-1/identity-metrics/startup-empty-state.json'];assert a=={'actualApplication':True,'endpointLiveness':200,'ownerRegistered':True,'initialSnapshots':0,'initialAttempts':0,'initialFlights':0,'startupFetches':0}
b=metrics['host-1/identity-metrics/startup-lifecycle.json'];assert all(b.values())
c=metrics['linux-1-metrics/startup-production-network.json'];assert c['actualApplication'] and c['endpointLiveness']==200 and c['coldTokenAdmitted'] and c['startupDNSQueries']==c['startupConnections']==c['productionPolicyBypasses']==0
assert all(c[x] for x in ['oldLeaseRejectedAfterRestart','restartColdAdmission','shutdownInflightCancelled','allThreeConnectionsClosed','fixtureKeyDirectoryRemoved'])
assert h['cleanup']=={'postgres_stopped':True,'scratch_removed':True} and all(l['cleanup'].values())
ca=json.loads((R/'verification/hosted-identity-startup-implementation/otp-ca-source.json').read_text())
assert all(sha(Path(p))==v for p,v in ca['files'].items())
assessment={'normalMatrix':'Reused immutable earlier independent normal runtime evidence plus verified fresh corrected-producer matrix; not rerun by this correction reviewer.','reason':'Only two Manifest anchors differ in production; startup ten-file overlay, transport, owner and dependency bytes are unchanged. Focused independent replay covers the amended boundary; review found no new lifecycle/network concern.','macOSCorrectedProducer':{'passed':93,'skipped':2,'scope':'Linux namespace tests explicitly skipped','receipt':'verification/hosted-identity-startup-correction/host-1/receipt.json','hostInputCount':len(consumed),'sourceTreeDigest':digest(consumed),'hostArchiveVerified':True},'LinuxCorrectedProducer':{'passed':95,'skipped':0,'sourceAndDependencyEntriesVerified':len(linux),'receipt':'verification/hosted-identity-startup-correction/linux-1-receipt.json'},'priorIndependent':{'receipt':'verification/hosted-identity-startup-review/receipt.json','macOSPassed':85,'macOSLinuxOnlySkipped':2,'LinuxPassed':87,'actualApplicationEndpointAndPostgreSQL':True,'productionDNS53HTTPS443SyntheticSignedToken':True,'restartOldLeaseAndInflightShutdown':True},'correctedProducerMetrics':metrics,'releaseCommandsVerified':[x for x in h['commands'] if x['label'] in ['release-build','release-missing-config','release-test-exclusion']],'OTPCAInstalledSourceHashesVerified':ca['files'],'sourceReview':{'staticKnownStringToAtomConversion':True,'singleRuntimeOTPCAFetchAndPreservedDatabaseRoots':True,'pureConstructorRequiresValidDER':True,'closedDuplicateAwareJSONAndFixedErrors':True,'actualApplicationRequiresExplicitSettingBeforeStartingChildren':True,'fixedProductionOwnerBeforeEndpoint':True,'noNewHTTPRouteProviderMembershipOrDiscovery':True},'ownChecks':{'oldAdversarial':9,'oldMinimal':4,'correctionFocused':14,'newIndependentBoundary':4,'totalPassed':31},'ownedRuntimeResources':'No PostgreSQL, containers, native or physical instances created by this focused correction review.'}
(O/'evidence-assessment.json').write_text(json.dumps(assessment,indent=2)+'\n');print(json.dumps({'hostConsumedInputsVerified':len(consumed),'linuxSourceAndDependencyEntriesVerified':len(linux),'freshReviewTestsPassed':31,'unresolvedFindings':0}))
