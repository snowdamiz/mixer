#!/usr/bin/env python3
"""Replay the actual fixed-Repo driver in an owned socket-only PostgreSQL cluster."""
import datetime,hashlib,json,os,pathlib,shutil,subprocess,sys,tarfile,tempfile,time,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 n=1
 while (HERE/f'run-{n}').exists():n+=1
 out=HERE/f'run-{n}';out.mkdir();scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-authz-driver-',dir='/private/tmp')).resolve();project=scratch/'hosted';sock=scratch/'socket';sock.mkdir(mode=0o700);data=scratch/'pg';commands=[];started=False;success=False
 receipt={'schema':1,'scope':'ISOLATED actual Ecto/Postgrex current-authority driver/coordinator candidate; no live integration, final schema selection, domain composition, HTTP/provider/native or GA acceptance','started_utc':utc(),'scratch':str(scratch)}
 def run(label,argv,cwd=ROOT,env=None,check=True,timeout=120):
  log=out/(label+'.log');a={'label':label,'argv':list(map(str,argv)),'cwd':str(cwd),'started_utc':utc(),'timeout_seconds':timeout,'environment_overrides':{k:env[k] for k in ['MIX_ENV','MIXER_AUTHZ_SOCKET','MIXER_AUTHZ_OUT','DRIVER_SOCKET','DRIVER_OUT','ERL_FLAGS','MIX_BUILD_PATH','MIX_DEPS_PATH'] if env and k in env}};start=time.monotonic()
  try:
   with log.open('wb') as f:p=subprocess.run(a['argv'],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
   a['exit_code']=p.returncode
  except Exception as e:a['error']=str(e);raise
  finally:
   a.update(duration_seconds=time.monotonic()-start,log=log.name,sha256=sha(log.read_bytes()) if log.exists() else None);commands.append(a);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  if check and p.returncode:raise RuntimeError(label+' failed; see '+str(log))
  return log.read_text()
 try:
  receipt['revision']=run('revision',['git','rev-parse','HEAD']).strip();receipt['tree']=run('tree',['git','rev-parse','HEAD^{tree}']).strip()
  for label,argv in [('elixir-version',['elixir','--version']),('mix-version',['mix','--version']),('postgres-version',['postgres','--version']),('python-version',['python3','--version']),('system',['uname','-a'])]:run(label,argv)
  src=out/'source';src.mkdir();inputs=out/'inputs';inputs.mkdir();baseline=[]
  for p in sorted((ROOT/'hosted').rglob('*')):
   if p.is_file() and not {'deps','_build','.git','__pycache__'}.intersection(p.relative_to(ROOT/'hosted').parts) and p.name!='erl_crash.dump':
    rel=p.relative_to(ROOT);b=p.read_bytes();target=inputs/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);baseline.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)})
  for rel in ['AGENTS.md','mixer-product-plan.md','docs/hosted-authority-driver-contract.md','docs/hosted-authority-schema-contract.md','docs/hosted-authority-schema-corrections.md','verification/hosted-authority-schema-root-review/driver-direction.json','verification/hosted-transaction-context-root-review/selection.json','verification/hosted-authority-schema-contract/receipt.json']:
   b=(ROOT/rel).read_bytes();p=inputs/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);baseline.append({'path':rel,'sha256':sha(b),'bytes':len(b)})
  for name in ['schema.sql','functions.sql','catalog.sql','tests.py']:
   b=(ROOT/'verification/hosted-authority-schema-contract/probe'/name).read_bytes();(src/name).write_bytes(b)
  assert sha((src/'schema.sql').read_bytes())=='d5883b47f308ffe9aa4ed55d3361aab313bf07421c41bffe13bba7b7f41cfd99'
  assert sha((src/'functions.sql').read_bytes())=='b70f9b1eb7d06f60a6ce3532d4d2fa51cd9afd564f10183a1d15a7ff36bbb11c'
  shutil.copytree(HERE/'probe',src/'probe');shutil.copy2(__file__,src/'run.py')
  (out/'input-manifest.json').write_text(json.dumps(baseline,indent=2)+'\n')
  sourceman=[{'path':str(p.relative_to(src)),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(src.rglob('*')) if p.is_file()];(out/'source-manifest.json').write_text(json.dumps(sourceman,indent=2)+'\n');receipt['source_digest']=sha(json.dumps(sourceman,sort_keys=True,separators=(',',':')).encode())
  deps=ROOT/'hosted/deps';depman=[{'path':str(p.relative_to(deps)),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(deps.rglob('*')) if p.is_file() and '.git' not in p.parts];(out/'dependency-manifest.json').write_text(json.dumps(depman,indent=2)+'\n');receipt['dependency_digest']=sha(json.dumps(depman,sort_keys=True,separators=(',',':')).encode())
  # Preserve all installed source bytes and lock; compile only the isolated copy.
  with tarfile.open(out/'dependencies.tar.gz','w:gz') as archive:
   for item in depman:archive.add(deps/item['path'],arcname=item['path'],recursive=False)
  shutil.copytree(inputs/'hosted',project);shutil.copytree(deps,project/'deps',ignore=shutil.ignore_patterns('.git','_build'));shutil.copytree(src/'probe/lib',project/'lib/mixer_hosted/authority_driver')
  env=dict(os.environ,MIX_ENV='test',ERL_FLAGS='+S 4:4',MIX_BUILD_PATH=str(scratch/'build'),MIX_DEPS_PATH=str(project/'deps'),DRIVER_SOCKET=str(sock),DRIVER_OUT=str(out))
  receipt['execution_environment']={'transport':'unix socket only, trust synthetic fixture','runtime_login':'mixer_hosted_runtime','fixture_login':os.environ['USER'],'driver_pool_size':1,'ERL_FLAGS':env['ERL_FLAGS'],'environment_names_preserved':sorted(k for k in os.environ if k in ['PATH','HOME','USER','SHELL','LANG','LC_ALL'])}
  run('format-overlay',['mix','format',*map(str,(src/'probe/lib').glob('*.ex')),str(src/'probe/driver_test.exs')],cwd=project,env=env)
  # Formatting is canonical source preparation; copy the exact formatted overlay back.
  for p in (src/'probe/lib').glob('*.ex'):shutil.copy2(p,project/'lib/mixer_hosted/authority_driver'/p.name)
  run('compile',['mix','compile','--warnings-as-errors'],cwd=project,env=env)
  run('initdb',['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
  run('wide-xid-fixture',['pg_resetwal','-e','1','-x','1000',data])
  run('postgres-start',['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700 -c track_functions=all",'-w','start']);started=True
  run('createdb',['createdb','-h',sock,'authority_contract'])
  run('schema',['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',src/'schema.sql'])
  # Frozen original suite executes once for this candidate. Later driver attempts retain
  # and bind that immutable successful observation instead of inflating driver counts.
  prior=next((p for p in sorted(HERE.glob('run-*/original-suite/summary.json')) if json.loads(p.read_text()).get('passed')==128),None)
  if prior:
   receipt['original_suite']={'qualification':'reused immutable successful original suite execution','path':str(prior.parent.relative_to(HERE)),'summary_sha256':sha(prior.read_bytes())}
  else:
   original=out/'original-suite';original.mkdir();schemaenv=dict(env,MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(original),PYTHONDONTWRITEBYTECODE='1')
   run('original-schema-suite',['python3','-B',src/'tests.py'],env=schemaenv,timeout=120)
   summary=json.loads((original/'summary.json').read_text());assert summary['total']==128 and summary['passed']==128
   receipt['original_suite']={'qualification':'exact original128cases replayed unchanged once','path':str(original.relative_to(HERE)),'summary_sha256':sha((original/'summary.json').read_bytes())}
  # Original catalog remains unchanged; narrowly synthetic effects live outside it.
  run('driver-tests',['mix','run','--no-start',src/'probe/driver_test.exs'],cwd=project,env=env,timeout=120)
  tests=json.loads((out/'driver-tests.json').read_text());assert tests['passed']==tests['total'];receipt['driver_tests']={'passed':tests['passed'],'total':tests['total']}
  success=True
 except Exception as e:
  receipt['error']=repr(e);(out/'failure.log').write_text(traceback.format_exc())
 finally:
  if started:run('postgres-stop',['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
  if (scratch/'postgres.log').exists():shutil.copy2(scratch/'postgres.log',out/'postgres.log')
  stopped=not (data/'postmaster.pid').exists()
  if stopped:shutil.rmtree(scratch)
  # Recompute frozen source manifest after canonical formatting, including failures.
  if (out/'source').exists():
   source=out/'source';sm=[{'path':str(p.relative_to(source)),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(source.rglob('*')) if p.is_file()];(out/'source-manifest.json').write_text(json.dumps(sm,indent=2)+'\n');receipt['source_digest']=sha(json.dumps(sm,sort_keys=True,separators=(',',':')).encode())
  receipt.update(success=success,finished_utc=utc(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False,'native_runs':False});(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
