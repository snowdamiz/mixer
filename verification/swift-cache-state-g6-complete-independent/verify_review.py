#!/usr/bin/env python3
"""Read-only independent-packet verification. No product/producer imports."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text())

preseal = sys.argv[1:] == ['--preseal']
if not preseal:
    seal = read(HERE/'seal.json')
    assert seal['source_sha256'] == '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
    for row in seal['members']:
        p = ROOT/row['path']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], row['path']
    assert seal['member_count'] == len(seal['members'])
    assert seal['member_bytes'] == sum(row['bytes'] for row in seal['members'])

result = read(HERE/'results.json')
correction = read(HERE/'receiver-correction.json')
custody = read(HERE/'custody.json')
assert len(correction['complete_receiver_rows']) == 6
assert sum(row['scalar_units'] for row in correction['complete_receiver_rows']) - len(correction['frozen_receiver_rows_replaced']) == 4
assert correction['corrected_template_scalars'] == 43
assert result['paths_compared_to_independent_source_recipes'] == 73
assert result['receiver_corrected_production']['groups'] == 512
assert result['receiver_corrected_all_paths']['groups'] == 514
for row in result['paths']:
    for key in ('frozen','receiver_corrected'):
        cost = row[key]
        assert cost['scalar_blocks'] == (cost['scalars']+15)//16
        assert cost['groups'] == cost['scalar_blocks']+cost['copies'] <= 640
    assert row['receiver_corrected']['scalars'] - row['frozen']['scalars'] == 4*len(row['affected_source_lines'])
    assert row['receiver_corrected']['copies'] == row['frozen']['copies']
for item in result['verified_custody']:
    seal_path = ROOT/item['seal']['path']
    assert sha(seal_path) == item['seal']['sha256']
    bound = read(seal_path)
    assert len(bound['members']) == item['member_count']
    for row in bound['members']:
        p = ROOT/row['path']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
for key in ('source','binding_prerequisite','selected_amendment','selection'):
    row = custody[key]
    assert sha(ROOT/row['path']) == row['sha256']
assert result['producer_module_imports_or_executions'] == 0
assert result['runtime_compiler_native_capture_process_inventory_executions'] == 0
print(json.dumps({'status':'verified independent source-only audit packet',
                  'source_sha256':result['source_sha256'],
                  'independent_source_recipes':73,
                  'required_correction_scalars_per_within':4,
                  'corrected_production_groups':512,
                  'corrected_private_groups':514,
                  'unchanged_G6_cap':640,
                  'root_addendum_selection_required':True,
                  'implementation_or_lifetime_acceptance':False,
                  'producer_frozen_packet_mutation':False,
                  'product_compiler_runtime_native_UI_capture_process_executions':0},indent=2))
