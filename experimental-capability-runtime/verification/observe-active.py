#!/usr/bin/env python3
"""Separate public active-payload observation; never mutates frozen candidate3."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "experimental-capability-runtime"
parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--base-receipt", type=Path, default=PACKAGE / "verification/2026-10-23-candidate-5/receipt.json")
a = parser.parse_args()
assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", a.name)
OUT = PACKAGE / "verification" / a.name
OUT.mkdir(exist_ok=False)
SCRATCH = PACKAGE / ".build" / a.name
SOURCE = SCRATCH / "source"
SOURCE.mkdir(parents=True, exist_ok=False)
base_path = a.base_receipt.resolve()
base = json.loads(base_path.read_text())
assert base["status"] == "scoped_checks_passed"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {}
for name, value in base["source"].items():
    original = Path(base["frozenSourceExport"]) / name
    assert sha(original) == value
    target = SOURCE / name; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(original.read_bytes()); target.chmod(0o444)
    inputs[name] = value
for p in [Path(__file__)] + sorted((PACKAGE / "verification/ActivePayload").rglob("*")):
    if not p.is_file() or {".build", ".swiftpm", "__pycache__"}.intersection(p.parts): continue
    name = str(p.relative_to(ROOT)); target = SOURCE / name; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(p.read_bytes()); target.chmod(0o444); inputs[name] = sha(p)
manifest = "".join(value+"  "+name+"\n" for name,value in sorted(inputs.items()))
(OUT / "source-manifest.sha256").write_text(manifest)
stage = Path(base["stageRoot"])/"host"
for name,value in base["nativeArtifacts"]["host"].items(): assert sha(Path(base["stageRoot"])/name) == value
receipt = {"status":"running", "baseReceipt":str(base_path.relative_to(ROOT)), "baseReceiptSHA256":sha(base_path),
    "baseSourceManifestSHA256":base["sourceManifestSHA256"], "source":inputs, "sourceManifestSHA256":hashlib.sha256(manifest.encode()).hexdigest(),
    "frozenExport":str(SOURCE), "nativeArtifacts":base["nativeArtifacts"]["host"], "commands":[],
    "scope":"Separate public API active payload observation, candidate3 production/SDK unchanged", "environment":{"DEVELOPER_DIR":"/Applications/Xcode.app/Contents/Developer"}}
def save(): (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
def run(name, command):
    began=time.monotonic(); result=subprocess.run(command,cwd=SOURCE,env=os.environ|receipt["environment"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    log=OUT/(name+".log"); log.write_bytes(result.stdout)
    record={"name":name,"command":command,"cwd":str(SOURCE),"exitCode":result.returncode,"elapsedSeconds":time.monotonic()-began,"log":log.name,"logSHA256":sha(log)}
    records=re.findall(rb"ACTIVE_PAYLOAD_OBSERVATION (.+)",result.stdout)
    if records: record["observations"]=[json.loads(r) for r in records]
    receipt["commands"].append(record);save();print(name+": "+str(result.returncode),flush=True)
    return record
save()
probe=SOURCE/"experimental-capability-runtime/verification/ActivePayload"
for mode in ["debug","release"]:
    record=run(mode+"-build",["swift","build","--package-path",str(probe),"--scratch-path",str(SCRATCH/mode),"-c",mode,"-Xcc","-I"+str(stage/"include"),"-Xlinker","-L"+str(stage/"lib"),"-Xswiftc","-warnings-as-errors"])
    if record["exitCode"] != 0: continue
    paths=sorted({p.resolve() for p in (SCRATCH/mode).rglob("active-payload-observer") if p.is_file() and not any(part.endswith(".dSYM") for part in p.parts)})
    assert len(paths)==1
    binary=paths[0]
    receipt.setdefault("binaries",{})[mode]={"path":str(binary),"sha256":sha(binary),"bytes":binary.stat().st_size}
    for iteration in range(2):
        record=run(mode+"-run-"+str(iteration+1),[str(binary)])
        record["observationCountMatch"]=len(record.get("observations",[]))==1;save()
receipt["exportUnchanged"] = all(sha(SOURCE/name)==value for name,value in inputs.items())
receipt["baseReceiptUnchanged"]=sha(base_path)==receipt["baseReceiptSHA256"]
receipt["baseProductionCurrentUnchanged"]=all(sha(ROOT/name)==value for name,value in base["source"].items() if "/Sources/" in name or name=="sdk/Package.swift")
receipt["nativeArtifactsUnchanged"]=all(sha(Path(base["stageRoot"])/name)==value for name,value in receipt["nativeArtifacts"].items())
receipt["limitations"]=["Observed1ms sample maximum is not exact per-codec/transient-copy peak or RSS bound", "Sampler and public verification/runtime/native work contribute to process totals", "Logical phase/worker counters sample pump boundaries and omit DTO/backing/transient copies", "No full allocator tracing, OOM/no-abort/recovery, devices, activation or release qualification"]
receipt["status"]="scoped_observations_passed" if all(c["exitCode"]==0 and c.get("observationCountMatch",True) for c in receipt["commands"]) and len(receipt.get("binaries",{}))==2 and all(receipt[k] for k in ["exportUnchanged","baseReceiptUnchanged","baseProductionCurrentUnchanged","nativeArtifactsUnchanged"]) else "failed_observation_preserved"
save()
raise SystemExit(0 if receipt["status"]=="scoped_observations_passed" else 1)
