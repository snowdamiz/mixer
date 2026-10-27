"""Source/call/phase invariants independent of conditional arithmetic inputs."""
from collections import Counter
import evaluator

def validate(ledger,contract):
 for key,n in ledger['nodes'].items():
  evaluator.flatten(ledger,key)
  if n['kind']=='MIR-all-written-block-upper':
   calls=Counter();payload=Counter();primitive=Counter();own=0
   for o in n['operations']:
    w=o['weight'];own+=w*o['source']
    for edge in o['edges']:
     if edge['kind']=='call':calls[edge['target']]+=w
     elif edge['kind']=='payload':payload[edge['target']]+=w
     else:primitive[edge['target']]+=w;own+=w
   # Pure/tuple adapter normalization is explicit and checked separately.
   if dict(calls)!=n['calls'] or dict(primitive)!=n['primitive']:raise ValueError('callsite/callback multiplicity mismatch '+key)
   if own>n['own']:raise ValueError('source operation omitted '+key)
 for name,count,bound in [('cache_cleanup',2,64),('wasi_pair',2,4)]:
  n=ledger['nodes'][name]
  if len(n['loops'])!=count:raise ValueError('loop closure omitted '+name)
  for loop in n['loops']:
   if loop['max_iterations']!=bound or loop['block_visits_upper']!=bound+1:raise ValueError('wrong source-specific finite loop cap')
   for op in n['operations']:
    if op['block'] in loop['blocks'] and op['weight']!=bound+1:raise ValueError('loop operation underpriced')
 core=ledger['core_phase_binding'];store=core['counter_store'];before=ledger['nodes']['core_callback_before'];after=ledger['nodes']['core_fixed_store_and_after']
 if any(o['code']==store['code'] for o in before['operations']) or sum(o['code']==store['code'] for o in after['operations'])!=1:raise ValueError('counter-store phase cut')
 if 'accepted::check_budget' not in before['calls'] or before['calls'].get('accepted::check')!=1:raise ValueError('pre-store checks omitted')
 if 'accepted::admit' in before['calls'] or after['calls'].get('accepted::admit')!=5:raise ValueError('admission moved across fixed-store cut')
 if ledger['nodes']['drop_proof']['calls'].get('accepted::refund_with_wasi')!=2:raise ValueError('proof refund pair undercounted')
 selected=ledger['source_bindings']['policy_retire']['source']
 if 'source.and(metadata)' not in selected or selected.count('control.refund(ticket)')!=2 or 'impl ClosedAdoptionV1 for Original' in selected:raise ValueError('concrete selected retirement body')
 if ledger['nodes']['accepted::wasi_cleanup']['calls'].get('accepted::drop_reserved_with_wasi')!=5:raise ValueError('four buffers plus header not funded')
 constructor=ledger['constructor_applicability']
 if constructor['product451814442_transferred'] or 'Err(AError::WorkAuditPending)' not in constructor['unconditional_refusal_body'] or constructor['writer_encoder_initializer_entered']:raise ValueError('constructor phase applicability')
 uses=[(k,n['calls']['accepted_constructor_region']) for k,n in ledger['nodes'].items() if 'accepted_constructor_region' in n['calls']]
 if uses!=[('construct_owned',1)] or ledger['nodes']['accepted_constructor_region']['own']==451814442:raise ValueError('aggregate transferred to unrelated callers')
 if ledger['nodes']['accepted_constructor_region']['payload'].get('payload::Partial')!=5:raise ValueError('constructor partial destruction omitted')
 if set(contract['exports'])!=set(ledger['exports']):raise ValueError('lost concrete leaf cut')
 return True
