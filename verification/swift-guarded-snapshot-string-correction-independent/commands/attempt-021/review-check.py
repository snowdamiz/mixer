#!/usr/bin/env python3
"""Read-only checker for this frozen independent return and its input packets."""
import hashlib,json,sys
from pathlib import Path
import custody
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(v,m):
 if not v:raise ValueError(m)
def main():
 sealed=(D/'seal.json').exists()
 if sealed:
  seal=json.loads((D/'seal.json').read_text());rows=seal['members'];actual=set()
  for f in D.rglob('*'):
   need(not f.is_symlink(),'review-symlink')
   if f.is_file() and f.name!='seal.json':actual.add(str(f.relative_to(D)))
  need(actual=={r['path'] for r in rows},'review-membership')
  for m in rows:
   p=Path(m['path']);need(not p.is_absolute() and '..' not in p.parts,'review-path');raw=(D/p).read_bytes();need(len(raw)==m['bytes'] and sha(raw)==m['sha256'],'review-member:'+str(p))
  need(len(rows)==seal['member_count'] and sum(m['bytes'] for m in rows)==seal['bytes'],'review-counts')
 for name,pin,count,size in [('swift-guarded-snapshot-string-provenance-correction','4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994',358,56817849),('swift-guarded-snapshot-string-provenance-independent','741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9',108,6581268),('swift-guarded-snapshot-string-provenance','b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',114,6305257)]:custody.check_packet(name,pin,count,size)
 cj=json.loads((D/'custody.json').read_text())
 for p,h in cj['root_and_contract_pins'].items():need(sha((V/p).read_bytes())==h,'root-pin:'+p)
 for p,m in json.loads((V/'swift-guarded-snapshot-string-provenance-correction/input-bindings.json').read_text())['files'].items():
  b=(R/p).read_bytes();need(len(b)==m['bytes'] and sha(b)==m['sha256'],'input-member:'+p)
 review=json.loads((D/'review.json').read_text());need(review['status']=='return-correction-candidate-for-further-correction','return-decision');need(review['independent_tests']==17 and review['independent_fail_closed_expectations_failed']==10,'adverse-census');need(review['actual_selected_header_discrepancies']==6,'actual-type-errors')
 for f in ('L_str_selected','whole_host_bound_selected','actual_P0_caller_or_fixture_selected','policy_or_operational_grant','OTA_authority','GA','future_outer_27deef_coverage','complete_typed_graph_or_source_closure_accepted'):need(review[f] is False,'no-authority:'+f)
 need([f['id'] for f in review['findings']]==['F1','F2','F3','F4'],'all-findings-retained')
 for p in sorted((D/'commands').glob('*/receipt.json')):
  r=json.loads(p.read_text());need(r['owned_child_waited'] and r['frozen_packets_unchanged'] and not r['timed_out'],'child/custody:'+str(p))
 print(json.dumps({'status':'independent-return-packet-check-passed','sealed':sealed,'decision':'return-for-further-correction','candidate_bytes_unchanged':True,'adverse_failures_preserved':10,'actual_selected_header_discrepancies':6,'L_str_selected':False,'operational_grant':False,'seal_sha256':sha((D/'seal.json').read_bytes()) if sealed else None},sort_keys=True))
if __name__=='__main__':main()
