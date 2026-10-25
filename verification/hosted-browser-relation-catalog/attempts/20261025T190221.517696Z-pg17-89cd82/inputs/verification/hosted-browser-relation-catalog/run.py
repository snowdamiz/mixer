#!/usr/bin/env python3
"""Serial, owned actual database verification; no broad app harness."""
import argparse,datetime as dt,hashlib,json,os,shutil,signal,socket,subprocess,tempfile,time,uuid
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=Path(__file__).resolve().parent
PG=Path('/opt/homebrew/Cellar/postgresql@17/17.11/bin')
IMAGE='postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97'
DEPS=['telemetry','decimal','db_connection','ecto','ecto_sql','postgrex','jason','oban']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(d):return hashlib.sha256(''.join(p+'\t'+h+'\n' for p,h in sorted(d.items())).encode()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--major',type=int,choices=[16,17],required=True);args=ap.parse_args()
 out=B/'attempts'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+f'-pg{args.major}-'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 receipt={'schema':1,'major':args.major,'commands':[],'cleanup':{},'scope':'Standalone RelationCatalog actual runtime prerequisite only; no Store provenance/readiness/provider/native'}
 env=dict(os.environ,ERL_FLAGS='+S 2:2',MIX_ENV='test')
 scratch=None;container=None;started=False
 def run(label,cmd,data=None,check=True,timeout=45):
  cmd=list(map(str,cmd));entry={'label':label,'command':cmd,'cwd':str(R),'timeout':timeout};receipt['commands'].append(entry)
  p=subprocess.Popen(cmd,cwd=R,env=env,stdin=subprocess.PIPE if data is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:stdout,stderr=p.communicate(data.encode() if isinstance(data,str) else data,timeout=timeout);entry['timed_out']=False
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=5);entry['timed_out']=True
  entry['exit']=p.returncode
  (out/(label+'.stdout')).write_bytes(stdout);(out/(label+'.stderr')).write_bytes(stderr)
  if data is not None:(out/(label+'.stdin')).write_bytes(data.encode() if isinstance(data,str) else data)
  if check and (p.returncode or entry['timed_out']):raise RuntimeError(label+' failed')
  return p.returncode,stdout.decode()
 try:
  manifests=json.loads((R/'hosted/priv/browser_auth/relation_surface_v1_pg16.json').read_text())
  sources=set(manifests['source_bindings'])|{'AGENTS.md','verification/hosted-browser-relation-representation/install.exs',
   'verification/hosted-browser-relation-catalog/run.py','verification/hosted-browser-relation-catalog/effects.exs','verification/hosted-browser-relation-catalog/live.exs',
   'hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex','hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex',
   'hosted/priv/browser_auth/relation_surface_v1_pg16.json','hosted/priv/browser_auth/relation_surface_v1_pg17.json'}
  source_hashes={p:sha(R/p) for p in sorted(sources)}
  for path in sources:
   target=out/'inputs'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/path,target)
  receipt['source_sha256']=source_hashes;receipt['source_tree_sha256']=tree(source_hashes)
  depdirs=[R/'hosted/_build/test/lib'/d/'ebin' for d in DEPS]
  dependencies={str(p.relative_to(R)):sha(p) for d in depdirs for p in sorted(d.iterdir()) if p.is_file()}
  receipt['dependency_sha256']=dependencies;receipt['dependency_tree_sha256']=tree(dependencies)
  _,rev=run('revision',['git','rev-parse','HEAD']);receipt['revision']=rev.strip()
  run('elixir-version',['elixir','--version']);run('python-version',['python3','--version']);run('psql-version',[PG/'psql','--version'])
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  receipt['port']=port
  if args.major==17:
   scratch=Path(tempfile.mkdtemp(prefix='mixer-relation-catalog-pg17-'));receipt['owned_scratch']=str(scratch)
   run('initdb',[PG/'initdb','-D',scratch/'data','-U','browser_admin','-A','trust','--no-locale','-E','UTF8'])
   started=True;run('start',[PG/'pg_ctl','-D',scratch/'data','-l',out/'server.log','-o',f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC",'-w','start'])
  else:
   container='mixer-relation-catalog-pg16-'+uuid.uuid4().hex[:12];receipt['owned_container']=container
   run('docker-version',['docker','version','--format','{{json .Server}}']);run('image',['docker','image','inspect',IMAGE])
   started=True;run('start',['docker','run','--detach','--rm','--name',container,'--label','mixer.fixture=relation-catalog','--publish',f'127.0.0.1:{port}:5432','--env','POSTGRES_USER=browser_admin','--env','POSTGRES_HOST_AUTH_METHOD=trust','--env','POSTGRES_INITDB_ARGS=--no-locale -E UTF8',IMAGE,'-c','timezone=UTC'])
   for i in range(80):
    code,_=run(f'ready-{i}',['docker','exec',container,'pg_isready','-h','127.0.0.1','-U','browser_admin'],check=False)
    if code==0:
     try:
      with socket.create_connection(('127.0.0.1',port),timeout=.2):break
     except OSError:pass
    time.sleep(.1)
   else:raise RuntimeError('owned PG16 readiness failed')
  admin=[PG/'psql','-X','-q','-A','-t','-h','127.0.0.1','-p',port,'-U','browser_admin','-d','postgres','-v','ON_ERROR_STOP=1']
  run('roles',admin,data=';'.join('CREATE ROLE '+r+' '+login+' NOSUPERUSER NOBYPASSRLS NOINHERIT' for r,login in [('browser_schema_owner','NOLOGIN'),('browser_writer','NOLOGIN'),('browser_lifecycle','LOGIN'),('browser_ordinary','LOGIN'),('representation_extra','NOLOGIN')])+';')
  run('database',admin,data='CREATE DATABASE browser_storage OWNER browser_schema_owner;')
  env['RELATION_MAJOR']=str(args.major);env['REPRESENTATION_PORT']=str(port);env['RELATION_PORT']=str(port);env['RELATION_OUTPUT']=str(out)
  elixir=['elixir']+[a for d in depdirs for a in ['-pa',d]]
  run('install',elixir+[R/'verification/hosted-browser-relation-representation/install.exs'],timeout=60)
  run('live',elixir+[R/'verification/hosted-browser-relation-catalog/live.exs'],timeout=90)
  receipt['passed']=True
 except Exception as e:receipt['failure']=type(e).__name__+': '+str(e)
 finally:
  if args.major==17 and scratch:
   if started and (scratch/'data/postmaster.pid').exists():run('stop',[PG/'pg_ctl','-D',scratch/'data','-m','immediate','-w','stop'],check=False)
   receipt['cleanup']['postmaster_absent']=not (scratch/'data/postmaster.pid').exists()
   if receipt['cleanup']['postmaster_absent']:shutil.rmtree(scratch)
   receipt['cleanup']['scratch_absent']=not scratch.exists()
  elif container:
   run('server-log',['docker','logs',container],check=False)
   run('stop',['docker','stop','--timeout','5',container],check=False)
   code,_=run('absence',['docker','container','inspect',container],check=False)
   receipt['cleanup']['container_absent']=code!=0
  receipt['source_changes']=[p for p,h in locals().get('source_hashes',{}).items() if sha(R/p)!=h]
  receipt['dependency_changes']=[p for p,h in locals().get('dependencies',{}).items() if sha(R/p)!=h]
  receipt['success']=receipt.get('passed',False) and all(receipt['cleanup'].values()) and not receipt['source_changes'] and not receipt['dependency_changes']
  receipt['output_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and 'inputs' not in p.relative_to(out).parts}
  receipt['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat()
  (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
  print(out.relative_to(R));print(json.dumps({k:receipt.get(k) for k in ['success','failure','cleanup']}))
 return 0 if receipt['success'] else 1
if __name__=='__main__':raise SystemExit(main())
