#!/usr/bin/env python3
"""One separately root-released saved-raw parse; no compiler or child process."""
from pathlib import Path
import argparse
import datetime
import json
import os
import time
from check import check,hashed,sha,R,V3
from parser import parse_diagnostics,decode,need
from input_bytes import read_pinned_bytes

D=Path(__file__).resolve().parent
def put(path,obj,deadline):
    need(time.monotonic()<deadline,'offline-evidence-deadline')
    raw=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();need(len(raw)<=262144,'offline-evidence-cap')
    stage=path.with_name(path.name+'.staged')
    with stage.open('xb') as handle:handle.write(raw)
    need(time.monotonic()<deadline,'offline-evidence-staged-deadline');os.link(stage,path)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan-sha256',required=True);ap.add_argument('--root-release-sha256',required=True);args=ap.parse_args()
    start=time.monotonic();deadline=start+55;plan=check(args.plan_sha256,start+20)
    release_path=R/plan['root_release_required']['path']
    need(hashed(release_path,start+20)['sha256']==args.root_release_sha256,'exact-new-offline-root-release')
    release=decode(release_path.read_bytes())
    need(release.get('plan_sha256')==args.plan_sha256 and release.get('offline_saved_raw_parser_released') is True and release.get('actual_saved_raw_parser_calls')==1 and release.get('compiler_invocations')==0,'offline-release-fields')
    out=D/'actual';out.mkdir(exist_ok=False);calls=0;candidate=None;error=None
    try:
        # Only this point, after exact separately reviewed release, supplies the
        # 58 saved actual error records to the amended whole-stream parser.
        need(hashed(V3/'command/stderr',deadline)==plan['saved_stderr'],'saved-raw-preparse-pin')
        stderr=read_pinned_bytes(V3/'command/stderr',plan['saved_stderr'],deadline)
        stdout=read_pinned_bytes(V3/'command/stdout',{'bytes':0,'sha256':sha(b'')},deadline)
        # Both in-memory values are bounded and pinned before the invocation
        # counter advances. Path restoration cannot authorize different bytes.
        calls+=1;candidate=parse_diagnostics(stderr,stdout,1,deadline=start+45)
        check(args.plan_sha256,start+51)
        candidate.update({'plan_sha256':args.plan_sha256,'root_release_sha256':args.root_release_sha256,
            'saved_stderr':plan['saved_stderr'],'source146_tree':plan['source146_tree'],'diagnostic146_tree':plan['diagnostic146_tree'],
            'historical_compiler_invocations':1,'new_compiler_invocations':0,'new_child_workloads':0})
        put(out/'candidate-observation.json',candidate,deadline)
    except BaseException as failure:error={'type':type(failure).__name__,'message':str(failure)}
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[plan['python']['tool']['path'],'-B',str(Path(__file__).resolve()),'--plan-sha256',args.plan_sha256,'--root-release-sha256',args.root_release_sha256],
        'python':plan['python']['version'],'plan_sha256':args.plan_sha256,'root_release_sha256':args.root_release_sha256,
        'saved_stderr':plan['saved_stderr'],'actual_saved_raw_parser_calls':calls,'candidate_emitted':error is None,
        'bounded_input_memory_sha256_verified_before_parser':calls==1,
        'original_v3_contract_accepted':False,'layouts_accepted':False,'retrospective_policy':True,'error':error,
        'elapsed_seconds':time.monotonic()-start,'compiler_invocations':0,'child_workloads':0,
        'prices_backing_peak_funding_full_ownership_native_FieldLog_OTA_GA_accepted':False}
    put(out/'receipt.json',receipt,deadline)
    print(json.dumps({'candidate_emitted':error is None,'layouts_accepted':False,'actual_saved_raw_parser_calls':calls,'error':error}))
    return 0 if error is None else 1
if __name__=='__main__':raise SystemExit(main())
