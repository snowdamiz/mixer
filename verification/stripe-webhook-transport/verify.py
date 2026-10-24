"""Read-only sealed candidate verifier. Historical failed runs remain failures."""
import argparse,difflib,hashlib,json
from pathlib import Path,PurePosixPath
import tarfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def check_manifest(base,manifest):
 for name,v in manifest.items():
  p=base/name
  digest=v['sha256'] if isinstance(v,dict) else v
  assert p.is_file() and not p.is_symlink() and sha(p)==digest,name
  if isinstance(v,dict):assert p.stat().st_size==v['bytes'],name

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--preseal',action='store_true');args=parser.parse_args()
 if not args.preseal:
  seal=read(HERE/'seal.json')
  actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'seal.json'}|{'docs/stripe-webhook-transport-implementation.md'}
  assert actual==set(seal),'top file-set changed'
  check_manifest(ROOT,seal)
 packet=read(HERE/'receipt.json');chosen=HERE/packet['acceptedRun']
 attempts=read(HERE/'attempts.json')
 assert len(attempts)==len(list(HERE.glob('run-*')))
 for attempt in attempts:
  run=HERE/attempt['run'];seal=read(run/'seal.json')
  actual={str(p.relative_to(run)) for p in run.rglob('*') if p.is_file() and p!=run/'seal.json'}
  assert actual==set(seal),run
  check_manifest(run,seal)
  receipt=read(run/'receipt.json')
  assert receipt['failure']==attempt['failure']
  assert receipt['cleanup']['scratchRemoved'] and receipt['cleanup']['ownedProcessGroupsEmpty'] and not receipt['cleanup']['openHolders']
  assert not Path(receipt['cleanup']['scratch']).exists()
  assert all(v['connectionRefused'] for v in receipt['cleanup']['ports'])
  for c in receipt['commands']:
   assert sha(run/c['output'])==c['sha256']
   if not receipt['failure']:assert c['exitCode']==0 and not c['timedOut']
  with tarfile.open(run/'source-closure.tar.gz') as archive:
   observed={}
   for member in archive.getmembers():
    name=PurePosixPath(member.name)
    assert member.isfile() and not name.is_absolute() and '..' not in name.parts and member.name not in observed
    observed[member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
   assert observed==read(run/'source-inputs.json'),run
  dep=read(run/'retained-dependency-closure.json')
  assert sha(ROOT/dep['path'])==dep['sha256']
 assert read(chosen/'receipt.json')['failure'] is None
 manifest=read(chosen/'source-inputs.json')
 accepted=read(chosen/'accepted-inputs.json')
 assert len(accepted)==71
 assert hashlib.sha256(json.dumps(accepted,sort_keys=True,separators=(',',':')).encode()).hexdigest()=='ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc'
 capture='hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'
 assert manifest['inputs/'+capture]==accepted[capture]=='a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea'
 assert manifest['candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex']==accepted[capture]
 for folder in ['candidate','tests']:
  for p in (HERE/folder).rglob('*'):
   if p.is_file():assert manifest[str(p.relative_to(HERE))]==sha(p),str(p)
 assert manifest['run.py']==sha(HERE/'run.py')
 assert read(chosen/'baseline-component/component-summary.json')=={'total':14,'failures':0,'excluded':0,'skipped':0}
 for folder in ['baseline-wire','composed-wire']:
  assert read(chosen/folder/'wire-summary.json')=={'total':13,'failures':0,'excluded':0,'skipped':0}
  clients=read(chosen/folder/'clients.json');events=read(chosen/folder/'events.json')
  assert len(clients)==105 and all(not any(200<=s<=299 for s in c['statuses']) for c in clients)
  assert all(e['verifierCalls']==(1 if e['outcome']=='captured' else 0) and e['domainCalls']==0 for e in events)
  assert read(chosen/folder/'listener-cleanup.json')['connectRefused']
 counts=read(chosen/'composed-wire/verifier-counts.json')
 assert counts['actualReturnTraceCount']==counts['inlineInvocationCount']==27 and counts['rawCallArgumentsSuppressed'] and counts['equal']
 owners=read(chosen/'composed-wire/owner-summary.json')
 assert owners['connections']==owners['permits']==0 and owners['peak']<=16
 log=read(chosen/'composed-wire/logs.json')
 assert log and not any(v['bodySeen'] or v['signatureSeen'] or v['trailerSeen'] for v in log)
 stdout=(chosen/'composed-wire.log').read_text()
 for sentinel in ['RAW_BODY_SENTINEL','RAW_SIG_SENTINEL','RAW_TRAILER_SENTINEL']:assert sentinel not in stdout
 adversarial=read(chosen/'adversarial/adversarial.json')
 assert adversarial['summary']=={'total':13,'failures':0,'excluded':0,'skipped':0}
 assert adversarial['actual_verifier_calls']==2
 rows=adversarial['rows']
 assert all(v['refused'] and v['role_down'] and v['owner_down'] and v['guard_supervisor_down'] for v in rows if v['kind']=='cleanup')
 for v in rows:
  if v['kind'] in ['stage','deadline']:
   assert all(h['overshoot_ms']<=100 for h in v['history'])
   expected=1000 if v['kind']=='stage' else (7000 if v['label']=='outer_response' else 5000)
   assert expected<=v['peer_observed_ms']<=expected+100
 assert {v['label'] for v in rows if v['kind']=='stage'}=={'h1_headers','h2_preface','h2_continuation'}
 assert any(v['kind']=='actual_max_h2' and v['body_bytes']==1_048_576 and v['captured'] for v in rows)
 assert any(v['kind']=='header_compression' and v['encoded_bytes']<16_384<v['value_bytes'] for v in rows)
 assert any(v['kind']=='logger_privileged_drift' and v['already_delivered_to_collector'] and not v['prevention_claim'] for v in rows)
 assert not adversarial['hard_memory_ceiling']
 inventories=[v for v in rows if v['kind']=='inventory']
 assert inventories
 for inventory in inventories:
  assert {h['id'] for h in inventory['logger']}=={'default','ssl_handler','mixer_private_collector'}
  assert all('mixer_private_schema' in h['filters'] and h['formatter']=='logger_formatter' for h in inventory['logger'])
  assert {h['id'] for h in inventory['telemetry']}=={'mixer-private-webhook-control'}
 negative=read(chosen/'stream-negative/negative.json')
 assert negative['pong'] and negative['stream_down'] and negative['connection_alive_after_stream_only_kill'] and negative['no_response_or_reset_in_200ms'] and negative['guard_intentionally_absent'] and not negative['composed_profile_qualification']
 matrix=read(HERE/'matrix.json')
 assert [r['id'] for r in matrix['rows']]==[f'P{i:02}' for i in range(1,17)]
 assert len(read(HERE/'capture-matrix.json')['rows'])==13
 assert not packet['publicAdmissionAccepted'] and not packet['gaAccepted'] and not packet['liveIntegrated']
 source=HERE/'candidate/lib/mixer_hosted/billing/webhook_transport.ex'
 expected=''.join(difflib.unified_diff([],source.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/hosted/lib/mixer_hosted/billing/webhook_transport.ex'))
 assert (HERE/'candidate.patch').read_text()==expected
 print(json.dumps({'verified':True,'acceptedRun':chosen.name,'retainedAttempts':len(attempts),'baselineComponent':14,'baselineWireGroups':13,'composedWireGroups':13,'adversarial':13,'composedClients':105,'actualComposedVerifierCalls':27,'matrixRows':16,'captureRows':13,'publicAdmissionAccepted':False,'gaAccepted':False},sort_keys=True))
if __name__=='__main__':main()
