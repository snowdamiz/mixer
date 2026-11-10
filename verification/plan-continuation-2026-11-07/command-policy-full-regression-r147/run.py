import os,subprocess,signal,json,time,re,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent;c=json.loads((p/'selection.json').read_text());vm=Path(c['vm']);owned=Path(c['ownedRoot']);env=os.environ.copy();env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env['CARGO_TARGET_DIR']=str(owned/'target');records=[];started=time.monotonic()
def run(name,argv):
 r={'name':name,'argv':argv,'cwd':str(vm)};records.append(r);t=time.monotonic()
 with (p/(name+'.stdout')).open('wb') as out,(p/(name+'.stderr')).open('wb') as err:
  child=subprocess.Popen(argv,cwd=vm,env=env,stdout=out,stderr=err,start_new_session=True);r.update(pid=child.pid,pgid=child.pid);(p/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
  try:r['exitCode']=child.wait(timeout=600-(time.monotonic()-started))
  except subprocess.TimeoutExpired:r['timeout']=True;os.killpg(child.pid,signal.SIGTERM);r['exitCode']=child.wait(timeout=10)
 try:os.killpg(child.pid,0);r['groupAbsent']=False
 except ProcessLookupError:r['groupAbsent']=True
 except PermissionError:r['groupAbsent']=None
 r.update(seconds=time.monotonic()-t,outputsClosed=out.closed and err.closed);(p/'commands.json').write_text(json.dumps(records,indent=2)+'\n');print(name,r['exitCode'],round(r['seconds'],3),r['groupAbsent'],flush=True)
 assert r['exitCode']==0 and r['groupAbsent'] is True,name
try:
 cargo='/opt/homebrew/opt/rustup/bin/cargo';base=[cargo,'test','--offline','--locked','--jobs','2','--all-features','--lib','--tests']
 run('all-feature-debug',base+['--','--test-threads=2'])
 run('all-feature-release',base+['--release','--','--test-threads=2'])
 summaries={}
 for mode in ['debug','release']:
  raw=(p/('all-feature-'+mode+'.stdout')).read_text();rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',raw);summaries[mode]={'passed':sum(int(x[0]) for x in rows),'failed':sum(int(x[1]) for x in rows),'ignored':sum(int(x[2]) for x in rows),'summaries':len(rows)}
 result={'passed':True,'modes':summaries,'sourceUnchanged':all(hashlib.sha256((vm/k).read_bytes()).hexdigest()==v for k,v in c['source'].items())}
except Exception as e:result={'passed':False,'error':repr(e)}
finally:result['seconds']=time.monotonic()-started;(p/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
