#!/usr/bin/env python3
"""Seal the bounded independent I/O probe and reused owner evidence."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PIN="1e82cfc41481dfd857288e4abd450228b18cacd9b5a4d196c103155060691254"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    probe_path=HERE/"2026-10-23-final/receipt.json";require(sha(probe_path.read_bytes())==PIN,"probe receipt binding")
    probe=json.loads(probe_path.read_bytes())
    require(probe["status"]=="independent review/probe passed; no actionable findings" and probe["probe_checks"]==29,"completed29-check probe")
    for path,digest in probe["owner_receipts"].items():require(sha((ROOT/path).read_bytes())==digest,"owner receipt unchanged")
    inputs=json.loads((ROOT/"verification/capability-durable-io/inputs.json").read_bytes());source=Path(inputs["source"])
    manifest=(ROOT/"verification/capability-durable-io/source-manifest.sha256").read_bytes()
    require(sha(manifest)==probe["owner_source_manifest_sha256"],"actual139-source manifest binding")
    for path,digest in probe["owner_sources"].items():require(sha((source/path).read_bytes())==digest,"frozen export unchanged")
    for path in inputs["new_files"]:require(sha((ROOT/path).read_bytes())==inputs["files"][path],"reviewed source unchanged")
    for path,digest in probe["reused_owner_logs"].items():require(sha((ROOT/path).read_bytes())==digest,"owner log unchanged")
    for row in probe["commands"]:require(sha((ROOT/row["log"]).read_bytes())==row["sha256"] and row["exit_code"]==row["expected_exit"],"probe log/outcome")
    require(sha(Path(probe["reused_debug_library"]["path"]).read_bytes())==probe["reused_debug_library"]["sha256"],"unmodified linked library")
    require(sha(Path(probe["probe_binary"]["path"]).read_bytes())==probe["probe_binary"]["sha256"],"probe binary")
    require(sha((HERE/"Probe.swift").read_bytes())==probe["probe_sha256"] and sha((HERE/"run.py").read_bytes())==probe["driver_sha256"],"review source unchanged")
    excluded={".build",".swiftpm","__pycache__"};records={}
    for path in HERE.rglob("*"):
        if path.is_file() and path.name not in {"final-receipt.json","evidence-manifest.sha256"} and not excluded.intersection(path.relative_to(ROOT).parts):records[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    encoded="".join(d+"  "+p+"\n" for p,d in sorted(records.items())).encode()
    (HERE/"evidence-manifest.sha256").write_bytes(encoded)
    receipt=dict(schema=1,result="Independent frozen private durable I/O review/probe passed; no actionable findings",sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        owner_source_manifest_sha256=probe["owner_source_manifest_sha256"],owner_source_count=len(probe["owner_sources"]),owner_receipts=probe["owner_receipts"],
        probe_receipt=dict(path=str(probe_path.relative_to(ROOT)),sha256=PIN),probe_checks=29,probe_commands=len(probe["commands"]),
        reused_owner_log_count=len(probe["reused_owner_logs"]),reused_owner_tests_per_mode=23,reused_owner_modes=["debug","release","Swift TSan"],official_cross="iOS/Android module/object compile only",
        old_io_preserved=probe["old_io_preserved"],evidence_manifest_sha256=sha(encoded),evidence_files=len(records),scope=probe["scope"],limitations=probe["limitations"])
    target=HERE/"final-receipt.json";target.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(dict(final_receipt_sha256=sha(target.read_bytes()),evidence_manifest_sha256=sha(encoded),evidence_files=len(records))))

if __name__=="__main__":main()
