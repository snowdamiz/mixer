#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,sys
D=Path(__file__).resolve().parent
P=D.parent
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def check(directory,name,expected):
    path=directory/name;assert row(path)['sha256']==expected;data=json.loads(path.read_text())
    for item in data['members']:
        target=directory/item['path'];assert not target.is_symlink();assert row(target)=={key:item[key] for key in ['bytes','sha256']}
    return {'seal':row(path),'members':len(data['members']),'bytes':sum(item['bytes'] for item in data['members'])}
assert not (D/'review-seal.json').exists()
protected={'preaccess':check(P,'preaccess-seal.json','169a0f581e0871e1ac273b88f653dc4d87381628fb8a39b8b2ec4bf7c80dbc62'),'findings':check(D/'findings-1','seal.json','a0cf5e8bff8ffee66f277b5e83c76b2778db13bd8eac558ae3ef65cdc007f5fd')}
runs={}
for name in ['host-1','cross-1']:
    path=D/'frozen/runs'/name/'receipt.json';receipt=json.loads(path.read_text());assert receipt['status']=='passed-'+name.split('-')[0]+'-only' and receipt['cleanup']['scratch_removed'] and receipt['cleanup']['children_reaped'];runs[name]=row(path)
assert not list((D/'frozen/runs').glob('*/owned-focus-history-*'))
controls={}
for name in ['controls-1','controls-2','controls-extra']:
    path=D/name/'receipt.json';receipt=json.loads(path.read_text());assert receipt['cleanup']['children_reaped'] and receipt['cleanup']['empty_source_removed'];controls[name]={'receipt':row(path),'commands':receipt['commands']}
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'verdict':'changes-required','independent_acceptance':False,'producer_seal_sha256':'2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8','root_custody_sha256':'89bf40f503c2302e957e2a64426323a978cd3a3514768a4c2e456231004f56ea','product_tree':'2d0a89dac0c629b7257a75dfa42dee3794f021c558300f968fc4d8baaaecba01','full_host_tree':'eb1ab63db285fb74cc45be5c415a4d56b65ae4a8e04da9ed3c4f807e97c3fe07','source_revision_context_only':'30f94a634da66279e28dba3fd9a0116accb705af','protected':protected,'source_verification':row(D/'source-verification.json'),'full_replay':{'receipts':runs,'producer52_assertions':722,'earlier_prepared_groups':6,'hostile3_assertions':51,'earlier_real_witness_positive2_assertions':15,'descriptor_closure':38,'producer_focus_groups':13,'producer_focus_assertions':598,'SDK37_D8':'passed_unsigned_only'},'independent':{'prepared_groups_passed_across_preserved_attempts':12,'prepared_assertions':838,'extra_groups_passed':2,'extra_assertions':25,'new_required_controls_failed':2,'first_preaccess_exhaustion_assumption_failure_preserved':True,'control_receipts':controls},'findings':[{'id':'FH-C01','priority':'P1','route':'ordinary known engine rejection status1','observed':'original current/snapshot unchanged; abort RETURNED; rollback FAILED_UNCERTAIN because same scope ended at successful attach return; old Binding unrestored','required':'eligible rollback under same captured original candidate/journal authority'},{'id':'FH-C02','priority':'P1 internal invariant','route':'wrong renderer Input.fieldPreservationEnd with actual foreign ended-countHeld scope','observed':'local count2→1; foreign counted true→false; foreign native count stays1','required':'scalar exact original receiver/renderer/Record/Input/fence/scope ownership before counted mutation'}],'coverage_distinction':'Producer multiple-preservations uses two blurred fields/no active target lease; additional independent test proves two inactive A/C scopes plus B existing EditorLease count3→B count1→0.','cleanup':{'all_owned_children_reaped':True,'all_scratch_and_empty_source_removed':True,'native_UI_capture_or_process_inventory':False,'other_projects_touched':False},'writes_only_actual_review':True,'canonical_or_Git_actions':False,'active_other_lane_reads':False,'native_or_GA_accepted':False,'pending':['Separate root-selected preservation-completion protocol/derivative and frozen actual-source review','Canonical integration/source profile/export guards after acceptance','Native IME/EditorInfo/batch/selection/composition/lifecycle/hidden suffix/accessibility/TalkBack/OEM after resumption','Physical phones/API28-35/FieldLog/store/signing/OTA/operations/GA']}
(D/'audit-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
members=[]
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():members.append({'path':str(path.relative_to(D)),**row(path)})
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent full actual-source focus-history review/replay; two required correction findings; no acceptance/integration/native execution','verdict':'changes-required','members':members,'member_count':len(members),'member_bytes':sum(item['bytes'] for item in members)}
encoded=(json.dumps(seal,indent=2)+'\n').encode();(D/'review-seal.json').write_bytes(encoded);print(json.dumps({'seal':str(D/'review-seal.json'),'sha256':hashlib.sha256(encoded).hexdigest(),'members':len(members),'bytes':seal['member_bytes'],'verdict':'changes-required'}))
