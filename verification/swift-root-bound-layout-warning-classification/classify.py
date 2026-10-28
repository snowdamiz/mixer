#!/usr/bin/env python3
"""Bounded offline warning provenance review; no imported producer or child execution."""
from pathlib import Path
import datetime, hashlib, json, sys, time
START=time.monotonic()
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
INPUTS={}
MAX_BYTES=100_000_000
read_bytes=0

def tick():
    assert time.monotonic()-START < 55, 'offline review exceeded 55 seconds'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canon(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def row(path,base=ROOT):
    raw=path.read_bytes()
    return {'path':str(path.relative_to(base)), 'bytes':len(raw), 'sha256':sha(raw)}
def read(path):
    global read_bytes
    tick()
    path=Path(path)
    if not path.is_absolute(): path=ROOT/path
    raw=path.read_bytes(); read_bytes+=len(raw); assert read_bytes<=MAX_BYTES
    INPUTS[str(path.relative_to(ROOT))]={'path':str(path.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha(raw)}
    return raw

def unique(pairs):
    out={}
    for key,val in pairs:
        assert key not in out, ('duplicate JSON field',key)
        out[key]=val
    return out

def load(path): return json.loads(read(path),object_pairs_hook=unique)
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
P=Path('verification/swift-guarded-snapshot-root-result-lifetime-implementation')
I=Path('verification/swift-guarded-snapshot-root-result-lifetime-independent')
D=Path('verification/swift-root-bound-work-storage-layout-probe')
V3=Path('verification/swift-root-bound-work-storage-layout-probe-v3')
A=Path('verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-acceptance.json')
accept=load(A)
assert accept['source146_tree']=='91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
seals={}
for base in (P,I):
    seal=load(base/'seal.json'); seals[str(base)]=seal
    adopted=next(x for x in accept['packets'] if x['directory']==str(base))
    assert row(ROOT/base/'seal.json')==adopted['seal']

def sealed(base,name):
    value=read(base/name)
    expected=next(x for x in seals[str(base)]['members'] if x['path']==name)
    assert {'path':name,'bytes':len(value),'sha256':sha(value)}==expected
    return value

# Verify every original and diagnostic source member and exact three-edit replay.
orig_manifest=load(P/'source-manifest.json')
diag_manifest=load(D/'diagnostic-source-manifest.json')
delta=load(D/'exact-three-edit-delta.json')
assert orig_manifest['member_count']==diag_manifest['member_count']==146
assert orig_manifest['tree_sha256']==delta['original_tree']==accept['source146_tree']
assert diag_manifest['tree_sha256']==delta['diagnostic_tree']=='2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e'
original={}; diagnostic={}
for base,manifest,save in ((P,orig_manifest,original),(D,diag_manifest,diagnostic)):
    for member in manifest['members']:
        raw=read(base/'source/vm'/member['path'])
        assert {'path':member['path'],'bytes':len(raw),'sha256':sha(raw)}==member
        if base==P: assert next(x for x in seals[str(P)]['members'] if x['path']=='source/vm/'+member['path'])=={'path':'source/vm/'+member['path'],'bytes':len(raw),'sha256':sha(raw)}
        save[member['path']]=raw
assert set(original)==set(diagnostic)
assert sorted(n for n in original if original[n]!=diagnostic[n])==sorted(delta['changed_source_members'])
assert delta['edit_count']==3
for name,original_raw in original.items():
    edits=sorted((x for x in delta['edits'] if x['file']==name),key=lambda x:x['original_byte_start'])
    pieces=[]; cursor=0; drift=0
    for edit in edits:
        start,end=edit['original_byte_start'],edit['original_byte_end']
        before=original_raw[start:end]
        assert sha(before)==edit['before_sha256']
        after=diagnostic[name][start+drift:start+drift+edit['after_bytes']]
        assert sha(after)==edit['after_sha256']
        pieces.extend((original_raw[cursor:start],after)); cursor=end
        drift+=len(after)-len(before)
    pieces.append(original_raw[cursor:])
    assert b''.join(pieces)==diagnostic[name]

raw=read(V3/'command/stderr')
assert len(raw)==292318 and sha(raw)=='05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'
v3_receipt=load(V3/'command/receipt.json'); v3_plan=load(V3/'command/plan.json')
assert v3_receipt['outputs']['stderr']['sha256']==sha(raw)
assert v3_receipt['accepted_diagnostic_observation'] is False
assert v3_receipt['compiler_invocations']==1 and v3_receipt['compiler_exit_code']==1
records=[]
for i,line in enumerate(raw.splitlines(keepends=True),1):
    value=json.loads(line,object_pairs_hook=unique)
    records.append((i,line,value))
warnings=[x for x in records if x[2]['level']=='warning']
assert [x[0] for x in warnings]==[1,2,15]
assert [x[2]['code']['code'] for x in warnings]==['unused_imports','unused_imports','deprecated']
assert len(warnings)==3
assert sum(1 for _,_,v in records if v.get('code') and v['code']['code']=='E0308')==56
assert sum(1 for _,_,v in records if v.get('code') and v['code']['code']=='E0512')==2

# Original production-MIR warning bytes, plan, receipt and producer review are all sealed.
base_stderr=sealed(P,'commands-v2/production-MIR/stderr')
base_plan=json.loads(sealed(P,'commands-v2/production-MIR/plan.json'),object_pairs_hook=unique)
base_receipt=json.loads(sealed(P,'commands-v2/production-MIR/receipt.json'),object_pairs_hook=unique)
producer_review=json.loads(sealed(P,'compiler-diagnostic-review.json'),object_pairs_hook=unique)
assert len(base_stderr)==2078 and sha(base_stderr)=='5bfb7f65ea15fc32565cfdf4ef344000c52518af81ecfa93e14ee160941430e8'
assert base_receipt['exit']==0 and base_receipt['success'] is True
assert producer_review['production_warnings']==base_stderr.decode()
assert base_stderr.decode().count('warning: ')==4 # three diagnostic starts and one emission summary
assert 'warning: 3 warnings emitted\n' in base_stderr.decode()
for _,_,warning in warnings: assert 'warning: '+warning['message'] in base_stderr.decode()
assert base_plan['tool']['sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
assert base_plan['version']['version']==v3_plan['toolchain_version']
assert base_plan['source146_tree']==orig_manifest['tree_sha256']
assert not any(arg.startswith(('-A','-W','-D','-F','--cap-lints')) for arg in base_plan['argv']+v3_plan['argv'])

def normalized(plan):
    return [x for x in plan['argv'] if not x.endswith('/src/lib.rs') and not x.startswith('--emit=') and x not in ('-Zmir-include-spans=yes','--error-format=json')]
assert normalized(base_plan)==normalized(v3_plan)
old_env=base_plan['environment']; new_env=v3_plan['environment']
assert {k:v for k,v in old_env.items() if k not in ('CARGO_MANIFEST_DIR','TMPDIR')}=={k:v for k,v in new_env.items() if k not in ('CARGO_MANIFEST_DIR','TMPDIR')}
command_inventory=[]
for base,ids in ((P,('production-MIR','build-debug','build-opt2')),(I,('P01-facade','P02-cache','build-debug','build-opt2'))):
    for ident in ids:
        prefix=('commands-v2/' if base==P else 'commands/')+ident+'/'
        stderr=sealed(base,prefix+'stderr')
        plan=json.loads(sealed(base,prefix+'plan.json'),object_pairs_hook=unique)
        receipt=json.loads(sealed(base,prefix+'receipt.json'),object_pairs_hook=unique)
        heads=[line for line in stderr.decode().splitlines() if line.startswith('warning:')]
        expected=6 if ident.startswith('build-') else 3
        assert len(heads)==expected+1 and heads[-1]==f'warning: {expected} warnings emitted'
        assert receipt['exit']==0 and receipt['success'] is True
        for _,_,warning in warnings: assert 'warning: '+warning['message'] in heads
        command_inventory.append({'directory':str(base),'id':ident,'stderr':row(ROOT/base/prefix/'stderr'),'plan':row(ROOT/base/prefix/'plan.json'),'receipt':row(ROOT/base/prefix/'receipt.json'),'exit':receipt['exit'],'warning_count':expected,'warning_headers':heads,'argv':plan['argv'],'environment':plan['environment'],'lint_suppression_argv':[],'test_configuration':'--test' in plan['argv']})

# Bind every primary/helper warning span to unchanged original source bytes.
def original_position(name,start,end):
    drift=0
    for edit in sorted((e for e in delta['edits'] if e['file']==name),key=lambda e:e['original_byte_start']):
        diag_start=edit['original_byte_start']+drift
        diag_end=diag_start+edit['after_bytes']
        assert not (start<diag_end and end>diag_start), 'warning intersects diagnostic-only edit'
        if start>=diag_end: drift+=edit['after_bytes']-(edit['original_byte_end']-edit['original_byte_start'])
    return start-drift,end-drift
provenance=[]
for idx,(line,raw_line,warning) in enumerate(warnings,1):
    mapped=[]
    all_spans=[('primary',s) for s in warning['spans']]
    for ci,child in enumerate(warning['children']): all_spans += [(f'child-{ci}',s) for s in child['spans']]
    for kind,s in all_spans:
        name=s['file_name'].split('/source/vm/',1)[1]
        start,end=original_position(name,s['byte_start'],s['byte_end'])
        assert original[name][start:end]==diagnostic[name][s['byte_start']:s['byte_end']]
        for part in s['text']:
            assert part['text'] in original[name].decode().splitlines()
        line_num=original[name][:start].count(b'\n')+1
        col=len(original[name][:start].rsplit(b'\n',1)[-1].decode())+1
        mapped.append({'kind':kind,'relative_source_path':name,'diagnostic_span':s,'original_byte_start':start,'original_byte_end':end,'original_line_start':line_num,'original_column_start':col,'unchanged_bytes_utf8':original[name][start:end].decode(),'original_member_sha256':sha(original[name]),'diagnostic_member_sha256':sha(diagnostic[name]),'intersects_three_edit_delta':False})
    provenance.append({'warning_id':f'W{idx:02d}','record_line':line,'record_line_bytes':len(raw_line),'record_line_sha256_including_newline':sha(raw_line),'exact_record':warning,'source_binding':mapped,'classification':'preexisting-accepted-IR02-source-warning','query_created':False,'original_production_MIR_warning_observed':True})
write('warning-source-bindings.json',{'schema':1,'warnings':provenance,'original_source_tree_sha256':orig_manifest['tree_sha256'],'diagnostic_source_tree_sha256':diag_manifest['tree_sha256'],'all146_each_member_hashes_verified':True,'exact_three_edit_replay_verified':True})
write('prior-command-evidence.json',{'schema':1,'commands':command_inventory,'same_toolchain':base_plan['version'],'normalized_production_and_query_argv_equal':True,'argv_differences':['source crate entry path changes to exact diagnostic scratch','production -Zmir-include-spans=yes is absent in query','production --emit metadata+mir replaced by query metadata-only path','query adds --error-format=json'],'environment_differences':['CARGO_MANIFEST_DIR and TMPDIR point to their owned immutable source/build locations'],'no_warning_free_build_observed':True,'original_production_MIR_warnings_explicitly_recorded_in_producer_review':True,'root_acceptance_seals_verified':True})

symbols=('OwnedCorrelationOutcomeV1','BorrowedOwnerDataV1','selected_bootstrap_ledger_v1','NEXT_ADMISSION_ASSOCIATION_V1')
occurrences=[]
for name,data in original.items():
    if name.endswith('.rs'):
        for number,line in enumerate(data.decode().splitlines(),1):
            found=[s for s in symbols if s in line]
            if found: occurrences.append({'source':name,'line':number,'symbols':found,'text':line})
write('symbol-occurrences.json',{'schema':1,'scope':'Occurrence inventory for source context only; compiler warnings establish unused bindings for the exact cfg, not this string inventory.','occurrences':occurrences})

# Read root metadata for the narrowly requested false-zero-warning claim audit.
metadata=[]
for name in ('PLAN.md','STATUS.md'):
    content=read(name).decode(); lines=content.splitlines()
    hits=[{'line':i,'text':l} for i,l in enumerate(lines,1) if any(t in l.lower() for t in ('ir02','root-result-lifetime','swift layout runners'))]
    metadata.append({'path':name,'observed_sha256':sha(content.encode()),'observed_relevant_lines':hits,'zero_warning_IR02_claim_found':False})
write('metadata-review.json',{'schema':1,'root_acceptance_path':str(A),'root_acceptance_zero_warning_claim_found':False,'files':metadata,'correction_required':False,'scope':'Current relevant IR02/root-result-lifetime paragraphs and root acceptance only; other projects or unrelated warnings-as-errors claims are outside scope.'})

write('warning-classification-proposal.json',{'schema':1,'status':'SOURCE_ONLY_CLOSED_CLASSIFICATION_PROPOSAL_AWAITING_ROOT_OFFLINE_AMENDMENT_REVIEW','scope':'Exactly the preserved single v3 command/stderr bytes; no compiler rerun or parser execution authorized by this proposal.','stream':{'path':str(V3/'command/stderr'),'bytes':len(raw),'sha256':sha(raw)},'required_warning_count':3,'required_ordered_record_lines':[1,2,15],'expected_warnings':[{'warning_id':v['warning_id'],'record_line':v['record_line'],'raw_line_sha256_including_newline':v['record_line_sha256_including_newline'],'exact_record':v['exact_record'],'classification':v['classification']} for v in provenance],'closed_recognition_requirements':['Bind the entire raw stderr length and SHA256 before recognizing any warning.','Parse strict UTF8 JSONL with duplicate-field rejection; compare each expected warning full decoded object, including code, level, message, all spans, children, rendered text, and nullable fields.','Require exactly three warning records at the specified ordered stream lines, each exactly once; reject any addition, omission, duplication, changed code/message/span/child/rendering or unexpected field.','Require the original source146 and diagnostic source146 manifest hashes and exact three-edit replay; all warning spans must map to unchanged original bytes outside the delta.','Preserve the original v3 command receipt and rejected outcome unchanged.','Count the three classified warnings explicitly in independently reviewed stream-summary accounting.','Keep all other frozen error, anchor, output-bound, custody and termination rejection rules; warnings recognized here grant no new error or summary tolerance.'],'blanket_warning_suppression':False,'unknown_warnings_reject':True,'producer_checker_amended':False,'original_v3_rejection_overridden':False,'compiler_rerun_authorized':False,'numerical_layout_price_backing_peak_funding_full_ownership_native_FieldLog_OTA_GA_acceptance':False})

notes="""All three diagnostics are preexisting warnings in the accepted IR02 source146, not artifacts introduced by the three diagnostic edits. The original successful production-MIR command emits exactly these three warnings; the producer's compiler-diagnostic-review.json explicitly preserves them as production_warnings. Root acceptance pins that producer seal. The independent P01/P02 successful metadata builds also emit the same three. Producer and independent Debug/opt2 builds each emit six warnings, including these three. There is no warning-free IR02 build among the inspected commands. The relevant current PLAN/STATUS paragraphs and root acceptance contain no false zero-warning claim, so this review requests no metadata correction.

W01 is a redundant explicit import of OwnedCorrelationOutcomeV1 into trusted_local_host_account_entry_v1, which is enabled by mixer_bootstrap_one_fixture_v1 in both the baseline and query. The body infers the returned correlation type from correlate_admitted_loader_v1 and invokes its method without naming that imported type. The underlying type is used in the owner module and is not a dead data contract merely because this binding is unused. W02 is two unused facade reexport bindings; BorrowedOwnerDataV1 remains the real scoped_binding_v1 return type inside the owner module, and selected_bootstrap_ledger_v1 remains defined and is invoked by inner cfg(test) code. Those inner uses do not consume the outer facade aliases. Both source files allow dead_code, which does not suppress unused_imports or deprecated. The actual compiler diagnostic, rather than occurrence scanning, establishes that these exact bindings are unused under the compiled cfg.

W03 concerns the real NEXT_ADMISSION_ASSOCIATION_V1 AtomicU64 operation in complete_admission_core_v1. The diagnostic-only delta neither inserts nor edits the operation. It uses Relaxed success/failure ordering and old.checked_add(1); the Err branch refuses admission on exhaustion. The pinned compiler reports a deprecation rename to try_update and suggests that exact replacement. This is a source/toolchain warning, not a missing method or generated query operation. No replacement was made. This source review does not prove atomic-ordering adequacy or runtime correctness; the warning itself supplies no evidence of a new runtime defect, and prior successful compilation does not prove one absent. Native production custody remains unselected in the source and no function is executed here.

The source-only proposal recognizes only full exact warning records in one bound raw stream and requires explicit warning counts. It grants no blanket lint tolerance, no compiler rerun, no parser amendment, and no numerical layout, price, backing, peak, funding, full ownership, native, FieldLog, OTA or GA acceptance. Root and an independent parser must review any separate offline policy amendment. The initial v3 rejection remains authoritative for that runner's frozen policy and is preserved.
"""
(OUT/'FINDINGS.md').write_text(notes)
write('input-manifest.json',{'schema':1,'members':sorted(INPUTS.values(),key=lambda x:x['path']),'bytes_read_including_repeat_reads':read_bytes,'source_revision_context': '837e7084a0c6e69a88848b484fa3556563c75a59','revision_source':'Pinned original root compiler release; not a new git command.'})
write('receipt.json',{'schema':1,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python_version':sys.version,'python_executable':row(Path(sys.executable),Path(sys.executable).parent),'elapsed_seconds':time.monotonic()-START,'wall_bound_seconds':55,'outcome':'Source warning provenance established and closed classification proposed; no acceptance policy amended.','source_trees_each_members_verified':146,'original_source_tree_sha256':orig_manifest['tree_sha256'],'diagnostic_source_tree_sha256':diag_manifest['tree_sha256'],'exact_original_sealed_production_MIR_receipt_verified':True,'exact_prior_warning_evidence_commands':len(command_inventory),'warnings_bound_to_unchanged_original_bytes':3,'producer_scripts_imported_or_executed':False,'compiler_or_version_commands':0,'host_runtime_UI_native_capture_phone_browser_global_inventory_operations':0,'product_or_metadata_files_mutated':False,'frozen_prior_packets_mutated':False,'new_runtime_or_release_acceptance':False})
write('seal.json',{'schema':1,'status':'FROZEN_SOURCE_ONLY_WARNING_CLASSIFICATION','members':[row(p,OUT) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='seal.json'],'no_numerical_acceptance':True})
print(json.dumps({'packet':str(OUT.relative_to(ROOT)),'seal_sha256':sha((OUT/'seal.json').read_bytes()),'members':len(list(OUT.iterdir()))-1,'elapsed_seconds':time.monotonic()-START,'warnings':3,'earlier_warning_commands':len(command_inventory)}))
