"""Recheck only recorded owned groups and remove only this packet's bytecode."""
from pathlib import Path
import json,os,shutil
ROOT=Path(__file__).resolve().parent
rows=[]
for path in sorted((ROOT/'commands').glob('*/receipt.json')):
    receipt=json.loads(path.read_text())
    checks=[('command',receipt)]
    if 'rustc_version_command' in receipt:checks.append(('compiler-version',receipt['rustc_version_command']))
    for kind,r in checks:
        group=r['owned_process_group']
        assert r['child_reaped'] and r['owned_group_absent']
        try:os.killpg(group,0);absent=False
        except ProcessLookupError:absent=True
        assert absent,group
        rows.append({'receipt':str(path.relative_to(ROOT)),'kind':kind,'owned_process_group':group,
                     'child_reaped':True,'owned_group_absent_at_final_recheck':True})
assert not (ROOT/'owned-work').exists()
for cache in ROOT.rglob('__pycache__'):
    shutil.rmtree(cache)
value={'schema':1,'owned_groups':rows,'all_owned_groups_absent_and_reaped':True,
       'compiler_scratch_removed':True,'packet_bytecode_removed':True,
       'process_inventory_performed':False,'native_instances_started':0,
       'native_device_simulator_emulator_UI_capture_checks':'paused and pending',
       'scope':'Only process groups already recorded as owned in this correction were rechecked. Other project processes/data were not inspected or changed.'}
(ROOT/'cleanup.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print('PASS',len(rows),'recorded owned groups absent/reaped; own compiler scratch and bytecode absent')
