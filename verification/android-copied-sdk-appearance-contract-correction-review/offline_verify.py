#!/usr/bin/env python3
"""Own source/Git identity checks only. Never import frozen producer harnesses."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = HERE / "inputs/verification/android-copied-sdk-appearance-contract-correction"
SOURCE = PACKET / "accepted-source"
EXPECTED = "559858810e133640d52730972a6610e98442be6d"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


checks = []
for packet, digest in [
    ("android-copied-sdk-appearance-contract", "e08abcacc8421eb2415daa259cf0f9d67a9e2fafa7a879f0b95f574866f62ffb"),
    ("android-copied-sdk-appearance-contract-review", "24d998719e2c5be67fd55a3426340bc8294b07aa78bbf0a8b9ac05bf0de287a9"),
    ("android-copied-sdk-appearance-contract-correction", "08841ed0fd50b5ee0f42b98dbcd5a8751d36ca4712ce0792f929ee933ee3fbdb"),
]:
    path = ROOT / "verification" / packet / "seal.json"
    raw = path.read_bytes()
    assert identity(raw)["sha256"] == digest
    sealed = json.loads(raw)
    for relative, expected in sealed["files"].items():
        assert identity((ROOT / relative).read_bytes()) == expected, relative
    checks.append({"packet": packet, "seal_sha256": digest, "all_members_verified": True,
                   "members": len(sealed["files"]), "bytes": sum(x["bytes"] for x in sealed["files"].values())})

source = json.loads((PACKET / "source-manifest.json").read_text())
assert source["accepted_git"] == EXPECTED
paths = sorted(source["files"])
argv = ["git", "cat-file", "--batch"]
request = "".join(EXPECTED + ":" + p + "\n" for p in paths).encode()
(HERE / "git-source-request.txt").write_bytes(request)
completed = subprocess.run(argv, cwd=ROOT, input=request, capture_output=True, timeout=30)
(HERE / "git-source-blobs.bin").write_bytes(completed.stdout)
(HERE / "git-source.stderr").write_bytes(completed.stderr)
assert completed.returncode == 0
offset = 0
objects = {}
for path in paths:
    newline = completed.stdout.index(b"\n", offset)
    header = completed.stdout[offset:newline].decode().split()
    assert len(header) == 3 and header[1] == "blob", (path, header)
    size = int(header[2]); start = newline + 1; end = start + size
    data = completed.stdout[start:end]
    assert completed.stdout[end:end+1] == b"\n"
    offset = end + 1
    observed = identity(data)
    assert observed == source["files"][path], path
    assert observed == identity((SOURCE / path).read_bytes()), path
    objects[path] = {"git_blob": header[0], **observed}
assert offset == len(completed.stdout)
old = ROOT / "verification/android-copied-sdk-appearance-contract-review/inputs/verification/android-copied-sdk-appearance-contract/source-inputs"
profile = source["sdk_projection"] + source["adapter_projection"]
assert len(profile) == 42
for path in profile:
    assert (SOURCE / path).read_bytes() == (old / path).read_bytes(), path

sdk_map = {str(Path(p).relative_to("sdk")): source["files"][p] for p in source["sdk_projection"]}
adapter_map = {}
for path in source["adapter_projection"]:
    label = str(Path(path).relative_to("native/android"))
    if label.startswith("engine/"):
        label = label[len("engine/"):]
    adapter_map[label] = source["files"][path]


def digest_map(mapping):
    return hashlib.sha256(b"".join((p + "\0" + v["sha256"] + "\n").encode()
                                   for p, v in sorted(mapping.items()))).hexdigest()


assert digest_map(sdk_map) == "4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7"
assert digest_map(adapter_map) == "05cd1c21b598d4b610ab19e10679982aabe618d62eb5784ef723777e1754c5fa"
result = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "seals_verified_unchanged": checks, "accepted_git": EXPECTED,
          "source_files_equal_to_accepted_git": len(paths), "source_identities": objects,
          "all_42_profile_files_equal_to_original_review": True,
          "sdk_projection_sha256": digest_map(sdk_map), "adapter_projection_sha256": digest_map(adapter_map),
          "command": {"argv": argv, "cwd": str(ROOT), "exit_code": completed.returncode,
                      "stdin": identity(request), "stdout": identity(completed.stdout), "stderr": identity(completed.stderr)},
          "scope": "Read-only named source identities from accepted Git and preserved seals; no compiler, producer harness or product execution."}
(HERE / "offline-verification.json").write_text(json.dumps(result, indent=2) + "\n")
(HERE / "exploratory-lookup-failure.json").write_text(json.dumps({
    "argv": ["nl", "-ba", str((PACKET / "source-inputs/cli/Sources/MixerBuild/Configuration.swift").relative_to(ROOT))],
    "error": "No such file or directory", "effect": "Read-only lookup failure; no source executed or changed.",
    "resolved": str((SOURCE / "cli/Sources/MixerBuild/Configuration.swift").relative_to(ROOT)),
}, indent=2) + "\n")
print(json.dumps({k:v for k,v in result.items() if k != "source_identities"}, indent=2))
