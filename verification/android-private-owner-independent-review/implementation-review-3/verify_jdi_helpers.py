#!/usr/bin/env python3
"""Verify source-bound JDI identities and combine exactly21 direct helper rows without duplicates."""
from pathlib import Path
import json
from validate_matrix_traces import expand
HERE=Path(__file__).resolve().parent
BASE=HERE/'jdi-helper'
def values(path):return [json.loads(line) for line in path.read_text().splitlines() if line.startswith('{')]
def main():
    bindings=json.loads((BASE/'product-bindings.json').read_text());selected={};failed=[]
    for attempt in [1,2,3,4]:
        directory=BASE/f'attempt-{attempt}';codes=json.loads((directory/'compiled-method-code-hashes.json').read_text());cleanup=json.loads((directory/'cleanup.json').read_text());assert cleanup['owned_exact_pids_reaped'] and cleanup['exclusive_scratch_removed']
        for path in sorted(directory.glob('site-*.command.json')):
            command=json.loads(path.read_text());site=command['site'];variant=command['variant'];key=(site,variant)
            assert command['owned_exact_pids_reaped'] and len(command['children'])==2
            if command['forced'] is not None or any(child['exit_code'] for child in command['children'].values()):failed.append(dict(site=site,variant=variant,command=str(path.relative_to(HERE)),qualification_credit=0));continue
            prefix=f'site-{site}-{variant}';controller=values(directory/(prefix+'-controller.stdout'));debuggee=values(directory/(prefix+'-debuggee.stdout'));binding=bindings[site]
            assert len([row for row in controller if row.get('point')=='callerPreinvoke'])==1
            for row in controller:
                if 'method_code_sha256' not in row:continue
                assert row['method_code_sha256']==codes[row['class']+'#'+row['method']+row['descriptor']]
                if row['point'] in ['callerPreinvoke','actualThrowAt','requestedThrowAt']:assert (row['class'],row['method'],row['descriptor'],row['bci'])==(binding['class_name'],binding['method'],binding['descriptor'],binding['caller_preinvoke_bci'])
                if row['point']=='calleeReturn':assert (row['class'],row['method'],row['descriptor'],row['bci'])==(binding['callee_class'],binding['callee_method'],binding['callee_descriptor'],binding['callee_return_bci'])
            scopes=[row for row in controller if 'mutationID' in row];assert len({row['mutationID'] for row in scopes})==1 and len({row['actualTokenID'] for row in scopes})==1
            summary=next(row for row in controller if row.get('scope')=='exact unmodified helper breakpoint controller');result=next(row for row in debuggee if row.get('scope')=='independent exact helper invoke/return witness')
            if variant.endswith('before-return') or variant=='clean':assert summary['calleeEntered'] and summary['returned']
            if 'throw' in variant:assert summary['exceptionEvents']==1 and len([row for row in controller if row.get('point')=='actualThrowAt'])==1
            expand(result['orderedTrace']);assert key not in selected
            selected[key]=dict(site_id=binding['id'],site=site,variant=variant,command=str(path.relative_to(HERE)),controller_assertions=summary['assertions'],debuggee_assertions=result['assertions'],ordered_trace_sha256=result['orderedTrace']['expanded_sha256'],caller_scope=scopes[0],owned_pids={name:child['pid'] for name,child in command['children'].items()})
    variants=['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'];assert set(selected)=={(site,variant) for site in range(3) for variant in variants}
    result=dict(scope='Exactly21 direct helper timing rows; previous nested21 complementary only, no duplicate credit',direct_rows=21,sites=3,controller_assertions=sum(row['controller_assertions'] for row in selected.values()),debuggee_assertions=sum(row['debuggee_assertions'] for row in selected.values()),failed_attempts=failed,rows=list(selected.values()),unmodified_product_and_leaf_class_hashes_checked=True,all_runtime_method_code_hashes_match=True,all_ordered_traces_expand_and_hash=True,all_exact_owned_pid_pairs_reaped=True)
    (BASE/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','failed_attempts']}))
if __name__=='__main__':main()
