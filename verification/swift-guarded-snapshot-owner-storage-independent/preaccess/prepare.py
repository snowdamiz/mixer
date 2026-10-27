"""Freeze source-bound owner/caller review expectations before producer access.

No producer imports, product execution, compiler invocation or process inventory.
The finite controls validate review requirements, not a product storage floor.
"""
from pathlib import Path
import copy, datetime, hashlib, json, platform, re, sys

HERE=Path(__file__).resolve().parent
V=HERE.parents[1]
AUTH=V/'swift-guarded-snapshot-scope-authority-correction'
OLD=V/'swift-guarded-snapshot-composition-source-preparation'
IND=V/'swift-guarded-snapshot-composition-independent'
E=V/'swift-guarded-snapshot-encoder-storage-closure'
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())
MAX=(1<<64)-1

def need(ok,label):
    if not ok:raise AssertionError(label)

def seal(directory,expected,count):
    content=(directory/'seal.json').read_bytes()
    need(sha(content)==expected,'frozen input seal')
    entries=json.loads(content)['members'];need(len(entries)==count,'frozen input count')
    need(len({e['path'] for e in entries})==count,'duplicate frozen input')
    for e in entries:
        p=directory/e['path'];need(p.resolve().is_relative_to(directory.resolve()),'input path escape')
        data=p.read_bytes();need((len(data),sha(data))==(e['bytes'],e['sha256']),'changed frozen input '+str(p))
    return dict(path=str(directory.relative_to(V)),seal_sha256=sha(content),members=count,
                member_bytes=sum(e['bytes'] for e in entries),all_members_verified=True)

C='src/experimental_swift_reactor/control.rs'
I='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
K='src/experimental_swift_reactor/cache.rs'
L='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
W='src/experimental_wasi/accounted.rs'
S='src/experimental/swift.rs'

# These are source regions and required families, not invented object arrays or
# an assertion that a partial roster is the complete final occurrence inventory.
GROUPS=[
 ('common_original_adoption',[(C,606,722),(C,1822,1844)],'common-before-admission',[
  'Original adapter parameters, core call-expression Result, adapter return and success/error handoff',
  'Closed Original foundation/retire_tickets/failure parameters, calls, returns and unit roles',
  'Retire helper source/metadata Option<ReservationTicket>, Some ticket patterns, refund call Results and primary move',
  'Shared adopt_body_core_v1 body/control/cursor/ticket/closure source roles alias inherited baseline by exact identity; add new boundary roles only']),
 ('common_original_constructor',[(I,125,186),(I,291,318)],'common-before-admission',[
  'Original wrapper/core argument and return boundary; associated branch argument and early-return calls',
  'OriginalAccess begin tuple return, access caller binding, shared_control receiver/reference return and guard-control argument',
  'Guarded primary/attempt tuple, primary/attempt patterns and finish parameters/call/return',
  'Original Attempt=()/Storage=() retain zero-sized identities; do not erase new nonzero adapter frames',
  'Unchanged original construction/header/rows/cleanup roles map to WrapperArguments/Phase/Emission/Caller/Move identities once']),
 ('selected_preconstruction_ingress',[(L,156,178),(C,1845,1859),(C,1905,1917)],'selected-before-admission',[
  'Actual selected carrier self parameter, proof/provenance patterns and AdoptionBody literal/return/call results',
  'SelectedSnapshotBody literal/binding/argument, consuming accessor self/return and budget/started/cancellation moves',
  'SnapshotAdoption foundation and independent source/metadata refund Results and combined retirement return',
  'SnapshotPreScopeFailure primary/retirement literal/return/error/pattern roles on every early refusal',
  'Actual Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1> return, caller Result, control/adopted pattern',
  'Scope full literal/Result/return/caller success/error/retained owner before Construction; None inline owners are not free']),
 ('consuming_owner_token',[(C,1878,1889),(C,1937,1944),(K,4868,4870),(I,541,544)],'selected-before-admission',[
  'SnapshotScopeBorrow literal, local, consuming outer call expression/parameter, forwarded inner argument/parameter',
  'Consuming into_parts receiver/self, four field patterns, tuple return, caller tuple result and four caller patterns',
  'Each actual token and actual four-part tuple is1240 bytes; field reference/Option/adopted roles are separately typed',
  'Replace old four raw wrapper/inner owner arguments with token route, relocating logical raw bindings to parts patterns',
  'Preserve unchanged private core raw arguments/outer result; no token Option/Result/array exists',
  'Token borrows end before scope move into Run; token grants no independent authority/ledger']),
 ('refused_full_phase_storage',[(I,324,356),(I,359,361),(I,385,406)],'selected-before-admission',[
  'Full begin tuple expression and return, Selected begin wrapper return, caller access/storage tuple/result/pattern',
  'Actual SnapshotPhaseStorage return/argument/move into branch.finish, Access::complete argument and refused drop argument',
  'Every source slot reachable on refused path is5328 bytes even when plan and transfer areNone',
  'Option<Plan>=128, Option<[u8;4096]>=4097 alignment1, Option<AError>=1096; whole storage5328 alignment8',
  'Admitted plan/Some transfer literal roles may be conditional; shared source return/parameter slots cannot be charged only conditionally']),
 ('shape_and_owner_helpers',[(I,362,406),(C,1987,2071),(K,4872,4896),(W,435,451),(S,1697,1703)],'selected-before-admission',[
  'Pairing/preflight/debit/shape/emission/commit call-result and error/return/move roles before conditional phase admission',
  'Actual decision closure captures/object/argument/body return and1096-byte Result<(usize,Shape,u64,u64),AError>',
  'Checked shape scalar/array/iterator/item/result/error slots and actual counts return; loops reuse declarations',
  'Owner/ticket/layout/stop/cancellation/helper chains include exact product parameters/returns/source temporaries',
  'Cache and WASI pairing fixed arrays/zip iterators/totals/counts and actual Construction/header/backing checks',
  'Unchanged inherited helper frames alias baseline once; new snapshot_* methods require closure, not a type-only list',
  'WorkAuditPending remains actual source behavior; a later emission-helper implementation requires separate source/slot binding']),
 ('writer_normalizers',[(I,419,439),(I,443,468)],'conditional-after-proved-admission',[
  'Six actual normalizer sites: View, Cursor, Block, output Metadata, row Metadata and stream-position u64',
  'Raw encoder/native Result, normalizer T parameter, post_stop, normalized return, writer call Result and success/error patterns/moves',
  'encode_result<T> alternatives View/Cursor/Option<Block>; io_result<T> alternatives Metadata/u64',
  'Measure each differing generic slot alternative; explicit per-role max under synchronous reuse or separately justified exact-instantiation recipe',
  'Two metadata caller Results remain distinct even though the generic helper template is reused',
  'Normalized View/Block/Metadata/u64 Results2248 bytes; normalized Cursor Result2600; raw encoder Result identities differ']),
 ('writer_closure_and_io_temporaries',[(I,414,514)],'conditional-after-proved-admission',[
  'Writer literal/progress and outer closure object/reference/callee argument/Result/return',
  'Actual stop map_err, absent-block closure, requested conversion, calls/acknowledged/bytes/block checked arithmetic closures',
  'Capture each exact writer/post_stop environment and all actual argument/move roles; no encoder16-byte representative substitute',
  'View/cursor/block owners and call Results, block Option conversion, requested byte views, slice/reference returns',
  '32-attempt range/iterator/item reused, native io Result and error patterns, Interrupted Option/take and post_stop Option',
  'Progress/error/observation/Attempt literal, return, patterns and persistent error moves',
  'Writer-only roles conditional only after admission and dead before completion; retained Attempt/Outer diagnostics require foundation']),
 ('optional_wasi_attachment',[(C,1867,1876),(C,1897,1901),(C,1918,1936)],'selected-before-admission',[
  'At most one concrete host attachment attempt; scope receiver/grants/budget/started/cursor and actual prepare Result/phase',
  'Actual Result<AccountedWasi,SwiftRunFailure>=1448 production or1496 unit, WASI success transfer and failure moves',
  'Original WASI prepare/construct/complete frames alias inherited phase inventory once',
  'Construction and completion Results, attachment literal/return/local/Some/retained Option and returned immutable reference',
  'Option<SnapshotWasiAttachmentV1>=2192 even whenNone; retained attachment survives finalizer and caller diagnostics']),
 ('retirement_all_eight',[(I,517,538)],'retained-through-host-return',[
  'Consuming Outer self, primary/export/completion patterns and all eight original outcomes',
  'Actual4024-byte seven-field match tuple expression/result plus seven caller patterns and all Some/failure/rejected-adopted moves',
  'Adopted proof cleanup argument/call Result and no-adopted unit success',
  'Actual7248-byte PrimaryRetirement literal/callee return, finalizer call Result/local/pattern/move']),
 ('selected_finalizer',[(C,1946,1974)],'retained-through-host-return',[
  'Consuming Run self and scope/outer patterns, consuming Scope control/adopted/cache/WASI/attachment/base patterns',
  'Actual WASI pairing Result/error/boolean/observation Option and usage return; .is_ok policy must be explicit',
  'Outer retirement call result, scope-adopted cleanup Result, cache cleanup Result/tail and complete args/results',
  'Failed cache Option drop keeps uncertain tickets; WASI cleanup and attachment/retirement Results are distinct',
  'Original finish_owned_cleanup usage call/return and actual13232-byte Finish literal/callee return/caller local/move',
  'Retain selected funding until surviving PrimaryRetirement/Finish/attachment/errors die; no base-equality or plan-drop shortcut']),
 ('selected_host_caller',[(I,592,648)],'retained-through-host-return',[
  'cfg(test) future_genuine_composition_v1::selected_owned_files_v1 is the selected concrete host route; no production caller exists',
  'Actual selected parameter/ingress receiver, scope Result and success/failure patterns, scope local and construct consuming move',
  'Engine ingress budget/Instant/Cancellation argument/result source temporaries must be classified explicitly',
  'Optional attachment call result/reference and immutable borrows, with at most1 actual call',
  'Run call result/local, outer_v1 receiver/return/reference caller binding with exactly1 getter call',
  'Actual outer diagnostic borrows end before consuming run.finish_v1 receiver; Finish return/local retained across later assertions to function end',
  'Host/unit Scope/Result8176 and Run14936; production8128/14888 remain separately pending',
  'Path/open/output/header-write/assertion/panic/test framework machinery excluded as nonzero external harness; engine-facing borrow/result slots still included']),
]

def validate_recipe(recipe):
    roles=recipe['roles'];ids=[r['id'] for r in roles]
    need(len(ids)==len(set(ids)),'duplicate source identity')
    for role in roles:
        need(role['multiplicity']==1,'invented source multiplicity')
        need(not (role['refused_reachable'] and role['funding']=='conditional'),'refused role charged after refusal')
        need(not (role['preconstruction'] and role['funding']=='conditional'),'preconstruction role funded late')
        need(not (role['retained'] and role['released_at']=='phase_completion'),'retained diagnostic unfunded')
        need(not role['invented_wrapper'],'invented Option/Result/array')
        need(role['alias'] is None or role['new_charge']==0,'baseline alias double charged')
        need(role['alias'] is None or (role['id']=='construct_profile_core_v1::inherited_wrapper' and role['alias']=='baseline::WrapperArgumentsV1'),'same-byte unrelated alias')
        if role['type']=='SnapshotPhaseStorageV1':need(role['bytes']==5328,'None shrinks full inline storage')
        if role['type']=='SnapshotScopeBorrowV1':need(role['bytes']==1240,'wrong token type size')
    need(recipe['encoder_E']==40531 and recipe['encoder_additive_terms']==1,'encoder aggregate double charge')
    need(recipe['attachment_calls'] in [0,1] and recipe['getter_calls']==1,'selected host call recipe')
    need(recipe['production_caller_accepted'] is False,'unit host mislabeled production caller')
    need(recipe['harness_cost']=='external-nonzero-unbounded-here','harness silently zero cost')
    need(not recipe['healthy_narrowing'],'surviving finalizer diagnostics lost funding')
    need(recipe['generic_alternatives']=={'encode_result':['View','Cursor','Option<Block>'],'io_result':['Metadata','u64']},'generic alternative omitted')
    need(recipe['metadata_caller_results']==2,'two metadata call results collapsed')
    need(not recipe['count_whole_inherited_engine_again'],'whole baseline counted twice')
    need(not recipe['replaced_raw_wrapper_owner_legs_counted'],'old raw arguments plus token counted')
    need(not recipe['caller_result_aliased_to_encoder_return'],'caller/callee result identity collapsed')
    need(recipe['pairing_diagnostic_policy']=='explicit-is_ok-discard-unattributed-observation','pairing diagnostic mislabeled cleanup result')
    return True

def controls():
    def role(identity,typ,size,**extra):
        return dict(id=identity,type=typ,bytes=size,multiplicity=1,refused_reachable=False,
                    preconstruction=False,retained=False,released_at='host_return',
                    funding='selected-foundation',invented_wrapper=False,alias=None,
                    new_charge=size,**extra)
    # Representative actual source identities, only for testing the review
    # invariants. This deliberately is not a complete byte inventory.
    roles=[role('begin_snapshot_access_v1::refused_storage_return','SnapshotPhaseStorageV1',5328),
           role('SnapshotScopeV1::construct_v1::owners','SnapshotScopeBorrowV1',1240),
           role('selected_owned_files_v1::finish','SnapshotScopeFinishV1',13232),
           role('construct_profile_core_v1::inherited_wrapper','inherited-source-role',0)]
    roles[0]['refused_reachable']=True;roles[0]['preconstruction']=True
    roles[1]['preconstruction']=True;roles[2]['retained']=True
    roles[3]['alias']='baseline::WrapperArgumentsV1';roles[3]['new_charge']=0
    good=dict(roles=roles,encoder_E=40531,encoder_additive_terms=1,attachment_calls=1,getter_calls=1,
              production_caller_accepted=False,harness_cost='external-nonzero-unbounded-here',
              healthy_narrowing=False,generic_alternatives={'encode_result':['View','Cursor','Option<Block>'],'io_result':['Metadata','u64']},
              metadata_caller_results=2,count_whole_inherited_engine_again=False,
              replaced_raw_wrapper_owner_legs_counted=False,caller_result_aliased_to_encoder_return=False,
              pairing_diagnostic_policy='explicit-is_ok-discard-unattributed-observation')
    validate_recipe(good);results={}
    def reject(name,mutate):
        bad=copy.deepcopy(good);mutate(bad)
        try:validate_recipe(bad)
        except AssertionError:results[name]=True
        else:raise AssertionError('control accepted '+name)
    reject('refused_None_storage_shrunk',lambda j:j['roles'][0].__setitem__('bytes',1))
    reject('full_refused_slot_conditionally_funded',lambda j:j['roles'][0].__setitem__('funding','conditional'))
    reject('early_token_funded_after_admission',lambda j:j['roles'][1].__setitem__('funding','conditional'))
    reject('retained_Finish_released_at_phase_completion',lambda j:j['roles'][2].__setitem__('released_at','phase_completion'))
    reject('invented_token_Result_or_array',lambda j:j['roles'][1].__setitem__('invented_wrapper',True))
    reject('inherited_role_alias_charged_again',lambda j:j['roles'][3].__setitem__('new_charge',1240))
    reject('loop_or_record_storage_multiplier',lambda j:j['roles'][0].__setitem__('multiplicity',32))
    reject('duplicate_source_identity',lambda j:j['roles'].append(copy.deepcopy(j['roles'][0])))
    reject('encoder_inherited_aggregate_added',lambda j:j.__setitem__('encoder_additive_terms',2))
    reject('second_attachment_call',lambda j:j.__setitem__('attachment_calls',2))
    reject('second_outer_getter',lambda j:j.__setitem__('getter_calls',2))
    reject('host_claimed_production_caller',lambda j:j.__setitem__('production_caller_accepted',True))
    reject('harness_claimed_zero_cost',lambda j:j.__setitem__('harness_cost','zero'))
    reject('healthy_narrowing_with_live_diagnostics',lambda j:j.__setitem__('healthy_narrowing',True))
    reject('generic_cursor_alternative_omitted',lambda j:j['generic_alternatives']['encode_result'].remove('Cursor'))
    reject('two_metadata_caller_results_collapsed',lambda j:j.__setitem__('metadata_caller_results',1))
    reject('entire_inherited_engine_recounted',lambda j:j.__setitem__('count_whole_inherited_engine_again',True))
    reject('same_byte_unrelated_source_alias',lambda j:(j['roles'][1].__setitem__('alias','baseline::WrapperArgumentsV1'),j['roles'][1].__setitem__('new_charge',0)))
    reject('old_raw_owner_arguments_plus_token',lambda j:j.__setitem__('replaced_raw_wrapper_owner_legs_counted',True))
    reject('caller_Result_aliased_to_encoder_return',lambda j:j.__setitem__('caller_result_aliased_to_encoder_return',True))
    reject('pairing_error_relabeled_as_cleanup_return',lambda j:j.__setitem__('pairing_diagnostic_policy','actual-wasi-cleanup-return'))
    total=MAX
    try:
        term=1;need(0<=term<=MAX-total,'checked u64 overflow');total+=term
    except AssertionError:results['checked_u64_overflow']=True
    else:raise AssertionError('overflow accepted')
    return results

def main():
    inputs=[seal(AUTH,'351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c',225),
            seal(OLD,'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751',495),
            seal(IND/'candidate-review','c38fc429932b8681569b57c3a86416c1d003d032e82d942ad424fc02712c5a58',102),
            seal(IND/'authority-correction-review','ed396b3b74fb5e399d7ebee1759b19dae35d8f7fc577fdd92825f7eb31421b36',77),
            seal(E,'a1d597f634b805344ecc3edc1e6bfe0095323130d201d68b5da819c50ac1b322',49)]
    accept=V/'swift-semantic-adapter-root-review/guarded-snapshot-encoder-storage-host-acceptance.json'
    need(sha(accept.read_bytes())=='ae71f01a593007cf89b093ca8dc5cfc5dc5e5801374d0f900be012bfd43d86b3','root encoder acceptance')
    manifest=read(AUTH/'source-manifest.json');need(len(manifest['members'])==144,'source count')
    tree=sha(json.dumps(manifest['members'],sort_keys=True,separators=(',',':')).encode())
    need(tree=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896','authority source tree')
    files={m['path']:m for m in manifest['members']}
    for m in manifest['members']:
        data=(AUTH/'source/vm'/m['path']).read_bytes()
        need((len(data),sha(data))==(m['bytes'],m['sha256']),'source member')
    groups=[]
    for identity,ranges,funding,expectations in GROUPS:
        sources=[]
        for path,lo,hi in ranges:
            lines=(AUTH/'source/vm'/path).read_text().splitlines(keepends=True)
            need(1<=lo<=hi<=len(lines),'source range '+identity)
            text=''.join(lines[lo-1:hi])
            sources.append(dict(path=path,start_line=lo,end_line=hi,source_sha256=files[path]['sha256'],
                                region_sha256=sha(text.encode()),functions=re.findall(r'\bfn\s+(\w+)',text)))
        groups.append(dict(id=identity,sources=sources,earliest_funding=funding,required_source_role_families=expectations))
    source=(AUTH/'source/vm'/I).read_text().splitlines(keepends=True)
    host=''.join(source[602:646])
    need(host.count('scope.attach_wasi_v1(')==1 and host.count('run.outer_v1()')==1,'concrete host calls')
    need(host.count('scope.construct_v1(')==1 and host.count('run.finish_v1()')==1,'consuming host calls')
    need('let outer=run.outer_v1();' in host and 'let finish=run.finish_v1();' in host,'actual host retained locals')
    need('wasi.snapshot_pair_v1(&control).is_ok()' in (AUTH/'source/vm'/C).read_text(),'explicit pairing diagnostic policy')
    # Confirm accepted E source coverage remains unchanged under the authority
    # correction. No new owner/caller bytes are inferred from these comparisons.
    ranges={S:[(732,1374)],'src/experimental/account.rs':[(224,333)],
            K:[(1497,1499)],C:[(350,356),(824,826)],I:[(262,283)],
            L:[(146,154),(214,238),(1399,1413)],W:[(432,432)],
            'src/experimental_wasi/mod.rs':[(638,638)]}
    encoder_unchanged=[]
    for path,spans in ranges.items():
        old=(OLD/'source/vm'/path).read_text().splitlines(keepends=True)
        new=(AUTH/'source/vm'/path).read_text().splitlines(keepends=True)
        for lo,hi in spans:
            need(old[lo-1:hi]==new[lo-1:hi],'encoder/helper range changed')
            encoder_unchanged.append(dict(path=path,start_line=lo,end_line=hi,sha256=sha(''.join(new[lo-1:hi]).encode())))
    inventory=read(E/'inventory.json');need(inventory['enumerated_bytes']==40531,'encoder E')
    for r in inventory['roles']:
        s=r['source'];path='src/'+s['path'];old=(OLD/'source/vm'/path).read_text().splitlines();new=(AUTH/'source/vm'/path).read_text().splitlines()
        need(old[s['start_line']-1:s['end_line']]==new[s['start_line']-1:s['end_line']],'encoder source role span changed')
    unit_layout=read(IND/'candidate-review/commands/independent-layout-unit-debug/layouts.json')
    facts={row['type']:dict(bytes=row['bytes'],alignment=row['alignment']) for rows in unit_layout.values() for row in rows}
    need(facts['SnapshotPhaseStorageV1']['bytes']==5328 and facts['SnapshotScopeFinishV1']['bytes']==13232,'full slot facts')
    token=read(AUTH/'summary.json')['layout_values_capability_size_align_tuple_size_align']
    need(token=={'debug':[1240,8,1240,8],'optimized':[1240,8,1240,8]},'owner token facts')
    old_layout=read(OLD/'layout-results.json')['profiles']
    profile_facts={p:{'scope':old_layout[p]['composition_control_layouts'][4],
                      'scope_result':old_layout[p]['composition_control_layouts'][14],
                      'run':old_layout[p]['composition_control_layouts'][10],
                      'finish':old_layout[p]['composition_control_layouts'][12]}
                   for p in ['gated-production-debug','gated-unit-debug']}
    expectations=dict(schema=1,status='independent preaccess requirements; no floor selected',
        authority_seal_sha256=inputs[0]['seal_sha256'],source_members=144,source_tree_sha256=tree,
        groups=groups,measured_unit_type_facts=facts,owner_token_and_parts=dict(bytes=1240,alignment=8),
        profile_facts=profile_facts,accepted_encoder_E=dict(bytes=40531,roles=2658,templates=64,
            charged_once=True,unchanged_source_regions=encoder_unchanged,role_spans_unchanged=2658),
        generic_rule='Measure every actual encode_result<T>/io_result<T> substitution. Use explicit per-role maxima only with acyclic synchronous reuse; caller result identities remain distinct.',
        baseline_rule='Preserve foundation13-term/inherited70/correction63 meanings by exact one-to-one aliases; replace old raw token arguments and encoder aggregates; never add entire baseline or substitute equal-byte identities.',
        caller_rule=dict(name='future_genuine_composition_v1::selected_owned_files_v1',cfg='test',
            attachment_calls=[0,1],outer_getter_calls=1,construct_calls=1,finish_calls=1,
            final_finish_live_until='function end after assertions',production_caller_exists=False,
            external_harness='path/output/File creation/header write/assertion/panic/test framework are nonzero external harness, excluded from bounded engine-source model'),
        producer_accessed=False,full_inventory_review_pending=True,complete_floor_or_runtime_accepted=False)
    # Source expression seeds resolve to actual materialized compiler slots in
    # final review. An operand move/field projection is an alias when no separate
    # slot exists; these seeds are not summed as if every spelling made a copy.
    caller_seeds=[
        ('parameter.selected','SelectedValidatedProfileV1',None,'selected argument','function entry','into_snapshot_scope consuming receiver'),
        ('call.into_snapshot_scope.result','Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>',8176,'ingress call result','before Construction','scope success/error match'),
        ('match.scope.success','SnapshotScopeV1',8176,'Ok(scope) pattern and move','ingress match','scope binding; alias only by actual slot'),
        ('match.scope.failure','SnapshotPreScopeFailureV1',2192,'Err(failure) pattern and primary/retirement borrows','ingress refusal','panic/harness transfer; actual engine argument slots included'),
        ('local.scope','SnapshotScopeV1',8176,'let mut scope binding','ingress success','consuming construct_v1'),
        ('optional_wasi.arguments','Option<(WasiBudget,WasiGrants)>',None,'host parameter and Some budget/grants patterns','function entry','at most one attachment call'),
        ('call.attach_wasi.result','&SnapshotWasiAttachmentV1',8,'let attachment reference','optional attach call','assertion borrows end; scope retains actual attachment'),
        ('call.construct.scope_receiver','SnapshotScopeV1',8176,'consuming scope receiver source operand','construct call','same actual moved owner; avoid invented operand copy'),
        ('call.construct.result','SnapshotRunV1',14936,'construct call-expression result','construct returns','run binding; exact materialized alias mapping required'),
        ('local.run','SnapshotRunV1',14936,'let run binding','construct returns','consuming finish_v1'),
        ('call.outer.receiver','&SnapshotRunV1',8,'outer_v1 shared receiver expression','after construct','getter call ends'),
        ('call.outer.result','&SnapshotOuterV1',8,'outer_v1 reference return/call result','exactly one getter','outer caller binding'),
        ('local.outer','&SnapshotOuterV1',8,'let outer reference binding','getter returns','all outer borrows end before Run consume'),
        ('call.finish.run_receiver','SnapshotRunV1',14936,'finish_v1 consuming receiver source operand','finish call','same actual moved owner; avoid invented operand copy'),
        ('call.finish.result','SnapshotScopeFinishV1',13232,'finish_v1 call-expression result','finish returns','finish caller binding; exact materialized alias mapping required'),
        ('local.finish','SnapshotScopeFinishV1',13232,'let finish binding and diagnostic borrows','finish returns','function end after retained diagnostic assertions'),
    ]
    caller_recipe=dict(schema=1,source_path=I,source_sha256=files[I]['sha256'],
        function='future_genuine_composition_v1::selected_owned_files_v1',cfg='test',
        source_start_line=603,source_end_line=648,profile='gated-unit-debug',
        source_occurrence_seeds=[dict(id='host::selected_owned_files_v1::'+identity,type=typ,
                                    measured_unit_bytes=size,role=role,starts=start,ends=end)
                                 for identity,typ,size,role,start,end in caller_seeds],
        materialization_rule='Bind every expression seed to compiler slot IDs; aliases, field projections and operand moves sharing one slot charge once. Callee parameters/returns and caller materialized results remain distinct.',
        before_ingress_temporaries=['selected_initial_profile_v1().budget','Instant::now()','Cancellation::default()'],
        engine_call_arguments=['scope attachment grants/budget/Instant','claims reference','rows mutable reference','snapshot mutable reference'],
        native_harness_exclusions=['Path/directory and joined paths','OpenOptions/File create_new/open/unwrap','claims test literal construction','primary header std::fs::write','assertion/panic formatting','test framework and diagnostic observer bodies; engine call-site slots and product wrappers remain included'],
        exclusions_are_zero_engine_cost=False,
        excluded_harness_cost='nonzero and unbounded by this engine-source inventory; no process/physical-stack claim',
        calls=dict(attachment_min=0,attachment_max=1,outer_getter=1,construct=1,finish=1),
        production_caller_accepted=False,operational_host_execution_accepted=False)
    results=controls()
    receipt=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='ready for frozen owner/caller producer release',command=[sys.executable,str(Path(__file__).resolve())],
        python_version=platform.python_version(),source_revision='38084d610c3b24d1146aae26f2012b3fb78e0e68',
        source_tree_sha256=tree,source_members=144,inputs=inputs,scope_groups=len(groups),
        finite_review_controls=results,source_bound_host_recipe_checked=True,encoder_source_span_comparisons=2658,
        producer_packet_accessed=False,compiler_invocations=0,engine_VM_writer_runtime_executions=0,
        native_device_simulator_emulator_UI_capture_process_inventory_executions=0,
        canonical_or_Git_mutations=False,source_floor_selected=False,healthy_cleanup_accepted=False,
        production_caller_accepted=False,GA_gates_verified=0,
        pending=['Frozen producer release and complete occurrence/layout/call/alias/funding reconciliation.',
                 'New emission-helper source changes require a separate exact slot delta and source binding.',
                 'No actual production caller exists; genuine host execution and operational acceptance remain pending.'])
    (HERE/'source-expectations.json').write_text(json.dumps(expectations,indent=2)+'\n')
    (HERE/'caller-recipe.json').write_text(json.dumps(caller_recipe,indent=2)+'\n')
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'],source_tree_sha256=tree,groups=len(groups),controls=len(results),producer_accessed=False)))

if __name__=='__main__':main()
