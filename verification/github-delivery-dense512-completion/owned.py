"""Fresh finite Git/GitHub custody for this one selected delivery only."""
from datetime import datetime, timezone
import hashlib, json, os, selectors, signal, subprocess, sys, time
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def now(): return datetime.now(timezone.utc).isoformat()
def save(name, value):
    with (OUT / name).open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')
def row(path):
    assert path.is_file() and not path.is_symlink(), path
    b=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
def wrapper():
    admission, gate = int(sys.argv[2]), int(sys.argv[3])
    payload={'pid':os.getpid(), 'pgid':os.getpgrp(), 'sid':os.getsid(0)}
    os.write(admission, json.dumps(payload).encode()+b'\n'); os.close(admission)
    admitted=os.read(gate, 1); os.close(gate)
    if admitted != b'1': raise SystemExit(125)
    os.execvpe(sys.argv[4], sys.argv[4:], os.environ)
class Commands:
    def __init__(self, seconds, count, prefix):
        self.deadline=time.monotonic()+seconds; self.maximum=count; self.prefix=prefix; self.records=[]
    def run(self, name, argv, seconds=25):
        assert len(self.records)<self.maximum and argv[0] in ('git','gh')
        if argv[0]=='git': argv=['git','-c','gc.auto=0','-c','maintenance.auto=false',*argv[1:]]
        remaining=self.deadline-time.monotonic(); assert remaining>12
        timeout=min(seconds,remaining-10); label=self.prefix+name; start=time.monotonic()
        ar,aw=os.pipe(); gr,gw=os.pipe()
        child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--owned-exec',str(aw),str(gr),*argv],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            start_new_session=True,pass_fds=(aw,gr))
        os.close(aw); os.close(gr)
        save(label+'.started.json',{'at':now(),'argv':argv,'ownedPID':child.pid,'timeoutSeconds':timeout,'targetReleased':False})
        admitted=False; timed=False; signals=[]; failure=None; identity=None
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(ar,selectors.EVENT_READ)
                if not selector.select(5): raise RuntimeError('owned admission deadline')
                data=os.read(ar,4096)
            identity=json.loads(data)
            assert identity=={'pid':child.pid,'pgid':child.pid,'sid':child.pid}
            assert os.getpgid(child.pid)==child.pid and os.getsid(child.pid)==child.pid
            save(label+'.admission.json',{'at':now(),'argv':argv,'identity':identity,'parentObservedPGID':child.pid,'parentObservedSID':child.pid,'targetReleasedOnlyAfterPersistedAdmission':True})
            admitted=True; os.write(gw,b'1'); os.close(gw); gw=None
            stdout,stderr=child.communicate(timeout=timeout)
        except BaseException as exc:
            timed=isinstance(exc,subprocess.TimeoutExpired); failure=repr(exc)
            if gw is not None: os.close(gw); gw=None
            for sig in (signal.SIGTERM,signal.SIGKILL):
                try:
                    if admitted: os.killpg(child.pid,sig)
                    else: child.send_signal(sig)
                    signals.append(int(sig))
                except ProcessLookupError: pass
                try: stdout,stderr=child.communicate(timeout=2); break
                except subprocess.TimeoutExpired: continue
            else: raise RuntimeError('owned command EOF unresolved; no further command')
        finally:
            os.close(ar)
            if gw is not None: os.close(gw)
        try: os.killpg(child.pid,0); absent=False
        except ProcessLookupError: absent=True
        assert len(stdout)+len(stderr)<=2*1024*1024
        for suffix,data in (('stdout',stdout),('stderr',stderr)):
            assert b'X-Amz-Signature' not in data and b'X-Goog-Signature' not in data
            with (OUT/(label+'.'+suffix)).open('xb') as f: f.write(data)
        result={'at':now(),'argv':argv,'exit':child.returncode,'admitted':admitted,'identity':identity,
            'timedOut':timed,'failure':failure,'elapsedSeconds':time.monotonic()-start,'ownedPID':child.pid,
            'ownedPGID':identity['pgid'] if identity else None,'directChildReaped':child.returncode is not None,
            'ownedGroupAbsent':absent,'stdoutEOF':True,'stderrEOF':True,'signals':signals,
            'stdout':row(OUT/(label+'.stdout')),'stderr':row(OUT/(label+'.stderr'))}
        save(label+'.command.json',result)
        self.records.append({'name':label,**{k:result[k] for k in ('exit','admitted','timedOut','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF')}})
        assert admitted and not timed and failure is None and absent and child.returncode==0,label
        return stdout
if __name__=='__main__':
    assert sys.argv[1]=='--owned-exec'
    wrapper()
