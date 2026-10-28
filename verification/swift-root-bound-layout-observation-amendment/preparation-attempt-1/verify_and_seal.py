#!/usr/bin/env python3
"""Synthetic-only final preparation checks and immutable proposal seal."""
from pathlib import Path
import contextlib
import datetime
import io
import json
import sys
import time
import check
import controls

D=Path(__file__).resolve().parent
def row(path):return {'path':path.relative_to(D).as_posix(),**check.hashed(path)}
def put(path,obj):
    with path.open('x') as handle:json.dump(obj,handle,indent=2,sort_keys=True);handle.write('\n')
def main():
    start=time.monotonic();assert not (D/'seal.json').exists() and not (D/'actual').exists()
    output=D/'commands/final-offline';output.mkdir(parents=True);transcript=io.StringIO();error=None;report=None
    try:
        with contextlib.redirect_stdout(transcript):
            plan=check.check(deadline=start+20)
            print(json.dumps({'status':'complete-saved-command-source-tool-cleanup-custody-passed','actual_saved_raw_parser_calls':0}))
            report=controls.main()
            check.check(deadline=start+45)
            print(json.dumps({'status':'post-controls-custody-reverified','actual_saved_raw_parser_calls':0}))
    except BaseException as failure:error={'type':type(failure).__name__,'message':str(failure)}
    raw=transcript.getvalue().encode();assert len(raw)<=65536
    (output/'stdout').write_bytes(raw);(output/'stderr').write_bytes(b'')
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[str(Path(sys.executable).resolve()),'-B',str(D/'verify_and_seal.py')],
        'cwd':str(check.R),'python':sys.version,'python_tool':{'path':str(Path(sys.executable).resolve()),**check.hashed(Path(sys.executable).resolve())},
        'script':row(Path(__file__).resolve()),'plan_sha256':check.sha((D/'plan.json').read_bytes()),'elapsed_seconds':time.monotonic()-start,
        'exit':int(error is not None),'error':error,'outputs':[row(output/'stdout'),row(output/'stderr')],
        'actual_saved_raw_parser_calls':0,'compiler_invocations':0,'child_workloads':0,'all_prior_source_raw_runtime_and_error_receipts_preserved':True,'layouts_accepted':False}
    put(output/'receipt.json',receipt)
    if error is not None:raise SystemExit(json.dumps(error))
    assert report['actual_saved_raw_parser_calls']==0 and report['adverse_controls_passed']>=100
    members=[row(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_OFFLINE_AMENDMENT_PREPARATION_AWAITING_ROOT_REVIEW_AND_SAVED_RAW_RELEASE',
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'member_count':len(members),'members':members,
        'tree_sha256':check.sha(check.canonical(members)),'member_bytes':sum(r['bytes'] for r in members),
        'plan_sha256':check.sha((D/'plan.json').read_bytes()),'synthetic_adverse_controls':report['adverse_controls_passed'],
        'actual_saved_raw_parser_calls':0,'compiler_invocations':0,'child_workloads':0,'retrospective_policy':True,
        'original_contract_accepted':False,'layouts_prices_backing_peak_funding_full_ownership_native_FieldLog_OTA_GA_accepted':False}
    put(D/'seal.json',seal)
    print(json.dumps({'status':seal['status'],'members':len(members),'plan_sha256':seal['plan_sha256'],'seal_sha256':check.sha((D/'seal.json').read_bytes()),'synthetic_adverse_controls':report['adverse_controls_passed'],'actual_saved_raw_parser_calls':0}))
if __name__=='__main__':main()
