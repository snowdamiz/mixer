"""Independent static source/proof checks. Never imports or runs product/producer code."""
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='verification/swift-cache-state-implementation/correction-2/'
AUDIT='verification/swift-cache-state-g6-accounting/'
ANON='verification/swift-semantic-adapter-root-review/clear128-anonymous-proposal/'
DOC='docs/swift-semantic-adapter-prerequisite.md'
EXPECTED={
    AUDIT+'seal.json':'56531ea3ebaf7e4fcd3eb8df2afddc7b2aa17dda2121156c4238659c6bdd1cbf',
    AUDIT+'proposal-clear128/seal.json':'021f726ae15a9a3046e149ccde61294be045956f43b1ddd431e5b9d98f7c8733',
    ANON+'seal.json':'ed0fa3abe9394bf4f7edfca280d80de7f89011a5eb6abb0db5742a13cf8cabb2',
    BASE+'candidate-repo-seal.json':'26e6ece9d86f054a57e335c6b170595aa1d21e3081b45db4eda167e59abe52fb',
    BASE+'source/library/cache_state.rs':'6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00',
    AUDIT+'proposal-clear128/cache_state.rs':'036856e13caa5e81b643374e0784936b20840a744b88a8024f9c46abbb54ce22',
    ANON+'cache_state.rs':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
    DOC:'c818e47d15d541731df98cdf79032846cb4e4aa28aad2eee7e25ac36cb1c7f41',
}
def meta(path):
    data=(ROOT/path).read_bytes()
    return {'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2)+'\n')
for p,sha in EXPECTED.items(): assert meta(p)['sha256']==sha,p
custody=[]
for p,count,total in [(AUDIT+'seal.json',13,167404),(AUDIT+'proposal-clear128/seal.json',3,51632),(ANON+'seal.json',5,55421),(BASE+'candidate-repo-seal.json',570,15269154)]:
    manifest=json.loads((ROOT/p).read_text())
    for m in manifest['members']:
        assert meta(m['path'])==m,m['path']
    assert len(manifest['members'])==count
    assert sum(m['bytes'] for m in manifest['members'])==total
    custody.append({'seal':meta(p),'verified_member_count':count,'verified_member_bytes':total})
before=(ROOT/BASE/'source/library/cache_state.rs').read_text()
named=(ROOT/AUDIT/'proposal-clear128/cache_state.rs').read_text()
anon=(ROOT/ANON/'cache_state.rs').read_text()
old='''    let zero = [0u8; 8];
    for i in 0..256 {
        let at = i * 8;
        c[at..at + 8].copy_from_slice(&zero);
    }
'''
assert before.count(old)==1
ranges=[(128*i,128*(i+1)) for i in range(16)]
named_block='    {\n        let zero = [0u8; 128];\n'+''.join(f'        c[{s}..{e}].copy_from_slice(&zero);\n' for s,e in ranges)+'    }\n'
anon_block=''.join(f'    c[{s}..{e}].copy_from_slice(&[0u8; 128]);\n' for s,e in ranges)
named_expected=before.replace('// Explicit zero-word stores avoid a second2048-byte temporary source owner.','// Explicit bounded stores avoid a second2048-byte temporary source owner.').replace(old,named_block)
assert named==named_expected
assert anon==before.replace(old,anon_block)
suffix=before.split(old)[1]
assert named.endswith(suffix) and anon.endswith(suffix)
assert [n for s,e in ranges for n in range(s,e)]==list(range(2048))
(HERE/'anonymous-clear-fragment.txt').write_text(anon_block)

# Independent payload enumeration from actual event source, not the producer total.
segments=[
    {'id':'event','lines':[642,671],'payload_groups':33,'derivation':'zero-tail64 copy1 +12 resident/pin st*2 +4 sq*2'},
    {'id':'staged_prior_pin','lines':[653,653],'payload_groups':1,'derivation':'ld input [u8;8] -> from_le_bytes by-value argument; computes staged pins, conservatively G6'},
    {'id':'final_sq','lines':[707,730],'payload_groups':12,'derivation':'six sq at0..5, each LE-array return copy1 + destination store copy1'},
    {'id':'rows','lines':[734,747],'payload_groups':2,'derivation':'resident64 and pin48 commit; plan_delta absent on built branch'},
    {'id':'scalar_commits','lines':[753,764],'payload_groups':12,'derivation':'12 exact literal8-byte Candidate->arena copies'},
    {'id':'old_clear','lines':[781,785],'payload_groups':257,'derivation':'zero8 source->local binding copy1 plus256 distinct destination8-byte copies'},
    {'id':'restores','lines':[786,797],'payload_groups':12,'derivation':'12 exact literal8-byte arena->Candidate restores'},
]
assert sum(x['payload_groups'] for x in segments)==329
core_names=[
    'i source -> multiplication operand','literal8 -> multiplication operand','multiply i*8','result -> local at',
    'at -> Range.start source field','at -> endpoint-add operand','literal8 -> endpoint-add operand','add at+8','end result -> Range.end source field',
    'Range.start -> received index start','Range.end -> received index end','ordered-range predicate','upper-bound predicate',
    'Candidate base+start address formation','end-start length formation','view.data -> copy receiver.data','view.len -> copy receiver.len',
    'zero address -> source slice argument.data','literal8 -> source slice argument.len','copy length equality','copy unit/control -> caller continuation',
]
assert len(core_names)==21
ids=[f'G6.clear[{i:03}].C{j:02}' for i in range(256) for j in range(1,22)]
assert len(ids)==5376 and 5376//16==336
ids_sha=hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()
assert ids_sha=='0bc6b4453b0cb18de0d9d4aff0a6432f59dd5ff60c789bcd3e661f93dc22c9d8'
write('core-review.json',{
    'schema':1,'status':'665 qualified lower/core independently reproduced; not a complete upper/unconditional overrun',
    'source_sha256':EXPECTED[BASE+'source/library/cache_state.rs'],'built_payload_segments':segments,'payload_total':329,
    'clear_scalar_core':[{'id':f'C{i:02}','operation':n,'units':1} for i,n in enumerate(core_names,1)],
    'iterations':256,'scalars':5376,'globally_pooled_scalar_blocks':336,'ordered_ids_sha256':ids_sha,'qualified_core_total':665,
    'scope':'One scalar handles one machine word or primitive arithmetic/predicate/control operation. Range/view components and literal/input/binding edges are distinct. Source+received belong to one transfer, not two duplicate debits. No per-site rounding.',
    'not_complete':['256 loop iterations and257 next/Option/guard controls','all helper scalar operands/returns/view/receiver places','all administration/event arithmetic/checks','zero8 repeat construction fields/inputs','actual cleanup caller/guard/return','all G1/G6 overlap reconciliation'],
    'st_sq':'Each call has exactly two distinct8-byte payload moves in this model: to_le_bytes return->temporary and temporary->fixed destination. By contrast ld contributes one input array copy and scalar returns; do not inherit st copies for ld.',
    'grouping_limit':'The component grammar is disclosed and consistent with earlier grain objections; binding text does not uniquely define it.665 is source-model lower/core evidence, not runtime work or final cap acceptance.',
})

write('boundaries-and-findings.json',{
    'schema':1,'findings':[
        {'id':'B1','status':'producer metadata boundary defect; root has not selected reassignment','source':'helpers-and-obligations.json boundary G7/G128','finding':'All guard SemanticReply moves were placed in G7. Keep zero-debit absent/readability/invalid-budget/underfunded guard reply source/received and caller terminal installation in separately reserved G128, per prerequisite277..282 and inherited correction1 source-accounting guard ownership. Paid ordinary success/refusal/poison replies remain G7. This does not affect329/665 core arithmetic.'},
        {'id':'B2','status':'named clear storage gate','source':'proposal-clear128 receipt local_zero_places','finding':'Named zero128 source+received local reaches256 at binding, +240 over old16. Live Paid24 still exists through projection, so assigning both entirely to original wire256 gives at least280. Even the steady local rises8->128 (+120). No inherited wire or whole29344 acceptance is available.'}
    ],
    'exact_boundary_map':{
        'G1':'Initial16 snapshot sq plus extra prior/first-pin staging and admitted identity/read preconditions only. Do not also charge G6 new pins checked_add/Option/staged-value work here. Any global ledger overlap must be removed explicitly.',
        'G2_G3_G4_G5':'Probe/seed, comparator, transfer and prefix work retain separate ownership. Final selected-prefix sq stores at562..567 are G6.',
        'G6':'Event delta writes and their new staged arithmetic, including prior_pins ld653/checked_add654/Option binding; final six sq; row/scalar commits; actual cleanup call/guard/clear/restore/returned bool and caller !/branch.',
        'G7':'Paid ordinary complete SemanticReply source/return/received/audit, p.calls/snapshot/header scheduling and actual cleanup-fault conditional poison installation. No spare G7 allowance funds G6 or G128.',
        'G128':'Zero-debit private guard computations, complete guard reply/received and corresponding absorbing caller terminal installation. A guard return inside an admitted loan still follows actual G6 cleanup from prepayment; preloan failures leave Candidate untouched.',
        'cleanup_fault':'cfg(test) cleanup false after corruption reaches caller1216 !/branch (G6) and latch_terminal16 (ordinary cleanup-fault poison effect, G7). If a test combines invalid-length guard and cleanup failure, classify each source edge/cause explicitly; no blanket all-replies G7 rule.',
        'cfg_test':'Private fault branch extra work is not production source-cost acceptance. No injected execution was run.'
    },
    'whole_G1_G6_G7_G128_ledger_closed':False,
})

# Complete bounded clear-block ledger within an explicit component-authored
# source model. Standard fixed-copy primitive covers <=128 payload, not its
# codegen loop. Repeat constructors are expanded into128 scalar element edges.
meta_ops=[
    'literal start -> Range.start source field','literal end -> Range.end source field',
    'Range.start -> Index received start','Range.end -> Index received end',
    'Candidate exclusive Index receiver borrow creation','Candidate thin pointer -> Index receiver received',
    'Index operation entry control','received start -> ordered predicate left','received end -> ordered predicate right',
    'start<=end predicate','ordered check success branch','received end -> upper predicate left',
    'Candidate length2048 source -> upper predicate right','end<=2048 predicate','upper check success branch',
    'Candidate base pointer -> address operand','received start -> address offset operand','destination address formation',
    'received end -> length subtraction left','received start -> length subtraction right','view length end-start',
    'address result -> returned view.data source','length result -> returned view.len source','projected exclusive view loan creation',
    'returned view.data -> caller received view.data','returned view.len -> caller received view.len','Index return control',
    'copy receiver reborrow creation','caller received view.data -> copy receiver.data','caller received view.len -> copy receiver.len',
    'zero array address formation','source shared borrow creation','source address -> source view.data source field',
    'source array length128 -> source view.len source field','source view.data -> copy argument.data received','source view.len -> copy argument.len received',
    'copy operation entry control','copy receiver.len -> equality left','copy argument.len -> equality right',
    'source/destination length equality predicate','length check success branch','copy unit/control returned -> caller','unit discard and statement continuation',
]
assert len(meta_ops)==43
init=[{'id':'I.zero','operation':'literal0u8 -> repeat operand value','units':1},{'id':'I.length','operation':'const128usize length operand -> array construction control','units':1}]
init += [{'id':f'I.element[{i:03}]','operation':f'repeat u8 value -> array element[{i}] initialization','units':1} for i in range(128)]
assert len(init)==130
anonymous_stream=[]
for i in range(16):
    # Receiver evaluated before argument; initializer before source borrow.
    anonymous_stream += [f'A{i:02}.M{j:02}' for j in range(1,31)]
    anonymous_stream += [f'A{i:02}.'+x['id'] for x in init]
    anonymous_stream += [f'A{i:02}.M{j:02}' for j in range(31,44)]
assert len(anonymous_stream)==2768 and len(set(anonymous_stream))==2768
assert 2768//16==173
write('clear-block-ledger.json',{
    'schema':1,'status':'complete conservative clear-block-only component-source bound, conditional on stated primitive model; not whole G6/binding-implied upper',
    'scope':'Exact replacement clear statements only. Unchanged cleanup invocation/length guard,12 restores, fault suffix, bool return/caller ! and all event/commit work are excluded and still G6 obligations, not free.',
    'primitive_definition':[
        'One scalar unit per at-most-one-word source->received edge or primitive arithmetic/predicate/branch/borrow/call control; source and received are endpoints of one transfer.',
        'Index and copy fixed platform operations use the explicit component/guard/control expansion below; a <=128-byte actual payload transfer is one separate fixed-copy unit. No whole16-byte Range/view scalar shortcut.',
        'Repeat array constructor evaluates non-const operand0 once and supplies128 Copy u8 elements. Charge each element-initialization edge separately, plus zero and const-length source/control inputs. This is authored semantic expansion, not an assumed machine loop, vectorization or memcpy lowering.',
        'No array promotion, optimizer copy elimination, constant-folded range-check omission or hidden callback/I/O is credited. Additional compiler ABI/std implementation internals are not source primitives in this model; if that scope is required, this source bound must be replaced.'
    ],
    'per_store_metadata':[{'id':f'M{i:02}','operation':n,'units':1} for i,n in enumerate(meta_ops,1)],
    'per_initializer_component_edges':init,'metadata_units_per_store':43,'initializer_units':130,
    'anonymous':{
        'source_sha256':EXPECTED[ANON+'cache_state.rs'],'initializer_instances':16,'scalars':2768,'scalar_blocks':173,
        'ordered_stream_definition':'For each statement i: M01..M30, I.zero/I.length/I.element000..127, M31..M43; repeat for i=0..15.',
        'ordered_stream_sha256':hashlib.sha256(('\n'.join(anonymous_stream)+'\n').encode()).hexdigest(),
        'actual_array_to_destination_payload_copies':16,'payload_copy_width':128,'complete_clear_block_groups':189,
        'array_to_array_initializer_copies':0,
        'constructor_counting':'Each anonymous constructor writes its sole temporary via130 scalar component edges. No second source-array-to-received-array move exists. Do not ALSO add16 fictitious initializer array copies.',
        'root32_convention':'The proposal32 convention can charge16 bounded initialization units +16 destination copies, if root separately defines that initialization primitive. It is not32 actual array-to-array copies. This ledger instead expands construction fields and uses16 actual copies; the conventions cannot be added together.'
    },
    'named':{
        'source_sha256':EXPECTED[AUDIT+'proposal-clear128/cache_state.rs'],'initializer_instances':1,'scalars':820,
        'scalar_derivation':'130 constructor edges +16*43 metadata +2 lexical block entry/exit controls =820',
        'scalar_blocks':52,'payload_copies':17,'copy_derivation':'one128-byte initializer temporary -> named local binding plus16 destination128-byte copies',
        'complete_clear_block_groups':69,'named_binding_peak_bytes':256,
        'limitation':'Cheaper within this model but same original wire256 assignment is infeasible with live Paid24; cannot select on work arithmetic alone.'
    },
    'no_whole_G6_upper_claimed':True,'runtime_or_compiler_tests':0,
})

write('equivalence-and-places.json',{
    'schema':1,'ranges':[list(x) for x in ranges],'coverage':'Every byte0..2048 written zero exactly once in both alternatives; then exact old12 restores and cfg(test) fault suffix.',
    'prefix_suffix':'Anonymous proposal differs only in old clear block. Named proposal additionally changes its clear comment. All remaining source bytes match exactly; no new2048 initializer, by-value Candidate, helper or API.',
    'source_safety':'All16 destination ranges have literal endpoints0<=start<end<=2048 and length128. Each source is exactly128 bytes, so Index/copy length checks succeed for every sized Candidate without callback, resize, allocation or fallible conversion after first store. Checks remain charged; no compiler removal is credited.',
    'named':{'source_place128':128,'received_local128':128,'binding_peak':256,'old_binding_peak':16,'increase':240,'steady_local_increase':120,'lifetime':'zero128 named local ends at explicit inner block before restores','wire_issue':'256 peak plus live Paid24=280 exceeds wire256 if inherited assignment unchanged'},
    'anonymous':{
        'place_proof':'Borrowing the repeat-array value creates one anonymous128-byte placed temporary. There is no let identifier receiving that full array and no by-value array parameter: copy_from_slice receives a shared slice. The array is initialized in that sole place; no second128-byte array owner is inferred from mere expression composition.',
        'scope':'Each temporary/borrow belongs to its expression statement and ends before the next statement. No reference escapes copy_from_slice. No promotion or optimization credit is used. Repeat operand0 is evaluated once for each statement, not once across statements.',
        'wire_base':{'temporary_array':128,'live_Paid_received':24,'subtotal':152},
        'remaining_simultaneous_places':[
            {'place':'repeat u8 operand and const usize length input','bytes_up_to':9,'hypothesis':'control/helper or wire explicitly; even adding9 to base gives161, not a whole-role proof'},
            {'place':'cleanup b slice16 and c thin mutable pointer8 received parameters','bytes':24,'hypothesis':'control/helper inherited function arguments; alive throughout cleanup'},
            {'place':'caller cleanup borrow-source views matching b/c parameters','bytes':24,'hypothesis':'caller/control source/received ownership; do not erase by argument optimization'},
            {'place':'Range source and Index received','bytes':32,'hypothesis':'helper role; both16-byte values'},
            {'place':'Index thin receiver source and received','bytes':16,'hypothesis':'helper role'},
            {'place':'projected destination slice source/caller receive/copy receiver','bytes':48,'hypothesis':'helper role; three pointer/length pairs'},
            {'place':'shared array reference plus source slice and received source slice','bytes':40,'hypothesis':'helper role;8+16+16'},
            {'place':'largest predicate operand pair and bool','bytes':17,'hypothesis':'helper/control phase; earlier address/range operands may end sooner, but full map required'},
            {'place':'ordinary semantic reply source/received and Loan/StepBudget/Progress','hypothesis':'remain in existing control roles with explicit last-use/drop before/during cleanup; not reassigned to wire'},
            {'place':'cleanup returned/received bool','hypothesis':'occurs after anonymous clear temporary ends; original caller effect role still needs proof'}
        ],
        'helper_local_sum_example':153,
        'helper_sum_definition':'32 Range +16 thin Index receiver +48 destination fat views +40 source borrow/views +17 predicate pair/bool =153; received/caller cleanup handles separately24+24, repeat inputs separately9.',
        'role_acceptance':'These are explicit assignment hypotheses, not acceptance that original helper192/control/wire remainder fits every phase or full29344 union. Full caller/leaf overlap and all existing owners must be reconciled.'
    },
    'primary_semantic_references':[
        {'url':'https://doc.rust-lang.org/reference/expressions/array-expr.html','use':'Repeat0 operand evaluated once, then Copy value supplies128 elements; usize constant length.'},
        {'url':'https://doc.rust-lang.org/reference/expressions/operator-expr.html#borrow-operators','use':'Borrow of a value creates a temporary place; no separate by-value array call argument.'},
        {'url':'https://doc.rust-lang.org/reference/destructors.html#temporary-scopes','use':'Method-call argument temporary falls within expression statement scope; no escaping reference or lifetime-extending let.'}
    ],
    'full_role_union_accepted':False,'stack_RSS_layout_measured':False,
})

write('verdict.json',{
    'schema':1,'status':'recommend anonymous clear as bounded source-design option; root selection and full qualification still required',
    'recommended_exact_source_sha256':EXPECTED[ANON+'cache_state.rs'],
    'reason':'Anonymous variant preserves exact clearing/restoration behavior, removes256-loop overhead and avoids named zero128 binding peak256 while retaining an explicit per-statement128 temporary. Its complete clear-only component ledger189 groups is bounded without whole-Range/view shortcuts or promotion credit.',
    'conditions':[
        'Root explicitly selects exact anonymous fragment/source and records this component-authored primitive model; no product source edit is authorized by reviewer.',
        'Explicitly amend/supersede the source-contract256 iterations x8-byte zero stores premise with16 literal x128-byte stores, preserving complete2048 zeroing before the exact12 restores, identical fault suffix, preloan untouched state, postloan sole cleanup/poison/both-leaf disablement and unchanged work/memory caps. The old256-iteration receipts stay historical, not reinterpreted.',
        'Resolve producer G128 boundary defect exactly: keep zero-debit guard reply/terminal installation in G128, paid ordinary replies in G7, actual cleanup work in G6 and cleanup-fault latch effects cause-specific.',
        'Close whole G6 plus G1/G7/guard overlap and all helper/admin/loop/Option/checked arithmetic under unchanged640;189 is clear block only, not a whole-G6 pass.',
        'Assign all listed simultaneous temporary/control/Range/view/caller/reply owners and complete29344 union, without borrowing unused global/role margin; wire152 is a subtotal only.',
        'After exact source admission run separately authorized host compile/API/layout/actual-File/private behavior regression; retain pending native/UI/capture/phone gates.'
    ],
    'qualified_old_core':665,'anonymous_clear_component_bound':189,'named_clear_component_bound':69,
    'required_contract_amendment':{'old':'one zero8 source/local and256 in-place8-byte store iterations','selected_design_candidate':'16 direct128-byte anonymous repeat-array borrows/stores; one temporary per statement','unchanged':['all2048 bytes become zero','all12 exact envelope restores888..984','cleanup length guard and same exclusive fixed Candidate/arena proof','preloan untouched failures and all admitted postloan cleanup exits','cfg(test) fault suffix and poison/both-leaf disablement','G1..G7 caps256/2560/2568/768/640/640/248','setup512/finish256/guard128','Candidate2048, complete max512, role union29344/reserved41984/global65536']},
    'source_equivalence_supported':True,'repair_selected':False,'whole_G6_accepted':False,'full29344_union_accepted':False,'implementation_accepted':False,
    'runtime_tests':0,'compiler_execution':False,'product_harness_or_model_execution':False,'native_capture_or_process_inventory':False,
})
write('custody.json',{
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'python':sys.version,'git_version':'git version2.56.0','HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'verified_input_hashes':[meta(p) for p in EXPECTED],'seals':custody,
    'mutation_scope':'verification/swift-cache-state-g6-independent-review/**','source_authority':'Frozen C2 member hashes, not mutable HEAD alone',
    'root_boundary_instruction':'Root explicitly retained G128 guard reply/terminal installation after B1 finding; producer audit left immutable.',
    'zero_product_compiler_runtime_or_native_operations':True,
})
(HERE/'README.md').write_text('''# Independent G6 core and clear review

The665 result is a qualified lower/core:329 actual built-path payload movements
plus5376 clear-body component operations in336 globally pooled16-operation
blocks. It is not a complete upper bound or unconditional runtime overrun.
The staged prior-pins ld contributes one copy; st/sq each contribute two arrays.

Producer boundary metadata incorrectly places zero-debit guard reply movements
in G7. Root retains those guard replies/terminal installation in G128. Ordinary
paid replies remain G7; real cleanup remains G6. The frozen audit is unchanged.

Both clear proposals cover all2048 bytes exactly and preserve the restore/fault
suffix. Named zero128 has256-byte source/local binding peak (+240), conflicting
with unchanged wire256 when live Paid24 is included. Anonymous per-statement
borrows need one128-byte temporary, no named128-byte receive/by-value argument,
and end before the next statement without promotion credit.

Recommend the exact anonymous source as a source-design option. A conservative
clear-only component ledger charges every128 element-initialization edge per
statement, all literal/range/view/receiver/guard/control work, and16 actual128B
destination copies:2768 scalars/173 groups +16 copies =189. Named variant69 is
cheaper but has the unresolved storage peak. The proposal32 convention counts
16 bounded initializations plus16 stores; it is not32 physical array-to-array
moves and must not be combined with this expanded initialization ledger.

`clear-block-ledger.json` defines every unit and exact scope; unchanged cleanup
call/guard/restore/return and all other G6 work remain separate. Primitive grammar
still requires explicit root acceptance; no machine/std ABI or codegen upper is
claimed. `equivalence-and-places.json` lists actual source/received hypotheses:
128 temporary+Paid24=152 is a wire subtotal, not whole-role acceptance.
Selection must explicitly amend256x8 cleanup to16x128, preserving full2048
zeroing, the exact12 restores/fault suffix, preloan/postloan poison semantics
and all caps. Old receipts remain historical. No contract change is implicit.

Reproduce only independent static checks:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g6-independent-review/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g6-independent-review/verify_review.py
```

Builder writes only this directory and verifies all570 frozen C2 members plus
the13/3/5-member input seals. Rebuilding changes custody metadata and requires
resealing. No producer builders, product/compiler/harness/model/native/device
execution or process inventory occurred. Root owns selection/delivery. Whole
G6,29344 union, implementation, dogfood, release and GA acceptance remain open.
''')
print(json.dumps({'status':'independent G6 static source/proof checks passed','verified_C2_members':570,'qualified_core':665,'anonymous_clear_component_groups':189,'named_clear_component_groups':69,'recommendation':'anonymous source design only','runtime_tests':0}))
