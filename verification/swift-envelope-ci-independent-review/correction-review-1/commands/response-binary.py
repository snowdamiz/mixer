#!/usr/bin/env python3
"""Synthetic libtest response fixture; never executes product semantics."""
import json
from pathlib import Path
import sys

ROUND=Path('REPLACED_ROUND')
cfg=json.loads((ROUND/'response-settings.json').read_bytes())
oracle=json.loads((ROUND/'response-oracle.json').read_bytes())
lane='producer' if Path(__file__).name=='producer-tests' else 'independent'
names=list(oracle[lane]);mode=cfg['mode'] if cfg.get('lane','producer')==lane else 'valid'
listing=sys.argv[1:]==['--list']
if not listing and sys.argv[1:]!=['--test-threads=1','--nocapture']:sys.exit(71)
if listing:
    if mode=='list-empty':names=[]
    if mode=='list-missing':names.pop()
    if mode=='list-extra':names.append('independent_unselected_extra')
    if mode=='list-duplicate':names[-1]=names[0]
    if mode=='list-substitute':names[-1]='independent_unselected_substitute'
    for name in names:print(name+': test')
    print(f'\n{len(names)} tests, 0 benchmarks');sys.exit(0)
if mode=='execute-empty':names=[]
if mode=='execute-missing':names.pop()
if mode=='execute-duplicate':names[-1]=names[0]
if mode=='execute-substitute':names[-1]='independent_unselected_substitute'
print(f'running {len(names)} tests')
for i,name in enumerate(names):print('test '+name+' ... '+('ignored' if mode=='execute-ignored' and i==0 else 'FAILED' if mode=='execute-failed' and i==0 else 'ok'))
failed=1 if mode=='execute-failed' else 0;ignored=1 if mode=='execute-ignored' else 0;measured=1 if mode=='execute-measured' else 0;filtered=1 if mode=='execute-filtered' else 0
print(f'\ntest result: ok. {len(names)-failed-ignored} passed; {failed} failed; {ignored} ignored; {measured} measured; {filtered} filtered out; finished in 0.01s')
if lane=='producer':
    values=list(oracle['layouts'])
    if mode=='layout-wrong':values[-1]-=1
    if mode!='layout-missing':print('CORRECTED_ACTUAL_COMPLETE_LAYOUTS='+json.dumps(values))
    if mode=='layout-duplicate':print('CORRECTED_ACTUAL_COMPLETE_LAYOUTS='+json.dumps(values))
    if mode!='comparison-missing':print('ENVELOPE_ORACLE_CASES='+('16171' if mode=='comparison-wrong' else '16170'))
    if mode=='comparison-duplicate':print('ENVELOPE_ORACLE_CASES=16170')
    print('CORRECTED_FINITE_BUDGET_CASES=5544')
