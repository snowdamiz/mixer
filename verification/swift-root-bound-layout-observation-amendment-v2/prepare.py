#!/usr/bin/env python3
"""Freeze exact offline proposal identities. No amended actual-stream evaluation."""
from pathlib import Path
import datetime
import json
import sys
from check import hashed,sha,R,O,V2,V3,P,W,A
from parser import decode,canonical,symbol_bindings

D=Path(__file__).resolve().parent
def row(path,base=R):return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),**hashed(path)}
def put(path,obj):
    with path.open('x') as handle:json.dump(obj,handle,indent=2,sort_keys=True);handle.write('\n')
def main():
    assert not (D/'plan.json').exists() and not (D/'seal.json').exists() and not (D/'actual').exists()
    vp=decode((V3/'plan.json').read_bytes());rootrelease=decode((R/vp['root_release_required']['path']).read_bytes())
    paths=[O/'seal.json',V2/'seal.json',V3/'seal.json',V3/'plan.json',P/'preaccess-seal.json',P/'diagnostic-bindings-corrected.json',
        P/'independent_diagnostic_parser.py',P/'terminal-v3-review-seal.json',P/'terminal-v3-review.json',W/'seal.json',
        W/'warning-classification-proposal.json',W/'warning-source-bindings.json',W/'FINDINGS.md',R/vp['root_release_required']['path'],
        A/'seal.json',A/'plan.json',P/'amendment-review-01-seal.json',P/'AMENDMENT-REVIEW-01.md']
    plan={'schema':2,'status':'FROZEN_V2_PREPARATION_AWAITING_ROOT_OFFLINE_SAVED_RAW_RELEASE',
        'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision_from_pinned_historical_root_release':rootrelease['source_revision'],
        'scripts':[row(D/n,D) for n in ['prepare.py','check.py','parser.py','controls.py','run.py','input_bytes.py','verify_and_seal.py']],
        'policy':row(D/'policy.json',D),'inputs':[row(path) for path in paths],
        'python':vp['python'],'source146_tree':vp['original_source']['tree_sha256'],'diagnostic146_tree':vp['diagnostic_source']['tree_sha256'],
        'saved_stderr':{'bytes':292318,'sha256':'05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'},
        'prior_amendment':{'seal':row(A/'seal.json'),'plan':row(A/'plan.json'),'members':22,'all_members_and_seal_immutable':True,'actual_saved_raw_parser_calls':0},
        'bounded_input_memory_policy':'Before calls++/parse, read at most pinned length+1 and require exact actual memory length292318 and SHA25605c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635. Pin empty stdout memory too. Preserve pathname precheck and complete posthash custody recheck.',
        'required_source_span_count':346,
        'v2_scope':'Only actual input-memory identity and explicit346 source-span guard, with richer synthetic secondary-span/read-race controls. Exact warning/symbol/summary policy and all existing guards unchanged. Prior amendment not executed.',
        'saved_command_directory':str(V3/'command'),'saved_query_plan_sha256':'95e3ebb57acc3c5ea9e7baac1f657c05ae36ffc957d86b77b38231f4480f958e',
        'saved_command_scope':'Exactly one historical compiler-only command, exit 1, all eight saved members, complete capture, original release/source/toolchain/Python/SDK and successful cleanup joined. Original runner and oracle refused; their bytes remain immutable.',
        'warning_baseline_justification':'Three preexisting source/toolchain warnings also emitted by accepted baseline production-MIR and positive metadata builds. Warning objects remain visible and counted; no warning-free or suppressed-warning claim.',
        'closed_warning_policy':'Exactly three complete decoded objects at zero-based indices0/1/14; every source/child/suggestion/rendered/nullable field is literal, all spans validated. Unknown/missing/duplicate/changed warnings reject.',
        'closure_symbols_derived_from_frozen_full_expressions':symbol_bindings(),
        'closed_summary_policy':'Exactly the frozen abort object for 58 errors and 3 warnings plus both exact failure-note objects at indices61/62/63.',
        'unchanged_refusals':['all56 E0308 exact type/operation/macro/source/expansion bindings','two actual closure identities and zero targets','concrete byte/usize/power-of-two/arithmetic guards','allsource span geometry/highlights/excerpts','unexpected diagnostic/message/child ambiguity/cardinality refusal','strict UTF8/JSON duplicate-key/nonfinite rejection','empty stdout and compiler exit1'],
        'retrospective_policy':True,'original_contract_accepted':False,'candidate_layouts_require_complete_amended_stream_and_later_review':True,
        'execution':{'actual_saved_raw_parser_calls':0,'compiler_invocations':0,'child_workloads':0,'native_UI_capture_process_inventory':False},
        'preparation_decoding_scope':'Literal policy copied byte-for-byte from the immutable first amendment. No actual raw record decoded in v2 preparation; all synthetic error values are arbitrary and no actual complete stream has been supplied to the amended parser.',
        'root_release_required':{'path':'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-amendment-release.json',
            'required_fields':{'plan_sha256':'exact digest of this new plan','offline_saved_raw_parser_released':True,'actual_saved_raw_parser_calls':1,'compiler_invocations':0}},
        'proposed_argv':[vp['python']['tool']['path'],'-B',str(D/'run.py'),'--plan-sha256','EXACT_NEW_PLAN_SHA256','--root-release-sha256','EXACT_NEW_ROOT_OFFLINE_RELEASE_SHA256'],
        'bounds':{'wall_seconds':55,'preflight_seconds':20,'parse_deadline_seconds':45,'posthash_deadline_seconds':51,'actual_saved_raw_parser_calls':1,'compiler_invocations':0,'child_workloads':0,'automatic_retries':0},
        'layouts_prices_backing_peak_funding_full_ownership_native_FieldLog_OTA_GA_accepted':False}
    put(D/'plan.json',plan)
    patch=''
    import difflib
    for name in ['check.py','parser.py','controls.py','run.py','prepare.py','verify_and_seal.py']:
        patch+=''.join(difflib.unified_diff((A/name).read_text().splitlines(True),(D/name).read_text().splitlines(True),fromfile='amendment/'+name,tofile='amendment-v2/'+name))
    patch+=''.join(difflib.unified_diff([],(D/'input_bytes.py').read_text().splitlines(True),fromfile='/dev/null',tofile='amendment-v2/input_bytes.py'))
    (D/'correction-delta.patch').write_text(patch)
    put(D/'preparation-receipt.json',{'schema':2,'command':[str(Path(sys.executable).resolve()),'-B',str(D/'prepare.py')],
        'python':sys.version,'python_tool':row(Path(sys.executable).resolve()),'plan_sha256':sha((D/'plan.json').read_bytes()),
        'actual_saved_raw_parser_calls':0,'compiler_invocations':0,'child_workloads':0,'layouts_accepted':False})
    print(json.dumps({'status':'prepared-v2-offline-amendment-no-actual-parser-call','plan_sha256':sha((D/'plan.json').read_bytes())}))
if __name__=='__main__':main()
