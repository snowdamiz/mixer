"""Record only this packet's bounded host checks; no target transport."""
from pathlib import Path
import datetime, hashlib, json, os, platform, selectors, subprocess, sys, time
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
name,kind,*args=sys.argv[1:]
argv={'custody-controls':[sys.executable,'-m','unittest','discover','-s',str(P),'-p','test_custody.py','-v'],
      'capture':[sys.executable,str(P/'custody.py'),*args],
      'literal-audit':[sys.executable,str(P/'literal_audit.py')]}[kind]
D=P/'commands'/name;D.mkdir(parents=True,exist_ok=False)
base=json.loads((P/'baseline-source-manifest.json').read_bytes())
live={n:sha((R/'vm'/n).read_bytes()) for n in base};assert live==base
before={str(f.relative_to(P)):sha(f.read_bytes()) for f in P.glob('*.py')}
command={'argv':argv,'cwd':str(R),'timeoutSeconds':120,'captureLimitPerStream':1048576,
    'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
    'tool':{'path':sys.executable,'sha256':sha(Path(sys.executable).read_bytes()),'version':sys.version},
    'platform':platform.platform(),'sourceHashes':before}
(D/'command.json').write_text(json.dumps(command,sort_keys=True,indent=2)+'\n')
process=subprocess.Popen(argv,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sel=selectors.DefaultSelector();sel.register(process.stdout,selectors.EVENT_READ,'stdout');sel.register(process.stderr,selectors.EVENT_READ,'stderr')
data={'stdout':bytearray(),'stderr':bytearray()};started=time.monotonic();status='exited'
while sel.get_map():
    if time.monotonic()-started>120:status='timeout';process.kill()
    for key,_ in sel.select(.1):
        block=os.read(key.fileobj.fileno(),65536)
        if not block:sel.unregister(key.fileobj);continue
        out=data[key.data]
        if len(out)+len(block)>1048576:status='output-cap';process.kill();block=block[:1048576-len(out)]
        out.extend(block)
code=process.wait(timeout=5)
for n,b in data.items():(D/(n+'.txt')).write_bytes(b)
after={str(f.relative_to(P)):sha(f.read_bytes()) for f in P.glob('*.py')}
live_after={n:sha((R/'vm'/n).read_bytes()) for n in base}
result={'status':status,'exitCode':code,'elapsedSeconds':time.monotonic()-started,'hostSourceUnchanged':before==after,'live132Unchanged':live_after==base,
    'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in data.items()}}
(D/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result));print(data['stdout'].decode(errors='replace')[-5000:]);print(data['stderr'].decode(errors='replace')[-5000:])
sys.exit(code or (0 if result['hostSourceUnchanged'] and result['live132Unchanged'] else 1))
