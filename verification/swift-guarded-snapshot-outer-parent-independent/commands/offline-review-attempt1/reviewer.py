#!/usr/bin/env python3
"""Offline source, exact MIR control-flow and synthetic affine-lifetime checks."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/swift-guarded-snapshot-outer-parent-source'
COMPILE=HERE/'commands/compiler-metadata-mir'
COUNTS={}
def check(group, condition, detail):
    COUNTS[group]=COUNTS.get(group,0)+1
    assert condition, detail
def read(path): return json.loads(path.read_bytes())
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path,obj): path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def uncomment(text): return re.sub(r'//[^\n]*','',text)
def item(text,kind,name):
    match=re.search(r'\b'+kind+r'\s+'+name+r'\b[^\{]*\{',text)
    assert match,name
    depth=1; end=match.end()
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}'); end+=1
    return text[match.start():end]
def fields(text,name):
    body=item(text,'struct',name)
    return re.findall(r'(?:^|[,\n])\s*(?:pub(?:\([^)]*\))?\s+)?(\w+)\s*:',body.split('{',1)[1])
def mir_function(text,name):
    start=re.search(r'^fn '+re.escape(name)+r'\(',text,re.M)
    assert start,name
    end=re.search(r'^\}',text[start.start():],re.M)
    assert end,name
    return text[start.start():start.start()+end.end()]+'\n'
def blocks(body):
    matches=list(re.finditer(r'^    (bb\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}',body,re.M|re.S))
    result={m.group(1):uncomment(m.group(2)) for m in matches}
    assert len(result)==len(matches) and 'bb0' in result
    return result
def graph_paths(body):
    graph=blocks(body); paths=[]
    def visit(node,prefix,events):
        check('mir-acyclic',node not in prefix,('cycle',prefix,node))
        code=graph[node]; path=prefix+[node]; ev=list(events)
        markers=[('::usage_v1(','U'),('borrow_original_diagnostics_once_v1(','I'),('run_one_fixture_v1(','fixture'),('destroy_returned_fixture_v1(','destroy-call'),('release_after_retirement_v1(','release')]
        for marker,event in markers:
            ev.extend([event]*code.count(marker))
        if 'as Some).0:' in code and 'DestroyedStorageV1' in code: ev.append('token')
        # Include explicit unwind/termination edges, not only normal successors.
        targets=re.findall(r'\bbb\d+\b',code)
        special=[]
        if 'unwind continue' in code: special.append('unwind-continue')
        if 'unwind terminate(' in code: special.append('terminate-cleanup')
        if not targets and not special:
            terminal='return' if re.search(r'\breturn;',code) else 'resume' if 'resume;' in code else 'unreachable' if 'unreachable;' in code else None
            check('mir-terminal',terminal is not None,(node,code))
            paths.append(dict(blocks=path,events=ev,terminal=terminal))
        for target in targets:
            check('mir-target',target in graph,(node,target))
            next_ev=list(ev)
            if 'destroy_returned_fixture_v1(' in code and re.search(r'return: '+target+r'\b',code): next_ev.append('destroy-returned')
            visit(target,path,next_ev)
        for terminal in special: paths.append(dict(blocks=path,events=ev,terminal=terminal))
    visit('bb0',[],[])
    return graph,paths

def main():
    snippet=(P/'outer-parent.inc.rs').read_text(); source=uncomment(snippet)
    account_path=ROOT/'verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
    account=uncomment(account_path.read_text())
    compiler=read(COMPILE/'receipt.json')
    check('custody',compiler['compile_success'] and compiler['exit_code']==0 and not compiler['timed_out'],'new compile success')
    for field in ['child_reaped','owned_group_absent','owned_scratch_removed','postprocess_success']: check('custody',compiler[field],field)
    check('custody',compiler['compiler_invocations']==1 and compiler['retries']==0,'one compile')
    old_compile=read(P/'commands/compiler-only-query/receipt.json')
    for field in ['compiler_exit_code','elapsed_seconds','compiler_timeout_occurred']: check('custody',old_compile[field] is None,field)
    check('custody',not old_compile['compile_success'] and not old_compile['metadata_status_pass_claim'],'old failure retained')
    for member in read(P/'seal.json')['members']:
        data=(P/member['path']).read_bytes();check('custody',dict(path=member['path'],bytes=len(data),sha256=sha(data))==member,member['path'])
    for binding in read(P/'input-bindings.json')['members']:
        data=(ROOT/binding['path']).read_bytes();check('custody',len(data)==binding['bytes'] and sha(data)==binding['sha256'],binding['path'])

    expected_layouts=dict(binding=(512,8),preimage=(48,8),identities=(576,8),preexisting=(1168,8),request=(8,8),selection_refusal=(0,1),observation=(1,1),borrow=(56,8),optional_borrow=(64,8),retirement=(1,1),result=(80,8),usage=(24,8),payload=(13608,8),wrapper=(13624,8),token=(16,8),account=(104,8),entry_result=(13624,8),frozen_fixture=(8,8),root=(64,8),cost=(16,8),quote=(16,8),reservation=(16,8))
    layouts=read(COMPILE/'layouts.json')['rows'];producer_layouts=read(P/'commands/compiler-only-query/layouts.json')['rows']
    check('layouts',layouts==producer_layouts and len(layouts)==44,'all 44 exact observations')
    values={r['query']:r['observed'] for r in layouts}
    for name,pair in expected_layouts.items():
        for suffix,value in zip(['size','align'],pair):check('layouts',values[name+'_'+suffix]==value,name+'_'+suffix)
    check('layouts',values['identities_size']==12*values['preimage_size'],'twelve complete identity records')
    check('layouts',values['preexisting_size']==values['binding_size']+5*16+values['identities_size'],'binding plus five native-byte slice headers plus identity records')
    check('layouts',values['wrapper_size']==values['payload_size']+values['token_size'],'inline wrapper is not just result scalar')

    identity_fields=['source','build','session','executable','compiler','compiler_version','compile_manifest','compile_argv','compile_environment','process_argv','process_environment','review']
    check('source-roster',fields(source,'ImmutableFixtureIdentitiesV1')==identity_fields,'all 12 identity inputs')
    check('source-roster',fields(source,'ImmutableIdentityPreimageV1')==['bytes','sha256'],'full preimage and digest')
    check('source-roster',fields(source,'PreexistingImmutableBindingV1')==['binding','native_path_bodies','identities'],'all input owners')
    check('source-roster',fields(source,'OneFixtureOuterRequestV1')==['preexisting'],'sole private affine input')
    for name in identity_fields:check('source-roster',name in json.dumps(read(P/'owner-roster.json')['new_P0_owners']),name)
    check('source-roster',"native_path_bodies: [&'static [u8]; 5]" in source,'5 native path preimages')
    check('source-roster',"preexisting: &'static PreexistingImmutableBindingV1" in source,'static immutable owner')
    check('source-roster','Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)' in item(source,'fn','selected_outer_request_v1'),'binding refuses')
    check('source-roster','Err(RefusalV1::RootPolicyPending)' in item(account,'fn','selected_parent_account_v1'),'root refuses')
    check('source-roster','Err(RefusalV1::WholeQuotePending)' in item(account,'fn','selected_whole_quote_v1'),'quote refuses')
    for forbidden in ['pub ', '#[derive', 'unsafe', 'std::env', 'std::process', 'Box::', 'Vec::', '.clone(', '.source(', '.to_string(', '.inspect_v1(&mut']:
        check('source-prohibited',forbidden not in source,forbidden)
    check('source-prohibited',source.count('.inspect_v1()')==1,'one shared inspect')
    check('source-prohibited',source.count('.usage_v1()')==4,'4 textual usage sites, path-specific bound')
    outer_result=item(source,'enum','OuterResultV1')
    for forbidden in ['&','File','OwnedFixtureOutcomeV1','PrepaidOwnedV1','DestroyedStorageV1']:check('source-prohibited',forbidden not in outer_result,('result escape',forbidden))
    borrow=item(source,'fn','borrow_original_diagnostics_once_v1')
    check('source-lifetime',"owned: &'a PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>" in borrow and "Option<BorrowedOriginalDiagnosticsV1<'a>>" in borrow,'view lifetime tied to wrapper borrow')
    consume=item(source,'fn','consume_outer_request_v1')
    for first,second in [('observe_borrowed_originals_v1(borrowed)','destroy_returned_fixture_v1(owned)'),('destroy_returned_fixture_v1(owned)','release_after_retirement_v1(destroyed)'),('release_after_retirement_v1(destroyed)','let after_retirement')]:
        check('source-lifetime',consume.index(first)<consume.index(second),(first,second))
    destroy=item(account,'fn','destroy_owned_v1')
    for first,second in [('drop(owned)','self.reservation.take()'),('self.reservation.take()','drop(self)'),('drop(self)','Some(DestroyedStorageV1')]:check('source-lifetime',destroy.index(first)<destroy.index(second),(first,second))
    check('source-lifetime','release_destroyed_v1' not in destroy,'destroy has no release')
    drop_impl=account[account.index('impl<T> Drop for PrepaidOwnedV1'):account.index('pub(super) struct DestroyedStorageV1')]
    check('source-lifetime','release_destroyed_v1' not in drop_impl and 'drop(owned)' in drop_impl,'ordinary drop no release')

    # Recursively inspect the exact frozen source type definitions behind each roster category.
    wanted=['ReviewedFixtureBindingV1','SetupOutcomeV1','OwnedFixtureOutcomeV1','SwiftRunBudget','SnapshotPreScopeFailureV1','SnapshotScopeFinishV1','SnapshotPrimaryRetirementV1','SnapshotAttemptV1','SnapshotExportErrorV1','SnapshotWasiAttachmentV1','LoaderFailureV1','ReturnedLoaderFilesV1','SwiftRunFailure','WasiFailure']
    definitions={}
    for member in read(P/'source-custody.json'):
        path=ROOT/member['origin']
        if path.suffix!='.rs':continue
        text=path.read_text()
        for name in wanted:
            match=re.search(r'\b(struct|enum) '+name+r'\b',text)
            if match:
                definitions[name]=dict(origin=member['origin'],source_sha256=member['sha256'],line=text[:match.start()].count('\n')+1,definition=item(uncomment(text),match.group(1),name))
    for name in wanted:check('source-roster',name in definitions,name)
    budget_fields=['source_bytes','metadata_bytes','cache_bytes','cache_entry_bytes','cache_entries','active_pins','cache_work','frames','values','controls','memory_pages','state_bytes','combined_bytes','instruction_fuel','execution_work','host_calls','deadline_ms']
    check('source-roster',fields(definitions['SwiftRunBudget']['definition'],'SwiftRunBudget')==budget_fields,'all 17 product budget fields remain explicit future inputs')
    roster=read(P/'owner-roster.json')
    check('source-roster',len(roster['new_P0_owners'])==8 and len(roster['original_payload_owners_and_diagnostic_pointees'])==10,'owner categories')
    for name in ['stage','original','files','original_files','original_loader_usage','rows','snapshot','cancellation_owner','claims_owner','primary','retirement','primary_retirement','cache_retirement','scope_adopted_retirement','wasi_attachment','wasi_retirement','usage','variant','header_error','header','construction_completion','adopted_retirement','export','phase_completion','io','validation','cause','post_stop','construction','completion']:
        check('source-roster',name in json.dumps(roster['original_payload_owners_and_diagnostic_pointees']),name)
    source_bytes=(ROOT/'verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm').read_bytes()
    check('source-constraints',len(source_bytes)==1947 and sha(source_bytes)=='9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806','actual selected source')
    digest_region=source[source.index('const SELECTED_SOURCE_SHA256_V1'):source.index('const SELECTED_VALIDATION_LIMITS_V1')]
    check('source-constraints',bytes(int(n,16) for n in re.findall('0x([0-9a-f]{2})',digest_region)).hex()==sha(source_bytes),'all 32 source digest bytes')
    check('source-constraints','[1947, 1_000_000, 65_536, 1_000_000, 10_000]' in source,'five validation constraints')

    full=gzip.decompress((COMPILE/'query.mir.gz').read_bytes())
    artifact=next(a for a in compiler['artifacts'] if a['path']=='query.mir')
    check('custody',len(full)==artifact['bytes'] and sha(full)==artifact['sha256'],'full MIR exact compressed custody')
    text=full.decode(); function_names=['selected_outer_request_v1','borrow_original_diagnostics_once_v1','observe_borrowed_originals_v1','run_selected_one_fixture_outer_v1','consume_outer_request_v1']
    functions={name:mir_function(text,name) for name in function_names}; paths_by_function={}
    for name,body in functions.items():
        _,paths=graph_paths(body);paths_by_function[name]=paths
    inspect=functions['borrow_original_diagnostics_once_v1']
    check('mir-lifetime',uncomment(inspect).count('::inspect_v1(')==1,'compiled helper sole inspect')
    observer=uncomment(functions['observe_borrowed_originals_v1'])
    check('mir-lifetime',' -> [' not in observer,'compiled observer no calls/callbacks')
    normal=uncomment(functions['consume_outer_request_v1'])
    check('mir-lifetime',normal.index('StorageDead(_31)')<normal.index('destroy_returned_fixture_v1(move _37)'),'borrow carrier dead before owner destruction')
    check('mir-lifetime','_37 = move _14;' in normal,'actual original owner moved into destruction')
    check('mir-lifetime','_39 = move ((_36 as Some).0:' in normal and '_41 = move _39;' in normal,'same returned token moves once into release')
    for route in paths_by_function['consume_outer_request_v1']:
        events=route['events']
        for event,maximum in [('I',1),('U',3),('fixture',1),('destroy-call',1),('destroy-returned',1),('token',1),('release',1)]:check('mir-route',events.count(event)<=maximum,(event,route))
        if 'release' in events:
            for previous in ['I','fixture','destroy-call','destroy-returned','token']:check('mir-route',previous in events and events.index(previous)<events.index('release'),('premature release',previous,route))
        if route['terminal']=='return' and 'token' in events:check('mir-route',events.count('release')==1,('normal token unreleased',route))
        if 'I' in events:check('mir-route',events.count('U')>=2,('inspect before while-owned snapshot',route))
    maxima={e:max(p['events'].count(e) for p in paths_by_function['consume_outer_request_v1']) for e in ['I','U','fixture','release']}
    check('mir-route',maxima==dict(I=1,U=3,fixture=1,release=1),'exact conditional maxima')
    check('arithmetic',2628088+194231*1+1039*3==2825436,'inherited old account surface only')

    # Independent synthetic phase oracle: exercise hostile operations at every prefix.
    phases=['charged','borrowed','borrow-ended','destruction-started','payload-destroyed','carrier-destroyed','token-returned','released']
    def allowed(phase,event):
        return {'inspect':phase=='charged','end-borrow':phase=='borrowed','destroy':phase=='borrow-ended','payload-drop':phase=='destruction-started','carrier-drop':phase=='payload-destroyed','token':phase=='carrier-destroyed','release':phase=='token-returned'}.get(event,False)
    events=['inspect','end-borrow','destroy','payload-drop','carrier-drop','token','release']
    for i,phase in enumerate(phases):
        for j,event in enumerate(events):check('adversarial-phase',allowed(phase,event)==(i==j),(phase,event))
    original_kinds=['setup-ready-defensive','setup-io-refused','setup-invariant','loader-io-and-validation','leaf-primary-and-retirement-failed','leaf-returned-with-independent-retirement-failures','missing-payload-defensive']
    for kind in original_kinds:
        originals=[object() for _ in range(9)]
        owner={'kind':kind,'originals':originals}; shared=owner
        check('adversarial-originals',shared is owner and all(a is b for a,b in zip(owner['originals'],originals)),kind)
        for token in [False,True]:
            release_count=1 if token else 0
            check('adversarial-originals',release_count==int(token),(kind,token))
            for unwind_prefix in range(7):check('adversarial-unwind',not allowed(phases[unwind_prefix],'release'),(kind,token,unwind_prefix))
    report=dict(schema=1,status='bounded-independent-source-and-production-compiler-review-no-blocking-source-finding',assertions=sum(COUNTS.values()),groups=COUNTS,compiler_query_count=1,compiler_observations=44,types_measured=22,conditional_route_maxima=maxima,consume_direct_terminal_paths=len(paths_by_function['consume_outer_request_v1']),selected_route_actual='ImmutableBindingAndP0ReviewPending before account or fixture dispatch',source_constraints_only=True,new_outer_work_and_storage_priced=False,all_three_selectors_pending=True,producer_missing_terminal_facts_preserved=True,rust_test_bodies_compiled_or_run=False,actual_fixture_io_product_test_native_runtime=False,healthy_close_or_operational_grant=False,OTA_FieldLog_GA=False)
    write(HERE/'reviewed-type-definitions.json',definitions)
    write(HERE/'mir-paths.json',paths_by_function)
    write(HERE/'results.json',report)
    print(json.dumps(report,sort_keys=True))

if __name__=='__main__':main()
