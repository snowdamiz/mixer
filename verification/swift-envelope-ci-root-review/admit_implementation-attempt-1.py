import datetime, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(base, rows):
 total=0
 for r in rows:
  p=base/r['path']
  if not p.is_file() or p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:
   raise RuntimeError('Input differs: '+str(p))
  total+=r['bytes']
 return len(rows),total
packet=ROOT/'verification/swift-envelope-ci-implementation'
p=packet/'seal.json'
if sha(p)!='5c871c7ca9de706b319f14689dc6f8b438b9f0b142ee310bd898efda511eecc1': raise RuntimeError('Seal changed')
s=json.loads(p.read_bytes()); count,total=verify(ROOT,s['members'])
if count!=1027 or total!=215957081: raise RuntimeError('Seal totals differ')
tree=hashlib.sha256(json.dumps(s['members'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
if tree!=s['tree_sha256']: raise RuntimeError('Seal tree differs')
pack=ROOT/'verification/swift-envelope-ci-pack'; manifest=pack/'manifest.json'
if sha(manifest)!='4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a': raise RuntimeError('Pack changed')
m=json.loads(manifest.read_bytes()); pack_count,pack_total=verify(pack,m['members'])
run=packet/'run-4'; r=json.loads((run/'receipt.json').read_bytes()); streams=0
for c in r['commands']:
 if not c['child_returned'] or not c['owned_group_gone'] or c['timed_out']: raise RuntimeError('Child not complete')
 expected=1 if c['name'].startswith('api-negative-') else 0
 if c['exit']!=expected: raise RuntimeError('Unexpected exit '+c['name'])
 for k in ['stdout','stderr']: verify(run,[c[k]]); streams+=1
final=json.loads((packet/'final-receipt.json').read_bytes())
if r['status']!='passed' or r['errors'] or not r['cleanup']['removed']: raise RuntimeError('Final run incomplete')
if final['producer_methods']!=78 or final['independent_methods']!=14 or final['complete_host_layouts']!=32 or final['fresh_candidate_comparisons_against_reused_expected_bytes']!=21714: raise RuntimeError('Final scope differs')
if sha(ROOT/'scripts/ci/check-analyzer-envelope.py')!=final['runner_sha256'] or sha(ROOT/'scripts/ci/tests/test_analyzer_envelope_runner.py')!=final['tests_sha256']: raise RuntimeError('Product differs')
report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__))],'python_version':sys.version,'status':'frozen-implementation-admitted-for-independent-review','implementation_seal_sha256':sha(p),'members_verified':count,'bytes_verified':total,'tree_sha256':tree,'pack_manifest_sha256':sha(manifest),'pack_members_verified':pack_count,'pack_bytes_verified':pack_total,'final_commands_verified':len(r['commands']),'final_streams_verified':streams,'runner_sha256':final['runner_sha256'],'tests_sha256':final['tests_sha256'],'final_host_receipt_sha256':sha(run/'receipt.json'),'producer_reported_scope':{'producer':78,'independent':14,'comparisons':21714,'layouts':32,'API_positive':1,'API_expected_negative':8,'runner_controls_normal':25,'runner_controls_optimized':25},'scope':'Byte verification and recorded producer outcome audit only; independent executable review still required.','independent_candidate_access_and_bounded_execution_authorized':True,'native_runtime_or_capture_authorized':False,'root_acceptance':False,'CI_1_98_1_envelope_qualified':False,'GA_qualified':False}
(OUT/'implementation-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
