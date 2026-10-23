#!/usr/bin/env python3
"""Review private I/O using frozen inputs and existing builds; no duplicate package graph."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OWNER=ROOT/"verification/capability-durable-io"
PIN="d27e35c2f6897c72384ccd566b5268f8b8a6d1d96e0b5d57d6b4bb96aefb26ff"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    out=HERE/"2026-10-23-final";out.mkdir(exist_ok=False)
    inputs=json.loads((OWNER/"inputs.json").read_bytes());source=Path(inputs["source"]);work=source.parent
    require(inputs["manifest_sha256"]==PIN and len(inputs["files"])==139,"139-source frozen candidate")
    host=json.loads((OWNER/"receipt.json").read_bytes());cross=json.loads((OWNER/"cross-receipt.json").read_bytes())
    require(host["status"]=="passed" and host["source_manifest_sha256"]==PIN and cross["status"]=="passed","owner host/cross passed")
    def unchanged():
        for relative,digest in inputs["files"].items():require(sha((source/relative).read_bytes())==digest,"frozen source "+relative)
        for relative in inputs["new_files"]:require(sha((ROOT/relative).read_bytes())==inputs["files"][relative],"new source "+relative)
    unchanged();audited_logs={}
    for evidence in [host,cross]:
        for row in evidence["commands"]:
            path=OWNER/(row["name"]+".log")
            require(row["exit_code"]==0 and sha(path.read_bytes())==row["log_sha256"],"owner command/log")
            audited_logs[path.relative_to(ROOT).as_posix()]=row["log_sha256"]
    for mode in ["debug","release","tsan"]:
        raw=(OWNER/(mode+".log")).read_bytes()
        require(re.findall(rb"Executed (\d+) tests, with 0 failures",raw)==[b"7",b"16",b"23",b"23"],"owner expected7+16=23 cases "+mode)
    for artifacts in cross["artifacts"].values():
        for path,digest in artifacts.items():require(sha(Path(path).read_bytes())==digest,"official cross artifact")
    preserved={}
    for relative in ["updates/Sources/MixerUpdates/DurableDirectory.swift","updates/Sources/MixerDurableIO/lock.c","updates/Sources/MixerDurableIO/include/MixerDurableIO.h"]:
        old=subprocess.check_output(["git","show","1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636:"+relative],cwd=ROOT)
        require(old==(ROOT/relative).read_bytes() and sha(old)==inputs["files"][relative],"old I/O exact bytes "+relative)
        preserved[relative]=sha(old)
    old_c=(source/"updates/Sources/MixerDurableIO/lock.c").read_bytes()
    require(old_c.replace(b'MixerDurableIO.h',b'MixerCapabilityDurableIO.h').replace(b'mixer_update_flock',b'mixer_capability_update_flock')==(source/"capability-activation/Sources/MixerCapabilityDurableIO/lock.c").read_bytes(),"C shim only renamed header/symbol")
    build=work/"build";products=build/"out/Products/Debug";maps=build/"out/Intermediates.noindex/GeneratedModuleMaps"
    native=Path(inputs["native_copy"]);library=products/"libMixerCapabilityActivation.a"
    library_pin=sha(library.read_bytes());probe_raw=(HERE/"Probe.swift").read_bytes()
    captured=work/"independent-review-probe.swift";captured.write_bytes(probe_raw)
    receipt=dict(status="running",started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),head_at_review=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        owner_source_manifest_sha256=PIN,owner_sources=inputs["files"],immutable_source=str(source),
        owner_receipts={str((OWNER/name).relative_to(ROOT)):sha((OWNER/name).read_bytes()) for name in ["inputs.json","receipt.json","cross-receipt.json"]},
        reused_owner_logs=audited_logs,old_io_preserved=preserved,
        reused_debug_library=dict(path=str(library),sha256=library_pin),probe_sha256=sha(probe_raw),driver_sha256=sha(Path(__file__).read_bytes()),commands=[],
        scope="Independent private-I/O review and labelled @testable unmodified-library host probe; reused owner23-case debug/release/TSan and official iOS/Android compile-only evidence",
        limitations=["Internal @testable probe is not a public API or execution-authority claim", "Probe I/O is a command-line test; product actor/executor/lifecycle integration is not present yet", "FIFO behavior is observed on this Darwin host only; subprocess bounds a possible platform-dependent hang", "No duplicate SwiftPM graph, device/app execution, updater/coordinator, production, publication or GA qualification"])
    def save():(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    env=dict(os.environ,DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    def run(name,argv,expected=0,fragment=None,timeout=60):
        unchanged();start=time.monotonic()
        try:
            result=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=result.stdout,result.returncode
        except subprocess.TimeoutExpired as error:raw,code=(error.stdout or b"")+b"\nReview subprocess timeout\n",124
        log=out/(name+".log");log.write_bytes(raw)
        receipt["commands"].append(dict(name=name,argv=argv,cwd=str(source),environment={"DEVELOPER_DIR":env["DEVELOPER_DIR"]},exit_code=code,expected_exit=expected,timeout_seconds=timeout,seconds=time.monotonic()-start,log=str(log.relative_to(ROOT)),sha256=sha(raw)))
        save();require(code==expected,name+" unexpected exit "+str(code))
        if fragment:require(fragment.encode() in raw,name+" expected output")
        unchanged();require(sha(library.read_bytes())==library_pin,"reused library unchanged");print(name+": "+str(code),flush=True)
    save()
    try:
        run("swift-version",["swift","--version"])
        common=["swiftc","-swift-version","6","-warnings-as-errors","-I",str(products)]
        for name in ["MixerCapabilityDurableIO","MixerDurableIO","MixerCapabilityIO","CMixerVMCapability"]:common += ["-Xcc","-fmodule-map-file="+str(maps/(name+".modulemap"))]
        common += ["-Xcc","-I"+str(native/"include")]
        binary=work/"independent-durable-io-review"
        run("internal-probe-link",common+["-L",str(products),"-lMixerCapabilityActivation","-L",str(native/"lib"),"-lmixer_vm_capability_experimental",str(captured),"-o",str(binary)])
        run("internal-probe-run",[str(binary)],fragment="internal unmodified-library durable I/O probe passed",timeout=20)
        output=(out/"internal-probe-run.log").read_text();match=re.search(r"passed (\d+) checks",output);require(match is not None,"probe count")
        receipt["probe_checks"]=int(match[1]);receipt["probe_binary"]=dict(path=str(binary),sha256=sha(binary.read_bytes()))
        opacity=work/"private-io-opacity.swift";opacity.write_text("import MixerCapabilityActivation\nfunc denied() { _ = CapabilityDurableDirectory.self }\n")
        run("private-io-opacity",common+["-typecheck",str(opacity)],expected=1,fragment="cannot find 'CapabilityDurableDirectory' in scope")
        require(captured.read_bytes()==probe_raw,"probe source unchanged")
        receipt.update(status="independent review/probe passed; no actionable findings",source_and_library_unchanged=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as error:
        receipt.update(status="failed check preserved",problem=str(error));save();raise
    save();print(json.dumps(dict(receipt_sha256=sha((out/"receipt.json").read_bytes()),checks=receipt["probe_checks"])))

if __name__=="__main__":main()
