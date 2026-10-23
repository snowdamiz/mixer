#!/usr/bin/env python3
"""Original public lifecycle SPI probes using the frozen owner's existing products."""
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
OWNER=ROOT/"experimental-capability-runtime/verification/2026-10-23-lifecycle-candidate-1"
SOURCE_PIN="f9e72d973b0cbc389a5b454dbf2126acb2c5e741e4d4ff7c0ec9e0b495daacb9"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    out=HERE/"2026-10-23-public";out.mkdir(exist_ok=False)
    work=HERE/".build/public";work.mkdir(parents=True,exist_ok=False)
    original=(OWNER/"receipt.json").read_bytes();owner=json.loads(original);source=Path(owner["frozenSourceExport"])
    require(owner["sourceManifestSHA256"]==SOURCE_PIN and len(owner["source"])==71,"exact71-input lifecycle candidate")
    require(sha((OWNER/"source-manifest.sha256").read_bytes())==SOURCE_PIN,"actual owner source manifest")
    snapshot=source.parent;stage=Path(owner["stageRoot"])
    def unchanged():
        for path,digest in owner["source"].items():
            require(sha((source/path).read_bytes())==digest,"frozen export "+path)
            require(sha((ROOT/path).read_bytes())==digest,"source "+path)
    unchanged()
    (out/"owner-receipt-at-public-start.json").write_bytes(original)
    captured=work/"PublicProbe.swift";captured.write_bytes((HERE/"PublicProbe.swift").read_bytes())
    receipt=dict(status="running",started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),head_at_start=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        owner_source_manifest_sha256=SOURCE_PIN,owner_source=owner["source"],immutable_source=str(source),owner_matrix_pending=owner["status"]!="scoped_checks_passed",
        original_probe_sha256=sha(captured.read_bytes()),driver_sha256=sha(Path(__file__).read_bytes()),commands=[],libraries={},binaries={},
        native_archive=dict(path=str(stage/"host/lib/libmixer_vm_capability_experimental.a"),sha256=sha((stage/"host/lib/libmixer_vm_capability_experimental.a").read_bytes())),
        scope="Original external public SPI consumer using actual Wasm/concrete KV and existing frozen owner Debug/Release libraries; no @testable or synthetic exit acknowledgement",
        limitations=["Known exclusive-use adapters and dedicated acyclic sinks are trusted caller requirements, not type-system uniqueness proofs", "Public probes do not deterministically hold the constructor tail or actual exit; separately audited derived gates cover those schedules", "No extra SwiftPM graph; owner broader matrix and cross receipts remain separate", "No activation/release selection, actual health, device, production, credential/trust changes, publication or GA qualification"])
    require(receipt["native_archive"]["sha256"]=="a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72","single qualified native archive")
    def save():(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    env=dict(os.environ,DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    def run(name,argv,expected=0,fragment=None,timeout=60):
        unchanged();began=time.monotonic()
        try:
            result=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=result.stdout,result.returncode
        except subprocess.TimeoutExpired as error:raw,code=(error.stdout or b"")+b"\npublic probe timeout\n",124
        log=out/(name+".log");log.write_bytes(raw)
        receipt["commands"].append(dict(name=name,argv=argv,cwd=str(source),environment={"DEVELOPER_DIR":env["DEVELOPER_DIR"]},exit_code=code,expected_exit=expected,timeout_seconds=timeout,seconds=time.monotonic()-began,log=str(log.relative_to(ROOT)),sha256=sha(raw)))
        save();require(code==expected,name+" unexpected exit "+str(code))
        if fragment:require(fragment.encode() in raw,name+" expected output")
        unchanged();print(name+": "+str(code),flush=True)
    save()
    try:
        run("swift-version",["swift","--version"])
        for mode,configuration in [("debug","Debug"),("release","Release")]:
            build=snapshot/mode;products=build/("out/Products/"+configuration);maps=build/"out/Intermediates.noindex/GeneratedModuleMaps"
            library=products/"libMixerExperimentalCapabilityRuntime.a";require(library.is_file(),"qualified owner product ready "+mode)
            record=dict(path=str(library),sha256=sha(library.read_bytes()));receipt["libraries"][mode]=record;save()
            common=["swiftc","-parse-as-library","-swift-version","6","-warnings-as-errors","-I",str(products)]
            for name in ["MixerCapabilityIO","CMixerVMCapability"]:common += ["-Xcc","-fmodule-map-file="+str(maps/(name+".modulemap"))]
            common += ["-Xcc","-I"+str(stage/"host/include")]
            if mode=="release":common += ["-O"]
            binary=work/("lifecycle-public-"+mode)
            run(mode+"-link",common+["-L",str(products),"-lMixerExperimentalCapabilityRuntime","-L",str(stage/"host/lib"),"-lmixer_vm_capability_experimental",str(captured),"-o",str(binary)])
            require(sha(library.read_bytes())==record["sha256"],"reused library unchanged through link")
            run(mode+"-run",[str(binary)],fragment="public lifecycle SPI review passed",timeout=45)
            match=re.search(r"passed (\d+) checks",(out/(mode+"-run.log")).read_text());require(match is not None,"observed public check count")
            receipt["binaries"][mode]=dict(path=str(binary),sha256=sha(binary.read_bytes()),checks=int(match[1]));save()
            if mode=="debug":
                negatives=HERE/"CompileNegative"
                run("spi-positive",common+["-typecheck",str(negatives/"spi-positive.swift")])
                for name,fragment in {"default-import-group":"cannot find 'OwnedCapabilityAdapterGroup' in scope","default-import-prepare":"inaccessible","spi-private-core":"inaccessible","spi-fake-drain":"has no member 'nativeDidDrain'"}.items():
                    run("reject-"+name,common+["-typecheck",str(negatives/(name+".swift"))],expected=1,fragment=fragment)
        require(captured.read_bytes()==(HERE/"PublicProbe.swift").read_bytes(),"probe capture unchanged")
        unchanged();receipt.update(status="public SPI debug/release checks passed; owner matrix/derived audit pending",source_and_export_unchanged=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as error:
        receipt.update(status="failed public check preserved",problem=str(error));save();raise
    save();print(json.dumps(dict(receipt_sha256=sha((out/"receipt.json").read_bytes()),checks=receipt["binaries"])))

if __name__=="__main__":main()
