"""Retain read-only CLI output without displaying raw artifact bytes."""
import datetime,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def digest(b):return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
def capture(name,argv,stdout_file=None):
    assert not (ROOT/(name+".command.json")).exists(), "One-shot capture name already used"
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        r=subprocess.run(argv,cwd=REPO,capture_output=True,timeout=60)
        out,err,code,timed_out=r.stdout,r.stderr,r.returncode,False
    except subprocess.TimeoutExpired as e:
        out,err,code,timed_out=e.stdout or b'',e.stderr or b'',None,True
    file=stdout_file or name+".stdout"
    (ROOT/file).write_bytes(out); (ROOT/(name+".stderr")).write_bytes(err)
    record={"started_utc":start,"completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"argv":argv,"cwd":str(REPO),"exit_code":code,"timed_out":timed_out,"stdout_file":file,"stdout":digest(out),"stderr":digest(err),"scope":"Read-only CLI data collection or reviewed data-only auditor; no artifact extraction or execution"}
    (ROOT/(name+".command.json")).write_text(json.dumps(record,indent=2)+"\n")
    assert not timed_out, 'Command timed out; partial outputs retained'
    r.check_returncode(); return out
if __name__=="__main__":
    payload=capture(sys.argv[1],sys.argv[2:]);print(json.dumps({"capture":sys.argv[1],**digest(payload)}))
