#!/usr/bin/env python3
"""Run v3 source/offline controls in-process and freeze this separate packet."""
from pathlib import Path
import contextlib
import datetime
import io
import json
import sys
import time

import check
import controls
from strict_json import loads

D = Path(__file__).resolve().parent
def row(path, base=D): return {'path':str(path.relative_to(base)), **check.hash_file(path)}
def put(path,obj):
    with path.open('x') as handle: json.dump(obj,handle,indent=2,sort_keys=True);handle.write('\n')
def main():
    started=time.monotonic(); assert not (D/'seal.json').exists() and not (D/'command').exists()
    output=D/'commands/final-offline';output.mkdir(parents=True)
    transcript=io.StringIO();error=None;plan=None
    try:
        with contextlib.redirect_stdout(transcript):
            plan=check.check(deadline=started+20)
            print(json.dumps({'status':'v3-custody-passed','original173_and_v2_16_members_immutable':True,
                'original_and_diagnostic146_unchanged':True,'preaccess_frozen_members_unchanged':True,
                'argv_environment_identical':True,'plan_sha256':check.sha((D/'plan.json').read_bytes()),'compiler_or_child_processes':0}))
            controls.main()
            check.check(deadline=started+20)
            print(json.dumps({'status':'post-controls-original173-v2_16-and-both146-reverified','compiler_or_child_processes':0}))
    except BaseException as failure:error={'type':type(failure).__name__,'message':str(failure)}
    stdout=transcript.getvalue().encode();assert len(stdout)<=65536
    (output/'stdout').write_bytes(stdout);(output/'stderr').write_bytes(b'')
    receipt={'schema':3,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[str(Path(sys.executable).resolve()),'-B',str(D/'verify_and_seal.py')],'cwd':str(D.parents[1]),'python':sys.version,
        'python_tool':{'path':str(Path(sys.executable).resolve()),**check.hash_file(Path(sys.executable).resolve())},
        'script':row(Path(__file__).resolve()),'plan_sha256':check.sha((D/'plan.json').read_bytes()),
        'elapsed_seconds':time.monotonic()-started,'exit':0 if error is None else 1,'error':error,
        'in_process_calls':['check.check(deadline=start+20)','controls.main()','check.check(deadline=start+20)'],
        'outputs':[row(output/'stdout'),row(output/'stderr')],'compiler_runtime_or_child_processes_started':0,
        'original_v2_preaccess_or_build_mutated':False,
        'scope':'Strict JSON/launch/finite-publication source and synthetic controls only; actual compiler diagnostics and layouts remain unqualified.'}
    put(output/'receipt.json',receipt)
    if error is not None:raise SystemExit(json.dumps(error))
    result=loads((D/'controls-result.json').read_text());assert len(result['controls'])==64
    assert result['actual_layout_strategy_qualified'] is False
    members=[row(path) for path in sorted(D.rglob('*')) if path.is_file() and path.name!='seal.json']
    seal={'schema':3,'status':'FROZEN_V3_SOURCE_OFFLINE_FINITE_PUBLICATION_CORRECTION_AWAITING_ROOT_COMPILER_RELEASE',
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'members':members,'member_count':len(members),
        'tree_sha256':check.sha(check.canonical(members)),'member_bytes':sum(member['bytes'] for member in members),
        'plan_sha256':check.sha((D/'plan.json').read_bytes()),'original_packet_seal_sha256':plan['original_packet']['seal']['sha256'],
        'prior_v2_packet_seal_sha256':plan['prior_v2_packet']['seal']['sha256'],
        'original173_and_v2_16_members_immutable':True,'source146_original_tree':plan['original_source']['tree_sha256'],
        'source146_diagnostic_tree':plan['diagnostic_source']['tree_sha256'],'argv_environment_preserved':True,
        'offline_controls':64,'compiler_released':False,'compiler_executed':False,'layout_strategy_qualified':False,
        'all_actual_layouts_prices_backing_peak_funding_full_ownership_GA_pending':True}
    put(D/'seal.json',seal)
    print(json.dumps({'status':seal['status'],'plan_sha256':seal['plan_sha256'],'seal_sha256':check.sha((D/'seal.json').read_bytes()),
        'members':len(members),'compiler_started':False}))

if __name__=='__main__':main()
