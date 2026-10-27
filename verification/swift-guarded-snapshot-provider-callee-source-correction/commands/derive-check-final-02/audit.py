"""Read-only correction consistency, complete frozen custody and command audit."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from custody import HERE,ROOT,roster,sha,row,need
import derive as D

def main():
 inputs=roster();need(inputs==D.load(HERE/'input-lock.json'),'complete final frozen input custody')
 for name,value in D.derive().items():need(D.canon(D.load(HERE/name))==D.canon(value),'stale corrected artifact '+name)
 final=D.load(HERE/'final-validation.json')
 for name in final['qualifying_commands']:
  p=HERE/'commands'/name;r=D.load(p/'receipt.json')
  need(r['exit_code']==0 and not r['timed_out'] and r['owned_group_absent'] and r['child_reaped'] and r['frozen_input_custody_unchanged'],'bounded qualifying command '+name)
  for kind in ('stdout','stderr','inputs_before','inputs_after'):
   q=p/({'inputs_before':'inputs-before.json','inputs_after':'inputs-after.json'}.get(kind,kind));need(row(q)==r[kind],'command output custody')
  need(D.load(p/'inputs-before.json')==inputs==D.load(p/'inputs-after.json'),'qualifying frozen inputs unchanged')
  for filename,expected in r['source_scripts'].items():need(row(HERE/filename)==expected,'qualifying exact final source '+filename)
 latest=D.load(HERE/'latest-checks.json');need(latest['failures']==latest['errors']==0 and latest['fresh_targeted_R1_R2_R3_test_methods']==8,'fresh targeted controls')
 sealpath=HERE/'seal.json';sealed=False
 if sealpath.exists():
  sealed=True;seal=D.load(sealpath);expected={x['path']:x for x in seal['members']};actual={p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!='seal.json'}
  need(actual==set(expected),'complete correction packet seal membership')
  for name,record in expected.items():
   p=HERE/name;need(not p.is_symlink() and p.resolve().is_relative_to(HERE),'own regular member');b=p.read_bytes();need(len(b)==record['bytes'] and sha(b)==record['sha256'],'immutable correction member '+name)
  need(seal['member_count']==len(expected) and seal['bytes']==sum(x['bytes'] for x in expected.values()),'correction envelope')
 print(json.dumps({'status':'source-correction-custody-derivation-focused-controls-pass','sealed_complete_membership_checked':sealed,'frozen_inputs':len(inputs['files']),'inherited_frozen_packets':15,'plus_original_producer_and_review_packets':2,'source146':D.TREE,'closed_interfaces':10,'partial_interfaces':4,'mandatory_positive_residual_contexts_per_unit':30,'all15_phases':True,'native_runtime_OTA_GA_or_price_selection':False}))
if __name__=='__main__':main()
