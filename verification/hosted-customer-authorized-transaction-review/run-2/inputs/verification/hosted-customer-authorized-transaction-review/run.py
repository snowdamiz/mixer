#!/usr/bin/env python3
"""Independent selected-source BEAM / disposable loopback PostgreSQL review."""
import argparse, hashlib, json, os, platform, shutil, socket, subprocess, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
LANE = ROOT / 'verification/hosted-customer-authorized-transaction-review'
SOURCES = [
 'hosted/lib/mixer_hosted/identity/encoding.ex',
 'hosted/lib/mixer_hosted/identity/verified_identity.ex',
 'hosted/lib/mixer_hosted/authorization/scope.ex',
 'hosted/lib/mixer_hosted/authorization/policy.ex',
 'hosted/lib/mixer_hosted/authorization/postgres/session.ex',
 'hosted/lib/mixer_hosted/authorization/postgres/evidence.ex',
 'hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex',
 'hosted/lib/mixer_hosted/authorization/transaction/context.ex',
 'hosted/lib/mixer_hosted/authorization.ex',
 'hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs',
 'hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs',
]
DEPS = ['telemetry','decimal','db_connection','ecto','ecto_sql','postgrex','jason']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output',required=True); p.add_argument('--source-revision',required=True); a=p.parse_args()
 out=(LANE/a.output).resolve(); out.relative_to(LANE); out.mkdir(parents=True,exist_ok=False)
 scratch=Path(tempfile.mkdtemp(prefix='mixer-authz-independent-review-'))
 env=dict(os.environ,ERL_FLAGS='+S 2:2',MIX_ENV='test')
 receipt={'source_revision':a.source_revision,'revision_provenance':'parent supplied; no Git invocation','scope':'ordinary selected BEAM modules; actual disposable local PostgreSQL; independent adversarial tests; no full Mix app, shared harness, frozen lanes, devices or providers','platform':platform.platform(),'started_unix':time.time(),'commands':[],'cleanup':{},'scratch':str(scratch)}
 started=False; success=False
 def run(name,argv,timeout=90,check=True):
  r=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
  (out/(name+'.log')).write_text(r.stdout)
  receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'exit_code':r.returncode,'output':name+'.log'})
  if check and r.returncode: raise RuntimeError(name+' failed; see preserved log')
  return r
 try:
  inputs=SOURCES+[str((LANE/'run.py').relative_to(ROOT)),str((LANE/'review_test.exs').relative_to(ROOT))]
  manifest={}
  for name in sorted(inputs):
   target=out/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,target); manifest[name]=sha(ROOT/name)
  receipt['input_sha256']=manifest; receipt['source_tree_sha256']=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  paths=[ROOT/'hosted/_build/test/lib'/dep/'ebin' for dep in DEPS]
  dm={}
  for path in paths:
   if not path.is_dir(): raise RuntimeError('missing existing dependency BEAM path: '+str(path))
   for beam in sorted(path.iterdir()):
    if beam.is_file(): dm[str(beam.relative_to(ROOT))]=sha(beam)
  (out/'dependency-beams.json').write_text(json.dumps(dm,indent=2,sort_keys=True)+'\n'); receipt['dependency_manifest_sha256']=sha(out/'dependency-beams.json')
  run('elixir-version',['elixir','--version']);run('python-version',['python3','--version'])
  pg=Path(run('postgres-bindir',['pg_config','--bindir']).stdout.strip());run('postgres-version',[pg/'postgres','--version'])
  beams=scratch/'beams';beams.mkdir();cp=[arg for path in paths for arg in ['-pa',str(path)]]
  run('compile',['elixirc','--warnings-as-errors',*cp,'-o',beams,*[out/'inputs'/s for s in SOURCES]])
  run('postgres-init',[pg/'initdb','-D',scratch/'pg','-U','review_admin','-A','trust','--no-locale','-E','UTF8'])
  with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  (scratch/'pg/postgresql.auto.conf').write_text(f"listen_addresses='127.0.0.1'\nport={port}\nunix_socket_directories='{scratch}'\nmax_connections=24\n")
  receipt['postgres_endpoint']={'host':'127.0.0.1','port':port,'database':'authz_review','disposable':True}
  run('postgres-start',[pg/'pg_ctl','-D',scratch/'pg','-l',scratch/'postgres.log','-w','start']);started=True
  sql=[pg/'psql','-h','127.0.0.1','-p',port,'-U','review_admin','-v','ON_ERROR_STOP=1']
  run('roles',sql+['-d','postgres','-c','CREATE ROLE review_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE review_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE review_alternate NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; GRANT review_alternate TO review_runtime;'])
  run('database',[pg/'createdb','-h','127.0.0.1','-p',port,'-U','review_admin','authz_review'])
  run('schema',sql+['-d','authz_review','-c','REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO review_owner; GRANT USAGE ON SCHEMA public TO review_runtime;'])
  env['MIXER_AUTHZ_REVIEW_PORT']=str(port)
  runner=scratch/'run.exs';runner.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file('+json.dumps(str(out/'inputs'/str((LANE/'review_test.exs').relative_to(ROOT))))+')\nr = ExUnit.run()\nSystem.halt(if r.failures == 0, do: 0, else: 1)\n')
  run('tests',['elixir',*cp,'-pa',beams,runner],timeout=120)
  success=True
 except Exception as e: receipt['failure']=str(e)
 finally:
  if started:
   try: receipt['cleanup']['postgres_stopped']=run('postgres-stop',[pg/'pg_ctl','-D',scratch/'pg','-m','immediate','-w','stop'],timeout=30,check=False).returncode==0
   except Exception as e: receipt['cleanup']['postgres_stop_error']=str(e)
  else:receipt['cleanup']['postgres_started']=False
  if (scratch/'postgres.log').exists():shutil.copy2(scratch/'postgres.log',out/'postgres.log')
  if not started or receipt['cleanup'].get('postgres_stopped'):shutil.rmtree(scratch)
  receipt['cleanup']['scratch_removed']=not scratch.exists();receipt['success']=success;receipt['finished_unix']=time.time();(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:receipt.get(k) for k in ['success','source_tree_sha256','failure','cleanup']},sort_keys=True));return 0 if success else 1
if __name__=='__main__':raise SystemExit(main())
