"""Read-only admission of the two frozen source-export evidence packets."""
import datetime
import hashlib
import json
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "verification/android-authored-toggle-generated-export"
REVIEW = ROOT / "verification/android-authored-toggle-generated-export-review"


def info(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def seal(directory, expected, count):
    path = directory / "seal.json"
    assert info(path)["sha256"] == expected
    members = json.loads(path.read_text())["files"]
    assert len(members) == count
    for name, binding in members.items():
        member = ROOT / name
        assert not member.is_symlink() and member.resolve().is_relative_to(ROOT)
        assert info(member) == binding, name
    return {"sha256": expected, "members": count,
            "bytes": sum(x["bytes"] for x in members.values())}


producer = seal(PRODUCER, "18b101a646638f16840cbec7af294da4feafda20197373c2646905554a966486", 206)
review = seal(REVIEW, "2b7e4e3582dc579ac1d843eacea2ab9db435406bd5953bae80df1f3a96d55b73", 97)
final = json.loads((REVIEW / "final-receipt.json").read_text())
replay = json.loads((REVIEW / "replay-1/receipt.json").read_text())
assert final["status"] == "independent-review-passed-scoped-source-export-only"
assert final["findings"] == []
assert len(replay["checks"]) == 784 and all(x["passed"] is True for x in replay["checks"])
assert len(replay["commands"]) == 28
negative_count = 0
for command in replay["commands"]:
    assert command["childReturned"] and not command["timedOut"]
    label = command["label"]
    negative = label == "independent-omit-authored" or "-lock-" in label
    assert command["exitCode"] == (1 if negative else 0), label
    negative_count += negative
    for stream in ["stdout", "stderr"]:
        binding = command[stream]
        assert info(REVIEW / "replay-1" / binding["name"]) == {
            "bytes": binding["bytes"], "sha256": binding["sha256"]}
assert negative_count == 13
assert replay["sourceInputCount"] == 127
assert replay["sourceTreeSHA256"] == "297b4a3cf52bdb1be0a748b3a25d93090280a4106bc21e55957d22ba9c54e408"
assert replay["cleanup"] == {"ownedCommandGroupsRemaining": [], "scratchRemoved": True}
assert not (REVIEW / "replay-1/scratch").exists()
for flag in ["nativeRuntime", "capture", "deviceDiscovery", "uiAutomation", "publicRouting", "signedOrHealthAuthority", "gaAcceptance"]:
    assert final[flag] is False and replay[flag] is False
print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "python": platform.python_version(),
    "auditor": info(Path(__file__)),
    "producer": producer,
    "review": review,
    "review_checks": 784,
    "review_commands": 28,
    "verified_command_outputs": 56,
    "expected_negative_commands": 13,
    "source_inputs": 127,
    "counts": final["counts"],
    "scratch_removed": True,
    "scope": "Read-only sealed evidence admission; no product or native execution",
    "status": "passed"
}, indent=2))
