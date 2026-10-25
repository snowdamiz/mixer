#!/usr/bin/env python3
import pathlib,os,json,signal,subprocess,hashlib,time,shutil,sys,datetime
HERE=pathlib.Path(__file__).resolve().parent
COPY=HERE/'scratch/verification/hosted-worker-transport-v2'
ENV={'PATH':os.environ['PATH'],'LANG':'C.UTF-8','ERL_CRASH_DUMP':'/dev/null','ERL_CRASH_DUMP_SECONDS':'0'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,args,timeout=40):
 original=name;attempt=1
 while (HERE/(name+'.stdout')).exists():
  attempt+=1;name=original+'-attempt-'+str(attempt)
 started=time.monotonic();p=subprocess.Popen(args,cwd=HERE,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed_out=False
 try: out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
 finally:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 for suffix,data in [('stdout',out),('stderr',err)]: (HERE/(name+'.'+suffix)).write_bytes(data)
 row={'name':name,'arguments':args,'cwd':str(HERE),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_ms':round((time.monotonic()-started)*1000),'exit_code':p.returncode,'timed_out':timed_out,'stdout':name+'.stdout','stdout_sha256':sha(HERE/(name+'.stdout')),'stderr':name+'.stderr','stderr_sha256':sha(HERE/(name+'.stderr')),'owned_command_group_disposed':True}
 rows=json.loads((HERE/'commands.json').read_text()) if (HERE/'commands.json').exists() else []
 rows.append(row);(HERE/'commands.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');print(json.dumps(row),flush=True)
 return row
prefix=[shutil.which('elixir'),'--erl','+S 2:2 +SDcpu 1 +SDio 1']
for d in ['mint','jason','hpax']:prefix+=['-pa',str(COPY/'locked/hosted/_build/test/lib'/d/'ebin')]
if __name__=='__main__':
 if sys.argv[1]=='independent':
  name=sys.argv[2];run('independent-'+name,prefix+[str(HERE/'review_harness.exs'),'independent',name])
 elif sys.argv[1]=='replay':
  jobs=[('elixir-version',[shutil.which('elixir'),'--version']),('openssl-version',[shutil.which('openssl'),'version']),('node-version',[shutil.which('node'),'--version']),('python-version',[sys.executable,'--version']),('baseline',prefix+[str(HERE/'review_harness.exs'),'baseline'])]
  names=sorted(p.name.removesuffix('_test.exs') for p in (COPY/'candidate/test/fault_cases').glob('*_test.exs'));assert len(names)==18
  jobs += [('fault-'+n,prefix+[str(HERE/'review_harness.exs'),'fault',n]) for n in names]
  jobs += [('generate-vectors',prefix+['-pa',str(HERE/'build/test'),str(COPY/'generate_vectors.exs')]),('check-vectors',[shutil.which('node'),str(COPY/'check_vectors.js')]),('production-exports',prefix+[str(COPY/'production_exports.exs')])]
  for name,args in jobs:
   assert run(name,args)['exit_code']==0,name
