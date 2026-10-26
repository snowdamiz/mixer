"""Read sealed data only; execute no producer/reviewer/product code."""
import datetime
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/android-default-appearance-packaging"
REVIEW = ROOT / "verification/android-default-appearance-packaging-implementation-review"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(path, expected):
    assert identity(path.read_bytes()) == expected, str(path)


seals = []
for base, expected in [
    (PRODUCER, "e7b005b12e6534db0c32ce213e52b2a20c5313ef744bae0411b6344b6a80941f"),
    (REVIEW, "2f8f7f128c8d4b0b0db53233b68c46bfc015a37bb0f3018eb865f7e978ad7b50"),
]:
    raw = (base / "seal.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    seal = json.loads(raw)
    for name, binding in seal["files"].items():
        verify(base / name, binding)
    for name, binding in seal["external_owned_files"].items():
        verify(ROOT / name, binding)
    seals.append({"packet": str(base.relative_to(ROOT)), "seal_sha256": expected,
                  "members": len(seal["files"]), "bytes": sum(x["bytes"] for x in seal["files"].values()),
                  "external_files": len(seal["external_owned_files"])})

handoff = json.loads((PRODUCER / "handoff.json").read_text())
review = json.loads((REVIEW / "acceptance.json").read_text())
assert review["status"] == "accepted-for-selected-development-data-packaging-slice-only"
assert review["actionable_product_findings"] == []
assert set(review["changed_paths"]) == set(handoff["owned_product_files"])
assert review["descriptor"] == handoff["observations"]["descriptor"]
assert review["source_files"] == 241
assert review["source_archive_sha256"] == handoff["product_closure"]["retained_archive"]["sha256"]
run = json.loads((REVIEW / "independent-run-3/receipt.json").read_text())
assert run["status"] == "independent-selected-development-contract-checks-passed"
assert len(run["vectors"]) == 50
assert all(v["status"] == "passed" for v in run["vectors"].values())
assert run["cleanup"]["all_collector_owned_command_groups_absent"]
assert run["cleanup"]["owned_scratch_removed"]
assert not run["native_runtime_or_capture_started"]
for command in run["commands"]:
    assert command["failure_reason"] is None
    assert command["owned_group_absent_on_completion"]
    for stream in ["stdout", "stderr"]:
        verify(REVIEW / "independent-run-3" / command[stream], {
            "bytes": command[stream + "_bytes"], "sha256": command[stream + "_sha256"]})
apk = REVIEW / "independent-run-3/IndependentAppearanceConsumer-unsigned.apk"
verify(apk, {k: review["independent_apk"][k] for k in ["bytes", "sha256"]})
with zipfile.ZipFile(apk) as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)) == 22
    assert [n for n in names if n == "assets" or n.startswith("assets/")] == ["assets/MixerAppearanceV2/descriptor.json"]
    assert identity(archive.read("assets/MixerAppearanceV2/descriptor.json")) == review["descriptor"]
assert not review["release_or_GA_qualified"] and not review["public_V2_accepted"]
result = {
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "status": "read-only-bindings-pass",
    "seals": seals,
    "independent_vectors": len(run["vectors"]),
    "final_run_commands": len(run["commands"]),
    "raw_outputs": 2 * len(run["commands"]),
    "expected_nonzero_commands": sum(c["exit_code"] != 0 for c in run["commands"]),
    "source_files": review["source_files"],
    "product_files": len(handoff["owned_product_files"]),
    "descriptor": review["descriptor"],
    "native_or_capture_started": False,
    "GA_qualified": False,
    "errors": [],
}
(OUT / "final-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
