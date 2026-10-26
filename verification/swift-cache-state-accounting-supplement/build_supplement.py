#!/usr/bin/env python3
"""Read frozen production/evidence bytes; write proof proposal only. No execution."""
import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,data):(ROOT/path).write_text(json.dumps(data,indent=2)+'\n')
base=REPO/'verification/swift-cache-state-implementation/correction-1'
review=REPO/'verification/swift-cache-state-independent-review/implementation-review-1/accounting-review.json'
assert sha(review)=='c15df868773e646cdf472a09415d676e8978e4d04816d79da93c6a28e1dda42a'
expected={'analyzer.rs':'ad039daac5de9ea811da70261ae6591dfe6846e23bea1a87fc013755b502af6e','cache_state.rs':'1ffc4ee5bb37c4ca2794c456f66bfcd9f1916090a0de3a548c19b6c82a3767b9','envelope.rs':'11aee91058837ba13a9000c44d30e93049f3011be46ea9493110bb81b8ab4798'}
for n,h in expected.items():assert sha(base/'source/library'/n)==h
# Verify every original and corrected sealed byte without running any contained tool.
seals=[]
for root,h in [(base.parent,'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'),(base,'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6')]:
 p=root/'candidate-repo-seal.json';assert sha(p)==h;s=json.loads(p.read_text())
 for m in s['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
 seals.append({'path':str(p.relative_to(REPO)),'sha256':h,'members_verified':len(s['members']),'all_members_unchanged':True})
source=base/'source/library/cache_state.rs';lines=source.read_text().splitlines(keepends=True)
def seam(id,first,last):
 raw=''.join(lines[first-1:last]);return {'id':id,'path':str(source.relative_to(REPO)),'source_sha256':sha(source),'first_line':first,'last_line':last,'excerpt_utf8':raw,'excerpt_sha256':hashlib.sha256(raw.encode()).hexdigest()}
seams=[seam(*v)for v in [('helpers',149,173),('merge',246,287),('built-publication',619,671),('final-stage-and-commit',705,770),('cleanup',775,797),('caller-cleanup',1165,1211),('config-flow',1251,1282),('public-macro-owners',1284,1377),('public-expansion-site',1389,1398)]]
save('proofs/source-seams.json',{'schema':1,'seams':seams,'binding_not_execution':True})
ops=[
 ('R01',785,'CELLS[i] index bound check'),
 ('R02',785,'CELLS[i] indexed element address'),
 ('R03',785,'CELLS[i] element read into value expression'),
 ('R04',785,'multiply selected cell value by8'),
 ('R05',785,'add SCALAR.base to source offset'),
 ('R06',786,'multiply i by8 for destination'),
 ('R07',786,'add888 to destination offset'),
 ('R08',789,'compute destination+8'),
 ('R09',789,'construct destination Range<usize> (one favorable scalar unit for both endpoints)'),
 ('R10',789,'check destination range start<=end'),
 ('R11',789,'check destination range end<=Candidate length'),
 ('R12',789,'create exclusive destination view/borrow (one favorable scalar unit for full view)'),
 ('R13',789,'compute source+8'),
 ('R14',789,'construct source Range<usize> (one favorable scalar unit for both endpoints)'),
 ('R15',789,'check source range start<=end'),
 ('R16',789,'check source range end<=arena slice length'),
 ('R17',789,'create shared source view/borrow (one favorable scalar unit for full view)'),
 ('R18',789,'copy_from_slice source/destination length equality guard'),
]
assert len(ops)==18
save('proofs/restore-operation-lower-bound.json',{'schema':1,'source_sha256':sha(source),'source_lines':[784,790],'unit_model':'proofs/cost-model.md','scalar_operations':[{'id':id,'line':line,'name':name,'units':1}for id,line,name in ops],'irreducible_scalar_operations_per_iteration_under_explicit_model':18,'maximum_named_operations_per_scalar_group':16,'minimum_scalar_groups_per_iteration':2,'copy_groups_per_iteration':1,'complete_copy_bytes':8,'minimum_groups_per_iteration':3,'iterations':12,'minimum_total_restore_groups':36,'claimed_total_restore_groups':24,'delta_to_old_restore_claim_at_least':12,'excluded_additional_work':['source/destination let binding transfers','loop iterator creation, next call, received Option/index, advancement and per-iteration guard','final loop test','method receiver and source argument transfers','complete Range source/received movement beyond one favorable unit per Range','fat-view scalar fields beyond one favorable unit per borrow','returned/received unit and cleanup returned/received bool','constant-region field reads','any check/dataflow removed only by optimizer'],'lower_bound_only':True,'measured_runtime_overrun':False,'cost_model_independently_accepted':False})
segments=[
 {'id':'B1','name':'built-publication event staging','lines':[642,671],'copies':33,'scalar_site_groups_at_least':17,'groups_at_least':50,'derivation':'one64-byte tail copy1+its scalar site1;12 st and4 sq each has complete LE-array received copy1, destination store copy1, and nonempty scalar site>=1;2+16*3=50','no_637_input':True},
 {'id':'B2','name':'six final scalar stages','lines':[707,730],'copies':12,'scalar_site_groups_at_least':6,'groups_at_least':18,'derivation':'sq indices0..5 exactly six sites; each two complete8-byte movements plus nonempty scalar site>=1;6*3=18','no_637_input':True},
 {'id':'B3','name':'resident+pin row commits','lines':[734,747],'copies':2,'scalar_site_groups_at_least':2,'groups_at_least':4,'derivation':'two fixed row copies64/48, each one copy and checked-address/borrow scalar site>=1; plan_delta remainsABSENT on this branch','no_637_input':True},
 {'id':'B4','name':'ten row+two extra scalar commits','lines':[753,762],'copies':12,'scalar_site_groups_at_least':12,'groups_at_least':24,'derivation':'12 fixed8-byte copies, each with a nonempty checked-address/borrow scalar iteration site>=1; loop prologues/final tests omitted here','no_637_input':True},
 {'id':'B5','name':'zero initializer+256 explicit clear stores','lines':[779,783],'copies':257,'scalar_site_groups_at_least':256,'groups_at_least':513,'derivation':'one8-byte zero initializer/source movement plus256 fixed8-byte destination copies; every clear iteration has checked-address/borrow scalar site>=1; all final/prologue work omitted','no_637_input':True},
 {'id':'B6','name':'twelve envelope restores','lines':[784,790],'copies':12,'scalar_site_groups_at_least':24,'groups_at_least':36,'derivation':'12*(one8-byte copy+ceil(18/16) scalar-site groups); full named operation list in restore-operation-lower-bound.json','no_637_input':True},
]
assert sum(v['groups_at_least']for v in segments)==645
save('proofs/group6-lower-bound.json',{'schema':1,'source_sha256':sha(source),'branch':'semantic kind11, built publication, successful guards/commits then normal cleanup','segments':segments,'minimum_before_administration_under_explicit_site_model':645,'selected_group6_ceiling':640,'excess_at_least':5,'administrative_groups_assumed':0,'source_only_claim':'source-derived blocker under explicitly stated ordered scalar-site model; not a measured runtime overrun or independent proof acceptance','independent_of_637_arithmetic':True,'no_credit_borrowed_or_cap_raised':True,'site_model_qualification':'Scalar blocks belong to a source call/iteration site, cannot carry unused scalar capacity across fixed-copy/helper/iteration boundaries. This is explicit and must itself be reviewed; the result is not claimed under an alternative pooled scalar-count convention.','unclosed_other_costs':['st/sq complete scalar blocks','G6 administrative block list','scalar-commit and clear exact scalar counts','G3 four ld paths','complete lifetime/place union'],'independent_accepted':False})
cells=[7,9,10,11,12,13,14,64,65,66,160,161];rows=[]
for i,cell in enumerate(cells):
 src=7729760+8*cell;dst=888+8*i
 rows.append({'index':i,'cell':cell,'source_start':src,'source_end':src+8,'destination_start':dst,'destination_end':dst+8,'bytes':8,'proposed_statement':f'c[{dst}..{dst+8}].copy_from_slice(&b[{src}..{src+8}]);'})
save('proofs/literal-restore-proposal.json',{'schema':1,'status':'unselected source-only proposal; not implemented or executed','target_source_sha256':sha(source),'replace_only_source_lines':[784,790],'proposed_calls':rows,'preserve':['fn cleanup signature','exact arena length guard','one8-byte zero initializer','256 explicit zero-word store loop','all12 restore bytes and destinations888..984-exclusive','test-only poison block and final bool','all public API,32 projection,terminal ordering,caps'],'removed_dynamic_work':['CELLS[i] check/address/read','source cell multiply/add','destination i multiply/add','two dynamic end additions','restore iterator/prologue/per-iteration/final control'],'remaining_work_to_reconcile':['two checked literal ranges and both borrows','copy length guard and method arguments/received unit','all12 literal copies','cleanup prologue and caller received bool','full G6 helper/admin reconciliation and caller lifetime union'],'hypothetical_per_restore_scalar_named_core':9,'hypothetical_group_bound_not_accepted':2,'proposed_total_restore_groups_if_complete_scalar_closure_fits16':24,'is_a_closed_fix':False,'no_product_or_test_file_changed':True,'no_compiler_or_test_executed':True,'independent_accepted':False})
save('proofs/open-obligations.json',{'schema':1,'status':'blocker proposal frozen promptly before product correction selection; remaining proof work explicitly open','target_source_sha256':sha(source),'items':[{'id':'ADMIN4','status':'open','actual_lines':[710,730,734,765,775,797,1209,1211],'required':'Every stage/row/pending predicate, both scalar-commit prologues/final tests, clear/restore final tests, cleanup prologue/length/return/received status; no assertion that all fit4 blocks.'},{'id':'STORE','status':'open','actual_lines':[149,173],'required':'Separate complete st/sq LE-array source/received/store and wrapper scalar transfers; old<=16 scalar bound unproved.'},{'id':'G3','status':'open','actual_lines':[265,267],'required':'Four actual ld paths, distinct LE input array flow and full scalar comparator; no inheritance of st bound and no claim8 groups closed.'},{'id':'LIFETIMES','status':'open','corrected_births':{'Paid':[1298,1302],'Progress':[1311,1315],'config_None':1316,'config_Some':1277,'Fixture_result_and_f':1275,'public_constructor_and_Ok':[1372,1376],'public_macro_site':1397},'required':'Every source/received/drop/peak owner within helper192,Option112,leaf256,wire174,Some/None/Fixture/inherited Result and aggregate/Ok/publicResult/immediate external caller; corrected birth indices are source facts only, not union proof.'}],'no_pending_proof_claimed_complete':True,'source_accounting_acceptance':False})
save('input-bindings.json',{'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),'review_input':{'path':str(review.relative_to(REPO)),'sha256':sha(review),'purpose':'proof-deficiency input only; no independent tests/glue/oracle read'},'source':{str((base/'source/library'/n).relative_to(REPO)):h for n,h in expected.items()},'immutable_seals':seals,'cost_definition_reference':{'path':'docs/swift-semantic-adapter-prerequisite.md','sha256':sha(REPO/'docs/swift-semantic-adapter-prerequisite.md'),'lines':[244,265]},'no_product_or_test_modification_or_execution':True,'no_native_capture_or_process_inventory':True,'source_accounting_acceptance':False})
print(json.dumps({'source_sha256':sha(source),'restore_core_scalar_operations':18,'minimum_restore_groups':36,'G6_before_any_administration':645,'cap':640,'excess_at_least_under_explicit_site_model':5,'original454_and_correction814_unchanged':True,'independent_accepted':False},indent=2))
