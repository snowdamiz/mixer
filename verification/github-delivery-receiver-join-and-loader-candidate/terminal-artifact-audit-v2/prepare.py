"""Retain immutable auditor provenance before any fresh audit phase execution."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OLD = HERE.parent / "terminal-artifact-audit"
PARENT = REPO / "verification/github-delivery-codec-and-finite-host-components/terminal-artifact-audit"
assert __debug__ and not (HERE / "preparation.json").exists()


def digest(data):
    return {"bytes":len(data), "sha256":hashlib.sha256(data).hexdigest()}


parent_seal_bytes = (PARENT / "seal.json").read_bytes()
assert digest(parent_seal_bytes)["sha256"] == "99cb9ab40fb87bd2e9bf324f3d323253927837b5bb80832d93a4a65df6193253"
parent_seal = json.loads(parent_seal_bytes)
assert parent_seal["member_count"] == len(parent_seal["members"]) == 65
for member in parent_seal["members"]:
    assert not (PARENT / member["path"]).is_symlink()
    assert digest((PARENT / member["path"]).read_bytes()) == {k:member[k] for k in ("bytes", "sha256")}
old_preparation_bytes = (OLD / "preparation.json").read_bytes()
old_preparation = json.loads(old_preparation_bytes)
for name in ("audit.py", "capability_review.py"):
    old_row, = [r for r in old_preparation["scripts"] if r["target"].endswith("/" + name)]
    blob = (OLD / name).read_bytes()
    assert digest(blob) == old_row["adapted_digest"]
    parent_row, = [r for r in parent_seal["members"] if r["path"] == name]
    assert old_row["source_digest"] == {k:parent_row[k] for k in ("bytes", "sha256")}
    (HERE / name).write_bytes(blob)
failure_bytes = (OLD / "collection.command.json").read_bytes()
failure = json.loads(failure_bytes)
assert failure["timed_out"] is True and failure["exit_code"] is None and failure["child_timeout_seconds"] == 60
prior_failure = {
    "path":str((OLD / "collection.command.json").relative_to(REPO)), "command_record":digest(failure_bytes),
    "started_utc":failure["started_utc"], "completed_utc":failure["completed_utc"], "timed_out":True,
    "child_timeout_seconds":60, "original_directory_modified_or_rerun":False, "descendant_reaping_verified":False,
    "qualification":"Preserved failed diagnostic only; original retained bytes supply no accepted phase or terminal-child provenance",
}
(HERE / "prior-failure.json").write_text(json.dumps(prior_failure, indent=2) + "\n")
scripts = []
for name in ("audit.py", "capability_review.py", "phases.py", "run-reviewed.py", "freeze.py", "prepare.py"):
    blob = (HERE / name).read_bytes()
    compile(blob, str(HERE / name), "exec")
    scripts.append({"path":name, "digest":digest(blob)})
adaptations = []
for target, original in (("audit.py", "audit.py"), ("capability_review.py", "capability_review.py"), ("phases.py", "collect-and-review.py"), ("run-reviewed.py", "run-reviewed.py"), ("freeze.py", "freeze.py")):
    before = (OLD / original).read_bytes(); after = (HERE / target).read_bytes()
    adaptations.append({"source":str((OLD / original).relative_to(REPO)), "source_digest":digest(before), "target":target, "adapted_digest":digest(after),
                        "diff":"".join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True), fromfile="failed-reviewed/" + original, tofile="fresh/" + target))})
preparation = {
    "schema":2, "at":datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv":[sys.executable, "-B", *sys.argv], "python":sys.version,
    "source_revision":"3e105c206c88e18461feb66bdecc0ddb1f2b0f0a", "source_tree":"d23017135c7b34cb030c5b515f7da1bd4b870bb8", "run_id":40437321290,
    "parent_seal":digest(parent_seal_bytes), "closed_parent_members_verified":65, "old_preparation":digest(old_preparation_bytes),
    "selection":"Same reviewed data-only artifact audits with independent bounded phases and explicit fresh child-reaping provenance",
    "execution_scripts":scripts, "adaptations":adaptations, "prior_failure":prior_failure,
    "bounds":"Each owned phase direct child has an independent 60 second timeout; no multistage global wrapper; owned process group liveness probes only",
    "prohibited_activity":"No artifact code execution/import/extraction, native/simulator/emulator/device/UI/capture/process inventories, product test execution, CI retry, Git mutation, hosted harness execution or external mutation",
}
(HERE / "preparation.json").write_text(json.dumps(preparation, indent=2) + "\n")
print(json.dumps({"status":"prepared", "scripts":len(scripts), "closed_parent_members_verified":65, "preparation":digest((HERE / "preparation.json").read_bytes())}))
