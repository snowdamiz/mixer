#!/usr/bin/env python3
"""Freeze the current independent preaccess membership before candidate release."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def emit(n,d):(OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 assert not (OUT/'preaccess-seal.json').exists(),'Do not replace a frozen preaccess seal'
 start=time.monotonic();argv=[sys.executable,str(OUT/'check_preaccess.py')]
 result=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
 (OUT/'preaccess-check.stdout').write_bytes(result.stdout);(OUT/'preaccess-check.stderr').write_bytes(result.stderr)
 emit('preaccess-check-receipt.json',{'schema':1,'argv':argv,'cwd':str(ROOT),'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':30,'python':sys.version,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'checker_sha256':sha((OUT/'check_preaccess.py').read_bytes()),'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr),'candidate_source_read':False})
 assert result.returncode==0
 emit('preaccess-decision.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'Independent PREACCESS packet ready and frozen; await explicit root frozen candidate release','new_concrete_contract_blockers':[],'candidate_read_or_accepted':False,'candidate_review_controls_pending':29,'old_source_only_actual_controls_per_mode':8,'modes':['Debug','optimized'],'source_manifest':'old-probe-source-manifest.json','fixed_expectations':'fixtures/expected.json','predeclared_compile_sources_unrun':10,'source_place_lifetime_work_IO_cleanup_acceptance_pending':True,'selected_configuration_actual_measurements_pending':True,'earlier_failures_retained':['old-controls-attempt-1.json','old-commands/attempt-1-debug-build/stderr','old-commands/attempt-1-release-build/stderr','retained-runner-attempt-1.py','evidence-inventory-attempt1-tool-transcript.json'],'cleanup':'All owned commands reaped and owned compiler/TMP/Cargo scratch removed in both attempts; no native/UI/capture/process inventory started; retained inputs/source/logs/output are intentional evidence','canonical_runtime_CI_FieldLog_GA_accepted':False})
 excluded=['preaccess-seal.json','preaccess-seal.sha256']
 members=[]
 for p in sorted(OUT.rglob('*')):
  if p.is_file() and str(p.relative_to(OUT)) not in excluded:
   b=p.read_bytes();members.append({'path':str(p.relative_to(OUT)),'bytes':len(b),'sha256':sha(b)})
 emit('preaccess-seal.json',{'schema':1,'scope':'Exact independent PREACCESS membership; no candidate access or acceptance','member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),'members':members,'excluded':excluded})
 digest=sha((OUT/'preaccess-seal.json').read_bytes());(OUT/'preaccess-seal.sha256').write_text(digest+'  preaccess-seal.json\n')
 print(f'PREACCESS frozen {len(members)} members, {sum(m["bytes"] for m in members)} bytes, seal SHA256 {digest}; candidate unread; waiting for explicit root release.')
if __name__=='__main__':main()
