#!/usr/bin/env python3
"""Snapshot and execute isolated Elixir/Ecto inspection on one owned PG17 fixture."""
import argparse,datetime,gzip,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tarfile,tempfile,time,traceback
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--model-only',action='store_true');a=ap.parse_args()
 out=pathlib.Path(a.out).resolve();assert out.parent==HERE;out.mkdir(exist_ok=False)
 commands=[];receipt={'schema':1,'scope':'isolated read-only Elixir/Ecto catalog inspector; no live installation or authority','started_utc':utc(),'success':False,'model_only':a.model_only}
 scratch=None;data=None;started=False;ok=False
 def run(label,argv,env=None,timeout=60,check=True,cwd=ROOT):
  rec={'label':label,'argv':list(map(str,argv)),'cwd':str(cwd),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic();log=out/(label+'.log')
  if env:rec['environment_overrides']={k:v for k,v in env.items() if k.startswith('MIXER_INSPECTOR_') or k in ['MIX_ENV','ERL_FLAGS','ERL_CRASH_DUMP']}
  try:
   p=subprocess.run(rec['argv'],cwd=cwd,env=env,capture_output=True,timeout=timeout);log.write_bytes(p.stdout+p.stderr);rec.update(exit_code=p.returncode,stdout_sha256=sha(p.stdout),stderr_sha256=sha(p.stderr),log=log.name,log_sha256=sha(log.read_bytes()))
  except Exception as e:rec.update(error=repr(e),exit_code=None);raise
  finally:rec['seconds']=time.monotonic()-t;commands.append(rec);save(out/'commands.json',commands)
  if check and p.returncode:raise RuntimeError(label+' failed: '+str(p.returncode))
  return p
 try:
  receipt['head']=run('head',['git','rev-parse','HEAD']).stdout.decode().strip();receipt['tree']=run('tree',['git','rev-parse','HEAD^{tree}']).stdout.decode().strip();receipt['platform']=platform.platform()
  tools={}
  for name in ['python3','elixir','mix','erl','postgres','pg_ctl','initdb','psql','createdb']:
   p=pathlib.Path(shutil.which(name)).resolve();version_args=['+V'] if name=='erl' else ['--version']
   v=run('version-'+name,[str(p),*version_args]);tools[name]={'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'version':(v.stdout+v.stderr).decode().strip()}
  save(out/'tools.json',tools)
  scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-catalog-inspector-',dir='/private/tmp')).resolve();receipt['scratch']=str(scratch)
  source=scratch/'component';shutil.copytree(HERE/'component',source);shutil.copytree(HERE/'inputs',scratch/'inputs')
  (out/'evidence').mkdir()
  sources=[]
  for base in [source,scratch/'inputs']:
   for p in sorted(base.rglob('*')):
    if p.is_file():sources.append({'path':str(p.relative_to(scratch)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
  deps=[]
  for name in ['ecto_sql','ecto','postgrex','db_connection','decimal','telemetry','jason']:
   origin=ROOT/'hosted/deps'/name;dest=source/'deps'/name;shutil.copytree(origin,dest,ignore=shutil.ignore_patterns('_build','.git','__pycache__'))
   for p in sorted(dest.rglob('*')):
    if p.is_file():deps.append({'path':str(p.relative_to(source/'deps')),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
  save(out/'source-manifest.json',sources);save(out/'dependency-manifest.json',deps)
  receipt['source_digest']=sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode());receipt['dependency_digest']=sha(json.dumps(deps,sort_keys=True,separators=(',',':')).encode())
  shutil.copyfile(__file__,out/'executed-run.py')
  with tarfile.open(out/'source-and-dependencies.tar.gz','w:gz') as arc:
   arc.add(source,arcname='component',recursive=True);arc.add(scratch/'inputs',arcname='inputs',recursive=True)
  env=dict(os.environ,MIX_ENV='test',ERL_FLAGS='+S 4:4',ERL_CRASH_DUMP=str(scratch/'erl_crash.dump'),MIXER_INSPECTOR_INPUTS=str(scratch/'inputs'),MIXER_INSPECTOR_OUT=str(out/'evidence'))
  run('deps-compile',['mix','deps.compile'],env=env,timeout=120,cwd=source)
  run('compile',['mix','compile','--warnings-as-errors'],env=env,timeout=60,cwd=source)
  run('model-tests',['mix','test','test/raw_test.exs','--trace','--warnings-as-errors'],env=env,timeout=120,cwd=source)
  if not a.model_only:
   data=scratch/'pg';sock=scratch/'socket';sock.mkdir(mode=0o700)
   run('initdb',['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
   run('pg-start',['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
   run('create-db',['createdb','-h',sock,'authority_contract'])
   padding='CREATE SCHEMA inspector_padding;'+''.join(f'CREATE TABLE inspector_padding.p{i}(a integer);' for i in range(173))
   run('padding',['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-c',padding])
   run('schema',['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',scratch/'inputs/schema.sql'])
   env['MIXER_INSPECTOR_SOCKET']=str(sock)
   run('runtime-tests',['mix','test','test/runtime_test.exs','--trace','--warnings-as-errors'],env=env,timeout=120,cwd=source)
  ok=True
 except Exception as exc:receipt['error']=repr(exc);(out/'failure.log').write_text(traceback.format_exc())
 finally:
  if data and (started or (data/'postmaster.pid').exists()):run('pg-stop',['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
  if scratch and (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
  if scratch and (scratch/'erl_crash.dump').exists():shutil.copyfile(scratch/'erl_crash.dump',out/'erl_crash.dump')
  stopped=not data or not (data/'postmaster.pid').exists()
  if scratch and stopped:shutil.rmtree(scratch)
  receipt.update(success=ok,finished_utc=utc(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch or not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_or_phone_runs':False})
  save(out/'receipt.json',receipt);print(json.dumps(receipt,indent=2))
 return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
