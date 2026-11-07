"""Fresh fixture-context-v4 delivery custody; prior helpers and admissions are read-only. Independent v4 process groups and persisted admission are required."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, selectors, signal, subprocess, time
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def now(): return datetime.now(timezone.utc).isoformat()
def save(name,value):
    with (OUT/name).open('x') as f: json.dump(value,f,indent=2); f.write('\n')
def row(path):
    assert path.is_file() and not path.is_symlink(),str(path)
    b=path.read_bytes();return {'path':str(path.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
class Commands:
    def __init__(self,seconds,count,prefix):
        assert 0<seconds<=240 and 0<count<=25
        self.deadline=time.monotonic()+seconds;self.maximum=count;self.prefix=prefix;self.records=[]
    def run(self,name,argv,seconds=25):
        assert len(self.records)<self.maximum and argv[0] in ('git','gh')
        assert self.deadline-time.monotonic()>8
        if argv[0]=='git': argv=['git','-c','gc.auto=0','-c','maintenance.auto=false',*argv[1:]]
        label=self.prefix+name; budget=min(seconds,self.deadline-time.monotonic()-7)
        assert not (OUT/(label+'.admission.json')).exists(),'No command replay'
        save(label+'.admission.json',{'at':now(),'argv':argv,'cwd':str(ROOT),'activeSeconds':budget,'cleanupSeconds':6,'streamCapEachBytes':1048576,'sessionCommandLimit':self.maximum,'commandOrdinal':len(self.records)+1,'freshOwnedGroupRequired':True})
        start=time.monotonic();child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        save(label+'.started.json',{'at':now(),'ownedPID':child.pid,'ownedPGID':child.pid,'argv':argv})
        sel=selectors.DefaultSelector();streams={'stdout':bytearray(),'stderr':bytearray()}; eof={'stdout':False,'stderr':False}
        for key,pipe in (('stdout',child.stdout),('stderr',child.stderr)):
            os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,key)
        stop=None; signals=[]; cleanup_deadline=None
        def absent():
            try:os.killpg(child.pid,0);return False
            except ProcessLookupError:return True
        while True:
            elapsed=time.monotonic()-start
            if stop is None and elapsed>=budget:stop='deadline'
            if stop is not None and cleanup_deadline is None:
                cleanup_deadline=time.monotonic()+6
                try:os.killpg(child.pid,signal.SIGTERM);signals.append(int(signal.SIGTERM))
                except ProcessLookupError:pass
            if cleanup_deadline is not None and time.monotonic()>=cleanup_deadline-3 and int(signal.SIGKILL) not in signals:
                try:os.killpg(child.pid,signal.SIGKILL);signals.append(int(signal.SIGKILL))
                except ProcessLookupError:pass
            for event,_ in sel.select(.05):
                data=os.read(event.fileobj.fileno(),65536);key=event.data
                if not data:sel.unregister(event.fileobj);event.fileobj.close();eof[key]=True
                else:
                    remaining=1048576-len(streams[key]);streams[key].extend(data[:max(remaining,0)])
                    if len(data)>remaining:stop=stop or 'stream-cap'
            code=child.poll()
            if code is not None and all(eof.values()):
                if absent():break
                stop=stop or 'surviving-owned-group'
            if cleanup_deadline is not None and time.monotonic()>=cleanup_deadline:break
        code=child.poll();group_absent=absent();sel.close()
        for key,data in streams.items():
            with (OUT/(label+'.'+key)).open('xb') as f:f.write(data)
        result={'at':now(),'argv':argv,'exit':code,'stopReason':stop,'elapsedSeconds':time.monotonic()-start,'ownedPID':child.pid,'ownedPGID':child.pid,'directChildReaped':code is not None,'ownedGroupAbsent':group_absent,'stdoutEOF':eof['stdout'],'stderrEOF':eof['stderr'],'signals':signals,'stdout':row(OUT/(label+'.stdout')),'stderr':row(OUT/(label+'.stderr'))}
        save(label+'.command.json',result);self.records.append({'name':label,**{k:result[k] for k in ('exit','stopReason','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF')}})
        assert stop is None and code==0 and group_absent and all(eof.values()),label
        return bytes(streams['stdout'])
