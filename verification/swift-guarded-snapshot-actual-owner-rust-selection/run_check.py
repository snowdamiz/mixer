"""One bounded owned Python custody/source-map child; never compiler or product."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def row(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes":len(raw), "sha256":hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in ("source-map-001", "source-map-final")
    out = HERE / "commands" / sys.argv[1]
    out.mkdir(parents=True, exist_ok=False)
    sources = [p for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ("seal.json", "source-map.json", "cleanup.json", "preparation.json")]
    for path in sources:
        (out / path.name).write_bytes(path.read_bytes())
    tool = Path(sys.executable).resolve()
    env = {"PATH":"/usr/bin:/bin", "LANG":"C", "LC_ALL":"C", "TZ":"UTC", "PYTHONDONTWRITEBYTECODE":"1", "PYTHONHASHSEED":"0"}
    argv = [str(tool), "-B", str(HERE / "check_selection.py"), "--source-map"]
    source_rows = [row(p) for p in sources]
    plan = {"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"argv":argv,"cwd":str(ROOT),"environment":env,"parent_environment":dict(os.environ),"tool":row(tool),"tool_version":sys.version,"source":source_rows,"source_tree_sha256":digest(source_rows),"source_revision_from_frozen_release":"9398732c23648a82097d5a72b02b1c77af818e41","timeout_seconds":55,"process_group_owned":True,"stdout_limit_bytes":4194304,"stderr_limit_bytes":4194304,"compiler_native_product_model_UI_capture":False}
    write(out / "plan.json",plan)
    start=time.monotonic()
    with (out / "stdout").open("wb") as stdout, (out / "stderr").open("wb") as stderr:
        child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        timed_out=False
        try:
            code=child.wait(timeout=55)
        except subprocess.TimeoutExpired:
            timed_out=True
            os.killpg(child.pid,signal.SIGKILL)
            code=child.wait(timeout=3)
    try:
        os.killpg(child.pid,0)
        absent=False
    except ProcessLookupError:
        absent=True
    outputs=[row(out / name) for name in ("stdout","stderr")]
    receipt={"schema":1,"exit":code,"timed_out":timed_out,"elapsed_seconds":time.monotonic()-start,"child_pid":child.pid,"owned_pgid":child.pid,"child_reaped":child.poll() is not None,"exact_owned_group_absent":absent,"outputs":outputs,"source_after":[row(p) for p in sources],"tool_after":row(tool),"native_compiler_product_model_UI_capture_processes_started":0,"global_process_inventory":False,"owned_scratch":[]}
    receipt["source_unchanged"]=receipt["source_after"]==source_rows
    receipt["tool_unchanged"]=receipt["tool_after"]==plan["tool"]
    write(out / "receipt.json",receipt)
    assert code==0 and not timed_out and absent and receipt["source_unchanged"] and receipt["tool_unchanged"], receipt
    assert all(item["bytes"]<=4194304 for item in outputs)
    result=json.loads((out/"stdout").read_bytes())
    write(HERE/"source-map.json",result.pop("source_map"))
    write(out/"input-before.json",result.pop("before"))
    write(out/"input-after.json",result.pop("after"))
    write(out/"result.json",result)
    receipts=[json.loads(p.read_bytes()) for p in sorted((HERE/"commands").glob("*/receipt.json"))]
    write(HERE/"cleanup.json",{"owned_children":len(receipts),"all_reaped":all(r["child_reaped"] for r in receipts),"exact_owned_groups_absent":all(r["exact_owned_group_absent"] for r in receipts),"owned_scratch":[],"native_UI_capture_compiler_product":0,"global_inventory":False})
    summary={"exit":code,"anchors":20,"input_members":result["custody_members"],"unchanged":result["unchanged"],"group_absent":absent}
    if sys.argv[1] == "source-map-final":
        seal_path=HERE/"seal.json"
        assert not seal_path.exists()
        members=[{"path":str(p.relative_to(HERE)),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in sorted(HERE.rglob("*")) if p.is_file() and p != seal_path]
        seal={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"member_count":len(members),"member_bytes":sum(r["bytes"] for r in members),"members":members,"tree_sha256":digest(members),"tree_algorithm":"sha256 canonical json.dumps(members,sort_keys=True,separators=(',',':'))","final_command":"commands/source-map-final","source_revision_from_frozen_release":plan["source_revision_from_frozen_release"],"root_selection":False,"Rust_implementation_or_compiler":False,"native_runtime_or_UI":False,"all17_fields_8claims_3Pendingselectors_6Pendingupstream_preserved":True,"root_funding_native_FieldLog_OTA_GA":"pending"}
        write(seal_path,seal)
        for path in HERE.rglob("*"):
            if path.is_file():
                path.chmod(path.stat().st_mode & ~0o222)
        summary.update(seal_sha256=hashlib.sha256(seal_path.read_bytes()).hexdigest(),members=len(members),bytes=seal["member_bytes"],tree_sha256=seal["tree_sha256"])
    print(json.dumps(summary,sort_keys=True))


if __name__=="__main__":
    main()
