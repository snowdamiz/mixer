"""Independently admit frozen implementation/review bytes and record scoped acceptance."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/android-copied-sdk-appearance-implementation"
REVIEW = ROOT / "verification/android-copied-sdk-appearance-implementation-review"
FINAL = REVIEW / "final-review"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def checked(path, expected):
    data = path.read_bytes()
    assert identity(data)["sha256"] == expected, str(path)
    return data


def members(base, entries, count, total):
    assert len(entries) == count
    actual = 0
    for name, expected in entries.items():
        relative = pathlib.PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        data = (base / relative).read_bytes()
        assert identity(data) == expected, name
        actual += len(data)
    assert actual == total
    return {"members": count, "bytes": actual}


selection = checked(OUT / "implementation-selection.json", "cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917")
checked(PRODUCER / "handoff.json", "38a6452b9208f0a88ef5a7f745c88a2cc3356b94c6df601280ea42d630164636")
producer_manifest = checked(PRODUCER / "members.json", "eeafe9198d06d3c57d9824b05f04da829114403f1e3f917c2b5b3ce4c35a6134")
checked(PRODUCER / "seal.sha256", "267e8a806dc2c22756f9e4ea100119bb457c493b830a83f737476fce60ee9077")
producer = members(PRODUCER, json.loads(producer_manifest), 592, 6030790)
preaccess_raw = checked(REVIEW / "preaccess/seal.json", "a9554732573f2d6aa29c22e760bb15ff1fa2643c8507b6bccaca948b3683183c")
preaccess = members(ROOT, json.loads(preaccess_raw)["files"], 222, 1754366)
review_raw = checked(FINAL / "seal.json", "f33465276842cf009534c36e551f895d21e0c2875cae2d44c6247060ab307e6c")
review = members(ROOT, json.loads(review_raw)["files"], 1809, 14935181)
checked(REVIEW / "final-handoff.json", "b510476d81280fe8d5eac49c1c840fe568ca313818bce2cf699337b657370f07")
verdict = json.loads(checked(FINAL / "verdict.json", "e56fd10f21f8a6ff908619232c016d538c07d720efee5a4b9130457d6a9807eb"))
assert verdict["actionable_product_findings"] == []
assert verdict["root_selection_sha256"] == identity(selection)["sha256"]
assert verdict["status"] == "recommend-root-acceptance-of-scoped-development-source-pair-slice"
assert verdict["timeouts"] == [] and verdict["scratch_removed"]

source = json.loads((PRODUCER / "source-binding.json").read_text())
assert source["tree_sha256"] == "59b55224378dd2ce2ef2524d35b303f2dae7c913176d112a203541acb2ddd2c4"
assert len(source["files"]) == 105
for name, expected in source["files"].items():
    assert identity((ROOT / name).read_bytes()) == expected, name
preflight = json.loads((OUT / "implementation-preflight.json").read_text())
source_review = json.loads((FINAL / "independent-source-review.json").read_text())
assert source_review["all_changes_within_root_selected_ownership"]
assert source_review["source_files"] == 105 and source_review["unchanged_source_files"] == 96
assert source_review["changed_or_added_files"] == preflight["owned_product_files"]
assert source_review["unchanged_native_target_input_files"] == 75

commands = json.loads((FINAL / "command-index.json").read_text())
assert len(commands) == 235
for label, result in commands.items():
    assert not result["timed_out"] and result["owned_process_reaped"], label
    for stream in ("stdout", "stderr"):
        assert identity((FINAL / "commands" / label / stream).read_bytes()) == result[stream], (label, stream)
for name, count in [("independent-entrypoint-results.json", 84), ("or-context-results.json", 26),
                    ("alias-control-results.json", 6), ("supplemental-results.json", 15)]:
    data = json.loads((FINAL / name).read_text())
    assert data["count"] == len(data["checks"]) == count
cleanup = json.loads((FINAL / "cleanup.json").read_text())
assert cleanup["scratch_removed"] and cleanup["owned_command_parents_reaped"]
assert cleanup["copied_producer_cli_invocation_directories_removed"]
assert not pathlib.Path(cleanup["scratch_path"]).exists()
assert not cleanup["native_ui_capture_or_device_process_started"]
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": identity(pathlib.Path(__file__).read_bytes())["sha256"],
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "accepted-scoped-copied-sdk-source-pair",
    "scope": "Nine selected product/test files: internal exact source-pair profile, common Swift preaccess and lazily rendered direct-driver admission; retained native source identity only",
    "producer": producer,
    "preaccess": preaccess,
    "independent_review": review,
    "verified_members": producer["members"] + preaccess["members"] + review["members"],
    "verified_bytes": producer["bytes"] + preaccess["bytes"] + review["bytes"],
    "review_seal_sha256": identity(review_raw)["sha256"],
    "source_binding_tree_sha256": source["tree_sha256"],
    "current_source_inputs_verified": 105,
    "owned_product_files": preflight["owned_product_files"],
    "independent_command_results": 235,
    "independent_output_streams_verified": 470,
    "observations": {key: verdict[key] for key in [
        "independent_main_entrypoint_controls", "independent_or_context_controls", "independent_alias_controls",
        "supplemental_observations", "copied_generated_swift_methods", "copied_independent_swift_methods",
        "production_java_assertions", "java_class_files", "focused_python_methods",
        "unchanged_native_generated_inputs_independently_created_and_compared"]},
    "producer_full_cli_methods_each_Debug_Release": 31,
    "root_review": "Source and frozen output review completed; no additional actionable defect. All intended refusal controls and retained reviewer failures stay distinct from passing product methods.",
    "implementation_accepted": True,
    "native_runtime_or_capture_started": False,
    "new_target_build_or_APK": False,
    "GA_qualified": False,
    "pending": verdict["pending"],
    "limitations": [
        "Local source and locks are mutable and unauthenticated; no hostile concurrent-writer or mixed-version range guarantee.",
        "Full UInt64 writer probes use internal test-only snapshot injection; no natural counter exhaustion claim.",
        "Matrices overlap and are not additive product functions. Four pure Java sources were compiled; other exported sources are pinned.",
        "No public V2 routing, stable target ABI, native runtime, physical, published consumer, signing/store/operational or GA qualification."
    ],
    "errors": [],
}
(OUT / "implementation-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("status", "verified_members", "verified_bytes", "current_source_inputs_verified", "independent_command_results", "errors")}))
