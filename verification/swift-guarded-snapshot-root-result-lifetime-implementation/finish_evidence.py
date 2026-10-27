#!/usr/bin/env python3
"""Review bounded outputs, retain complete MIR and clean only generated owned artifacts."""
from pathlib import Path
import datetime,gzip,hashlib,json,re,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def row(path,base=P):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def rows(base):return [row(path,base) for path in sorted(base.rglob('*')) if path.is_file()]
def write(name,value):
    with (P/name).open('x') as output:json.dump(value,output,indent=2,sort_keys=True);output.write('\n')
source=json.loads((P/'source-manifest.json').read_text());host=json.loads((P/'host-manifest.json').read_text())
assert rows(P/'source/vm')==source['members'] and rows(P/'source/host')==host['members']
roster=json.loads((P/'proposed-command-roster-v2.json').read_text());commands=[]
for command in roster['commands']:
    d=P/'commands-v2'/command['id'];receipt=json.loads((d/'receipt.json').read_text());plan=json.loads((d/'plan.json').read_text())
    assert receipt['success'] and not receipt['failure_classifications'] and receipt['seconds']<55
    assert receipt['child_reaped'] and receipt['exact_owned_group_absent'] and receipt['postrun_source_and_tool_pins_verified']
    assert plan['argv']==command['argv']
    commands.append({'id':command['id'],'kind':command['kind'],'receipt':row(d/'receipt.json'),'plan':row(d/'plan.json'),'exit':receipt['exit'],'seconds':receipt['seconds'],
      'owned_pid':receipt['owned_pid'],'owned_pgid':receipt['owned_pgid'],'child_reaped':True,'owned_group_absent':True,'stdout':row(d/'stdout'),'stderr':row(d/'stderr')})
assert len(commands)==24 and len(list((P/'commands-v2').iterdir()))==24
write('command-summary.json',{'schema':1,'commands':commands,'compiler':21,'host':2,'version':1,'retries':0,'max_seconds':max(c['seconds'] for c in commands),'sum_command_seconds':sum(c['seconds'] for c in commands),'one_compiler_sequential':True})
reviews={
 'N01':'E0597 is at the actual local original-root reference passed to the genuine facade helper. The helper returns after acquisition-owner retirement.',
 'N02':'E0505 is explicit movement of the same borrowed root before later use of the whole result.',
 'N03':'E0597 is the local original root for a carrier chosen from two complete optional shapes. This is universal type coverage, not File Some/None execution.',
 'N04':'E0597 follows the original attempt root through the helper accepting an independent foreign owner. It is not a foreign-root lifetime rejection.',
 'N05':'E0597 follows actual facade live/association refusal helpers in the owner module. Positive helper fields/types are otherwise checked with no extra errors.',
 'N06':'E0597 follows final result original root; shared original io view helper is accepted. Original io pointee identity is separately host guard evidence.',
 'N07':'E0597 follows final result original root; shared typed original validation view helper is accepted. No string coercion is used.',
 'N08':'E0425 names removed facade CorrelatedSelectedProfileV1 reexport and notes its private inaccessible definition.',
 'N09':'E0532 rejects destructuring the opaque correlation tuple field because the field/constructor is private.',
 'N10':'E0599 rejects bare into_selected_v1 on the facade result. The only complete fixed consuming operation remains available.',
 'N11':'E0597 holds for the complete fixed leaf result with an Ok observation. Actual VM/File Ok arm is not executed.',
 'N12':'E0597 holds for the complete fixed leaf result with an Err observation. Actual VM/File Err arm is not executed.',
 'N13':'E0597 binds child payload to local original root while child account is an independent input. The genuine child helper retires acquisition owner before return.',
 'N14':'E0597 binds the actual cache final family including observed SetupRefused; no native File prefix is executed.',
 'N15':'E0505 rejects destruction/movement of the original carrier before its shared typed diagnostic view is used.',
 'N16':'E0603 identifies the actual production generic core as private to owner module.',
 'N17':'E0599 rejects the requested consuming map/caller-slot closure. Iterator candidate diagnostics do not grant an API or payload projection.',
 'N18':'Two E0277 diagnostics concern the same DerefMut boundary and its Deref supertrait; neither trait exists. Other projection exclusions are source-review obligations.',
}
negative=[]
for probe in json.loads((P/'probe-roster.json').read_text())['probes']:
    id=probe['id'];d=P/'commands-v2'/id;receipt=json.loads((d/'receipt.json').read_text());stderr=(d/'stderr').read_text()
    assert receipt['exit']!=0 and receipt['diagnostic']['intended_diagnostics_found'] and not receipt['diagnostic']['unexpected_error_codes']
    assert not receipt['diagnostic']['negative_rmeta_created']
    negative.append({'id':id,'fragment':row(P/probe['fragment']),'stderr':row(d/'stderr'),'error_codes':receipt['diagnostic']['error_codes'],
      'semantic_review':reviews[id],'paired_positive':probe['paired_control'],'limit':probe['limitation'],'status':'intended-boundary-observed-producer-review'})
write('compiler-diagnostic-review.json',{'schema':1,'negative_probes':negative,'all_intended':True,'no_syntax_missing_cfg_missing_lifetime_or_startup_error_counted':True,
 'positive_controls':'Normal Debug/opt2 builds compile actual File facade owner-before-result and child-before-owner return helpers; production metadata compiles all real methods. Expected-failing fragments also contain paired controls with no extra diagnostic codes.',
 'production_warnings':(P/'commands-v2/production-MIR/stderr').read_text(),'acceptance':'Producer review only; independent/root acceptance Pending. No native File or actual VM fixture execution.'})
host_results=[]
for mode in ['debug','opt2']:
    d=P/'commands-v2'/('run-'+mode);stdout=(d/'stdout').read_text();names=re.findall(r'^test (.*?) \.\.\. ok$',stdout,re.M)
    assert len(names)==38 and '38 passed; 0 failed' in stdout and '470 filtered out' in stdout
    host_results.append({'mode':mode,'passed':38,'failed':0,'filtered':470,'test_names':names,'stdout':row(d/'stdout'),'stderr':row(d/'stderr'),
      'scope':'Actual production generic guard/acquisition/correlation/validator/retirement and unchanged child-account guard tests; selector remains Pending. File facade helper functions compile but are not invoked.'})
write('host-review.json',{'schema':1,'runs':host_results,'original_guard_mutation_vectors_executed':46,
 'historical_460_vector_mapping':'Preserved predecessor evidence/source; not claimed as 460 executions in these filtered runs.',
 'new_cases':['H23 foreign expected root ends before original-root-bound refusal','H24 exact original Guard destruction unwind retains full acquisition charge'],
 'not_executed':['native File setup partial prefixes','actual File correlation family','actual VM fixed leaf Ok/Err/adoption panic','end-to-end complete File child retirement'],'no_native_or_UI_processes':True})
# Retain exact compiler text before removing only generated files.
mir_path=P/'build/actual.mir';raw=mir_path.read_bytes();mir_original=row(mir_path)
mir_dir=P/'mir';mir_dir.mkdir(exist_ok=False)
archive=mir_dir/'complete-production.mir.gz'
with archive.open('xb') as output:
    with gzip.GzipFile(fileobj=output,mode='wb',filename='',mtime=0,compresslevel=6) as zipped:zipped.write(raw)
assert gzip.decompress(archive.read_bytes())==raw
# Every byte is covered by the preamble plus contiguous top-level item spans.
starts=list(re.finditer(rb'(?m)^(?:fn|const|static) ',raw));assert starts
inventory=[];relevant=[];new_types=[b'RootBoundV1',b'RawSelectedBundleV1',b'CorrelatedSelectedProfileV1',b'RootBoundSelectedProfileV1',b'RawCorrelationOutcomeV1',b'OwnedCorrelationOutcomeV1',b'FixtureLeafArgumentsV1',b'RawFixturePrimaryV1',b'RawFixtureResultV1',b'RootBoundFixtureOutcomeV1',b'RootBoundPrimaryBorrowV1',b'AdmittedFixtureOutcomeV1',b'AdmittedFixturePayloadV1']
for index,match in enumerate(starts):
    start=match.start();end=starts[index+1].start() if index+1<len(starts) else len(raw);chunk=raw[start:end]
    line_start=raw.count(b'\n',0,start)+1
    header=chunk.split(b'\n',1)[0].decode();item={'index':index,'kind':header.split(' ',1)[0],'header':header,
      'byte_start':start,'byte_end_exclusive':end,'line_start':line_start,'lines':chunk.count(b'\n'),'bytes':len(chunk),'sha256':sha(chunk)}
    inventory.append(item)
    if any(t in chunk for t in new_types):
        text=chunk.decode();local=[];transfers=[]
        for offset,line in enumerate(text.splitlines()):
            if re.match(r'\s*let(?: mut)? _\d+:',line) and any(term in line for term in ['RootBound','RawFixture','RawSelected','RawCorrelation','AdmittedFixture','BootstrapLedger','SelectedValidated','SnapshotScope','SnapshotRun','RuntimeControl','AdoptedProof','File','Cancellation','UnverifiedProfileDigest']):
                local.append({'mir_line':line_start+offset,'text':line})
            if re.search(r'\bmove |\bcopy |\bdrop\(|\breturn;|\bunwind\b|_0 =',line):transfers.append({'mir_line':line_start+offset,'text':line})
        relevant.append({'item':item,'new_type_terms':[t.decode() for t in new_types if t in chunk],'local_and_return_places':local,'moves_copies_calls_returns_drops_and_unwind':transfers})
write('complete-mir-item-inventory.json',{'schema':1,'compiler_command':'production-MIR','complete_mir':mir_original,'archive':row(archive),'preamble_bytes':starts[0].start(),
 'item_count':len(inventory),'function_count':sum(i['kind']=='fn' for i in inventory),'items':inventory,'coverage':'Preamble plus contiguous byte ranges cover complete emitted production MIR. Format-sensitive inventory assists review; archive is authoritative.'})
write('mir-function-inventory.json',{'schema':1,'complete_mir':mir_original,'archive':row(archive),'items_containing_new_types':relevant,
 'scope':'Complete production MIR includes generic methods and all caller-visible production transitions. Test build bodies and actual native/VM execution are not additional MIR or runtime receipts.',
 'layouts_prices_funding_review':'Pending. No sizes/floors/quotes approved by this inventory.'})
write('mir-review.json',{'schema':1,'complete_mir':mir_original,'archive':row(archive),'archive_decompressed_hash_verified':True,
 'producer_review':['correlate_core returns RootBound on all three branches from attempt original reference',
 'into_result preserves bound complete payload and same root in both branches',
 'opaque File facade reassembles complete original selected/error/files/usage in bound families',
 'fixed fixture frame contains original-root local, bound selected transition, raw scope/run temporaries, calls and both typed result arms; return contains all resources and root',
 'cache setup uses original_root before setup; both setup-refusal and loaded output assignments contain root',
 'child closure and outer observation/destruction retain separate child/account and original-root payload types'],
 'source_inventory':row(P/'private-transition-inventory.json'),'independent_private_place_funding_review':'Pending','new_layouts_and_prices_accepted':False})
# Only exact named generated outputs from this lane may be removed.
allowed={'actual.mir','actual.rmeta','tests-debug','tests-opt2'}
assert {p.name for p in (P/'build').iterdir()}==allowed
removed=[]
for name in sorted(allowed):
    path=P/'build'/name;identity=row(path)
    assert path.parent==P/'build' and path.is_file() and not path.is_symlink()
    removed.append({**identity,'kind':'MIR text retained in verified complete archive' if name=='actual.mir' else 'generated compiler metadata or test binary',
      'reason':'Terminal selected use complete; exact hash retained before removal'})
    path.unlink()
write('artifact-cleanup.json',{'schema':1,'removed':removed,'build_directory_empty':not list((P/'build').iterdir()),'retained_complete_MIR':row(archive),
 'total_bytes_removed':sum(item['bytes'] for item in removed),'source_or_evidence_removed':False,'other_projects_or_processes_touched':False})
write('cleanup.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':24,'all_exact_owned_children_reaped':True,'all_exact_owned_groups_absent_at_each_terminal_receipt':True,
 'compiler_host_native_capture_simulator_processes_started_after_roster':False,'native_processes_started_by_this_lane':False,'generated_binaries_metadata_removed':True,'complete_MIR_retained':True,'global_inventory':False})
assert rows(P/'source/vm')==source['members'] and rows(P/'source/host')==host['members']
write('result.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'bounded-producer-evidence-frozen-awaiting-independent-review',
 'source146_tree':source['tree_sha256'],'host11_tree':host['tree_sha256'],'changed':source['changed'],'new_distribution_members':0,'source_copy_count':1,
 'version':json.loads((P/'toolchain.json').read_text()),'compiler_commands':21,'negative_intended_boundaries':18,'host_runs':2,'host_passed_each':38,'host_failed':0,'retries':0,
 'source_or_probe_edits_after_release':False,'all_own_groups_absent_at_command_return':True,'binary_metadata_cleanup':True,'complete_production_MIR_retained':True,
 'scope':'Accessible-result original-root lifetime candidate; production File facade compiles, actual generic guard/core executes. No native File acquisition or VM fixture/runtime.',
 'no_full_ownership_accepted':True,'Pending':['independent/root accessible-result acceptance','native File setup partial-prefix and fixed VM leaf Ok/Err/full child runtime','forgotten-result/root durable funding and shutdown','new source/MIR/layout prices','useful joint acquisition retirement','full ownership','native selectors/startup/allocator/custody/healthy close','FieldLog','OTA','GA'],
 'native_UI_capture_runtime':'Paused/Pending','original_IR01_IR02_failures_and_corrected_witnesses':'Preserved in original frozen packets; not rewritten or erased.'})
print(json.dumps({'commands':24,'host_passed_each':38,'intended_negative_boundaries':18,'complete_MIR_bytes':len(raw),'MIR_items':len(inventory),'new_type_MIR_items':len(relevant),'archive':row(archive),'generated_removed_bytes':sum(item['bytes'] for item in removed)}))
