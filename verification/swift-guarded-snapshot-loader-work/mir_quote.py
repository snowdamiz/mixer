"""Checked pure quote for exact descriptor145 source-bound loader component."""
import json
from pathlib import Path
from quote import Geometry,CAPS,Refused,natural,add,mul,ceil_blocks
D=Path(__file__).resolve().parent

def evaluate(geometry,ledger=None):
 g=geometry.checked()
 if ledger is None:ledger=json.loads((D/'mir-ledger.json').read_text())
 if ledger.get('schema')!=1:raise Refused('ledger-schema')
 variables=dict(source=g.source,validator_source=g.validator_source,
  maximum_file=max(g.source,g.executable,g.build,g.session),
  allocation_cap=max(g.metadata,g.scratch),retained_visits=add(ceil_blocks(max(g.source,g.executable,g.build,g.session)),1),read_buffer=4096)
 nodes=ledger['nodes'];validator=ledger['roots']['validator'];cache={};seen=set()
 def expand(n,mode,stack=()):
  if n not in nodes:raise Refused('unknown-callee')
  if n in stack:raise Refused('unclassified-cycle')
  # The real loader contains exactly one validator call. Host original validator
  # is priced separately, never implicitly counted as a one-action std call.
  if mode=='wrapper' and n==validator:return 0
  key=(n,mode)
  if key in cache:return cache[key]
  row=nodes[n];seen.add(n)
  required={'owner','mir_sha256','local_actions','parts','calls','standard_calls','callback_bound','repeat','native'}
  if set(row)-required-{'validator_fixed_repeat'} or required-set(row):raise Refused('row-schema')
  if row['local_actions']!=add(2,*row['parts'].values()):raise Refused('local-omission')
  out=natural(row['local_actions'])
  for term in row['native']:
   e=variables[term['extent']] if isinstance(term['extent'],str) else term['extent']
   out=add(out,mul(term['count'],e))
  for call in row['calls']:
   out=add(out,mul(call['multiplicity'],expand(call['callee'],mode,stack+(n,))))
  repeat=row['repeat'] if mode=='wrapper' else row.get('validator_fixed_repeat',1)
  if isinstance(repeat,str):repeat=variables[repeat]
  out=mul(repeat,out);cache[key]=out;return out
 wrapper=expand(ledger['roots']['loader'],'wrapper')
 sweep=expand(validator,'validator')
 converted=mul(add(g.credits,1),sweep)
 return dict(schema=1,component='P1LoaderV1',status='source-bound-finite-MIR-proposal-needs-independent-review-and-final-fixture-rebinding',
  W_loader=add(wrapper,converted),wrapper_logical_actions=wrapper,validator_original_credits=g.credits,
  validator_acyclic_expanded_ceiling=sweep,validator_host_logical_actions=converted,
  geometry=g.__dict__,source_tree_sha256=ledger['source_tree_sha256'],parent_mir_sha256=ledger['parent_mir_sha256'],
  priced_nodes_visited=len(seen),operational_grant=False,actual_genuine_fixture_bound=False,
  excluded=['P0 trusted parent/account/custody and quote evaluation','P1 caller File setup/path argument acquisition before loader','P2 carrier conversion and remaining seven leaf arguments','P3 ingress/pre-store shell','P4 shared route/VM/cache/scope/construct/writer','P5 caller reporting/outcome custody and teardown of returned File owners','standard private implementations/retries/allocator/kernel/CPU/RSS/latency'])
if __name__=='__main__':
 import sys
 if len(sys.argv)!=2:raise SystemExit('explicit geometry JSON path required')
 print(json.dumps(evaluate(Geometry(**json.loads(Path(sys.argv[1]).read_text()))),sort_keys=True,indent=2))
