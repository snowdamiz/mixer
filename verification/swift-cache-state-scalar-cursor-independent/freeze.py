#!/usr/bin/env python3
"""Seal only this review's finite output; no Git or canonical source writes."""
import datetime
import hashlib
import json
import pathlib

HERE=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
latest=json.loads((HERE/'latest-run.json').read_text())
receipt=json.loads((HERE/latest['path']/'receipt.json').read_text())
if not receipt['all_passed']:raise ValueError('latest recorded normal/-O pair must pass')
result=json.loads((HERE/'result.json').read_text())
optimized=json.loads((HERE/'result-optimized.json').read_text())
if result['independent_complete_uppers']!=optimized['independent_complete_uppers']:raise ValueError('normal/-O bound mismatch')
attempts=[]
for path in sorted((HERE/'commands').glob('*/receipt.json')):
    r=json.loads(path.read_text())
    attempts.append(dict(receipt=str(path.relative_to(HERE)),all_passed=r['all_passed'],checker_sha256=r['checker_sha256'],exits=[c['exit']for c in r['commands']]))
history=dict(schema=1,attempts=attempts,latest=latest['path'],failed_attempt_reason='Initial duplicate-victim negative fixture correctly broke on headroom before reaching duplicate; corrected by retaining another occupied pinned row. Both failures, Python warning and exact checker snapshot retained.',
             preliminary_success_superseded='Earlier successful reviewer output counts2507/699 and2508/701 variants were authoring checkpoints. Final result.json plus latest-run.json bind current source, explicit static message fields, selected niche grammar and conservative duplicate charge wording.',
             source_and_producer_packets_unchanged=True)
(HERE/'authoring-attempts.json').write_text(json.dumps(history,indent=2,sort_keys=True)+'\n')
final=dict(schema=1,decision='Accept scoped exact-source universal merge/prefix argument, conservative complete source-work uppers and logical role union for root selection only',
           source_sha256=result['source_sha256'],producer_seal_sha256=result['producer_seal_sha256'],bounds=result['independent_complete_uppers'],whole_added_peaks=result['whole_added_peaks'],whole_role_union=29344,
           inherited_G2=2494,inherited_G6_production=512,inherited_G6_private=514,combined_production_G1_to_G7=result['combined_production_G1_to_G7'],
           all_numeric_caps_unchanged=True,exact_once_charge_partition=True,exact_once_actual_source_event_claim=False,selected_niche_grammar_preserved=True,
           extra21_niche_payload_charges='Optional conservative duplicates tied to existing actual scalar pointer-transfer labels; not newly missing required copies.',
           producer_exact_totals_selected=False,final_command_receipt=latest['path']+'/receipt.json',checks=result['checks'],finite=result['finite'],negative_controls=result['negative_controls'],
           independent_review_complete=True,root_selection_required=True,implementation_selected=False,
           remaining=['Root independent selection','Actual Rust/compiler/implementation checks','New public File admission and reachability','Physical phones/native simulator/emulator/UI and capture remain paused','Signing/store/customer/operations','Separate-repository immutable published-package FieldLog dogfood','GA gates and accountable reviewer evidence'],
           no_compiler_runtime_native_capture_process_inventory_Git_or_hosted_actions=True,
           cleanup='All bounded sequential reviewer Python children reaped; no native/capture processes or external scratch started. Other projects untouched.')
(HERE/'final-decision.json').write_text(json.dumps(final,indent=2,sort_keys=True)+'\n')
members=[]
for path in sorted(HERE.rglob('*')):
    if path.is_file()and path.name!='seal.json':
        raw=path.read_bytes();members.append(dict(path=str(path.relative_to(HERE)),bytes=len(raw),sha256=sha(raw)))
seal=dict(schema=1,member_base='packet-relative',source_sha256=result['source_sha256'],members=members,total_bytes=sum(m['bytes']for m in members),independent_review_complete=True,root_selection_required=True,implementation_selected=False)
(HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(members),bytes=seal['total_bytes'],bounds=final['bounds'],whole_added_peaks=final['whole_added_peaks']),sort_keys=True))
