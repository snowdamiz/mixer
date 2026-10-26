#!/usr/bin/env python3
"""Freeze this bounded inventory-reconciliation output; refuse any missing/drifted input."""
from pathlib import Path
import datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def ident(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
# Expand the audited closure to every canonical Java source actually inspected and
# the frozen tool receipt. None of these reads touch active integration folders.
v=json.loads((HERE/'source-inputs.json').read_text())
for path in sorted((ROOT/'native/android/app/src/dev/mixer/android').glob('*.java')):
    v['members'][str(path.relative_to(ROOT))]=ident(path.read_bytes())
path=ROOT/'verification/android-editor-integration-protocol/support-controls/receipt.json'
v['members'][str(path.relative_to(ROOT))]=ident(path.read_bytes())
v['source_tree_sha256']=hashlib.sha256(json.dumps(v['members'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
for relative,identity in v['members'].items():
    if ident((ROOT/relative).read_bytes())!=identity:raise RuntimeError('Audited source drift '+relative)
save('source-inputs.json',v)
r=json.loads((HERE/'audit-receipt.json').read_text());r['source_tree_sha256']=v['source_tree_sha256'];r['source_map_expanded_at_freeze_to_all_inspected_canonical_java_and_tool_receipt']=True;save('audit-receipt.json',r)
save('freeze-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'source_tree_sha256':v['source_tree_sha256'],'source_members_rechecked':len(v['members']),'scope':'bounded source-inventory audit and legacy appearance compile; root amendment selection remains pending','forbidden_active_folders_read':False,'new_native_capture_UI_or_process_inventories':False,'owned_class_output_removed':not (HERE/'classes').exists(),'only_write_root':str(HERE)})
def members(exclude):
    result=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink():raise RuntimeError('Symlink output '+str(path))
        if path.is_file() and str(path.relative_to(HERE)) not in exclude:
            result.append({'path':str(path.relative_to(HERE)),**ident(path.read_bytes())})
    return result
m=members({'manifest.json','seal.json'})
save('manifest.json',{'schema':1,'scope':'complete bounded inventory-reconciliation pathset except manifest/seal','members':m,'member_count':len(m)})
m=members({'seal.json'})
save('seal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'bounded read-only Android source-pair5 inventory reconciliation and separately scoped legacy appearance host compile only','members':m,'member_count':len(m),'root_policy_selection':False,'canonical_integration':False,'native_OTA_release_or_GA_acceptance':False})
seal=json.loads((HERE/'seal.json').read_text())
actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()}
expected={x['path'] for x in seal['members']}|{'seal.json'}
if actual!=expected:raise RuntimeError('Closed output inventory drift')
for member in seal['members']:
    if ident((HERE/member['path']).read_bytes())!={k:member[k] for k in ('bytes','sha256')}:raise RuntimeError('Output drift '+member['path'])
print(json.dumps({'status':'frozen-and-complete-pathset-verified','members':len(m),'seal_sha256':ident((HERE/'seal.json').read_bytes())['sha256'],'manifest_sha256':ident((HERE/'manifest.json').read_bytes())['sha256'],'source_tree_sha256':v['source_tree_sha256'],'source_members':len(v['members'])},sort_keys=True))
