"""Bounded host commands: private groups, separate EOF, reaping and receipts."""
import hashlib, json, os, selectors, signal, subprocess, time
from pathlib import Path
HELD = {23663,20745,20770,20780,20817,20842,20851,20866,2424,2621}
LIMIT = 4*1024*1024

def digest(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value):
    with Path(path).open('x') as f: json.dump(value, f, indent=2, sort_keys=True); f.write('\n')

class Commands:
    def __init__(self, directory):
        self.directory=Path(directory); self.directory.mkdir(exist_ok=True)
        self.total=0; self.events=[]
    def run(self, label, argv, timeout=45):
        if not 0 < timeout <= 120: raise ValueError('Deadline outside bound')
        started=time.monotonic(); streams={'stdout':bytearray(),'stderr':bytearray()}; eof={k:False for k in streams}
        p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer'})
        if p.pid in HELD: raise RuntimeError('Unexpected held PID collision; no probing/signalling')
        sel=selectors.DefaultSelector()
        for name,pipe in [('stdout',p.stdout),('stderr',p.stderr)]:
            os.set_blocking(pipe.fileno(),False); sel.register(pipe,selectors.EVENT_READ,name)
        failure=None; sent=[]; termination=None
        while True:
            now=time.monotonic()
            if failure is None and now-started>=timeout: failure='deadline'
            if failure and termination is None:
                try: os.killpg(p.pid,signal.SIGTERM); sent.append('TERM')
                except ProcessLookupError: pass
                termination=now
            if termination is not None and now-termination>=2 and 'KILL' not in sent:
                try: os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                sent.append('KILL')
            for key,_ in sel.select(0.02):
                chunk=os.read(key.fileobj.fileno(),65536); name=key.data
                if not chunk:
                    eof[name]=True; sel.unregister(key.fileobj); key.fileobj.close(); continue
                room=min(LIMIT-len(streams[name]),32*1024*1024-self.total)
                retained=chunk[:max(0,room)]; streams[name].extend(retained); self.total+=len(retained)
                if len(retained)!=len(chunk): failure=failure or 'output-limit'
            if p.poll() is not None and all(eof.values()): break
            if termination is not None and now-termination>=5: break
        sel.close()
        for pipe in [p.stdout,p.stderr]:
            if not pipe.closed: pipe.close()
        reaped=p.poll() is not None
        if reaped: p.wait()
        try: os.killpg(p.pid,0); absent=False
        except ProcessLookupError: absent=True
        row=dict(argv=argv,argvSHA256=digest(json.dumps(argv,separators=(',',':')).encode()),
            executableSHA256=digest(Path(argv[0]).resolve().read_bytes()),cwd=os.getcwd(),pid=p.pid,pgid=p.pid,
            timeoutSeconds=timeout,elapsedSeconds=time.monotonic()-started,exitCode=p.returncode,
            failure=failure,reaped=reaped,ownedGroupAbsent=absent,signals=sent,streams={})
        for name,raw in streams.items():
            (self.directory/(label+'.'+name)).write_bytes(raw)
            row['streams'][name]=dict(bytes=len(raw),sha256=digest(raw),eof=eof[name])
        write(self.directory/(label+'.command.json'),row); self.events.append(row)
        if failure or not reaped or not absent or not all(eof.values()) or p.returncode:
            raise RuntimeError('Command failed or custody unresolved: '+label)
        return bytes(streams['stdout']).decode()
