"""Summarize observed candidate evidence without upgrading endpoint/GA gates."""
import difflib, hashlib, json, re
from pathlib import Path
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def main():
    runs=sorted(HERE.glob('run-*'),key=lambda p:int(p.name.split('-')[1]))
    good=[p for p in runs if json.loads((p/'receipt.json').read_text())['failure'] is None]
    latest=good[-1]
    component=json.loads((latest/'component/component-summary.json').read_text())
    wire=json.loads((latest/'wire/wire-summary.json').read_text())
    clients=json.loads((latest/'wire/clients.json').read_text())
    events=json.loads((latest/'wire/events.json').read_text())
    telemetry=json.loads((latest/'wire/telemetry.json').read_text())
    logs=json.loads((latest/'wire/logs.json').read_text())
    assert component['total']==14 and component['failures']==0 and wire['total']==13 and wire['failures']==0
    assert len(clients)==105 and all(not any(200<=s<=299 for s in c['statuses']) for c in clients)
    assert all(e['verifierCalls']==(1 if e['outcome']=='captured' else 0) and e['domainCalls']==0 for e in events)
    by_id={event['id']:event for event in events}
    correlations=[{'id':client['id'],'transport':client['transport'],'statuses':client['statuses'],'classification':by_id.get(client['id'],{}).get('outcome','framework-pre-Plug'),'event':by_id.get(client['id'])} for client in clients]
    write(HERE/'wire-correlations.json',correlations)
    scopes={
      'envelope':('scoped-pass',['Public endpoint first-consumer placement and original-method dispatch remain pending.']),
      'metadata':('scoped-pass',['Public header-read limits and endpoint parser placement remain pending.']),
      'signature-occurrences':('scoped-pass',[]),
      'exact-signature-body':('scoped-pass',[]),
      'content-length':('scoped-pass',['Real exact-maximum CL evidence is HTTP1; no real maximum-size HTTP2 test claimed.']),
      'framing':('scoped-pass-with-trailer-limit',['Undeclared HTTP1 trailers are ignored by pinned Bandit and invisible to capture; no trailer-policy enforcement claimed.']),
      'limits':('scoped-pass',['Requested read size is advisory; adapter/OS buffered memory is not bounded by this component.']),
      'http2':('scoped-h2c-pass',['TLS/ALPN, deployed ingress, and transport privacy are not qualified.']),
      'deadlines':('scoped-success-admission-pass-cancellation-pending',['Slow HTTP2 completed after five seconds then rejected; forced cancellation is unresolved.']),
      'adapter-faults':('scoped-fake-adapter-pass',['Fake adapter evidence is not Bandit/socket evidence; malformed Plug shapes and transport raises propagate.']),
      'logging':('observed-exposure-not-qualified',['ThousandIsland recv measurements.data and Bandit conn metadata expose synthetic sentinels; H2 trailer logger exposes sentinel.']),
      'failure-disposal':('scoped-test-caller-pass-endpoint-pending',['Disposable caller closes HTTP1 responses and all clients/listener are closed; future public endpoint stream/connection disposal and cancellation remain pending.']),
      'ingress':('pending-not-run',['No selected deployed ingress/provider test was run.'])
    }
    matrix=json.loads((REPO/'verification/stripe-raw-body-contract/test-matrix.json').read_text())
    matrix.update(selection='profile-1-normal-bandit',status='scoped-component-and-localhost-evidence-public-admission-pending',allRowsPassed=False,evidenceRun=latest.name)
    for row in matrix['rows']:
        row['status'],row['limitations']=scopes[row['id']]
        row['evidence']=[f'{latest.name}/component.log',f'{latest.name}/wire.log',f'{latest.name}/wire/clients.json',f'{latest.name}/wire/events.json']
        if row['id']=='logging': row['evidence'] += [f'{latest.name}/wire/telemetry.json',f'{latest.name}/wire/logs.json']
    write(HERE/'matrix.json',matrix)
    observations={
      'transportFieldErratum':'ThousandIsland.Socket.recv passes %{data: bytes} as measurements (third untimed_span_event argument), not telemetry metadata. Both measurements and metadata are recursively scanned in final run.',
      'transportBodyEvents':[e for e in telemetry if e['event']==['thousand_island','connection','recv'] and e['measurementBodySeen']],
      'transportSignatureEvents':[e for e in telemetry if e['event']==['thousand_island','connection','recv'] and e['measurementSignatureSeen']],
      'banditMetadataSentinelEvents':[e for e in telemetry if e['event'][0]=='bandit' and (e['metadataBodySeen'] or e['metadataSignatureSeen'] or e['metadataTrailerSeen'])],
      'loggerTrailerEvents':[e for e in logs if e['trailerSeen']],
      'lateHTTP2':[e for e in events if e['id']=='h2-late-success'],
      'http2AdvisoryOvershoot':[e for e in events if e['id']=='h2-exact'],
      'noRedactionOrHardCancellationClaim':True,
    }
    assert observations['transportBodyEvents'] and observations['transportSignatureEvents'] and observations['loggerTrailerEvents']
    write(HERE/'transport-observations.json',observations)
    notes={1:'Fake-adapter malformed-shape test incorrectly used a valid script tuple; corrected harness wrapper, candidate unchanged.',
      2:'Wire harness syntax error before listener startup; corrected sigil assignment spacing.',
      3:'Wire harness if/else case macro grouping error before listener startup; corrected block form.',
      4:'H2 harness sent one fewer body byte than expected; SHA assertion detected the fixture segmentation error; corrected final-part length.',
      5:'Metadata-only observer depended on unrelated earlier requests; H2 slow-gap assertion incorrectly expected rejection although progress within total deadline is allowed; corrected observer and expectation.',
      6:'All tests passed; observer scanned metadata only, so this run is not evidence of received-byte measurements.data exposure.',
      7:'All tests passed; full telemetry observer and command/environment/toolchain/group cleanup provenance added.',
      8:'All tests passed; verifier-call counter initialized/incremented but recorded fields still literals; superseded by measured final record.'}
    attempts=[]
    for p in runs:
        receipt=json.loads((p/'receipt.json').read_text())
        assert receipt['cleanup']['scratchRemoved']
        attempts.append({'run':p.name,'receipt':str((p/'receipt.json').relative_to(HERE)),'receiptSHA256':sha(p/'receipt.json'),'failure':receipt['failure'],'note':notes.get(int(p.name.split('-')[1]),'Final fully pinned replay; measured verifier counts and complete observer.'),'listenerStarted':(p/'wire/listener.json').exists(),'sourceClosure':str((p/'candidate-source-closure.tar.gz').relative_to(HERE))})
    write(HERE/'attempts.json',attempts)
    candidate=HERE/'candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex'
    patch=''.join(difflib.unified_diff([],candidate.read_text().splitlines(True),fromfile='/dev/null',tofile='b/hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'))
    (HERE/'candidate.patch').write_text(patch)
    write(HERE/'acceptance.json',{'schema':1,'status':'candidate-private-capture-scope-awaiting-root-review','observedUTC':datetime.now(timezone.utc).isoformat(),
      'authoritativeRun':latest.name,'acceptedHostedSourceDigest':'eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d',
      'signatureModuleSHA256':'3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6',
      'candidateSHA256':sha(candidate),'profile':1,'componentTests':component,'wireTestGroups':wire,
      'wireClientScenarios':len(clients),'HTTP1Clients':sum(c['transport']=='raw-tcp-http1' for c in clients),'HTTP2h2cClients':sum(c['transport']=='mint-h2c' for c in clients),
      'frameworkPrePlugCases':sum(c['id'] not in by_id for c in clients),'testSuccessHTTPStatus':418,
      'zero2xx':True,'measuredVerifierCallCounts':True,'domainCallScope':'No domain/provider/DB/Oban entry point exists in the isolated harness; zero does not qualify a production endpoint.',
      'freshCandidateCompilation':True,'freshDependencyCompilation':False,'dependencyCache':'All copied dependency source/BEAM/toolchain identities fixed in pinned-dependency-identity.json; five original dependency API BEAM pins rechecked against root selection.',
      'productionClockPolicy':'Production artifact has only capture/1 plus standard metadata exports, no TestClock atom, and ignores conn-private/process test clock spoof; test seam compiled separately.',
      'liveHostedChanged':False,'nativeStarted':False,'publicAdmissionAccepted':False,'g23Accepted':False,
      'pending':['root independent review','endpoint-owned telemetry/logging privacy','hard cancellation and connection/stream disposal','TLS/ALPN/deployed ingress/provider compatibility','server-owned endpoint/account/mode/generation/secrets','durable deduplicated inbox and atomic Oban enqueue','Stripe test-mode reconciliation','usage ledger','G23'],
      'finalizeCommand':['python3','-B','verification/stripe-raw-body-capture/finalize.py'],
      'cleanupAllAttempts':all(json.loads((p/'receipt.json').read_text())['cleanup']['scratchRemoved'] for p in runs)})
    # Include every nested receipt/seal/failure, excluding only this top-level seal.
    entries={}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p!=HERE/'seal.json': entries[str(p.relative_to(REPO))]={'bytes':p.stat().st_size,'sha256':sha(p)}
    doc=REPO/'docs/stripe-raw-body-capture.md'
    if doc.exists(): entries[str(doc.relative_to(REPO))]={'bytes':doc.stat().st_size,'sha256':sha(doc)}
    write(HERE/'seal.json',entries)
    print(f'PASS: {latest.name}; 14 component tests, 13 wire groups, 105 clients; all 13 matrix rows retained; nested producer sealed')
if __name__=='__main__': main()
