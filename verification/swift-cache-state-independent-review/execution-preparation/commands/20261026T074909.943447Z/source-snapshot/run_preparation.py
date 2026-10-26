"""Serial bounded reviewer preparation with retained evidence and owned cleanup."""
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import shutil
import sys
from harness import HERE,ROOT,bounded,sha,write_json

def main():
 name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
 attempt=HERE/'commands'/name; attempt.mkdir(parents=True)
 scratch=HERE/'owned-work'/name; scratch.mkdir(parents=True)
 results=[]; compiled=[]; status='preparation-failed'
 try:
  r=bounded([sys.executable,'-B',str(HERE/'prepare_support.py')],ROOT,attempt,'prepare-support')
  results.append(r)
  if r['exit_code']!=0: raise ValueError('support preparation failed')
  sources=[]
  for p in sorted(HERE.rglob('*')):
   rel=p.relative_to(HERE)
   if p.is_file() and p.suffix in ('.py','.rs') and rel.parts[0] not in ('inputs','commands','owned-work'):
    b=p.read_bytes(); copy=attempt/'source-snapshot'/rel; copy.parent.mkdir(parents=True,exist_ok=True); copy.write_bytes(b)
    sources.append({'path':str(rel),'bytes':len(b),'sha256':sha(b)})
  write_json(attempt/'source-manifest.json',{'members':sources,'scope':'reviewer-owned source, no candidate'})
  discover=bounded(['/opt/homebrew/bin/rustup','which','rustc'],ROOT,attempt,'rustc-location',seconds=10)
  results.append(discover)
  if discover['exit_code']!=0: raise ValueError('installed Rust compiler unavailable; no download attempted')
  rustc=Path(Path(discover['stdout']).read_text().strip())
  if not rustc.is_absolute() or not rustc.is_file(): raise ValueError('compiler path not exact')
  r=bounded([str(rustc),'--version','--verbose'],ROOT,attempt,'rustc-version',seconds=10); results.append(r)
  if r['exit_code']!=0: raise ValueError('compiler identity failed')
  write_json(attempt/'tool-identity.json',{'python':sys.version,'python_executable':sys.executable,
   'platform':platform.platform(),'rustc':str(rustc),'rustc_sha256':sha(rustc.read_bytes()),
   'rustc_version':Path(r['stdout']).read_text(),'compiler_scope':'self-owned tooling protocol stub only; no product/native runtime'})
  library=scratch/'libmixer_fixture_cache_state.rlib'; driver=scratch/'public-driver'
  commands=[('stub-library',[str(rustc),'--edition=2021','--crate-name','mixer_fixture_cache_state','--crate-type','rlib',str(HERE/'protocol_stub.rs'),'-o',str(library)]),
   ('public-driver',[str(rustc),'--edition=2021',str(HERE/'public_driver.rs'),'--extern','mixer_fixture_cache_state='+str(library),'-o',str(driver)])]
  for title,argv in commands:
   r=bounded(argv,ROOT,attempt,title); results.append(r)
   if r['exit_code']!=0 or r['timed_out'] or r['output_truncated']: raise ValueError('self-owned protocol compilation failed')
  compiled=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in [library,driver]]
  for probe in json.loads((HERE/'api-probes/manifest.json').read_text()):
   source=HERE/probe['path']; target=scratch/(probe['id']+'.rmeta')
   r=bounded([str(rustc),'--edition=2021','--emit=metadata','--crate-name','probe_'+probe['id'].replace('-','_'),
    str(source),'--extern','mixer_fixture_cache_state='+str(library),'-o',str(target)],ROOT,attempt,'api-'+probe['id'])
   results.append(r)
   if (r['exit_code']==0)!=probe['compile_success_expected'] or r['timed_out'] or r['output_truncated']:
    raise ValueError('self-owned API probe unexpected disposition '+probe['id'])
  test_output=attempt/'protocol-controls'; test_output.mkdir()
  r=bounded([sys.executable,'-B',str(HERE/'test_preparation.py'),str(driver),str(test_output)],ROOT,attempt,'protocol-controls'); results.append(r)
  if r['exit_code']!=0: raise ValueError('tooling protocol controls failed')
  status='reviewer-tooling-preparation-passed'
 except Exception as problem:
  write_json(attempt/'failure.json',{'type':type(problem).__name__,'message':str(problem),
   'candidate_source_accessed':False,'candidate_Rust_semantic_executions':0})
 finally:
  # This directory was created exclusively above; all bounded children returned.
  if scratch.exists(): shutil.rmtree(scratch)
  if scratch.parent.exists() and not any(scratch.parent.iterdir()): scratch.parent.rmdir()
  write_json(attempt/'cleanup.json',{'removed_owned_scratch':str(scratch),'all_owned_children_returned':True,
   'compiled_artifacts_before_cleanup':compiled,'native_capture_UI_or_process_discovery':False,'unrelated_processes_touched':False})
  summary={'status':status,'attempt':str(attempt.relative_to(HERE)),
   'commands':[{'argv':r['argv'],'exit_code':r['exit_code'],'timed_out':r['timed_out'],'output_truncated':r['output_truncated']} for r in results],
   'candidate_source_accessed':False,'candidate_Rust_semantic_executions':0,'product_tests':0}
  write_json(attempt/'summary.json',summary)
  if status=='reviewer-tooling-preparation-passed': write_json(HERE/'latest-preparation.json',summary)
  print(json.dumps(summary))
 return 0 if status=='reviewer-tooling-preparation-passed' else 1

if __name__=='__main__': raise SystemExit(main())
