import hashlib,json,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent; P=ROOT/'verification/android-environment-observer-lifecycle'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check(p,r):
 if p.is_symlink() or not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Input differs '+str(p))
f=P/'manifest.json'
if sha(f)!='12ff1a93d3ea3bfcbac663745759514a72c9db78e7ef43729f697030dc393060':raise RuntimeError('Manifest changed')
j=json.loads(f.read_bytes());total=0
for name,r in j['files'].items():check(P/name,r);total+=r['bytes']
if len(j['files'])!=946 or total!=7811904:raise RuntimeError('Manifest totals changed')
proposal=json.loads((P/'candidate-proposal.json').read_bytes())
for name,r in proposal['files'].items():check(ROOT/name,r)
freeze=json.loads((P/'host-source-freeze.json').read_bytes())
for name,r in freeze['files'].items():check(ROOT/name,r)
if (ROOT/'docs/android-environment-observer-lifecycle.md').read_bytes()!=(P/'documentation.md').read_bytes():raise RuntimeError('Documentation changed')
receipt=json.loads((P/'receipt.json').read_bytes())
for name,r in receipt['receipts'].items():check(P/name,r)
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__))],'python_version':sys.version,'status':'frozen-implementation-byte-audit-complete-awaiting-independent-harness-freeze','manifest_sha256':sha(f),'members_verified':len(j['files']),'bytes_verified':total,'proposal_current_inputs_verified':len(proposal['files']),'host_current_inputs_verified':len(freeze['files']),'candidate_proposal_sha256':sha(P/'candidate-proposal.json'),'final_receipt_sha256':sha(P/'receipt.json'),'producer_reported_scope':{'host_cases':161,'swift_admission_test_functions':10,'python_admission_tests':9,'app_host_tests':4,'session_host_tests':3,'java_sources':14,'classes':160,'D8_min_api':28,'SDK':'37.0','Swift_Android':'6.3.3','NDK':'r27d'},'scope':'Byte and preserved producer receipt binding audit only; independent behavior/profile/cross evidence review required.','candidate_access_authorized_to_independent_reviewer':False,'next':'Admit separately after independently authored leaves/assertions are frozen','native_runtime_or_capture_authorized':False,'implementation_accepted':False,'GA_qualified':False}
(OUT/'implementation-preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
