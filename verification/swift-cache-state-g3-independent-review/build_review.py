"""Independent static G3 proof validation only. No product/compiler/model execution."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE='verification/swift-cache-state-implementation/correction-1/source/library/cache_state.rs'
DOC='docs/swift-semantic-adapter-prerequisite.md'
OLD='verification/swift-cache-state-accounting-independent-review/seal.json'
EXPECTED={SOURCE:'1ffc4ee5bb37c4ca2794c456f66bfcd9f1916090a0de3a548c19b6c82a3767b9',DOC:'c818e47d15d541731df98cdf79032846cb4e4aa28aad2eee7e25ac36cb1c7f41',OLD:'706e1ab2a1caa6b14cf588d40545a086ea32fc1a7a23a7eb5c1b1f5a48dfacd8'}

def meta(path):
    data=(ROOT/path).read_bytes()
    return {'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2)+'\n')

for path,expected in EXPECTED.items():
    assert meta(path)['sha256']==expected,path
source=(ROOT/SOURCE).read_text().splitlines()
assert source[264].strip()=='let a = ld(c, src + left * 8);'
assert source[265].strip()=='let b = ld(c, src + right * 8);'
assert source[266].strip()=='b == ABSENT || (a != ABSENT && ld(c, a as usize * 8) <= ld(c, b as usize * 8))'

write('custody.json',{
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'python':sys.version,'git_version':'git version 2.56.0','rg_version':'ripgrep15.2.0',
    'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'verified_inputs':[meta(p) for p in EXPECTED],
    'prior_packet_preserved':'Old13-member seal hash verified; old members were not rewritten or reinterpreted as new execution evidence.',
    'root_reported_correction2_selection_sha256':'c083b9bc61b2728847392f070cf0ae38de9d0c72b159d083cf384c96ad23b249',
    'selection_custody_qualification':'Root-supplied authorization identity only. No path supplied; not independently read/verified here.24 literal commits/restores only; no G3 edit authorized.',
    'unread':'Active correction2 source/evidence writes; producer exact G3 proposal not yet received; hosted inspectors/drivers/rejectedWorkerV2/broad hosted harness.',
    'mutation_scope':'verification/swift-cache-state-g3-independent-review/**',
    'proof_inputs_only':True,'product_compiler_tests_models_native_ui_capture_process_inventory':False,
})

common=[
    ('H01',151,'at+8 endpoint arithmetic'),
    ('H02',151,'construct complete Range<usize> (one favorable operation for both fields and its source form)'),
    ('H03',151,'range start<=end predicate'),
    ('H04',151,'range end<=slice length predicate'),
    ('H05',151,'create complete shared slice view/borrow (one favorable operation)'),
    ('H06',152,'first_chunk::<8> length>=8 predicate'),
    ('H07',152,'first_chunk Option<&[u8;8]> source -> received value (one favorable complete-value transfer)'),
    ('H08',153,'expect Option tag predicate on successful Some path'),
    ('H09',153,'expect returned &[u8;8] source -> received borrowed array view'),
    ('H10',150,'LE decode in from_le_bytes'),
    ('H11',150,'from_le_bytes u64 return source -> ld received/tail-result value'),
    ('H12',154,'ld u64 return source -> merge received a/b or timestamp-operand value'),
]
sites=[
    ('L1',265,'a','left*8','src+offset'),
    ('L2',266,'b','right*8','src+offset'),
    ('L3',267,'left timestamp','a as usize','converted a*8'),
    ('L4',267,'right timestamp','b as usize','converted b*8'),
]
loads=[]
for ident,line,value,arith1,arith2 in sites:
    operations=[
        {'id':ident+'-A1','line':line,'operation':arith1,'scalar_units':1},
        {'id':ident+'-A2','line':line,'operation':arith2,'scalar_units':1},
        {'id':ident+'-A3','line':line,'operation':'caller complete slice reference -> ld b parameter (one favorable transfer; no extra reborrow/coercion operation charged)','scalar_units':1},
        {'id':ident+'-A4','line':line,'operation':'computed offset source -> ld at parameter','scalar_units':1},
    ]
    operations += [{'id':ident+'-'+i,'line':ln,'operation':op,'scalar_units':1} for i,ln,op in common]
    assert len(operations)==16
    loads.append({'id':ident,'caller_line':line,'received_value':value,'operations':operations,'scalar_core':16,
                  'payload_copy':{'groups':1,'bytes':8,'source':'dereferenced array behind successful first_chunk/expect reference','destination':'from_le_bytes by-value [u8;8] argument'},
                  'no_returned_LE_array':'from_le_bytes returns u64; no st-like LE-array return copy is introduced.'})

predicates=[
    {'id':'P1','line':267,'operation':'b==ABSENT predicate','scalar_units':1},
    {'id':'P2','line':267,'operation':'|| short-circuit branch on P1; false continues','scalar_units':1},
    {'id':'P3','line':267,'operation':'a!=ABSENT predicate','scalar_units':1},
    {'id':'P4','line':267,'operation':'&& short-circuit branch on P3; true continues','scalar_units':1},
    {'id':'P5','line':267,'operation':'left timestamp <= right timestamp predicate','scalar_units':1},
    {'id':'P6','line':268,'operation':'comparison result source -> received take_left value','scalar_units':1},
]
full=[op for load in loads for op in load['operations']]+predicates
assert len({op['id'] for op in full})==70
assert sum(op['scalar_units'] for op in full)==70
write('operation-table.json',{
    'schema':1,'source_sha256':EXPECTED[SOURCE],'model':'Explicit favorable source/value-flow atomization; conditional, not an implicit amendment of binding primitive definitions.',
    'loads':loads,'comparison_operations':predicates,'four_load_scalar_core':64,'comparison_scalar_core':6,'four_load_path_scalar_lower_core':70,
    'payload_copy_groups':4,'maximum_scalar_groups_available_under8':4,'maximum_named_scalars_available':64,
    'partition_test':{'possible':False,'reason':'70 distinct named operations cannot be partitioned into4 sets each of cardinality<=16; even arbitrary regrouping within comparison cannot cure the6-operation deficit.','scalar_groups_at_least':5,'total_groups_at_least':9},
    'zero_cost_same_width_cast_sensitivity':'Even granting both explicit u64->usize casts zero cost, contrary to this source-operation convention,68 remain>64.',
    'lower_core_omissions_not_free':[
        'extra scalar reads/coercions/reborrows beyond one favorable complete slice-argument transfer',
        'Range parameter movement into slice indexing beyond one complete constructor',
        'first_chunk method receiver transfer and Some construction beyond one favorable Option result movement',
        'expect method receiver movement, string-message argument transfer, success-reference extraction beyond one favorable returned-reference transfer',
        'any full fat-reference fields beyond one favorable complete view/transfer',
        'additional expression/boolean intermediate places or operand reads not already in named predicates'
    ],
    'not_complete9_group_upper_bound':True,'not_measured_runtime_overrun':True,
})

write('path-and-boundary-table.json',{
    'schema':1,'source_sha256':EXPECTED[SOURCE],
    'evaluation_order':[
        'G4 first tests left==mid (258). If true choose false without any G3 load.',
        'Otherwise G4 tests right==end (260). If true choose true without any G3 load.',
        'When both runs nonempty, G3 evaluates L1 index a completely, including ld return to a, then L2 index b completely, including ld return to b.',
        'Evaluate b==ABSENT. True short-circuits ||, choosing true; a eligibility and both timestamp loads are skipped.',
        'If b is eligible, evaluate a!=ABSENT. False short-circuits &&, choosing false; both timestamp loads are skipped.',
        'Only when both indices eligible, evaluate L3 left timestamp before L4 right timestamp, then <=. Equality chooses left, preserving stability.',
        'G3 result enters take_left. G4 tests it and recomputes chosen offset at270/274, advances selected cursor, then copy_within278.'
    ],
    'paths':[
        {'id':'T-left-empty','G3_loads':[],'G3_scalar_core':0,'G3_payload_copies':0,'result_owner':'G4 tail path'},
        {'id':'T-right-empty','G3_loads':[],'G3_scalar_core':0,'G3_payload_copies':0,'result_owner':'G4 tail path'},
        {'id':'B-absent','G3_loads':['L1','L2'],'G3_operations':['P1','P2','P6'],'G3_scalar_core':35,'G3_payload_copies':2},
        {'id':'A-absent-B-eligible','G3_loads':['L1','L2'],'G3_operations':['P1','P2','P3','P4','P6'],'G3_scalar_core':37,'G3_payload_copies':2},
        {'id':'both-eligible','G3_loads':['L1','L2','L3','L4'],'G3_operations':['P1','P2','P3','P4','P5','P6'],'G3_scalar_core':70,'G3_payload_copies':4}
    ],
    'G3_owns':[
        '265..267 actual index/timestamp address computations, ld scalar argument/result transfers, checked range/chunk/expect work,8-byte input copies and LE decodes',
        '267 eligibility predicates/short-circuit control, timestamp comparison, result transfer into take_left on actual comparison paths'
    ],
    'G4_owns':[
        '258 and260 run-empty tail predicates/branches, including paths with no comparison',
        '269 take_left branch;270/274 separate repeated chosen-source computation and at binding;271/275 cursor update;272/276 chosen-offset return/received;278 checked copy_within range/destination work and8-byte transfer',
        '246..257 and281..285 merge entry/local state, outer/pass/pair/output iteration creation/guards/advance/final tests, base=end, swap source/received references and width update, according to its complete transfer-loop proof'
    ],
    'no_cross_credit':'Neither G4 unused allowance nor fewer actual G3 comparisons purchases missing scalar operations for one actual four-load comparison. Identical offset text evaluated again in G4 is separate source work; no optimizer common-expression elimination is assumed.',
    'structural_count_scope':'Six-pass321 pair comparison and384 transfer maxima are inherited structural obligations; no sort model or executable sort was run. This packet does not close G4<=2 or global complete ledger.',
})

write('verdict-and-options.json',{
    'schema':1,'status':'G3 source proof blocked; no <=64 partition under explicit complete-value lower-core model',
    'source_sha256':EXPECTED[SOURCE],
    'binding_contract':{
        'path':DOC,'lines':[244,266],'sha256':EXPECTED[DOC],
        'mandatory':['G3 <=321 comparisons at8 groups each, total2568','each actual micro-operation/check/LE conversion/copy/value/return/caller move exactly once','<=16 named scalar operations/group and distinct fixed copies<=128 bytes/group','no cross-group spare credits, cap increase or implicit optimizer elision'],
        'not_formally_fixed':'Exact primitive grammar is not supplied. This review explicitly exposes its favorable source/value-flow atomization rather than claiming that70 is a universal machine-instruction count.'
    },
    'independent_result':'Four8-byte input-array copies plus70 named scalar lower-core operations.4 scalar groups hold64, so no partition exists in that explicit model; even arbitrary per-comparison pooling requires at least5 scalar+4 copy=9 groups. This is not a complete9-group bound or runtime measurement.',
    'mandatory_missing_mapping_blocker':'Regardless of primitive-grammar ambiguity, the inherited general8-group declaration contains no complete source-bound <=64 partition and cannot be accepted as proof. A differently compressed grammar requires explicit justification/acceptance, not omission of actual returned/received places.',
    'unselected_source_only_options':[
        {
            'id':'O1','scope':'Comparator-local source rewrite, preserving existing global ld helper and all other callers',
            'candidate':'Expose the four checked LE reads directly inside merge with explicit offset values and the same short-circuit sequence. Consider RangeFrom + first_chunk to avoid dynamic end arithmetic and one range predicate, while preserving successful8-byte access and failure safety.',
            'why':'Potentially removes merge->ld b/at argument and ld->merge return transfers plus redundant exact-range work. Merely text-inlining ld duplicates offset expressions or adds source/received bindings, so it is not itself a cost proof.',
            'required':'Produce exact proposed bytes with every Range/Option/reference/argument/return/binding move and a complete<=64 table for every eligible/absent path; preserve a,b evaluation and left timestamp before right; establish G4 remains unchanged and no additional helper/lifetime owner. No concrete<=64 bound accepted here.'
        },
        {
            'id':'O2','scope':'Dedicated comparison helper or narrower checked-load helper selected only after full map',
            'candidate':'A specialized comparison operation can absorb offset computations and eligibility handling while exposing exactly which generic ld layers disappear; a checked tail-slice + first_chunk read can reduce scalar checks without relying on compiler removal.',
            'why':'May replace nested generic load-call movement with fewer explicit source transfers. Helper addition also creates its own full arguments, return, ranges and options; these can erase savings.',
            'required':'Freeze precise implementation/proof first; account helper caller/received/result and complete lifetimes; show unchanged panic/fail-closed contracts and <=8 groups. A helper signature or opaque read primitive alone is not a fix.'
        },
        {
            'id':'O3','scope':'Representation/merge redesign if no local safe source rewrite closes8',
            'candidate':'Reduce actual repeated index->timestamp loads by changing the owned scratch/merge representation with an explicit source contract amendment inside unchanged caps.',
            'why':'Could reduce the number of loads rather than relabel their cost, but affects Candidate layout, sort transfers, prefix, zero-tail induction and work/lifetime accounting.',
            'required':'Broader root selection and complete G2/G3/G4/G5/G6/layout/lifetime proof. No extra Candidate, unassigned memory, cap raise, precomputed uncharged loads, or hidden source store. This is a fallback design option, not a narrow authorized edit.'
        }
    ],
    'current_authorization':'Root reported correction2 selection permits24 literal commit/restore copies only. No G3/helper edit is selected or authorized by this review.',
    'producer_proposal_custody':'No separately sealed producer exact proposal received/read for this packet. Any future proposal needs its own frozen review/amendment.',
    'next_gate':'Root selects concrete source repair only after complete named per-path scalar/copy and source/received/drop/peak proof; then separately admits compile/layout/API/behavior/private regression against its exact hash.',
    'runtime_tests':0,'product_compiler_harness_model_execution':False,
    'implementation_accepted':False,'repair_selected':False,
    'limitations':['Source-only conditional cost proof; no actual stack/RSS/runtime/target or release measurement.','No active correction2 writes inspected; original candidate/correction1/old independent packet remain immutable.','G4 and other semantic groups, full lifetime union and final product gates remain open.','No native/UI/capture/simulator/emulator/phone runs or process inventory.']
})

excerpts=['# Frozen source and binding cost excerpts\n\nSource custody and hashes: custody.json. Text evidence only.\n']
for lo,hi in [(149,164),(238,287)]:
    excerpts.append('\n```text\n'+'\n'.join(f'{i}: {source[i-1]}' for i in range(lo,hi+1))+'\n```\n')
doc=(ROOT/DOC).read_text().splitlines()
excerpts.append('\n## '+DOC+'\n\n```text\n'+'\n'.join(f'{i}: {doc[i-1]}' for i in range(244,267))+'\n```\n')
(HERE/'source-excerpts.md').write_text(''.join(excerpts))
(HERE/'README.md').write_text('''# Independent G3 source review

No complete eight-group comparison proof is accepted. A favorable explicit
source/value-flow map gives16 scalar operations for each of four actual ld
calls, then6 for eligibility, short circuit, timestamp comparison and the
received result:70 scalars plus four distinct8-byte payload copies. Four scalar
groups hold64. No <=64 partition exists in that model; at least9 total groups
are needed as a lower bound. Additional omitted argument/view/Option work is
not free, and9 is not a complete upper bound.

The binding contract fixes exact-once work mapping,8 groups/comparison,16 named
scalar operations/group, fixed copies<=128 bytes and unchanged caps. It does
not define a formal primitive grammar. The70 result is conditional on the
explicit favorable atomization, not a machine/runtime measurement. The existing
unexpanded8-group claim is insufficient independently of that qualification.

`operation-table.json` names every lower-core operation and scalar return
boundary. `path-and-boundary-table.json` preserves short-circuit order and G3/G4
ownership. `verdict-and-options.json` describes unselected source repair options
and their proof conditions. Simple textual inlining is not a closed fix.

No separately sealed exact producer proposal was received/read. The active
correction2 source was not inspected. Root's existing selection covers only
24 literal commit/restore copies; this packet authorizes no G3/helper change.

Reproduce only the static source/proof checks:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/verify_review.py
```

The builder writes only this directory; rebuilding changes custody time/HEAD
and requires resealing. The verifier validates the frozen packet and arithmetic.
No product/compiler/harness/model/native/device execution or process inventory
occurred. Source-work, complete lifetime, runtime and implementation acceptance
remain blocked. Root owns source selection and delivery.
''')
PROPOSAL='verification/swift-cache-state-implementation/correction-2/g3-proposal/'
proposal_seal=meta(PROPOSAL+'seal.json')
assert proposal_seal['sha256']=='e57b30d5ef4ab540f98e8fa60d324c9497b5d0afeeb001c09c5ec549ebd1768b'
proposal_manifest=json.loads((ROOT/PROPOSAL/'seal.json').read_text())
proposal_members=[]
for m in proposal_manifest['members']:
    assert meta(m['path'])==m,m['path']
    proposal_members.append(m)
assert len(proposal_members)==8 and sum(x['bytes'] for x in proposal_members)==25104
proposed=(ROOT/PROPOSAL/'proposed-fragment.txt').read_text()
old=(ROOT/PROPOSAL/'old-fragment.txt').read_text()
assert old.strip()=='\n'.join(source[264:267]).strip()
assert proposed.count('$offset')==2 # matcher plus one transcription, not two runtime uses
assert proposed.count('comparison_word!')==4
assert 'let at = $offset;' in proposed
assert '.expect("proved eight-byte range")' in proposed
(HERE/'proposed-fragment.txt').write_text(proposed)

new_core=[
    ('offset1','first caller multiplication or explicit usize cast'),
    ('offset2','second caller addition or multiplication'),
    ('at_binding','computed offset source -> block-local at:usize received'),
    ('end','at+8'),
    ('range','complete Range<usize> constructor/index argument source->receive; explicit favorable atomic primitive'),
    ('range_order','start<=end'),
    ('range_end','end<=Candidate length'),
    ('view','shared c indexing reborrow, complete slice view and first_chunk receiver; explicit favorable atomic primitive'),
    ('chunk','first_chunk::<8> length predicate'),
    ('option','complete Option<&[u8;8]> source -> expect received self value'),
    ('expect_tag','expect Some tag test'),
    ('array_ref','expect returned &[u8;8] source -> received dereference operand view'),
    ('LE','from_le_bytes LE conversion'),
    ('conversion_receive','from_le_bytes returned u64 source -> outer initializer/operand temporary received'),
]
new_ops={}
for load in ['A','B','TA','TB']:
    for ident,text in new_core:
        new_ops[load+'.'+ident]={'operation':text,'scalar_units':1}
for ident,text in [('A.init_binding','A initializer temporary -> a:u64 identifier binding'),('B.init_binding','B initializer temporary -> b:u64 identifier binding'),('b_absent','b==ABSENT'),('b_branch','|| short-circuit'),('a_present','a!=ABSENT'),('a_branch','&& short-circuit'),('order','timestamp_a<=timestamp_b'),('result','comparison bool source -> take_left binding')]:
    new_ops[ident]={'operation':text,'scalar_units':1}
ordered=[*['A.'+i for i,_ in new_core],'A.init_binding',*['B.'+i for i,_ in new_core],'B.init_binding','b_absent','b_branch','a_present','a_branch',*['TA.'+i for i,_ in new_core],*['TB.'+i for i,_ in new_core],'order','result']
assert len(ordered)==64 and set(ordered)==set(new_ops)
blocks=[{'id':'S'+str(i+1),'operations':ordered[i*16:(i+1)*16],'count':16} for i in range(4)]
assert len({op for block in blocks for op in block['operations']})==64
write('proposal-disposition.json',{
    'schema':1,'status':'macro flow plausible; conservative64 core partition established; complete bound and implementation not accepted',
    'proposal_seal':proposal_seal,'proposal_members_verified':proposal_members,
    'proposal_source_target_sha256_as_sealed_not_current_source_verified':'6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00',
    'exact_current_source_not_read':'Only admitted frozen proposal text and correction1 source were read, not active correction2 product writes.',
    'syntax_hygiene_and_order':[
        'The macro is an item declaration inside the comparison else-block; defining it has no runtime function/closure/capture-owner construction.',
        'The transcriber contains exactly one $offset use, in let at=$offset. Offsets evaluate exactly once. Four invocation sites preserve A then B then the same ||/&& guards then TA before TB and <=.',
        'The literal c identifier resolves to the enclosing merge parameter at the macro definition site. Introduced at bindings are hygienic and separate per expansion; they do not capture/rebind a/b/src/left/right.',
        'The transcriber outer delimiter contains one expression block; no extra runtime macro invocation frame exists. The final from_le_bytes call has no semicolon and supplies that block value.',
        'Range indexing the byte Candidate requires Range<usize>; at and all offset expressions are usize. src/left/right are correspondingly inferred usize, while a/b and decoded timestamps are u64. The producer value-flow labels offset as u64 and must be corrected; equal64-bit width is not a type argument.',
        'c remains the same &mut Candidate2048 owner. Indexing creates an implicit shared reborrow and slice view for each read; no captured closure, by-value Candidate, or runtime b slice parameter is created. That shared receiver belongs to view, not zero work.',
        'Only successful decoded u64 escapes each expansion. Offset local and borrowed Range/Option/reference/array operands end at their expression/block scopes; shared borrows end before c.copy_within278. Operand temporaries, including TA while TB evaluates, remain named lifetime owners.'
    ],
    'block_tail_decision':{
        'intrinsic_extra_u64_forwarding_place':False,
        'reason':'An ordinary expression block has the type/value of its final operand. Here that operand is a call value, not a named local moved out. The block adds neither function output location, constructor nor u64 local. It therefore introduces no extra tail-to-block function return edge. This is a source-expression classification, not assumed compiler copy elimination.',
        'received_place_caveat':'A/B let initializers are place contexts and identifier patterns bind by copy/move. Conservatively name each outer initializer temporary and its separate a/b binding; the conversion return reaches that initializer temporary and one extra transfer initializes the binding. Timestamp conversion returns reach comparison operand temporaries. No unassigned value disappears.',
        'consistency_rule':'Apply the same expression-composition rule to ordinary blocks and cache_body!: a macro alone creates no forwarding function Result. Still account every real constructor/Ok payload, initializer or operand temporary, local binding, function output and immediate caller Result. A tail containing a named owned local would entail its actual move; no general macros-have-no-moves rule is asserted.',
        'binding_atomization_limit':'Rust language semantics distinguish value/place/function boundaries but do not define the debit grammar. Root must accept the explicit primitive partition; neither Reference nor this reviewer supplies an optimizer/runtime bound.'
    },
    'independent_conservative_core':{
        'operations':new_ops,'ordered_operations':ordered,'scalar_blocks':blocks,
        'scalars':64,'copies':4,'candidate_groups':8,
        'producer62_difference':'Add distinct A and B initializer->identifier binding transfers. Partition shifts B.offset1 into S1; all four blocks contain16. No operation is assigned twice.',
        'block_sizes':[16,16,16,16],
        'complete_upper_bound':False,
        'path_core_totals':{'B_absent':33,'A_absent_B_eligible':35,'both_eligible':64}
    },
    'remaining_explicit_source_edges':[
        {'id':'M1..M4','where':'every .expect("proved eight-byte range")','type':"&'static str",'edge':'constant string-reference source -> expect msg parameter received','why':'Literal identity is constant, but the method still has a distinct msg argument. The named expect_tag/Option/reference rows do not explicitly own this transfer. A generic constants-are-free claim is insufficient.','effect_if_separate_scalar_transfer_each':4,'conditional_total_with_core':68},
        {'id':'RANGE_VIEW','where':'range constructor/index receiver and slice/first_chunk receiver','edge':'all complete source/received/coercion/reborrow fields','why':'64 core groups these into favorable named primitives. Show exact source places and root acceptance of this atomization; splitting any additional operation exhausts the current capacity.'},
        {'id':'LIFETIME','where':'macro at, A/B initializers/bindings, TA/TB operands and preexisting helpers','edge':'birth/drop/peak assignment','why':'No automatic extra function result, but actual operand/initializer/temp/borrow owners must enter fixed helper192/merge144/leaf/Option/wire role map; no full29344 proof supplied.'},
        {'id':'ACTUAL_BYTES','where':'implementation','edge':'selected exact source -> fresh admitted host evidence','why':'Conceptual syntax review is not compilation, API/layout or actual comparison/borrow behavior acceptance.'}
    ],
    'minimal_additional_unselected_option':'A separately sealed macro amendment using .unwrap() rather than .expect(message) removes the explicit message argument while retaining a Some/None check and same successful read. Internal panic text changes; fail-closed behavior and complete source/lifetime partition must be reviewed. No such amendment is selected here.',
    'G3_G4_disjointness':'Same boundaries as path-and-boundary-table.json. The macro changes comparison reads only; G4 tail checks/repeated chosen-offset/index-advance/copy/loop work still needs its own unchanged2-group proof. No spare G4 credit is transferred.',
    'semantic_concept_supported':True,'cost_bound_accepted':False,'full_lifetime_accepted':False,'implementation_accepted':False,'repair_selected':False,'runtime_tests':0,
})

references=[
    {'url':'https://doc.rust-lang.org/reference/expressions/block-expr.html','sections':['expr.block.value-trailing-expr','expr.block.value'],'use':'A block adopts its final operand value/type and evaluates that operand in value context. This supports no separate function boundary, but says nothing about debit units.'},
    {'url':'https://doc.rust-lang.org/reference/expressions.html','sections':['expr.place-value.place-context','expr.move.copy','expr.temporary','expr.operand-order'],'use':'Let initializers are place contexts; value expressions can require temporaries. Copy values in identifier/operand flows remain owners. Comparison operands are evaluated left to right.'},
    {'url':'https://doc.rust-lang.org/reference/patterns.html','sections':['patterns.ident.move'],'use':'Identifier patterns bind by copying or moving. This motivates explicit A/B initializer-to-binding edges.'},
    {'url':'https://doc.rust-lang.org/reference/macros-by-example.html','sections':['macro.decl.hygiene'],'use':'Definition-site local resolution captures c; expansion-local at bindings are separate. Macro syntax expansion creates no function or closure owner.'},
    {'url':'https://doc.rust-lang.org/reference/expressions/return-expr.html','sections':['expr.return.behavior'],'use':'Function return semantics include a designated function output location and control transfer. Ordinary expression blocks do not add that function boundary.'},
    {'url':'https://doc.rust-lang.org/std/option/enum.Option.html#method.expect','sections':['method.expect'],'use':'The official signature has self and msg:&str parameters. Each message source/received argument requires an accounting disposition even on Some.'}
]
write('language-reference-basis.json',{'schema':1,'retrieved_at':datetime.now(timezone.utc).isoformat(),'tool':'web.run via functions.exec','sources':references,'primary_specifications_only':True,'no_compiler_execution':True,'qualification':'Current official Reference/std documentation reviewed for language/API semantics. No compiler-version-specific layout or generated instructions measured.'})
custody=json.loads((HERE/'custody.json').read_text())
custody['admitted_proposal_seal']=proposal_seal
custody['admitted_proposal_members_verified']=8
custody['admitted_proposal_member_bytes']=25104
custody['unread']='Active correction2 source/evidence writes; hosted inspectors/drivers/rejectedWorkerV2/broad hosted harness.'
custody['selection_custody_qualification']='Root-supplied authorization identity, also named by admitted proposal input-bindings; selection source itself not read.24 literal copies only; no G3 source edit authorized.'
write('custody.json',custody)
verdict=json.loads((HERE/'verdict-and-options.json').read_text())
verdict['status']='old G3 lower core blocked; macro design semantically plausible with64-scalar core, complete cost/lifetime proof still blocked'
verdict['producer_proposal_custody']='Admitted8-member/25104-byte proposal independently hash verified; see proposal-disposition.json.'
verdict['macro_proposal_disposition']='No intrinsic function-return layer from expression block; explicit A/B initializer transfers yield64 core with16/16/16/16 partition. Actual expect msg argument and favorable primitive granularity remain open; not a complete upper bound.'
write('verdict-and-options.json',verdict)
(HERE/'README.md').write_text('''# Independent G3 source and proposal review

Original four-ld source has a favorable70-scalar lower core plus four8-byte
payload copies. It cannot fit the selected64 scalar slots under that explicit
model. The binding contract does not formalize every primitive: this is a
conditional source-work finding, not a measured runtime overrun.

The admitted expression-macro proposal preserves single offset evaluation,
hygiene, short-circuit/read order and checked byte mapping. An ordinary block
adds no function return owner solely by having a tail expression. A/B outer
initializer temporaries and identifier bindings still need distinct edges.
Including those gives a conservative64-operation core with16/16/16/16 blocks.
Offsets are usize; the producer flow's u64 labels must be corrected. The captured
c shared indexing reborrow remains inside the named view primitive.

This is bounded design evidence, not a complete cost upper bound. In particular,
four expect message arguments still have no explicit owners. Charging one
scalar transfer each makes68 with this core. Range/view aggregation, every
other complete transfer and full lifetime assignment also need explicit closure.
A separately selected unwrap amendment could remove the message argument but
would still need exact source/proof review. No amendment is selected here.

`operation-table.json` and `path-and-boundary-table.json` bind the old comparison
and G3/G4 boundary. `proposal-disposition.json` freezes the exact conservative
partition, macro/block/temporary decisions, remaining edges and limitations.
`language-reference-basis.json` records official Rust specifications used for
semantic reasoning; they do not define debit atomization.

Reproduce static checks only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/verify_review.py
```

Builder writes only this directory; rebuilding changes custody time/HEAD and
requires resealing. Verifier checks packet integrity and table arithmetic.
No active correction2 source, product/compiler/harness/model/native/device
execution or process inventory occurred. Old independent seal and all producer
bytes remain unchanged. Root owns repair selection and delivery. No complete
source-work, memory-role, implementation, release or GA acceptance is supplied.
''')
print(json.dumps({'status':'independent static G3/proposal checks passed','proposal_members':8,'proposal_bytes':25104,'old_lower_core':70,'macro_conservative_core':64,'block_sizes':[16,16,16,16],'unassigned_expect_message_transfers':4,'conditional_core_plus_messages':68,'complete_upper_bound_accepted':False,'runtime_tests':0}))
