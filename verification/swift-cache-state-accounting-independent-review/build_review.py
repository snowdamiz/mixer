"""Reviewer-owned static proof validation. Never imports/compiles/runs product code."""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REL = OUT.relative_to(ROOT).as_posix()
SOURCE = 'verification/swift-cache-state-implementation/correction-1/source/library/'
EXPECTED = {
    SOURCE+'analyzer.rs': 'ad039daac5de9ea811da70261ae6591dfe6846e23bea1a87fc013755b502af6e',
    SOURCE+'cache_state.rs': '1ffc4ee5bb37c4ca2794c456f66bfcd9f1916090a0de3a548c19b6c82a3767b9',
    SOURCE+'envelope.rs': '11aee91058837ba13a9000c44d30e93049f3011be46ea9493110bb81b8ab4798',
}
PARENTS = {
    'verification/swift-cache-state-accounting-supplement/seal.json': '7558f957bfe4b8cb62703b76e064f87d2e70a535cf5d61d55b826244c6770c77',
    'verification/swift-cache-state-implementation/candidate-repo-seal.json': 'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3',
    'verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json': 'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6',
    'verification/swift-cache-state-independent-review/implementation-review-1/accounting-review.json': 'c15df868773e646cdf472a09415d676e8978e4d04816d79da93c6a28e1dda42a',
    'docs/swift-semantic-adapter-prerequisite.md': 'c818e47d15d541731df98cdf79032846cb4e4aa28aad2eee7e25ac36cb1c7f41',
}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def meta(path: str) -> dict:
    data = (ROOT/path).read_bytes()
    return {'path': path, 'bytes': len(data), 'sha256': digest(data)}

def write(name: str, value: object) -> None:
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')

for path, sha in (EXPECTED | PARENTS).items():
    assert meta(path)['sha256'] == sha, path

supplement = json.loads((ROOT/next(iter(PARENTS))).read_text())
verified = []
for entry in supplement['members']:
    actual = meta(entry['path'])
    assert actual == entry, (actual, entry)
    verified.append(actual)
assert len(verified) == 11
assert sum(x['bytes'] for x in verified) == 55558

accept_path = 'verification/swift-semantic-adapter-root-review/combined-contract-acceptance.json'
acceptance = json.loads((ROOT/accept_path).read_text())
contract_seals = []
for entry in acceptance['packets']:
    actual = meta(entry['seal'])
    assert actual['sha256'] == entry['sha256'], entry['seal']
    contract_seals.append(actual)
prerequisite = json.loads((ROOT/acceptance['packets'][0]['seal']).read_text())
doc_entry = next(x for x in prerequisite['members'] if x['path'] == 'docs/swift-semantic-adapter-prerequisite.md')
assert doc_entry == meta(doc_entry['path'])

source_text = {Path(p).name: (ROOT/p).read_text() for p in EXPECTED}
# Assertions bind handwritten source observations. No Rust parsing/compilation or execution.
assert 'const SCALAR: Region = Region { base: 7_729_760, rows: 512, stride: 8 };' in source_text['analyzer.rs']
assert 'const CELLS: [usize; 12] = [7, 9, 10, 11, 12, 13, 14, 64, 65, 66, 160, 161];' in source_text['envelope.rs']
assert 'const ROW_CELLS: [usize; 10] = [21, 22, 23, 17, 128, 130, 131, 137, 84, 141];' in source_text['cache_state.rs']
assert 'const EXTRA_CELLS: [usize; 2] = [71, 78];' in source_text['cache_state.rs']

cells = [7,9,10,11,12,13,14,64,65,66,160,161]
base = 7729760
literal_path = 'verification/swift-cache-state-accounting-supplement/proofs/literal-restore-proposal.json'
literal = json.loads((ROOT/literal_path).read_text())
restore_endpoints = []
for i, cell in enumerate(cells):
    expected = {'index': i, 'cell': cell, 'source_start': base+8*cell,
                'source_end': base+8*cell+8, 'destination_start': 888+8*i,
                'destination_end': 896+8*i, 'bytes': 8}
    proposed = literal['proposed_calls'][i]
    for key, value in expected.items():
        assert proposed[key] == value, (key, expected, proposed)
    statement = 'c[{destination_start}..{destination_end}].copy_from_slice(&b[{source_start}..{source_end}]);'.format(**expected)
    assert proposed['proposed_statement'] == statement
    restore_endpoints.append(expected)
assert len(literal['proposed_calls']) == 12
assert {x['destination_start'] for x in restore_endpoints} == set(range(888,984,8))
assert max(x['source_end'] for x in restore_endpoints) <= 8388608
assert set(cells).isdisjoint([21,22,23,17,128,130,131,137,84,141,71,78,138])

write('custody.json', {
    'schema':1, 'at':datetime.now(timezone.utc).isoformat(),
    'source_authority':'Exact frozen source hashes, independent of mutable HEAD',
    'head_at_packet_creation':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'source': [meta(p) for p in EXPECTED],
    'source_tree_digest_definition':'SHA256 of lexicographically sorted UTF8 path + NUL + sha256 + LF',
    'source_tree_digest':digest(''.join(p+'\0'+EXPECTED[p]+'\n' for p in sorted(EXPECTED)).encode()),
    'parent_inputs':[meta(p) for p in PARENTS],
    'supplement_members_independently_verified':verified,
    'supplement_member_count':len(verified), 'supplement_member_bytes':sum(x['bytes'] for x in verified),
    'accepted_root_contract_receipt':meta(accept_path),
    'accepted_contract_packet_seal_bytes_verified_only':contract_seals,
    'binding_cost_document_member':doc_entry,
    'unperformed_parent_verification':'Did not rehash every member of original454/correction814 or accepted651-member union; root prior custody is not new independent credit.',
    'additional_source_bound_claim_inputs':[meta('verification/swift-cache-state-implementation/correction-1/proofs/'+n) for n in ['source-accounting.md','source-work-ledger.json','lifetime-ledger.json','correction-work-and-lifetime.md']],
    'scope_inputs':[meta('AGENTS.md'),meta('PLAN.md'),meta('docs/swift-cache-state-implementation-review-plan.md')],
    'platform':platform.platform(), 'python':sys.version,
    'command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'tool_versions':{'git':'git version 2.56.0','rg':'ripgrep 15.2.0 (rev e89fff89ac)','Python':'3.14.8'},
    'no_product_tests_harness_or_model_execution':True,
    'no_compiler_execution':True,
    'no_native_capture_ui_device_or_process_inventory':True,
    'mutation_scope':REL+'/**',
    'preparation_errors':[
        'A targeted rg referenced nonexistent implementation/README.md and exited2; no evidence inferred from it.',
        'Initial ls of this new review directory exited1 because it did not yet exist.',
        'An early recursive text search returned excessive truncated contract metadata; subsequent conclusions use exact bounded document/source reads.'
    ],
})

write('cost-model-review.json', {
    'schema':1, 'binding_source':{'path':'docs/swift-semantic-adapter-prerequisite.md','sha256':PARENTS['docs/swift-semantic-adapter-prerequisite.md'],'lines':[244,266]},
    'accepted_requirements':[
        'Each actual micro-operation, loop guard, fixed copy, LE conversion, complete Result and caller move maps exactly once.',
        'At most16 named scalar operations per scalar group; at most128 bytes per distinct fixed-copy group.',
        'Selected seven group maxima are not interchangeable; no optimizer elision; missing mapping blocks acceptance.'
    ],
    'not_explicitly_defined_by_binding_passage':[
        'A formal primitive-operation grammar, including whether every index address/read/check is individually named and how complete reference/Range moves are atomized.',
        'Mandatory ceil(scalars/16) independently at every helper/copy/iteration site, prohibiting transport of partially filled scalar capacity between sites within G6.'
    ],
    'selected_producer_site_partition':'Inherited source-accounting.md explicitly assigns each st/sq3, direct copy2, scalar commit2, clear2 and restore2, and says only adjacent scalar operations fuse. Those local proof claims can be assessed under a consistent local model.',
    'independent_atomization_for_conditional_tests':{
        'index':'bound predicate, indexed address, element read:3',
        'arithmetic':'one per written arithmetic operation; literals cost0',
        'range':'one complete Range constructor plus start<=end and end<=len predicates:3',
        'view':'one favorable complete borrow/view creation',
        'copy':'one separate payload-copy group plus one length-equality scalar predicate',
        'omissions':'loops, local binding and argument/scalar/unit movement are excluded from lower cores, never declared free in a complete proof'
    },
    'conclusion':'Supplement18-operation restore core is reproducible and refutes its inherited one-scalar-block iteration claim under the stated site/atomization model.645 is a conditional model result, not a numeric bound compelled solely by accepted definitions. A different grouping convention needs explicit source-bound complete proof and root acceptance; it cannot silently repair the selected ledger.',
    'measured_runtime_overrun':False,
    'new_cost_model_silently_accepted':False,
})

def op(i, line, text):
    return {'id':i,'source_line':line,'operation':text,'scalar_units':1}

restore_ops = [
    op('R01',785,'CELLS[i] index bound predicate'),op('R02',785,'CELLS[i] indexed address'),op('R03',785,'CELLS[i] element read'),
    op('R04',785,'cell*8'),op('R05',785,'SCALAR.base + selected offset'),
    op('R06',786,'i*8'),op('R07',786,'888 + destination offset'),
    op('R08',789,'destination+8'),op('R09',789,'destination Range constructor'),
    op('R10',789,'destination start<=end'),op('R11',789,'destination end<=Candidate length'),op('R12',789,'exclusive destination view'),
    op('R13',789,'source+8'),op('R14',789,'source Range constructor'),
    op('R15',789,'source start<=end'),op('R16',789,'source end<=arena length'),op('R17',789,'shared source view'),op('R18',789,'source/destination length equality'),
]
commit_ops = [
    op('C01',754,'6+i (or17+i at759)'),op('C02',754,'source index*8'),op('C03',754,'SC + source offset'),
    op('C04',755,'ROW_CELLS[i] index bound predicate (or EXTRA_CELLS[i] at760)'),op('C05',755,'cell indexed address'),op('C06',755,'cell element read'),op('C07',755,'cell*8'),op('C08',755,'SCALAR.base + destination offset'),
    op('C09',756,'destination+8'),op('C10',756,'destination Range constructor'),op('C11',756,'destination start<=end'),op('C12',756,'destination end<=arena length'),op('C13',756,'exclusive destination view'),
    op('C14',756,'source+8'),op('C15',756,'source Range constructor'),op('C16',756,'source start<=end'),op('C17',756,'source end<=Candidate length'),op('C18',756,'shared source view'),op('C19',756,'source/destination length equality'),
]
assert sum(x['scalar_units'] for x in restore_ops)==18
assert sum(x['scalar_units'] for x in commit_ops)==19
commit_endpoints=[]
for i,cell in enumerate([21,22,23,17,128,130,131,137,84,141]):
    commit_endpoints.append({'loop':'ROW_CELLS','index':i,'source':[1688+(6+i)*8,1688+(6+i)*8+8],'destination':[base+cell*8,base+cell*8+8]})
for i,cell in enumerate([71,78]):
    commit_endpoints.append({'loop':'EXTRA_CELLS','index':i,'source':[1688+(17+i)*8,1688+(17+i)*8+8],'destination':[base+cell*8,base+cell*8+8]})

segments = [
    {'id':'B1','source_lines':[642,671],'name':'built publication staging','derivation':'one64-byte tail copy + nonempty scalar site =2; resident st at643,644,645,646,660,661 =6; pin st662..667 =6; sq647,651,670,671 =4; (12+4)*3+2=50','copy_groups':33,'minimum_scalar_site_groups':17,'conditional_groups':50},
    {'id':'B2','source_lines':[707,730],'name':'final scalar stages','derivation':'six sq at707,708,709,728,729,730; each two distinct LE-array/destination copies plus >=one scalar site','copy_groups':12,'minimum_scalar_site_groups':6,'conditional_groups':18},
    {'id':'B3','source_lines':[734,751],'name':'built resident and pin commits','derivation':'resident64 + pin48 copies; plan_delta remains ABSENT on branch11; >=one scalar site each','copy_groups':2,'minimum_scalar_site_groups':2,'conditional_groups':4},
    {'id':'B4','source_lines':[753,762],'name':'ten ROW_CELLS plus two EXTRA_CELLS commits','derivation':'twelve distinct8-byte payload copies;19-operation scalar core needs two local groups each','copy_groups':12,'minimum_scalar_site_groups':24,'conditional_groups':36},
    {'id':'B5','source_lines':[779,783],'name':'one zero source initializer and256 explicit stores','derivation':'one8-byte initializer/source-to-zero move +256 separate8-byte payload stores; each iteration has nonempty scalar site; no assertion full scalar iteration fits16','copy_groups':257,'minimum_scalar_site_groups':256,'conditional_groups':513},
    {'id':'B6','source_lines':[784,790],'name':'twelve restores','derivation':'twelve8-byte payload copies;18-operation scalar core needs two local groups each','copy_groups':12,'minimum_scalar_site_groups':24,'conditional_groups':36},
]
assert sum(x['conditional_groups'] for x in segments)==657
write('operation-tables.json',{
    'schema':1,'source_sha256':EXPECTED[SOURCE+'cache_state.rs'],
    'model_reference':'cost-model-review.json; all numerical lower bounds conditional on explicit site/atomization model',
    'restore_core':restore_ops,'restore_core_scalar_operations':18,
    'commit_core':commit_ops,'commit_core_scalar_operations':19,
    'iteration_copy':'One distinct8-byte payload movement. Index element access and scalar references do not move those payload bytes.',
    'missing_above_cores':['iterator construction/next/Option/guard/advance/final test','source/destination let binding transfers','actual method argument and receiver transfers','complete Range/reference field transfers beyond the favorable one-operation forms','returned/received unit and cleanup bool','constant region field reads'],
    'actual_commit_endpoints':commit_endpoints,
    'built_publication_segments':segments,
    'original_conditional_subtotal_before_ADMIN':657,
    'supplement_conditional_subtotal_before_ADMIN':645,
    'difference':'Supplement B4 retained24, but identical atomization requires at least36; +12.',
    'with_only_literal_restore_and_proved24_restores_conditional_subtotal_before_ADMIN':645,
    'selected_G6_cap':640,'no_ADMIN_credit_added':True,
    'conditional_original_excess_before_ADMIN':17,
    'conditional_literal_only_excess_before_ADMIN':5,
    'not_runtime_or_machine_instruction_measurement':True,
})

write('literal-restore-review.json',{
    'schema':1,'source_sha256':EXPECTED[SOURCE+'cache_state.rs'],'proposal_sha256':meta(literal_path)['sha256'],
    'verdict':'All12 byte mappings are equivalent for the exact admitted arena/Candidate and CELLS constants; optimization proposal sound at byte-mapping level only. Not a complete G6 repair and not selected/implemented/executed.',
    'independent_endpoint_method':'For each handwritten cell from envelope.rs16: source=7729760+8*cell; destination=888+8*i; both widths8; compare exact proposal fields and statement. Arithmetic checker is static proof validation, not execution of product/model.',
    'endpoints':restore_endpoints,
    'source_max_exclusive':7731056,'destination_union':[888,984],
    'disjoint_from_semantic_committed_scalar_cells':[21,22,23,17,128,130,131,137,84,141,71,78,138],
    'literal_core_per_statement':[
        'destination Range construction','destination start<=end','destination end<=Candidate length','exclusive destination view',
        'source Range construction','source start<=end','source end<=arena length','shared source view','copy length equality'
    ],
    'literal_core_scalar_count':9,'payload_copy_groups_per_statement':1,
    'required_before_selection_as_complete_fix':[
        'Root must explicitly select a concrete repair scope; original sealed packets remain immutable. The current12-restore-only proposal is insufficient under its own model.',
        'Close or repair scalar commit753..762:19-operation core already exceeds one local scalar block. No optimizer or cross-group margin may erase it.',
        'Specify and accept exact source-operation atomization/group boundaries; record each omitted argument/reference/Range/unit/bool/loop movement exactly once.',
        'For all12 literal restores prove every complete scalar block<=16 including arguments, received unit and cleanup caller bool. Nine named core operations alone do not establish that.',
        'Independently close st/sq full operation and distinct array-move maps; G3 four-load comparator<=8 including caller scalars; G6 ADMIN exact named blocks and every branch.',
        'Preserve cleanup guard, sole8-byte zero source,256 explicit stores,12 identical restores, borrow lifetime, poison and both-leaf disablement, all API/projection/terminal ordering/caps.',
        'Replace coarse lifetime buckets with per-place source/receive/drop/peak maps in fixed29344 role union, complete values<=512 and Candidate2048.',
        'Only after root source admission, perform separately authorized host compile/layout/API/behavior/private regression against new exact bytes. This review supplies zero such pass credit; native/phone checks remain paused/pending.'
    ],
    'product_changed':False,'repair_selected':False,
})

write('helper-and-admin-review.json',{
    'schema':1,'source_sha256':EXPECTED[SOURCE+'cache_state.rs'],
    'STORE':{
        'source_lines':[156,164],
        'st_value_flow':['u64 n caller source -> received parameter (scalar transfer)','n.to_le_bytes LE conversion','complete8-byte returned LE-array source -> received temporary (copy1)','shared borrow of received LE array (scalar view)','at..at+8 checked mutable destination range and view (scalar work)','copy_from_slice length guard (scalar)','LE-array temporary -> destination8 payload (copy2)','returned/received unit, argument/receiver transfers (scalar)'],
        'sq_additional_flow':['c/i/n received wrapper arguments','8*i and SC+offset','Candidate-to-slice borrow/coercion and st argument transfers','st unit received and sq returned/received unit'],
        'copy_lower_bound_st_or_sq':2,
        'scalar_block_bound_closed':False,
        'why':'Two distinct array movements are justified by the source and no optimizer elision. Exact<=16 scalar block for wrapper+helper is not supplied by merely counting these arrays; each caller indexed value/arithmetic must also have exactly one owner.'
    },
    'G3LD':{
        'source_lines':[149,155,265,267],
        'worst_path':'both runs nonempty, b!=ABSENT and a!=ABSENT -> four actual ld calls',
        'load_sites':[
            {'id':'L1','line':265,'address':'src+left*8','payload':'index a'},
            {'id':'L2','line':266,'address':'src+right*8','payload':'index b'},
            {'id':'L3','line':267,'address':'a as usize*8','payload':'timestamp[a]'},
            {'id':'L4','line':267,'address':'b as usize*8','payload':'timestamp[b]'}
        ],
        'ld_value_flow':['b/at scalar argument transfers','at+8, Range source/receive, two range predicates and shared slice view','first_chunk length predicate and complete Option<&[u8;8]> source/received','expect tag test/unwrapping and borrowed array view','dereferenced8-byte array -> from_le_bytes by-value argument: one payload copy','LE decode -> u64 scalar return/received and caller binding'],
        'minimum_distinct_payload_copies_on_worst_path':4,
        'difference_from_st':'ld has no returned LE-array. Its from_le_bytes returns u64, so inheriting st two-array-copy count as exact would be wrong; conversely merely claiming ld one-copy+one-scalar is unproved.',
        'eight_group_obligation':'Four payload copies leave four scalar groups (<=64 named operations if appropriately partitioned) for all four ld flows, caller offset/cast/argument/binding, a/b ABSENT tests, short-circuit path, timestamp<= and returned take_left. Map G3 versus G4 tail/loop work disjointly.',
        'numeric_overrun_asserted':False,'bound_closed':False,
        'sort_structural_observation':'32+48+56+60+62+63=321 comparisons and6*64=384 transfers are structurally plausible from six passes; this is not executable or per-comparison source-cost qualification.'
    },
    'ADMIN4':{
        'source_lines':[710,730,734,765,775,797,1209,1211],
        'required_named_rows':[
            {'id':'A1','owner':'G6 stage','operations':'w[1] actual checked read; match dispatch; applicable w[13] branch; stage source/received; two stage==0 predicates/branches and conditional field reads into sq arguments. sq internals must not be counted twice.'},
            {'id':'A2','owner':'G6 row controls','operations':'resident_delta, pin_delta, plan_delta ABSENT tests/branches; row offset/binding work not already in row-copy site; commit_succeeded production true return/receive and !/branch; poison-return branch owns complete reply under G7.'},
            {'id':'A3','owner':'G6 scalar-loop controls','operations':'both loop Range/iterator/Option source/received and entry/final tests; interior index/body/next/control must be in the exact iteration table or here once.'},
            {'id':'A4','owner':'G6 pending scalar control','operations':'w[1] checked read, kind6 equality/branch; optional pending st argument offset/value receives only on EvictBegin, disjoint from built branch.'},
            {'id':'A5','owner':'G6 cleanup','operations':'cleanup argument/receiver borrow transfer; b.len read; exact-length equality/branch; clear-loop and restore-loop creation/final tests; final bool return/receive, caller ! and conditional latch branch. Original restore controls disappear only after actual selected literal repair.'}
        ],
        'selected_allowance_groups':4,'selected_allowance_named_scalar_ops_at_most':64,
        'numeric_overrun_asserted':False,'closed_four_blocks':False,
        'reason':'The source-bound producer ledger assigns4 without an exact list/partition. It has not established<=64 distinct scalar operations or each<=16 block and has not reconciled all caller-owned paths. We do not invent a stage-match linear comparison count or assign guard/reply work to two groups.'
    },
    'administration_not_zero_in_complete_proof':True,
})

write('lifetime-review.json',{
    'schema':1,'source_sha256':EXPECTED[SOURCE+'cache_state.rs'],
    'positive_source_facts':[
        'Public File API at1391..1398 expands cache_body! at1397 directly. Generic cache_core1380..1388 is cfg(test); no production forwarding Result layer.',
        'Finish256 then setup512 reservations1296..1297 precede Paid1298..1302 and Progress1311..1315; failures propagate before these new owners.',
        'Candidate2048 initialized once1097 after old envelope and semantic guard reservations; no by-value Candidate in shown path.',
        'Semantic call1175..1181 returns a reference-free24-byte reply; ordinary audit1191..1208 is followed by sole cleanup1209 before next iteration/I/O. Private loan references cannot escape reply.',
        'Successful typed aggregate is inline1372..1376; write_report? and final budget error precede it. New public complete result is488 by prior declared compiler receipt, not remeasured here.'
    ],
    'exact_source_place_table':[
        {'id':'P1','place':'Paid initializer source and paid destination','birth':[1298,1302],'last_use':1348,'role':'wire256','required':'two24-byte complete places; reservation branches and drop/move boundary'},
        {'id':'P2','place':'Progress initializer source and p destination, q[0;16] source','birth':[1311,1315],'last_use':1348,'role':'control1280','required':'144-byte source/received plus nested128 initializer; show permitted nonoverlap/reuse without optimizer'},
        {'id':'P3','place':'config None source, outer Option<Fixture>, parsed Fixture Result/source/f, Some(f) source','birth':[1316,1275,1277],'last_use':1348,'role':'setup256 plus inherited parser roles','required':'Fixture72, Option/Result80 source/receive and80 Some source; no inferred reuse of distinct places; exact shared/move phases and errors'},
        {'id':'P4','place':'Loan literal source/received, semantic_steps literal source/received, record and semantic argument views','birth':[1165,1181],'last_use':1208,'role':'control1280','required':'full source16/received16 loan and budget movement, borrow ends and audit-before-cleanup phase'},
        {'id':'P5','place':'semantic reply constructor/source, returned value, received local','birth':[174,186,318,322,738,742,766,770,1175],'last_use':1208,'role':'control1280/G7 work','required':'branch-specific reply source24/received24 with no extra unassigned owner'},
        {'id':'P6','place':'zero[8] initializer source and zero local','birth':779,'last_use':783,'role':'wire256','required':'one16-byte source/receive union; loop borrows and complete Range/Option positions'},
        {'id':'P7','place':'projection extent zero/enum initializer source, z source, caller cache_state destination','birth':[910,914,1348],'last_use':[1368,1375],'role':'report2896','required':'early-return projection paths,256 observation movements, source zero extent240, post-projection error drops'},
        {'id':'P8','place':'aggregate constructor source, Ok payload destination, public complete Result source, immediate external caller complete Result','birth':[1372,1376,1397],'last_use':'external return/drop','role':'report2896','required':'exact ownership of constituent framing104/envelope128/cache256, every488-byte move, tag/source/destination, caller source and two512 complete Result reservations; role aliases cannot silently hide a place'},
        {'id':'P9','place':'caught result/error; observation/decision; report and final budget errors; early admission errors','birth':[1291,1297,1303,1317,1329,1332,1342,1368,1370],'last_use':'matching propagation, projection or drop','role':'inherited fixed errors and report128','required':'complete Result<bool,AnalyzerError> source/receive and AnalyzerError32 source/receive/caller; no aggregate on early error'}
    ],
    'remaining_required_subplace_maps':[
        'helper192: exact nested rr/pr/pl/ld/st/cq/sq arguments, u64 results,8-byte LE-array sources/received, Range16, slice16 and Option/reference source/received; maximum simultaneous phase and sequential reuse',
        'Option112 and leaf256: checked_add/checked_sub complete source/received/tag/success/error values with every event/local binding and branch drop',
        'wire174 remainder: identify each actual borrow, iterator, Option, Range, unit, bool, scalar source/receive and cleanup phase; a remainder is no place map',
        'Progress/Paid/config index rows incorrectly point to callee function ranges rather than actual macro construction; replace births with exact table above',
        'Full P01-P35 plus inherited caller map and exact report/result construction/drop phases; fresh independent layouts only under a separately selected host execution scope'
    ],
    'selected_caps':{'role_union':29344,'reserved':41984,'global':65536,'max_complete_value':512,'Candidate':2048,'setup':512,'finish':256,'guard':128},
    'role_union_proved':False,'numeric_storage_overrun_asserted':False,
    'no_stack_RSS_or_optimizer_claim':True,
})

write('verdict.json',{
    'schema':1,'status':'source-accounting acceptance blocked; literal restore proposal byte-equivalent but insufficient as sole repair',
    'source_sha256':EXPECTED[SOURCE+'cache_state.rs'],
    'independent_findings':[
        {'id':'F1','severity':'blocking proof model qualification','finding':'Binding definitions do not expressly prescribe per-source-site scalar rounding or exact index/range/reference atomization. Retain645 as conditional, not unconditional cap overrun. Selected producer local blocks are nevertheless unproved and fail under the supplement consistent explicit model.'},
        {'id':'F2','severity':'blocking local accounting','finding':'Restore core18 fits no single16-scalar group under explicit model; commit cores19 also fail. Original selected source conditional subtotal657 before ADMIN, not merely645. Same model with restore-only24 still gives645 before ADMIN.'},
        {'id':'F3','severity':'blocking repair completeness','finding':'All12 literal endpoint copies exactly preserve bytes from canonical envelope cells into Candidate888..984. They remove dynamic restore work but do not close scalar commits, helper bounds, ADMIN, G3 or lifetimes.'},
        {'id':'F4','severity':'blocking proof completion','finding':'Separate st/sq returned LE-array moves from ld scalar returns; close four-ld G3 comparison8 with named operations; close ADMIN4 and every branch; replace coarse helper/Option/wire/lifetime buckets with actual source/received/drop/peak maps.'}
    ],
    'source_contract_unchanged':True,'implementation_accepted':False,
    'complete_fix_selected':False,'original_packets_modified':False,
    'semantic_group_caps':[256,2560,2568,768,640,640,248],
    'semantic':7680,'inherited':471,'combined':8151,'preflight':8192,
    'tests_run':0,'product_or_model_execution':False,
    'limitations':[
        'Independent static source/proof validation only; producer counts and previous test receipts are not used as proof.',
        'No Rust compiler, source harness, hosted inspector/authority-driver/rejectedWorkerV2/broad hosted harness import or execution.',
        'No native/UI/capture/simulator/emulator/phone operations or process inventory; all new runtime/device checks pending.',
        'No measured runtime, instruction, stack/RSS or unconditional numeric cap-overrun claim.',
        'No source/test/product/CLI/root-metadata/index/commit changes; root owns selection and delivery. No release/dogfood/GA qualification.'
    ]
})

excerpt_ranges={
    'cache_state.rs':[(104,173),(246,287),(306,340),(625,797),(901,918),(1072,1116),(1159,1214),(1251,1398)],
    'analyzer.rs':[(27,35),(68,105),(257,263)],
    'envelope.rs':[(1,20),(77,86)],
}
parts=['# Source-bound excerpts\n\nExact frozen source hashes appear in custody.json. These are text evidence only.\n']
for name,ranges in excerpt_ranges.items():
    lines=source_text[name].splitlines()
    parts.append('\n## '+SOURCE+name+'\n')
    for lo,hi in ranges:
        parts.append('\n```text\n'+'\n'.join(f'{i}: {lines[i-1]}' for i in range(lo,hi+1))+'\n```\n')
doc=(ROOT/'docs/swift-semantic-adapter-prerequisite.md').read_text().splitlines()
parts.append('\n## Accepted definition: docs/swift-semantic-adapter-prerequisite.md\n\n```text\n'+'\n'.join(f'{i}: {doc[i-1]}' for i in range(219,321))+'\n```\n')
(OUT/'source-excerpts.md').write_text(''.join(parts))

(OUT/'README.md').write_text('''# Independent source accounting review

The source-work proof remains blocked. The supplement's restore core18 is
reproducible under its explicit site/operation model. The same independent
derivation gives19 operations per scalar-commit iteration:12 commits require
at least36 groups in that model. The original source subtotal is657 before
administration. Literalizing only restores to a proved24 would leave645 before
administration, above G6=640 under that same model.

This is a conditional source-model blocker, not a measured runtime overrun.
The accepted contract fixes16 named scalar operations/group, distinct fixed
copies<=128 bytes/group, exact-once mapping, unchanged group caps and no optimizer
elision. It does not expressly specify local rounding at every helper/iteration
or the full primitive grammar. Root must retain that qualification and accept
any precise replacement convention before using it. The producer's selected
local block assertions are not currently proved under any complete mapping.

All12 proposed literal endpoints exactly match source cell and destination
formulas. This validates byte mapping, not the total cost or implementation.
`literal-restore-review.json` states all remaining selection conditions;
`operation-tables.json` gives independent named operation and copy tables;
`helper-and-admin-review.json` separates st/sq, G3 ld, and ADMIN obligations;
`lifetime-review.json` gives corrected actual source births and missing places.

Reproduce static validation with:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-accounting-independent-review/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-accounting-independent-review/verify_review.py
```

The first command writes only this review directory and refuses changed parent
hashes. It does not execute producer builders or Rust. Rebuilding changes time
and custody HEAD metadata and requires resealing; original packets stay intact.
The verifier only validates the frozen packet and static table arithmetic.
No product/model/compiler/harness/native/device execution or process inventory
occurred. No implementation, complete lifetime union, release, dogfood or GA
acceptance is supplied. Root controls repair selection and delivery.
''')

print(json.dumps({'status':'static proof validation passed; independent verdict written','owned':REL,'supplement_members':len(verified),'supplement_bytes':sum(x['bytes'] for x in verified),'restore_core':18,'commit_core':19,'conditional_original_before_ADMIN':657,'conditional_literal_only_before_ADMIN':645,'product_tests':0}))
