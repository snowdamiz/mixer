"""Seal owned offline evidence after design checks; no product execution."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
receipt=json.loads((P/'checks-receipt.json').read_text());assert receipt['exit_code']==0
assert 'Ran 32 tests' in (P/'checks.stderr').read_text() and (P/'checks.stderr').read_text().endswith('OK\n')
comp=json.loads((P/'closure-comparison.json').read_text())
verified=[]
for manifest in ['input-manifest.json','additional-inputs.json','acceptance-input.json']:
 for row in json.loads((P/manifest).read_text())['members']:
  b=(P/row['snapshot']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'];verified.append(row['snapshot'])
# Only exact predeclared canonical source names; not a process/file-system discovery.
source_unchanged=all(sha((R/'vm'/r['path']).read_bytes())==r['sha256'] for r in comp['canonical_members'])
assert source_unchanged
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,text=True,timeout=15,check=True).stdout.strip()
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision_context_at_freeze':revision,'source_revision_scope':'Context only; canonical and consulted bytes bound individually','canonical_132_source_bytes_still_match_frozen_inputs':True,'frozen_input_snapshots_verified':len(verified),'offline_design_controls_passed':32,'compiler_or_VM_executions':0,'native_capture_UI_or_process_inventory_operations':0,'Git_mutations':0,'product_implementation_or_contract_selection':False,'custody_or_real_binding_or_runtime_or_GA_accepted':False,'row_root_acceptance_record_bound':True,'producer_provisional_accounting_complete_totals_not_adopted':True,'cleanup':'No disposable compiler/VM/native process or scratch was created. Retained packet source/outputs are evidence; other projects processes untouched.','scope':'Completed bounded independently reviewable design proposal only; root controls selection/delivery and later implementation'}
(P/'decision.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
rows=[]
for f in sorted(P.rglob('*')):
 if f.is_file() and f.name not in ['seal.json','seal.sha256']:
  b=f.read_bytes();rows.append({'path':str(f.relative_to(P)),'bytes':len(b),'sha256':sha(b)})
tree=sha(''.join(f"{r['path']}\t{r['bytes']}\t{r['sha256']}\n"for r in rows).encode())
seal={'schema':1,'scope':'offline exact-source profile-header/closure proposal; not implementation selection or acceptance','excluded':['seal.json','seal.sha256'],'member_count':len(rows),'total_bytes':sum(r['bytes']for r in rows),'tree_sha256':tree,'tree_definition':'SHA256 of sorted relative-path TAB bytes TAB sha256 LF rows','members':rows,'implementation_accepted':False,'real_binding_or_runtime_or_GA_accepted':False}
b=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode();(P/'seal.json').write_bytes(b);(P/'seal.sha256').write_text(sha(b)+'  seal.json\n')
print(json.dumps({'member_count':len(rows),'total_bytes':seal['total_bytes'],'tree_sha256':tree,'seal_sha256':sha(b),'design_controls':32,'input_snapshots_verified':len(verified),'canonical_132_unchanged':True,'scope':result['scope']},sort_keys=True))
