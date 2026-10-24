"""Build the review summaries and seal only this independently owned packet."""
import hashlib,json,shutil
from pathlib import Path
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/stripe-webhook-transport'
PRODUCER_SEAL='a36676ab1ab9bf1d0f98077d86d7f375b7c46a18c13cdb4bcd1adb24ce5d430d'
CANDIDATE='62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0'
CAPTURE='a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea'
BASELINE='ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')

assert sha(PRODUCER/'seal.json')==PRODUCER_SEAL
assert sha(HERE/'candidate/lib/mixer_hosted/billing/webhook_transport.ex')==CANDIDATE
shutil.copyfile(PRODUCER/'seal.json',HERE/'producer-bindings.json')
replay=HERE/'run-1'
independent=HERE/'run-5'
adv=read(replay/'adversarial/adversarial.json')
review=read(independent/'review-independent/review-independent.json')
assert review['summary']=={'total':12,'failures':0,'excluded':0,'skipped':0}
rows=review['rows']
write(HERE/'sink-inventory.json',{'schema':1,'scope':'dedicated-owned-BEAM-only','inventories':[r for r in rows if r['kind']=='inventory'],'teardown':[r for r in rows if r['kind']=='cleanup'],'rawCollectorLeaks':sum(r['raw'] for r in review['logger_events']),'stdoutAndMergedStderr':'run-5/review-independent.log','arbitraryPrivilegedSinkPreventionClaim':False})
baseline={r['id']:r for r in read(replay/'baseline-wire/events.json')}
composed={r['id']:r for r in read(replay/'composed-wire/events.json')}
common=[]
for id,b in baseline.items():
 c=composed.get(id)
 if b['outcome']=='captured' and c and c['outcome']=='captured':
  assert all(b[k]==c[k] for k in ['bodySHA256','bodyBytes','signatureValues'])
  common.append(id)
comparison=[]
for id in ['h1-no-body','h1-slow-gap','h2-slow-gap','h2-late-success']:
 item={'id':id}
 for phase,events in [('baseline-wire',baseline),('composed-wire',composed)]:
  item[phase]={'captureEvent':events.get(id),'client':next(c for c in read(replay/phase/'clients.json') if c['id']==id)}
 comparison.append(item)
write(HERE/'baseline-comparison.json',{'schema':1,'commonSuccessfulCaptureArgumentsByteExact':True,'commonSuccessfulCaptureIDs':sorted(common),'baselineSuccessfulCaptures':28,'composedSuccessfulCaptures':27,'differences':comparison,'selectedIdleMilliseconds':1000,'historicalBaselineH2IdleMilliseconds':2000,'coarseSleepingClientElapsedIsNotPeerDeathMeasurement':True})
metrics=[r for r in adv['rows'] if r['kind']=='resources']
write(HERE/'resource-observations.json',{'schema':1,'replayRun':'run-1','samples':metrics,'sampleCount':len(metrics),'sampledMaxRSSKiB':max(r['vm_rss_kib'] for r in metrics),'sampledMaxHeapWords':max(p['heap_words'] for r in metrics for p in r['processes']),'sampledMaxBinaryReferenceBytes':max(p['binary_bytes'] for r in metrics for p in r['processes']),'sampledMaxMailboxMessages':max(p['mailbox'] for r in metrics for p in r['processes']),'hardMemoryCeilingClaim':False,'absolutePeakClaim':False,'osContainerFailureBehaviorQualified':False})
statuses={
 'P01':('scoped-private-pass','Exact frozen source/tool/dependency binding; private marker-only role; no product integration.',[]),
 'P02':('scoped-local-pass','Original stage probes: incomplete H1 headers, H2 preface and CONTINUATION; <=deadline+100ms.',[]),
 'P03':('scoped-local-pass','Original five-second frozen reader/seven-second held response; independent real zero-window response with PINGs closes at 7000ms.',[]),
 'P04':('scoped-local-pass','Original caller/generation/replay/forged metadata probes plus independent exact-expiry, expired begin/finish, delayed guard reply and generation probes.',[]),
 'P05':('scoped-local-pass','Original peer and owner disposal; independent H2 preinstalled monitors observe original connection and distinct reader DOWN.',[]),
 'P06':('scoped-negative-control-pass','Stream-only kill intentionally leaves PING/PONG-capable connection; not protected-profile evidence.',[]),
 'P07':('scoped-owned-sinks-pass','Sole control subscriber, eight fixed events; measurement and metadata raw sentinels; no exporter; drift negative control expressly shows no privileged prevention.', ['Privileged arbitrary subscribers and IO remain outside trusted bootstrap boundary.']),
 'P08':('scoped-owned-sinks-pass','All primary callbacks, default/ssl/collector filters and formatters inventoried; raw reports, metadata, genuine ignored trailers, parser/unknown-frame/crash and teardown logs dropped; safe counter observed.', ['Dump/core collection and collector retention need operational review.']),
 'P09':('scoped-local-pass','Bootstrap rejects unknown sinks/subscribers; malformed registration, detach/drift, listener/owner/guard/reader failure and explicit fresh bootstrap tested.', ['No promise of atomic prevention for privileged runtime reconfiguration.']),
 'P10':('finite-local-profile-pass','Sixteen slots/overflow, line/header/count/encoded/decoded/frame limits; 3 valid SETTINGS vectors, 11 invalid SETTINGS/window vectors, 4 live SETTINGS transitions, 3 window cases, 2 reset bursts and 5 second-stream orderings.', ['64 reset frames are submitted; whole-connection disposal/max_requests may win before all are parsed. The dependency 16-per-second reset threshold is not isolated, and is not needed to claim this stricter one-request private profile. No exhaustive hostile-input or sustained-load claim.']),
 'P11':('sampled-local-only-os-ceiling-pending','Fresh replay max-body and hostile heap/binary/mailbox/RSS samples retained.', ['Select actual independently enforced OS/container CPU, memory, process, socket and egress limits; measure overload/OOM/termination and raw-dump/export behavior with accountable operational reviewer.']),
 'P12':('private-discard-scoped-public-policy-pending','H1/H2 valid undeclared trailers discarded by pinned adapter; exact captured body/signatures preserved; configured sinks protected.', ['Root and ingress/privacy reviewers must choose public discard-versus-reject and qualify deployed framing path/provider compatibility.']),
 'P13':('scoped-local-cleanup-pass','All five attempts retain source archives/output/compiled BEAMs/seals; all owned groups gone, observed ports refused and identity-marked scratch removed.',[]),
 'P14':('pending-not-run','Local TCP/h2c only.', ['Accountable ingress/operational reviewer must qualify real TLS 1.2/1.3 ALPN and deployed Cloudflare ingress byte/header/framing/backpressure/timeouts/retention.']),
 'P15':('pending-not-run','No Stripe provider or authority interaction.', ['Separate accountable billing/security review must qualify test-mode delivery and endpoint/account/mode/generation/secret ownership. Catalog-inspector/authority reviews remain separate and were not retried.']),
 'P16':('pending-not-run','No inbox/DB/Oban/billing/domain acknowledgment or GA claim.', ['Deduplicated durable inbox with atomic Oban enqueue before authenticated acknowledgment, duplicate/out-of-order reconciliation and realistic G23 billing/account workflows remain required.'])
}
original=read(PRODUCER/'matrix.json')
matrix=[]
for p in original['rows']:
 status,evidence,pending=statuses[p['id']]
 matrix.append({'id':p['id'],'boundary':p['boundary'],'requiredCases':p['requiredCases'],'reviewStatus':status,'observedEvidence':evidence,'remainingPrerequisites':pending,'reviewer':'independent transport source/behavior/privacy lane','evidenceRuns':['run-1','run-5'] if p['id'] not in ['P14','P15','P16'] else []})
write(HERE/'matrix.json',{'schema':1,'rows':matrix,'publicAdmissionAccepted':False,'gaAccepted':False})
findings=[
 {'id':'R01','severity':'scope-limitation','launchBlocking':True,'privateSliceBlocking':False,'finding':'Public admission remains unqualified for OS/container limits, TLS/ALPN/Cloudflare ingress, provider compatibility and trailer policy.','matrix':['P11','P12','P14']},
 {'id':'R02','severity':'scope-limitation','launchBlocking':True,'privateSliceBlocking':False,'finding':'This transport permit authorizes private exact-byte capture only. Endpoint/account/mode/generation/secret authority, inbox/Oban atomicity and billing/G23 remain unqualified.','matrix':['P15','P16']},
 {'id':'R03','severity':'trusted-boundary','launchBlocking':False,'privateSliceBlocking':False,'finding':'No supported telemetry API atomically prevents a privileged subscriber or raw IO. Bootstrap/reconfiguration must remain trusted; drift detection cannot undo prior delivery. Negative controls establish that limitation.','matrix':['P07','P08','P09']},
 {'id':'R04','severity':'integration-condition','launchBlocking':False,'privateSliceBlocking':False,'finding':'Keep dedicated-role sink bootstrap before listener start and retain schema filters through crash/teardown. The future trusted Plug must always dispose in an after/finally path; capture errors return halted connections while the independent deadline stays active.','sourceLines':[37,84,625,718],'matrix':['P01','P03','P08','P09']},
 {'id':'R05','severity':'evidence-limitation','launchBlocking':False,'privateSliceBlocking':False,'finding':'Finite H2 hostile cases and burst submission demonstrate protected-profile behavior; they do not independently validate the dependency reset-rate threshold or sustained hostile-load ceilings.','matrix':['P10','P11']}
]
write(HERE/'findings.json',{'schema':1,'scopedCandidateDefects':[],'findings':findings,'recommendation':'accept-frozen-private-development-candidate-only','publicAdmissionRecommended':False,'gaRecommended':False})
attempts=[]
for p in sorted(HERE.glob('run-*'),key=lambda p:int(p.name.split('-')[1])):
 r=read(p/'receipt.json')
 phases=[x['label'] for x in r['commands'] if x['label'] in ['baseline-component','baseline-wire','composed-wire','adversarial','stream-negative','review-independent']]
 attempts.append({'run':p.name,'failure':r['failure'],'phases':phases,'compiledCandidateObserved':bool(list(p.glob('*/compiled/Elixir.MixerHosted.Billing.WebhookTransport.beam'))),'cleanupPassed':r['cleanup']['scratchRemoved'] and r['cleanup']['ownedProcessGroupsEmpty'] and not r['cleanup']['openHolders'],'interpretation':{'run-1':'Original producer harness replay passed.','run-2':'Failed review harness: JSON tuple serialization, concurrent stop race, zero-window test closed on 1s idle before adding PINGs. No candidate defect inferred.','run-3':'Failed review harness: second recv on a locally closed socket was not a fresh peer-close measurement. Original EOF was already observed.','run-4':'Initial corrected ten-group independent suite passed.','run-5':'Expanded final twelve-group independent suite passed.'}[p.name]})
write(HERE/'attempts.json',attempts)
timing=[r for r in adv['rows'] if r['kind'] in ['stage','deadline']]+[r for r in rows if r['kind']=='actual_window_block']
write(HERE/'receipt.json',{'schema':1,'observedUTC':datetime.now(timezone.utc).isoformat(),'reviewer':'independent transport source/behavior/privacy lane','candidateSHA256':CANDIDATE,'producerSealSHA256':PRODUCER_SEAL,'acceptedBaselineSourceDigest':BASELINE,'acceptedBaselineInputs':71,'unchangedCaptureSHA256':CAPTURE,'acceptedReplayRun':'run-1','acceptedIndependentRun':'run-5','retainedAttempts':len(attempts),'independentGroups':12,'independentClientVectors':34,'originalComponentTests':14,'originalBaselineWireGroups':13,'originalComposedWireGroups':13,'originalComposedClients':105,'originalAdversarialTests':13,'actualComposedVerifierReturns':27,'actualAdversarialVerifierCalls':2,'actualIndependentVerifierReturns':review['actual_verifier_returns'],'inlineIndependentVerifierCalls':review['inline_verifier_calls'],'rejectionVerifierCalls':0,'sourceReviewLines':{'sinks':[1,226],'guards':[228,347],'owner':[349,615],'profileAndCapture':[617,720]},'timing':timing,'recommendation':'accept-frozen-private-development-candidate-only','scopedCandidateDefects':0,'arbitraryPrivilegedSubscriberPreventionClaim':False,'osMemoryCeilingClaim':False,'physicalDeviceEvidence':False,'nativeStarted':False,'liveProductChanged':False,'trackerChanged':False,'gitActions':False,'providerContacted':False,'databaseChanged':False,'credentialsChanged':False,'catalogInspectorOrAuthorityReviewRetried':False,'publicAdmissionAccepted':False,'gaAccepted':False,'limitations':['local macOS TCP/h2c development evidence only','known original timing differences retained','trusted bootstrap and owned sink configuration only','no OS/VM/native allocation ceiling','no TLS/ALPN or Cloudflare ingress','no Stripe provider/authority or durable billing/G23 evidence'],'verificationCommand':['python3','-B','verification/stripe-webhook-transport-review/verify.py']})
files={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(HERE.rglob('*')) if p.is_file() and p!=HERE/'seal.json'}
doc=ROOT/'docs/stripe-webhook-transport-review.md'
files[str(doc.relative_to(ROOT))]={'sha256':sha(doc),'bytes':doc.stat().st_size}
write(HERE/'seal.json',files)
print(json.dumps({'sealed':True,'files':len(files),'attempts':len(attempts),'recommendation':'accept-frozen-private-development-candidate-only','sealSHA256':sha(HERE/'seal.json')},sort_keys=True))
