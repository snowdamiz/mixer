from pathlib import Path
import hashlib,json,datetime,time,sys
D=Path(__file__).resolve().parent;R=D.parents[2]
assert not (D/'review-seal.json').exists(),'review already immutable'
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
start=time.monotonic();verified=[]
for path,sha in [(R/'verification/android-editor-preservation-membership-correction/seal.json','620bfefe8cde4b63c2101db76af991fcc1933276f9c1e8d8d1aa1e3db8f0bf0e'),(D.parent/'preaccess/seal.json','1890771da4c76e8010a196a7cd2f5c4a9ebdef2f915878367e079c1c7accd863'),(D/'findings-1/seal.json','ac298ea6ac5527da15a0746e2e8a790ef915c854efb3959e46b9f98f5d811914')]:
 assert ident(path)['sha256']==sha
 s=json.loads(path.read_text());assert len(s['members'])==s['member_count']
 for row in s['members']:assert ident(path.parent/row['path'])=={k:row[k] for k in ('bytes','sha256')}
 assert sum(m['bytes'] for m in s['members'])==s['member_bytes'];verified.append({'path':str(path.relative_to(R)),'seal_sha256':sha,'verified_members':s['member_count'],'verified_member_bytes':s['member_bytes']})
save(D/'terminal-input-custody.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only final rehash before sealing independent review','command':['python3','verification/android-editor-preservation-membership-independent/actual-review/freeze_review.py'],'python':sys.version,'elapsed_seconds':time.monotonic()-start,'inputs':verified})
summary=json.loads((D/'summary.json').read_text());assert summary['verdict']=='scoped-positive-independent-host-source-review' and summary['selected_passed_commands']==114
runs={name:json.loads((D/'runs'/name/'receipt.json').read_text())['cleanup'] for name in ('host-1','cross-1','controls-1','selected-1','selected-2')}
assert all(r['scratch_removed'] and r['children_reaped'] for r in runs.values())
save(D/'cleanup.json',{'schema':1,'scope':'Owned review child groups and scratch only; no native/global process inventory','runs':runs,'all_owned_children_bounded60s_and_reaped':True,'all_owned_scratch_removed':True,'retained_classes_dex_are_deliberate_evidence':True,'native_UI_capture_process_inventory':False})
entries=[{'path':str(p.relative_to(D)),**ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p not in (D/'manifest.json',D/'review-seal.json')]
save(D/'manifest.json',{'schema':1,'scope':'Exact immutable independent review payload; manifest separately listed in seal','member_count':len(entries),'member_bytes':sum(r['bytes'] for r in entries),'members':entries})
entries.append({'path':'manifest.json',**ident(D/'manifest.json')});entries.sort(key=lambda r:r['path'])
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':summary['verdict'],'scope':summary['scope'],'candidate_seal_sha256':summary['candidate_seal_sha256'],'product_tree':summary['product_tree'],'complete_host_tree':summary['complete_host_tree'],'preaccess_seal_sha256':summary['preaccess_seal_sha256'],'root_exact_forward_amendment_sha256':summary['root_selected_exact_forward_amendment_sha256'],'manifest':ident(D/'manifest.json'),'member_count':len(entries),'member_bytes':sum(r['bytes'] for r in entries),'members':entries,'root_acceptance_pending':True,'canonical_native_OTA_release_or_GA_accepted':False}
save(D/'review-seal.json',seal)
for row in seal['members']:assert ident(D/row['path'])=={k:row[k] for k in ('bytes','sha256')}
print(json.dumps({'seal':ident(D/'review-seal.json'),'member_count':len(entries),'member_bytes':seal['member_bytes'],'verdict':seal['verdict'],'selected_passed_commands':114,'preaccess_unchanged':True,'source':'Only NativeRenderer differs; independent product/host/SDK37/D8 exact-source verification complete'},indent=2))
