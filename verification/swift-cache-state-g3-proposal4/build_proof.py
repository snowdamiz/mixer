#!/usr/bin/env python3
"""Source-only component audit; never compiles/imports/executes Rust snippets."""
import datetime,hashlib,json,pathlib,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,j):(ROOT/n).write_text(json.dumps(j,indent=2)+'\n')
verified=[]
for rel,expected in [
 ('verification/swift-cache-state-implementation/candidate-repo-seal.json','caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'),
 ('verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json','b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6'),
 ('verification/swift-cache-state-implementation/correction-2/candidate-repo-seal.json','26e6ece9d86f054a57e335c6b170595aa1d21e3081b45db4eda167e59abe52fb'),
 ('verification/swift-cache-state-g3-proposal3/seal.json','8bacc0355f35b504889784313ce070365f347262908bd3d416f26b2b6e11aa0b'),
 ('verification/swift-cache-state-g3-independent-review/proposal2/seal.json','9f5b1779b4bcdeda9070df047682723848c3bcd6361d8bcd5e5b189782c0e2c0')]:
 p=REPO/rel;assert sha(p)==expected;j=json.loads(p.read_text())
 for m in j['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
 verified.append({'path':rel,'sha256':expected,'members_verified':len(j['members']),'bytes_verified':sum(m['bytes']for m in j['members'])})
source=REPO/'verification/swift-cache-state-implementation/correction-2/source/library/cache_state.rs'
assert sha(source)=='6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00'
lines=source.read_text().splitlines();old='\n'.join(lines[245:287])+'\n';assert old.startswith('fn merge(')
(ROOT/'old-merge.txt').write_text(old)
explored=ROOT/'explored-merge.txt';text=explored.read_text();ls=text.splitlines()
def line(s):return next(i+1 for i,l in enumerate(ls)if s in l)
assert text.count('as_chunks_mut::<8>()')==1 and 'copy_within'not in text
assert text.count('u64::from_le_bytes')==4 and 'let mut out = base;'in text
assert 'words[dst + out] = words[src + left];'in text and 'words[dst + out] = words[src + right];'in text
commit='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
platform=[]
for name,expected in [('mod.rs','8026ddec62fb732d01dc6fcb700fbf109aa5dd94d2391387db3202f405669d43'),('index.rs',None)]:
 u=f'https://raw.githubusercontent.com/rust-lang/rust/{commit}/library/core/src/slice/{name}'
 with urllib.request.urlopen(u,timeout=15)as f:raw=f.read(512*1024+1);assert len(raw)<=512*1024 and f.status==200 and f.url==u
 h=hashlib.sha256(raw).hexdigest();assert expected is None or h==expected
 spans=[]
 for a,z,n in ([(1499,1512,'as_chunks_unchecked_mut'),(1555,1567,'as_chunks_mut'),(2101,2121,'split_at_mut_unchecked')]if name=='mod.rs'else[(8,31,'Index and IndexMut wrapper implementations'),(215,226,'usize SliceIndex intrinsic bodies')]):
  body='\n'.join(raw.decode().splitlines()[a-1:z]);spans.append({'name':n,'lines':[a,z],'sha256':hashlib.sha256(body.encode()).hexdigest()})
 platform.append({'url':u,'bytes':len(raw),'sha256':h,'spans':spans})
save('official-api-bindings.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'compiler_commit':commit,'official_source_hashes':platform,'references':[
 'https://doc.rust-lang.org/reference/expressions/array-expr.html#array-and-slice-indexing-expressions',
 'https://doc.rust-lang.org/reference/expressions/operator-expr.html#assignment-expressions',
 'https://doc.rust-lang.org/reference/expressions.html#place-expressions-and-value-expressions',
 'https://doc.rust-lang.org/std/primitive.slice.html#method.as_chunks_mut',
 'https://doc.rust-lang.org/std/primitive.slice.html#method.copy_within'],
 'facts':['usize indexing of a slice is built-in; no Index/IndexMut trait wrapper is invented for this fragment','assignment evaluates RHS before LHS; Copy array values are copied and assignment produces unit','chunk method returns borrowed mutable arrays and a disjoint remainder'],
 'not_compiled_or_executed':True,'not_a_machine_instruction_model':True})
index=[('ptr','read word-view data pointer component'),('len','read word-view element-length component'),('bound','usize index < length predicate'),('branch','normal bounds branch'),('scale','index * eight-byte element size'),('address','data pointer + scaled offset -> element place')]
loads={}
for tag,where,offset,binding in [('A','words[src + left]','src+left',True),('B','words[src + right]','src+right',True),('TA','words[a as usize]','a as usize',False),('TB','words[b as usize]','b as usize',False)]:
 rows=[{'id':tag+'.offset','operation':offset,'source_line':line(where),'scalar':1}]
 rows += [{'id':tag+'.'+id,'operation':name,'source_line':line(where),'scalar':1}for id,name in index]
 rows += [{'id':tag+'.LE','operation':'one fixed-width LE conversion (not an array copy)','source_line':line(where),'scalar':1},{'id':tag+'.return','operation':'from_le_bytes output u64 -> caller initializer/operand','source_line':line(where),'scalar':1}]
 if binding:rows.append({'id':tag+'.binding','operation':'initializer u64 -> actual a/b binding','source_line':line(where),'scalar':1})
 loads[tag]=rows
preds=[('b.absent','b == ABSENT',line('b == ABSENT')),('b.branch','|| short circuit',line('|| (a != ABSENT')),('a.present','a != ABSENT',line('|| (a != ABSENT')),('a.branch','&& short circuit',line('&& u64::from_le_bytes')),('order','timestamp a <= timestamp b',line('<= u64::from_le_bytes')),('bool.binding','comparison-expression bool -> take_left binding',line('let take_left ='))]
predrows=[{'id':id,'operation':s,'source_line':n,'scalar':1}for id,s,n in preds]
ops=loads['A']+loads['B']+predrows[:4]+loads['TA']+loads['TB']+predrows[4:]
assert len(ops)==44 and len({o['id']for o in ops})==44
save('G3-component-map.json',{'schema':1,'scope':'only actual comparison body, not whole G3 setup','operations':ops,'source_order_note':'A,B,b guard,a guard,TA,TB,order,binding; block stream preserves this order','payload_copies':[{'id':x+'.array','bytes':8,'source':'built-in indexed array place','received':'from_le_bytes by-value array parameter','groups':1}for x in ['A','B','TA','TB']], 'scalars':44,'copy_groups':4,'scalar_blocks':[{'id':f'S{i//16+1}','operations':[o['id']for o in ops[i:i+16]],'count':len(ops[i:i+16])}for i in range(0,len(ops),16)],'comparison_groups_in_disclosed_leaf_model':7,'max_comparisons':321,'comparison_total_upper_in_model':2247,'LE_leaf_model':'The required fixed-width LE conversion is one primitive; the four actual array arguments and all actual scalar outputs/bindings remain separate. Platform implementation internals of that conversion are not expanded as application-authored helpers.','builtin_index_note':'No fat Index call argument, Option, Range, reference-return or trait-wrapper call is created. Pointer and length components used by built-in access remain separate operations.','whole_G3_source_bound_accepted':False,'reason':'one-time chunk/helper/setup full upper remains unclosed; this comparison map alone does not qualify the proposed repair'})
core=[]
for tag in ['RHS','LHS']:
 core.append({'id':tag+'.offset','operation':'src+chosen side'if tag=='RHS'else'dst+out','scalar':1})
 core += [{'id':tag+'.'+id,'operation':name,'scalar':1}for id,name in index]
core += [{'id':id,'operation':s,'scalar':1}for id,s in [('side.add','chosen left/right+1'),('side.store','write chosen cursor'),('out.add','out+1'),('out.store','write out'),('loop.test','out<end for successful iteration'),('loop.branch','enter output body')]]
assert len(core)==20
for o in core:
 if o['id'].startswith(('RHS.','LHS.')):o['source_lines']=[line('words[dst + out] = words[src + left]'),line('words[dst + out] = words[src + right]')]
 elif o['id'].startswith('side.'):o['source_lines']=[line('left += 1;'),line('right += 1;')]
 elif o['id'].startswith('out.'):o['source_lines']=[line('out += 1;')]
 else:o['source_lines']=[line('while out < end')]
# A less fine address primitive combines scale+address only as sensitivity.
favorable=[o for o in core if not o['id'].endswith('.scale')]
assert len(favorable)==18
admin=[{'id':'select.left','operation':'left==mid','max_scalar':1},{'id':'select.left.branch','operation':'if normal branch','max_scalar':1},{'id':'select.right','operation':'right==end','max_scalar':1},{'id':'select.right.branch','operation':'else-if normal branch','max_scalar':1},{'id':'select.literal.binding','operation':'only exhausted-arm literal bool -> take_left; absent on comparison arm','max_scalar':1},{'id':'side.branch','operation':'if take_left branch','max_scalar':1}]
# Non-payload loop administration outside the per-output core, within G4.
outer=[('init',3,1,['64->src','128->dst','1->width']),('outer.guard',2,7,['width<64','while branch including final']),('base.init',1,6,['0->base']),('base.guard',2,69,['base<64','while branch,63 bodies+6 final']),('half.init',8,63,['base->left','base+width','sum->mid','2*width','base+product','sum->end','mid->right','base->out']),('output.final',2,63,['out<end','final loop branch only']),('base.store',1,63,['end->base']),('swap',3,6,['src->old_src','dst->src','old_src->dst']),('width',2,6,['width*2','store width'])]
outer_scalar=sum(n*k for _,n,k,_ in outer);assert outer_scalar==884
save('G4-component-obstacle.json',{'schema':1,'scope':'direct indexed word assignment + all selected cursor/output-loop work','always_per_transfer_core':core,'core_scalars':20,'favorable_combined_address_core_scalars':18,'favorable_core_operations':favorable,'always_payload_copy_groups_at_least':1,'copies_are_not_scalar_credit':True,'side_selection_operations':admin,'max_per_transfer_scalars_with_side_selection':26,'outer_administration':[{'id':id,'scalars_per_instance':n,'instances':k,'operations':ss,'scalar_total':n*k}for id,n,k,ss in outer],'outer_scalar_upper':outer_scalar,'max_transfers':384,'selected_groups':768,'lower_bound_under_main_component_model':{'scalar_core':20*384,'scalar_groups_even_if_packed_across_all_transfers':(20*384+15)//16,'copy_groups':384,'groups':864,'excess_over_selected':96},'lower_bound_with_favorable_single_address_operation':{'scalar_core':18*384,'scalar_groups_even_if_packed_across_all_transfers':(18*384+15)//16,'copy_groups':384,'groups':816,'excess_over_selected':48},'favorable_single_compound_update_sensitivity':'If each += is one operation instead of add+store, favorable core becomes16, but every output still evaluates at least left==mid, its branch, and if take_left branch:>=19 scalars/output, before other selection/final/outer work.','copy_grain_sensitivity':'The obstacle grants only one8-byte RHS->destination copy. A distinct RHS value->destination move adds work and cannot rescue it. No second array is assumed to establish the lower bound.','enumerated_component_inventory_ceiling_not_complete_source_upper':{'scalars':26*384+outer_scalar,'scalar_groups':(26*384+outer_scalar+15)//16,'if_one_payload_copy_per_assignment_groups':384+(26*384+outer_scalar+15)//16,'if_two_payload_movements_groups':768+(26*384+outer_scalar+15)//16},'normal_exit_unit_note':'Assignment/compound-update/block unit0 places are named in the lifetime map; they are not fictitious std calls or separately charged return boundaries. Arithmetic/store/index entries own their normal completion.','not_unconditional_runtime_or_machine_overrun':True,'component_model_not_independently_admitted':True,'full_source_upper_accepted':False})
save('custody.json',{'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),'target_source':{'path':str(source.relative_to(REPO)),'sha256':sha(source),'old_merge_lines':[246,287]},'explored_source':{'path':str(explored.relative_to(REPO)),'sha256':sha(explored)},'verified_old_packets':verified,'contract':{'path':'docs/swift-semantic-adapter-prerequisite.md','sha256':sha(REPO/'docs/swift-semantic-adapter-prerequisite.md'),'lines':[244,286]},'new_source_only_ownership':str(ROOT.relative_to(REPO))+'/**','product_compiler_runtime_fixture_execution':False,'native_UI_capture_process_inventory_Git_mutation':False,'repair_selected_for_product':False,'source_accounting_accepted':False,'lifetime_proof_accepted':False})
print(json.dumps({'G3_comparison_model':{'scalars':44,'copies':4,'groups':7,'whole_G3_closed':False},'G4_favorable_core':{'scalars_per_output':18,'copy_groups_per_output_at_least':1,'all384_global_lower_groups':816,'cap':768},'G4_main_core':{'scalars_per_output':20,'all384_global_lower_groups':864},'source_only':True,'all_old_packets_unchanged_verified':True,'acceptance':False},indent=2))
