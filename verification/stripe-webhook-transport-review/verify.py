"""Read-only verifier for the frozen independent review; never replays a listener."""
import argparse,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def check(base,manifest):
 for name,v in manifest.items():
  p=base/name
  assert p.is_file() and not p.is_symlink() and sha(p)==(v['sha256'] if isinstance(v,dict) else v),name
  if isinstance(v,dict):assert p.stat().st_size==v['bytes'],name
def main():
 p=argparse.ArgumentParser();p.add_argument('--preseal',action='store_true');args=p.parse_args()
 if not args.preseal:
  manifest=read(HERE/'seal.json')
  actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'seal.json'}|{'docs/stripe-webhook-transport-review.md'}
  assert actual==set(manifest),'review packet file-set changed'
  check(ROOT,manifest)
 receipt=read(HERE/'receipt.json')
 producer=ROOT/'verification/stripe-webhook-transport'
 assert receipt['producerSealSHA256']==sha(producer/'seal.json')=='a36676ab1ab9bf1d0f98077d86d7f375b7c46a18c13cdb4bcd1adb24ce5d430d'
 assert read(HERE/'producer-bindings.json')==read(producer/'seal.json')
 check(ROOT,read(HERE/'producer-bindings.json'))
 candidate='candidate/lib/mixer_hosted/billing/webhook_transport.ex'
 assert sha(HERE/candidate)==receipt['candidateSHA256']=='62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0'
 assert (HERE/candidate).read_bytes()==(producer/candidate).read_bytes()
 attempts=read(HERE/'attempts.json')
 assert len(attempts)==receipt['retainedAttempts']==len(list(HERE.glob('run-*')))==5
 assert [a['run'] for a in attempts if a['failure']]==['run-2','run-3']
 for a in attempts:
  run=HERE/a['run'];r=read(run/'receipt.json');seal=read(run/'seal.json')
  assert set(seal)=={str(p.relative_to(run)) for p in run.rglob('*') if p.is_file() and p!=run/'seal.json'}
  check(run,seal)
  assert r['failure']==a['failure']
  clean=r['cleanup']
  assert clean['scratchRemoved'] and clean['identityMatched'] and clean['ownedProcessGroupsEmpty'] and not clean['openHolders']
  assert clean['lsofExitCode']==1 and not Path(clean['scratch']).exists()
  assert all(p['connectionRefused'] for p in clean['ports'])
  assert not read(run/'owned-process-groups.json')['remaining']
  for c in r['commands']:
   assert sha(run/c['output'])==c['sha256']
   if a['failure'] is None:assert c['exitCode']==0 and not c['timedOut']
  with tarfile.open(run/'source-closure.tar.gz') as archive:
   seen={}
   for m in archive.getmembers():
    path=PurePosixPath(m.name)
    assert m.isfile() and not path.is_absolute() and '..' not in path.parts and m.name not in seen
    seen[m.name]=hashlib.sha256(archive.extractfile(m).read()).hexdigest()
   assert seen==read(run/'source-inputs.json')
  accepted=read(run/'accepted-inputs.json')
  assert len(accepted)==71
  assert hashlib.sha256(json.dumps(accepted,sort_keys=True,separators=(',',':')).encode()).hexdigest()==receipt['acceptedBaselineSourceDigest']=='ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc'
  assert seen[candidate]==receipt['candidateSHA256']
  capture='hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'
  assert seen['inputs/'+capture]==seen['candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex']==accepted[capture]==receipt['unchangedCaptureSHA256']=='a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea'
  dep=read(run/'retained-dependency-closure.json');assert sha(ROOT/dep['path'])==dep['sha256']
  for phase in a['phases']:
   if not phase.startswith('baseline-'):
    assert (run/phase/'compiled/Elixir.MixerHosted.Billing.WebhookTransport.beam').is_file()
 replay=HERE/receipt['acceptedReplayRun'];independent=HERE/receipt['acceptedIndependentRun']
 assert replay.name=='run-1' and independent.name=='run-5'
 assert read(replay/'receipt.json')['failure'] is None and read(independent/'receipt.json')['failure'] is None
 assert read(replay/'baseline-component/component-summary.json')=={'total':14,'failures':0,'excluded':0,'skipped':0}
 for phase in ['baseline-wire','composed-wire']:
  assert read(replay/phase/'wire-summary.json')=={'total':13,'failures':0,'excluded':0,'skipped':0}
  clients=read(replay/phase/'clients.json');events=read(replay/phase/'events.json')
  assert len(clients)==105 and not any(200<=s<=299 for c in clients for s in c['statuses'])
  assert all(e['domainCalls']==0 and e['verifierCalls']==(1 if e['outcome']=='captured' else 0) for e in events)
  assert read(replay/phase/'listener-cleanup.json')['connectRefused']
 counts=read(replay/'composed-wire/verifier-counts.json')
 assert counts['actualReturnTraceCount']==counts['inlineInvocationCount']==27 and counts['rawCallArgumentsSuppressed'] and counts['equal']
 owner=read(replay/'composed-wire/owner-summary.json');assert owner['connections']==owner['permits']==0 and owner['peak']<=16
 for e in read(replay/'composed-wire/logs.json'):assert not e['bodySeen'] and not e['signatureSeen'] and not e['trailerSeen']
 for s in ['RAW_BODY_SENTINEL','RAW_SIG_SENTINEL','RAW_TRAILER_SENTINEL']:assert s not in (replay/'composed-wire.log').read_text()
 adv=read(replay/'adversarial/adversarial.json');assert adv['summary']=={'total':13,'failures':0,'excluded':0,'skipped':0} and adv['actual_verifier_calls']==2
 for r in adv['rows']:
  if r['kind'] in ['stage','deadline']:
   expected=1000 if r['kind']=='stage' else (7000 if r['label']=='outer_response' else 5000)
   assert expected<=r['peer_observed_ms']<=expected+100
   assert all(h['overshoot_ms']<=100 for h in r['history'])
  if r['kind']=='cleanup':assert r['role_down'] and r['owner_down'] and r['guard_supervisor_down'] and r['refused']
 assert any(r['kind']=='logger_privileged_drift' and r['already_delivered_to_collector'] and not r['prevention_claim'] for r in adv['rows'])
 negative=read(replay/'stream-negative/negative.json')
 assert all(negative[k] for k in ['pong','stream_down','connection_alive_after_stream_only_kill','no_response_or_reset_in_200ms','guard_intentionally_absent']) and not negative['composed_profile_qualification']
 result=read(independent/'review-independent/review-independent.json');assert result['summary']=={'total':12,'failures':0,'excluded':0,'skipped':0}
 assert result['actual_verifier_returns']==result['inline_verifier_calls']==8 and result['trace_call_arguments_suppressed']
 assert not result['arbitrary_privileged_sink_prevention_claim'] and not result['os_memory_ceiling_claim']
 assert all(not e['raw'] for e in result['logger_events']) and 'REVIEW_PRIVATE_' not in (independent/'review-independent.log').read_text()
 rows=result['rows'];kinds={k:sum(r['kind']==k for r in rows) for k in {r['kind'] for r in rows}}
 assert {k:kinds[k] for k in ['inventory','cleanup','protocol_rejection','permit_boundary','settings_valid','settings_request_transitions','header_limit','window_request','reset_flood','second_stream','second_stream_race','h2_failure_domain']}=={'inventory':14,'cleanup':14,'protocol_rejection':11,'permit_boundary':6,'settings_valid':3,'settings_request_transitions':1,'header_limit':2,'window_request':3,'reset_flood':2,'second_stream':3,'second_stream_race':2,'h2_failure_domain':3}
 for r in rows:
  if 'peer' in r:assert r['peer']['closed']
  if 'deaths' in r:assert all(x['down'] and x['reason']!=':noproc' for x in r['deaths'])
  if r['kind'] in ['protocol_rejection','header_limit','window_request','reset_flood','h2_failure_domain']:assert r['verifier_delta']==0
  if r['kind']=='cleanup':assert all(r[k] for k in ['role_down','owner_down','guard_supervisor_down','port_refused','filters_retained'])
  if r['kind']=='actual_window_block':assert 7000<=r['total_peer_ms']<=7100 and all(h['overshoot_ms']<=100 for h in r['history']) and len(r['deaths'])==2
  if r['kind']=='permit_boundary' and r['mode'] in ['expired_begin','expired_finish','delayed_finish']:
   assert r.get('independent_kill_won') or (r['result']=='{:error, :deadline}' and r['checked_at_or_after_deadline'])
  if r['kind']=='inventory':
   assert {h['id'] for h in r['logger']}=={'default','ssl_handler','review_collector'}
   assert all(h['filters'][0]['id']=='mixer_private_schema' and 'logger_formatter' in h['formatter'] for h in r['logger'])
   assert len(r['telemetry'])==8 and {h['id'] for h in r['telemetry']}=={'mixer-private-webhook-control'}
   assert r['exporters']==[] and 'Logger.Utils.translator/2' in r['primary'] and 'Logger.Utils.process_level/2' in r['primary']
 assert all(c['original_signature_values']==['REVIEW_PRIVATE_SIGNATURE'] and c['bytes']==len('REVIEW_PRIVATE_BODY') for c in result['captures'])
 original={e['id']:e for e in read(replay/'baseline-wire/events.json')};composed={e['id']:e for e in read(replay/'composed-wire/events.json')}
 compare=read(HERE/'baseline-comparison.json')
 for id in compare['commonSuccessfulCaptureIDs']:assert all(original[id][k]==composed[id][k] for k in ['bodySHA256','bodyBytes','signatureValues'])
 assert len(compare['commonSuccessfulCaptureIDs'])==27 and original['h2-slow-gap']['outcome']=='captured' and 'h2-slow-gap' not in composed
 assert {x['id'] for x in compare['differences']}=={'h1-no-body','h1-slow-gap','h2-slow-gap','h2-late-success'}
 matrix=read(HERE/'matrix.json')['rows'];assert [r['id'] for r in matrix]==[f'P{i:02}' for i in range(1,17)]
 assert {r['id']:r['reviewStatus'] for r in matrix if r['id'] in ['P11','P12','P14','P15','P16']}=={'P11':'sampled-local-only-os-ceiling-pending','P12':'private-discard-scoped-public-policy-pending','P14':'pending-not-run','P15':'pending-not-run','P16':'pending-not-run'}
 assert read(HERE/'findings.json')['scopedCandidateDefects']==[]
 assert not any(receipt[k] for k in ['arbitraryPrivilegedSubscriberPreventionClaim','osMemoryCeilingClaim','physicalDeviceEvidence','nativeStarted','liveProductChanged','trackerChanged','gitActions','providerContacted','databaseChanged','credentialsChanged','catalogInspectorOrAuthorityReviewRetried','publicAdmissionAccepted','gaAccepted'])
 assert receipt['recommendation']=='accept-frozen-private-development-candidate-only'
 # Bind the accepted executed reviewer test to its current copied source, while
 # preserving every earlier failed/successful attempt's own exact source archive.
 accepted_manifest=read(independent/'source-inputs.json')
 for folder in ['candidate','tests']:
  for f in (HERE/folder).rglob('*'):
   if f.is_file():assert accepted_manifest[str(f.relative_to(HERE))]==sha(f)
 assert accepted_manifest['run.py']==sha(HERE/'run.py')
 print(json.dumps({'verified':True,'retainedAttempts':5,'originalReplay':'run-1','independentReview':'run-5','independentGroups':12,'independentVerifierReturns':8,'configuredSinkLeaks':0,'recommendation':receipt['recommendation'],'publicAdmissionAccepted':False,'gaAccepted':False},sort_keys=True))
if __name__=='__main__':main()
