#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
O=Path(__file__).resolve().parent;R=O.parents[1];E=O/'final-checks';E.mkdir(exist_ok=False);commands=[];env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
for script in ['verify_custody.py','audit_sources.py','audit_cross_and_runs.py','audit_ime_frames.py']:
 argv=[sys.executable,'-B',str(O/script)];start=time.monotonic();r=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=60);(E/(script+'.stdout')).write_bytes(r.stdout);(E/(script+'.stderr')).write_bytes(r.stderr);commands.append({'argv':argv,'exit':r.returncode,'elapsed_seconds':time.monotonic()-start,'script':ident(O/script),'stdout':ident(E/(script+'.stdout')),'stderr':ident(E/(script+'.stderr')),'child_reaped':True});assert r.returncode==0,(script,r.stderr.decode())
version=subprocess.run([sys.executable,'--version'],capture_output=True,timeout=15);(E/'python-version.stdout').write_bytes(version.stdout);revision=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,timeout=15);assert revision.returncode==0
(E/'receipt.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'python_executable':sys.executable,'git_revision_at_final_offline_review':revision.stdout.decode().strip(),'commands':commands,'scope':'final reproducible independent custody/source/retained-cross/fresh-host frame audits only','native_UI_capture_process_inventory':False},indent=2)+'\n');print('PASS all four final source-bound independent audits')
