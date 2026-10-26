"""Seal only the reviewer-owned preaccess packet and its plan, then readiness."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PLAN=ROOT/'docs/swift-cache-state-implementation-review-plan.md'
REVIEW=HERE.parent
def digest(b): return hashlib.sha256(b).hexdigest()
def put(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def load(p): return json.loads(p.read_text())

def main():
 latest=load(HERE/'latest-controls.json'); attempt=HERE/latest['attempt']
 normal=json.loads((attempt/'normal.stdout').read_text().splitlines()[-1])
 optimized=json.loads((attempt/'optimized.stdout').read_text().splitlines()[-1])
 encoded=json.loads((attempt/'fixture-encoding.stdout').read_text().splitlines()[-1])
 if any(r['exit_code']!=0 or r['timed_out'] for r in latest['results']): raise ValueError('latest controls not passed')
 if normal!=optimized or normal['methods']!=14 or normal['checks']!=29006: raise ValueError('unexpected final check closure')
 tooling=[]
 for name,argv in [('git-version',['git','--version']),('git-context-revision',['git','rev-parse','HEAD']),
  ('owned-diff-check',['git','diff','--check','--','docs/swift-cache-state-implementation-review-plan.md',str(HERE.relative_to(ROOT))])]:
  r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=10,check=False)
  if r.returncode: raise ValueError((name,r.stderr.decode()))
  tooling.append({'name':name,'argv':argv,'cwd':str(ROOT),'exit_code':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()})
 put(HERE/'tooling.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
  'machine':platform.machine(),'commands':tooling,'new_Rust_compiler_invoked':False})
 for p in [PLAN]+[p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py','.md') and 'inputs' not in p.relative_to(HERE).parts]:
  for i,line in enumerate(p.read_text().splitlines(),1):
   if line.rstrip()!=line: raise ValueError(('trailing whitespace',str(p),i))
 failures=[]
 for summary in sorted((HERE/'commands').glob('*/summary.json')):
  s=load(summary)
  if s['status']!='reviewer-controls-passed': failures.append({'path':str(summary.relative_to(HERE)),'results':s['results']})
 put(HERE/'authoring-failures.json',{'retained_failed_attempts':failures,
  'corrections':['Own Python exception variable cleared a same-named envelope local; renamed the local.',
   'Own happy-path release fixture incorrectly claimed post-count0 after two pins; corrected to the exact post-count1.'],
  'scope':'reviewer test-support authoring failures, not product/Rust failures; raw stdout/stderr and source hashes retained',
  'final_result':'14 methods and29006 checks per mode passed'})
 sources=[PLAN]+sorted(HERE.glob('*.py'))
 source_manifest=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sources]
 put(HERE/'source-manifest.json',{'members':source_manifest,
  'tree_sha256':digest(''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in source_manifest).encode()),
  'scope':'independently authored reviewer support and plan; no producer source'})
 put(HERE/'cleanup.json',{'all_owned_command_children_returned':True,'parallel_children':0,'timeouts_in_latest_run':0,
  'native_or_capture_or_UI_processes_started_or_queried':False,'process_discovery':False,'scratch_compilers_started':0,
  'disposable_native_instances_started':0,'other_projects_touched':False,'removed_paths':[],
  'retained':'all raw evidence and fixtures; -B prevented owned bytecode scratch'})
 put(HERE/'final-receipt.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),
  'status':'independent implementation preaccess fixture/proof preparation complete; no implementation acceptance',
  'selected_agent_model':'gpt-6.1-sol','reasoning_effort':'xhigh','fresh_context':True,'spawned_agents':0,
  'preaccess_start_context_revision':'0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c',
  'closing_context_revision':tooling[1]['stdout'].strip(),
  'root_accepted_contract_sha256':'aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc',
  'upstream_verified':{'packets':6,'members':651,'bytes':4801337},'encoded_fixture_counts':encoded,
  'sequence_variants':len(load(HERE/'fixtures/sequence-variants.json')),
  'private_semantic_witnesses':len(load(HERE/'fixtures/private-semantic-witnesses.json')),
  'control_evidence':{'normal':normal,'optimized':optimized,'attempt':latest['attempt']},
  'actual_public_File_semantic_executions':0,'actual_private_candidate_controls':0,
  'Rust_product_tests_run':0,'new_producer_source_accessed':False,'consulted_old_code_imported_compiled_or_executed':False,
  'three_partial_paid_exclusions':'contract-domain exclusions only; zero runtime passes; actual constructor/return proof pending',
  'predicate_order_limitation':'Accepted contract fixes named single-defect reasons but not overlapping predicate order. Explicit allowed sets in private-controls.json; actual deterministic source ordering requires explanation and independent review.',
  'state_expectation_scope':'Complete contract logical scalars and row defaults/overrides; inactive private storage remains unspecified and must be guarded. Actual scalar-index mapping, non-owned bytes and private snapshot instrumentation pending.',
  'provisional_bounds_proved_by_Rust':False,'root_selection_of_producer':'after this preaccess seal; separate immutable candidate admission required',
  'old_CI_scope':'Root reported exact old envelope Rust1.98.1 / Engine40273904826 passed42steps; no new semantic qualification',
  'pending':['actual new Rust implementation and private loan provenance','every35 actual-source proof obligation',
   'exact debit/moves/lifetimes/cleanup/source ledger','fresh layouts/API/report/old-envelope regressions',
   'independent public actual-File execution and separate private fault controls','real adapters/source/custody/live VM/target',
   'native/device/compiler/signing/store/customer/operations/published FieldLog/GA'],
  'storedPrefixValidated':False,'fullReplayAccepted':False,'semanticMetricsValid':False,'realBindingVerified':False,
  'native_runtime_or_capture_started':False,'GA_qualified':False})
 exclude={HERE/'seal.json',HERE/'seal.sha256'}
 paths=[PLAN]+sorted(p for p in HERE.rglob('*') if p.is_file() and p not in exclude)
 members=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths]
 seal={'schema':1,'scope':'independent cache-state implementation preaccess; no producer Rust',
  'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members),'members':members,
  'tree_sha256':digest(''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in members).encode()),
  'excluded':[str(x.relative_to(ROOT)) for x in sorted(exclude)]+[str((REVIEW/'preaccess-ready.json').relative_to(ROOT))]}
 put(HERE/'seal.json',seal); seal_sha=digest((HERE/'seal.json').read_bytes())
 (HERE/'seal.sha256').write_text(seal_sha+'  seal.json\n')
 ready={'schema':1,'status':'sealed-preaccess-ready-for-root-custody-check',
  'seal':str((HERE/'seal.json').relative_to(ROOT)),'seal_sha256':seal_sha,
  'members':seal['member_count'],'bytes':seal['member_bytes'],'tree_sha256':seal['tree_sha256'],
  'plan_sha256':digest(PLAN.read_bytes()),'normal_methods':14,'optimized_methods':14,'checks_per_mode':29006,
  'actual_public_File_execution_tests':0,'Rust_product_tests':0,'new_producer_source_accessed':False,
  'paid_domain_exclusions_runtime_passes':0,'implementation_bounds_status':'pending actual source/debit/move/lifetime/layout/cleanup review',
  'predicate_overlap_order_status':'actual source design choice; explicit legitimate reason sets, absorbing refusal and full nonmutation required',
  'source_closure':'only immutable accepted data and reviewer-owned support; future producer source separately admitted',
  'authority_all_false':True,'GA_qualified':False}
 put(REVIEW/'preaccess-ready.json',ready)
 # Verify the complete newly written closure from disk before reporting ready.
 for m in members:
  b=(ROOT/m['path']).read_bytes()
  if len(b)!=m['bytes'] or digest(b)!=m['sha256']: raise ValueError('new seal member drift')
 print(json.dumps(ready))

if __name__=='__main__': main()
