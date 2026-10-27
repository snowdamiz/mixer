#!/usr/bin/env python3
"""Independent read-only input verification; writes only this review packet."""
from pathlib import Path
import hashlib, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-emission-bound-implementation'
BASE = ROOT / 'verification/swift-guarded-snapshot-scope-authority-correction'
INITIAL = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
HELPER = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def emit(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def bound(path):
    raw=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha(raw)}

def extract(text, marker):
    """Lexical brace matching, including comments and ordinary string literals."""
    assert text.count(marker)==1, marker
    start=text.index(marker)
    begin=text.rfind('\n', 0, start)+1
    while begin:
        previous=text.rfind('\n', 0, begin-1)+1
        if text[previous:begin].lstrip().startswith('#['): begin=previous
        else: break
    pos=text.index('{', start); depth=0; state='code'; nesting=0
    while pos<len(text):
        c=text[pos]; pair=text[pos:pos+2]
        if state=='line':
            if c=='\n': state='code'
        elif state=='block':
            if pair=='/*': nesting+=1; pos+=1
            elif pair=='*/':
                nesting-=1; pos+=1
                if nesting==0: state='code'
        elif state=='string':
            if c=='\\': pos+=1
            elif c=='"': state='code'
        elif pair=='//': state='line'; pos+=1
        elif pair=='/*': state='block'; nesting=1; pos+=1
        elif c=='"': state='string'
        elif c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0:
                end=pos+1+(text[pos+1:pos+2]=='\n')
                return text[begin:end].encode(), text[:start].count('\n')+1
        pos+=1
    raise AssertionError(('unbalanced input', marker))

def main():
    release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-emission-bound-independent-release.json'
    assert bound(release)['sha256']=='23f498b066a99f6ef231cfea4b539e1128d1920fd401505a3df5c9d7be7d5bf1'
    assert sha((PRODUCER/'seal.json').read_bytes())=='e92026187ef181ddbcc178e53611ce5e4aa0111c613e9c8ad3a4aca58ff8ffcc'
    seal=json.loads((PRODUCER/'seal.json').read_bytes())
    rows=seal['members']
    assert (len(rows),sum(r['bytes'] for r in rows),sha(canonical(rows)))==(58,169951,'b0877704d06924f65c7f15f23c9a7bca8b7ec8f28449ef90ad7f01b84a199e4b')
    for r in rows:
        raw=(PRODUCER/r['path']).read_bytes()
        assert len(raw)==r['bytes'] and sha(raw)==r['sha256'],r['path']
    observed=sorted(str(p.relative_to(PRODUCER)) for p in PRODUCER.rglob('*') if p.is_file())
    assert observed==sorted([r['path'] for r in rows]+['seal.json','freeze-receipt.json'])
    freeze=bound(PRODUCER/'freeze-receipt.json')
    assert freeze['sha256']=='8e62ad31ae77e9ec07e0f48f5125443559f2a7f483537c9b4c3b7177558b22fa'
    original=json.loads((BASE/'source-manifest.json').read_bytes())
    assert bound(BASE/'seal.json')['sha256']=='351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c'
    assert bound(BASE/'source-manifest.json')['sha256']=='6f835a7607d319966204225bde1e4716bcaa4d53260242b36c3bd50f1d1f45a1'
    assert len(original['members'])==144
    assert sha(canonical(original['members']))==original['source_tree_sha256']=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
    for r in original['members']:
        raw=(BASE/'source/vm'/r['path']).read_bytes()
        assert len(raw)==r['bytes'] and sha(raw)==r['sha256'], r['path']
    candidate=json.loads((PRODUCER/'source-manifest.json').read_bytes())
    assert len(candidate['members'])==145
    assert sha(canonical(candidate['members']))==candidate['source_tree_sha256']=='32e10cca35240748978ea635899cd14229814c61c0a6f7c988b1c2bed2980abc'
    for r in candidate['members']:
        base=PRODUCER/'overlay/vm' if r['path'] in [INITIAL,HELPER] else BASE/'source/vm'
        raw=(base/r['path']).read_bytes()
        assert (len(raw),sha(raw))==(r['bytes'],r['sha256']),r['path']
    parent=(PRODUCER/'overlay/vm'/INITIAL).read_text()
    unchanged=(BASE/'source/vm'/INITIAL).read_text()
    addition='// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n'
    assert parent==unchanged.replace('fn proposed_emission_work_v1(',addition+'fn proposed_emission_work_v1(')
    helper=(PRODUCER/'overlay/vm'/HELPER).read_bytes()
    assert sha(helper)=='ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a'
    assert parent.count('checked_snapshot_emission_bound_v1')==0
    stable=[]
    for marker in ['fn proposed_emission_work_v1(',"fn begin_snapshot_access_v1<'c>(",'fn write_snapshot_v1(']:
        actual,line=extract(parent,marker);previous,_=extract(unchanged,marker)
        assert actual==previous
        stable.append({'marker':marker,'line':line,'bytes':len(actual),'sha256':sha(actual)})
    assert 'Err(AError::WorkAuditPending)' in extract(parent,'fn proposed_emission_work_v1(')[0].decode()
    # Reconstruct real types independently from immutable source declarations,
    # then compare the resulting complete compilation input to the frozen packet.
    custody=json.loads((PRODUCER/'input-custody.json').read_bytes())
    chunks=[];declarations=[]
    for r in custody['host_real_type_and_pure_shape_extractions']:
        raw,line=extract((BASE/'source/vm/src'/r['path']).read_text(),r['marker'])
        assert sha(raw)==r['context_sha256'] and len(raw)==r['context_bytes'] and line==r['line']
        chunks.append(raw)
        declarations.append({'path':r['path'],'marker':r['marker'],'line':line,'bytes':len(raw),'sha256':sha(raw)})
    types=b'\n'.join(chunks)
    assert types==(PRODUCER/'host/source-types.rs').read_bytes()
    (HERE/'host').mkdir(exist_ok=True)
    (HERE/'host/source-types.rs').write_bytes(types)
    names=[('guarded-snapshot-encoder-work-host-acceptance.json','757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'),
        ('guarded-snapshot-writer-work-host-acceptance.json','21251a3aef2d42373ba71711f8eb389634294d4b5b3b61388e718bfb0a25e281'),
        ('guarded-snapshot-authority-work-host-acceptance.json','82913dae316073164e82b661cab7f6baf83a68879a25c85c97fc014d56da0b73')]
    accepted=[]
    for name,digest in names:
        p=ROOT/'verification/swift-semantic-adapter-root-review'/name
        assert bound(p)['sha256']==digest
        accepted.append(bound(p))
    e=json.loads((ROOT/accepted[0]['path']).read_bytes())['accepted_interface']
    assert e=={'fixed_initialization':14224,'block':'26+68I+39D+139W+Q','per_call_maximum':291214,'opaque_getter':3,'I_max':515,'D_max':'9I','W_max':513,'Q_max':4096}
    w=json.loads((ROOT/accepted[1]['path']).read_bytes())
    assert w['writer_formula']=='1217+4259B+122A' and w['mandatory_native_transfer_term']=='32E separate'
    assert w['future_begin_excluding_evaluator']==7930
    a=json.loads((ROOT/accepted[2]['path']).read_bytes())
    assert a['added_once']==19 and a['operational_work_selected'] is False
    # Full-source metadata inclusion is already resolved by a frozen diagnostic:
    # its invalid return is reported in the declared helper module. Do not rerun.
    negative=json.loads((PRODUCER/'commands/metadata-negative-type/receipt.json').read_bytes())
    diagnostics=[json.loads(x) for x in (PRODUCER/'commands/metadata-negative-type/stderr').read_text().splitlines() if x.startswith('{')]
    errors=[d for d in diagnostics if (d.get('code') or {}).get('code')=='E0308']
    assert negative['expectation_met'] and negative['exit_code']==1 and errors
    assert any(HELPER in s['file_name'] for d in errors for s in d['spans'])
    loader=BASE/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    lines=loader.read_text().splitlines()
    descriptor=[{'line':i+1,'text':line.strip()} for i,line in enumerate(lines) if 'word(b, 32) != 144' in line or 'word(b, 40) != 11' in line]
    assert len(descriptor)==2,descriptor
    emit('input-custody.json',{'schema':1,'root_release':bound(release),'producer_seal':bound(PRODUCER/'seal.json'),
        'producer_members':len(rows),'producer_member_bytes':sum(r['bytes'] for r in rows),'producer_tree':sha(canonical(rows)),
        'postseal_freeze_receipt':freeze,'only_postseal_exclusions':['seal.json','freeze-receipt.json'],
        'base_source_members_verified':144,'base_source_tree':original['source_tree_sha256'],
        'candidate_source_members_verified':145,'candidate_source_tree':candidate['source_tree_sha256'],
        'accepted_interfaces':accepted,'helper':bound(PRODUCER/'overlay/vm'/HELPER),
        'parent':bound(PRODUCER/'overlay/vm'/INITIAL),'unchanged_actual_functions':stable,
        'real_type_and_geometry_declarations':declarations,'reconstructed_host_types':bound(HERE/'host/source-types.rs'),
        'retained_descriptor_lines':descriptor,'descriptor_source':bound(loader),'descriptor_mismatch_unresolved':True,
        'full_source_inclusion_resolved_from_bound_producer_metadata_negative':True,'fresh_metadata_needed':False,
        'producer_runners_imported_or_executed':False,'canonical_component_folders_read':False})
    assert 26+68*515+39*9*515+139*513+4096==291214
    fixed=14224+1217+4096;per=291214+4259+32*122
    assert (fixed,per)==(19537,299377)
    emit('derivation.json',{'schema':1,'candidate':'19537+299377B+32E','fixed':fixed,'per_block':per,
        'accepted_expansion':'14224 + B*(26+68*515+39*(9*515)+139*513+4096) + 1217+4259B+122A + 32E +4096',
        'encoder_ceiling':291214,'writer_attempts_A_at_most':'32B','native_requested_at_most':'32E',
        'native_proof':'For block length Li and each native attempt requested<=Li; at most32 attempts. Sum_i(32Li)<=32E, including Interrupted and partial-write retries.',
        'first_error_prefix':'Every ? or explicit error returns immediately from the writer closure. A failed encoder call receives the whole accepted nonempty-call ceiling. No retry follows encoder error. Actual geometry/count equality precedes output operations. At most B cursor calls; final_block breaks without terminal None.',
        'prefix_includes_stop_and_IO':'Accepted writer fixed/block/attempt terms include early failure paths and first terminal observation; the bound is conditional on those accepted interfaces and unchanged inherited bodies.',
        'getter':'Getter3 is already in accepted writer terms; no second getter debit.',
        'initializer':'Exactly one4096 transfer initializer is included. Future-begin7930 also names it; combining decompositions must attribute one occurrence.',
        'helper_source_actions':{'entry_and_return':2,'named_field_reads':2,'checked_ops':4,'eager_Arithmetic_variants':4,'ok_or_inspect_and_result':8,'question_inspect_and_payload':6,'local_bindings':3,'total':29},
        'helper_first_error_action_prefixes_by_checked_operation':[9,17,24,29],
        'helper_checked_order':['B*299377','E*32','19537+transfers','blocks+fixed_and_transfers'],
        'helper_fail_closed':'Each overflow maps None to Arithmetic; first three use ? and the fourth returns its Result directly. All terms nonnegative, so successful u64 result equals the mathematical sum.',
        'maximum_geometry':{'extent':69765152,'blocks':17033,'emission':fixed+per*17033+32*69765152},
        'unchanged_execution_work_ceiling':1000000000,'arithmetic_minimum_geometry_not_runtime_validation':{'extent':2560,'blocks':1,'emission':fixed+per+32*2560},
        'separate_authority_delta19':'Already accepted as earlier pre-admitted routing, outside emission.',
        'pending':['Pay helper29 under planning before computed debit; preserve caller ?/binding3 and exact callsite review.',
            'Fund helper reference/scalars/checked Option/eager AError/ok_or Result/? success-error/return places before evaluation, preceding storage commit.',
            'Close helper source-place lifetimes/target layout with separate owner delta; host layout does not close a simultaneous byte floor.',
            'Retain shell/inherited/caller/stop/cleanup/F1 lifetime costs and initializer attribution.',
            'Correct and requalify genuine loader descriptor144/support11 against145 source overlay.',
            'Select no writer, complete work/storage floor, product runtime, OTA/FieldLog/store/customer or GA gate.']})
    print(json.dumps({'custody':'verified','producer_members':58,'candidate_source_members':145,'derived_fixed':fixed,'derived_per_block':per,'logical_helper_actions':29,'fresh_metadata_needed':False},sort_keys=True))

if __name__=='__main__':main()
