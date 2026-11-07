#!/usr/bin/env python3
"""Source-only field-grain audit of one safe immutable-word-view candidate.
No product, compiler, fixture/model/runtime execution. Network reads official
platform source only; all output is confined to this new proof directory.
"""
import datetime,hashlib,itertools,json,pathlib,re,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(ROOT/n).write_text(json.dumps(v,indent=2)+'\n')
source=REPO/'verification/swift-cache-state-implementation/correction-2/source/library/cache_state.rs'
assert sha(source)=='6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00'
review=REPO/'verification/swift-cache-state-g3-independent-review/proposal2/seal.json';assert sha(review)=='9f5b1779b4bcdeda9070df047682723848c3bcd6361d8bcd5e5b189782c0e2c0'
for m in json.loads(review.read_text())['members']:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
baselines=[]
for rel,expected in [
 ('verification/swift-cache-state-implementation/candidate-repo-seal.json','caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'),
 ('verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json','b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6'),
 ('verification/swift-cache-state-implementation/correction-2/candidate-repo-seal.json','26e6ece9d86f054a57e335c6b170595aa1d21e3081b45db4eda167e59abe52fb')]:
 p=REPO/rel;assert sha(p)==expected;j=json.loads(p.read_text())
 for m in j['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes'] and sha(q)==m['sha256']
 baselines.append({'path':rel,'sha256':expected,'members_verified':len(j['members']),'member_bytes_verified':sum(m['bytes']for m in j['members'])})
# Fetch, hash and inspect exact recorded compiler's official platform source.
# Preserve identity/ranges only, not a copy of unrelated external implementation.
commit='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
url=f'https://raw.githubusercontent.com/rust-lang/rust/{commit}/library/core/src/slice/mod.rs'
with urllib.request.urlopen(url,timeout=15)as f:
 raw=f.read(512*1024+1);assert len(raw)<=512*1024 and f.status==200
 std=raw.decode();final_url=f.url
assert final_url==url
stdlines=std.splitlines()
def platform_fn(name):
 a=next(i for i,l in enumerate(stdlines)if re.search(r'pub const (?:unsafe )?fn '+name+r'\b',l));depth=0;seen=False
 for j in range(a,len(stdlines)):
  s=re.sub(r'"(?:\\.|[^"\\])*"','""',stdlines[j].split('//')[0])
  for c in s:
   if c=='{':depth+=1;seen=True
   elif c=='}':depth-=1
  if seen and depth==0:
   body='\n'.join(stdlines[a:j+1]);return {'name':name,'first_line':a+1,'last_line':j+1,'function_sha256':hashlib.sha256(body.encode()).hexdigest()}
 raise ValueError(name)
funcs=[platform_fn(n)for n in ['as_chunks','as_chunks_unchecked','split_at_unchecked','as_chunks_mut','as_chunks_unchecked_mut','split_at_mut_unchecked']]
assert 'self.split_at_unchecked(len_rounded_down)'in std and 'multiple_of_n.as_chunks_unchecked()'in std
save('official-api-assumptions.json',{'schema':1,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exact_compiler_platform_source':{'commit':commit,'url':url,'final_url':final_url,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'functions':funcs},'prior_compiler_identity_receipt':{'path':'verification/swift-cache-state-implementation/correction-2/evidence/rust-version.stdout','sha256':sha(REPO/'verification/swift-cache-state-implementation/correction-2/evidence/rust-version.stdout')},'official_API_reference':'https://doc.rust-lang.org/std/primitive.slice.html#method.as_chunks','API_facts':['safe immutable borrowed chunks plus remainder; no element allocation/copy','stable since Rust1.88; N8 nonzero','returned tuple contains two fat references, not one scalar','exact commit source invokes split_at_unchecked then as_chunks_unchecked internally','internal unsafe is platform implementation; proposed application fragment uses no unsafe'],'API_semantic_assumptions_not_compile_qualification':True,'external_source_not_executed':True})
old='''                    let a = ld(c, src + left * 8);
                    let b = ld(c, src + right * 8);
                    b == ABSENT || (a != ABSENT && ld(c, a as usize * 8) <= ld(c, b as usize * 8))
'''
assert old in source.read_text();(ROOT/'old-fragment.txt').write_text(old)
old_first_line=source.read_text()[:source.read_text().index(old)].count('\n')+1
new='''                    let (words, _) = c.as_chunks::<8>();
                    let a = u64::from_le_bytes(words[src / 8 + left]);
                    let b = u64::from_le_bytes(words[src / 8 + right]);
                    b == ABSENT
                        || (a != ABSENT
                            && u64::from_le_bytes(words[a as usize])
                                <= u64::from_le_bytes(words[b as usize]))
'''
(ROOT/'explored-fragment.txt').write_text(new)
# Every item below is one scalar word, predicate, explicit arithmetic operation
# or indexed address; no Range16 or fat-view16 is charged as one scalar.
view=[
 ('V01','thin shared Candidate receiver reborrow',1),
 ('V02','byte-slice receiver source pointer field',1),
 ('V03','byte-slice receiver source length field',1),
 ('V04','byte-slice pointer source->as_chunks received field',1),
 ('V05','byte-slice length source->as_chunks received field',1),
 ('V06','N!=0 predicate',1),
 ('V07','nonzero assert conditional branch',1),
 ('V08','read self length for rounding expression',1),
 ('V09','length /8',1),
 ('V10','rounded word count *8',1),
 ('V11','rounded byte-length initializer->local binding',1),
 ('V12','split_at_unchecked receiver pointer field transfer',1),
 ('V13','split_at_unchecked receiver length field transfer',1),
 ('V14','rounded byte-length->split received mid scalar',1),
 ('V15','split tuple front pointer->multiple_of_n binding',1),
 ('V16','split tuple front length->multiple_of_n binding',1),
 ('V17','split tuple remainder pointer->remainder binding',1),
 ('V18','split tuple remainder length->remainder binding',1),
 ('V19','outer tuple chunks pointer field construction',1),
 ('V20','outer tuple chunks length field construction',1),
 ('V21','outer tuple remainder pointer field construction',1),
 ('V22','outer tuple remainder length field construction',1),
 ('V23','outer return tuple chunks pointer->caller received',1),
 ('V24','outer return tuple chunks length->caller received',1),
 ('V25','outer return tuple remainder pointer->caller received',1),
 ('V26','outer return tuple remainder length->caller received',1),
 ('V27','received chunks pointer->words pattern binding',1),
 ('V28','received chunks length->words pattern binding',1),
]
load=[('receiver_ptr','words pointer field->Index received'),('receiver_len','words length field->Index received'),('index_arg','usize index source->received'),('bound','index<len predicate'),('address','indexed element address'),('reference','thin array reference source->received dereference'),('LE','from_le_bytes conversion'),('conversion_return','u64 conversion source->received initializer/operand')]
loads=[{'id':'A','offset':[('A.div','src/8'),('A.add','plus left')],'reads':'bytes[8*(src/8+left)..+8]','executes':'first always'}, {'id':'B','offset':[('B.div','src/8'),('B.add','plus right')],'reads':'bytes[8*(src/8+right)..+8]','executes':'second always'}, {'id':'TA','offset':[('TA.cast','a as usize')],'reads':'timestamp bytes at8*a','executes':'after b!=MAX and a!=MAX'}, {'id':'TB','offset':[('TB.cast','b as usize')],'reads':'timestamp bytes at8*b','executes':'after TA under same guards'}]
ops=[]
for v in loads:
 ops += [{'id':id,'name':name,'units':1}for id,name in v['offset']]
 ops += [{'id':v['id']+'.'+id,'name':name,'units':1}for id,name in load]
 if v['id']in['A','B']:ops.append({'id':v['id']+'.binding','name':'initializer8->named u64 binding8','units':1})
pred=[('P1','b==MAX'),('P2','|| short-circuit branch'),('P3','a!=MAX'),('P4','&& short-circuit branch'),('P5','timestamp_a<=timestamp_b'),('P6','comparison bool source->take_left received')]
ops += [{'id':id,'name':name,'units':1}for id,name in pred]
assert len(ops)==46 and len(view)==28
save('field-operation-lower-core.json',{'schema':1,'target_source_sha256':sha(source),'variant':'one safe word-slice borrow scoped to each actual comparison','scalar_grain':'one usize/pointer/u64/bool field transfer or predicate/arithmetic/address operation; no whole Range/fat view as one scalar','view_operations':[{'id':id,'name':name,'units':n}for id,name,n in view],'view_lower_core_scalar_count':28,'loads':loads,'load_and_predicate_operations':ops,'load_and_predicate_scalar_count':46,'total_scalar_lower_core':74,'array_payload_copies':4,'minimum_groups_under_this_field_core':9,'selected_comparison_groups':8,'not_a_complete_upper_bound':True,'omitted_additional_normal_path_work':['split_at_unchecked tuple construction/function return source->received fields before pattern binding','all split_at_unchecked internal pointer/length arithmetic and precondition work','as_chunks_unchecked receiver fields, return view fields, initializer binding and internal metadata/precondition work','standard Index receiver reborrow, bounds branch and further pointer metadata reads if separate','any additional aggregate/argument/returned value not represented by these lower-core edges'],'const_generic_sensitivity':'Even omitting V06/V07 entirely,72 scalars +4 copies require9 groups. This does not invoke constant folding to claim a bound.','unconditional_machine_or_runtime_overrun_asserted':False,'source_bound_accepted':False})
# Exhaust every permitted fixed-copy replacement for the explicitly named
# existing transfer objects. A copy replaces only those field-transfer edges,
# never scalar metadata construction/arithmetic/guards, and has its own group.
transfers=[('byte_receiver',2),('split_front_binding',2),('split_remainder_binding',2),('outer_constructor_chunks',2),('outer_constructor_remainder',2),('outer_return_tuple',4),('word_binding',2)]+[(v['id']+'_Index_receiver',2)for v in loads]
choices=[]
for flags in itertools.product([False,True],repeat=len(transfers)):
 scalars=74-sum(n for (_,n),f in zip(transfers,flags)if f);copies=4+sum(flags);groups=copies+(scalars+15)//16
 choices.append({'fixed_copy_substitutions':[id for (id,_),f in zip(transfers,flags)if f],'scalars':scalars,'copies':copies,'groups':groups})
minimum=min(r['groups']for r in choices);assert minimum==9
save('copy-alternative-check.json',{'schema':1,'eligible_existing_transfer_objects':[{'id':id,'field_scalars_replaced':n,'complete_copy_bytes':8*n,'fixed_copy_groups_if_chosen':1}for id,n in transfers],'enumerated_choices':len(choices),'minimum_lower_core_groups':minimum,'minimum_choices':[r for r in choices if r['groups']==minimum],'all_other_choices_above_minimum':True,'single_scalar_transfer_copy_choices':'Replacing one8-byte scalar transfer with one fixed copy adds one group and removes at most one scalar operation; it cannot improve the minimum. No one whole copy replaces different noncontiguous source values or independent operand calls.','method':'exhaustive static integer partition check; not product/model/runtime execution or a performance counter','copy_source_and_destination':'each substitution has complete source and received object; it cannot also retain its replaced scalar fields or share one of the four data-array copy groups','constructor_caveat':'Metadata constructor field writes V02/V03 and V19..V22 are not made free by copying the constructed aggregate later. No contiguous pre-existing32-byte source is invented for distinct tuple fields.','not_global_impossibility':'This only rejects the exact explored fragment under this source-bound field core; other structural designs require their own proof.'})
save('value-layout-lifetime-map.json',{'schema':1,'new_places':[{'name':'shared thin Candidate receiver','type':'&Candidate2048','complete_source_received_bytes_at_least':16,'birth_drop':'word-view call only'},{'name':'byte slice receiver','type':'&[u8]','complete_source_received_bytes_at_least':32,'birth_drop':'input view creation through as_chunks call'},{'name':'split result tuple','type':'(&[u8],&[u8])','complete_source_received_bytes_at_least':64,'birth_drop':'internal split return and tuple-pattern receive; no payload byte copies'},{'name':'multiple_of_n/remainder','type':'two shared slices','complete_source_received_bytes_at_least':64,'birth_drop':'as_chunks internal locals until outer tuple return'},{'name':'array_slice','type':'&[[u8;8]]','complete_source_received_bytes_at_least':32,'birth_drop':'as_chunks_unchecked return/local until outer tuple construction'},{'name':'outer view tuple','type':'(&[[u8;8]],&[u8])','complete_source_received_bytes_at_least':64,'birth_drop':'as_chunks return->caller tuple-pattern receive'},{'name':'words binding','type':'&[[u8;8]]','complete_source_received_bytes_at_least':32,'birth_drop':'received chunks fields move into words; lives actual comparison block only'},{'name':'Index receiver per actual load','type':'&[[u8;8]]','complete_source_received_bytes_at_least':32,'birth_drop':'one load Index call; two pointer/length fields named separately'},{'name':'array reference per load','type':'&[u8;8]','complete_source_received_bytes_at_least':16,'birth_drop':'Index return through array dereference'},{'name':'array payload per load','type':'[u8;8]','complete_source_received_bytes_at_least':16,'birth_drop':'dereference source->from_le_bytes argument; one distinct copy'},{'name':'decoded scalar per load','type':'u64','complete_source_received_bytes_at_least':16,'birth_drop':'conversion return->initializer/operand'},{'name':'a/b initializer and binding','type':'u64 each','complete_source_received_bytes_at_least':16,'birth_drop':'initializer ends after each statement; a/b bindings persist through guard/comparison'},{'name':'left timestamp operand','type':'u64','complete_source_received_bytes_at_least':8,'birth_drop':'must remain while right timestamp load executes'},{'name':'comparison result','type':'bool','complete_source_received_bytes_at_least':2,'birth_drop':'result->take_left; no reference escapes'}],'layout_status':'64-bit source field arithmetic/lower bounds only. Fat references have pointer+length; tuple holds two such values. No new compiler layout measurement or complete role-union proof. Padding/additional owners cannot reduce the lower-core obstacle.','loan':'shared words borrows exactly the existing Candidate; no new buffer, native u64 alias, allocation, unsafe user code or adopted FD. All view/Index borrows end at comparison-block end before G4 c.copy_within.','read_order':['metadata-only view formation, no payload read','index a','index b','bMAX ||','aMAX &&','timestamp a','timestamp b','<=','result'],'byte_equivalence':'src is512/1024 so8*(src/8+left/right)==src+8*left/right. Eligible a,b are0..63; MAX guards unchanged. Decode remains LE, timestampMAX is valid data, equality chooses left.','panic_notes':'New nonzero-chunk check cannot fail at literal8; shared Index bounds preserve panic on out-of-range. Exact panic text/type location may differ and is not admitted. No panic or runtime branch was executed.','full_lifetime_or_29344_proof_accepted':False})
save('input-bindings.json',{'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),'target_source':{'path':str(source.relative_to(REPO)),'sha256':sha(source),'old_fragment_lines':[old_first_line,old_first_line+2]},'review':{'path':str(review.relative_to(REPO)),'sha256':sha(review),'members_verified':13},'contract':{'path':'docs/swift-semantic-adapter-prerequisite.md','sha256':sha(REPO/'docs/swift-semantic-adapter-prerequisite.md'),'lines':[244,265]},'baselines_verified':baselines,'old_packets_unchanged':True,'no_product_or_compiler_or_fixture_or_native_execution':True,'no_Git_or_process_inventory':True,'repair_selected':False,'source_accounting_accepted':False})
print(json.dumps({'exact_platform_source_sha256':hashlib.sha256(raw).hexdigest(),'view_lower_core':28,'body_lower_core':46,'total_scalar_lower_core':74,'copies':4,'minimum_with_all_copy_alternatives':minimum,'selection_bound':8,'no_valid_bound_for_explored_fragment':True,'product_unchanged':True},indent=2))
