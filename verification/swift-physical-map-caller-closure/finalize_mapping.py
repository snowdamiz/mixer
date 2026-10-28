#!/usr/bin/env python3
"""Finalize a negative mapping from immutable saved artifacts; stdlib only."""
import datetime, hashlib, json, pathlib, platform, re, signal, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
signal.alarm(55)
START = time.monotonic()
NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
H = lambda b: hashlib.sha256(b).hexdigest()
def write(name, obj):
    data=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode(); (OUT/name).write_bytes(data)
    return {'path':str((OUT/name).relative_to(ROOT)), 'bytes':len(data), 'sha256':H(data)}
def pin(path, data):
    st=path.stat()
    return {'path':str(path.relative_to(ROOT)), 'bytes':len(data), 'sha256':H(data),
            'device':st.st_dev,'inode':st.st_ino,'mtime_ns':st.st_mtime_ns}
def span(data,b,e):
    return {'byte_begin':b,'byte_end_exclusive':e,'line_begin':data.count(b'\n',0,b)+1,
            'line_end_inclusive':data.count(b'\n',0,e-1)+1,'bytes':e-b,'sha256':H(data[b:e])}
def lines(data):
    p=0
    for n,line in enumerate(data.splitlines(keepends=True),1):
        yield n,p,line
        p+=len(line)
method={
 'schema':1,'at':NOW(),'status':'frozen-before-final-mapping-access',
 'command':'python3 verification/swift-physical-map-caller-closure/finalize_mapping.py',
 'tool':{'python_implementation':platform.python_implementation(),'python_version':sys.version,
         'version_provenance':'running stdlib process; no external compiler/version command'},
 'script':pin(pathlib.Path(__file__),pathlib.Path(__file__).read_bytes()),
 'source_revision':'9e860ea12074ca31bef4087ce34177a03f295dd8',
 'method':['Revalidate exact selected raw pair against accepted custody and initial index pins.',
           'Validate complete pinned source/MIR files and exact selected Caller/Closure spans; retain complete anchor excerpts.',
           'Index all LLVM definitions with exact byte/line span and whole SHA-256, all LLVM aliases/declarations with the target name, every DISubprogram record, and every assembly function delimited by cfi_startproc/cfi_endproc.',
           'Enumerate all target-file debug subprograms and all source-file line 853/861 subprogram candidates, using file metadata and scope references only as identity evidence.',
           'Literal target occurrences include definitions, declarations, aliases, metadata, instruction references, assembly symbols and comments; zero occurrences cannot be promoted to a mapped function.',
           'Missing definitions/debug identity/native edges produce incomplete status. Do not claim DCE cause, private linkage, mangled alternative identity, or reachability from negative textual evidence.',
           'No compiler, linker, native runtime, test, model, verifier input, subprocess version or capture retry invocation.'],
 'bounds':{'maximum_each_command_seconds':55,'maximum_total_distinct_raw_artifact_bytes':67108864,'maximum_derived_bytes':8388608},
 'meaning':'Offline identity mapping only; no geometry/alias/capacity/prices/backings/destruction or GA acceptance.'}
write('finalization-index-method.json',method)
selection_path=ROOT/'verification/swift-semantic-adapter-root-review/dispatch-physical-mapping-selection.json'
selection_data=selection_path.read_bytes(); selection=json.loads(selection_data)
frontier_path=ROOT/selection['target_frontier']['path']; frontier_data=frontier_path.read_bytes()
assert len(frontier_data)==selection['target_frontier']['bytes'] and H(frontier_data)==selection['target_frontier']['sha256']
frontier=json.loads(frontier_data)
accept_path=ROOT/selection['capture_acceptance']['path']; accept_data=accept_path.read_bytes()
assert len(accept_data)==selection['capture_acceptance']['bytes'] and H(accept_data)==selection['capture_acceptance']['sha256']
accept=json.loads(accept_data)
seal_path=ROOT/accept['independent_terminal_review']['path']; seal_data=seal_path.read_bytes()
assert len(seal_data)==accept['independent_terminal_review']['bytes'] and H(seal_data)==accept['independent_terminal_review']['sha256']
raws={}; before=[]
for expected in selection['artifacts']:
    path=ROOT/expected['path']; data=path.read_bytes(); p=pin(path,data)
    assert p['bytes']==expected['bytes'] and p['sha256']==expected['sha256']
    raws[path.suffix]=(path,data); before.append(p)
assert sum(p['bytes'] for p in before)<=67108864
write('finalization-input-pins-before.json',{'schema':1,'at':NOW(),'raw_artifacts':before,
 'selection':pin(selection_path,selection_data),'frontier':pin(frontier_path,frontier_data),
 'capture_acceptance':pin(accept_path,accept_data),'independent_terminal_seal':pin(seal_path,seal_data),
 'raw_pair_total_distinct_bytes':sum(p['bytes'] for p in before)})
manifest_path=ROOT/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json'
manifest_data=manifest_path.read_bytes(); manifest=json.loads(manifest_data)
assert H(manifest_data)=='5f20215aef11436b0a3cde511c0820450f37a613de20e74d810728bd5efa8249'
assert manifest['member_count']==146 and manifest['tree_sha256']==frontier['source146_tree_sha256']
anchor_inputs={}; anchors=[]
for target in frontier['targets']:
    if target['id'] not in ['Caller','Closure']: continue
    record={'id':target['id'],'name':target['name'],'anchors':{}}
    for kind in ['source','retained_MIR']:
        anchor=target[kind]; file=anchor['file']; path=ROOT/file['path']
        if file['path'] not in anchor_inputs:
            data=path.read_bytes(); p=pin(path,data)
            assert p['bytes']==file['bytes'] and p['sha256']==file['sha256']
            anchor_inputs[file['path']]=(path,data,p)
        path,data,p=anchor_inputs[file['path']]
        b,e=anchor['byte_begin'],anchor['byte_end']; selected=data[b:e]
        assert H(selected)==anchor['span_sha256']
        excerpt_name=target['id'].lower()+'-'+kind.lower()+'.txt'
        (OUT/excerpt_name).write_bytes(selected)
        record['anchors'][kind]={'input':p,'span':span(data,b,e),'expected_span_sha256':anchor['span_sha256'],
                                'complete_anchor_excerpt':excerpt_name,'excerpt_is_whole_original_function':kind=='retained_MIR'}
    anchors.append(record)
write('original-anchor-pins.json',{'schema':1,'at':NOW(),'manifest':pin(manifest_path,manifest_data),
 'source146_tree_sha256':manifest['tree_sha256'],'source146_tree_validation':'manifest exact pin checked; full 146-member tree not rehashed in this bounded partition',
 'anchors':anchors})
ll_path,ll=raws['.ll']; asm_path,asm=raws['.s']
defs=[]; metadata={}; current=None; declarations=[]; aliases=[]; ll_mentions=[]
for n,off,line in lines(ll):
    if line.startswith(b'define '):
        assert current is None
        m=re.search(rb'@(?:"([^"\n]+)"|([^\s(]+))\(',line); assert m
        current=(n,off,line,(m[1] or m[2]).decode())
    elif current and line.rstrip(b'\r\n')==b'}':
        begin_line,begin,header,symbol=current; end=off+len(line)
        defs.append({'symbol':symbol,'header':header.decode().rstrip('\n'),'span':{'byte_begin':begin,'byte_end_exclusive':end,
                     'line_begin':begin_line,'line_end_inclusive':n,'bytes':end-begin,'sha256':H(ll[begin:end])}}); current=None
    if line.startswith(b'declare '): declarations.append((n,off,line))
    if b' = ' in line and (b' alias ' in line or b' ifunc ' in line): aliases.append((n,off,line))
    m=re.match(rb'^!(\d+)\s*=\s*(.*)',line)
    if m: metadata[int(m[1])]=(n,off,m[2].decode().rstrip('\n'))
    if b'run_one_admitted_fixture_v1' in line: ll_mentions.append({'line':n,'byte':off,'text':line.decode()})
assert current is None
write('llvm-whole-definition-index.json',{'schema':1,'artifact':before[0],'count':len(defs),'complete':True,
 'span_convention':'bytes zero-based half-open; lines one-based inclusive; hash covers complete define header through closing-brace newline',
 'definitions':defs})
source_files=[]
for ident,(n,off,text) in metadata.items():
    if text.startswith('!DIFile(') and 'initial_profile_v1.rs' in text:
        source_files.append({'metadata_id':ident,'line':n,'byte':off,'text':text})
file_ids={x['metadata_id'] for x in source_files}
subprograms=[]; target_subprograms=[]
for ident,(n,off,text) in metadata.items():
    if '!DISubprogram(' not in text: continue
    record={'metadata_id':ident,'line':n,'byte':off,'text':text}
    subprograms.append(record)
    fm=re.search(r'\bfile: !(\d+)',text)
    if fm and int(fm[1]) in file_ids: target_subprograms.append(record)
debug_target_ids={x['metadata_id'] for x in target_subprograms}
scope_children=[]
for ident,(n,off,text) in metadata.items():
    sm=re.search(r'\bscope: !(\d+)',text)
    if sm and int(sm[1]) in debug_target_ids:
        scope_children.append({'metadata_id':ident,'line':n,'byte':off,'text':text})
write('debug-source-identity-index.json',{'schema':1,'artifact':before[0],
 'metadata_record_count':len(metadata),'DISubprogram_record_count':len(subprograms),
 'expected_source_file_records':source_files,'all_subprograms_with_expected_file':target_subprograms,
 'direct_metadata_scope_children_of_expected_file_subprograms':scope_children,
 'expected_source_line_853_861_subprograms':[x for x in target_subprograms if re.search(r'\bline: (853|861)(?:,|\))',x['text'])],
 'target_function_literal_occurrences':ll_mentions,'llvm_define_debug_attachment_count':sum('!dbg !' in x['header'] for x in defs),
 'limit':'Debug scope/file matches cannot substitute for an absent exact named function or closure identity.'})
asm_functions=[]; active=None; latest_label=None; asm_mentions=[]; assembly_label_count=0
for n,off,line in lines(asm):
    # Assembly emitted by this capture uses unquoted Rust symbols ending in a colon.
    lm=re.match(rb'^([^\s:][^:\n]*):(?:\s*(?:;.*)?)?\n?$',line)
    if lm and not lm[1].startswith(b'L'):
        latest_label=(n,off,lm[1].decode()); assembly_label_count+=1
    if b'.cfi_startproc' in line:
        assert active is None
        assert latest_label is not None
        active=latest_label
    if b'.cfi_endproc' in line:
        assert active is not None
        begin_line,begin,symbol=active; end=off+len(line)
        asm_functions.append({'symbol':symbol,'span':{'byte_begin':begin,'byte_end_exclusive':end,
           'line_begin':begin_line,'line_end_inclusive':n,'bytes':end-begin,'sha256':H(asm[begin:end])}})
        active=None
    if b'run_one_admitted_fixture_v1' in line: asm_mentions.append({'line':n,'byte':off,'text':line.decode()})
assert active is None
write('assembly-whole-function-index.json',{'schema':1,'artifact':before[1],'count':len(asm_functions),
 'complete_cfi_pairs':True,'nonlocal_label_count':assembly_label_count,
 'span_convention':'bytes zero-based half-open; lines one-based inclusive; hash covers nonlocal function symbol label through cfi_endproc newline; directives before the label excluded explicitly',
 'functions':asm_functions,'target_literal_occurrences':asm_mentions})
assert not ll_mentions and not asm_mentions
assert not [d for d in defs if 'run_one_admitted_fixture_v1' in d['symbol']]
summary={
 'schema':1,'at':NOW(),'status':'incomplete-required-Caller-and-Closure-definitions-not-identified',
 'source_revision':'9e860ea12074ca31bef4087ce34177a03f295dd8',
 'source146_tree_sha256':frontier['source146_tree_sha256'],
 'raw_artifacts':before,'raw_pair_total_distinct_bytes':sum(p['bytes'] for p in before),
 'original_source_and_MIR_anchors_verified':True,
 'capture_acceptance':pin(accept_path,accept_data),'independent_terminal_review':pin(seal_path,seal_data),
 'indexed':{'llvm_definitions':len(defs),'llvm_declarations':len(declarations),'llvm_aliases_or_ifuncs':len(aliases),
            'llvm_debug_metadata_records':len(metadata),'llvm_DISubprogram_records':len(subprograms),
            'assembly_complete_cfi_functions':len(asm_functions)},
 'targets':[{'id':'Caller','expected_name':'run_one_admitted_fixture_v1','source_lines':'853-862',
             'status':'incomplete-no-unique-actual-LLVM-definition-or-native-assembly-function-identified',
             'llvm_definition':None,'native_assembly_function':None,'llvm_literal_occurrences':0,'assembly_literal_occurrences':0,
             'actual_call_edges':[],'required_facts_unresolved':['caller frame','child result destination','outer Result destination','direct Dispatch instantiation']},
            {'id':'Closure','expected_name':'run_one_admitted_fixture_v1::{closure#0}','source_identity':'861:36 || run_prepaid_admitted_fixture_v1(fixture, attempt, expected)',
             'status':'incomplete-no-unique-actual-LLVM-definition-or-native-assembly-function-identified',
             'llvm_definition':None,'native_assembly_function':None,'llvm_literal_occurrences':0,'assembly_literal_occurrences':0,
             'actual_call_edges':[],'required_facts_unresolved':['exact closure 861:36 native identity','callee return-pointer forwarding','closure frame and return']}],
 'interpretation':'The named Caller has no literal occurrence anywhere in either exact saved artifact. No actual Caller or exact Closure body can be bound. The mapping remains incomplete. This does not establish why bodies are absent; no private/DCE/renaming cause is asserted, and generic MIR/source presence is not native presence.',
 'unknown':['geometry','physical arena identities and offsets','return-slot and child aliases','native frame/call peak','backing capacity','destruction/unwind obligations','prices','root funding'],
 'actual_geometry_verifier_input_run':False,'physical_peak_or_capacity_accepted':False,
 'source_flag_or_reachability_changes':False,'compiler_or_runtime_invocations':0,'capture_retry':False,
 'UI_simulator_device_capture_processes_started':False,
 'frontier_complete':False,'root_semantic_approval':False,'GA_accepted':False,
 'next_step':'Root independent review of the merged four-target map; no automatic retry, alternative compiler/flags/source wrapper or reachability change authorized.'}
write('mapping-report.json',summary)
after=[pin(path,path.read_bytes()) for path,data in raws.values()]
assert after==before
anchor_after=[pin(path,path.read_bytes()) for path,data,p in anchor_inputs.values()]
assert anchor_after==[p for path,data,p in anchor_inputs.values()]
write('finalization-input-pins-after.json',{'schema':1,'at':NOW(),'raw_artifacts':after,
 'raw_equal_before':after==before,'anchor_inputs':anchor_after,'anchors_equal_before':True,
 'elapsed_seconds':time.monotonic()-START,'derived_bytes_before_final_seal':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())})
assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<=8388608
print(json.dumps({'status':summary['status'],'indexed':summary['indexed'],
                  'expected_source_file_debug_records':len(source_files),'expected_file_subprograms':len(target_subprograms),
                  'source_line_853_861_subprograms':len([x for x in target_subprograms if re.search(r'\bline: (853|861)(?:,|\))',x['text'])]),
                  'derived_bytes':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),'elapsed_seconds':time.monotonic()-START},indent=2))
