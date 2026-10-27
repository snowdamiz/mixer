"""Bind root-accepted corrected145 component, without active sibling access."""
import json
from prepare import D,R,V,sha,put,verify_seal
RECEIPT=V/'swift-semantic-adapter-root-review/guarded-snapshot-loader-work-host-acceptance.json'
EXPECTED='e819f93e5219c631255c4322f291539c72b2660f8b7cb593a51cb4beb78742c7'
def verify_accepted_basis():
 b=RECEIPT.read_bytes();assert sha(b)==EXPECTED
 j=json.loads(b);assert j['source_members']==145 and j['validator_coefficient']==1748020339
 assert j['cap_W_loader']==895083809874789059 and j['exact_source_value_coverage_accepted'] and not j['generic_reference_base_local_coverage_claim_accepted']
 ind=V/j['independent_correction']['path'].removeprefix('verification/')
 custody=verify_seal(ind,'5b15b973477808ff0aeafb00b53006b763d71f5b30d71de5995854aa5193e876',10)
 return dict(schema=1,root_receipt=dict(path=str(RECEIPT.relative_to(R)),sha256=EXPECTED),accepted_source_members=145,accepted_source_tree_sha256=j['source_tree_sha256'],accepted_cap_W_loader=j['cap_W_loader'],accepted_coefficient=j['validator_coefficient'],independent_correction=custody,source146_quote_accepted=False,generic_reference_projection_proof=False,actual_site_coverage_basis=dict(dereference_sites=j['independent_dereference_sites'],projected_stores=j['independent_projected_stores']))
if __name__=='__main__':
 result=verify_accepted_basis();put('accepted145-basis.json',result);print(json.dumps(result,sort_keys=True,indent=2))
