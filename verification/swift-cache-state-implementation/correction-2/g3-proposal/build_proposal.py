#!/usr/bin/env python3
"""Source-only four-load inlining proposal. Never edits or runs product/tests."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[3]
source=ROOT.parent/'source/library/cache_state.rs';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)=='6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00'
def save(name,data):(ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
old='''                    let a = ld(c, src + left * 8);
                    let b = ld(c, src + right * 8);
                    b == ABSENT || (a != ABSENT && ld(c, a as usize * 8) <= ld(c, b as usize * 8))
'''
assert old in source.read_text()
new='''                    macro_rules! comparison_word {
                        ($offset:expr) => {{
                            let at = $offset;
                            u64::from_le_bytes(
                                *c[at..at + 8]
                                    .first_chunk::<8>()
                                    .expect("proved eight-byte range"),
                            )
                        }};
                    }
                    let a = comparison_word!(src + left * 8);
                    let b = comparison_word!(src + right * 8);
                    b == ABSENT
                        || (a != ABSENT
                            && comparison_word!(a as usize * 8)
                                <= comparison_word!(b as usize * 8))
'''
(ROOT/'old-fragment.txt').write_text(old);(ROOT/'proposed-fragment.txt').write_text(new)
# Complete favorable source-value-flow grammar: one named primitive for each
# full transfer edge, including both source and received places; no machine code.
shared=[('end_add','at+8',1),('range','complete Range16 constructor/index argument source->receive',1),('range_order','range start<=end',1),('range_end','range end<=slice length',1),('view','complete shared8-byte range view/receiver',1),('chunk_predicate','first_chunk::<8> length predicate',1),('option','complete Option<&[u8;8]>8 source->received',1),('expect_tag','expect Option tag test',1),('array_reference','complete &[u8;8]8 source->received',1),('LE','from_le_bytes conversion',1)]
old_ops=[('offset_mul','caller offset multiplication/cast',1),('offset_add','caller offset addition/multiplication',1),('slice_arg','complete b slice view/argument source->ld received',1),('offset_arg','offset scalar source->ld received',1)]+shared+[('conversion_return','from_le_bytes u64 return->ld tail received',1),('ld_return','ld u64 return->caller binding received',1)]
new_ops=[('offset_mul','caller offset multiplication/cast',1),('offset_add','caller offset addition/multiplication',1),('address_binding','offset scalar source->block-local at received',1)]+shared+[('conversion_return','from_le_bytes u64 return->enclosing caller expression/binding received',1)]
assert sum(v[2]for v in old_ops)==16 and sum(v[2]for v in new_ops)==14
pred=[('b_absent','b==ABSENT'),('b_short_circuit','|| short-circuit branch'),('a_present','a!=ABSENT'),('a_short_circuit','&& short-circuit branch'),('timestamp_order','timestamp_a<=timestamp_b'),('result','complete comparison bool source->take_left received')]
loads=[{'id':'A','old_line':265,'address':'src+left*8','reads':'index a','execution':'always within actual pair comparison'}, {'id':'B','old_line':266,'address':'src+right*8','reads':'index b','execution':'after A, always within actual pair comparison'}, {'id':'TA','old_line':267,'address':'a as usize*8','reads':'timestamp[a]','execution':'only after b!=ABSENT then a!=ABSENT'}, {'id':'TB','old_line':267,'address':'b as usize*8','reads':'timestamp[b]','execution':'after TA, under same b/a guards'}]
ops=lambda values:[{'id':id,'name':name,'scalar_units':n}for id,name,n in values]
save('operation-partition.json',{'schema':1,'target_sha256':sha(source),'old_lines':[265,267],'old_helper_lines':[149,155],'load_sites':loads,'old_scalar_ops_per_load':ops(old_ops),'proposed_scalar_ops_per_expanded_load':ops(new_ops),'shared_comparator_scalars':[{'id':id,'name':name,'scalar_units':1}for id,name in pred],'payload_flow_per_load':'dereferenced8-byte source array -> from_le_bytes by-value received array; exactly one fixed-copy group, no returned LE array','old':{'scalar_total':70,'copy_groups':4,'conditional_pooled_group_minimum':9},'new':{'scalar_total':62,'copy_groups':4,'proposed_groups':8},'proposed_scalar_blocks':[{'id':'S1','load':'A','operations':[f'A.{v[0]}'for v in new_ops],'count':14},{'id':'S2','load':'B plus b guard','operations':[f'B.{v[0]}'for v in new_ops]+['b_absent','b_short_circuit'],'count':16},{'id':'S3','load':'a guard then TA','operations':['a_present','a_short_circuit']+[f'TA.{v[0]}'for v in new_ops],'count':16},{'id':'S4','load':'TB then result','operations':[f'TB.{v[0]}'for v in new_ops]+['timestamp_order','result'],'count':16}],'G3_G4_boundary':'left==mid/right==end tail guards, output transfer/loop work stay G4; every actual pair comparison load, its offset/cast/received and the six result predicates stay G3','contract_requirement':'every source operation/complete move exactly once;<=16 scalar/group and one fixed<=128-byte copy/group; no optimizer elision or cross-group credit','chosen_atomization_qualification':'Complete Range constructor/index argument, full shared view/receiver and scalar/pointer Option/reference source->received edges each count one favorable named scalar primitive. Binding contract does not formalize this grammar; independent source review/root admission required. All sources/received places named, no split-layer is silently removed from old helper.','no_product_change_or_execution':True,'bound_accepted':False})
save('value-and-lifetime-flow.json',{'schema':1,'target_sha256':sha(source),'old_value_edges':[{'type':'u64','from':'offset expression','to':'ld received at8'},{'type':'&[u8]16','from':'caller c shared/coerced view','to':'ld received b16'},{'type':'u64','from':'from_le_bytes return8','to':'ld received tail/return place8'},{'type':'u64','from':'ld return8','to':'a/b/comparator operand8'}],'new_value_edges':[{'type':'u64','from':'offset expression','to':'block local at8'},{'type':'u64','from':'from_le_bytes return8','to':'a/b/comparator operand8'}],'unchanged_complete_edges':['Range16 source/index received','shared slice view16 source/receiver','Option<&[u8;8]>8 source/received','&[u8;8]8 expect-return/received','array8 dereference source/from_le_bytes parameter received'],'no_new_function_return_or_call_argument_layer':'macro expands expression in the current comparator; no runtime comparison_word function exists','new_at_birth_drop':'each macro expansion has one8-byte block-local at; offset evaluated once; drops at that block end before next load or mutation','source_array_lifetime':'temporary8-byte value consumed as from_le_bytes argument before scalar return; no borrowed array exported','candidate_loan':'shared read borrow only within comparison expression; ends before mutable c.copy_within278','read_order':['index a','index b','b==ABSENT || short-circuit','a!=ABSENT && short-circuit','timestamp[a]','timestamp[b]','<=','take_left received'],'eligibility':'b==MAX skips all timestamp loads; otherwise a==MAX skips all timestamp loads. Legitimate timestampMAX is still data; equal timestamps retain left preference.','forbidden_claims':['no compiler optimization assumed','no changed logical read or short-circuit ordering','no full memory-role union claimed by this local table','no implementation/test/qualification acceptance'],'lifetime_proof_accepted':False})
save('input-bindings.json',{'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'target':{'path':str(source.relative_to(REPO)),'sha256':sha(source)},'selection':{'path':'verification/swift-semantic-adapter-root-review/accounting-correction-selection.json','sha256':sha(REPO/'verification/swift-semantic-adapter-root-review/accounting-correction-selection.json')},'contract':{'path':'docs/swift-semantic-adapter-prerequisite.md','sha256':sha(REPO/'docs/swift-semantic-adapter-prerequisite.md'),'lines':[244,265]},'basis':'producer-derived source flow and approved prior accounting deficiency inputs only; no active G3 independent review inspected','implemented_or_executed':False,'proposal_selected':False})
print('G3_PROPOSAL old70scalar+4copy vs proposed62scalar+4copy; qualified atomization, unselected/unexecuted')
