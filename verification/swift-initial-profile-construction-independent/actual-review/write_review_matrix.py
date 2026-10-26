#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
PRE=OUT.parent
def main():
 controls=json.loads((PRE/'predeclared-review-matrix.json').read_text())['controls']
 scopes={
  'O1':'Actual occupied existing A cache and consumed B proof; preserved identity/usage/ledger/Files; B cleanup through B only.',
  'O2':'17 drifts including min-hidden29 case, canonical ceilings, literal structural early refusals and no prepare counters.',
  'O3':'Actual cancellation/deadline/foreign proof/foreign WASI/prepare capacity failures return exact original failure and adopted owner.',
  'O4a':'Actual constructed-phase repeat prepartial Some proof and partial combined/cache/work failure None, with original completion Ok.',
  'O4b':'Original repeated/partial failure plus separately displaced real phase authority; exact nested Err survives, after_cleanupNone retained.',
  'O5':'Actual successful cache remains Some on missing construction-authority completion failure; exact replaced ticket restored before cleanup.',
  'O6':'Actual nonce fault tag6; explicit zero slots/pins and B/state refusals; original cache retained/restored for cleanup.',
  'O7':'Actual missing/foreign header/buffer/proof checks retain original runtime result; fixed code3 only invariant without runtime error.',
  'O8a':'Exact preaccess29/67 header/rows with None and common-control WASI; independent64 production physical rows; actual owner cleanup.',
  'O8b':'Actual nonempty/nonzero-offset/readonly/directory File errors retain header and same typed row result; original writer schedules retained.',
  'G1':'Actual source sole fresh guard after prepare/construct/complete/inspect; no operation/admission/callback/reentry/escape after it.',
  'G2':'Actual imported0 acquisition refusal retains initial-looking fields; wrapper occupied route cannot remint guard.',
  'B1':'24 explicit frozen full records, 17 separate drifts, ceilings and exhaustion; no Default in named component tests.',
  'B2':'Actual zero slots/pins unsupported5, entry0/entry>capacity succeed, cache belowB original failure, source0 original adoption failure.',
  'S1':'Every12 cache usage field plus both control current/peak pairs reviewed and exercised; other owner categories allowed.',
  'S2':'Actual per-vector empty and retained-length extra-capacity faults; pin/slot/index/plan state and nonce; complete fixed checks source reviewed.',
  'S3':'Actual authentic ticket-owner and exact category/byte checks; source/metadata sealed owner type unmodified; foreign storage restored and separately cleaned.',
  'S4':'Actual unrelated Cache0 admitted and cleaned separately; positive Cache1 refuses B equality; unrelated State/WASI survive until own cleanup.',
  'L1':'Literal165 production/unit source records and type IDs match root; all165 actual size+align both modes/configs;24 extra types separate.',
  'H1':'Preaccess byte0..255 eight distinct slots, exact512 bytes and all reserved zeros; finite29/67 actual byte comparisons both modes.',
  'H2':'All4096 actual fresh constructor/header/row-refusal/cleanup pairs each config/mode; selected target unreachable overflow/policy branches source-only.',
  'R1':'Exact two-argument guard+File bridge obtains only initial.cache.proof(); forbidden foreign snapshot/callback compiler errors at intended source.',
  'R2':'Four independent actual kernel File cases; metadata/position syscall faults source-only where safely unobtainable, no all-kernel fault claim.',
  'R3':'All17 accepted row methods per unit mode rerun on unchanged source; interrupted/short/zero/error/overreport/32ndcall/late-progress semantics.',
  'A1':'Exact134 originals+6 new files, only explanatory comment/private module delta; exact140 distribution+11 declared host support.',
  'A2':'Actual five inventory source roles,24 complete helper types,12 budget copies and all typed argument/error/return/move places joined in source-review.md.',
  'A3':'Object/heap/I/O/explicit loop joins close under corrected original floors. Root-selected abstract primitive/callsite+requested-I/O unit reconciles row450652288+added521088;451173376 is not an actual all-source/callback/CPU/retry/time/VM bound or release gate.',
  'A4':'Actual original None slots and tail consume-before-refund; healthyzero separate from unit fault331496/one-ticket quarantine; no foreign/double refund.',
  'E1':'149 fresh successful selected/independent commands,44 compiler observations; raw failed harness and audits retained; owned scratch removed, no native/UI/capture/process inventory.'}
 limits={'H2','R2','R3','S3','A3'}
 for c in controls:
  c['candidate_status']='REVIEWED_WITH_EXPLICIT_SCOPE_LIMITS' if c['id'] in limits else 'SCOPED_ACTUAL_SOURCE_AND_EVIDENCE_SATISFIED'
  c['observed_resolution']=scopes[c['id']]
 (OUT/'review-matrix.json').write_text(json.dumps({'schema':1,'preaccess_matrix_sha256':hashlib.sha256((PRE/'predeclared-review-matrix.json').read_bytes()).hexdigest(),'controls':controls,'no_runtime_GA_or_all_defensive_kernel_branch_pass':True,'abstract_same_unit_reconciliation_complete':True,'actual_all_source_callback_CPU_retry_time_VM_bound_qualified':False},indent=2,sort_keys=True)+'\n')
 print('Mapped all29 frozen preaccess controls to scoped actual source/evidence; same abstract action unit reconciled; defensive/kernel and stronger actual-execution limits explicit.')
if __name__=='__main__':main()
