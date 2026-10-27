#!/usr/bin/env python3
"""Seal this bounded proposal only. No Git, compiler, product or native calls."""
from pathlib import Path
import hashlib
import json
import platform
import sys

here = Path(__file__).resolve().parent
def sha(data):
    return hashlib.sha256(data).hexdigest()
members = []
for path in sorted(here.rglob('*')):
    if path.is_file() and path != here/'seal.json':
        assert '__pycache__' not in path.parts
        data = path.read_bytes()
        members.append({'path':path.relative_to(here).as_posix(),'bytes':len(data),'sha256':sha(data)})
summary = json.loads((here/'summary.json').read_text())
labels = [('checked_components_v1','Checked six-part quote'),('selected_whole_quote_v1','Pending selected quote'),
          ('selected_parent_account_v1','Pending selected account'),('from_preexisting_root_v1','Account from pre-existing root'),
          ('usage_v1','Usage, per `U`'),('reserve_whole_v1','Reserve whole quote'),('dispatch_v1','Dispatch carrier'),
          ('inspect_v1','Inspection, per `I`'),('destroy_owned_v1','Explicit owned destruction'),
          ('drop','Ordinary wrapper Drop'),('release_destroyed_v1','Destroyed token release'),
          ('run_one_fixture_v1','Typed one-fixture entry'),('fixture_dispatch_closure','Exact dispatch closure'),
          ('destroy_returned_fixture_v1','Typed destroy adapter'),('release_after_retirement_v1','Typed release adapter')]
documentation = (here/'README.md').read_text()
for name,label in labels:
    values = summary['tables'][name]
    expected = '| '+label+' | '+' | '.join(f'{values[key]:,}' for key in
        ['source_action_units_per_invocation','native_sized_occurrence_bytes_per_invocation','combined_surface_units_per_invocation'])+' |'
    assert expected in documentation, 'README dimension table mismatch: '+name
for directory in ('command','check-command'):
    receipt = json.loads((here/directory/'receipt.json').read_text())
    assert receipt['exit_code'] == 0 and receipt['driver_unchanged']
    assert receipt['driver_sha256'] == sha((here/'derive.py').read_bytes())
    assert receipt['source_tree_sha256'] == summary['source_binding']['sha256']
    for name in ('stdout','stderr'):
        data = (here/directory/name).read_bytes()
        assert len(data) == receipt[name+'_bytes'] and sha(data) == receipt[name+'_sha256']
    assert json.loads((here/directory/'stdout').read_text())['passed'] is True
    assert (here/directory/'stderr').stat().st_size == 0
seal = {'schema':1,'status':'sealed-private-P0-source-surface-proposal-pending-independent-review',
        'source_tree_sha256':summary['source_binding']['sha256'],'source_members':145,
        'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,
        'fixed_surface_units':summary['fixed_combined_surface_units'],
        'seal_command':[sys.executable,str(here/'freeze.py')],'Python_version':platform.python_version(),
        'README_dimension_rows_verified':len(labels),
        'successful_command_receipts_verified':2,
        'complete_P0_allocation_or_host_quote':False,'selected_policy_or_operational_grant':False,
        'native_OTA_FieldLog_GA_authority':False}
if '--check-only' in sys.argv:
    assert json.loads((here/'seal.json').read_text()) == seal
    print(json.dumps({'passed':True,'members':len(members),'bytes':seal['member_bytes'],
                      'seal_sha256':sha((here/'seal.json').read_bytes())}))
else:
    assert not (here/'seal.json').exists(), 'already sealed; do not overwrite'
    (here/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'sealed':True,'members':len(members),'bytes':seal['member_bytes'],
                      'seal_sha256':sha((here/'seal.json').read_bytes())}))
