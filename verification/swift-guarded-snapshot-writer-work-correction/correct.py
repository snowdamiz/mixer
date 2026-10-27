#!/usr/bin/env python3
"""Bounded writer-ledger correction; only source reads/Python arithmetic.

Never imports predecessor/producer scripts or executes Rust, an encoder or a
writer. Outputs are confined to this correction directory. --verify is read-only.
"""
from pathlib import Path
import copy, hashlib, json, platform, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
OLD=ROOT/'verification/swift-guarded-snapshot-writer-work-audit'
REVIEW=ROOT/'verification/swift-guarded-snapshot-writer-work-independent/candidate-review'
ORIGINAL=ROOT/'verification/swift-guarded-snapshot-composition-source-preparation'
SRC=ORIGINAL/'source/vm/src'
ROOT_REVIEW=ROOT/'verification/swift-semantic-adapter-root-review'
I='experimental_swift_reactor/cache/initial_profile_v1.rs'
C='experimental_swift_reactor/control.rs'
K='experimental_swift_reactor/cache.rs'
A='experimental_wasi/accounted.rs'

def raw_sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return raw_sha(canonical(value))
def read_json(path):return json.loads(path.read_text())
def rowmap(ledger):return {row['name']:row for row in ledger['rows']}

def seal_custody(directory,expected,count):
    raw=(directory/'seal.json').read_bytes()
    assert raw_sha(raw)==expected,(str(directory),'seal drift')
    seal=json.loads(raw);assert len(seal['members'])==count
    total=0
    for row in seal['members']:
        data=(directory/row['path']).read_bytes()
        assert len(data)==row['bytes'] and raw_sha(data)==row['sha256'],row['path']
        total+=len(data)
    return {'path':str((directory/'seal.json').relative_to(ROOT)),
            'sha256':expected,'verified_members':count,'verified_member_bytes':total}

# A custody lexer, not an authority/semantic analyzer. It reproduces the
# producer's exact complete-definition and adjacent-declaration contexts.
def source_definition(path,marker,occurrence):
    data=(SRC/path).read_bytes();starts=[];at=0
    while True:
        at=data.find(marker.encode(),at)
        if at<0:break
        starts.append(at);at+=len(marker)
    start=starts[occurrence];i=data.index(b'{',start)
    depth=0;state='code';block_depth=0
    while i<len(data):
        pair=data[i:i+2];char=data[i:i+1]
        if state=='line':
            if char==b'\n':state='code'
        elif state=='block':
            if pair==b'/*':block_depth+=1;i+=1
            elif pair==b'*/':
                block_depth-=1;i+=1
                if block_depth==0:state='code'
        elif state=='string':
            if char==b'\\':i+=1
            elif char==b'"':state='code'
        elif pair==b'//':state='line';i+=1
        elif pair==b'/*':state='block';block_depth=1;i+=1
        elif char==b'"':state='string'
        elif char==b'{':depth+=1
        elif char==b'}':
            depth-=1
            if depth==0:
                end=i+1
                if data[end:end+1]==b'\n':end+=1
                context=data.rfind(b'\n',0,start)+1
                while context:
                    previous=data.rfind(b'\n',0,context-1)+1
                    if data[previous:context].strip().startswith(b'#['):context=previous
                    else:break
                body=data[start:end]
                return {'path':path,'marker':marker,'occurrence':occurrence,
                        'line':data[:start].count(b'\n')+1,'bytes':len(body),
                        'sha256':raw_sha(body),
                        'declaration_context_sha256':raw_sha(data[context:end])},body.decode()
        i+=1
    raise AssertionError(('unclosed source definition',path,marker))

def inputs():
    custody=[
      seal_custody(OLD,'1dba5632efbf285f303eddc4c9dcb727d0bfaae9f24400a32de98a8989d292ea',14),
      seal_custody(REVIEW,'8ecf12f725d6a6ffc449d46c29243948efcb95332a8d9a33dda0f0eac7732592',6),
    ]
    root_files=[
     ('guarded-snapshot-writer-work-review-custody.json','815fac152cf94dc5affd5e954efeb6310c68b303f41b34c8f471ea92dbd4b54b'),
     ('guarded-snapshot-writer-work-independent-release.json','2c67bc8fe96325eefaeebc6365f2aea7baf76d5995cb0aa1db904ab343305cdd'),
     ('guarded-snapshot-encoder-work-host-acceptance.json','757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'),
    ]
    for name,expected in root_files:
        raw=(ROOT_REVIEW/name).read_bytes();assert raw_sha(raw)==expected
        custody.append({'path':str((ROOT_REVIEW/name).relative_to(ROOT)),
                        'bytes':len(raw),'sha256':expected})
    composer_raw=(ORIGINAL/'seal.json').read_bytes()
    assert raw_sha(composer_raw)=='bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'
    assert len(json.loads(composer_raw)['members'])==495
    custody.append({'path':str((ORIGINAL/'seal.json').relative_to(ROOT)),
       'sha256':raw_sha(composer_raw),'member_count':495,
       'full_member_custody':'inherited original independent review; not rerun or replaced by the later authority candidate'})
    bindings=read_json(OLD/'source-bindings.json');actual=[];bodies={}
    for row in bindings['definitions']:
        found,body=source_definition(row['path'],row['marker'],row['occurrence'])
        assert found==row,('original495 exact definition drift',row['path'],row['marker'])
        actual.append(found);bodies[(row['path'],row['marker'])]=body
    assert len(actual)==121 and digest(actual)==bindings['definition_tree_sha256']
    findings=read_json(REVIEW/'findings.json');review_result=read_json(REVIEW/'results.json')
    assert [f['id'] for f in findings['findings']]==['W1','W2','W3']
    assert review_result['checks_passed']==1413 and review_result['numerical_whole_bound_disproven'] is False
    previous=read_json(REVIEW/'input-custody.json')['predecessor']
    assert previous['independent_controls']==812
    focused=[x for x in actual if (x['path'],x['marker']) in {
       (I,'fn write_snapshot_v1('),(C,'fn snapshot_observe_stop_v1('),
       (K,'fn snapshot_pair_v1('),(A,'fn snapshot_pair_v1('),
       (I,'fn proposed_emission_work_v1(')}]
    source={'schema':1,'target':'original frozen495 composer only; no source delta',
      'composer_seal_sha256':raw_sha(composer_raw),
      'original144_source_tree_sha256':'140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395',
      'definitions_verified':121,'definition_tree_sha256':digest(actual),
      'full_bindings_reference':{'path':str((OLD/'source-bindings.json').relative_to(ROOT)),
        'sha256':raw_sha((OLD/'source-bindings.json').read_bytes())},
      'focused_definitions':focused,
      'source_revision_reference':'79b948a7b361e537cfdd03285f68ea8c50d1a382 from external encoder acceptance; actual source custody is frozen original495',
      'later225_authority_candidate':'not read, imported, priced or authorized by this packet'}
    custody_out={'schema':1,'inputs':custody,'source':source,
       'original_review_controls':{'count':1413,'attribution':'read under frozen review seal; not this correction execution'},
       'predecessor_controls':{'count':812,'attribution':'prior preaccess evidence referenced by frozen review; not this correction execution'},
       'source_delta':False,'producer_and_review_scripts_imported_or_executed':False}
    return read_json(OLD/'ledger.json'),custody_out,source,bodies

def corrected(original):
    value=copy.deepcopy(original);rows=rowmap(value)
    rows['writer_fixed_nonstop_nogetters']['parts']['actual_proof_counts_binding']=1+9+46+1
    rows['writer_fixed_nonstop_nogetters']['note']='401: original400 plus the missing actual-count binding1. initial.cache fetch1 + proof9 + counts46 + actual binding1=57. All other fixed row components unchanged.'
    rows['AccountedWasi.snapshot_pair_v1']['parts']['four_identity_loop_with_setup']=1+2+4*(2+1+2+1+2+51+2)
    rows['AccountedWasi.snapshot_pair_v1']['note']='667: first identity-loop receiver fetch1 + setup2 +4*61=247, replacing246. Ten ticket checks and all other components unchanged.'
    cache=rows['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']
    cache['parts']['three_identity_loop']=1+2+3*(2+1+2+1+2+51+2)
    cache['parts']['optional_WASI_match_upper']=667+10
    cache['note']='1930: cache identity receiver adds1; embedded WASI receiver adds1. First identity loop186; optional WASI match677. The later zip receiver remains a separate occurrence; all other components unchanged.'
    rows['snapshot_observe_stop_v1_without_large_Copy']['note']='Success upper15 is retained. Deadline path has preceding14 + origin fetch1 + Deadline tag1 + Err1=17. The excess2 is charged once in writer/admission terminal tails; no per-observation inflation.'
    rows['writer_global_terminal_tail']['parts']['terminal_Deadline_excess_over_success']=2
    rows['writer_global_terminal_tail']['note']='630: original628 named terminal/copy actions plus once-only Deadline excess2. First terminal stop ends writer; no additional2 on successful observations.'
    rows['admission_global_large_copy_tail']['note']='608 large-copy actions remain unchanged. The separate admission terminal Deadline row adds2 once. Refused export Copy306 remains separately explicit.'
    value['rows'].append({'name':'snapshot_observe_stop_v1_Deadline_branch',
       'parts':{'preceding_common_actions':14,'deadline_origin_fetch':1,'Deadline_tag':1,'Err_carrier':1},
       'credits':17,'note':'17 branch upper versus success15; difference2 goes only in the once-terminal tail, never every observation.'})
    value['rows'].append({'name':'admission_once_only_terminal_Deadline_tail',
       'parts':{'terminal_Deadline_excess_over_success':2},'credits':2,
       'note':'At most one selected Deadline in begin: cache final stop, storage preflight/repeated preflight or either debit. First error aborts; large-copy608 remains a distinct row.'})
    finish=rows['SnapshotRun.finish_v1_added_bookkeeping_without_retire']
    finish['parts']['WASI_pair_ref_result_guard']=667+3
    finish['note']='813: original812 plus the WASI identity receiver1. Retire132 and possible Existing302 remain distinct; finish direct WASI pair does not observe Deadline. All inherited cleanup bodies remain prerequisites.'
    for row in value['rows']:row['credits']=sum(row['parts'].values())
    writer=value['writer'];writer.update(base_without_terminal_tail=401+12*15+2*3,
       global_terminal_tail=628+2,base_with_terminal_tail=401+12*15+2*3+628+2,
       source_action_upper='1217+4259B+122A <=1217+8163B',
       required_native_transfer_additive_term='32E must be added separately in any future complete paid emission formula;1217+8163B alone is insufficient.')
    writer['S_observe_terminal_Deadline_without_large_Copy']=17
    admission=value['admission'];admission.update(max_optional_WASI_pair=1930,
      global_terminal_Deadline_tail=2,current_pending_path_upper=3435,
      future_all_branch_begin_excluding_formula_evaluator=7930,
      pre_admitted_shell_with_common_refusal_tail_upper=2871)
    admission['current_pending_path_decomposition']='32 own source path +1930 pair +260 preflight +44 first debit +55 proof/counts +501 shape +3 WorkAuditPending helper +608 once large copies +2 once terminal Deadline=3435.'
    admission['future_begin_decomposition']='66 own source branches +1930 pair +260 preflight +88 two debit helpers +55 proof/counts +501 shape +293 commit +31 optional usage +4096 initialization +608 once large copies +2 once terminal Deadline=7930, plus exact future evaluator body.'
    admission['shell_decomposition']='13 before/through first debit own source +14 shared decision/refusal return +1930 pair +260 preflight +44 first debit +608 once large copies +2 once terminal Deadline=2871; proposed fixed pre-admitted obligation, not retrospective work funding.'
    value['wrappers']['finish_once_including_retire_and_optional_pair_Existing_copy']=813+132+302
    value['formula_interface']['partial_emission_consumption_contract']='F14224+26B+68I+39D+139W+Q +1217+4259B+122A +32E +4096(initializer), plus independently completed admission/planning/evaluator/caller/cleanup terms. Getter costs are already in writer terms. Not a selected complete operational formula.'
    value['formula_interface']['conservative_partial_substitution']='With A<=32B and Q<=E: F14224+1217+8189B+68I+39D+139W+33E+4096(initializer); remaining paid evaluator/caller/cleanup obligations cannot be silently omitted.'
    value['status']='corrected original495 writer/control source-action proposal; independent correction review and complete operational selection pending'
    return value

def exact_diff(before,after,path=''):
    changes=[]
    if type(before) is not type(after):return [{'path':path,'before':before,'after':after}]
    if isinstance(before,dict):
        for key in sorted(before.keys()|after.keys()):
            sub=path+'/'+key.replace('~','~0').replace('/','~1')
            if key not in before:changes.append({'path':sub,'operation':'add','after':after[key]})
            elif key not in after:changes.append({'path':sub,'operation':'remove','before':before[key]})
            else:changes+=exact_diff(before[key],after[key],sub)
    elif isinstance(before,list):
        for i in range(max(len(before),len(after))):
            sub=path+'/'+str(i)
            if i>=len(before):changes.append({'path':sub,'operation':'add','after':after[i]})
            elif i>=len(after):changes.append({'path':sub,'operation':'remove','before':before[i]})
            else:changes+=exact_diff(before[i],after[i],sub)
    elif before!=after:changes.append({'path':path,'operation':'replace','before':before,'after':after})
    return changes

def validate(value):
    rows=rowmap(value);credit=lambda name:rows[name]['credits']
    assert all(sum(r['parts'].values())==r['credits'] for r in value['rows'])
    assert rows['writer_fixed_nonstop_nogetters']['parts']['actual_proof_counts_binding']==1+9+46+1
    assert rows['AccountedWasi.snapshot_pair_v1']['parts']['four_identity_loop_with_setup']==1+2+4*61
    assert rows['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['three_identity_loop']==1+2+3*61
    assert rows['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['optional_WASI_match_upper']==credit('AccountedWasi.snapshot_pair_v1')+10
    assert credit('AccountedWasi.snapshot_pair_v1')==667 and credit('SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI')==1930
    assert credit('snapshot_observe_stop_v1_without_large_Copy')==15 and credit('snapshot_observe_stop_v1_Deadline_branch')==17
    assert rows['writer_global_terminal_tail']['parts']['terminal_Deadline_excess_over_success']==2
    assert credit('admission_once_only_terminal_Deadline_tail')==2
    assert credit('writer_fixed_nonstop_nogetters')==401 and credit('writer_global_terminal_tail')==630
    w=value['writer'];assert w['base_without_terminal_tail']==401+12*15+2*3
    assert w['base_with_terminal_tail']==w['base_without_terminal_tail']+630==1217
    assert w['per_block_including_clear_and_observations_getters']==4259 and w['per_attempt_including_observations_getters']==122
    a=value['admission'];assert a['max_optional_WASI_pair']==1930 and a['global_large_copy_tail']==608 and a['global_terminal_Deadline_tail']==2
    assert a['current_pending_path_upper']==32+1930+260+44+55+501+3+608+2==3435
    assert a['future_all_branch_begin_excluding_formula_evaluator']==66+1930+260+88+55+501+293+31+4096+608+2==7930
    assert a['pre_admitted_shell_with_common_refusal_tail_upper']==13+14+1930+260+44+608+2==2871
    assert rows['SnapshotRun.finish_v1_added_bookkeeping_without_retire']['parts']['WASI_pair_ref_result_guard']==667+3
    assert credit('SnapshotRun.finish_v1_added_bookkeeping_without_retire')==813
    assert value['wrappers']['finish_once_including_retire_and_optional_pair_Existing_copy']==813+132+302==1247

def models(original,value,bodies):
    checks=[]
    def check(family,condition,detail=None):
        assert condition,(family,detail)
        checks.append({'family':family,'detail':detail})
    rows=rowmap(value);old=rowmap(original)
    validate(value);check('corrected-ledger-dependency-closure',True)
    check('W1-source-row', 'let actual=initial.cache.proof().snapshot_counts_v1();' in bodies[(I,'fn write_snapshot_v1(')] and old['writer_fixed_nonstop_nogetters']['parts']['actual_proof_counts_binding']==56,
          {'expanded':{'cache_fetch':1,'proof':9,'count_getter':46,'binding':1},'total':57})
    for path,name,term,n in [(K,'SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI','three_identity_loop',3),(A,'AccountedWasi.snapshot_pair_v1','four_identity_loop_with_setup',4)]:
        check('W2-distinct-source-occurrence','for ticket in &self.buffers {' in bodies[(path,'fn snapshot_pair_v1(')] and 'self.buffers.iter().zip(' in bodies[(path,'fn snapshot_pair_v1(')],path)
        check('W2-loop-derived',rows[name]['parts'][term]==1+2+n*61 and old[name]['parts'][term]==2+n*61,n)
    check('W3-Deadline-source','Err(SnapshotStopV1::Deadline(self.deadline_origin))' in bodies[(C,'fn snapshot_observe_stop_v1(')])
    check('W3-Deadline-derived',14+1+1+1==17 and 17-15==2)
    # Reverting any source action must fail named-ledger completeness, even
    # when mutually exclusive terminal copy allowances could numerically dominate.
    mutants=[('W1',lambda m:rowmap(m)['writer_fixed_nonstop_nogetters']['parts'].__setitem__('actual_proof_counts_binding',56)),
       ('W2-cache',lambda m:rowmap(m)['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts'].__setitem__('three_identity_loop',185)),
       ('W2-WASI',lambda m:rowmap(m)['AccountedWasi.snapshot_pair_v1']['parts'].__setitem__('four_identity_loop_with_setup',246)),
       ('W3-writer',lambda m:rowmap(m)['writer_global_terminal_tail']['parts'].__setitem__('terminal_Deadline_excess_over_success',0)),
       ('W3-admission',lambda m:rowmap(m)['admission_once_only_terminal_Deadline_tail']['parts'].__setitem__('terminal_Deadline_excess_over_success',0))]
    for name,mutate in mutants:
        m=copy.deepcopy(value);mutate(m)
        for row in m['rows']:row['credits']=sum(row['parts'].values())
        rejected=False
        try:validate(m)
        except AssertionError:rejected=True
        check('regression-reverted-action-rejected',rejected,name)
    # Deadline can select one observation, terminate immediately, and needs
    # exactly2 beyond success15 for that observation; no per-call inflation.
    for blocks in range(1,65):
        for factor in (1,16,32):
            attempts=factor*blocks;observations=12+5*blocks+2*attempts
            for terminal in sorted({1,2,observations//2,observations}):
                actual=15*(terminal-1)+17
                check('once-terminal-Deadline-prefix',actual==15*terminal+2 and terminal<=observations,
                      [blocks,attempts,terminal])
    # Exact propagated deltas, including shell and finish, without silently
    # reclassifying inherited cleanup bodies or future evaluator as zero.
    check('writer-propagation',value['writer']['base_with_terminal_tail']-original['writer']['base_with_terminal_tail']==1+2)
    check('admission-propagation',value['admission']['current_pending_path_upper']-original['admission']['current_pending_path_upper']==2+2)
    check('future-admission-propagation',value['admission']['future_all_branch_begin_excluding_formula_evaluator']-original['admission']['future_all_branch_begin_excluding_formula_evaluator']==2+2)
    check('finish-propagation',value['wrappers']['finish_once_including_retire_and_optional_pair_Existing_copy']-original['wrappers']['finish_once_including_retire_and_optional_pair_Existing_copy']==1)
    for blocks in (1,2,3,17,17033):
        for attempts in (blocks,16*blocks,32*blocks):
            check('writer-A-substitution',1217+4259*blocks+122*attempts<=1217+8163*blocks,[blocks,attempts])
    for extent in (2560,4095,4096,4097,8191,8192,8193,69765152):
        blocks=(extent+4095)//4096
        for attempt_limit in (1,2,31,32):
            # Full block geometry: every request <=its original block length,
            # and all original block lengths partition E. No native transfers.
            requested=attempt_limit*extent
            check('transfer-fill-encoder-initializer-separation',requested<=32*extent and
                  blocks*4096>=extent and value['admission']['admitted_transfer_zero_bytes_once']==4096,
                  [extent,blocks,requested,4096*blocks])
    for width in (32,64):
        maximum=2**width-1
        for left in (0,1,maximum-1,maximum):
            for right in (0,1,2,maximum):
                by_subtraction=right<=maximum-left
                by_integer=left+right<=maximum
                check('checked-bound-arithmetic',by_subtraction==by_integer,[width,left,right])
    changed={'writer_fixed_nonstop_nogetters','AccountedWasi.snapshot_pair_v1',
       'SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI','snapshot_observe_stop_v1_without_large_Copy',
       'writer_global_terminal_tail','admission_global_large_copy_tail',
       'SnapshotRun.finish_v1_added_bookkeeping_without_retire'}
    for name,row in old.items():
        if name not in changed:check('unchanged-original-row',rows[name]==row,name)
    check('large-copy-rows-not-raised-per-observation',value['admission']['global_large_copy_tail']==608 and
          rows['writer_global_terminal_tail']['parts']['one_Existing_failure_Copy']==302 and
          rows['writer_global_terminal_tail']['parts']['one_post_stop_Copy']==304)
    check('inherited-dependencies-preserved',value['wrappers']['inherited_dependencies']==original['wrappers']['inherited_dependencies'] and len(value['wrappers']['inherited_dependencies'])==14)
    check('caller-count-interface-preserved',value['wrappers']['attach_outer_per_call']==16 and value['wrappers']['outer_getter_per_call']==3 and value['wrappers']['attach_inner_at_most_once']==45)
    check('WorkAuditPending-original-source','Err(AError::WorkAuditPending)' in bodies[(I,'fn proposed_emission_work_v1(')] and value['admission']['original_unselected_planning']==16384)
    check('partial-native-term-required','+32E' in value['formula_interface']['partial_emission_consumption_contract'] and '33E' in value['formula_interface']['conservative_partial_substitution'])
    families={}
    for check_row in checks:families[check_row['family']]=families.get(check_row['family'],0)+1
    return {'schema':1,'status':'corrected-original495-source-action-proposal-awaiting-independent-review',
      'python':platform.python_version(),'checks_passed':len(checks),'families':families,
      'checks_sha256':digest(checks),'prior_independent_checks':1413,'prior_preaccess_checks':812,
      'prior_checks_attribution':'referenced frozen evidence; neither prior script executed by this correction',
      'numerical_original_whole_bound_disproven':False,'original_completeness_findings_retained':['W1','W2','W3'],
      'derived_interface':{'writer':'1217+4259B+122A <=1217+8163B','native_requested_bytes_additive':'32E',
         'current_begin':3435,'future_begin_excluding_missing_evaluator':7930,'finish_excluding_inherited':1247,
         'source_delta':False,'original_frozen495_only':True,'later_authority_candidate_included':False},
      'WorkAuditPending_preserved':True,'operational_work_selected':False,'runtime_execution':False}

def main():
    original,custody,source,bodies=inputs();value=corrected(original)
    difference={'schema':1,'kind':'exact JSON path ledger delta; no product source diff',
       'before_path':str((OLD/'ledger.json').relative_to(ROOT)),
       'before_sha256':raw_sha((OLD/'ledger.json').read_bytes()),
       'after_canonical_sha256':digest(value),'source_delta':False,
       'findings_repaired':['W1','W2','W3'],'changes':exact_diff(original,value)}
    outputs={'corrected-ledger.json':value,'ledger-diff.json':difference,
       'input-custody.json':custody,'source-bindings.json':source,
       'results.json':models(original,value,bodies)}
    for name,data in outputs.items():
        if '--verify' in sys.argv:assert read_json(HERE/name)==data,('correction output drift',name)
        else:(HERE/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'checks_passed':outputs['results.json']['checks_passed'],
       'source_definitions_verified':121,'source_delta':False,
       'writer_base':value['writer']['base_with_terminal_tail'],
       'current_begin':value['admission']['current_pending_path_upper'],
       'future_begin':value['admission']['future_all_branch_begin_excluding_formula_evaluator'],
       'finish':value['wrappers']['finish_once_including_retire_and_optional_pair_Existing_copy'],
       'corrected_ledger_canonical_sha256':digest(value),'operational_work_selected':False},sort_keys=True))

if __name__=='__main__':main()
