"""Bind the frozen producer and mandatory independent cleanup correction."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "cleanup-contract-selection.json"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

require(not OUT.exists(), "Immutable selection already exists")
packets = []
for folder, expected, count in [
    ("android-editor-cleanup-contract", "060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7", 54),
    ("android-editor-cleanup-contract-independent", "ecdc6bd94e2c49b501c2d1dbf69323b8abb3d830c78c689acc39435a31d273c0", 37),
]:
    base = ROOT / "verification" / folder
    index = base / "seal.json"
    require(sha(index) == expected, "Seal identity")
    rows = json.loads(index.read_text())["members"]
    require(len(rows) == count, "Member count")
    seen = set()
    for row in rows:
        p = base / row["path"]
        require(p.resolve().is_relative_to(base.resolve()) and not p.is_symlink() and row["path"] not in seen, "Member path")
        seen.add(row["path"])
        require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], row["path"])
    packets.append({"path": str(index.relative_to(ROOT)), "sha256": expected, "members_verified": count, "bytes": sum(r["bytes"] for r in rows)})

base = ROOT / "verification/android-editor-cleanup-contract-independent"
for row in json.loads((base / "canonical-source-map.json").read_text())["files"]:
    p = ROOT / row["path"]
    require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], "Current input drift: " + row["path"])
addendum = base / "required-addendum.md"
require(sha(addendum) == "6e2dc0989eeb7c6c61a9c8f1c08934b0a637a0c2bf60ba2bc4ecf636593ea5bb", "Required correction identity")

receipt = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": sys.argv,
    "python": sys.version,
    "selector_sha256": sha(pathlib.Path(__file__)),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "packets": packets,
    "current_input_rows_verified": 9,
    "required_addendum": {"path": str(addendum.relative_to(ROOT)), "sha256": sha(addendum)},
    "decision": "Accept combined design and select isolated actual-source implementation with complete-source host controls and pinned SDK cross-compilation; no canonical integration or native acceptance",
    "supersedes": "Earlier design-selection coordinator-unchanged scope is expanded only to the two reviewed disposal guards; old nested creator and main-checked getHandler proposals remain rejected",
    "ownership": ["Isolated copy of NativeAppearanceViewsV2.java", "Isolated copy of NativeRenderer.java", "Isolated NativeCoordinatorV2.java: disposal busy predicate and pre-consumption disposeOnce guard only", "New private API-specific direct InputConnection adapter and bounded authored host controls"],
    "fixed": ["Owner/core unchanged", "Both SDK36 guards unchanged", "No native work in successful commitV2 to finishV2 interval", "No native/editor-busy guard added to ordinary feature entry", "Preserve healthy compatible Binding echoes, Editable, selection, composition and temporary seal behavior", "Fresh private field/owner; no graft over existing subscriptions"],
    "mandatory_corrections": ["Count exact standalone lifecycle lease before revoke through super and callbacks", "Persistent actual loss denials until corresponding authoritative gain; never revive retired adapter", "Hidden TextView detach suffix is outside public-hook lease; unknown retired callbacks fail closed", "Constructor bootstrap and absent Editable cannot create cleanup authority", "Plain native throws retire immediately; no-call refusals are distinct", "Observe failure before cleanup, preserve first fatal and original ordinary failure", "Inaccessible creator target is FAILED_UNCERTAIN with no fabricated close", "Keep cleanup busy through restoration and terminal reporting, clear last, no synchronous owner resumption afterward", "Finite exact callback joins and bounded recursion"],
    "selected_private_policies": ["Serialized CREATING; nested creator returns null before super", "Exact old target close once before successor", "Fixed-null getHandler on every thread without state access", "Nonmonitor extraction, zero-only cursor disabling, spelling refusal", "Unsupported text bounds result without native delegate or text payload", "sendKeyEvent refusal; configured IME_ACTION_DONE only", "Clear refused gesture advertisements; keep generic stylus text enabled", "Scrub failed EditorInfo public and private surrounding payload under original attempt"],
    "evidence": {"producer_model_groups": 24, "producer_actual_source_witnesses": 2, "producer_Java_host_checks": 20, "producer_schema_controls": 10, "independent_model_groups": 24, "independent_exact_source_Java_groups": 3},
    "limits": ["These are design, model and bounded source-fragment receipts, not actual complete adapter qualification", "Handler post rejection retains pending disposal without autonomous resumption guarantee", "No public-hook lease proves platform outer-dispatch quiescence", "Exact close RETURNED does not prove native batch/service reclamation", "New private ancillary refusals are compatibility limitations; eventual binding product scope remains open"],
    "pending": ["Complete actual-source candidate, descriptor and hostile callback/output controls", "Independent review of frozen implementation", "Canonical integration selection", "Native runtime and physical-phone matrix when user resumes", "API28-35 admission, TalkBack, immutable FieldLog, store/signing/OTA and GA"],
    "native_or_GA_accepted": False,
}
OUT.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"path": str(OUT.relative_to(ROOT)), "sha256": sha(OUT), "members_verified": 91}))
