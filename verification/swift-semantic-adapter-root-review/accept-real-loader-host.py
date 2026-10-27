"""One-shot exact root acceptance of the selected private host loader scope."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("real-loader-host-acceptance.json")
assert __debug__ and not OUT.exists()
def identity(path):
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
def read(path):
    return json.loads(path.read_bytes())
def packet(name, expected, count, byte_count):
    folder = ROOT / "verification" / name
    assert identity(folder / "seal.json")["sha256"] == expected
    seal = read(folder / "seal.json")
    members = seal["members"]
    names = set()
    for item in members:
        rel = PurePosixPath(item["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and str(rel) not in names
        names.add(str(rel))
        assert identity(folder / rel) == {k: item[k] for k in ("bytes", "sha256")}
    nodes = list(folder.rglob("*"))
    assert not any(p.is_symlink() for p in nodes)
    assert {str(p.relative_to(folder)) for p in nodes if p.is_file()} == names | {"seal.json"}
    assert len(names) == count and sum(v["bytes"] for v in members) == byte_count
    return folder, {"path": str(folder.relative_to(ROOT)), "seal_sha256": expected,
                    "members_verified": count, "member_bytes_verified": byte_count}

producer, producer_id = packet("swift-real-profile-loader-binding", "e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2", 1050, 31053532)
review, review_id = packet("swift-real-profile-loader-independent", "20841ffd95685e0a65d926c747dfd2c7394341663593cca7c6c01d2c2f329c3f", 635, 27439202)
baseline = ROOT / "verification/swift-typed-result-codec-implementation"
assert identity(baseline / "seal.json")["sha256"] == "4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86"
old = {r["path"]: r for r in read(baseline / "source-manifest.json")["members"]}
new = {r["path"]: r for r in read(producer / "source-manifest.json")["members"]}
added = {"src/experimental_swift_reactor/retained_profile_loader_v1.rs", "src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs"}
assert len(old) == 142 and len(new) == 144 and set(new) - set(old) == added
assert {p for p in old if old[p] != new[p]} == {"src/experimental_swift_reactor/mod.rs"}
for name in old:
    before = (baseline / "source/vm" / name).read_bytes()
    after = (producer / "source/vm" / name).read_bytes()
    if name == "src/experimental_swift_reactor/mod.rs":
        assert after == before + b"\n// Selected-host retained source correlation only; no runtime adoption or public route.\nmod retained_profile_loader_v1;\n"
    else:
        assert after == before
assert {str(p.relative_to(baseline / "host")): p.read_bytes() for p in (baseline / "host").rglob("*") if p.is_file()} == {str(p.relative_to(producer / "host")): p.read_bytes() for p in (producer / "host").rglob("*") if p.is_file()}
verified = []
for filename, logs, count in (("baseline-command-receipts.json", "baseline-logs", 9),
                              ("independent-command-receipts.json", "independent-logs", 43),
                              ("replay/command-receipts.json", "replay/logs", 105)):
    commands = read(review / filename)
    assert len(commands) == count and len({c["label"] for c in commands}) == count
    for command in commands:
        assert command["terminally_waited"] and command["killed_for"] is None
        assert command.get("expectation_met", command["exit_code"] == 0)
        assert command["timeout_seconds"] == 60
        assert "/" not in command["label"] and ".." not in command["label"]
        for stream in ("stdout", "stderr"):
            path = review / logs / (command["label"] + "." + stream)
            assert identity(path) == {k: command[stream][k] for k in ("bytes", "sha256")}
    verified.append({"path": filename, "commands": count, "outputs_rehashed": True})
result = read(review / "review-result.json")
assert result["authority_blocking_findings"] == [] and result["fresh_successful_bounded_commands"] == 157
assert len(result["nonblocking_findings"]) == 1 and result["nonblocking_findings"][0]["id"] == "R1"
assert result["source_tree_sha256"] == "3d7776d8ca3dc10894522079b49e0e8602b567c2e3926f9438b51c843fd6af13"
assert result["all_owned_scratch_removed"] and result["direct_owned_children_terminally_waited"]
assert result["operational_storage_or_runtime_adoption_accepted"] is False
assert read(review / "replay/receipt.json")["runner"]["sha256"] == identity(review / "replayed_run_checks.py")["sha256"]
assert read(review / "independent-receipt.json")["runner_hashed_before_compile"]["sha256"] == identity(review / "run_independent.py")["sha256"]
preimages = Path(__file__).with_name("real-loader-preimage-review.json")
assert read(preimages)["candidate_accepted"] is False
receipt = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "accepted-isolated-private-loader-carrier-host-correlation-with-R1-retained",
    "source_revision_context": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "python": platform.python_version(), "script": identity(Path(__file__)),
    "producer": producer_id, "independent": review_id,
    "source_tree_sha256": result["source_tree_sha256"], "distribution_members": 144,
    "unchanged_host_support_members": 11, "old_source_files_unchanged": 141,
    "only_old_source_change": "private module declaration append",
    "independent_commands": verified, "fresh_independent_successful_commands": 157,
    "producer_replay": result["producer_replay"], "independent_extra": result["independent_extra"],
    "root_source_preimage_audit": {"path": str(preimages.relative_to(ROOT)), **identity(preimages)},
    "accepted_scope": "Safe retained File loader, complete original validation with exact five limits, live source/proof byte equality, private non-Clone carrier and trusted-launcher quiescent-local source/build/session/binary/process correlation. Original validation and I/O errors and retained/opened File ownership survive refusal.",
    "nonblocking_findings_retained": result["nonblocking_findings"],
    "unrun_cases": result["unsupported"],
    "fixed_named_storage_bytes": 197656, "conservative_source_object_union_bytes": 152437784,
    "storage_scope": "Logical source-object bound only; not operational reservation, physical compiler stack/RSS or allocator/kernel accounting. Old165 owner layouts do not cover loader.",
    "cleanup": {"direct_owned_children_waited": True, "owned_scratch_removed": True,
                "descendant_process_group_cleanup_claimed": False, "File_drop_is_close_success": False},
    "next_contract": "Private selected provenance adoption through shared original admission/cleanup and complete new owner/lifetime accounting; precise type/visibility contract selection required before implementation. R1 role correction included in next slice.",
    "runtime_adoption_selected_or_accepted": False, "operational_storage_accepted": False,
    "authenticated_build_package_or_hostile_parent_protection": False,
    "canonical_native_OTA_FieldLog_store_customer_operational_GA_accepted": False,
    "native_UI_capture_process_inventory_started": False}
with OUT.open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"status": receipt["status"], "producer_members": 1050, "review_members": 635,
                  "fresh_independent_commands": 157, "receipt": identity(OUT)}))
