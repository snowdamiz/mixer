"""Root data-only custody of the frozen independent review; no product execution."""
import datetime, hashlib, json, pathlib, platform, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
REVIEW=ROOT/'verification/android-editor-focus-history-independent/actual-review'
OUT=pathlib.Path(__file__).with_name('focus-history-full-review-custody.json')
assert not OUT.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
seal=REVIEW/'review-seal.json'
assert sha(seal)=='69e1f6a02702e5a4181cbb6ff76263301d499e8853115c7059bb39e0c393dcb8'
s=json.loads(seal.read_text()); seen=set(); total=0
for m in s['members']:
 p=pathlib.PurePosixPath(m['path']); assert str(p)==m['path'] and not p.is_absolute() and '..' not in p.parts and str(p) not in seen
 seen.add(str(p)); f=REVIEW/p; assert f.is_file() and not f.is_symlink() and f.stat().st_size==m['bytes'] and sha(f)==m['sha256'],str(p)
 total+=m['bytes']
assert len(seen)==s['member_count']==1151 and total==s['member_bytes']==10030967
receipt=json.loads((REVIEW/'audit-receipt.json').read_text())
assert receipt['verdict']=='changes-required' and receipt['independent_acceptance'] is False
assert len(receipt['findings'])==2 and receipt['independent']['new_required_controls_failed']==2
assert receipt['cleanup']['all_owned_children_reaped'] and receipt['cleanup']['all_scratch_and_empty_source_removed']
commands=[]
for path in sorted(REVIEW.rglob('receipt.json')):
 if path.relative_to(REVIEW).parts[0] not in ('controls-1','controls-2','controls-3','frozen'):continue
 data=json.loads(path.read_text())
 entries=data.get('commands',[])
 if not isinstance(entries,list):continue
 for c in entries:
  if not isinstance(c,dict):continue
  assert c.get('reaped',True),str(path)
  if 'timeout_seconds' in c: assert c['timeout_seconds']<=60
  commands.append({'receipt':str(path.relative_to(REVIEW)),'name':c.get('name'),'exit_code':c.get('exit_code'),'reaped':c.get('reaped'),'timeout_seconds':c.get('timeout_seconds')})
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':['python3',str(pathlib.Path(__file__).relative_to(ROOT))],'tool_version':sys.version,'platform':platform.platform(),'verifier_sha256':sha(pathlib.Path(__file__)),'source_revision_context_only':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'seal':str(seal.relative_to(ROOT)),'seal_sha256':sha(seal),'members_verified':len(seen),'bytes_verified':total,'audit_receipt_sha256':sha(REVIEW/'audit-receipt.json'),'review_sha256':sha(REVIEW/'review.md'),'verdict':'changes-required','findings':receipt['findings'],'independent_prepared_groups':12,'independent_prepared_assertions':838,'additional_groups':2,'additional_assertions':25,'new_required_controls_failed':2,'command_receipt_observations':commands,'cleanup_reported':receipt['cleanup'],'implementation_accepted':False,'canonical_native_or_GA_accepted':False,'scope':'Root rehash and data review of complete independent host/SDK audit; no rerun, no native execution or implementation acceptance'}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'members':len(seen),'bytes':total,'custody':str(OUT.relative_to(ROOT)),'sha256':sha(OUT),'verdict':result['verdict']}))
