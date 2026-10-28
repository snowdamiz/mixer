"""Fresh bounded delivery commands; only this delivery owns these groups."""
from datetime import datetime, timezone
import hashlib, json, os, signal, subprocess, time
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def now(): return datetime.now(timezone.utc).isoformat()
def save(name,value):
    with (OUT/name).open("x") as f: json.dump(value,f,indent=2); f.write("\n")
def row(path):
    assert path.is_file() and not path.is_symlink(), path
    b=path.read_bytes(); return {"path":str(path.relative_to(ROOT)),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
class Commands:
    def __init__(self,seconds,count,prefix):
        self.deadline=time.monotonic()+seconds; self.maximum=count; self.prefix=prefix; self.records=[]
    def run(self,name,argv,seconds=25):
        assert len(self.records)<self.maximum and argv[0] in ("git","gh")
        if argv[0]=="git": argv=["git","-c","gc.auto=0","-c","maintenance.auto=false",*argv[1:]]
        remaining=self.deadline-time.monotonic(); assert remaining>8
        label=self.prefix+name; start=time.monotonic()
        child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        save(label+".started.json",{"at":now(),"argv":argv,"ownedPID":child.pid,"ownedPGID":child.pid,"timeoutSeconds":min(seconds,remaining-6)})
        timed=False; signals=[]
        try: stdout,stderr=child.communicate(timeout=min(seconds,remaining-6))
        except subprocess.TimeoutExpired:
            timed=True
            for sig in (signal.SIGTERM,signal.SIGKILL):
                try: os.killpg(child.pid,sig); signals.append(int(sig))
                except ProcessLookupError: pass
                try: stdout,stderr=child.communicate(timeout=2); break
                except subprocess.TimeoutExpired: continue
            else: raise RuntimeError("owned command EOF not reached after bounded cleanup")
        try: os.killpg(child.pid,0); absent=False
        except ProcessLookupError: absent=True
        assert len(stdout)+len(stderr)<=2*1024*1024
        for suffix,data in (("stdout",stdout),("stderr",stderr)):
            with (OUT/(label+"."+suffix)).open("xb") as f:f.write(data)
        result={"at":now(),"argv":argv,"exit":child.returncode,"timedOut":timed,"elapsedSeconds":time.monotonic()-start,"ownedPID":child.pid,"ownedPGID":child.pid,"directChildReaped":child.returncode is not None,"ownedGroupAbsent":absent,"stdoutEOF":True,"stderrEOF":True,"signals":signals,"stdout":row(OUT/(label+".stdout")),"stderr":row(OUT/(label+".stderr"))}
        save(label+".command.json",result)
        self.records.append({"name":label,**{k:result[k] for k in ("exit","timedOut","directChildReaped","ownedGroupAbsent","stdoutEOF","stderrEOF")}})
        assert not timed and absent and child.returncode==0,label
        return stdout
