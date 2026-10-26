#!/usr/bin/env python3
"""Author the source-only C3 lifetime proposal. Never import upstream code."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C3 = 'verification/swift-cache-state-implementation/correction-3/'
SOURCE = C3 + 'source/library/cache_state.rs'
EXPECTED = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
def digest(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
def read(p): return json.loads((ROOT / p).read_text())
def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

assert digest(SOURCE) == EXPECTED
inputs = [
 'AGENTS.md', 'docs/swift-semantic-adapter-prerequisite.md',
 'docs/swift-cache-state-clear128-selection.md', 'docs/swift-cache-state-g6-accounting-selection.md',
 C3 + 'candidate-repo-seal.json', SOURCE, C3 + 'source/library/analyzer.rs', C3 + 'source/library/envelope.rs',
 C3 + 'proofs/phase-lifetime-inventory.json',
 'verification/swift-semantic-adapter-root-review/correction3-host-results.json',
 'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json',
 'verification/swift-cache-state-g6-complete/seal.json',
 'verification/swift-cache-state-g6-complete/local-places.json',
 'verification/swift-cache-state-g6-complete-independent/seal.json',
 'verification/swift-cache-state-g6-complete-independent/receiver-correction.json',
 'verification/swift-ordered-retention-analyzer-envelope-root-review/absence-implementation-acceptance.json',
 'verification/swift-envelope-absent-state-correction/proposal-1/seal.json',
 'verification/swift-envelope-absent-state-correction/proposal-1/type-lifetime-delta.json',
 'verification/swift-envelope-absent-state-correction/proposal-1/src/analyzer.rs',
 'verification/swift-envelope-absent-state-correction/proposal-1/src/envelope.rs',
 'verification/swift-envelope-absent-state-accounting-review/seal.json',
 'verification/swift-ordered-retention-analyzer-envelope-correction/inputs/accepted-inventory.json',
 'verification/swift-ordered-retention-analyzer-envelope-correction/logical-inventory.json',
]
manifest = [{'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': digest(p)} for p in inputs]
write('inputs.json', {'schema': 1, 'members': manifest, 'method': 'explicit selected local references only; no upstream code imported or executed'})
old = read(inputs[-1])
roles = {'Candidate': (2048, 0, 2048), 'Control': (6656, 1280, 8192), 'IO': (1472, 0, 4096), 'Metadata': (2400, 0, 4096), 'Report': (4296, 2896, 8192), 'Setup': (5168, 256, 12288), 'Wire': (2616, 256, 3072)}
assert old['named_role_upper_total'] == 24656
binding=[]
for name in ('analyzer', 'envelope'):
    before = (ROOT / f'verification/swift-envelope-absent-state-correction/proposal-1/src/{name}.rs').read_bytes()
    after = (ROOT / (C3 + f'source/library/{name}.rs')).read_bytes()
    assert after.startswith(before)
    binding.append({'name': name, 'inherited_prefix_bytes': len(before), 'inherited_prefix_sha256': hashlib.sha256(before).hexdigest(), 'appended_utf8': after[len(before):].decode(), 'whole_sha256': hashlib.sha256(after).hexdigest()})
write('inheritance.json', {
 'schema': 1, 'root_acceptance': inputs[15], 'root_acceptance_sha256': digest(inputs[15]),
 'selected_inventory': inputs[-1], 'selected_inventory_sha256': digest(inputs[-1]),
 'selected_envelope_source_sha256': binding[1]['inherited_prefix_sha256'],
 'logical_roles': {k: v[0] for k,v in roles.items()}, 'logical_bytes': 24656,
 'source_prefix_bindings': binding,
 'inherited_scope': 'Exact old safe-File framing/envelope sources and their accepted finite source/transfer/lifetime closure. No live VM recount. All inherited slots remain charged, including slots unnecessary on the new path.',
 'new_path_crosswalk': [
  {'old': 'analyze_fixture_envelope_core360..382', 'new': 'cache_body1304..1394', 'inherited': 'File/reference handles, Budget, output safety, arena Vec24, Framing80, envelope Progress144, caught Result40, AnalyzerError32, decisions, finalize128, framing104, write_report, all source/received/error/metadata places', 'deltas': 'Paid, p, config, extra reservations, semantic projection, expanded public aggregate/Result are separately enumerated'},
  {'old': 'observe_inputs_fixture_envelope_v1350..358', 'new': 'cache_inputs1269..1301', 'inherited': 'three Stamp72 bindings and initial Results80, fixture Result80/f72, profile f72/source+received unit Results40, three stable Stamp72 transfers and Results40, bool result40', 'deltas': 'p/paid/config handles, Some(f) config80 and f borrow into cache_walk'},
  {'old': 'walk_fixture_envelope_v1298..348', 'new': 'cache_walk1090..1268', 'inherited': 'Reader48; header512 source/destination; candidate initializer2048 in Setup and retained2048 in Candidate; loop Range/Option; w128; record8; envelope steps16 and received reply128; footer512; drain/I/O/early Results40; prior scratch payload aliases Candidate', 'deltas': 'thin arena8 explicitly added, semantic guard result40, altered setup st helpers, p/paid f handles, semantic call and cleanup'},
 ],
 'old_and_new_values_not_doubled': ['Arena Vec24 is distinct from thin arena8 and slice16 references; references do not duplicate heap payload', 'Candidate initializer2048 is inherited Setup; Candidate destination2048 and all its subranges are one existing payload', 'envelope reply128 inside e144 is contained storage; received reply128 remains a separate inherited source/received slot', 'new aggregate fields framing104/envelope128/cache_state256 are contained in each whole488 aggregate; field endpoints alias those exact whole owners'],
 'all_old_source_closure_reaccepted_here': False,
})

# Named Rust places: lexical endpoints are block ends, never last-use or optimizer retirement.
named=[]
def n(fn, names, sizes, lines, end, origin='new', role='Control'):
    if isinstance(sizes,int): sizes=[sizes]*len(names)
    if isinstance(lines,int): lines=[lines]*len(names)
    for name,size,line in zip(names,sizes,lines):
        named.append({'id': f'{fn}.{name}@{line}', 'function':fn, 'rust_name':name, 'bytes':size, 'birth_line':line, 'lexical_end_line':end, 'role':role, 'origin':origin, 'source_received_rule':'initializer/source and named received owner are distinct at transfer; source ends with its producing statement or callee return; named owner ends at stated lexical block'})
n('cache_body',['stream','profile_file','context','output','limit'],[8]*5,[1304,1305,1306,1307,1308],1395,'inherited')
n('cache_body',['budget','output_initial','arena','s','e','result','observation','decision','framed','envelope','framing'],[56,72,24,80,144,40,32,8,1,128,104],[1309,1321,1322,1323,1324,1335,1347,1348,1349,1365,1367],1395,'inherited')
n('cache_body',['paid'],24,1316,1395,role='Wire')
n('cache_body',['p'],144,1329,1395)
n('cache_body',['config'],80,1334,1395,role='Setup')
n('cache_body',['err'],32,1350,1359,'inherited',role='Report')
n('cache_body',['cache_state'],256,1366,1395,role='Report')
n('cache_inputs',['stream','profile_file','context','arena','budget','s','e'],8,1269,1301,'inherited')
n('cache_inputs',['p','paid','config'],8,1269,1301)
n('cache_inputs',['before_s','before_p','before_c','f'],72,[1281,1282,1283,1293],1301,'inherited',role='Setup')
n('cache_walk',['input','budget','s','e'],8,1090,1268,'inherited')
n('cache_walk',['arena','f','p','paid'],8,1090,1268)
n('cache_walk',['length'],8,1095,1268,'inherited')
n('cache_walk',['reader','h','candidate'],[48,512,2048],[1101,1102,1115],1268,'inherited')
n('cache_walk',['setup.i','setup.at'],8,[1116,1117],1129)
n('cache_walk',['index','w','offset','record','steps','received_envelope'],[8,128,8,8,16,128],[1141,1149,1151,1159,1160,1166],1233,'inherited')
n('cache_walk',['loan','semantic_steps','received_semantic'],[16,16,24],[1183,1187,1193],1230)
n('cache_walk',['snapshot.i'],8,1209,1211)
n('cache_walk',['target','available','n','count','foot'],[8,8,8,8,512],[1235,1238,1239,1248,1262],1268,'inherited')
n('semantic',['b','c','loan','p','steps'],[16,8,8,8,8],306,773)
n('semantic',['w','f'],8,[326,327],773)
n('semantic',['resident_delta','pin_delta','plan_delta','total','count','found','first_empty','first_pin','resident_pins','live_tokens','release_nonce_matches'],8,list(range(350,361)),773)
n('semantic',['body','stage'],8,[441,710],773)
n('semantic',['snapshot.i','extra.i'],8,[343,347],349)
n('semantic',['resident.slot','occupied','function','bytes','pins'],8,[362,363,364,365,366],402)
n('semantic',['resident.sum'],8,376,387)
n('semantic',['fill.slot'],8,403,406)
n('semantic',['pin.pin','entry','nonce'],8,[407,408,409],431)
n('semantic',['plan.cell','plan.prior','plan.outcome'],8,[478,479,480],513)
n('semantic',['plan.i'],8,497,509)
n('semantic',['miss.cell','headroom','remaining','mask','destination'],8,[515,542,543,544,545],568)
n('semantic',['feasible'],1,561,568)
n('semantic',['prefix.i','prefix.slot','prefix.next'],8,[546,550,554],560)
n('semantic',['outstanding','expected','evict.slot'],8,[573,574,582],613)
n('semantic',['publish.slot_u64','publish.slot_usize','prior_pins','pins'],8,[626,630,653,654],672)
n('semantic',['built.sum'],8,648,652)
n('semantic',['release.slot','release.pin'],8,[674,675],701)
n('semantic',['release.i'],8,695,697)
n('semantic',['resident.at','pin.at','plan.at'],8,[735,746,750],752)
n('merge',['c'],8,246,287)
n('merge',['src','dst','width'],8,[247,248,249],287)
n('merge',['base'],8,251,286)
n('merge',['left','mid','end','right'],8,[253,254,255,256],283)
n('merge',['out','index_at'],8,[257,269],281)
n('merge',['take_left'],1,258,281)
n('merge',['a','b'],8,[265,266],268)
n('merge',['left.at','right.at'],8,[270,274],277)
n('cleanup',['b','c'],[16,8],777,815)
n('projection',['p','paid','s','input','env','f_option'],8,919,1089)
n('projection',['z'],256,928,1089,role='Report')
n('projection',['e'],8,937,951)
n('projection',['child','f_binding','q','stage'],8,[967,1018,1032,1033],1089)
n('projection',['active','planned','pending'],1,[1034,1035,1036],1089)
for fn, names, sizes, line, end in [
 ('ld',['b','at'],[16,8],149,155),('st',['b','at','n'],[16,8,8],156,158),
 ('cq',['c','i'],[8,8],159,161),('sq',['c','i','n'],[8,8,8],162,164),
 ('rr',['b','row','field'],[16,8,8],165,167),('pr',['b','row','field'],[16,8,8],168,170),('pl',['b','row','field'],[16,8,8],171,173),
 ('reject',['reason'],[8],174,180),('poison',['debit'],[8],181,187),('selected_mask',['slots'],[8],188,194),
 ('shape_q',['q','calls','latch','n','f'],[8]*5,195,237),('why',['n'],[8],896,918),
 ('Progress.first_pin',['self','n'],[8,8],116,123),('Progress.terminal',['self'],[8],113,115),
 ('Progress.latch_terminal',['self','n'],[8,8],124,126),('Progress.remember_pin',['self','n'],[8,8],127,129)]: n(fn,names,sizes,line,end)
write('named-places.json', {'schema':1,'source':SOURCE,'source_sha256':EXPECTED,'places':named,'source_column_convention':'1-based inclusive line; lexical end conservatively includes full block. Nested-loop/error exact subphase restrictions live in phases.json; named places never retired at last use.'})

# Correct inherited role owners using the exact old role/lease closure, rather
# than treating every inherited value as new Control storage.
inherited_roles={
 'cache_body': {'output_initial':'Metadata','arena':'Setup','e':'Report','result':'Report','observation':'Report','decision':'Report','envelope':'Report','framing':'Report','err':'Report'},
 'cache_inputs': {'before_s':'Metadata','before_p':'Metadata','before_c':'Metadata','f':'Control'},
 'cache_walk': {'reader':'IO','h':'Wire','candidate':'Candidate','w':'Wire','record':'Wire','received_envelope':'Report','foot':'Wire'},
}
for item in named:
    if item['origin']=='inherited':
        item['role']=inherited_roles.get(item['function'],{}).get(item['rust_name'],'Control')
        item['inheritance_binding']='inheritance.json selected source/prefix/function crosswalk and upstream named role/lease closure'
write('named-places.json', {'schema':1,'source':SOURCE,'source_sha256':EXPECTED,'places':named,'source_column_convention':'1-based inclusive line; lexical end conservatively includes full block. Nested-loop/error exact subphase restrictions live in phases.json; named places never retired at last use.'})

# Complete helper endpoint templates. Byte payload references alias existing storage;
# only explicitly produced LE or anonymous arrays add payload storage.
templates={
 'write_sq_st': [
  ('sq_caller_sources',24,'c,i,n'),('sq_received',24,'c,i,n'),('offset_operand_residue',32,'one active bounded arithmetic primitive and outer operand'),
  ('st_caller_sources',32,'slice.data,slice.len,at,n'),('st_received',32,'slice.data,slice.len,at,n'),
  ('to_le_self_source',8,'u64'),('to_le_self_received',8,'u64'),('to_le_array_source',8,'complete array'),('to_le_array_return',8,'complete designated array'),('to_le_array_received',8,'complete caller array'),
  ('Range_source',16,'start,end'),('Range_received',16,'start,end'),('Index_receiver_source',16,'data,len'),('Index_receiver_received',16,'data,len'),('Index_view_return',16,'data,len'),('Index_view_received',16,'data,len'),
  ('LE_array_borrow_source',8,'thin'),('LE_source_view',16,'data,len'),('copy_receiver_received',16,'data,len'),('copy_source_received',16,'data,len'),('bounds_operand_residue',32,'active bounds primitive and outer operand'),
  ('Candidate_array_address_source',8,'thin address when forwarding Candidate'),('Candidate_exclusive_reference_source',8,'thin coercion reference'),('Region_complete_source',24,'conservative base/length/width source'),('copy_receiver_source_reborrow',16,'complete data,len reborrow')],
 'read_forward_ld': [
  ('row_forward_caller_sources',32,'caller b.data+b.len,row,field'),('row_forward_received',32,'rr/pr/pl received b.data+b.len,row,field'),
  ('Region_constant_source',24,'base,length,width complete constant value'),('offset_operand_residue',32,'bounded arithmetic source/received operands; one active primitive and a retained outer operand'),
  ('ld_caller_sources',24,'b.data,b.len,at'),('ld_received',24,'b.data,b.len,at'),
  ('Range_source',16,'start,end'),('Range_received',16,'start,end'),('Index_receiver_source',16,'data,len'),('Index_receiver_received',16,'data,len'),('Index_return_view_source',16,'data,len'),('Index_return_view_received',16,'data,len'),
  ('first_chunk_receiver',16,'data,len'),('first_chunk_Option_source',8,'complete Option<&[u8;8]>'),('first_chunk_Option_return',8,'complete designated Option'),('first_chunk_Option_received',8,'complete caller Option'),
  ('expect_Option_source',8,'source moved Option'),('expect_Option_received',8,'complete self'),('expect_message_source',16,'static-string data,len'),('expect_message_received',16,'static-string data,len'),('expect_reference_return',8,'complete array borrow'),('expect_reference_received',8,'complete array borrow'),
  ('from_le_array_received',8,'complete by-value array; source is borrowed existing payload'),('from_le_word_source',8,'u64'),('from_le_word_received',8,'complete u64 received in ld'),('ld_designated_word',8,'u64'),('caller_word_received',8,'u64 received in forwarding helper or immediate caller'),('forward_designated_word_source',8,'cq/rr/pr/pl complete returned u64'),('forward_word_received',8,'semantic or other caller complete u64'),('primitive_bounds_and_control',32,'maximum one active scalar primitive plus predicate; not all prior guard values simultaneously')],
 'checked_Option_u64': [
  ('self_source',8,'u64'),('self_received',8,'u64'),('rhs_source',8,'u64'),('rhs_received',8,'u64'),('sum',8,'u64'),('overflow',1,'bool'),('Option_constructor',16,'complete Option<u64>'),('Option_return',16,'complete Option<u64>'),('Option_received',16,'complete Option<u64>'),('pattern_binding',8,'u64'),('predicate',1,'bool'),
  ('is_none_or_self_received',16,'complete Option; source is existing Option_received'),('closure_capture_source',8,'immutable Fixture reference'),('closure_constructor',8,'captured reference'),('closure_received',8,'captured reference'),('closure_argument_source',8,'u64'),('closure_argument_received',8,'u64'),('closure_bool_source_return_received',3,'three complete bools'),('Option_method_bool_source_return_received',3,'three complete bools')],
 'loop_next': [('iterator',16,'Range start,end'),('receiver_source',8,'&mut Range'),('receiver_received',8,'&mut Range'),('Option_constructor',16,'complete Option<u64/usize> including None'),('Option_return',16,'complete Option'),('Option_received',16,'complete Option')],
 'loop_setup': [('Range_source',16,'start,end'),('IntoIterator_received',16,'start,end'),('iterator_return',16,'start,end'),('iterator_binding',16,'start,end')],
 'clear_metadata': [('Range_source',16,'start,end'),('Range_received',16,'start,end'),('Candidate_Index_receiver_source',8,'thin'),('Candidate_Index_receiver_received',8,'thin'),('destination_view_source',16,'data,len'),('destination_view_received',16,'data,len'),('copy_received_receiver',16,'data,len'),('anonymous_array_shared_reference',8,'thin reference to existing sole anonymous128'),('array_to_slice_source',16,'data,len'),('copy_received_source',16,'data,len'),('bounds_operands',16,'two8-byte values'),('bounds_bool',1,'bool'),('repeat_zero_operand',1,'u8'),('repeat_length_operand',8,'usize'),('extra_scalar_primitive',32,'one active bounded primitive with operand residue')],
 'copy_within_receiver': [('Candidate_address_source',8,'thin'),('exclusive_array_reference_source',8,'thin'),('coerced_slice_source',16,'data,len'),('received_receiver',16,'data,len'),('Range_source',16,'start,end'),('Range_received',16,'start,end'),('destination_source',8,'usize'),('destination_received',8,'usize'),('count_local',8,'usize'),('available_local',8,'usize'),('source_address',8,'usize'),('destination_address',8,'usize'),('bounds_operand_pair',16,'two8-byte'),('bounds_bool',1,'bool')],
 'copy_from_two_ranges': [('destination_Range_source',16,'start,end'),('destination_Range_received',16,'start,end'),('source_Range_source',16,'start,end'),('source_Range_received',16,'start,end'),('destination_receiver_source',16,'data,len; array receiver overbound'),('destination_receiver_received',16,'data,len; array receiver overbound'),('source_receiver_source',16,'data,len; array receiver overbound'),('source_receiver_received',16,'data,len; array receiver overbound'),('destination_view_return',16,'data,len'),('destination_view_received',16,'data,len'),('source_view_return',16,'data,len'),('source_view_received',16,'data,len'),('copy_receiver_received',16,'data,len'),('copy_source_received',16,'data,len'),('bounds_scalar_residue',32,'active primitive and retained operand')],
}
write('templates.json', {'schema':1,'templates':{key:{'places':[{'id':a,'bytes':b,'fields':c} for a,b,c in vals],'conservative_phase_union_bytes':sum(x[1] for x in vals)} for key,vals in templates.items()},'transfer_rule':'Distinct source/designated-return/received endpoints are separate complete objects. Generic templates intentionally union some sequential callee endpoints; this is an overbound, never optimizer credit. A contained field aliases its parent and gets no second payload allocation. Referenced Candidate/arena bytes are aliases, not produced arrays.','stdlib_scope':'Authored-source primitive boundary selected in G6. No libstd internal stack/allocator/ABI/RSS claim.'})
assert sum(v[1] for v in templates['write_sq_st']) <= sum(v[1] for v in templates['read_forward_ld'])

phases=[]
def phase(id, lines, active, note, inherited_phase='new_record_leaf_or_guard'):
    # active records are deliberately explicit source and received objects, not
    # an assumed helper192 or Option112 lease.
    rows=[]
    for name,size,role,endpoint in active:
        rows.append({'place':name,'bytes':size,'role':role,'endpoint':endpoint})
    totals={r:sum(p['bytes'] for p in rows if p['role']==r) for r in roles}
    phases.append({'id':id,'source_lines':lines,'inherited_phase':inherited_phase,'inherited_upper':{r:v[0] for r,v in roles.items()},'added_places':rows,'added_totals':totals,'composed_upper':{r:v[0]+totals[r] for r,v in roles.items()},'note':note})
def c(name,size,endpoint='received named/temporary'):return(name,size,'Control',endpoint)
def w(name,size,endpoint='received named/temporary'):return(name,size,'Wire',endpoint)
def s(name,size,endpoint='received named/temporary'):return(name,size,'Setup',endpoint)
def r(name,size,endpoint='received named/temporary'):return(name,size,'Report',endpoint)
def tpl(name,prefix=''):
    return [c(prefix+a,b,'explicit template source/received: '+fields) for a,b,fields in templates[name]]
paid=[w('cache_body.paid',24)]
p=[c('cache_body.p',144)]
outer=p+paid+[s('cache_body.config',80),c('cache_inputs.new_argument_sources(p,paid,config)',24,'three caller sources'),c('cache_inputs.new_received(p,paid,config)',24,'three received parameters'),c('cache_walk.new_argument_sources(p,paid)',16,'two caller sources'),c('cache_walk.new_received(p,paid)',16,'two received parameters'),c('cache_walk.f_source',8,'borrow source'),c('cache_walk.f_received',8,'borrow received'),c('cache_walk.arena',8,'thin received &mut Arena; distinct from inherited Vec24')]
loan=[c('cache_walk.loan',16),c('cache_walk.semantic_steps',16)]
call=[c('semantic.argument_sources',48,'b fat16,c8,loan8,p8,steps8'),c('semantic.received_parameters',48,'b fat16,c8,loan8,p8,steps8')]
leaf=[c('semantic.w/f',16),c('semantic.eleven_scalar_locals',88,'all eleven350..360 lexical locals'),c('semantic.body',8)]
phase('admission.pre-semantic-owners','1309..1315',[c('semantic_reservation_Result_source',40,'complete source unit Result'),c('semantic_reservation_Result_received',40,'complete received unit Result'),r('public_Err_Result_source',488,'complete public Result'),r('immediate_external_Result_received',488,'complete public caller Result')],'SF/SS failures precede Paid/p/config. Complete original error remains inherited; full488 Result capacity applies even to Err.','new_wrapper_admission')
phase('paid.constructor','1316..1320',[w('Paid_constructor',24,'source'),w('paid',24,'received')],'Source/local distinct; source ends at initialization statement.','new_progress_initialize')
phase('progress.constructor','1329..1333',paid+[c('q_zero_initializer',128,'array source'),c('Progress_constructor',144,'source containing q128'),c('p',144,'received containing q128')],'q source is distinct; constructor q and local q are contained fields.','new_progress_initialize')
phase('config.None','1334',p+paid+[s('None_Option_source',80,'full source Option<Fixture>'),s('config_Option_received',80,'full destination Option<Fixture>')],'All80 bytes counted for None; old Fixture parser belongs inherited Setup.','new_context')
phase('config.Some','1293..1295',p+paid+[s('config_old_None_destination',80,'same outer config storage'),s('Some_f_source',80,'complete source Option containing copied f72'),c('config_handle_source',8),c('config_handle_received',8)],'Existing f72 and Result<Fixture>80/source/received/profile72 stay inherited. Some payload aliases its Option owner; assigning config replaces the same80-byte storage.','new_context')
phase('walk.setup.st','1110..1139',outer+tpl('read_forward_ld','helper_overbound.')+[c('setup.iterator_and_received_Option',32),c('setup.i/at',16)],'Using456-byte explicit read/helper union also bounds st/sq424 setup frames; inherited candidate initializer2048 and destination2048 are both preserved.','new_header_and_candidate_initialize')
phase('loan.constructor','1183..1190',outer+[c('Loan_source',16,'constructor source'),c('Loan_received',16,'local'),c('StepBudget_source',16,'constructor source'),c('StepBudget_received',16,'local')],'Two statements sequential; conservatively retain both constructor sources for this phase. Record8,w128,envelope received128 remain inherited.','new_record_framing')
phase('semantic.resident.helper','350..402',outer+loan+call+[c('semantic.w/f',16),c('semantic.eleven_scalar_locals',88),c('resident.iterator',16),c('resident.Option_received',16),c('resident.slot',8),c('occupied/function/bytes/pins',32),c('sum_binding',8)]+tpl('read_forward_ld')+tpl('checked_Option_u64','checked.'),'Conservative superphase retains all local/helper and checked-Option endpoints even though helper and checked method finish sequentially.','new_record_leaf_or_guard')
phase('semantic.extra-cell.constant','347..349',outer+loan+call+[c('semantic.w/f',16),c('extra.iterator/Option_received',32),c('extra.i',8),s('EXTRA_CELLS_complete_literal_source',16,'constant array source; distinct from borrowed constant element')]+tpl('read_forward_ld'),'Materializes complete two-word constant conservatively. ROW_CELLS declaration has no production reference and creates no evaluated runtime owner.')
merge_places=[c('miss.cell',8),c('merge.argument_source',8),c('merge.received_c',8),c('merge.src/dst/width',24),c('merge.base',8),c('merge.left/mid/end/right',32),c('merge.iterator',16),c('merge.Option_received',16),c('merge.out',8),c('merge.take_left',1),c('merge.index_at',8),c('merge.a/b',16),c('merge.inner_at',8)]
phase('semantic.merge.helper','515..538;246..287',outer+loan+call+leaf+merge_places+tpl('read_forward_ld'),'Conservatively retains mutually sequential a/b and index_at/inner at. Nested read template456 includes explicit caller/source/received, complete Range and Option endpoints. No G3/G4 work acceptance is inferred.')
phase('semantic.merge.iterator.next-or-None','257',outer+loan+call+leaf+merge_places+tpl('loop_next','next.')+tpl('loop_setup','setup.'),'Loop next construction/return/caller Options16 are explicit including final None. This overcounts setup and body; no nested ld helper is active during next.')
phase('semantic.prefix.checked','542..568',outer+loan+call+leaf+[c('miss.cell/headroom/remaining/mask/destination',40),c('feasible',1),c('prefix.iterator',16),c('prefix.Option_received',16),c('prefix.i/slot/next',24)]+tpl('checked_Option_u64')+tpl('read_forward_ld','read.'),'Checked subtraction and rr source/received chain counted conservatively together; one iteration/template bounds all64, with lexical body end before next.')
phase('semantic.publish.checked','626..672',outer+loan+call+leaf+[c('publish.slot_u64/slot_usize/prior_pins/pins',32),c('built.sum',8)]+tpl('checked_Option_u64')+tpl('read_forward_ld','read.'),'Both shadowed slots counted. built.sum ends at652 before prior_pins653; including both is conservative.')
phase('semantic.copy-within','596 or642',outer+loan+call+leaf+[c('evict.outstanding/expected/slot_or_publish_two_slots',24)]+tpl('copy_within_receiver'),'Received data and len are distinct components. Candidate source and destination payload alias existing Candidate bytes; no duplicate64-byte allocation.')
phase('semantic.commit.copy','734..764',outer+loan+call+leaf+[c('semantic.stage',8),c('one_commit_at',8)]+tpl('copy_from_two_ranges'),'All arm-local scopes ended before common stage. No arm local is silently reused while still live; resident/pin/plan at blocks run sequentially.')
phase('semantic.reply.source-return-received','174..187;768..773;1193',outer+loan+call+leaf+[c('reply_helper_argument_source',8),c('reply_helper_received',8),c('reply_constructor',24,'complete source'),c('semantic_designated_reply',24,'complete return'),c('walk_received_reply',24,'complete received')],'Guard/paid/refusal/poison all have full24-byte replies. Semantic callee frames end before cleanup; G7/G128 work ownership is unchanged.')
cleanup_base=outer+loan+[c('walk.received_semantic',24),c('cleanup_argument_b',16,'source fat view data,len'),c('cleanup_argument_c',8,'source thin Candidate'),c('cleanup_received_b',16,'received fat view data,len'),c('cleanup_received_c',8,'received thin Candidate'),c('Vec_reference_source',8),c('Deref_received_Vec_reference',8),c('Deref_returned_slice_source',16,'received argument b aliases caller slice output, no second allocation')]
for i,line in enumerate(range(781,797)):
    phase(f'cleanup.anonymous128.{i:02}',str(line),cleanup_base+[w(f'anonymous128@{line}',128,'sole repeat-construction source payload')]+tpl('clear_metadata'),f'Exact statement clear [{i*128}..{(i+1)*128}]. Anonymous array ends at statement; next array cannot coexist. Its received slice points at same payload; all view data/len and Range start/end endpoints remain explicit.')
phase('cleanup.restore','797..808',cleanup_base+tpl('copy_from_two_ranges'),'No anonymous128 remains. Each8-byte payload source/destination is existing arena/Candidate storage; all ranges and views are complete.')
phase('cleanup.private-fault-and-return','809..814;1227..1229',cleanup_base+[c('atomic_receiver_source/received',16),c('atomic_value/ordering/bools',16),c('byte_Index_source/received',32),c('returned_bool/caller/not/predicate',5)],'cfg(test) fault explicitly separate; globals are static, the written Candidate byte aliases existing payload. Early length false return has fewer live places.')
phase('projection.constructor','919..950',p+paid+[s('config',80),c('projection_argument_sources',48),c('projection_received_parameters',48),c('config_as_ref_Option_source/received',16),r('extent_initializer',240,'array source'),r('observation_constructor',256,'source containing extent'),r('projection_z',256,'received containing extent')],'Initializer240 and struct256 source/local are separate; contents of a struct are aliases, not an extra object.','new_final_projection')
phase('projection.body','951..1088',p+paid+[s('config',80),c('projection_argument_sources',48),c('projection_received_parameters',48),c('projection.child/f/q/stage',32),c('projection.active/planned/pending',3),c('shape_q_caller_sources',40),c('shape_q_received',40),c('RangeInclusive_source/received',48),c('closure_capture/source/received_option',96),c('index_operand_residue',96),r('projection_z',256)],'Option<&Fixture>8 full source/received; Option<u64>16 checked operations are separate templates. shape_q ranges and closure handles explicitly bounded.','new_final_projection')
phase('projection.return','950,955,965,1008,1013,1016,1021,1030,1088',p+paid+[s('config',80),c('projection_argument_sources',48),c('projection_received_parameters',48),r('projection_z',256,'source local'),r('projection_designated_observation',256,'complete returned observation'),r('cache_state_received',256,'complete caller observation')],'Every early projection return uses complete256-byte type. Callee z/params end at return, before outer report work.','new_final_projection')
# The old inventory already charges five232 aggregate/Result slots. Widening each
# to488 adds256 each, including full Err and immediate caller/extraction values.
expanded=[r(f'inherited_aggregate_Result_slot_{i}_growth',256,'old232 capacity +256 = full488; exact whole object fields are contained') for i in range(1,6)]
obs_union=[r(f'new_observation_slot_{i}',256,'initializer240-or-observation256 source/received phase slot; no simultaneous alias') for i in range(1,6)]
phase('public.aggregate-Result-caller-role-union','1366..1415; external immediate receiver',p+paid+[s('config',80)]+expanded+obs_union+[r('new_error_source/received_reserve',128,'four complete32 error values; full public Err still488')],'Conservative role union: five inherited aggregate slots grow232->488 (+1280); five new observation slots256 (+1280); error128. Total2688<=2896. Explicit owner schedules are in return-moves.json. No contained field is an additional full aggregate.','new_public_return_or_getters')
phase('new.getters','54..103;816..895',[( 'self_source',8,'Control','source borrow'),('self_received',8,'Control','received borrow'),('return_source/received',16,'Control','two complete8 words/references'),('Index_source/received_and_control',96,'Control','explicit bounded index/operand superphase')],'One getter at a time, returned enum/reference/word8; false bool returns use1. No forwarding-stack bound.','new_public_return_or_getters')
for ph in phases:
    for role,(_,addition,reserved) in roles.items():
        assert ph['added_totals'][role] <= addition, (ph['id'],role,ph['added_totals'][role],addition)
        assert ph['composed_upper'][role] <= reserved
peaks={role:max(ph['added_totals'][role] for ph in phases) for role in roles}
write('phases.json',{'schema':1,'source_sha256':EXPECTED,'phase_rule':'Role upper is accepted inherited full bound plus explicit new phase places. Keeping the full inherited bound on every new phase is deliberately conservative; old helper slots are never spent as credits. Distinct live source/received endpoints have distinct rows. Phases are finite source templates, not runtime observations.','phases':phases,'added_role_peaks':peaks,'claimed_role_union':{role:v[0]+v[1] for role,v in roles.items()},'fixed_role_union_bytes':29344,'composed_peak_role_sum':sum(v[0]+peaks[k] for k,v in roles.items()),'reserved_bytes':41984,'global_bytes':65536,'global_unassigned_margin_used':0,'whole_lifetime_proof_accepted':False,'proposal_only':True})

write('return-moves.json', {'schema':1,'aggregate_bytes':488,'complete_public_Result_bytes':488,
 'scope':'One public invocation, its designated return and immediate external caller complete receiver plus one extraction/branch. Arbitrarily deep user forwarding is outside the inherited contract.',
 'slots':[{'id':i,'old_bytes':232,'new_bytes':488,'growth_bytes':256} for i in range(1,6)],
 'phases':[
  {'id':'observation_init','owners':{'repeat_extent_source':240,'observation_ctor':256,'z':256},'distinct_source_received':True},
  {'id':'observation_return','owners':{'z_source':256,'designated_observation':256,'cache_state_received':256},'distinct_source_received':True},
  {'id':'aggregate_construct','owners':{'field_sources_framing_envelope_cache_state':488,'aggregate_ctor':488},'contained':{'aggregate_ctor':[104,128,256]},'no_extra_field_payload':True},
  {'id':'Ok_construct','owners':{'aggregate_ctor_source':488,'Ok_Result_source':488},'contained':{'Ok_Result_source':['Ok_payload488']},'no_extra_field_payload':True},
  {'id':'designated_return','owners':{'Ok_Result_source':488,'public_designated_Result':488},'complete_Err_also_488':True},
  {'id':'external_receive','owners':{'public_designated_Result_source':488,'immediate_caller_Result_received':488},'complete_Err_also_488':True},
  {'id':'external_extract','owners':{'immediate_caller_Result_source':488,'extract_method_self_received':488,'extract_designated_aggregate':488,'caller_aggregate_received':488},'rule':'Conservative source/callee/designated/received union4x488 uses four of five expanded slots; source public callee has already ended. Err uses complete Result488 self/source with original Error32 payload values separate. No Copy/Clone or elision assumed.'}
 ],
 'all_early_errors':[
  {'sites':'1309..1315','full_Result':488,'new_owners_exist':False,'note':'Budget/new/wrapper/SF/SS errors return before Paid/p/config. Error32 and complete unit/Budget Results64 remain inherited; source+public+caller complete488 receiving slots are expanded.'},
  {'sites':'1321..1322','full_Result':488,'new_owners':['Paid24'],'note':'Output safety/Arena error returns no aggregate; all stamp/IO/metadata and error values inherited.'},
  {'sites':'1281..1299;1103..1265','full_Result':40,'note':'Private input/walk Results40 source/received and original Error32 remain complete; result40 remains in outer scope through finalize/projection. Extra semantic_guard Result40 source/received is no larger than inherited maximal setup/report unit Result pair; phase walk.setup.st explicitly adds a larger helper overbound.'},
  {'sites':'1386..1388','full_Result':488,'note':'write_report/budget failures after cache_state256 construction retain lexical p/paid/config/result/envelope/cache_state/framing while complete Err488 is propagated and received. New report role union includes five observation slots and expanded five public488 slots plus four extra32 errors.'}
 ],'public_success_and_error_authority':False})
source_lines=(ROOT/SOURCE).read_text().splitlines()
loops=[(250,286,'merge width while'),(252,283,'merge base while'),(257,281,'merge Range output'),(343,345,'snapshot16'),(347,349,'extra2'),(362,402,'resident max64'),(403,406,'fill max64'),(407,431,'pin max64'),(497,509,'plan stage5'),(546,560,'prefix64'),(695,697,'pin reset6'),(1116,1129,'setup12'),(1141,1233,'paid record loop; one iteration at a time'),(1209,1211,'snapshot receive16'),(1236,1259,'bounded structural drain')]
loop_rows=[]
for a,b,kind in loops:
    is_for=source_lines[a-1].lstrip().startswith('for ')
    loop_rows.append({'line':a,'end_line':b,'scope':kind,'excerpt':source_lines[a-1],'source_excerpt_sha256':hashlib.sha256(source_lines[a-1].encode()).hexdigest(),'source_received_templates':['loop_setup','loop_next'] if is_for else ['scalar_while_guard'],'final_None_complete':is_for,'body_received_Option_bytes':16 if is_for else 0,'body_binding_bytes':8 if is_for else 0})
copy_rows=[]
for line in [278,534,596,635,642,692,736,747,751,*range(753,765),*range(781,809)]:
    text=source_lines[line-1]
    copy_rows.append({'line':line,'excerpt':text,'template': 'clear_metadata' if 781<=line<=796 else 'copy_within_receiver' if line in (278,596,642) else 'copy_from_two_ranges','payload_alias':'Candidate/arena existing payload; sole anonymous128 source only for781..796','source_excerpt_sha256':hashlib.sha256(text.encode()).hexdigest()})
option_rows=[{'line':line,'excerpt':source_lines[line-1],'template':'checked_Option_u64','complete_source_bytes':16,'complete_designated_return_bytes':16,'complete_received_bytes':16} for line in (376,530,554,648,654)]
write('source-sites.json',{'schema':1,'source':SOURCE,'source_sha256':EXPECTED,'loops':loop_rows,'copy_sites':copy_rows,'checked_Option_sites':option_rows,'other_Options':{'projection.f':{'line':925,'bytes':8,'source_received_each':8},'config':{'None_line':1334,'Some_line':1295,'full_source_received_each':80},'ld.first_chunk':{'line':152,'full_source_return_received_each':8}},'navigation_not_authorization':'Exact excerpts are source-location anchors for the independently authored manual mapping; syntax presence alone proves no lifetime, operation bound, implementation or OTA authority.'})
write('coverage.json',{
 'schema':1,'status':'complete authored source-role/lifetime proposal for independent review; not accepted',
 'source':SOURCE,'source_sha256':EXPECTED,'named_places':len(named),'phase_templates':len(phases),
 'functions':{'read_helpers':'ld/st/cq/sq/rr/pr/pl149..173: explicit read_forward_ld456 and write_sq_st424 source/received templates; st/sq superphase fits the456-byte helper bound, including complete LE array source/return/received and fat slice receivers', 'semantic':'306..773 all parameters/named locals/loops/event arms/common stage/commit/replies covered', 'merge':'246..287 source-only G3/G4 storage; comparisons/work remain pending', 'cleanup':'777..815 all16 anonymous128 statements,12 restore statements,private fault,early length false and returned bool covered', 'projection':'919..1089 all parameters,initializer/ctor/z,early returns,shape_q,Option/closure/ranges,published extents and complete returned256 covered', 'walk_inputs_macro_public':'1090..1415 inherited source crosswalk + added params/config/source/received/guards/semantic/caller/error phases', 'scalar_helpers':'Progress.terminal/first_pin/latch_terminal/remember_pin, reject/poison,selected_mask,shape_q,why; complete parameter/return sources/received words in456 helper phase or128 getter bound', 'getters':'All26 semantic observation extent getters, borrowed boundary/reason,three borrowed aggregate members,and eight literal-false getters: per-call128 superphase; no new retained payload.'},
 'explicit_finite_repetition':{'snapshot':16,'extra_cells':2,'resident_rows_max':64,'pin_rows_max':64,'merge_passes':6,'merge_outputs_per_pass':64,'prefix':64,'plan_stage':5,'pin_reset':6,'semantic_projection_words':30,'clear_statements':16,'restore_statements':12},
 'complete_Options':['Option<u64>/Option<usize>16 constructor + designated return + caller received, including final None','Option<&[u8;8]>8 complete source/return/received','Option<&Fixture>8 source/received','Option<Fixture>80 source/config destination; inactive bytes never omitted'],
 'prior_claims_not_inherited':['helper192','Option112','leaf256','wire174'],
 'newly_unrun_pending':['compiler/native/device layout beyond already accepted host receipt','independent accounting review','G3/G4 and combined source work acceptance','independent implementation replay','real-source binding/custody','native/device/signing/store/customer/operations/FieldLog/GA'],
 'no_compiler_product_runtime_native_UI_capture_process_inventory_git_or_hosted_action':True,
 'no_production_source_or_old_packet_writes':True,
 'source_accounting_or_GA_acceptance_granted':False})
write('build-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'python_executable':sys.executable,'context_revision_from_frozen_root_receipt':read('verification/swift-semantic-adapter-root-review/correction3-host-results.json')['head_context_only'],'source_tree_digest_from_candidate_seal':read(C3+'candidate-repo-seal.json')['source_tree_digest'],'build_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'phase_templates':len(phases),'named_places':len(named),'added_role_peaks':peaks,'proposal_only':True})
print(json.dumps({'status':'proposal-built','named_places':len(named),'phase_templates':len(phases),'added_role_peaks':peaks,'fixed_union':29344,'accepted':False},sort_keys=True))
