"""Seal a completed owned candidate packet; failures are never rewritten."""
import difflib,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def main():
 assert not (HERE/'seal.json').exists(),'immutable packet already sealed; create a reviewed new packet for more work'
 name=sys.argv[1] if len(sys.argv)>1 else 'run-14';run=HERE/name
 evidence=read(run/'adversarial/adversarial.json');assert not read(run/'receipt.json')['failure']
 attempts=[]
 for p in sorted(HERE.glob('run-*'),key=lambda p:int(p.name.split('-')[1])):
  receipt=read(p/'receipt.json')
  attempts.append({'run':p.name,'failure':receipt['failure'],'sealSHA256':sha(p/'seal.json'),'freshCandidateCompilationObserved':any((p/phase/'compiled').exists() for phase in ['composed-wire','adversarial','stream-negative']),'historicalIntendedCompilationFlagNotAClaimOfCompletedCompilation':bool(receipt['failure'])})
 write(HERE/'attempts.json',attempts)
 source=HERE/'candidate/lib/mixer_hosted/billing/webhook_transport.ex'
 (HERE/'candidate.patch').write_text(''.join(difflib.unified_diff([],source.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/hosted/lib/mixer_hosted/billing/webhook_transport.ex')))
 resources=[r for r in evidence['rows'] if r['kind']=='resources']
 process=[p for r in resources for p in r['processes']]
 peaks={'sampleCount':len(resources),'vmRSSKiB':max(r['vm_rss_kib'] for r in resources),'vmBinaryBytes':max(r['vm_binary_bytes'] for r in resources),'vmTotalBytes':max(r['vm_total_bytes'] for r in resources),'processMemoryBytes':max(p['memory_bytes'] for p in process),'heapWords':max(p['heap_words'] for p in process),'totalHeapWords':max(p['total_heap_words'] for p in process),'processBinaryReferencesBytes':max(p['binary_bytes'] for p in process),'mailboxMessages':max(p['mailbox'] for p in process),'samplingScope':'observed snapshots in bounded local cases; not an absolute peak or resource ceiling','hardMemoryCeiling':False}
 write(HERE/'resource-observations.json',peaks)
 comparison=[]
 for case in ['h1-no-body','h1-slow-gap','h2-slow-gap','h2-late-success']:
  row={'id':case}
  for phase in ['baseline-wire','composed-wire']:
   client=next(c for c in read(run/phase/'clients.json') if c['id']==case)
   row[phase]={'statuses':client['statuses'],'serverEnd':client['serverEnd'],'elapsedMs':client['elapsedMs'],'captureEvent':client['event']}
  row['interpretation']='selected one-second idle or independent five-second disposal may prevent a capture return; no verifier on rejection; client elapsed can be a coarse upper bound after deliberate send sleeps'
  comparison.append(row)
 write(HERE/'baseline-comparison.json',comparison)
 capture=read(ROOT/'verification/stripe-raw-body-capture/matrix.json')
 capture['transportCandidateReplay']=name
 capture['unchangedBaseline']={'componentTests':14,'wireGroups':13,'clients':105,'rawSinkExposurePreserved':True}
 capture['composedReplay']={'wireGroups':13,'clients':105,'actualVerifierReturns':27,'timingChanges':'baseline-comparison.json','publicIngressStillPending':True}
 capture['allRowsPassed']=False
 write(HERE/'capture-matrix.json',capture)
 matrix=read(ROOT/'verification/stripe-webhook-transport-contract/matrix.json')
 notes={
 'P01':('scoped-local-pass','14 unchanged component tests + 13 unchanged wire groups + 13 composed wire groups; capture/signature source unchanged; public ingress row remains pending'),
 'P02':('scoped-local-pass-tls-handshake-pending','H1 header drip and H2 preface/unfinished CONTINUATION with PINGs observed within selected stage deadline+100ms; real TLS handshake unrun'),
 'P03':('scoped-local-pass','real H2 frozen/queued reader and outer blocked response; actual 5s/7s owner and peer disposal; original component late-read/flatten refusal remains baseline; VM starvation/suspension has no real-time guarantee'),
 'P04':('scoped-local-pass','issued/capturing/consumed one-use caller+generation+deadline permits, replay/unknown/forged conn fields; exact expiry checks with deliberately suspended own guard; original HTTP envelope tests retained'),
 'P05':('scoped-local-pass','guard monitors exact original connection and distinct H2 request owners, retires only after observed DOWN; no pipeline continuation, no detached reader; response blocking retains outer guard'),
 'P06':('scoped-negative-control-pass','fresh isolated stream-only cancellation leaves connection alive with PING/PONG and no response/reset in 200ms; guard intentionally absent; never called composed qualification'),
 'P07':('scoped-owned-sink-pass-independent-review-pending','only private control subscriber configured; raw measurements and metadata injected; no raw exporter; privileged attachment cannot be atomically prevented or retroactively undone'),
 'P08':('scoped-owned-sink-pass-independent-review-pending','default, OTP ssl_handler, explicitly declared collector, fixed standard formatters and stdout/stderr captured; H2 trailers/opaque reports dropped; missing-filter drift records already delivered collector data; no arbitrary filter failure prevention claim'),
 'P09':('scoped-local-pass','unknown Logger/telemetry bootstrap rejection; malformed registration; owner/guard/listener loss and required subscriber detach close role; explicit trusted restart tested across roles; unknown privileged changes remain outside boundary'),
 'P10':('partial-local-profile-pass','exact sixteen slots and overflow, selected parser/header/frame limits, compressed HPACK header beyond decompressed limit; exhaustive SETTINGS/window extremes/reset flood/new-stream matrix remains pending'),
 'P11':('sampled-local-evidence-os-ceiling-pending','real accepted max H2 body, hostile queued/frozen reader, oversize frame/header snapshots with heap/binary/mailbox/VM RSS; sampled maxima only; independently enforced OS/container limits and failure behavior unselected'),
 'P12':('private-discard-scoped-public-policy-pending','real H1 and H2 undeclared trailers discarded by pinned adapter without changing body/signature; all configured sinks protected; public ingress discard-vs-reject unselected'),
 'P13':('scoped-local-cleanup-pass','all successful/failed attempts retain exact source/output/seals, unique owned groups, refused observed ports, open-holder scans and removed identity-marked scratch; role sinks stay filtered until owned BEAM exit'),
 'P14':('pending-not-run','localhost h2c/TCP only; real TLS1.2/1.3, ALPN, Cloudflare Worker/DO/container ingress and retention unrun'),
 'P15':('pending-not-run','no Stripe contact or authority selection; endpoint/account/mode/generation/secret ownership and provider timing compatibility remain separate'),
 'P16':('pending-not-run','no inbox, schema, DB, migrations, Oban enqueue, billing domain progression or G23 acceptance')}
 for row in matrix['rows']:
  row['observedStatus'],row['candidateEvidence']=notes[row['id']]
  row['evidenceRun']=name
 matrix.update({'rootSelection':'selected-private-direction-only','fullPrivacyQualified':False,'publicAdmissionAccepted':False,'independentImplementationReview':'pending','allRowsPassed':False})
 write(HERE/'matrix.json',matrix)
 timing=[r for r in evidence['rows'] if r['kind'] in ['stage','deadline']]
 write(HERE/'receipt.json',{'schema':1,'status':'sealed-private-candidate-awaiting-independent-review','observedUTC':datetime.now(timezone.utc).isoformat(),'acceptedRun':name,'upstreamRootSelectionSHA256':sha(ROOT/'verification/stripe-webhook-transport-root-review/selection.json'),'upstreamRootBindings':228,'producerFiles':150,'producerSealSHA256':'2ade7904589112ca5329856952eb1653620e996b4f780c30f42ffbfa95ed9847','sourceDigest':'ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc','sourceFiles':71,'unchangedCaptureSHA256':'a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea','candidateSHA256':sha(source),'actualComposedVerifierCalls':27,'actualAdversarialVerifierCalls':evidence['actual_verifier_calls'],'timing':timing,'resourceObservations':'resource-observations.json','freshCandidateCompilation':True,'freshDependencyCompilation':False,'newDependencies':[],'trustedBootstrapOnly':True,'arbitraryPrivilegedSubscriberLeakPreventionClaim':False,'independentReviewAccepted':False,'liveIntegrated':False,'publicAdmissionAccepted':False,'gaAccepted':False,'providerContacted':False,'productionChanged':False,'nativeStarted':False,'trackerChanged':False,'gitActions':False,'verificationCommand':['python3','-B','verification/stripe-webhook-transport/verify.py'],'futureRequired':['independent implementation/privacy review','remaining SETTINGS/window/reset/new-stream matrix','public trailer policy','actual OS/container resource values and enforced failure behavior','TLS/ALPN and deployed Cloudflare ingress','Stripe test-mode provider/account/mode/endpoint/generation/secret authority','durable inbox + atomic Oban enqueue','billing reconciliation and G23']})
 doc=f'''# Private webhook transport candidate

Status: sealed isolated candidate awaiting independent implementation review. No
live product role, route, provider, DB/schema, tracker or Git state was changed.
The [root-selected direction](stripe-webhook-transport-direction.md), frozen
contract and selection receipt remain authoritative. This packet adds no public
admission or G23 acceptance and does not retry catalog-inspector or authority work.

The [candidate source](../verification/stripe-webhook-transport/candidate/lib/mixer_hosted/billing/webhook_transport.ex)
contains a dedicated supervisor, bounded owner, independently supervised guards,
and owned sink boundary. The [patch](../verification/stripe-webhook-transport/candidate.patch)
adds only that proposed hosted module; it is not applied to hosted. Capture and
signature compile freshly from the accepted 71-input source digest
`ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc`.
Capture remains byte-identical at `a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea`.

The profile fixes one acceptor, sixteen connections, retry count zero, backlog
128, one request and one concurrent H2 stream, 1s handshake and header settings,
5s capture, and a 7s outer lifetime. Documented Thousand Island span references
register the original connection before parsing. Documented Bandit request refs
and the exact trusted Plug identity register the original reader. The owner
mints caller/generation/deadline-bound one-use permits, checking before capture,
after flattening and before returning bytes. A final local monotonic comparison
also refuses a delayed owner reply. Permits grant no billing authority.

The per-connection guard never reads the body. Absolute timers and monotonic
checks dispose the whole registered connection using standard Process.exit,
monitoring connection and distinct H2 request owners until DOWN. Body progress
cannot extend the outer lifetime. Successful capture changes the active stage
to the unchanged absolute outer deadline; it does not disarm disposal during a
blocked response. Guard, owner, listener and required registration loss terminate
the dedicated role. Restart requires trusted bootstrap; no unguarded automatic
listener restart is enabled. Unknown/replayed permits fail closed.

The separate owned BEAM inventories all telemetry subscribers, primary Logger
callbacks, handler filters, formatters, default stdout, OTP ssl_handler, declared
collector and merged stderr capture. No APM/error exporter or raw trace subscriber
is configured. Known standard primary/filter callbacks are validated; undeclared
sinks reject bootstrap. Every handler receives the pure schema filter before its
standard logger_formatter callback. Only reconstructed fixed event/reason enums,
bounded integers and fixed domain metadata reach sinks. Arbitrary messages,
metadata, exception reports and H2 trailer warnings are dropped. Protective
filters remain through role teardown and BEAM exit, covering supervisor reports.
The harness's return-only verifier trace suppresses call messages/arguments.

Trusted application/bootstrap and controlled sink configuration are the boundary.
The supported telemetry API cannot atomically stop privileged code from attaching
a raw subscriber. Inventory checks precede registration and permit admission;
25ms drift polling is additional detection, not a confidentiality guarantee. The
privileged subscriber and removed-filter negative controls explicitly make no
prevention claim; the latter observes data already delivered to its collector.
No claim reverses delivered bytes or protects arbitrary IO/diagnostics by
privileged application code. Dynamic third-party instrumentation, dump/core
collection and collector retention need operational review.

[Run {name}](../verification/stripe-webhook-transport/{name}/receipt.json) passes
14 unchanged component tests, 13 unchanged baseline wire groups, 13 composed
wire groups (105 clients), 13 adversarial tests, and a fresh stream-only negative
control. An independent return-only trace measures 27 composed verifier returns,
equal to the actual inline invocation count. Adversarial max-body/blocked-response
cases call the actual verifier {evidence['actual_verifier_calls']} times; no billing/domain work runs.
All responses are private non-2xx markers. The negative control kills only an H2
stream, observes no response/reset in 200ms, then receives PONG on the still-live
connection before explicit cleanup; it is never counted as the protected profile.

The [timing receipt](../verification/stripe-webhook-transport/receipt.json) retains
actual peer closure times and exact monitored disposal overshoot. Under the local
load, H1 headers, H2 preface and unfinished CONTINUATION close at the selected
1s stage, a frozen H2 reader closes at 5s despite PINGs, and blocked response work
closes at the absolute 7s lifetime, each within deadline+100ms. Deliberately
suspended own-guard permit tests separately refuse at/after expiry; they do not
promise real-time scheduling during VM suspension/starvation.

[Baseline comparison](../verification/stripe-webhook-transport/baseline-comparison.json)
retains exact case IDs and outputs. `h2-slow-gap` previously captured after a
1.2s gap under the older 2s idle profile; selected 1s idle disposal rejects it.
`h1-no-body`/`h1-slow-gap` may lose their connection before framework error return,
and `h2-late-success` is disposed rather than returning a late capture failure.
Every recorded rejected case has zero verifier calls. Client elapsed values in
old deliberately sleeping send loops are upper bounds, not exact peer-death
measurements; dedicated adversarial clients observe peer termination directly.
These are narrower transport timings, not a changed capture grammar or a provider
compatibility claim. Original captures and byte/signature arguments remain intact.

H1 Content-Length/chunked and H2 optional Content-Length remain supported. Real
undeclared H1/H2 trailers retain pinned adapter discard semantics and do not
change the exact body/original signature arguments. Their values reach no owned
configured sink. Public discard-versus-reject policy remains unselected.

[Resource observations](../verification/stripe-webhook-transport/resource-observations.json)
include a real accepted 1,048,576-byte H2 terminal DATA body, queued/frozen H2
hostility, sixteen occupied slots, overflow, oversize frames and compressed
headers exceeding the decompressed limit. Observed sampled maxima are RSS
{peaks['vmRSSKiB']} KiB, per-process heap {peaks['heapWords']} words, binary references
{peaks['processBinaryReferencesBytes']} bytes, and {peaks['mailboxMessages']} queued messages.
These are sampled observations, not an absolute peak or memory ceiling. Shared
binary references can overcount allocations; parser/window/body/heap settings do
not establish OS/VM/native resource ceilings. SETTINGS/window extremes, reset
floods and the full new-stream matrix remain explicitly partial in the
[16-row matrix](../verification/stripe-webhook-transport/matrix.json).

All fourteen attempts retain original sources, actual outputs, tool versions,
executable hashes, compiled candidate BEAMs where compilation completed, source
archives and exact seals. Failed runs stay failed. Some early failed receipt
`freshCandidateCompilation` fields recorded intent before a compile completed;
[attempts.json](../verification/stripe-webhook-transport/attempts.json) distinguishes
observed compiled artifacts. Pinned original dependency source closures and
BEAM/source identities are retained; no dependency was added or freshly built.
Every attempt has no remaining owned process group/open scratch holder, refused
observed ports and removed identity-marked scratch. Role cleanup rows additionally
cover every sequential listener, connection/owner/guard supervisor and client.
No host simulator, native device, unrelated process or shared logger was touched.

Independent implementation/privacy review is pending. Public OS/container resource
values and enforced failure behavior, real TLS/ALPN, deployed Cloudflare ingress,
provider test-mode timing/body/header behavior, public trailers, endpoint/account/
mode/generation/secret ownership, durable inbox with atomic Oban enqueue, billing
reconciliation and G23 remain pending. Local evidence cannot pass those gates.

```sh
python3 -B verification/stripe-webhook-transport/verify.py
```

The verifier checks the immutable packet and every retained attempt. A fresh
`run.py` replay creates a new numbered attempt; it invalidates the current sealed
file set until root explicitly accepts and reseals a new packet. Never silently
replace this receipt or reinterpret failed/historical probes as qualification.
'''
 (ROOT/'docs/stripe-webhook-transport-implementation.md').write_text(doc)
 proc=subprocess.run([sys.executable,'-B',str(HERE/'verify.py'),'--preseal'],cwd=ROOT,capture_output=True,text=True)
 (HERE/'verification.log').write_text(proc.stdout+proc.stderr)
 assert proc.returncode==0,(proc.stdout,proc.stderr)
 paths=[p for p in HERE.rglob('*') if p.is_file() and p!=HERE/'seal.json']+[ROOT/'docs/stripe-webhook-transport-implementation.md']
 write(HERE/'seal.json',{str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(paths)})
 print(json.dumps({'sealSHA256':sha(HERE/'seal.json'),'files':len(paths),'acceptedRun':name,'verification':json.loads(proc.stdout)},sort_keys=True))
if __name__=='__main__':main()
