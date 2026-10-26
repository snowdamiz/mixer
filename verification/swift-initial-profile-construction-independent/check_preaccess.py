#!/usr/bin/env python3
"""Audit only this preaccess packet and frozen baseline inputs."""
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(m,base):
 p=base/m['path'];assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256'],m['path']
def main():
 custody=json.loads((OUT/'input-custody.json').read_text())
 for m in custody['copied_inputs']:check(m,OUT)
 assert [s['members'] for s in custody['seals']]==[210,19,481]
 base=json.loads((OUT/'old-base-source-manifest.json').read_text())
 expected=json.loads((OUT/'inputs/base-source-manifest.json').read_text())
 assert base['members']==expected['members'] and base['member_count']==134
 probe=json.loads((OUT/'old-probe-source-manifest.json').read_text())
 for m in probe['members']:check(m,OUT/'old-source/vm')
 assert probe['member_count']==136
 original={m['path']:m for m in base['members']};current={m['path']:m for m in probe['members']}
 assert set(current)-set(original)=={'src/bin/independent-preaccess.rs','src/experimental_swift_reactor/cache/independent_preaccess_controls.rs'}
 changed={p for p,m in original.items() if current[p]!=m}
 assert changed=={'src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/mod.rs','src/lib.rs'}
 for p in changed:
  actual=(OUT/'old-source/vm'/p).read_bytes();n=original[p]['bytes']
  assert hashlib.sha256(actual[:n]).hexdigest()==original[p]['sha256']
 assert (OUT/'old_source_controls.rs').read_bytes()==(OUT/'old-source/vm/src/experimental_swift_reactor/cache/independent_preaccess_controls.rs').read_bytes()
 expectations=json.loads((OUT/'fixtures/expected.json').read_text())
 for f in expectations['expectations']:
  for suffix,key,n in [('wasm','wasm_sha256',f['fixture_bytes']),('header.bin','header_sha256',512),('rows.bin','row_body_sha256',2560000)]:
   p=OUT/'fixtures'/f"{f['id']}.{suffix}";assert p.stat().st_size==n and sha(p)==f[key]
  header=(OUT/'fixtures'/f"{f['id']}.header.bin").read_bytes()
  assert header[:8]==b'MIXPRF01' and header[104:128]==bytes(24) and header[128:384]==bytes(range(256)) and header[384:]==bytes(128)
  assert int.from_bytes(header[80:88],'little')==f['B']
  body=(OUT/'fixtures'/f"{f['id']}.rows.bin").read_bytes();wasm=(OUT/'fixtures'/f"{f['id']}.wasm").read_bytes()
  for row in f['descriptor_rows']:
   a=row['absolute'];b=body[a*32:(a+1)*32]
   assert int.from_bytes(b[:4],'little')==1 and int.from_bytes(b[4:8],'little')==row['type']
   assert int.from_bytes(b[8:16],'little')==row['offset'] and int.from_bytes(b[16:24],'little')==row['length'] and b[24:]==bytes(8)
   assert wasm[row['offset']:row['offset']+row['length']] in [b'\0\x0b',b'\0\x41\0\x0b']
 matrix=json.loads((OUT/'compiler-matrix.json').read_text())
 closure=json.loads((OUT/'inputs/future-closure.json').read_text())
 assert closure['distribution_path_count']==140 and closure['host_support_path_count']==11
 assert sorted(m['name'] for m in matrix['independent_predeclared_sources'])==sorted(Path(p).name for p in closure['host_support_paths'] if p.endswith('.rs'))
 for m in matrix['independent_predeclared_sources']:assert sha(OUT/m['path'])==m['sha256'] and not m['executed']
 assert matrix['scratch_placements']['external']['append']=='\n#[cfg(test)] mod initial_profile_external_contract { include!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE")); }\n'
 assert matrix['scratch_placements']['internal']['append']=='\ninclude!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE"));\n'
 assert matrix['required_positive_placements']==['external','internal']
 budgets=json.loads((OUT/'inputs/test-budget-records.json').read_text())
 selected=budgets['records'][0]['budget'];assert len(selected)==17
 drifts=budgets['records'][1:18];assert len(drifts)==17
 for r in drifts:
  diff=[k for k in selected if selected[k]!=r['budget'][k]]
  assert diff==r['altered_fields'] and len(diff)==1
 assert len(json.loads((OUT/'fixtures/slot-pin-grid.json').read_text())['pairs'])==4096
 result=json.loads((OUT/'old-controls-attempt-2.json').read_text());assert result['all_passed'] and len(result['results'])==2
 for r in result['results']:
  assert r['build_exit']==0 and r['control_exit']==0 and len(r['PASS_lines'])==8
  mode=r['mode'];artifact=OUT/f'old-artifacts/attempt-2-{mode}/same-cache.rows.bin'
  assert artifact.read_bytes()==(OUT/'fixtures/reactor-29.rows.bin').read_bytes()
 assert result['cleanup']['owned_scratch_removed'] and result['cleanup']['all_owned_children_reaped']
 pending=json.loads((OUT/'pending-boundary.json').read_text());assert not any(pending[k] for k in ['candidate_access_authorized','candidate_source_read','candidate_tests_run','candidate_acceptance'])
 review=json.loads((OUT/'predeclared-review-matrix.json').read_text());assert len(review['controls'])==29 and all(c['candidate_status']=='PENDING' for c in review['controls'])
 config=json.loads((OUT/'configuration-selection-custody.json').read_text())
 for m in config['copied_inputs']:check(m,OUT)
 assert [d['production']['id'] for d in config['literal_table_deltas']]==[122,146,160]
 history=json.loads((OUT/'runner-history.json').read_text())
 assert sha(OUT/'retained-runner-attempt-1.py')==history['attempt1_exact_source_sha256']
 for p in (OUT/'old-commands').glob('*/receipt.json'):
  d=json.loads(p.read_text());assert sha(p.parent/'stdout')==d['stdout_sha256'] and sha(p.parent/'stderr')==d['stderr_sha256'] and d['child_reaped']
 for n in [1,2]:
  env=json.loads((OUT/f'old-environment-attempt-{n}.json').read_text());assert env['cleanup']['owned_scratch_removed'] and not Path(env['owned_scratch']).exists()
 print('PASS PREACCESS: frozen custody710; original134+fixed old driver2+3 declared deltas; finite fixtures29/67; 512/2560000 exact expectations; 17 budget drifts; 4096 slot/pin pairs; 10 unrun compiler sources/two placements; 29 pending candidate controls; old actual-source controls8 per mode; candidate unread; owned compiler scratch removed.')
if __name__=='__main__':main()
