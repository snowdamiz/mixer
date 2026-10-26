"""Independent final custody/closure seal for execution tooling preparation."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from harness import HERE,ROOT,bounded,sha,write_json

PLAN=ROOT/'docs/swift-cache-state-execution-review-preparation.md'
PRE=HERE.parent/'preaccess'
def load(p): return json.loads(p.read_text())

def main():
 latest=load(HERE/'latest-preparation.json'); attempt=HERE/latest['attempt']
 if latest['status']!='reviewer-tooling-preparation-passed': raise ValueError('preparation controls pending')
 modes=[]
 for name in ['protocol-controls','protocol-controls-optimized']:
  result=json.loads((attempt/(name+'.stdout')).read_text().splitlines()[-1])
  if result['methods']!=9 or result['checks']!=372 or result['stub_executions']!=35 or any(result[k] for k in ['failures','errors','skips','candidate_source_accesses','candidate_Rust_semantic_executions','product_tests']): raise ValueError('unexpected protocol closure')
  modes.append(result)
 if modes[0]!=modes[1]: raise ValueError('normal/optimized mismatch')
 custody=load(HERE/'inputs/custody.json')
 for member in custody['root_receipts_and_API_references']:
  p=HERE/member['snapshot']; b=p.read_bytes()
  if sha(b)!=member['sha256'] or len(b)!=member['bytes']: raise ValueError('input snapshot drift')
  # All four current inputs are authorized immutable receipts/API references.
  if sha((ROOT/member['path']).read_bytes())!=member['sha256']: raise ValueError('authorized upstream drift')
 pre_seal=PRE/'seal.json'
 if sha(pre_seal.read_bytes())!='1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c': raise ValueError('sealed preaccess identity')
 upstream=load(pre_seal)
 for m in upstream['members']:
  b=(ROOT/m['path']).read_bytes()
  if sha(b)!=m['sha256'] or len(b)!=m['bytes']: raise ValueError('sealed preaccess was changed')
 for p in [PLAN]+[p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py','.rs','.md') and p.relative_to(HERE).parts[0] not in ('inputs','commands')]:
  for i,line in enumerate(p.read_text().splitlines(),1):
   if line.rstrip()!=line: raise ValueError(('owned whitespace',str(p),i))
 final_commands=HERE/'final-commands'
 revision=bounded(['git','rev-parse','HEAD'],ROOT,final_commands,'context-revision',seconds=10)
 if revision['exit_code']!=0: raise ValueError('context revision unavailable')
 diff=bounded(['git','diff','--check','--','docs/swift-cache-state-execution-review-preparation.md',str(HERE.relative_to(ROOT))],ROOT,final_commands,'owned-diff-check',seconds=10)
 if diff['exit_code']!=0: raise ValueError('owned diff check')
 sources=[]
 for p in sorted(HERE.rglob('*')):
  if p.is_file() and p.suffix in ('.py','.rs') and p.relative_to(HERE).parts[0] not in ('inputs','commands'):
   b=p.read_bytes(); sources.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
 sources.append({'path':str(PLAN.relative_to(ROOT)),'bytes':PLAN.stat().st_size,'sha256':sha(PLAN.read_bytes())})
 write_json(HERE/'final-source-manifest.json',{'members':sources,'scope':'reviewer tooling and plan only; no producer source'})
 failed=[]
 for p in sorted((HERE/'commands').glob('*/summary.json')):
  summary=load(p)
  if summary['status']!='reviewer-tooling-preparation-passed': failed.append(str(p.relative_to(HERE)))
 write_json(HERE/'final-receipt.json',{
  'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'independent execution tooling preparation sealed; candidate review unrun',
  'command':[sys.executable,'-B',str(HERE/'seal_preparation.py')],'script_sha256':sha(Path(__file__).read_bytes()),
  'model':'gpt-6.1-sol','reasoning_effort':'xhigh','model_switch':False,'spawned_agents':0,
  'context_revision':Path(revision['stdout']).read_text().strip(),
  'root_selection_sha256':'012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3',
  'getter_selection_sha256':'80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1',
  'unchanged_preaccess_seal_sha256':sha(pre_seal.read_bytes()),'unchanged_preaccess_members':173,'unchanged_preaccess_bytes':27268876,
  'tool_identity':load(attempt/'tool-identity.json'),'normal_controls':modes[0],'optimized_controls':modes[1],
  'API_probe_sources':15,'self_owned_stub_API_positive_controls':1,'self_owned_stub_API_negative_controls':14,
  'API_diagnostic_attribution':'exact declared error category and intended primary source span; unrelated failure is not a pass',
  'protocol_stub':'independently authored five-byte control protocol; arbitrary counters/report bytes; no profile parser/cache transitions/old model or ABI claim',
  'authoring_failures_retained':failed,'authoring_correction':'Duplicate synthetic getter-1-0 directory label fixed with unique case index; original outputs/source snapshots preserved.',
  'intentional_tooling_refusals':['owned timeout','owned output cap','driver input alias/missing/directory/argument/output-exists preconditions',
   'API-negative compile controls','malformed JSON/Result/getter protocol'],
  'candidate_source_accessed':False,'candidate_Rust_semantic_executions':0,'actual_public_candidate_File_cases':0,
  'actual_private_candidate_controls':0,'actual_candidate_API_probe_compilations':0,'product_tests':0,
  'private_seams_status':'explicit unimplemented plan; no public injection requested',
  'private_paid_domain_exclusions_runtime_passes':0,
  'pending':['exact root candidate admission','actual candidate source/debit/move/caller/lifetime/cleanup review',
   'actual compiler/layout/API/report/public File execution','separate root-admitted private snapshots/corruption/fault/receipt proofs',
   'real adapters/live VM/target','native/device/compiler/signing/store/customer/operations/immutable FieldLog/GA'],
  'cleanup':'All serial owned children returned; exact created scratch removed after return; hashes retained. No other process or instance touched.',
  'native_capture_UI_simulator_emulator_phone_started_or_queried':False,'process_discovery':False,
  'root_metadata_CI_git_index_commit_push_changed':False,
  'authority_all_false_for_product_claims':True,'implementation_accepted':False,'GA_qualified':False})
 excluded={HERE/'seal.json',HERE/'seal.sha256',HERE/'ready.json'}
 files=[PLAN]+sorted(p for p in HERE.rglob('*') if p.is_file() and p not in excluded)
 members=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files]
 seal={'schema':1,'scope':'independent execution-preparation tooling; candidate unopened',
  'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,
  'tree_sha256':sha(''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in members).encode()),
  'excluded':[str(p.relative_to(ROOT)) for p in sorted(excluded)]}
 write_json(HERE/'seal.json',seal); seal_sha=sha((HERE/'seal.json').read_bytes())
 (HERE/'seal.sha256').write_text(seal_sha+'  seal.json\n')
 ready={'schema':1,'status':'execution-preparation-ready-for-root-custody-review',
  'seal':str((HERE/'seal.json').relative_to(ROOT)),'seal_sha256':seal_sha,
  'members':seal['member_count'],'bytes':seal['member_bytes'],'tree_sha256':seal['tree_sha256'],
  'plan_sha256':sha(PLAN.read_bytes()),'reviewer_protocol_methods_per_mode':9,'reviewer_protocol_checks_per_mode':372,
  'self_owned_stub_executions_per_mode':35,'self_owned_stub_API_negative_controls':14,'self_owned_stub_API_positive_controls':1,
  'tooling_compiler':'Rust1.99.0 b940084d7 Apple arm; self-owned protocol scope only',
  'candidate_source_accessed':False,'candidate_Rust_semantic_executions':0,'product_tests':0,
  'actual_public_File_candidate_cases':0,'actual_private_candidate_controls':0,
  'sealed_preaccess_unchanged':True,'private_source_fault_budget_receipt_seams':'unimplemented separate-admission plan',
  'later_candidate_execution':'requires a separately hash-bound root-owned admission and new review output closure',
  'GA_qualified':False}
 write_json(HERE/'ready.json',ready)
 for m in members:
  b=(ROOT/m['path']).read_bytes()
  if sha(b)!=m['sha256'] or len(b)!=m['bytes']: raise ValueError('new seal member changed')
 print(json.dumps(ready))

if __name__=='__main__': main()
