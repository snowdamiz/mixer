import hashlib,json,os,signal,subprocess,time
from pathlib import Path
p=Path(__file__).resolve().parent;c=json.loads((p/'selection.json').read_text());vm=Path(c['vm']);owned=Path(c['ownedRoot']);env=os.environ.copy();env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env['CARGO_TARGET_DIR']=str(owned/'target');records=[];started=time.monotonic()
module='/Users/andreyyurlov/.t3/userdata/mixer-taskeditor-r106-pferm211/wasm/release/FieldLogTaskEditorBurstAndSaveDifferential.wasm'
assert hashlib.sha256(Path(module).read_bytes()).hexdigest()=='24c0fb1bb38f64ad254ca89543b7ca1328bc8bdf83d198c9e84ba127d9fb7d85'
env.update(MIXER_R110_MODULE=module,MIXER_R110_STDOUT=str(p/'guest.stdout'),MIXER_R110_STDERR=str(p/'guest.stderr'))
def run(name,argv,limit):
 r={'name':name,'argv':argv,'cwd':str(vm)};records.append(r);t=time.monotonic()
 with (p/(name+'.stdout')).open('wb') as out,(p/(name+'.stderr')).open('wb') as err:
  child=subprocess.Popen(argv,cwd=vm,env=env,stdout=out,stderr=err,start_new_session=True);r.update(pid=child.pid,pgid=child.pid);(p/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
  try:r['exitCode']=child.wait(timeout=min(limit,240-(time.monotonic()-started)))
  except subprocess.TimeoutExpired:
   r['timeout']=True;os.killpg(child.pid,signal.SIGKILL);r['exitCode']=child.wait(timeout=10)
 try:os.killpg(child.pid,0);r['groupAbsent']=False
 except ProcessLookupError:r['groupAbsent']=True
 except PermissionError:r['groupAbsent']=None
 r.update(seconds=time.monotonic()-t,outputFilesClosed=out.closed and err.closed);(p/'commands.json').write_text(json.dumps(records,indent=2)+'\n');print(name,r['exitCode'],round(r['seconds'],3),r['groupAbsent'],flush=True)
 assert r['exitCode']==0 and r['groupAbsent'] is True,name
try:
 cargo='/opt/homebrew/opt/rustup/bin/cargo';opts=['--offline','--locked','--jobs','2','--release','--features','experimental-swift-reactor']
 run('focused-regressions',[cargo,'test',*opts,'--test','experimental_swift_command','--test','swift_reactor_validation','--test','swift_reactor_validation_allocations','--test','swift_wasi','--test','swift_wasi_allocations','--','--test-threads=1'],120)
 run('clippy',[cargo,'clippy','--offline','--locked','--jobs','2','--lib','--features','experimental-swift-reactor','--','-D','warnings'],60)
 run('example-build',[cargo,'build',*opts,'--example','taskeditor_owned_command'],60)
 run('actual-taskeditor',[str(owned/'target/release/examples/taskeditor_owned_command')],45)
 raw=(p/'guest.stdout').read_bytes();assert len(raw)==439 and hashlib.sha256(raw).hexdigest()=='3135cb2d45d78106ddda5675c763457df818085394e7c8c63c84ea210d903f22';assert (p/'guest.stderr').read_bytes()==b''
 result={'passed':True,'fullJSONByteIdentical':True,'bytes':439,'sha256':hashlib.sha256(raw).hexdigest(),'sourceUnchanged':all(hashlib.sha256((vm/k).read_bytes()).hexdigest()==v for k,v in c['source'].items())}
except Exception as e:result={'passed':False,'error':repr(e)}
finally:result['seconds']=time.monotonic()-started;(p/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
