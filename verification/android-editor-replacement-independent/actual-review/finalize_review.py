#!/usr/bin/env python3
"""Freeze this review only, preserving all prior producer and preaccess evidence."""
from pathlib import Path
import datetime, hashlib, json, sys
D=Path(__file__).resolve().parent
P=D.parent
def metadata(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def exact(directory,seal_name):
    seal=json.loads((directory/seal_name).read_text())
    for member in seal['members']:
        path=directory/member['path'];assert not path.is_symlink()
        assert metadata(path)=={key:member[key] for key in ['bytes','sha256']},str(path)
    return {'seal':metadata(directory/seal_name),'members':len(seal['members']),'bytes':sum(member['bytes'] for member in seal['members'])}
assert not (P/'review-seal.json').exists()
protected={'preaccess':exact(P,'preaccess-seal.json'),'prior_audit':exact(P.parent/'android-editor-implementation-independent','audit-seal.json'),'producer':exact(P.parent/'android-editor-replacement-implementation','seal.json'),'minimal_findings':exact(D/'findings-focus-history','seal.json')}
tools={}
declared=json.loads((D/'frozen/tool-dependencies.json').read_text())['tools']
for name,expected in declared.items():
    actual=metadata(Path(name));assert actual==expected,name;tools[name]=actual
for run in ['host-1','cross-1']:
    receipt=json.loads((D/'frozen/runs'/run/'receipt.json').read_text());assert receipt['cleanup']['scratch_removed'] and receipt['cleanup']['children_reaped']
assert not list((D/'frozen/runs').glob('*/editor-implementation-*'))
independent=[]
for folder in sorted(D.glob('independent-controls*')):
    if not folder.is_dir():continue
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['children_reaped']
    assert not (folder/'empty-source').exists()
    independent.append({'path':str(folder.relative_to(D)),'commands':receipt['commands'],'receipt':metadata(folder/'receipt.json')})
focus=P.parent/'android-editor-boundary-root-review/focus-history-amendment.md'
assert metadata(focus)['sha256']=='736476a269fae9a6745fbfbd5413a7ef231f57f9254c3279e41c2921d2088833'
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'verdict':'changes-required','independent_acceptance':False,'canonical_integration_accepted':False,'producer_seal_sha256':'4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3','product_tree_digest':'c1f5367c3fbab040e1a0130304262b3d2850c3d235cc83ab54aae5e3c6b1b7c1','host_closure_digest':'ebbe167f0e5f45d9b646474e4d4185af48c016e4475f53f0de31a75139793988','source_revision_context_only':'db6332d4c27efec4f9e22b9adc43000d48c591a1','protected_verified_unchanged':protected,'source_verification':metadata(D/'source-verification.json'),'tools_current_hashes_match_frozen_declared_tool_closure':tools,'complete_source_replay':{'host':'52 groups / 722 assertions passed','sdk':'SDK37 javac and D8 min-api28 passed; unsigned only','host_receipt':metadata(D/'frozen/runs/host-1/receipt.json'),'cross_receipt':metadata(D/'frozen/runs/cross-1/receipt.json')},'independent_groups':{'prepared_actual_source':6,'reflected_actual_source':3,'reflected_assertions':51,'descriptor_closure':38,'required_focus_history_groups_failed':2,'single_field_focus_history':'observation, not compatibility pass'},'failures':[{'id':'FH01','priority':'P1','control':'blurred-A-replacement','required':'ordinary accessibility success after completed old close','observed':'false/no event/Eold unchanged/B remains healthy','source':'NativeAppearanceViewsV2.java:957'},{'id':'FH02','priority':'P1','control':'focused-B-echo-after-A-blur','required':'ordinary B IME compatible echo preserves settled blurred A','observed':'native B becomes otherz; false/owner terminal before feature prepare','source':'NativeAppearanceViewsV2.java:963; NativeRenderer.java:102'}],'independent_attempts':independent,'prospective_root_amendment_reviewed_no_concrete_contradiction':metadata(focus),'cleanup':{'all_owned_children_reaped':True,'all_owned_scratch_removed':True,'native_ui_capture_started_or_queried':False,'process_inventory':False,'other_projects_touched':False},'writes_limited_to_owned_review_area':True,'canonical_or_git_actions':False,'native_or_GA_acceptance':False,'pending':['Separate root-selected focus-history source derivative, frozen release and full independent actual-source audit','Root canonical integration and source profile/export guard selection','Native IME/EditorInfo/selection/composition/batch/lifecycle/visibility/hidden suffix/accessibility/TalkBack/OEM qualification after resumption','Physical phones/API28-35/immutable separate-repository FieldLog/store/signing/OTA/operations/GA']}
(D/'audit-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
members=[]
for path in sorted(P.rglob('*')):
    assert not path.is_symlink(),str(path)
    if path.is_file():members.append({'path':str(path.relative_to(P)),**metadata(path)})
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent complete-source frozen replacement review; two real compatibility failures; no acceptance/integration/native execution','verdict':'changes-required','members':members,'member_count':len(members),'member_bytes':sum(member['bytes'] for member in members)}
encoded=(json.dumps(seal,indent=2)+'\n').encode();(P/'review-seal.json').write_bytes(encoded)
print(json.dumps({'seal':str(P/'review-seal.json'),'sha256':hashlib.sha256(encoded).hexdigest(),'members':len(members),'bytes':seal['member_bytes'],'verdict':'changes-required'}))
