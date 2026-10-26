"""Retain read-only CLI output without displaying raw artifact bytes."""
import datetime,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def digest(b):return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
def capture(name,argv,stdout_file=None):
    assert not (ROOT/(name+".command.json")).exists(), "One-shot capture name already used"
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r=subprocess.run(argv,cwd=REPO,capture_output=True,timeout=60)
    file=stdout_file or name+".stdout"
    (ROOT/file).write_bytes(r.stdout); (ROOT/(name+".stderr")).write_bytes(r.stderr)
    record={"started_utc":start,"completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"argv":argv,"cwd":str(REPO),"exit_code":r.returncode,"stdout_file":file,"stdout":digest(r.stdout),"stderr":digest(r.stderr),"scope":"Read-only CLI data collection; no artifact execution"}
    (ROOT/(name+".command.json")).write_text(json.dumps(record,indent=2)+"\n")
    r.check_returncode(); return r.stdout
if __name__=="__main__":
    payload=capture(sys.argv[1],sys.argv[2:]);print(json.dumps({"capture":sys.argv[1],**digest(payload)}))
