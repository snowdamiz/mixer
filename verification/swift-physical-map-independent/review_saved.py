#!/usr/bin/env python3
"""Independent bounded read-only saved-artifact census and merged review."""
import time
START=time.monotonic()
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer')
D=Path(__file__).resolve().parent
CC=ROOT/'verification/swift-physical-map-caller-closure'
DB=ROOT/'verification/swift-physical-map-dispatch-body'
RR=ROOT/'verification/swift-semantic-adapter-root-review'
PINS={};DATA={}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
def pin(path,expected=None):
    assert time.monotonic()-START<53.5
    path=Path(path)
    if path not in PINS:
        info=path.lstat();assert stat.S_ISREG(info.st_mode) and path.resolve(strict=True)==path and info.st_size<=67108864
        h=hashlib.sha256();size=0
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            while block:=stream.read(262144):
                assert time.monotonic()-START<53.5
                size+=len(block);assert size<=info.st_size;h.update(block)
            after=os.fstat(stream.fileno())
        assert size==info.st_size and identity(info)==identity(opened)==identity(after)
        PINS[path]={'path':str(path.relative_to(ROOT)),'bytes':size,'sha256':h.hexdigest(),'device':info.st_dev,'inode':info.st_ino,'mtime_ns':info.st_mtime_ns}
    value=PINS[path]
    if expected:
        for key in ('bytes','sha256','device','inode','mtime_ns'):
            if key in expected:assert value[key]==expected[key],(str(path),key)
    return value
def raw(path,expected_sha=None):
    path=Path(path);entry=pin(path)
    if expected_sha:assert entry['sha256']==expected_sha
    if path not in DATA:
        with path.open('rb') as stream:value=stream.read(entry['bytes']+1)
        assert len(value)==entry['bytes'] and sha(value)==entry['sha256'];DATA[path]=value
    return DATA[path]
def load(path,expected_sha=None):
    def pairs(items):
        result={}
        for key,value in items:assert key not in result;result[key]=value
        return result
    return json.loads(raw(path,expected_sha),object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
def save(name,value):
    with (D/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def check_row(row):return pin(ROOT/row['path'],row)
def lines(value):
    offset=0
    for number,line in enumerate(value.splitlines(keepends=True),1):
        yield number,offset,line;offset+=len(line)
    assert offset==len(value)

selection=load(RR/'dispatch-physical-mapping-selection.json','bad62b51344efcc72640c0eaad4f25e721901e4b2e6c35b6887ffaba035c8aa1')
assert selection['bounds']=={'maximum_each_command_seconds':55,'maximum_total_raw_artifact_bytes':67108864,'maximum_derived_bytes_each_partition':8388608}
assert selection['frontier_complete'] is selection['actual_verifier_input_run_released'] is selection['GA_accepted'] is False
for key in ('capture_acceptance','target_frontier'):check_row(selection[key])
acceptance=load(ROOT/selection['capture_acceptance']['path'])
for key in ('receipt','capture_observation','observations','independent_terminal_review'):check_row(acceptance[key])
frontier=load(ROOT/selection['target_frontier']['path'])
assert [row['id'] for row in frontier['targets']]==['Caller','Closure','Dispatch','Body']
cc_seal=load(CC/'final-seal.json','b639e106e5645932350a511ef3d812e6124f9732238d536e4e37ffbbc4babd2c')
db_seal=load(DB/'seal.json','bc89fe72d1cdace89cda45644bd801c201c7caedd69ab069dbcc52405fb94b48')
assert len(cc_seal['files'])==cc_seal['derived_file_count_excluding_seal']==21
assert len(db_seal['derived_members'])==14
for sealed,folder,entries in [(cc_seal,CC,cc_seal['files']),(db_seal,DB,db_seal['derived_members'])]:
    assert len({row['path'] for row in entries})==len(entries)
    assert sum(row['bytes'] for row in entries)==sealed['derived_bytes_excluding_seal']<=8388608
    for row in entries:
        assert Path(row['path']).parent==folder.relative_to(ROOT)
        check_row(row)
    assert all(not path.is_symlink() and path.is_file() for path in folder.iterdir())
    assert {str(path.relative_to(ROOT)) for path in folder.iterdir()}=={row['path'] for row in entries}|{str((folder/('final-seal.json' if folder==CC else 'seal.json')).relative_to(ROOT))}
cc_report=load(CC/'mapping-report.json');db_report=load(DB/'mapping.json')
cc_index=load(CC/'candidate-index.json');db_index=load(DB/'index-candidates.json')
llvm_index=load(CC/'llvm-whole-definition-index.json');asm_index=load(CC/'assembly-whole-function-index.json');debug_index=load(CC/'debug-source-identity-index.json')
for item in db_seal['inputs_rechecked_unchanged_at_freeze']:check_row(item)
for item in db_index['inputs']:check_row(item)
before_cc=load(CC/'input-pins-before.json');after_cc=load(CC/'input-pins-after-index.json')
before_final=load(CC/'finalization-input-pins-before.json');after_final=load(CC/'finalization-input-pins-after.json')
assert before_cc['raw_artifacts']==after_cc['raw_artifacts']==before_final['raw_artifacts']==after_final['raw_artifacts']==cc_report['raw_artifacts']
assert after_cc['equal_before'] is after_final['raw_equal_before'] is after_final['anchors_equal_before'] is True
for item in after_final['anchor_inputs']:check_row(item)
for key in ('selection','frontier','capture_acceptance','independent_terminal_seal'):check_row(before_final[key])
for item in before_final['raw_artifacts']:check_row(item)
assert before_cc['total_distinct_raw_artifact_bytes']==before_final['raw_pair_total_distinct_bytes']==58805427
assert db_seal['raw_unique_artifact_bytes']==cc_seal['raw_pair_total_distinct_bytes']==db_index['raw_artifact_unique_bytes']==58805427
assert after_cc['elapsed_seconds']<55 and after_final['elapsed_seconds']<55 and db_index['elapsed_seconds']<55
assert cc_seal['raw_input_pins_rechecked_at_seal'] is cc_seal['source_MIR_and_control_pins_rechecked_at_seal'] is True
assert db_index['raw_artifact_full_hash_passes_each']==2 and db_index['no_compiler_native_test_model_verifier_or_geometry_run'] is True
# Bind and inspect the entire exact pair; names count across all bytes, not snippets.
artifacts={}
for item in selection['artifacts']:check_row(item);artifacts[Path(item['path']).suffix]=raw(ROOT/item['path'])
assert sum(len(value) for value in artifacts.values())==58805427<67108864
ll=artifacts['.ll'];assembly=artifacts['.s']
terms=['run_one_admitted_fixture_v1','run_prepaid_admitted_fixture_v1','dispatch_v1','AdmittedFixtureOutcomeV1','ReservationV1','PrepaidOwnedV1','host_account_v1.rs','initial_profile_v1.rs']
occurrences={kind:{term:value.count(term.encode()) for term in terms} for kind,value in artifacts.items()}
for kind in occurrences:
    assert all(occurrences[kind][term]==0 for term in terms if term!='initial_profile_v1.rs')
    assert occurrences[kind]['initial_profile_v1.rs']==2
for item in db_index['artifacts']:
    kind=Path(item['input']['path']).suffix;check_row(item['input'])
    assert item['whole_artifact_literal_occurrences']==occurrences[kind] and item['candidates']==[]
    assert item['whole_artifact_line_coverage']=={'bytes_covered':len(artifacts[kind]),'first':1,'last_inclusive':len(artifacts[kind].splitlines()),'no_input_truncation':True}
    assert item['disk_sha256_after_index']==item['input']['sha256'] and item['disk_stat_unchanged_after_index'] is True
    assert item['line_count']==len(artifacts[kind].splitlines())
assert cc_index['llvm_all_target_mentions']==cc_index['assembly_all_target_mentions']==cc_index['llvm_candidate_definitions']==[]
assert cc_index['llvm_definition_count_all']==3758
# Independently enumerate complete definition boundaries, then verify every frozen span/hash.
definition_spans=[];active=None;declarations=0;aliases=0;metadata={}
for number,offset,line in lines(ll):
    if number%8192==0:assert time.monotonic()-START<53.5
    if line.startswith(b'define '):
        assert active is None and line.rstrip().endswith(b'{')
        active=(number,offset,line.rstrip(b'\n'))
    elif line.rstrip(b'\r\n')==b'}':
        assert active is not None
        first,start,header=active;end=offset+len(line)
        definition_spans.append((start,end,first,number,header));active=None
    if line.startswith(b'declare '):declarations+=1
    if line.startswith(b'@') and (b' alias ' in line or b' ifunc ' in line):aliases+=1
    if line.startswith(b'!'):
        match=re.match(rb'!(\d+) = (.*)',line)
        if match:
            ident=int(match.group(1));assert ident not in metadata
            metadata[ident]=(number,offset,match.group(2).decode().rstrip('\n'))
assert active is None and len(definition_spans)==3758 and declarations==145 and aliases==0 and len(metadata)==174794
assert llvm_index['complete'] is True and llvm_index['count']==len(llvm_index['definitions'])==3758
previous=0;llvm_symbols=[]
for item,(start,end,first,last,header) in zip(llvm_index['definitions'],definition_spans):
    entry=item['span'];assert previous<=start<end;previous=end
    assert entry=={'byte_begin':start,'byte_end_exclusive':end,'bytes':end-start,'line_begin':first,'line_end_inclusive':last,'sha256':sha(ll[start:end])}
    assert item['header'].encode()==header
    symbol=re.search(rb'@(?:"([^"\n]+)"|([^\s(]+))\(',header);assert symbol
    assert item['symbol'].encode()==(symbol[1] or symbol[2]);llvm_symbols.append(item['symbol'])
check_row(llvm_index['artifact'])
# Assembly: match every CFI start/end and its preceding nonlocal symbol label.
function_spans=[];active=None;latest_symbol=None;cfi_starts=0;cfi_ends=0;begin_labels=0;end_labels=0
for number,offset,line in lines(assembly):
    if number%8192==0:assert time.monotonic()-START<53.5
    stripped=line.strip()
    if stripped.startswith(b'Lfunc_begin') and stripped.endswith(b':'):begin_labels+=1
    if stripped.startswith(b'Lfunc_end') and stripped.endswith(b':'):end_labels+=1
    # Quoted or local labels are not the selected emitted Rust symbol labels.
    candidate=line.split(b';',1)[0].rstrip()
    if candidate.endswith(b':') and candidate[:1] not in (b' ',b'\t') and not candidate.startswith(b'L'):
        latest_symbol=(number,offset,candidate[:-1].decode())
    if stripped==b'.cfi_startproc':
        cfi_starts+=1;assert active is None and latest_symbol is not None;active=latest_symbol
    if stripped==b'.cfi_endproc':
        cfi_ends+=1;assert active is not None
        first,start,symbol=active;function_spans.append((start,offset+len(line),first,number,symbol));active=None
assert active is None and cfi_starts==cfi_ends==begin_labels==end_labels==3758
assert asm_index['complete_cfi_pairs'] is True and asm_index['count']==len(asm_index['functions'])==3758
previous=0;assembly_symbols=[]
for item,(start,end,first,last,symbol) in zip(asm_index['functions'],function_spans):
    assert previous<=start<end;previous=end
    assert item['span']=={'byte_begin':start,'byte_end_exclusive':end,'bytes':end-start,'line_begin':first,'line_end_inclusive':last,'sha256':sha(assembly[start:end])}
    assert item['symbol']==symbol;assembly_symbols.append(symbol)
check_row(asm_index['artifact'])
assert len(set(llvm_symbols))==len(set(assembly_symbols))==3758
llvm_to_asm_missing=sorted(set('_'+name for name in llvm_symbols)-set(assembly_symbols))
asm_to_llvm_missing=sorted(set(assembly_symbols)-set('_'+name for name in llvm_symbols))
# Verify the exhaustive directly attributed source/debug census independently.
subprograms={ident:row for ident,row in metadata.items() if '!DISubprogram(' in row[2]}
files={ident:row for ident,row in metadata.items() if row[2].startswith('!DIFile(') and 'initial_profile_v1.rs' in row[2]}
assert len(subprograms)==13692 and len(files)==1
file_subprograms=[]
for ident,(number,offset,text) in subprograms.items():
    match=re.search(r'\bfile: !(\d+)',text)
    if match and int(match.group(1)) in files:file_subprograms.append({'metadata_id':ident,'line':number,'byte':offset,'text':text})
assert len(file_subprograms)==50
assert debug_index['metadata_record_count']==174794 and debug_index['DISubprogram_record_count']==13692
assert debug_index['all_subprograms_with_expected_file']==file_subprograms
assert debug_index['expected_source_file_records']==[{'metadata_id':ident,'line':row[0],'byte':row[1],'text':row[2]} for ident,row in files.items()]
assert not [item for item in file_subprograms if re.search(r'\bline: (?:853|861)(?:,|\))',item['text'])]
assert debug_index['expected_source_line_853_861_subprograms']==debug_index['target_function_literal_occurrences']==[]
expected_ids={item['metadata_id'] for item in file_subprograms};children=[]
for ident,(number,offset,text) in metadata.items():
    match=re.search(r'\bscope: !(\d+)',text)
    if match and int(match.group(1)) in expected_ids:children.append({'metadata_id':ident,'line':number,'byte':offset,'text':text})
assert debug_index['direct_metadata_scope_children_of_expected_file_subprograms']==children
assert debug_index['llvm_define_debug_attachment_count']==sum(b'!dbg !' in header for *_,header in definition_spans)
assert load(DB/'caller-closure-definition-headers.json')==load(DB/'assembly-label-structural-excerpts.json')==[]
hits=load(DB/'llvm-target-metadata-hits.json');assert len(hits)==1
selected_file=next(iter(files.values()));assert hits[0]['line']==selected_file[0] and hits[0]['byte_begin']==selected_file[1]
# Source/MIR anchors prove selected source identities, not native presence.
anchor_summary=[];source_files={}
cc_anchors=load(CC/'original-anchor-pins.json')
check_row(cc_anchors['manifest']);source_manifest=load(ROOT/cc_anchors['manifest']['path'])
assert sha(canonical(source_manifest['members']))==source_manifest['tree_sha256']==frontier['source146_tree_sha256']
for target in frontier['targets']:
    checked=[]
    for kind in ('source','retained_MIR'):
        anchor=target[kind];check_row(anchor['file']);value=raw(ROOT/anchor['file']['path'])
        start,end=anchor['byte_begin'],anchor['byte_end'];chunk=value[start:end]
        first=value.count(b'\n',0,start)+1;last=value.count(b'\n',0,end-1)+1
        assert sha(chunk)==anchor['span_sha256']
        if 'line_begin' in anchor:assert first==anchor['line_begin'] and last==anchor['line_end_inclusive']
        else:assert target['id']=='Closure' and kind=='source' and first==last==861 and chunk.decode()==anchor['expression']
        if target['id'] in ('Caller','Closure'):
            original=next(item for item in cc_anchors['anchors'] if item['id']==target['id'])['anchors'][kind]
            assert raw(CC/original['complete_anchor_excerpt'])==chunk
            assert original['span']=={'byte_begin':start,'byte_end_exclusive':end,'bytes':end-start,'line_begin':first,'line_end_inclusive':last,'sha256':sha(chunk)}
        else:assert raw(DB/(target['id'].lower()+'.'+kind+'.txt'))==chunk
        checked.append({'kind':kind,'file':anchor['file']['path'],'bytes':len(chunk),'span_sha256':sha(chunk)})
        if kind=='source':source_files[target['id']]=value
    anchor_summary.append({'id':target['id'],'anchors':checked})
assert b'run_one_admitted_fixture_v1' in raw(CC/'caller-source.txt')
assert raw(CC/'closure-source.txt')==b'|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)'
for target in cc_report['targets']:
    assert target['llvm_definition'] is target['native_assembly_function'] is None and target['actual_call_edges']==[]
for target in db_report['targets']:
    for key in ('LLVM_definition_sha256','LLVM_definition_whole_span','linkage_identity','native_assembly_function','native_assembly_whole_sha256','native_assembly_whole_span','native_call_edge_provenance','unique_LLVM_definition'):assert target[key] is None
    assert target['MIR_is_not_native_presence_evidence'] is target['all_required_native_facts_pending'] is True
for data in (cc_report,db_report,cc_seal,db_seal):
    assert data.get('frontier_complete',data.get('complete_frontier',False)) is False
    assert data.get('physical_peak_or_capacity_accepted',data.get('physical_peak_accepted',False)) is False
    assert data.get('root_semantic_approval',False) is False
    assert data.get('GA_accepted',data.get('product_GA_accepted',False)) is False
assert cc_report['indexed']=={'assembly_complete_cfi_functions':3758,'llvm_DISubprogram_records':13692,'llvm_aliases_or_ifuncs':0,'llvm_debug_metadata_records':174794,'llvm_declarations':145,'llvm_definitions':3758}
assert db_report['status']=='INCOMPLETE' and cc_report['compiler_or_runtime_invocations']==0 and cc_report['capture_retry'] is False
assert raw(DB/'inspection.stderr')==b''
census={'llvm_definitions':3758,'llvm_declarations':145,'llvm_aliases_ifuncs':0,'llvm_metadata_records':174794,'llvm_DISubprogram_records':13692,'assembly_CFI_functions':3758,'raw_line_counts':{'.ll':len(ll.splitlines()),'.s':len(assembly.splitlines())},'literal_occurrences':occurrences,'selected_DIFile_count':1,'direct_source_file_subprograms':50,'direct_source_line_853_861_subprograms':0,'LLVM_to_assembly_missing_symbol_count':len(llvm_to_asm_missing),'assembly_to_LLVM_missing_symbol_count':len(asm_to_llvm_missing),'whole_function_span_hashes_checked':7516}
save('independent-census.json',census)
save('source-anchor-checks.json',{'anchors':anchor_summary,'source146_manifest_verified':True,'source146_full_tree_rehashed':False,'generic_MIR_does_not_prove_actual_monomorphization':True})
before=sorted(PINS.values(),key=lambda item:item['path']);old=dict(PINS);PINS.clear()
for path,expected in old.items():pin(path,expected)
after=sorted(PINS.values(),key=lambda item:item['path']);assert before==after
save('checked-inputs.json',{'before':before,'after':after,'equal':True,'tree_sha256':sha(canonical(before))})
result={
 'schema':1,'status':'FROZEN_INDEPENDENT_MERGED_MAPPING_REVIEW_INCOMPLETE_ALL_FOUR_TARGETS',
 'at':datetime.now(timezone.utc).isoformat(),'findings':[],'merged_incomplete_conclusion_accepted':True,
 'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],
 'review_script_sha256':sha(Path(__file__).read_bytes()),'python':sys.version,'elapsed_seconds':time.monotonic()-START,
 'checked_input_members':len(before),'before_after_custody_equal':True,
 'prior_own_review_failure_preserved':'review-attempt-1 preserves the original script/stdout/stderr. It assumed line fields on the Closure byte-only source anchor;corrected review derives and checks line861 without changing either frozen producer packet.',
 'selection':pin(RR/'dispatch-physical-mapping-selection.json'),'caller_closure_seal':pin(CC/'final-seal.json'),'dispatch_body_seal':pin(DB/'seal.json'),
 'raw_unique_artifact_bytes':58805427,'source146_tree_sha256':frontier['source146_tree_sha256'],'whole_function_span_hashes_checked':7516,
 'independent_census':census,'unresolved_targets':['Caller','Closure','Dispatch','Body'],
 'accepted_boundary':'Both frozen mapping lanes correctly report incomplete. Full exact artifacts have no literal target-name candidate;complete indexes and selected source/debug anchors identify no uniquely bindable actual body or native call edge for any of the four targets.',
 'cause_of_nonidentification':'Unproved. No DCE,private-linkage,renaming,cfg or toolchain cause follows from the negative name/debug census.',
 'recommendation':'Accept the merged incomplete result and preserve current evidence. No additional mapping or recapture is authorized automatically. An optional separately selected source-only assessment of exact source146 module/cfg/visibility and instantiation roots could clarify source-level reachability requirements;it cannot establish the compiler cause or upgrade this capture.',
 'safe_next_assessment_needed_for_this_decision':False,
 'limits':[
  'Zero exact-name occurrences and absent direct file/line subprogram identities are bounded negative evidence,not proof of absent machine semantics under every possible renaming or representation.',
  'Original source/MIR spans verify source identity and generic/template structure only;they supply no actual native monomorphization,return destination,frame,call or cleanup mapping.',
  'No geometry,aliases,physical peak,whole capacity,backing/destruction bounds,numeric prices,root funding,product integration,publication or GA is accepted.',
  'All existing native/device/UI/capture/local-custody and UnitA holds remain;only new owned offline review files were written.'
 ],
 'compiler_version_link_test_model_native_geometry_verifier_or_process_probe_actions':0,
 'canonical_product_metadata_commit_push_actions':0,'compiler_retry_or_source_flag_reachability_change':False,
 'frontier_complete':False,'root_semantic_approval':False,'physical_peak_or_capacity_accepted':False,'GA_accepted':False
}
assert time.monotonic()-START<55
save('review-result.json',result)
print(json.dumps({'status':result['status'],'checked_inputs':len(before),'LLVM_definitions':3758,'assembly_CFI_functions':3758,'source_file_subprograms':50,'unresolved_targets':4,'elapsed_seconds':result['elapsed_seconds']}))
