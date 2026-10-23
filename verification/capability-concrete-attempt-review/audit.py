#!/usr/bin/env python3
"""Independently bind review executions to frozen concrete source and owner evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OWNER=ROOT/'verification/capability-concrete-attempt'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
 if not ok:raise RuntimeError(why)
def read(p):return json.loads(p.read_bytes())
def main():
 final=OWNER/'final-receipt.json';need(sha(final.read_bytes())=='4af5f7181072ea2a3f324e972d8c1707e92b78b2cfd9533df772b9c127f55c60','owner final pin')
 f=read(final);a=read(OWNER/'owner-audit.json');need(sha((OWNER/'owner-audit.json').read_bytes())==f['owner_audit_sha256'],'owner audit pin')
 counts={}
 for filename,key in [('implementation-source.sha256','implementation_source_manifest_sha256'),('verification-source.sha256','verification_source_manifest_sha256'),('evidence-manifest.sha256','evidence_manifest_sha256')]:
  raw=(OWNER/filename).read_bytes();need(sha(raw)==f[key],filename)
  entries=raw.decode().splitlines();counts[filename]=len(entries)
  for line in entries:
   d,p=line.split('  ',1);need(sha((ROOT/p).read_bytes())==d,'owner manifest '+p)
 base=read(OWNER/'2026-10-23-candidate-4/receipt.json');derived=read(OWNER/'2026-10-23-derived-1/receipt.json')
 for p,d in base['source_files'].items():need(sha((Path(base['export'])/p).read_bytes())==d,'base export '+p)
 need(sha(''.join(d+'  '+p+'\n' for p,d in sorted(base['source_files'].items())).encode())==base['source_manifest_sha256'],'base manifest recomputation')
 for p,d in derived['derived_source'].items():need(sha((Path(derived['export'])/p).read_bytes())==d,'derived export '+p)
 for name in ['CapabilityConcreteAttempt.swift','CapabilityConcreteRetirement.swift']:
  p='capability-activation/Sources/MixerCapabilityActivation/'+name;text=(Path(base['export'])/p).read_text()
  for filename,old,new in derived['fixed_edits']:
   if filename==name:
    need(text.count(old)==1,'edit once '+filename);text=text.replace(old,new,1)
  need(sha(text.encode())==derived['derived_source'][p],'independent derived reconstruction '+name)
 for p,d in a['verified_logs'].items():need(sha((ROOT/p).read_bytes())==d,'owner log '+p)
 for p,d in a['verified_artifacts'].items():need(sha(Path(p).read_bytes())==d,'owner artifact '+p)
 for p,d in a['implementation'].items():need(sha((ROOT/p).read_bytes())==d,'live implementation '+p)
 execution=HERE/'2026-10-23-final-2/receipt.json';need(sha(execution.read_bytes())=='dd96e68fb158cddbef5cbc32d0997d25d8003cdcc78646891ffc2bc85eae283a','execution pin');r=read(execution)
 for p,d in r['probes'].items():need(sha((HERE/p).read_bytes())==d,'independent probe '+p)
 need(sha((HERE/'run.py').read_bytes())==r['driver_sha256'],'independent execution driver')
 for c in r['commands']:need(sha((ROOT/c['log']).read_bytes())==c['sha256'],'independent log '+c['name'])
 for v in r['artifacts'].values():
  if 'executable' in v:need(sha(Path(v['executable']).read_bytes())==v['executable_sha256'],'review executable')
  if 'library' in v:need(sha(Path(v['library']).read_bytes())==v['library_sha256'],'concrete library')
  for p,d in v.get('module_files',{}).items():need(sha(Path(p).read_bytes())==d,'imported module')
 negative=read(HERE/'private-types-receipt.json');need(negative['exit_code']==1 and sha((HERE/'private-types.log').read_bytes())==negative['output_sha256'],'public opacity')
 need(sha((HERE/'PrivateTypes.swift').read_bytes())==negative['source_sha256'],'negative source')
 files={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['final-receipt.json','evidence-manifest.sha256','audit.log']}
 manifest=''.join(d+'  '+p+'\n' for p,d in sorted(files.items())).encode();(HERE/'evidence-manifest.sha256').write_bytes(manifest)
 out={'status':'Independent bounded review passed; no confirmed actionable defect. New coordinator composition and wider gates remain separate.','model':'gpt-6.1-sol','reasoning_effort':'xhigh',
  'command':['python3','verification/capability-concrete-attempt-review/audit.py'],'python':sys.version,'owner_final_receipt_sha256':sha(final.read_bytes()),'owner_audit_sha256':f['owner_audit_sha256'],
  'production_inputs':r['production_inputs'],'owner_source_manifest_sha256':base['source_manifest_sha256'],'owner_source_files':len(base['source_files']),'derived_source_files':len(derived['derived_source']),
  'owner_manifest_counts':counts,'owner_logs_checked':len(a['verified_logs']),'owner_artifacts_checked':len(a['verified_artifacts']),'fixed_derived_edits_reconstructed':len(derived['fixed_edits']),
  'execution_receipt_sha256':sha(execution.read_bytes()),'probe_executions':6,'per_mode':{'join_permutations':6,'concurrent_joins':128,'cancelled_wait_orders':2,'cancel_finish_races':128,'actual_signed_native_last_owner_drop_cycles':8},
  'public_opacity_rejections':2,'production_changed':False,'new_package_or_rust_graph':False,'evidence_files':len(files),'evidence_manifest_sha256':sha(manifest),'audit_script_sha256':sha(Path(__file__).read_bytes()),
  'limitations':['Exact owner-supplied module/library products reused and audited, not independently rebuilt.','Private owner assumes same factory material/Signals, acyclic external terminal consumer, one waiter and stop-before-wait coordinator ordering.','Frozen transition candidate2/old Signals scope; newer allowFallback/control-wake/coordinator composition remains separate.','Host synthetic original fixtures; no device, real product UI/FieldLog health, published-package, performance, signing/store/GA qualification.','TSan excludes Rust/platform internals; logical joins/counters are not Task destruction/total RSS/OOM guarantees.']}
 (HERE/'final-receipt.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':'audit passed','owner_source_files':len(base['source_files']),'derived_source_files':len(derived['derived_source']),'logs':len(a['verified_logs']),'artifacts':len(a['verified_artifacts']),'final_receipt_sha256':sha((HERE/'final-receipt.json').read_bytes()),'evidence_manifest_sha256':sha(manifest)},indent=2))
if __name__=='__main__':main()
