"""One-shot root custody and scoped acceptance after completed independent reviews."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def identity(path):
    assert stat.S_ISREG(path.lstat().st_mode), path
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads((ROOT / path).read_bytes())

def save(path, value):
    with (ROOT / path).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

def packet(name, expected):
    folder = ROOT / "verification" / name
    assert identity(folder / "seal.json")["sha256"] == expected
    seal = json.loads((folder / "seal.json").read_bytes())
    members = seal["members"]
    names = set()
    for row in members:
        name = row["path"]
        p = PurePosixPath(name)
        assert not p.is_absolute() and ".." not in p.parts and ".git" not in p.parts
        assert str(p) == name and name not in names
        names.add(name)
        assert identity(folder / name) == {k: row[k] for k in ("bytes", "sha256")}
    actual = set()
    for base, dirs, files in os.walk(folder, followlinks=False):
        for item in dirs + files:
            assert not (Path(base) / item).is_symlink()
        actual.update(str((Path(base) / x).relative_to(folder)) for x in files)
    assert actual == names | {"seal.json"}
    return {"path": str(folder.relative_to(ROOT)), "seal_sha256": expected,
            "members_verified": len(members), "bytes_verified": sum(r["bytes"] for r in members)}

assert __debug__
codec = packet("swift-typed-result-codec-implementation", "4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86")
codec_review = packet("swift-typed-result-codec-independent", "8f22a9842cb609027d6f6cbe808eefb13d56cd52b68ef6cddec9a9926f5fc16b")
field = packet("android-field-preservation-replacement-finite-controls", "309dc0fe8b70849fd95df09b673577cbbb74dbeeac02c4aee9b01870306a9626")
field_review = packet("android-field-preservation-replacement-independent", "d1d18c25ecebacecdba20d8c117a36f9dd01a082d14c394f86b8e08874e314a1")
full_path = "verification/android-renderer-semantic-policy-preparation/inputs/complete-280-checklist.json"
assert identity(ROOT / full_path)["sha256"] == "c782b54865efc29534908b8ae71b6c83f749ad79af1d62c3d0a4a364772c20b2"
full = read(full_path)["subjects"]
assert len(full) == 280 and len({r["id"] for r in full}) == 280
by_id = {r["id"]: r for r in full}
four = read(field["path"] + "/inputs/exact-four-subject-contracts.json")["subjects"]
assert len(four) == 4 and all(r == by_id[r["id"]] for r in four)
cr = read(codec_review["path"] + "/decision.json")
fr = read(field_review["path"] + "/review.json")
assert cr["findings"] == [] and fr["actionable_blockers_for_this_scope"] == []
assert cr["producer_methods_replayed_each_mode"] == 27 and cr["independent_methods_each_mode"] == 7
assert cr["ordinary_production_modes"] == ["debug", "optimized"]
assert cr["negative_compile_controls_each_mode"] == 6 and cr["positive_compile_controls_each_mode"] == 1
assert fr["summary"]["invocations"] == 123 and fr["summary"]["checks"] == 645
assert fr["producer_replay_byte_identical"] and fr["additional_independent_controls"]["checks"] == 107
assert fr["all_children_reaped_owned_scratch_removed"] and cr["owned_scratch_removed_and_children_reaped"]
common = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
          "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
          "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
          "python": platform.python_version(), "script": identity(Path(__file__)),
          "root_runtime_replay": False, "root_review": "Source/typed-contract/independent-output review and fresh closed member custody; no duplicate runtime replay",
          "native_UI_capture_process_inventory": "paused-unrun", "canonical_native_OTA_GA_accepted": False}
codec_path = "verification/swift-semantic-adapter-root-review/typed-result-codec-host-acceptance.json"
save(codec_path, {**common, "status": "accepted-isolated-private-pure-data-codec-host-scope",
    "producer": codec, "independent_review": codec_review,
    "candidate_source_tree_sha256": cr["candidate_source_tree_sha256"],
    "distribution_members": 142, "unchanged_host_support_members": 11,
    "producer_methods_each_mode": 27, "independent_methods_each_mode": 7,
    "full_result_positive_combinations": 54, "positive_compile_controls_each_mode": 1,
    "negative_compile_controls_each_mode": 6, "production_modes_passed": ["debug", "optimized"],
    "old_owner_layouts_unchanged_each_mode": 165, "codec_layouts_operationally_accepted": False,
    "reviewed_semantics": ["complete actual-type mapping and fixed extents", "closed tags/reserved and absent payload refusal",
        "all fallible preflight before writes", "exact borrowed code/digests and private unverified views",
        "three distinct usage snapshots and None/Some-zero preservation", "required raw zero length remains present empty artifact"],
    "pending": ["authentic loader/carrier", "build/session/source provenance", "operational storage and lifetime accounting",
        "runtime adoption/exporter", "semantic context admission", "canonical integration", "FieldLog immutable published consumption"]})
field_path = "verification/android-editor-boundary-root-review/field-preservation-replacement-selection.json"
save(field_path, {**common, "status": "accepted-four-exact-body-finite-host-facets",
    "producer": field, "independent_review": field_review, "source_context": fr["source_context"],
    "source_tool_closure_sha256": fr["source_tool_closure_sha256"],
    "original_four_subject_records_equal_complete_280": True, "original_checklist": {"path": full_path, **identity(ROOT / full_path)},
    "subjects": fr["subjects"], "producer_summary": fr["summary"],
    "independent_replay_byte_identity": fr["producer_replay_actual_results"],
    "independent_cases": 4, "independent_checks": 107, "setup_constructor_calls": 2,
    "native_callback_state_credit": 0, "actual_Input_observations": fr["Input_observations"],
    "retained_failed_attempts": ["producer run-1 javac accessor collision", "reviewer run-1 final-field assignment"],
    "pending": fr["scope_limitations"], "fresh_coherent_matrix_consumption_authorized": True})
print(json.dumps({"codec": {"path": codec_path, **identity(ROOT / codec_path)},
                  "field": {"path": field_path, **identity(ROOT / field_path)}, "all_original_four_records_equal": True}))
