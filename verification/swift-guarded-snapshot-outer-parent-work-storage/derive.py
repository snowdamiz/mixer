#!/usr/bin/env python3
"""Source-bound logical work/storage derivation from immutable retained data.

No compiler or product execution occurs here. Native dimensions mean typed
inline object extents, never machine stack, CPU, RSS or allocator footprint.
"""
import collections, gzip, hashlib, importlib.util, json, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'
OLD_TREE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
NEW_TREE='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
PROFILE='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
NAMES=('selected_outer_request_v1','borrow_original_diagnostics_once_v1','observe_borrowed_originals_v1','run_selected_one_fixture_outer_v1','consume_outer_request_v1')
INPUTS={}
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(a):return json.dumps(a,sort_keys=True,separators=(',',':')).encode()
def row(p,b):return {'path':p,'bytes':len(b),'sha256':sha(b)}
def read(p):
    b=p.read_bytes();INPUTS[p.relative_to(ROOT).as_posix()]=row(p.relative_to(ROOT).as_posix(),b);return b
def load(p):return json.loads(read(p))
def require(ok,label):
    if not ok:raise ValueError(label)
def write(p,a): (HERE/p).write_text(json.dumps(a,sort_keys=True,indent=2)+'\n')
def norm(t):return re.sub(r'\b(?:[A-Za-z_]\w*::)+','',t).replace("'static","'_")
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def packet(name,digest,count,size):
    p=V/name;s=load(p/'seal.json')
    require(sha((p/'seal.json').read_bytes())==digest,'seal:'+name)
    require(len(s['members'])==count and sum(x['bytes'] for x in s['members'])==size,'closure:'+name)
    for m in s['members']:require(row(m['path'],read(p/m['path']))==m,'member:'+name+'/'+m['path'])
def check_exact_addition(old,new,snippet):
    require(old.endswith(b'\n}\n') and snippet.endswith(b'}\n'),'exact module boundary')
    inserted=b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n'+snippet
    require(new==old[:-2]+inserted+b'}\n','exact addition only; all previous declaration/body bytes preserved')
    return inserted
def source():
    folder=V/'swift-guarded-snapshot-host-composition';base=V/'swift-guarded-snapshot-funding-implementation/source/vm'
    old_manifest=load(folder/'source-manifest.json');candidate_manifest=load(V/'swift-guarded-snapshot-outer-parent-source/source-manifest.json')
    require(sha(canon(old_manifest['members']))==OLD_TREE and len(old_manifest['members'])==146,'old source146')
    old={}
    for m in old_manifest['members']:
        p=folder/'overlay/vm'/m['path']
        if not p.is_file():p=base/m['path']
        old[m['path']]=read(p);require(row(m['path'],old[m['path']])==m,'source member:'+m['path'])
    new=dict(old);new[PROFILE]=read(V/'swift-guarded-snapshot-outer-parent-source/overlay/vm'/PROFILE)
    snippet=read(V/'swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs')
    inserted=check_exact_addition(old[PROFILE],new[PROFILE],snippet)
    rows=[row(p,new[p]) for p in sorted(new,key=Path)]
    require(rows==candidate_manifest['members'] and sha(canon(rows))==NEW_TREE,'candidate source146')
    require(sum(old[p]==new[p] for p in old)==145,'145 members byte exact')
    rebind={'schema':1,'old_tree':OLD_TREE,'candidate_tree':NEW_TREE,'members':146,'byte_exact_members':145,
        'changed_member':PROFILE,'removed_bytes':0,'all_original_member_bytes_restored_by_removing_exact_addition':True,
        'changed_old_sha256':sha(old[PROFILE]),'changed_new_sha256':sha(new[PROFILE]),'addition_sha256':sha(inserted),
        'component_policy':'All old source146 work/storage/diagnostic/destructor components retain their exact old unit, source bodies, dimensions, limitations and positive external inputs. Only source correspondence is rebound; no new whole binary correspondence claim.',
        'new_caller_priced_separately':True,'old_account_surface_counted_once':True,'actual_route':'Pending selector returns before account; I/U ceilings are conditional, not executed counts.'}
    return new,rebind
def catalog():
    # Whole source146 retained compiler output, accepted previously; no requery.
    p=V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz'
    archived=read(p);require(sha(archived)=='1ddc23c6274a1c4f148e9d4a389aa0aeaa070384929280de044f4889a49ec9ec','old layout archive')
    raw=gzip.decompress(archived);require(sha(raw)=='6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a','old compiler stdout')
    sizes=collections.defaultdict(set)
    for ty,n,a in re.findall(rb'^print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes$',raw,re.M):sizes[norm(ty.decode())].add((int(n),int(a)))
    old=load(V/'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')['actual_type_sizes']
    exact_selected={}
    for ty,n in old.items():
        k=norm(ty);require(k not in exact_selected or exact_selected[k]==n,'selected concrete query short-name collision')
        exact_selected[k]=n
    rows=load(V/'swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/layouts.json')['rows']
    observed={r['query']:r['observed'] for r in rows};require(len(observed)==44,'all 44 retained observations')
    names={'ReviewedFixtureBindingV1':'binding','ImmutableIdentityPreimageV1':'preimage','ImmutableFixtureIdentitiesV1':'identities','PreexistingImmutableBindingV1':'preexisting','OneFixtureOuterRequestV1':'request','BindingSelectionRefusalV1':'selection_refusal','OriginalObservationV1':'observation',"BorrowedOriginalDiagnosticsV1<'_>":'borrow',"Option<BorrowedOriginalDiagnosticsV1<'_>>":'optional_borrow','RetirementObservationV1':'retirement','OuterResultV1':'result','UsageV1':'usage','OwnedFixtureOutcomeV1':'payload',"PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>":'wrapper',"DestroyedStorageV1<'_>":'token','TrustedHostAccountV1':'account',"Result<PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>, RefusalV1>":'entry_result','FrozenFixtureV1':'frozen_fixture','TrustedRootPolicyV1':'root','CostV1':'cost','ReviewedWholeQuoteV1':'quote',"ReservationV1<'_>":'reservation'}
    for ty,q in names.items():sizes[ty].add((observed[q+'_size'],observed[q+'_align']))
    q=load(HERE/'commands/result-layout/layouts.json');r=load(HERE/'commands/result-layout/receipt.json')
    plan=load(HERE/'query-plan.json');query_manifest=load(HERE/'query-source-manifest.json')
    require(all(r[k]==value for k,value in plan.items()),'exact predeclared compiler context')
    require(sha(read(HERE/'query_once.py'))==plan['runner_sha256'] and row('query-result-layout.inc.rs',read(HERE/'query-result-layout.inc.rs'))==plan['query_tail'],'exact inert query and runner')
    require(sha(canon(query_manifest['members']))==query_manifest['tree_sha256']==plan['query_tree'],'exact diagnostic source manifest')
    require(r['query_success'] and r['expected_diagnostic_exit_observed'] and r['exit_code']==1 and r['compiler_invocations']==1 and r['child_reaped'] and r['owned_group_absent'] and r['owned_scratch_removed'],'one missing layout diagnostic terminal/cleanup')
    for name in ['stdout','stderr']:require(row(name,read(HERE/'commands/result-layout'/name))==r[name],'exact compiler '+name)
    require(q['rows'][0]['query']=='size' and q['rows'][1]['query']=='align','query identity')
    sizes['Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>'].add(tuple(x['observed'] for x in q['rows']))
    # All selected dimensions are <=8-aligned; historical exact queries may
    # expose only size. Any conflicting size is fatal, never max-selected.
    table={}
    for t,pairs in sizes.items():
        if len({n for n,a in pairs})==1:table[t]={'bytes':next(iter(pairs))[0],'alignment':max(a for n,a in pairs),'rule':'retained exact compiler type/query'}
    # The retained90 exact concrete queries disambiguate known std/resource
    # names from unrelated same-short-name types elsewhere in the whole crate.
    for t,n in exact_selected.items():table[t]={'bytes':n,'alignment':min(8,max(1,n)),'rule':'retained90 concrete production query disambiguates exact selected type'}
    table.update({t:{'bytes':n,'alignment':max(1,n),'rule':'fixed aarch64 primitive'} for t,n in {'()':0,'!':0,'bool':1,'isize':8}.items()})
    return table
def extent(t,table,H):
    t=norm(t)
    if t in table:return dict(table[t])
    if t.startswith('&'):
        inner=re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?",'',t)
        require(inner not in ('str','Path') and not(inner.startswith('[') and ';' not in inner),'unsized ref requires exact query')
        return {'bytes':8,'alignment':8,'rule':'sized shared reference; actual aarch64 pointer query8'}
    if t.startswith('(') and t.endswith(')'):
        parts=H.split(t[1:-1]);require(all(p.startswith('&') for p in parts),'unknown tuple')
        return {'bytes':sum(extent(p,table,H)['bytes'] for p in parts),'alignment':8,'rule':'homogeneous8-byte reference field union; logical inline extent only'}
    match=re.fullmatch(r'\[(.+); (\d+)\]',t)
    if match:
        e=extent(match[1],table,H);return {'bytes':e['bytes']*int(match[2]),'alignment':e['alignment'],'rule':'fixed array element extent'}
    raise ValueError('missing concrete compiler extent:'+t)
def parse_functions(raw):
    result={}
    for name in NAMES:
        m=re.search(r'^fn '+name+r'\(.*?^}\n',raw,re.M|re.S);require(m is not None,'complete exact MIR:'+name);result[name]=m[0]
    return result
def roles(body):
    header=body.splitlines()[0];params=re.search(r'\((.*)\) ->',header)[1]
    rows=[{'local':n,'type':t,'kind':'parameter'} for n,t in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',params)]
    rows += [{'local':n,'type':t,'kind':'return' if n=='_0' else 'local'} for n,t in re.findall(r'^\s+let(?: mut)? (_\d+): ([^\n]+?);(?: +//|$)',body,re.M)]
    require(len(rows)==len({r['local'] for r in rows}),'unique all roles');return rows
def paths(blocks):
    result=[]
    def visit(b,prior):
        require(b not in prior,'cycle needs explicit bound');p=prior+[b];last=blocks[b]['operations'][-1]
        successors=sorted(set(re.findall(r'\bbb\d+\b',last)))
        if 'unwind continue' in last:result.append({'blocks':p,'terminal':'unwind-continue'})
        if 'unwind terminate' in last:result.append({'blocks':p,'terminal':'terminate-cleanup'})
        if not successors:
            terminal={'return;':'return','resume;':'resume','unreachable;':'unreachable'}.get(last)
            require(terminal is not None,'unknown terminal:'+last);result.append({'blocks':p,'terminal':terminal})
        for s in successors:visit(s,p)
    visit('bb0',[]);return result
def price(code,by,H):
    mentions=re.findall(r'\b_\d+\b',code);require(all(x in by for x in mentions),'unbound local')
    constants=[]
    for m in re.finditer(r'\bconst\s+',code):
        token=re.match(r'(?:\d+_(?:u64|usize|isize)|true\b|false\b|\(\))',code[m.end():]);require(token is not None,'unpriced constant:'+code)
        value=token[0];constants.append({'text':value,'bytes':0 if value=='()' else 1 if value in ('true','false') else 8,'scalar_leaves':1})
    base=2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b',code))
    scalar=2*sum(by[x]['scalar_leaves']+by[x]['pointee_scalar_leaves'] for x in mentions)+2*len(constants)
    native=2*sum(by[x]['bytes']+by[x]['pointee_bytes'] for x in mentions)+2*sum(c['bytes'] for c in constants)
    if code=='return;':scalar+=2*(by['_0']['scalar_leaves']+by['_0']['pointee_scalar_leaves']);native+=2*(by['_0']['bytes']+by['_0']['pointee_bytes'])
    return {'code':code,'mentions':mentions,'constants':constants,'source_action_units':base+scalar,'native_sized_occurrence_bytes':native,'combined':base+scalar+native}
def derive():
    INPUTS.clear()
    for name,h,n,b in [('swift-guarded-snapshot-outer-parent-source','3936c73a0f3558000834c92c3ade9822465069492740a954765cb775684bcb57',39,613222),('swift-guarded-snapshot-outer-parent-independent','70bbf1cdd9a63494e63c4c7cbda22cd8e8c1cd8c961af36dee37d528b695902e',42,4142412)]:packet(name,h,n,b)
    accepted={'guarded-snapshot-outer-parent-host-acceptance.json':'a9ebe62c104b7fd0ef61b6216ead52885e4f8a62b39834b3ac57ee5493a05d0b','guarded-snapshot-host-storage-host-acceptance.json':'9862bbe187dea2e1c6999218604ec43db3d3c9bc28d4fd815615d81dd98df432','guarded-snapshot-whole-host-work-host-acceptance.json':'d797f7c9a86259fdb40700c290e5f83488142117a355f7b5826c1d92710a784f','guarded-snapshot-direct-adapter-contract-amendment.json':'af33b1faed65d1de6764520f7f6a3eb08a2877b2612b5d8c4fdee36ea55dfcff','guarded-snapshot-remaining-work-contract-amendment.json':'766e27395fd3ba66d2e7968ef1aeb192e2691ab38614f00c1563bf5e5dcdb1ab'}
    for name,digest in accepted.items():require(sha(read(V/'swift-semantic-adapter-root-review'/name))==digest,'exact acceptance:'+name)
    src,rebind=source()
    helper=V/'swift-guarded-snapshot-parent-work-source146/helpers.py';helper_bytes=read(helper)
    helper_seal=load(helper.parent/'seal.json');require(row('helpers.py',helper_bytes)==next(m for m in helper_seal['members'] if m['path']=='helpers.py'),'sealed accepted scalar scanner')
    # This accepted source type scanner has no file/process operations on import.
    H=module(helper,'outer_accepted_shape_helper');shapes=H.SourceShapes(src);table=catalog()
    raw=read(V/'swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/outer-and-query.mir').decode()
    bodies=parse_functions(raw);functions=[];slots=[]
    for name,body in bodies.items():
        rs=roles(body)
        for r in rs:
            t=r['type'];r.update(extent(t,table,H));r['scalar_leaves']=shapes.n(t)
            inner=re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?",'',t) if t.startswith('&') else None
            r.update(pointee_type=inner,pointee_bytes=extent(inner,table,H)['bytes'] if inner else 0,pointee_scalar_leaves=shapes.n(inner) if inner else 0)
            # Reference pointee extent is work only. Pointee ownership/backing
            # remains in the original child or immutable binding, charged once.
        by={r['local']:r for r in rs};blocks={}
        for m in re.finditer(r'^    (bb\d+)( \(cleanup\))?: \{\n(.*?)^    \}',body,re.M|re.S):
            code=[line.split('//',1)[0].strip() for line in m[3].splitlines()];code=[c for c in code if c]
            blocks[m[1]]={'cleanup':bool(m[2]),'operations':code,'rows':[price(c,by,H) for c in code]}
        ps=paths(blocks)
        parameter=[r for r in rs if r['kind']=='parameter']
        entry_source=2+2*sum(r['scalar_leaves']+r['pointee_scalar_leaves'] for r in parameter)
        entry_native=2*sum(r['bytes']+r['pointee_bytes'] for r in parameter)
        surface=entry_source+entry_native+sum(x['combined'] for b in blocks.values() for x in b['rows'])
        end=sum(2+2*r['scalar_leaves']+2*r['bytes'] for r in rs)
        for p in ps:require(entry_source+entry_native+sum(x['combined'] for b in p['blocks'] for x in blocks[b]['rows'])<=surface,'path within all-written-block envelope')
        for r in rs:
            uses=[bid for bid,b in blocks.items() if any(r['local'] in x['mentions'] for x in b['rows'])]
            slots.append({'id':name+':'+r['local'],'type':r['type'],'bytes':r['bytes'],'kind':r['kind'],'used_in_blocks':uses,
                'funded_by':'P0','reserved_first':'P0_BEFORE_BINDING_POLICY_QUOTE_ACCOUNT_ENTRY','reserved_last':'P0_AFTER_FINAL_RESULT_CONSUMPTION',
                'lifetime_rule':'Every declared logical slot is preprovisioned and conservatively retained across the whole route. Moved values keep separate source slots; no physical alias/stack reuse claim or refund.',
                'pointee_owner':'original child payload or immutable binding; reference header only in this roster' if r['pointee_type'] else None})
        functions.append({'name':name,'MIR_sha256':sha(body.encode()),'roles':rs,'blocks':blocks,'terminal_paths':ps,'entry_source':entry_source,'entry_native':entry_native,'source_and_native_surface':surface,'finite_role_end_envelope':end,'work':surface+end,'logical_inline_slot_bytes':sum(r['bytes'] for r in rs)})
    require(len(slots)==130 and sum(len(b['rows']) for f in functions for b in f['blocks'].values())==386,'all130roles386operations')
    by={f['name']:f for f in functions};consumer=by['consume_outer_request_v1'];require(len(consumer['terminal_paths'])==32,'32 consumer terminal paths including unwind')
    source_review_paths=load(V/'swift-guarded-snapshot-outer-parent-independent/mir-paths.json')
    for f in functions:require({(tuple(p['blocks']),p['terminal']) for p in f['terminal_paths']}=={(tuple(p['blocks']),p['terminal']) for p in source_review_paths[f['name']]},'exact independent terminal path set:'+f['name'])
    new_work=sum(f['work'] for f in functions)
    final_result_end=2+2*shapes.n('OuterResultV1')+2*table['OuterResultV1']['bytes']
    new_work+=final_result_end
    inline=sum(r['bytes'] for r in slots)
    # Derive call multiplicities directly, retaining independent route event
    # semantics for Some/None and shared-borrow termination before destruction.
    maxima=collections.Counter()
    for p in consumer['terminal_paths']:
        code='\n'.join(x for b in p['blocks'] for x in consumer['blocks'][b]['operations'])
        calls={n:len(re.findall(r'= .*?\b'+n+r'\(',code)) for n in ['usage_v1','borrow_original_diagnostics_once_v1','run_one_fixture_v1','destroy_returned_fixture_v1','release_after_retirement_v1']}
        maxima|=collections.Counter(calls)
    require(dict(maxima)=={'usage_v1':3,'borrow_original_diagnostics_once_v1':1,'run_one_fixture_v1':1,'destroy_returned_fixture_v1':1,'release_after_retirement_v1':1},'exact conditional call caps')
    phase_names=['P0_BEFORE_BINDING_POLICY_QUOTE_ACCOUNT_ENTRY','P0_CHILD_RESERVED','P1_SETUP','P1_LOADER','P2_ARGUMENTS','P3_SHELL','P4_LEAF','P5_RETURNED_ORIGINAL_PAYLOAD','P5_SHARED_OBSERVATION','P5_SHARED_VIEW_ENDED','P5_PAYLOAD_AND_CARRIER_DESTROYING','P0_DESTROYED_TOKEN_RETURNED','P0_RELEASE_AFTER_SOME_TOKEN','P0_FINAL_OWNED_RESULT','P0_AFTER_FINAL_RESULT_CONSUMPTION']
    # Bind the reused old storage algebra itself, preserving all its inputs and
    # owners rather than silently replacing it with a new budget recipe.
    for p in ['model.py','inline-inventory.json']:read(V/'swift-guarded-snapshot-host-storage-composition'/p)
    producer_inventory=load(V/'swift-guarded-snapshot-outer-parent-source/outer-mir-inventory.json')
    leaf_counts={f['name']:len(f['paths']) for f in producer_inventory['functions']}
    path_reconciliation=[]
    for f in functions:
        kinds=collections.Counter(p['terminal'] for p in f['terminal_paths'])
        path_reconciliation.append({'function':f['name'],'producer_successor_leaf_paths':leaf_counts[f['name']],'independent_explicit_terminal_paths':len(f['terminal_paths']),'additional_explicit_unwind_or_terminate_terminals':len(f['terminal_paths'])-leaf_counts[f['name']],'terminal_kinds':dict(kinds)})
    require(sum(leaf_counts.values())==43 and sum(r['additional_explicit_unwind_or_terminate_terminals'] for r in path_reconciliation)==13,'43+13=56 exact convention reconciliation')
    report={'schema':1,'status':'bounded-source-work-storage-candidate-requires-independent-review','old_source_tree':OLD_TREE,'candidate_source_tree':NEW_TREE,
        'function_count':5,'roles':len(slots),'written_operations':386,'terminal_paths_including_unwind':sum(len(f['terminal_paths']) for f in functions),'consumer_terminal_paths':32,
        'producer_successor_leaf_paths':43,'terminal_convention_reconciliation':path_reconciliation,
        'source_and_native_surface':sum(f['source_and_native_surface'] for f in functions),'finite_role_end_envelope':sum(f['finite_role_end_envelope'] for f in functions),'external_final_result_end':final_result_end,
        'new_outer_work':new_work,'new_outer_inline_bytes':inline,'separate_final_result_owner_bytes':80,'whole_preexisting_binding_inline_bytes':1168,
        'P0_fixed_inline_before_external_root_backing':234375+inline+80+1168,
        'conditional_account_surface_once':2825436,'conditional_counts':{'I_max':1,'U_max':3,'entry_max':1,'release_max':1},
        'conditional_whole_work_fixed_with_new_outer':895084428323053276+194231+1039*3+new_work,
        'inherited_remaining_work_terms':{'L_str':67424,'P0_dynamic_backing':1,'P0_fixture_binding':1,'P0_root_route':1,'native_error_request':1,**{'native_open_request_'+str(i):1 for i in range(5)}},
        'inherited_fixed_includes_old_account_once':True,'new_outer_is_added_once':True,'frozen35_model_rewritten':False,'L_str5080_selected':False,
        'source_helper_sha256':sha(helper_bytes),'all_three_selectors_pending':True,'actual_execution_I_U_entry_release':{'I':0,'U':0,'entry':0,'release':0},
        'whole_root_policy_or_funding_selected':False,'compiled_complete_old_body_correspondence':False,'actual_immutable_binding_selected':False,'runtime_healthy_cleanup_native_FieldLog_OTA_GA':False,
        'metric':'Inherited logical source/typed aggregate/destructor-interface occurrences plus native typed-byte allowances. Every new role end and every written new block is conservatively charged once; private standard/compiler/panic/CPU/physical allocation remain outside the unit.',
        'P5_import_rule':'The old full actual payload-destructor and authored wrapper Drop/carrier envelope remain charged once. Across normal explicit destroy and new cleanup alternatives the sole affine wrapper payload is destroyed at most once; taking before destructor prevents duplicate payload teardown on unwind. New call/drop operand surfaces are charged here; no second credit or P5 subtraction.',
        'residual_work_rule':'New fixed caller surface prices the accepted pending source and the finite conditional consumer. It does not price a future selector implementation, immutable preimage production/correspondence, external final launcher or native/library binary. P0_root_route/P0_fixture_binding/P0_dynamic_backing remain explicit positive obligations.'}
    phase={'schema':1,'phases':phase_names,'new_slot_reserved_bytes_each_phase':{p:inline for p in phase_names},'all_new_roles':slots,
        'authored_function_activity_without_storage_credit':{'selected_outer_request_v1':['P0_BEFORE_BINDING_POLICY_QUOTE_ACCOUNT_ENTRY'],'run_selected_one_fixture_outer_v1':['P0_BEFORE_BINDING_POLICY_QUOTE_ACCOUNT_ENTRY','P0_FINAL_OWNED_RESULT'],'consume_outer_request_v1':['P0_BEFORE_BINDING_POLICY_QUOTE_ACCOUNT_ENTRY','P0_CHILD_RESERVED','P1_SETUP','P1_LOADER','P2_ARGUMENTS','P3_SHELL','P4_LEAF','P5_RETURNED_ORIGINAL_PAYLOAD','P5_SHARED_OBSERVATION','P5_SHARED_VIEW_ENDED','P5_PAYLOAD_AND_CARRIER_DESTROYING','P0_DESTROYED_TOKEN_RETURNED','P0_RELEASE_AFTER_SOME_TOKEN','P0_FINAL_OWNED_RESULT'],'borrow_original_diagnostics_once_v1':['P5_SHARED_OBSERVATION'],'observe_borrowed_originals_v1':['P5_SHARED_OBSERVATION']},
        'fixed_extra_owners':[{'id':'immutable-full-binding','bytes':1168,'includes':'ReviewedBinding512 + path-byte headers80 + twelve identity records576; no separate512/576 added again'},{'id':'external-owned-final-result','bytes':80,'includes':'finite result consumed by future outer caller; distinct source place from both function _0 returns'}],
        'all_P0_before_policy_quote_account_entry':True,'all_original_owners_remain_charged_until_actual_payload_and_carrier_destruction_return':True,
        'view_end':'Borrowed diagnostics/Option and temporary reference tuples have no used-after-destruction or escaping result path. Reserving their old header slots longer supplies no borrow or owner authority.',
        'normal_release':'Only Some actual DestroyedStorageV1 after old payload/carrier destruction return; P0 token/release/result slots remain allocated.',
        'none_refusal_unwind':'No refund. Cleanup preserves prepaid charge, original diagnostic owners and complete destructor temporary backing envelope; finite result/snapshots are P0.',
        'storage_is_conservative_logical_slot_reservation':True,'compiler_stack_or_physical_liveness_claim':False,'move_alias_sharing_refund_credit':False}
    return {'candidate.json':report,'source-rebind.json':rebind,'operation-ledger.json':{'schema':1,'functions':functions},'phase-roster.json':phase,'source-shapes.json':{'schema':1,'types':shapes.used},'input-custody.json':{'schema':1,'members':sorted(INPUTS.values(),key=lambda r:r['path'])}}
def main():
    result=derive()
    if sys.argv[1:]==['--check']:
        for p,a in result.items():require(json.loads((HERE/p).read_bytes())==a,'stale generated evidence:'+p)
    else:
        require(not (HERE/'seal.json').exists(),'immutable packet')
        for p,a in result.items():write(p,a)
    print(json.dumps({k:v for k,v in result['candidate.json'].items() if k in ['roles','written_operations','terminal_paths_including_unwind','new_outer_work','new_outer_inline_bytes','conditional_whole_work_fixed_with_new_outer','P0_fixed_inline_before_external_root_backing']}))
if __name__=='__main__':main()
