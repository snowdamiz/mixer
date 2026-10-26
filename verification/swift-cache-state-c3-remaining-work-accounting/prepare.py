#!/usr/bin/env python3
"""Write new packet metadata only; read exact, local, named source references."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,indent=2)+'\n')
INPUTS=[
 'AGENTS.md','docs/swift-semantic-adapter-prerequisite.md','docs/swift-cache-state-g6-accounting-selection.md',
 'verification/swift-semantic-adapter-prerequisite/contract.json',
 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs',
 'verification/swift-cache-state-implementation/correction-3/source/library/analyzer.rs',
 'verification/swift-cache-state-implementation/correction-3/source/library/envelope.rs',
 'verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json',
 'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json',
 'verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json',
 'verification/swift-cache-state-g6-complete/source-model.json',
 'verification/swift-cache-state-g6-complete/operation-templates.json',
 'verification/swift-cache-state-g6-complete/local-places.json',
 'verification/swift-cache-state-g6-complete/paths.json',
 'verification/swift-cache-state-g6-complete/seal.json',
 'verification/swift-cache-state-g6-complete-independent/receiver-correction.json',
 'verification/swift-cache-state-g6-complete-independent/seal.json',
 'verification/swift-cache-state-c3-lifetime-accounting/inputs.json',
 'verification/swift-cache-state-c3-lifetime-accounting/inheritance.json',
 'verification/swift-cache-state-c3-lifetime-accounting/return-moves.json',
 'verification/swift-cache-state-c3-lifetime-accounting/seal.json',
 'verification/swift-cache-state-c3-lifetime-independent/coverage-addendum.json',
 'verification/swift-cache-state-c3-lifetime-independent/seal.json',
 'verification/swift-envelope-absent-state-correction/proposal-1/ledger-delta.json',
 'verification/swift-envelope-absent-state-correction/proposal-1/guard-funding-proposal.json',
 'verification/swift-ordered-retention-analyzer-envelope-correction/step-inventory.json',
 'verification/swift-ordered-retention-analyzer-envelope-root-review/absence-implementation-acceptance.json',
]
rows=[]
for p in INPUTS:
 b=(ROOT/p).read_bytes();rows.append({'path':p,'bytes':len(b),'sha256':sha(b)})
save('inputs.json',{'schema':1,'scope':'local data/source bytes only; no old code execution/import','members':rows})
source=(ROOT/INPUTS[4]).read_text().splitlines(keepends=True)
spans=[('reply-progress-helpers',113,148),('read-store-helpers',149,185),('shape-q',196,237),('semantic-admission',306,340),('initial-delta-flags',350,352),('body-identity-and-event-guards',441,703),('semantic-paid-return',768,773),('projection',896,1089),('walker-inherited-and-new-boundaries',1090,1233),('inputs-wrapper',1269,1301),('public-wrapper',1302,1416)]
save('source-map.json',{'source_sha256':sha((ROOT/INPUTS[4]).read_bytes()),'spans':[{'id':n,'first_line':a,'last_line':b,'excerpt_sha256':sha(''.join(source[a-1:b]).encode())} for n,a,b in spans],'navigation_only':True})
save('ownership.json',{
 'schema':1,'caps':{'G1':256,'G2':2560,'G3':2568,'G4':768,'G5':640,'G6':640,'G7':248,'SS':512,'SF':256,'G128':128},
 'semantic_sum':7680,'old_combined_record':471,'new_combined_record':8151,'preflight':8192,
 'old_public_debit':'534*S_paid + 47*F_paid + 425*N_B',
 'new_public_debit':'512*SS_paid + 256*SF_paid + 7680*N_C',
 'bound_kind':'conservative complete authored-source covering proposal; not exact feasible-path maxima',
 'selected_here':False,'combined_source_work_accepted':False,'implementation_accepted':False,'GA_qualified':False,
 'owners':{
  'G1':['1158 new terminal dispatch before loan and 1177..1190 semantic admission/Loan16/StepBudget16 constructors','314..339 paid entry debit/config/prior guards','350..352 delta flags','441..451 fixture defined-body identity','452..703 branch admission/identity guards only; all helper loads in those guards'],
  'G7':['ld/cq bodies charged only through actual G1/G7 helper calls, never globally','174..185 paid complete SemanticReply constructor/helper designated/received/leaf designated/caller receive','616 repeated cq18 only in rejected readiness reason','1171..1181 new envelope poison and preloan unreadability p latches','1193..1225 actual paid semantic arguments/control, calls increment, audit, full snapshot16+remember_pin and latch'],
  'G128':['314..322 zero-debit leaf readability/entry-spent/underfunded checks and exact terminal reply/caller audit/latching; at most once'],
  'SS':['1314..1334 new report/setup/guard reservation call edges and Result40 receives, Paid24, Progress144+q array128 source, config80','1295 Some(f) Fixture72 -> payload and complete Option80 -> config','new p/paid/config fixed call borrows','1130..1139 four q defaults and six st calls; candidate initializer and twelve old envelope st remain inherited'],
  'SF':['896..1089 why/projection/shape_q/getter calls, zero extent240 constructor and full observation256 returns','1366 added projection arguments','1390..1394 complete488 aggregate/Result/public/caller and one immediate extraction','all new API errors retain complete Result488 including inactive bytes; no aggregate payload on Err'],
  'inherited':['Budget and old wrappers T42/F42, context/profile/header/admission/stability/drain/IO/report implementations and Candidate initializer2048 retain accepted predecessors','on the new API SF owns full public488 moves; old F42 public232 edges are replaced in the crosswalk rather than charged again; the old public entry remains unchanged'],
  'G6_selected_unchanged':['staged prior_pins ld/calculation at653..656','all staging/commit and every actual postloan cleanup','merge caller four edges only; callee unit/return remains G4'],
  'active_other_lanes':['G2 resident/token probes and seeds','G3/G4 merge body','G5 headroom/prefix/feasibility; no result from those proposals assumed']},
 'source_primitive_scope':'source operand -> received operand / operator / source result -> target; scalar Index20 plus expression and field projection; scalar IndexMut17 plus expression, field projection and final store; full Option16 copies including final None; complete real payload chunks<=128; at most16 named scalar primitives/group; no optimizer or inactive-enum credit',
 'guard_terminal_argument':'main constructs steps remaining7680/spent0; private zero forms terminate status2/reason1 or poison3, and caller immediately latches. Later p.terminal()==0 is false. G128 never pays cleanup, which stays selected G6.',
 'budget_invocation_ownership':'Every new report/setup invocation includes its actual authored Budget helper body at frozen analyzer.rs170..180; source reuse is not free. On successful SS admission report256/setup512/report128 helper work belongs SS. A failed initial SF report attempt plus fixed public Error suffix is F42, before any semantic aggregate owner. A failed SS attempt is SF because SF was already reserved. Existing Budget::new/T42/F42 bodies retain inherited funding and paths; this F42 recipe is not added to another inherited maximum.',
 'reservation_order':['Budget::new','setup SETUP_WRAPPER42','report FINAL_WRAPPER42','report SF256','setup SS512','Paid24 only now','output_safety','Arena::new','s/e/p/config','actual context/profile/header admission','old S534 / old F47 / old G112 / new G128','candidate construction and scalar mutation'],
 'admission_failure':'1309..1315 return complete Err Result488 using existing fixed Error32 chain; no Progress/observation/aggregate payload exists. SF is reserved before SS so a later SS failure retains SF funding. No guard or inactive branch is credit.',
 'all_unrun':['compiler / ABI remeasurement','product execution','native targets / simulator / emulator / device','UI / capture / process inventory','FieldLog release / signing / store / customers / operations / GA'],
})
save('necessary-lower-bounds.json',{
 'method':'strict actually required subtraces, not sufficient acceptance or upper bounds; additions never borrowed across owners',
 'rows':[
 {'owner':'G1','actual_subtrace':'release event12 requires two pr and five rr helper loads; seven full selected row-read templates','scalars':679,'copies':7,'groups_lower':50,'cap':256},
 {'owner':'G7','actual_subtrace':'successful caller reads cq16 snapshot iterations plus cq16 for remember_pin:17 complete cq templates','scalars':1411,'copies':17,'groups_lower':106,'cap':248},
 {'owner':'SS','actual_subtrace':'six new st calls: six slice literal/value templates62 scalars+2 real8-byte copies each; expressions add nonnegative work','scalars':372,'copies':12,'groups_lower':36,'cap':512},
 {'owner':'SF','actual_subtrace':'complete observation constructor/return chain and full488 constructor/Result/caller/extraction endpoints; selected explicit copy chain alone','scalars':0,'copies':36,'groups_lower':36,'cap':256},
 {'owner':'G128','actual_subtrace':'poison helper reply24 source/designated/received and semantic designated/caller24 require four real copies','scalars':0,'copies':4,'groups_lower':4,'cap':128}],
 'cap_obstruction_found':False,'floors_are_not_upper_acceptance':True})
save('local-places.json',{
 'source_layout_authority':'selected C3 lifetime union29344 and exact host Result488; no fresh compiler run',
 'roles_not_reallocated':True,'logical_role_union':29344,'selected_lifetime_selection_sha256':'ab2e74fa3fa7a6ff967a5c0d000d46336cc42dc5654c6b38fdce008fcafedaf4',
 'source_named_scopes':[
  {'owner':'G1','places':['semantic b slice16,c reference8,loan reference8,p reference8,steps reference8','w record words reference8,f Fixture reference8','resident_delta8,pin_delta8,plan_delta8','body8,cell8,prior8,outcome8,outstanding8,expected8,slot8 and publication shadowed slot8,pin8'],'ends':'semantic lexical function/arm scope; no retirement at last use'},
  {'owner':'G7/G128','places':['Loan16 constructor+caller local and borrowed pointer8','StepBudget16 constructor+caller local and borrow8','SemanticReply24 constructor, helper designated24, semantic received24, semantic designated24, caller received24','caller snapshot Range16/iterator16 and full next Option16 including final None; i8','cq/ld complete source/received arrays8, Some reference8, slice16, ranges16, helper parameters and u64 returns','latch/remember self8,n8, literal/operator/result8 temporaries'],'ends':'semantic helper frames before return; caller Loan/steps/received remain lexical-live through selected G6 cleanup'},
  {'owner':'SS','places':['Paid24 source and local','Progress144 source and local; q repeat128 source','config Option<Fixture>80 source/local; Fixture72 source for Some','each helper st slice16,Range16, LE source8/received8, copy source16/destination16, unit boundaries','public early Result488 source/designated/caller; active Error32 is separate; no semantic aggregate payload exists'],'ends':'q initializer after Progress statement; named Paid/Progress/config through outer wrapper scope'},
  {'owner':'SF','places':['projection refs p8,paid8,s8,input8,env8 and Option<&Fixture>8','z256 constructor/local, extent240 repeat source, designated observation256 and caller cache_state256','child8,f8,q8,stage8,active1,planned1,pending1 to source1088','shape_q all received ref/scalar operands, RangeInclusive24, closure self/argument/result and bool returns','actual field sources framing104/envelope128/cache_state256','aggregate488 constructor, complete Ok/Err Result488, public designated488 and caller received488','caller complete self488, designated extraction aggregate488, immediate caller aggregate488; Err self remains488, Error32 extraction'],'ends':'each helper by source call return; projection named locals survive return1088; outer wrapper values survive report error; external caller bounded to one receive/extraction'}],
 'not_a_new_lifetime_acceptance':'uses selected exact29344 source inventory only; machine stack/RSS/libstd/ABI/native remain outside'})
save('whole-setup-funding.json',{
 'scope':'complete actual setup-debit call sites on this selected new API; debit arithmetic, not a fresh detailed work proof for inherited helpers',
 'fixed_source_debits':[
  {'site':'cache_body1310','description':'SETUP_WRAPPER','debit':42},
  {'site':'cache_body1315','description':'SEMANTIC_SETUP','debit':512},
  {'site':'analyzer output_safety431','description':'four metadata/position/pairwise loops','debit':15},
  {'site':'analyzer Arena119..128','description':'12 Region checks +64 resident/pin/recency iterations +512 plan +128 window +32 top','debit':748},
  {'site':'cache_inputs1281..1283 / analyzer initial419','description':'three initial calls at2','debit':6},
  {'site':'analyzer fixture_context265..276','description':'1024 words +16 checked header +976 reserved words','debit':2016},
  {'site':'analyzer profile282..288','description':'64 header +3x4 echo','debit':76},
  {'site':'analyzer header303..307','description':'64 header +4x4 echo','debit':80},
  {'site':'cache_walk1105','description':'SETUP_ENVELOPE','debit':534},
  {'site':'analyzer footer364','description':'footer header checks','debit':64},
  {'site':'cache_inputs1297..1299 / analyzer stable426','description':'three stability calls at1','debit':3}],
 'fixed_sum':4096,'STREAM_CAP':536871936,'read_block_bytes':65536,
 'drain_iteration_bound':8194,
 'drain_argument':'ceil(STREAM_CAP/65536)+1. All nonfinal successful drain iterations advance to a checked positive next block or finish. At most one initially empty current block and one paid iteration ending in read failure are conservatively accommodated by using the whole-file ceiling plus1. Earlier return only removes suffixes. No profile row is setup-debited: its actual replay8 fee stays inherited.',
 'whole_setup_debit_upper':12290,'setup_cap':65536,
 'report_reserved_upper':6830,'report_cap':3000000,
 'report_formula':'old6446 +newSF256 +newG128128',
 'source_helper_work_new_calls':'SS.complete-new-source includes all new successful reservation helper invocations; SF.SS-admission-failure and F42.finish-admission-failure own actual failed-admission helper paths',
 'not_claimed':'old detailed setup/IO proof independently replayed; old source and accepted proof inherited via exact prefixes'})
print('prepared named local input custody, ownership, lower bounds and local places')
