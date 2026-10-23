#!/usr/bin/env python3
"""Capture exact independent fixture bytes and focused feature preservation."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
VM=ROOT/"vm"
TARGET=VM/"target/stream-validation-verification"
ENV=dict(os.environ)
ENV["PATH"]="/opt/homebrew/opt/rustup/bin:"+ENV["PATH"]
ENV["CARGO_TARGET_DIR"]=str(TARGET)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
receipt={"schema":1,"commands":[],"scope":"Host native-only feature wiring and unchanged default regression; fixture encoding capture."}
def run(label, argv):
    p=subprocess.run(argv,cwd=VM,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/(label+".log");log.write_bytes(p.stdout)
    receipt["commands"].append({"argv":argv,"cwd":str(VM),"exit_status":p.returncode,"log":str(log.relative_to(ROOT)),"log_sha256":sha(log)})
    print(label+": "+str(p.returncode),flush=True)
    if p.returncode: raise RuntimeError(p.stdout[-4000:].decode(errors="replace"))
    return p.stdout
before={profile:sha(TARGET/profile/"libmixer_vm.a") for profile in ["debug","release"]}
for profile in ["debug","release"]:
    release=["--release"] if profile=="release" else []
    run(profile+"-native-only-focused",["cargo","test",*release,"--features","experimental-capability-native","--test","experimental_guest_ui_validation","--test","experimental_guest_ui_allocations","--","--nocapture"])
    run(profile+"-default-regression",["cargo","test",*release,"--no-default-features","--lib","--test","interpreter","--test","sessions"])
binary=TARGET/"debug/guest-ui-fixture-capture"
run("fixture-capture-build",["rustc","--edition","2021",str(OUT/"capture_fixture.rs"),"-o",str(binary)])
raw=run("fixture-capture-run",[str(binary)]).decode()
fixtures={}
for line in raw.splitlines():
    name,hexbytes=line.split()
    b=bytes.fromhex(hexbytes)
    fixtures[name]={"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
fixture_manifest={"schema":1,"builder":"vm/tests/guest_ui/fixture.rs","builder_sha256":sha(VM/"tests/guest_ui/fixture.rs"),
    "capture_source_sha256":sha(OUT/"capture_fixture.rs"),"fixtures":fixtures,
    "inventory":{"types":["()->i32","(i32)->i32","()->()","()->i64","(i64)->i32","(i32)->()","(i32,i32,i32)->i32"],
                 "approved_unused_imports":["mixer.checkpoint:()->()","mixer.capability.v1.storage_get:(i32,i32,i32)->i32"],
                 "base_defined_instructions":["local declaration count0","i32.const0","local.get0","end"],
                 "negative_deliberate_additions":["unreachable startup (valid static code; would trap if run)","i64.const0 in uncalled i32 function (type error)","0xfd unsupported opcode in uncalled body","section8 start","unknown capability import","wrong required exports/signatures"],
                 "memory":"One defined nonshared memory, base min=max1page; variants exact0 and32pages."},
    "reviewer":"Pending root review; independently authored fixture source, no external competitor source or VM builder."}
(OUT/"fixture-manifest.json").write_text(json.dumps(fixture_manifest,indent=2)+"\n")
receipt["fixture_manifest_sha256"]=sha(OUT/"fixture-manifest.json")
after={profile:sha(TARGET/profile/"libmixer_vm.a") for profile in before}
assert before==after,"selected archive changed during supplementary tests"
receipt["selected_archives_unchanged"]=after
receipt["source_manifest_sha256"]=sha(OUT/"source-manifest.json")
receipt["result"]="passed"
(OUT/"supplemental-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
