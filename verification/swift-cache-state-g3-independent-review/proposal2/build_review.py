"""Static proposal2 custody, arithmetic and source-proof checks; no Rust execution."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PROPOSAL='verification/swift-cache-state-implementation/correction-2/g3-proposal-2/'
CACHE='verification/swift-cache-state-implementation/correction-1/source/library/cache_state.rs'
ENV='verification/swift-cache-state-implementation/correction-1/source/library/envelope.rs'
DOC='docs/swift-semantic-adapter-prerequisite.md'
OLD='verification/swift-cache-state-g3-independent-review/seal.json'
EXPECTED={
    PROPOSAL+'seal.json':'08b6b164cb4cb8d420538f9bcf4cb0b97850912789b29635aaf8e140a74263b7',
    CACHE:'1ffc4ee5bb37c4ca2794c456f66bfcd9f1916090a0de3a548c19b6c82a3767b9',
    ENV:'11aee91058837ba13a9000c44d30e93049f3011be46ea9493110bb81b8ab4798',
    DOC:'c818e47d15d541731df98cdf79032846cb4e4aa28aad2eee7e25ac36cb1c7f41',
    OLD:'4773adbb72299087ba2c7ee1f060186e373d1091b8d8eeac07b059099584e6c6',
}
def meta(path):
    data=(ROOT/path).read_bytes()
    return {'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2)+'\n')
for path,sha in EXPECTED.items():
    assert meta(path)['sha256']==sha,path
manifest=json.loads((ROOT/PROPOSAL/'seal.json').read_text())
for m in manifest['members']:
    assert meta(m['path'])==m,m['path']
assert len(manifest['members'])==9
assert sum(m['bytes'] for m in manifest['members'])==35935
source=(ROOT/CACHE).read_text().splitlines()
old=(ROOT/PROPOSAL/'old-fragment.txt').read_text()
assert old.strip()=='\n'.join(source[264:267]).strip()
fragment=(ROOT/PROPOSAL/'proposed-fragment.txt').read_text()
assert len(fragment.encode())==620
assert fragment.count('$offset')==2 # matcher once, transcription once
assert fragment.count('comparison_word!')==4
assert 'let at: usize = $offset;' in fragment
assert '.first_chunk::<8>().unwrap()' in fragment
assert '.expect(' not in fragment
(HERE/'proposed-fragment.txt').write_text(fragment)

# Handwritten independent source/value-flow grammar. Compare identifiers only
# after deriving this operation stream; producer code/builders are never run.
load_rows=[
    ('offset_1','usize multiplication or explicit u64->usize cast'),
    ('offset_2','usize addition or multiplication'),
    ('at_local','offset-expression source -> explicit local at:usize received'),
    ('end','at+8'),
    ('range','complete Range<usize> constructor and Index argument source/received primitive'),
    ('start_check','range start<=end'),
    ('end_check','range end<=Candidate length'),
    ('shared_c_view','complete shared c Index receiver/reborrow and returned range-view/first_chunk-receiver primitive'),
    ('first_chunk_predicate','slice length>=8'),
    ('option_edge','complete Option<&[u8;8]> source -> unwrap received self'),
    ('tag','unwrap Some tag check'),
    ('ref_edge','unwrap returned &[u8;8] source -> received dereference operand'),
    ('LE','u64 LE decode'),
    ('conversion_return','from_le_bytes u64 source -> outer initializer/operand received temporary'),
]
ops=[]
stream=[]
for load in ['A','B']:
    for ident,desc in load_rows:
        full=load+'.'+ident
        stream.append(full)
        ops.append({'id':full,'operation':desc,'scalar_units':1})
    binding=load.lower()+'_binding'
    stream.append(binding)
    ops.append({'id':binding,'operation':load+' initializer temporary -> named u64 binding','scalar_units':1})
for ident,desc in [('b_absent','b==ABSENT'),('b_branch','|| short-circuit'),('a_present','a!=ABSENT'),('a_branch','&& short-circuit')]:
    stream.append(ident)
    ops.append({'id':ident,'operation':desc,'scalar_units':1})
for load in ['TA','TB']:
    for ident,desc in load_rows:
        full=load+'.'+ident
        stream.append(full)
        ops.append({'id':full,'operation':desc,'scalar_units':1})
for ident,desc in [('order','left timestamp<=right timestamp'),('result','comparison bool source -> received take_left binding')]:
    stream.append(ident)
    ops.append({'id':ident,'operation':desc,'scalar_units':1})
assert len(stream)==64 and len(set(stream))==64
assert sum(x['scalar_units'] for x in ops)==64
blocks=[{'id':'S'+str(i+1),'count':16,'operations':stream[16*i:16*i+16]} for i in range(4)]
producer=json.loads((ROOT/PROPOSAL/'operation-partition.json').read_text())
assert blocks==producer['proposed']['full_scalar_blocks']
assert 2*14+2+3==33
assert 2*14+2+5==35
assert 4*14+2+6==64
assert 4*17+2+6==76
assert 1024+63*8+8==1536<=2048
assert 63*8+8==512
assert 512+63*8+8==1024
assert 8+9*8+8+8+2*8+8==120
assert 32+32+16+16+16+16+16==144
write('operation-review.json',{
    'schema':1,'independent_operations':ops,'ordered_scalar_stream':stream,'scalar_blocks':blocks,
    'named_scalars':64,'payload_copies':[{'load':load,'source':'dereferenced [u8;8] behind Some reference','destination':'from_le_bytes by-value [u8;8] parameter','bytes':8,'groups':1} for load in ['A','B','TA','TB']],
    'copy_groups':4,'conditional_groups':8,'headroom_scalar_operations':0,
    'path_counts':{'B_absent':{'scalars':33,'copies':2},'A_absent_B_eligible':{'scalars':35,'copies':2},'both_eligible':{'scalars':64,'copies':4}},
    'partition_rule':'Source-order scalar stream within one G3 comparison: S1 ends with B.offset_1, S2 continues B through b guard. No reordering, per-load rounding, cross-group credit or optimizer elision.',
    'old_source_count':'Earlier70 is only a lower/core count. Adding old four explicit expect-message transfers and two A/B initializer bindings gives76 under this same favorable grammar, still not a measured runtime or universal primitive count.',
    'model_qualification':{
        'binding':'Exact-once mapping,8/comparison,<=16 named scalar ops/group, one distinct fixed copy<=128 bytes/group, unchanged G3/G4 caps and no optimizer elision.',
        'explicit_chosen_primitives':'Range construction+Index argument source/received is one full primitive. Shared c Index receiver/reborrow+result view/first_chunk receiver is one full primitive. Option/reference full source/received transfers are each one primitive. Standard slice/chunk/unwrap/LE operations are bounded source primitives, not an enumeration of compiler ABI or std machine instructions.',
        'not_implied_by_binding_text':'The formal atomization is not defined by prerequisite244..266. Root must explicitly retain/accept this disclosed convention rather than treating64 as an unconditional source/runtime cap proof.',
        'receiver_example_if_split':'Separately naming a captured-c Index receiver argument transfer in addition to the whole-view primitive adds one per load:68 rather than64. The proposal explicitly names its8-byte source/received receiver places; it has not hidden them, but groups them into the chosen primitive.',
        'no_unowned_explicit_message_argument':'unwrap has only self; the prior explicit msg:&str call argument is absent from exact source. Panic-only internal formatting is not declared normal product work or an optimizer saving.'
    },
    'within_same_explicit_model':'Consistent complete named local operation partition; no additional separately named explicit source argument omitted within that declared primitive grammar.',
    'final_source_bound_accepted':False,'runtime_tests':0,
})

write('semantic-and-panic-review.json',{
    'schema':1,
    'syntax_and_types':[
        'The620-byte fragment replaces only frozen265..267 within the existing actual-comparison else branch. Macro definition is a declaration, not a runtime closure/function.',
        'Exactly one transcription of $offset initializes explicit at:usize. All four invocations evaluate their offset once. src/left/right and range endpoints remain usize; a/b and timestamp values remain u64. No width-only type equivalence is used.',
        'Definition-site c resolves to the same &mut Candidate2048. Expansion-local at bindings are hygienic and per expansion. No by-value c/Candidate capture or separate persistent slice parameter exists.',
        'Actual shared Index receiver/reborrow, slice view, chunk receiver, Option self receiver, returned array reference,8-byte LE argument and returned u64 all have named operations/places under the disclosed full-view grammar.',
        'The expression block has its tail call value/type. It creates no extra function return output location. A/B outer initializer temporaries -> identifier bindings are counted separately; TA received operand survives while TB evaluates. No value place disappears merely because syntax is a macro.'
    ],
    'read_order_and_branches':[
        'G4 left==mid, then right==end tail checks precede actual comparison. Tail branches execute zero G3 loads.',
        'A index load completes before B index load. b==ABSENT short-circuits to true and skips a predicate and both timestamps.',
        'If b!=ABSENT, a!=ABSENT is checked; false skips both timestamps. Both eligible evaluates TA before TB, then <=. Equal timestamps choose left; timestampMAX remains data.',
        'After received take_left, G4 owns branch, repeated chosen offset, selected cursor advance, copy_within and all pass/pair/output loop state. No G3 costs move into G4.'
    ],
    'None_unreachability':{
        'strong_local_fact':'Any successful c[at..at+8] range access produces a slice of exactly8 bytes. first_chunk::<8> therefore returns Some by its API contract. No callback, mutation or slice resize occurs between these operations. A bad offset may panic before this point, but cannot produce a shorter successful range and then None.',
        'admitted_offset_induction':[
            {'id':'I1','lines':[328,334,362,405],'fact':'f.slots is admitted1..64. Resident loop plus inactive tail loop writes all64 index cells512..1024, each slot0..63 or ABSENT; timestamps occupy0..512. No uninitialized index position survives.'},
            {'id':'I2','lines':[247,257,282,285],'fact':'src/dst alternate512 and1024. width is1,2,4,8,16,32; base is a multiple of2*width and end<=64. left/right begin inside their half-open runs.'},
            {'id':'I3','lines':[258,278],'fact':'Tail guards and one selected-cursor increment per output preserve cursor bounds. Both-nonempty comparisons read indices0..63. Largest index slice end is1024+63*8+8=1536<=2048.'},
            {'id':'I4','lines':[267,278],'fact':'Every transfer copies one existing8-byte index from current src to disjoint dst. Inductively every copied value remains0..63 or ABSENT; no arbitrary timestamp is substituted for an index.'},
            {'id':'I5','lines':[267,267],'fact':'The original b/a sentinel guards precede timestamp casts. Both non-ABSENT indices are0..63, so casts are value-preserving and timestamp slice end<=63*8+8=512. Timestamp u64MAX is not an index sentinel.'},
            {'id':'I6','lines':[534,538],'fact':'Plan staging1648..1688 and scalar stages1688..1944 are disjoint from timestamp/index scratch. merge follows successful full seed/guards; no fallible I/O or user callback mutates these ranges during comparison.'}
        ],
        'not_optimizer_elision':'The checks are still counted even though this induction proves success. No checks are removed from authored source or presumed optimized away.',
        'scope':'All admitted production semantic states reaching merge, including arbitrary timestamp bytes and stale pre-seed Candidate bytes. Direct private calls with unseeded index arrays are outside the admitted merge contract; even there successful exact8-byte slice cannot yield None.'
    },
    'panic_difference':{
        'explicit_change':'An impossible None would use unwrap panic text instead of old expect custom text. Bounds/overflow checks remain; no public AnalyzerError/reason/projection behavior is changed on admitted inputs.',
        'new_safety_escape':False,'unchecked_or_unsafe_read':False,
        'not_executed':'No panic, private state, comparison or compiled macro was executed; this is a source/API proof.'
    },
    'language_semantics_basis':[
        {'url':'https://doc.rust-lang.org/std/primitive.slice.html#method.first_chunk','retrieved':'2026-10-26','fact':'first_chunk<N> returns an array reference when the slice has at leastN items; otherwise None. Applied here with len=N=8.'},
        {'url':'https://doc.rust-lang.org/std/option/enum.Option.html#method.unwrap','fact':'unwrap consumes self and returns Some payload; no explicit message parameter.'},
        {'url':'https://doc.rust-lang.org/reference/expressions/block-expr.html','fact':'Block value/type is its final operand; expression-only block creates no function boundary.'},
        {'url':'https://doc.rust-lang.org/reference/macros-by-example.html','fact':'Mixed-site hygiene resolves captured local c at definition and keeps introduced at bindings per expansion.'},
        {'url':'https://doc.rust-lang.org/reference/expressions.html','fact':'Value/place context, initializer/operand temporaries and left-to-right operand order inform named source/received places; they do not define debit units.'}
    ],
})

write('lifetime-disposition.json',{
    'schema':1,'status':'local place arithmetic consistent; full union/layout/caller proof remains open',
    'independent_merge_places':[
        {'place':'c merge parameter','type':'&mut Candidate2048','bytes':8},
        {'place':'src,dst,width,base,left,mid,end,right,out','type':'nine usize','bytes':72},
        {'place':'current offset source and at local received','type':'two usize','bytes':16},
        {'place':'a,b bindings','type':'two u64','bytes':16},
        {'place':'TA received operand while TB runs','type':'u64','bytes':8}
    ],
    'merge_sum':120,'selected_merge_subrole':144,
    'independent_helper_places':[
        {'place':'Range source+Index argument received','bytes':32},
        {'place':'shared slice view source+chunk receiver','bytes':32},
        {'place':'Option source+unwrap self received','bytes':16},
        {'place':'array reference source+received','bytes':16},
        {'place':'array8 dereference source+LE argument received','bytes':16},
        {'place':'decoded u64 source+received operand/initializer','bytes':16},
        {'place':'implicit shared Candidate receiver source+received','bytes':16}
    ],
    'helper_sum':144,'selected_helper_subrole':192,
    'phase_detail':[
        'For A/B, decoded received slot is initializer source, copied once into named a/b binding; no duplicate source slot is invented. A initializer ends before B; no two at locals coexist.',
        'For TB, a/b bindings and TA operand still exist; TB decoded received operand is already in helper16 row. This avoids omitting the left operand while right is evaluated.',
        'take_left source/received bool occurs after expanded load locals/borrows finish; no peak120+144 proof depends on eliding it. G4 index_at/chosen branch locals are a later distinct phase and require their own full ledger.',
        'Source/received Range/view/Option/array rows conservatively coexist in local helper144; earlier actual drops are not needed to fit that local sum.',
        'No extra Result/Ok/aggregate, closure, Candidate, heap owner, map or array owner is introduced. Full enclosing leaf/Progress/options/wire/caller role union must still be reconciled.'
    ],
    'size_qualification':'These are declared64-bit source-type sizes for local design arithmetic, not newly measured compiler layouts, physical stack/RSS or complete product peak.',
    'same_rule_for_other_macros':'Do not invent function Results solely for macro blocks; do retain actual constructor/Ok, initializer/operand, local, function-return and immediate caller places elsewhere.',
    'full_role_union_proved':False,'fresh_layout_run':False,
})

write('grain-and-ownership-review.json',{
    'schema':1,'status':'root primitive-model choice required; binding text alone does not establish single-scalar grain',
    'binding_question':'Prerequisite244..266 requires every micro-operation/fixed copy/full caller move exactly once, with<=16 named scalar operations/group. It does not define a whole Range16 or fat-view16 as a scalar, nor authorize hiding their complete transfers.',
    'exact_control_value_owners':[
        {'producer_row':'range','source':'Range<usize>{start:at,end:at+8}, complete16 bytes','received':'Index range argument, complete16 bytes','covered_by64_row':'Construction and complete source-to-received Range boundary are combined as one authored-source primitive. The two endpoint values and32-byte source/received role sum remain named, not optimized away.'},
        {'producer_row':'shared_c_view','source':'Thin shared Candidate Index receiver8 plus returned &[u8] view16','received':'Index receiver8 plus first_chunk shared-view receiver16','covered_by64_row':'Receiver reborrow/transfer and shared fat-view source/received flow are combined into one whole checked-view primitive. Distinct16-byte thin-receiver union and32-byte fat-view union remain in local helper144.'},
        {'producer_row':'option_edge','source':'Option<&[u8;8]> payload/tag representation, claimed8 bytes','received':'unwrap self of same complete type','covered_by64_row':'One complete Option source/received boundary; this is not permission to erase a second independent caller/local if one exists.'},
        {'producer_row':'ref_edge','source':'unwrap returned &[u8;8], claimed8 bytes','received':'dereference operand reference of same type','covered_by64_row':'One actual complete reference boundary;8-byte payload array movement stays a separate fixed-copy group.'}
    ],
    'defensibility_and_limit':'These are finite authored-source control operations with named complete owners, so they can form an explicit abstract cost model. They are not established as single physical/register/memory micro-operations by Rust semantics or by the binding passage. The reviewer does not infer conformance merely from64 fitting. Root must explicitly select/clarify this grammar, or require a finer proof/repair. This packet offers no unconditional source-cost upper bound.',
    'illustrative_finer_grain_sensitivity':{
        'not_a_new_binding_rule':True,
        'Range':'Even charging two endpoint/control-field operations to each Range row rather than one adds4 over four loads.',
        'fat_view':'Even charging pointer/length as two control operations to each view row rather than one adds4 more.',
        'partial_scalar_total':72,
        'additional_receiver_note':'A distinct8-byte Index receiver argument and actual constructor-to-parameter moves could add still more.72 is illustrative partial expansion, not a complete alternate upper bound.',
        'copy_alternative':'If a full Range16/view16 transfer is instead classified as its own fixed copy, each distinct transfer needs a copy unit; it cannot be silently mixed into the existing four payload copies.'
    },
    'required_consistency_if_root_selects_whole_control_primitives':[
        'Write the permitted primitive semantics, complete types/sizes and all source/received boundaries explicitly, rather than treating any convenient multi-operation bucket as one scalar.',
        'Apply exactly the same Range/view/reference/Option and binding rules to ld, st, sq, direct copies, setup, cleanup, projections and existing ordinary/macro blocks. Changed grammar must not silently rescue only G3.',
        'Keep actual independent arrays/payload stores as fixed copies: st LE-array return and destination store remain two copies; four comparator input arrays remain four copies; full Result/aggregate/caller moves retain their explicit copy chunks.',
        'An atomic primitive never erases a lifetime owner: source and received Range/view/receiver/Option places remain present in the role union even if their work debit uses one named operation.',
        'Require a fresh complete bound under the selected definition before marking implementation accepted. Actual code, full roles and runtime behavior remain separate gates.'
    ],
    'root_model_choice_resolved_by_reviewer':False,
})

write('verdict.json',{
    'schema':1,'status':'proposal2 locally consistent within same explicit source model; bounded implementation-design evidence only',
    'proposal_seal_sha256':EXPECTED[PROPOSAL+'seal.json'],'proposed_fragment_sha256':meta(PROPOSAL+'proposed-fragment.txt')['sha256'],
    'supported':[
        'Exact620-byte comparator-local macro has one offset evaluation, explicit usize, original read/short-circuit/stable comparison order and no extra function output owner.',
        'All normal-path local operation categories are assigned within the disclosed whole-Range/view/Option primitive grammar, including c receiver and A/B initializer bindings. No explicit expect msg argument remains.',
        'Independent64-ID source-order partition is16/16/16/16 plus four distinct8-byte input copies.33/35 short-path totals and local120/144 place arithmetic reconcile.',
        'Successful exact8-byte slice makes unwrap None unreachable; admitted seeding/copy/cursor induction additionally proves bounds. Private panic-text difference is explicit.'
    ],
    'conditions_before_any_actual_implementation_acceptance':[
        'Root explicitly resolves/records the whole Range16/view16 primitive grain and its consistency with scalar/copy/full-caller rules, then selects exact620-byte source repair. Binding text alone does not establish that grain; review itself authorizes no edit or model change.',
        'No headroom: any newly separated receiver/Range/coercion/return operation invalidates64 and requires a new source/proof design; no spare G4/G6/global credit or cap increase.',
        'Bind actual selected source/diff and independently recheck macro expansion/compile/type/borrow, layout/API, actual-File public behavior and separately authorized private sort/edge/poison regression.',
        'Complete G1/G2/G4/G5/G6/G7/ADMIN/st/sq and inherited caller/Result/error/cleanup proof within unchanged caps; local proposal proof is not a full source ledger.',
        'Complete per-source/received/drop/phase union29344 within reserved41984/global65536, max complete value512 and sole Candidate2048. Local merge/helper sums do not prove this.',
        'Keep native/UI/capture/simulator/emulator/phone checks paused/pending; no release/dogfood/GA qualification inferred.'
    ],
    'conditional_G3_design_partition_supported':True,'binding_cost_model_amended':False,
    'root_grain_choice_required':True,'unconditional64_upper_bound_supplied':False,
    'final_G3_bound_accepted':False,'full_lifetime_accepted':False,'implementation_accepted':False,'repair_selected':False,
    'runtime_tests':0,'compiler_execution':False,'product_or_model_or_harness_execution':False,
    'no_active_correction2_source_read':True,
})
write('custody.json',{
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'python':sys.version,'git_version':'git version2.56.0',
    'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'verified_inputs':[meta(p) for p in EXPECTED],
    'producer_members_verified':manifest['members'],'member_count':9,'member_bytes':35935,
    'current_correction2_source_custody':'Target6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00 is from admitted producer seal and root; active product source not read/verified here.',
    'original_members_unchanged':'Prior G3 seal bytes verified; no old review or producer files written. Parent old manifest does not include this new subpacket.',
    'mutation_scope':'verification/swift-cache-state-g3-independent-review/proposal2/**',
    'commands_and_outputs':'This builder validates parent hashes, exact text invariants and handwritten proof arithmetic; see static-validation.stdout.json. Separate freeze/verifier commands appear in README/seal.',
    'native_ui_capture_device_process_inventory_or_runtime_execution':False,
})
parts=['# Source-bound proof excerpts\n\nFrozen correction1 cache source hash: '+EXPECTED[CACHE]+'.\n']
for lo,hi in [(246,287),(328,334),(362,405),(526,538)]:
    parts.append('\n```text\n'+'\n'.join(f'{i}: {source[i-1]}' for i in range(lo,hi+1))+'\n```\n')
(HERE/'source-excerpts.md').write_text(''.join(parts))
(HERE/'README.md').write_text('''# Independent proposal2 disposition

The exact620-byte unwrap macro is locally consistent within the same disclosed
source-operation model. The independent partition has64 named scalars in four
16-operation blocks plus four8-byte payload copies; short paths use33/35 scalars.
Explicit usize, one offset evaluation, hygienic c access, all initializer/result
edges and original short-circuit/read order reconcile. No headroom remains.

Any successful at..at+8 access yields exactly8 bytes, so first_chunk::<8> is
Some. Full seed/cursor/copy induction also bounds admitted reads. Replacing expect
with unwrap changes private panic text only on impossible None; it removes the
explicit message argument rather than assuming it optimized away.

This is bounded implementation-design evidence. The binding contract does not
formalize the favorable whole-Range/full-view/Option primitives. A separately
charged receiver or other new operation breaks64. Local merge120/helper144
arithmetic does not establish the complete29344 role union or compiler layout.
`grain-and-ownership-review.json` names every complete control owner and makes
the root model choice explicit. Merely expanding each Range/view row to two
field operations gives72; that sensitivity is not a new mandatory rule or a
complete alternate upper bound. No physical/register micro-operation claim is
made for a whole16-byte primitive, and no independent copy disappears.
Actual G3/source/lifetime/implementation acceptance is false. Root must select
any source edit and separately admit fresh compile/API/layout/behavior evidence.

Reproduce static checks only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/proposal2/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/proposal2/verify_review.py
```

Builder writes only proposal2; rebuilding changes custody time/HEAD and requires
resealing. Verifier validates frozen bytes and arithmetic. No product/compiler/
harness/model/native/device execution or process inventory occurred. Active
correction2 writes were not read. Prior review/proposal packets remain immutable.
No release/dogfood/GA qualification is supplied.
''')
print(json.dumps({'status':'independent proposal2 static review checks passed','producer_members':9,'producer_bytes':35935,'scalar_count':64,'block_sizes':[16,16,16,16],'copy_groups':4,'short_paths':[33,35],'design_partition_supported_under_explicit_model':True,'final_G3_or_lifetime_or_implementation_accepted':False,'runtime_tests':0}))
