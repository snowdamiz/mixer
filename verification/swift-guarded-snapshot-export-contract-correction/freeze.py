#!/usr/bin/env python3
"""One-time freeze of this separate correction only; no external writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

OWN=Path(__file__).resolve().parent
REPO=OWN.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def main():
    assert not (OWN/'seal.json').exists(), 'never rewrite a frozen packet'
    spec=importlib.util.spec_from_file_location('owned_correction_controls',OWN/'run_controls.py')
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    before=json.loads((OWN/'input-custody-before.json').read_text())
    after=json.loads((OWN/'input-custody-after.json').read_text())
    assert before==after==runner.custody()
    result=json.loads((OWN/'correction-result.json').read_text())
    for name,digest in result['source_inputs_sha256'].items():
        assert sha((OWN/name).read_bytes())==digest, name
    assert result['producer_format_methods_passed']==12
    assert result['fresh_independent_format_groups']==6
    assert result['fresh_independent_format_subcases']==26
    assert result['exact_five_original_failures_retained_now_refused']==5
    assert result['new_boundary_controls']==53 and not result['new_boundary_failed']
    assert result['original_positive_word_disagreements_retained_as_negatives']==3
    assert result['source_controls']['bounded_source_excerpts']==19
    assert result['source_controls']['existing_wrapper_call_line']==137
    assert result['fresh_compiler_controls']==0 and result['inherited_prototype_compiler_controls']==28
    assert result['product_native_OTA_GA_accepted'] is False and result['GA_gates_verified']==0
    assert (OWN/'run.stderr').read_bytes()==b''
    for path in (OWN/'controls/commands').glob('*/receipt.json'):
        receipt=json.loads(path.read_text())
        assert receipt['expectation_met'] and receipt['child_reaped']
        for stream in ['stdout','stderr']:
            assert sha((path.parent/stream).read_bytes())==receipt[stream+'_sha256']
    for name in ['attempt-1','attempt-2']:
        failure=json.loads((OWN/name/'failure.json').read_text())
        assert failure['exit_code']==1
    assert json.loads((OWN/'attempt-3/scope.json').read_text())['exit_code']==0
    paths=sorted(OWN.rglob('*'))
    assert not any(p.is_symlink() for p in paths)
    assert not any(p.name=='__pycache__' for p in paths)
    assert not any(p.suffix in {'.pyc','.rmeta','.rlib','.dylib','.o'} for p in paths)
    write(OWN/'freeze-receipt.json',{
        'schema':1,'at':datetime.now(timezone.utc).isoformat(),
        'command':{'argv':[sys.executable,'-B',str(Path(__file__).resolve())],'cwd':str(REPO)},
        'python':sys.version,'freeze_script_sha256':sha(Path(__file__).read_bytes()),
        'final_controls_runner_exit_code':0,'final_control_expectation_failures':0,
        'preliminary_failed_runs_retained':2,'preliminary_successful_run_retained':1,
        'all_tested_source_hashes_verified':True,'all_original_packets_reverified_unchanged':True,
        'producer_or_peer_one_shot_wrappers_invoked':False,
        'independent_format_function_only_invoked':True,'fresh_compilation':False,
        'scope':'separate R1-R3 contract/model correction; fresh independent review and root acceptance pending',
        'cleanup':result['cleanup'],'implementation_native_OTA_GA_accepted':False})
    members=[{'path':p.relative_to(OWN).as_posix(),'bytes':p.stat().st_size,
              'sha256':sha(p.read_bytes())} for p in sorted(OWN.rglob('*')) if p.is_file()]
    seal={'schema':1,'scope':'frozen separate R1-R3 guarded snapshot export contract/model correction; no implementation/native/OTA/GA acceptance',
          'member_count':len(members),'bytes':sum(r['bytes'] for r in members),
          'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),
          'members':members}
    write(OWN/'seal.json',seal)
    for row in seal['members']:
        p=OWN/row['path']
        assert p.stat().st_size==row['bytes'] and sha(p.read_bytes())==row['sha256']
    print(json.dumps({'member_count':seal['member_count'],'bytes':seal['bytes'],
                      'tree_sha256':seal['tree_sha256'],'seal_sha256':sha((OWN/'seal.json').read_bytes()),
                      'final_failed_expectations':0,'preliminary_failed_runs_retained':2,
                      'status':'frozen-awaiting-fresh-independent-review-and-root-acceptance'}))


if __name__=='__main__':
    main()
