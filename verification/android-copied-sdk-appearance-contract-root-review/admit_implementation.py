"""Read-only root admission of frozen implementation before independent execution."""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
PACKET = ROOT / "verification/android-copied-sdk-appearance-implementation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(path, meta):
    assert path.is_file() and not path.is_symlink(), str(path)
    data = path.read_bytes()
    assert len(data) == meta["bytes"] and sha(data) == meta["sha256"], str(path)
    return len(data)


manifest_raw = (PACKET / "members.json").read_bytes()
assert sha(manifest_raw) == "eeafe9198d06d3c57d9824b05f04da829114403f1e3f917c2b5b3ce4c35a6134"
assert sha((PACKET / "seal.sha256").read_bytes()) == "267e8a806dc2c22756f9e4ea100119bb457c493b830a83f737476fce60ee9077"
assert (PACKET / "seal.sha256").read_text().split() == [sha(manifest_raw), "members.json"]
manifest = json.loads(manifest_raw)
total = 0
for name, meta in manifest.items():
    rel = pathlib.PurePosixPath(name)
    assert not rel.is_absolute() and ".." not in rel.parts
    total += check(PACKET / rel, meta)
assert len(manifest) == 592 and total == 6030790
assert {x.relative_to(PACKET).as_posix() for x in PACKET.rglob("*") if x.is_file()} == set(manifest) | {"members.json", "seal.sha256"}
handoff_raw = (PACKET / "handoff.json").read_bytes()
assert sha(handoff_raw) == "38a6452b9208f0a88ef5a7f745c88a2cc3356b94c6df601280ea42d630164636"
handoff = json.loads(handoff_raw)
assert sha((OUT / "implementation-selection.json").read_bytes()) == handoff["selection_sha256"] == "cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917"
owned = json.loads((PACKET / "owned-source-manifest.json").read_text())
assert owned == handoff["owned_product_files"] and len(owned) == 9
for name, meta in owned.items():
    check(ROOT / name, meta)
check(ROOT / "docs/android-copied-sdk-appearance-implementation.md", handoff["implementation_document"])
binding_raw = (PACKET / "source-binding.json").read_bytes()
assert sha(binding_raw) == handoff["source_binding"]["sha256"]
binding = json.loads(binding_raw)
for name, meta in binding["files"].items():
    check(ROOT / name, meta)
assert len(binding["files"]) == 105
index = json.loads((PACKET / "command-index.json").read_text())
assert len(index) == 90
for name, command in index.items():
    assert not command["timed_out"], name
    assert sha((PACKET / "commands" / name / "output.txt").read_bytes()) == command["output_sha256"], name
final_commands = ["20261026T023826286449Z-frozen-full-debug", "20261026T023912904780Z-frozen-full-release"]
for name in final_commands:
    assert index[name]["exit_code"] == 0 and index[name]["source_binding_sha256"] == sha(binding_raw)
    assert "31 tests" in (PACKET / "commands" / name / "output.txt").read_text()
cleanup = json.loads((PACKET / "cleanup.json").read_text())
assert cleanup["owned_commands_completed_before_removal"] and all(x["removed"] for x in cleanup["removed"])
result = {
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": sha(pathlib.Path(__file__).read_bytes()),
    "scope": "Frozen packet and current owned-source/output admission only; no producer/product execution",
    "members_manifest_sha256": sha(manifest_raw),
    "seal_file_sha256": "267e8a806dc2c22756f9e4ea100119bb457c493b830a83f737476fce60ee9077",
    "handoff_sha256": sha(handoff_raw),
    "members": len(manifest), "bytes": total,
    "max_member_bytes": max(x["bytes"] for x in manifest.values()),
    "owned_product_files": owned,
    "source_binding_files": 105,
    "source_binding_tree_sha256": binding["tree_sha256"],
    "retained_command_outputs_verified": len(index),
    "final_full_suite_commands_bound_to_source": final_commands,
    "reported_producer_observations": handoff["observations"],
    "independent_review_authorized": True,
    "implementation_accepted": False, "GA_qualified": False, "errors": [],
}
(OUT / "implementation-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("members", "bytes", "source_binding_files", "retained_command_outputs_verified", "implementation_accepted", "errors")}))
