#!/usr/bin/env python3
"""Bind the independent public run and reused immutable owner qualification evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OWNER=ROOT/"verification/release-v3-service/2026-10-23-candidate-2"
PUBLIC_PIN="23d57e2a38fd992ab821d86620930b31ade77bca5e2194ffbc493d05643517d3"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    public_path=HERE/"2026-10-23-final/receipt.json"
    require(sha(public_path.read_bytes())==PUBLIC_PIN,"independent public receipt")
    public=json.loads(public_path.read_bytes())
    owner_path=OWNER/"receipt.json";owner=json.loads(owner_path.read_bytes())
    require(sha(owner_path.read_bytes())==public["owner_receipt"]["sha256"],"owner final receipt")
    source=Path(owner["frozenSourceExport"])
    for path,digest in owner["source"].items():
        require(sha((source/path).read_bytes())==digest,"frozen owner source "+path)
        require(sha((ROOT/path).read_bytes())==digest,"live owner source "+path)
    require(sha((HERE/"public_test.go").read_bytes())==public["original_external_tests_sha256"],"original public tests")
    require(sha((HERE/"run.py").read_bytes())==public["driver_sha256"],"independent driver")
    logs={}
    for row in public["commands"]:
        path=ROOT/row["log"];require(row["exit_code"]==0 and sha(path.read_bytes())==row["sha256"],"public run log")
        logs[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    for row in owner["commands"]:
        path=OWNER/(row["name"]+".log");require(row["exitCode"]==0 and sha(path.read_bytes())==row["logSHA256"],"owner main log")
        logs[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    pg=json.loads((OWNER/"postgres/receipt.json").read_bytes())
    require(sha((OWNER/"postgres/receipt.json").read_bytes())==owner["subreceipts"]["postgres"]["sha256"],"PG subreceipt")
    require(pg["status"]=="passed" and not pg["mockDatabase"] and pg["privateClusterRemoved"],"real private PostgreSQL receipt")
    for path,digest in pg["sourceSHA256"].items():require(owner["source"].get("services/"+path)==digest,"same frozen PG source "+path)
    for row in pg["commands"]:
        require(row["exitCode"]==0,"PG command exit")
        for stream in ["stdout","stderr"]:
            record=row[stream];path=OWNER/"postgres"/record["path"]
            require(sha(path.read_bytes())==record["sha256"] and path.stat().st_size==record["bytes"],"PG stream binding")
            logs[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
        if row["name"]=="initialize":
            directory=Path(row["command"][row["command"].index("-D")+1])
            require(not directory.parent.exists(),"disposable PG directory removed")
    pg_output=(OWNER/"postgres/real-postgres-tests.stdout").read_text()
    require("--- SKIP:" not in pg_output and "--- FAIL:" not in pg_output and "TestPostgresV3CoexistenceRLSReplayAndRuntimeIsolation" in pg_output and "TestPostgresV3InterruptedPublicationImmediateRestart" in pg_output,"actual V3 PostgreSQL cases passed without skips")
    old=json.loads((OWNER/"old-binary/receipt.json").read_bytes())
    require(sha((OWNER/"old-binary/receipt.json").read_bytes())==owner["subreceipts"]["old-binary"]["sha256"],"old binary subreceipt")
    require(old["oldRejectsSchema3"] and old["newAcceptsSchema3"] and old["containerUnchanged"],"old/new container outcomes")
    for path,digest in old["currentSource"].items():require(owner["source"].get("services/"+path)==digest,"same frozen old-binary candidate source")
    for row in old["commands"]:
        expected=1 if row["name"]=="old-rejection" else 0
        path=OWNER/"old-binary"/(row["name"]+".log")
        require(row["exitCode"]==expected and sha(path.read_bytes())==row["logSHA256"],"old/new binary command/log")
        logs[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    for path,digest in old["binaries"].items():require(sha(Path(path).read_bytes())==digest,"retained old/new binary")
    protocol_preserved={}
    for path,digest in owner["source"].items():
        if path.startswith("services/protocol/"):
            raw=subprocess.check_output(["git","show",public["baseline"]+":"+path],cwd=ROOT)
            require(sha(raw)==digest,"reviewed protocol exact bytes")
            protocol_preserved[path]=digest
    excluded={".build",".swiftpm","__pycache__"}
    records={}
    for p in HERE.rglob("*"):
        if p.is_file() and p.name not in {"final-receipt.json","evidence-manifest.sha256"} and not excluded.intersection(p.relative_to(ROOT).parts):records[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes())
    manifest="".join(d+"  "+p+"\n" for p,d in sorted(records.items())).encode()
    (HERE/"evidence-manifest.sha256").write_bytes(manifest)
    receipt=dict(schema=1,result="Independent frozen service-v3 source/public API review passed; no actionable findings",observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        owner_receipt=public["owner_receipt"],owner_source_manifest_sha256=owner["sourceManifestSHA256"],owner_source_inputs=len(owner["source"]),
        independent_public_receipt=dict(path=public_path.relative_to(ROOT).as_posix(),sha256=PUBLIC_PIN),
        independent_public_tests=public["original_public_tests"],independent_public_race=True,independent_vet=True,
        inspected_production_files=["services/release/"+p+".go" for p in ["server","storage","store","versioned"]],
        protocol_preserved_from_baseline=protocol_preserved,additional_preserved_baseline=public["preserved_baseline"],legacy_test_adjustment=public["legacy_test_adjustment"],
        owner_subreceipts=owner["subreceipts"],audited_log_files=logs,audited_log_count=len(logs),
        evidence_manifest_sha256=sha(manifest),evidence_files=len(records),scope=public["scope"],limitations=public["limitations"])
    path=HERE/"final-receipt.json";path.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(dict(final_receipt_sha256=sha(path.read_bytes()),evidence_manifest_sha256=sha(manifest),audited_logs=len(logs),evidence_files=len(records))))

if __name__=="__main__":main()
