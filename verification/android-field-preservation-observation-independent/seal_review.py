#!/usr/bin/env python3
"""Seal this owned independent review once; future invocations only verify."""
from pathlib import Path
import datetime,hashlib,json,sys
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
F=D.parent/'android-field-preservation-observation-controls'
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 assert identity(F/'seal.json')['sha256']=='02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250'
 author=json.loads((F/'seal.json').read_bytes());expected={r['path']:r for r in author['members']}
 assert set(expected)=={str(p.relative_to(F)) for p in F.rglob('*') if p.is_file() and p!=F/'seal.json'}
 for name,r in expected.items():assert identity(F/name)=={'bytes':r['bytes'],'sha256':r['sha256']}
 sealpath=D/'review-seal.json';paths=sorted(p for p in D.rglob('*') if p.is_file() and p!=sealpath)
 assert not any(p.is_symlink() or 'scratch' in p.relative_to(D).parts or '__pycache__' in p.relative_to(D).parts for p in paths)
 members=[{'path':str(p.relative_to(D)),**identity(p)} for p in paths]
 if sealpath.exists():
  seal=json.loads(sealpath.read_bytes());assert seal['members']==members
  print('PASS immutable independent review',len(members),'members; seal',identity(sealpath)['sha256']);return
 inspection=json.loads((D/'inspection.json').read_bytes());recovery=json.loads((D/'recovery-validation.json').read_bytes());review=json.loads((D/'review-commands.json').read_bytes())
 assert inspection['whole_four_original_records_preserved'] and inspection['finite_facet_projections_exact']
 assert recovery['all209_exact_in_both_runs'] and recovery['supplemental_controls']==2
 assert all(c['exit']==0 and not c['timeout'] and c['reaped'] for c in review['commands'])
 seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'independent-review-passed-finite-host-evidence-only-root-selection-pending','author_packet_seal':identity(F/'seal.json'),'author_member_count':171,'source_context':author['source_context'],'source_revision_context':author['source_revision_context'],'exact_replay_rows':56,'exact_replay_assertions':731,'exact_replay_result':identity(D/'run-exact/actual-results.json'),'supplemental_controls':2,'supplemental_actual_exact_calls':3,'supplemental_run_assertions':747,'original_cases_enclosing_helper_allocation_obligations':'retained pending without substitution','exact_subject_Input_counts_and_BCIs':'pending; seven direct support returns are separate','diagnostic_limits':['Shared.events literal0 does not prove event-log restoration','fixture close catches product exceptions; no newly asserted full-disposal state'],'owned_cleanup':'all children terminally reaped, owned scratch removed, shared JDK hashes unchanged','native_UI_capture_process_inventory_Git_or_canonical_mutations':False,'members':members,'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members)}
 sealpath.write_text(json.dumps(seal,indent=2)+'\n');print('SEALED independent review',len(members),'members; seal',identity(sealpath)['sha256'])
if __name__=='__main__':main()
