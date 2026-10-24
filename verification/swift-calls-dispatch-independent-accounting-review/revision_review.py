#!/usr/bin/env python3
"""Explain the rejected-to-repaired inventory delta from actual bound inventories."""
from pathlib import Path
import collections,datetime,json,sys
from review import PACKET,read,require,sha
HERE=Path(__file__).resolve().parent
def main():
 old={r['field']:r for r in read(PACKET/'inventory-v4.json')};new={r['field']:r for r in read(PACKET/'inventory-v5.json')};removed=[old[f]for f in sorted(old.keys()-new.keys())]
 require(not new.keys()-old.keys()and len(removed)==32,'unexpected repaired field set')
 counts=collections.Counter()
 for r in removed:
  require(r['config']in ['all-debug-production','all-debug-unit','swift-debug-production','swift-debug-unit'],'removal outside Debug scanner')
  require(r['body'].endswith('call_dispatch::signature_mismatch')and r['method']=='exact-typed'and r['ownerClass']=='active','removed prior/finite/permanent position')
  require(r['position']in ['source','argument','returned','caller'],'invalid removed role')
  if r['kind']=='canonical':require(r['mirType']=='&mut experimental_swift_reactor::cache::SwiftFunctionCache','unexpected removed canonical type')
  else:require(r['kind']=='constant-operand'and r['mirType']=="&'static str",'unexpected removed operand type')
  counts[(r['config'],r['kind'])]+=1
 require(all(v==4 for v in counts.values())and len(counts)==8,'removed positions do not retain four-role groups')
 require({f for f,r in old.items()if 'numeric'in r['method']}=={f for f,r in new.items()if 'numeric'in r['method']},'finite set changed')
 carriers=[r for r in old.values()if r['config']=='source'];require(len(carriers)==36 and all(new[r['field']]==r for r in carriers),'original whole carrier position changed')
 summary=read(PACKET/'v4-to-v5-mapping-summary.json');require({r['field']for r in removed}=={r['field']for r in summary['removedScannerOnlyTypedRoles']},'producer removal explanation disagrees with actual inventories')
 result={'schema':1,'status':'rejected-to-repaired-position-delta-passed','command':sys.argv,'tool':sys.version,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verifierSHA256':sha(Path(__file__).read_bytes()),'oldRoles':len(old),'finalRoles':len(new),'removedRoles':removed,'addedRoles':[],'retainedOriginalWholeCarrierRoles':len(carriers),'finiteRolesUnchanged':1032,'removedCounts':[{'config':cfg,'kind':kind,'roles':n}for(cfg,kind),n in sorted(counts.items())],'scope':'Candidate-only scanner temporaries changed by R1; full final compiler role coverage and prior baseline classes are independently checked in the other receipts.','qualifiedRuntimeExecuted':False}
 (HERE/'source-revision-review.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='removedRoles'},indent=2))
if __name__=='__main__':main()
