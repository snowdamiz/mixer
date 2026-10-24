#!/usr/bin/env python3
"""Compile/probe only in a new owned socket-only PostgreSQL 17 cluster."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def digest(data):return hashlib.sha256(data).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 idx=1
 while (HERE/f'run-{idx}').exists():idx+=1
 out=HERE/f'run-{idx}';out.mkdir(); scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-authz-contract-',dir='/private/tmp')).resolve();sock=scratch/'socket';sock.mkdir(mode=0o700);data=scratch/'pg';commands=[];started=False;success=False
 receipt={'schema':1,'scope':'ISOLATED authoritative schema/resolver prerequisite only; no live migration/repository/HTTP/provider/native/GA acceptance','started_utc':utc(),'run':out.name,'scratch':str(scratch)}
 def run(argv,check=True,timeout=30):
  a={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':utc(),'timeout_seconds':timeout};t=time.monotonic()
  try:
   p=subprocess.run(a['argv'],cwd=ROOT,text=True,capture_output=True,timeout=timeout);a.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
  except Exception as e:a.update(error=repr(e));raise
  finally:a['duration_seconds']=time.monotonic()-t;commands.append(a);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  if check and p.returncode:raise RuntimeError(a)
  return p
 try:
  receipt['observed_head']=run(['git','rev-parse','HEAD']).stdout.strip();receipt['observed_tree']=run(['git','rev-parse','HEAD^{tree}']).stdout.strip()
  for argv in [['python3','--version'],['postgres','--version'],['pg_ctl','--version'],['psql','--version'],['pg_config','--libdir']]:run(argv)
  bindings=[]
  inputs=['AGENTS.md','mixer-product-plan.md','docs/hosted-membership-storage-contract.md','docs/hosted-transaction-context-preflight.md','docs/hosted-atomic-storage-corrections.md','verification/hosted-atomic-storage-root-review/correction-selection.json','verification/hosted-transaction-context-root-review/selection.json','verification/hosted-transaction-context-root-review/atomic-writer-direction.json','hosted/lib/mixer_hosted/identity/verified_identity.ex','hosted/lib/mixer_hosted/identity/access_token_verifier.ex','verification/hosted-identity-startup-root-review/integration.json']
  for rel in inputs:
   b=(ROOT/rel).read_bytes();p=out/'inputs'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);bindings.append({'path':rel,'sha256':digest(b),'bytes':len(b)})
  (out/'input-manifest.json').write_text(json.dumps(bindings,indent=2)+'\n')
  sources=[]
  for p in sorted((HERE/'probe').glob('*')):
   if p.is_file():
    b=p.read_bytes();t=out/'source'/p.name;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b);sources.append({'path':'probe/'+p.name,'sha256':digest(b),'bytes':len(b)})
  b=pathlib.Path(__file__).read_bytes();(out/'source'/'run.py').write_bytes(b);sources.append({'path':'run.py','sha256':digest(b),'bytes':len(b)})
  receipt['source_digest']=digest(json.dumps(sources,sort_keys=True,separators=(',',':')).encode());(out/'source-manifest.json').write_text(json.dumps(sources,indent=2)+'\n')
  run(['initdb','-D',data,'-A','trust','--no-locale','--encoding=UTF8'])
  run(['pg_ctl','-D',data,'-l',scratch/'postgres.log','-o',f"-F -k {sock} -c listen_addresses='' -c unix_socket_permissions=0700",'-w','start']);started=True
  run(['createdb','-h',sock,'authority_contract'])
  run(['psql','-X','-v','ON_ERROR_STOP=1','-h',sock,'-d','authority_contract','-f',out/'source'/'schema.sql'])
  env=dict(os.environ,MIXER_AUTHZ_SOCKET=str(sock),MIXER_AUTHZ_OUT=str(out),PYTHONDONTWRITEBYTECODE='1')
  a={'argv':['python3','-B',str(out/'source'/'tests.py')],'cwd':str(ROOT),'environment_overrides':{k:env[k] for k in ['MIXER_AUTHZ_SOCKET','MIXER_AUTHZ_OUT','PYTHONDONTWRITEBYTECODE']},'started_utc':utc()};t=time.monotonic();p=subprocess.run(a['argv'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90);a.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,duration_seconds=time.monotonic()-t);commands.append(a);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  if p.returncode:raise RuntimeError('probe tests failed; see commands/tests')
  success=True
 except Exception as e:receipt['error']=repr(e);(out/'failure.log').write_text(traceback.format_exc())
 finally:
  if started:run(['pg_ctl','-D',data,'-m','immediate','-w','stop'],check=False)
  if (scratch/'postgres.log').exists():shutil.copyfile(scratch/'postgres.log',out/'postgres.log')
  stopped=not (data/'postmaster.pid').exists();shutil.rmtree(scratch);receipt.update(success=success,finished_utc=utc(),cleanup={'owned_cluster_stopped':stopped,'owned_scratch_removed':not scratch.exists(),'tcp_listener_opened':False,'other_processes_touched':False});(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
 return 0 if success else 1
if __name__=='__main__':sys.exit(main())
