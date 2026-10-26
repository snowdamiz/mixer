from pathlib import Path
import json
p=Path('verification/android-private-owner-independent-review/preaccess/inputs/verification/android-private-owner-effect-roster-amendment/required-host-roster.json');r=json.loads(p.read_text())
for k in ['early_virtual_constructor_entries','mandatory_callback_regions','mandatory_nonbarrier_controls']:print(k,json.dumps(r[k],indent=2))
for k,v in r['closures'].items():print(k,'actual',len(v['actual_production_sources']),'substitutes',len(v['substitutes']))
m=json.loads((p.parent/'manifest.json').read_text())
print('manifest roster record', next(x for x in m['files'] if x.get('path')=='required-host-roster.json'))
print('multi-call baseline lines')
d={}
for x in r['baseline_callback_barriers']+r['v1_compile_baseline_only']:d.setdefault((x['source'],x['line']),[]).append(x['id'])
for k,v in d.items():
 if len(v)>1:print(k,v)
