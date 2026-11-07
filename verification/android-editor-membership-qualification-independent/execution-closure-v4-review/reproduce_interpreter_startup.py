#!/usr/bin/env python3
"""Owned venv startup witness against v4's explicit synthetic positive fixture."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,sys,time
D=Path(__file__).resolve().parent
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
E=D/'interpreter-startup-witness';E.mkdir();scratch=E/'scratch';scratch.mkdir();commands=[]
jdk=Path(json.loads((D/'input/jdk17-tool-context.json').read_bytes())['jdk_home'])
env={'PATH':str(jdk/'bin')+':/usr/bin:/bin','LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'}
def run(label,argv):
 start=time.monotonic();stdout=E/(label+'.stdout');stderr=E/(label+'.stderr')
 with stdout.open('wb') as out,stderr.open('wb') as err:
  child=subprocess.Popen([str(x) for x in argv],cwd=scratch,env=env,stdout=out,stderr=err,start_new_session=True);timeout=False
  try:child.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
 record={'name':label,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-start,'stdout':identity(stdout),'stderr':identity(stderr)};commands.append(record);save(E/'commands.json',commands);assert child.returncode==0 and not timeout,record
 return stdout.read_text()
try:
 fixture=scratch/'fixture';shutil.copytree(D/'input/integrity-controls-3/retained-positive-fixture',fixture)
 bootstrap=fixture/'bootstrap.py';manifest=fixture/'execution-manifest.json';payload=fixture/'payload';original_selection=identity(manifest)
 arguments=['--execution-manifest',manifest,'--execution-root',payload,'--jdk-home',jdk]
 run('baseline-selected-synthetic-bootstrap',[sys.executable,'-I','-B',bootstrap,*arguments,'--output',fixture/'baseline-receipt.json'])
 baseline=json.loads((fixture/'baseline-receipt.json').read_bytes());assert baseline['status']=='passed-exact-host-qualified-matrix'
 venv=scratch/'owned-venv';run('create-owned-venv-without-pip',[sys.executable,'-I','-B','-m','venv','--without-pip',venv])
 python=venv/'bin/python';assert identity(python.resolve())==json.loads(manifest.read_bytes())['python_executable']
 site=venv/('lib/python%d.%d/site-packages'%sys.version_info[:2]);assert site.is_dir()
 marker=scratch/'unselected-site-startup-executed.txt'
 hook=site/'unselected-startup.pth';hook.write_text('import pathlib; pathlib.Path('+repr(str(marker))+').write_text("unselected venv site startup executed")\n')
 source_identity=identity(hook);save(E/'venv-hook-evidence.json',{'site_hook_source':hook.read_text(),'site_hook_identity':source_identity,'resolved_interpreter_identity':identity(python.resolve()),'selected_interpreter_identity':json.loads(manifest.read_bytes())['python_executable'],'venv_config':(venv/'pyvenv.cfg').read_text(),'same_binary_identity':True})
 run('unselected-venv-site-bootstrap',[python,'-I','-B',bootstrap,*arguments,'--output',fixture/'site-receipt.json'])
 receipt=json.loads((fixture/'site-receipt.json').read_bytes())
 assert receipt['status']=='passed-exact-host-qualified-matrix'
 assert marker.is_file() and marker.read_text()=='unselected venv site startup executed'
 assert identity(manifest)==original_selection
 save(E/'result.json',{'scope':'Actual released v4 bootstrap/checker control flow under its explicitly synthetic selected policy. No real product policy/context/matrix is approved.',
 'witness_reproduced':True,'unselected_site_code_executed':True,'certificate_still_accepted':True,
 'manifest_unchanged':True,'selected_manifest':original_selection,
 'resolved_interpreter_file_matches_selected':True,'startup_flags':['-I','-B'],
 'startup_hook_outside_selected_payload_jdk_and_executable_hash':True,
 'baseline_receipt':baseline,'site_receipt':receipt,'marker_contents':marker.read_text(),
 'unselected_hook_source':hook.read_text(),'unselected_hook_identity':source_identity,
 'global_python_or_jdk_mutated':False,'native_UI_capture_or_process_inventory':False})
 shutil.copy2(fixture/'site-receipt.json',E/'accepted-synthetic-site-receipt.json');shutil.copy2(fixture/'baseline-receipt.json',E/'accepted-synthetic-baseline-receipt.json');shutil.copy2(bootstrap,E/'synthetic-selected-bootstrap.py');shutil.copy2(manifest,E/'synthetic-execution-manifest.json')
 print(json.dumps({'witness_reproduced':True,'unselected_startup_executed':True,'same_binary':True,'same_manifest':True,'synthetic_certificate_accepted':True}))
finally:
 shutil.rmtree(scratch);save(E/'cleanup.json',{'owned_venv_and_scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'global_installations_changed':False,'native_UI_capture_or_process_inventory':False})
