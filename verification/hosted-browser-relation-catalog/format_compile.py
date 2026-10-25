#!/usr/bin/env python3
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=Path(__file__).resolve().parent
files=['hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex','hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex','verification/hosted-browser-relation-catalog/live.exs','verification/hosted-browser-relation-catalog/effects.exs']
out={'commands':[],'cleanup':{}}
env=dict(os.environ,ERL_FLAGS='+S 2:2')
scratch=Path(tempfile.mkdtemp(prefix='mixer-relation-catalog-format-'))
try:
 for p in files: shutil.copy2(R/p,scratch/Path(p).name)
 for cmd,cwd in [(['mix','format']+[Path(p).name for p in files],scratch)]:
  p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True);out['commands'].append({'command':cmd,'cwd':str(cwd),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
  if p.returncode: raise RuntimeError('format failed')
 for p in files: shutil.copy2(scratch/Path(p).name,R/p)
 cmd=['elixirc']+[a for d in ['telemetry','decimal','db_connection','ecto','ecto_sql','postgrex','jason','oban'] for a in ['-pa',str(R/'hosted/_build/test/lib'/d/'ebin')]]+['--warnings-as-errors','-o',str(scratch)]+files[:2]
 p=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True);out['commands'].append({'command':cmd,'cwd':str(R),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 out['passed']=p.returncode==0
finally:
 shutil.rmtree(scratch);out['cleanup']['scratch_absent']=not scratch.exists()
 (B/'format-compile.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
if not out.get('passed'):raise SystemExit(1)
