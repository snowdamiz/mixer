"""Snapshot and execute only a root-selected immutable framing library freeze."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OWN = pathlib.Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(65536), b""):
            h.update(block)
    return h.hexdigest()

def execute(name, argv, out, env=None):
    command={"argv":list(map(str,argv)), "cwd":str(ROOT),
             "at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "environment_overrides":{} if env is None else {key:env[key] for key in ["MIXER_REVIEW_SCRATCH","MIXER_ANALYZER_LIBRARY_TEST_SCRATCH","MIXER_ANALYZER_LIBRARY_HISTORICAL"] if key in env}}
    (out/(name+".command.json")).write_text(json.dumps(command,indent=2)+"\n")
    with (out/(name+".stdout")).open("wb") as stdout, (out/(name+".stderr")).open("wb") as stderr:
        result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    row={"command":command,"exit":result.returncode,
         "stdout_sha256":sha(out/(name+".stdout")),"stderr_sha256":sha(out/(name+".stderr"))}
    (out/(name+".result.json")).write_text(json.dumps(row,indent=2)+"\n")
    return row

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--packet",required=True)
    parser.add_argument("--source",required=True)
    parser.add_argument("--seal",required=True)
    parser.add_argument("--attempt",required=True)
    parser.add_argument("--private-tests")
    args=parser.parse_args()
    packet=ROOT/args.packet
    seal=packet/"seal.json"
    assert sha(seal)==args.seal
    assert seal.with_suffix(".sha256").read_text().split()[0]==args.seal
    members=json.loads(seal.read_bytes())["members"]
    before=[]
    for row in members:
        source=ROOT/row["path"]
        assert source.stat().st_size==row["bytes"] and sha(source)==row["sha256"],row
        before.append(row)
    source_path=ROOT/args.source
    assert any(row["path"]==args.source for row in members),"source is not sealed"
    frozen=OWN/"snapshots"/args.attempt
    frozen.mkdir(parents=True,exist_ok=False)
    for row in members:
        destination=frozen/row["path"]
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/row["path"],destination)
        assert sha(destination)==row["sha256"]
    shutil.copyfile(seal,frozen/"producer-seal.json")
    shutil.copyfile(seal.with_suffix(".sha256"),frozen/"producer-seal.sha256")
    out=OWN/"commands"/args.attempt
    out.mkdir(parents=True,exist_ok=False)
    tests=out/"executed-independent-tests.rs"
    tests.write_bytes((OWN/"independent_tests.rs").read_bytes())
    inputs=out/"inputs"
    inputs.mkdir()
    product=inputs/"framing.rs"
    product.write_bytes(source_path.read_bytes())
    test_source=frozen/args.packet/"tests"/"fixture_tests.rs"
    if test_source.exists():
        (out/"tests").mkdir()
        shutil.copyfile(test_source,out/"tests"/"fixture_tests.rs")
    if args.private_tests:
        extension=ROOT/args.private_tests
        product.write_bytes(product.read_bytes()+b"\n"+extension.read_bytes())
    scratch=OWN/"scratch"/args.attempt
    scratch.mkdir(parents=True,exist_ok=False)
    scratch_marker=scratch/"ownership.json"
    scratch_marker.write_text(json.dumps({"owner":"/root/swift_analyzer_framing_review","path":str(scratch),"remove_only_this_owned_tree":True})+"\n")
    rustc=pathlib.Path(subprocess.check_output(["rustup","which","rustc"],cwd=ROOT,text=True).strip()).resolve()
    rows=[]
    rows.append(execute("rust-version",[rustc,"--version","--verbose"],out))
    rows.append(execute("python-version",[sys.executable,"--version"],out))
    binary=scratch/"independent-tests"
    rows.append(execute("compile",[rustc,"--edition=2021","--test","-Dwarnings","-O",tests,"-o",binary],out))
    if rows[-1]["exit"]==0:
        producer_scratch=scratch/"producer"
        producer_scratch.mkdir()
        env=dict(os.environ,MIXER_REVIEW_SCRATCH=str(scratch),
                 MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(producer_scratch),
                 MIXER_ANALYZER_LIBRARY_HISTORICAL=str(frozen/args.packet/"inputs"/"historical"))
        rows.append(execute("execute",[binary,"--test-threads=1","--nocapture"],out,env))
    after=[]
    for row in members:
        source=ROOT/row["path"]
        assert source.stat().st_size==row["bytes"] and sha(source)==row["sha256"],"producer changed during review: "+row["path"]
        after.append(row)
    result={"schema":1,"revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"producer_seal":args.seal,
            "producer_members":len(members),"quiescent_before_after":before==after,
            "executed_product_sha256":sha(product),"unmodified_product_source_sha256":sha(source_path),
            "test_source_sha256":sha(tests),"rustc_path":str(rustc),"rustc_sha256":sha(rustc),
            "commands":rows,"passed":all(row["exit"]==0 for row in rows),
            "scratch":str(scratch.relative_to(ROOT)),"scratch_cleanup_pending":True,
            "native_capture_target_process_discovery":False,"fullReplayAccepted":False,"storedPrefixValidated":False}
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"passed":result["passed"],"commands":len(rows),"producer_seal":args.seal,"members":len(members),"result":str((out/"result.json").relative_to(ROOT))}))
    return 0 if result["passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
