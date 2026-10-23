#!/usr/bin/env python3
"""Independent frozen-source public service review; no private imports or owner edits."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / "verification/release-v3-service/2026-10-23-candidate-2"
OWNER_PIN = "974478bb7f9c50173ca0dfd3defac5828ade0d4aa16ebbb106780c338b2cad0b"
BASE = "c5bf3fee0c7823d976861d7c452ef3245980df30"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)


def main():
    out = HERE / "2026-10-23-final"; out.mkdir(exist_ok=False)
    work = ROOT / ".build/release-v3-service-review-final"; work.mkdir(exist_ok=False)
    owner_raw = (OWNER / "receipt.json").read_bytes(); require(sha(owner_raw) == OWNER_PIN, "final owner receipt")
    owner = json.loads(owner_raw); source = Path(owner["frozenSourceExport"])
    require(owner["sourceManifestSHA256"] == "e37325fc0c158a3b41f399f2cee80d372eb3527cc321698d0c5262b724bd3b4b", "53-input source freeze")
    require(owner["sourceUnchanged"] and owner["exportUnchanged"] and owner["protocolUnchangedFromReviewedRevision"], "completed owner checks")
    def unchanged():
        for relative, digest in owner["source"].items():
            require(sha((source / relative).read_bytes()) == digest, "immutable export " + relative)
            require(sha((ROOT / relative).read_bytes()) == digest, "current source " + relative)
    unchanged()
    manifest = "".join(d + "  " + p + "\n" for p, d in sorted(owner["source"].items())).encode()
    require(sha(manifest) == owner["sourceManifestSHA256"], "owner manifest reconstruction")
    artifacts = {}
    for row in owner["commands"]:
        path = OWNER / (row["name"] + ".log")
        require(row["exitCode"] == 0 and sha(path.read_bytes()) == row["logSHA256"], "owner command/log " + row["name"])
        artifacts[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    for path, pin in [(OWNER / "postgres/receipt.json", "ad780670612d52f32777c4881bb6ec83b624908d86aac41c560455e365001cbe"),
                      (OWNER / "old-binary/receipt.json", "2101bb169a612863829ff977113cf2571139cfd56d8ecc8706db90e3556b2e84")]:
        require(sha(path.read_bytes()) == pin, "exact owner subreceipt")
        artifacts[str(path.relative_to(ROOT))] = pin
    preserved = {}
    for relative in ["services/release/postgres.go", "services/release/migrations/001_release.sql", "services/internal/durable/store.go", "services/release/server_test.go", "services/release/storage_test.go", "services/protocol/v2.go", "services/protocol/protocol.go", "services/protocol/v3.go"]:
        baseline = subprocess.check_output(["git", "show", BASE + ":" + relative], cwd=ROOT)
        require((source / relative).read_bytes() == baseline, "baseline preservation " + relative)
        preserved[relative] = sha(baseline)
    test_path = "services/release/v2_test.go"
    old_test = subprocess.check_output(["git", "show", BASE + ":" + test_path], cwd=ROOT)
    revised_test = old_test.replace(b'strings.Replace(v2Base, "/v2/", "/v3/", 1)', b'strings.Replace(v2Base, "/v2/", "/v4/", 1)').replace(b'fields["schema"] = []byte(`3`)', b'fields["schema"] = []byte(`4`)')
    require((source / test_path).read_bytes() == revised_test, "only now-supported3 to unsupported4 legacy test changes")
    legacy_test_adjustment = dict(path=test_path, before_sha256=sha(old_test), after_sha256=sha(revised_test),
        reason="Exactly two old unknown-version probes move3 to4 because protocol/store3 is now explicitly supported; no v1/v2 acceptance assertion removed")
    # Exactly the four production files were inspected as an additive diff.
    diff = subprocess.run(["git", "diff", BASE, "--", "services/release/server.go", "services/release/storage.go", "services/release/store.go", "services/release/versioned.go"], cwd=ROOT, check=True, capture_output=True).stdout
    (out / "reviewed-production.diff").write_bytes(diff)
    module = work / "public"; module.mkdir()
    test_raw = (HERE / "public_test.go").read_bytes(); (module / "public_test.go").write_bytes(test_raw)
    (module / "go.mod").write_text("module mixer/servicev3review\n\ngo 1.26.0\n\nrequire mixer/services v0.0.0\n\nreplace mixer/services => " + str(source / "services") + "\n")
    shutil.copyfile(source / "services/go.sum", module / "go.sum")
    receipt = dict(status="running", started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), head_at_review=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        owner_receipt=dict(path=str((OWNER / "receipt.json").relative_to(ROOT)), sha256=OWNER_PIN), owner_source_manifest_sha256=owner["sourceManifestSHA256"], frozen_source=owner["source"],
        immutable_owner_export=str(source), reused_owner_evidence=artifacts, baseline=BASE, preserved_baseline=preserved, legacy_test_adjustment=legacy_test_adjustment,
        reviewed_diff_sha256=sha(diff), original_external_tests_sha256=sha(test_raw), driver_sha256=sha(Path(__file__).read_bytes()), commands=[],
        scope="Independent source review and original external public-API httptest cases; reuse audited owner full-race/vet/private-PostgreSQL/old-binary evidence; root owns actual TCP-to-Swift sidecar",
        limitations=["Development loopback service only; no production deployment/signing/customer/credential/device operations", "Independent tests use public ServeHTTP via httptest, not actual TCP or native activation", "No duplicated PostgreSQL cluster or broad full-suite run; owner receipts are reused with exact log/hash checks", "Synthetic metadata payloads confer no executable or native authority"])
    def save(): (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def run(name, argv):
        unchanged(); began=time.monotonic();result=subprocess.run(argv,cwd=module,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        log=out/(name+".log");log.write_bytes(result.stdout)
        receipt["commands"].append(dict(name=name, argv=argv, cwd=str(module), exit_code=result.returncode, elapsed_seconds=time.monotonic()-began, log=str(log.relative_to(ROOT)), sha256=sha(result.stdout)))
        save();require(result.returncode==0,name+" failed");unchanged();print(name+": 0",flush=True)
    save()
    try:
        run("go-version", ["go", "version"])
        run("public-race", ["go", "test", "-mod=mod", "-race", "-count=1", "-json", "./..."])
        rows=[json.loads(line) for line in (out/"public-race.log").read_text().splitlines() if line.startswith("{")]
        passed=[row["Test"] for row in rows if row.get("Action")=="pass" and row.get("Test") and "/" not in row["Test"]]
        require(len(passed)==4,"four original public tests passed")
        require(not any(row.get("Action") in ["skip","fail"] for row in rows),"no skipped/failed independent cases")
        receipt["original_public_tests"]=passed
        run("public-vet", ["go", "vet", "-mod=mod", "./..."])
        require((module/"public_test.go").read_bytes()==test_raw,"test export unchanged")
        unchanged();receipt.update(status="independent source/public API review passed; no actionable findings",completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_and_export_unchanged=True)
    except Exception as error:
        receipt.update(status="failed independent check preserved",problem=str(error));save();raise
    save();print(json.dumps(dict(receipt_sha256=sha((out/"receipt.json").read_bytes()),status=receipt["status"])))


if __name__ == "__main__": main()
