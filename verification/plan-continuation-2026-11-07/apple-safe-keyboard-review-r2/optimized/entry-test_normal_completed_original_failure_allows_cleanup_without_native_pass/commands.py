"""Bounded commands; unknown custody is sticky, including exceptional exits."""
import hashlib, json, os, selectors, signal, subprocess, time
from pathlib import Path
from holds import HELD
LIMIT = 4*1024*1024
DISPATCH_SECONDS = 950

def digest(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value):
    with Path(path).open('x') as f: json.dump(value, f, indent=2, sort_keys=True); f.write('\n')

class Commands:
    def __init__(self, directory):
        self.directory=Path(directory); self.directory.mkdir(exist_ok=True)
        self.total=0; self.events=[]; self.unresolved=False
    def run(self, label, argv, timeout=45, *, operation='command'):
        if self.unresolved: raise RuntimeError('Prior command custody unresolved; no further commands')
        if operation not in ('command','native-dispatch'): raise ValueError('Unknown operation')
        native=operation=='native-dispatch'
        if not (timeout==DISPATCH_SECONDS if native else 0 < timeout <= 120):
            raise ValueError('Deadline outside bound')
        started=time.monotonic(); streams={'stdout':bytearray(),'stderr':bytearray()}; eof={k:False for k in streams}
        row=dict(argv=argv,argvSHA256=digest(json.dumps(argv,separators=(',',':')).encode()),
                 executableSHA256=digest(Path(argv[0]).resolve().read_bytes()),cwd=os.getcwd(),
                 operation=operation,timeoutSeconds=timeout,reaped=False,ownedGroupAbsent=False,
                 exitCode=None,failure=None,signals=[],streams={},unknownCustody=True)
        p=None; sel=None; termination=None; error=None
        # Popen itself can raise after acquisition: never infer no child from that exception.
        self.unresolved=True
        try:
            p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer'})
            row.update(pid=p.pid,pgid=p.pid)
            if p.pid in HELD: raise RuntimeError('Unexpected held PID collision; no probing/signalling')
            sel=selectors.DefaultSelector()
            for name,pipe in [('stdout',p.stdout),('stderr',p.stderr)]:
                os.set_blocking(pipe.fileno(),False); sel.register(pipe,selectors.EVENT_READ,name)
            while True:
                # Reap before signals: Darwin can return EPERM for a zombie-only group.
                if p.poll() is not None:
                    p.wait(); row.update(reaped=True,exitCode=p.returncode)
                now=time.monotonic()
                if row['failure'] is None and now-started>=timeout: row['failure']='deadline'
                if row['failure'] and termination is None:
                    try: os.killpg(p.pid,signal.SIGTERM); row['signals'].append('TERM')
                    except ProcessLookupError: pass
                    termination=now
                if termination is not None and now-termination>=2 and 'KILL' not in row['signals']:
                    try: os.killpg(p.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    row['signals'].append('KILL')
                for key,_ in sel.select(0.02):
                    chunk=os.read(key.fileobj.fileno(),65536); name=key.data
                    if not chunk:
                        eof[name]=True; sel.unregister(key.fileobj); key.fileobj.close(); continue
                    room=min(LIMIT-len(streams[name]),32*1024*1024-self.total)
                    retained=chunk[:max(0,room)]; streams[name].extend(retained); self.total+=len(retained)
                    if len(retained)!=len(chunk): row['failure']=row['failure'] or 'output-limit'
                if row['reaped'] and all(eof.values()): break
                if termination is not None and now-termination>=5: break
            if not row['reaped'] and p.poll() is not None:
                p.wait(); row.update(reaped=True,exitCode=p.returncode)
            if row['reaped']:
                try: os.killpg(p.pid,0)
                except ProcessLookupError: row['ownedGroupAbsent']=True
        except BaseException as exc:
            error=exc; row['exception']=dict(type=type(exc).__name__,message=str(exc))
        finally:
            # Local descriptors only. No poll, wait, signal, AX or new child after an exception.
            try:
                if sel is not None: sel.close()
                if p is not None:
                    for pipe in (p.stdout,p.stderr):
                        if pipe is not None and not pipe.closed: pipe.close()
                row['elapsedSeconds']=time.monotonic()-started
            except BaseException as exc:
                error=error or exc; row['localCleanupException']=str(exc)
            terminal=row['reaped'] and row['ownedGroupAbsent'] and all(eof.values())
            row['nestedCustodyUnknown']=native and bool(error or row['failure'] or row['exitCode']!=0 or not terminal)
            row['unknownCustody']=bool(error or not terminal or row['nestedCustodyUnknown'])
            try:
                for name,raw in streams.items():
                    row['streams'][name]=dict(bytes=len(raw),sha256=digest(raw),eof=eof[name])
                    (self.directory/(label+'.'+name)).write_bytes(raw)
                write(self.directory/(label+'.command.json'),row)
            except BaseException as exc:
                row['unknownCustody']=True; row['receiptException']=str(exc); error=error or exc
                # Best effort exception receipt; a failed primary write always retains the latch.
                try: write(self.directory/(label+'.exception.json'),row)
                except BaseException: pass
            self.events.append(row)
            self.unresolved=row['unknownCustody']
        if error is not None: raise error
        if row['failure'] or self.unresolved or row['exitCode']:
            raise RuntimeError('Command failed or custody unresolved: '+label)
        try: return bytes(streams['stdout']).decode()
        except BaseException:
            self.unresolved=True
            raise
