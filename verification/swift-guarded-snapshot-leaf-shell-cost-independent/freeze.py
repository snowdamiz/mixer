#!/usr/bin/env python3
"""Freeze this owned independent review only. Never mutates frozen inputs."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
if (HERE/'seal.json').exists():
    raise SystemExit('review already frozen')
main = json.loads((HERE/'review-results.json').read_bytes())
layout = json.loads((HERE/'layout-review-results.json').read_bytes())
assert main['independent_assertions'] == 5810 and layout['independent_assertions'] == 542
assert main['source_tree_sha256'] == layout['source_tree_sha256'] == '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
for receipt_path in HERE.glob('commands/*/receipt.json'):
    receipt = json.loads(receipt_path.read_bytes())
    for name in ['stdout','stderr']:
        raw = (receipt_path.parent/name).read_bytes()
        assert len(raw) == receipt[name]['bytes'] and sha(raw) == receipt[name]['sha256']
    raw = (receipt_path.parent/'executed-source.py').read_bytes()
    assert len(raw) == receipt['executed_source']['bytes'] and sha(raw) == receipt['executed_source']['sha256']
    for source in receipt.get('own_source_inputs',[]):
        raw = (HERE/source['retained_copy']).read_bytes()
        assert len(raw) == source['bytes'] and sha(raw) == source['sha256']
    assert receipt['direct_child_waited'] and not receipt['compiler'] and not receipt['product_runtime']
rows = []
for p in sorted(HERE.rglob('*')):
    if p.is_file():
        assert not p.is_symlink()
        raw = p.read_bytes()
        rows.append({'path':p.relative_to(HERE).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
seal = {'schema':1,'status':'frozen-independent-finite-interface-and-actual146-sized-layout-substitution-accepted','member_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'members':rows,'source_tree_sha256':main['source_tree_sha256'],'producer_seal_sha256':main['producer_seal_sha256'],'layout_packet_seal_sha256':layout['layout_packet_seal_sha256'],'independent_assertions':6352,'hostile_evaluator_cases':783,'source_actions':639237,'actual146_native_occurrence_bytes':3597716,'constant_source_plus_native_component':4236953,'remaining_unsized_combined_coefficient':4376,'required_positive_cut_terms':33,'complete_component_price':False,'complete_host_quote_or_operational_grant':False,'product_runtime_or_native_OTA_GA':False}
(HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'members':len(rows),'bytes':seal['total_bytes'],'bounded_acceptance':True,'complete_component_price':False,'runtime':False}))
