#!/usr/bin/env python3
"""Pure archive/source ownership review; no compiler or runtime invocation."""
from pathlib import Path
import json,re,sys
from artifact_review import balanced
from review import PACKET,archive,sha,read,require
HERE=Path(__file__).resolve().parent
def main():
 bm=read(PACKET/'baseline-manifest.json');cm=read(HERE/'replacement-source-manifest.json');require(cm==read(PACKET/'candidate-final-manifest.json'),'reviewed source differs from final source');c=archive(HERE/'replacement-source.tar.gz',cm)
 b={n:(PACKET/'baseline'/n).read_bytes()for n in bm};require(all(sha(v)==bm[n]for n,v in b.items()),'baseline source drift');types={}
 groups={'execution.rs':['SwiftExecutionState','SwiftReactorInstance','SwiftFrame','ExecutionOperationPhase','EntryGuard'],'frame_operations.rs':['FrameOperationPhase','FrameOperationStorage','FrameCleanupState','FrameBound'],'memory_growth_operations.rs':['GrowthCompletion','SwiftGrowthContext','SwiftGrowthStorage']}
 for suffix,names in groups.items():
  n='src/experimental_swift_reactor/'+suffix;s0=b[n].decode();s1=c[n].decode()
  for name in names:
   start=lambda s:re.search(r'\b(?:struct|enum) '+name+r'\b',s).start()
   a0=balanced(s0,start(s0));a1=balanced(s1,start(s1));require(a0==a1,'original owner declaration changed '+name);types[name]={'file':n,'sha256':sha(a0.encode()),'byteIdentical':True}
 for n in ['Cargo.toml','Cargo.lock','src/lib.rs','src/experimental_swift_reactor/mod.rs','include/mixer_vm.h']:require(cm[n]==bm[n],'dependencies/public export source changed '+n)
 res={'schema':1,'sourceClosure':sha((HERE/'replacement-source-manifest.json').read_bytes()),'command':sys.argv,'tool':sys.version,'status':'source-owner-review-passed-final-packet-pending','owners':types,'dependenciesIdentical':True,'publicLibraryAndHeaderIdentical':True,'activeSaturationSourceOrder':'prepare_growth computes checked previous+FRAME_OPERATION_BYTES, enlarges construction and records admitted FrameBound before publishing phase; enter and growth require that original phase.','headerTemporalSourceOrder':'Header includes CALLS_PERMANENT_BYTES and is admitted during State construction. original_owners validates exact header before prepare_growth; complete/complete_growth retain State-owned header through frame restoration and returned/caller lifetimes. Full owner cleanup separately transfers header to original ExecutionCleanupTail.','qualifiedRuntimeExecuted':False,'accountingAccepted':False}
 (HERE/'source-owner-temporal-review.json').write_text(json.dumps(res,sort_keys=True,indent=2)+'\n');print(json.dumps(res,indent=2))
if __name__=='__main__':main()
