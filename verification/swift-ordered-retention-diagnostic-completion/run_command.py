from pathlib import Path
import os,sys,json,hashlib,subprocess,datetime,time,selectors
P=Path(__file__).resolve().parent;R=P.parents[1];S=P/'.scratch';TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
def sha(b):return hashlib.sha256(b).hexdigest()
name,side,*args=sys.argv[1:];D=P/'commands'/name;D.mkdir(parents=True,exist_ok=False)
manifest=json.loads((P/(side+'-manifest.json')).read_text());before={n:sha((S/side/n).read_bytes()) for n in manifest};assert before==manifest
base=json.loads((P/'baseline-source-manifest.json').read_text());live={n:sha((R/'vm'/n).read_bytes()) for n in base};assert live==base
argv=[str(TOOL/'cargo'),'test','--offline','--release',*args]
overrides={'RUSTC':str(TOOL/'rustc'),'PATH':str(TOOL)+':'+os.environ['PATH'],'CARGO_NET_OFFLINE':'true','CARGO_BUILD_JOBS':'1','CARGO_TARGET_DIR':str(S/('build-'+side)),'TMPDIR':str(S/('tmp-'+side)/name)}
Path(overrides['TMPDIR']).mkdir(exist_ok=False)
command={'argv':argv,'cwd':str(S/side),'environmentOverrides':overrides,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeoutSeconds':240,'captureLimitPerStream':1048576,'sourceManifestSHA256':sha((P/(side+'-manifest.json')).read_bytes()),'liveManifestSHA256':sha((P/'baseline-source-manifest.json').read_bytes()),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'tools':{t:{'sha256':sha((TOOL/t).read_bytes()),'version':subprocess.check_output([str(TOOL/t),'--version'],text=True).strip()}for t in ['cargo','rustc']}}
(D/'command.json').write_text(json.dumps(command,indent=2)+'\n')
child=subprocess.Popen(argv,cwd=S/side,env={**os.environ,**overrides},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ,'stdout');sel.register(child.stderr,selectors.EVENT_READ,'stderr');data={'stdout':bytearray(),'stderr':bytearray()};status='exited';started=time.monotonic()
while sel.get_map():
 if time.monotonic()-started>240:status='timeout';child.kill()
 for key,_ in sel.select(0.1):
  block=os.read(key.fileobj.fileno(),65536)
  if not block:sel.unregister(key.fileobj);continue
  which=key.data
  if len(data[which])+len(block)>1048576:status='host-output-cap';child.kill();block=block[:1048576-len(data[which])]
  data[which].extend(block)
code=child.wait(timeout=5)
for n,b in data.items():(D/(n+'.txt')).write_bytes(b)
after={n:sha((S/side/n).read_bytes()) for n in manifest};liveafter={n:sha((R/'vm'/n).read_bytes()) for n in base}
result={'status':status,'exitCode':code,'elapsedSeconds':time.monotonic()-started,'sourceUnchanged':after==before,'live132Unchanged':liveafter==base,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in data.items()}}
(D/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));print(data['stdout'].decode(errors='replace')[-14000:]);print(data['stderr'].decode(errors='replace')[-14000:]);sys.exit(code if code else 0 if result['sourceUnchanged']and result['live132Unchanged']else 1)
