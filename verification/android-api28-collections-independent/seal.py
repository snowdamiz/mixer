#!/usr/bin/env python3
"""Seal only this independent review and its new report; no canonical mutation."""
from pathlib import Path
import datetime, hashlib, json, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REPORT=ROOT/'docs/android-api28-collections-independent.md'
def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
receipt=json.loads((HERE/'receipt.json').read_text())
assert receipt['status']=='passed-independent-finite-host-and-binary-review'
assert receipt['checks_count']==851
cleanup=json.loads((HERE/'cleanup.json').read_text())
assert cleanup['owned_scratch_removed'] and cleanup['all_recorded_children_reaped']
assert not list(HERE.rglob('__pycache__'))
final={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,
       'status':'sealed-independent-review-ready-for-root-selection',
       'recommendation':'Accept only the exact Java20 emitted Java-library API floor and existing private read-only consumer evidence; no product factory replacement is required by this artifact.',
       'scope_accepts':['exact 170-member/60-type Java-library API floor at or below API28','exact pinned source20/profile4/compiler flags','existing private read-only collection consumers'],
       'scope_excludes':['universal Java17 factory/no-op-mutator exception equivalence','Android verifier/class-loading/library runtime','public V2 or new rendering contexts','changed source/compiler/flags or future consumers','Swift/JNI/APK/signing/store/operations/GA qualification'],
       'checks':851,'fresh_negative_controls':7,'fresh_pure_source_host_assertions':57,'separate_JDK_empty_mutator_mismatch_assertions':8,
       'producer_prototype_or_controls_counted_as_fresh':False,'fresh_exact_consumer_D8_byte_match':True,
       'all_current_Java20_stable_before_and_after':True,'all23_profile4_snapshot_members_bound':True,
       'Java_member_ids':170,'Java_component_classes':60,'all_binary_code_bodies':2307,'all_lowering_edges':57,'all_empty_edges':15,
       'additional_consumer_detail':'Group.records has three writes: constructor placeholder, installChildren replacement, restoreV2 rollback replacement. None mutates the empty map through the field.',
       'retained_failed_expanded_review_attempts':[p.name for p in sorted(HERE.glob('failure-*.json'))],
       'producer_manifest':identity(ROOT/'verification/android-api28-collections-prerequisite/manifest.json'),
       'profile4_manifest':identity(ROOT/'verification/android-environment-platform-profile4/manifest.json'),
       'owned_children_reaped':len(cleanup['commands']),'owned_scratch_removed':True,'no_native_UI_capture_or_process_inventory':True,
       'no_product_profile_rootmetadata_Git_or_dependency_mutation':True,
       'pending':['root exact scope selection','API28 native verifier/class-loading/library execution','older rendering/accessibility/editor/insets/accessibilityValue semantics','public V2','TalkBack/design parity/final phones','immutable separately published FieldLog packages','OTA/signing/store/operations/accountable GA']}
(HERE/'final-receipt.json').write_text(json.dumps(final,indent=2,sort_keys=True)+'\n')
files=sorted(p for p in HERE.rglob('*') if p.is_file() and p.name!='manifest.json')+[REPORT]
members={str(p.relative_to(ROOT)):identity(p) for p in sorted(files)}
manifest={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,
          'scope':'Independent exact frozen Android Java-library source/compiler review; no native/runtime or product selection',
          'members':len(members),'bytes':sum(r['bytes'] for r in members.values()),'files':members,
          'native_runtime_qualified':False,'universal_factory_exception_equivalence':False,'new_profile_or_product_implementation_selected':False}
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'manifest':str((HERE/'manifest.json').relative_to(ROOT)),**identity(HERE/'manifest.json'),'members':len(members),'member_bytes':manifest['bytes']}))
