"""Compose reviewed bytes and check a prospective patch without applying it."""
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HEAD = "6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2"
CLI = REPO / "verification/android-editor-source-pair5-cli-integration"
HOST = REPO / "verification/android-editor-source-pair5-host-integration"
PROBE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v3"
PAIR = REPO / "verification/android-editor-source-pair5-rebinding"
LEAVES = "native/android/tests/NativeOwnerV2ConcreteHostLeaves/"
commands = []


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + "\n")


def safe_name(name):
    p = PurePosixPath(name)
    assert str(p) == name and not p.is_absolute() and ".." not in p.parts
    assert all(c not in name for c in ("\0", "\n", "\r", "\t"))
    return name


def ordinary(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    for parent in path.parents:
        assert not parent.is_symlink(), str(parent)
        if parent == REPO:
            break
    return path.read_bytes()


def run(name, argv, data=None):
    result = subprocess.run(argv, input=data, capture_output=True, cwd=REPO, timeout=60)
    for suffix, value in (("stdout", result.stdout), ("stderr", result.stderr)):
        (HERE / (name + "." + suffix)).write_bytes(value)
    commands.append({"name": name, "argv": argv, "exit_code": result.returncode,
                     "input": None if data is None else digest(data),
                     "stdout": digest(result.stdout), "stderr": digest(result.stderr),
                     "timeout_seconds": 60})
    save("commands.json", commands)
    assert result.returncode == 0, (name, result.returncode, result.stderr.decode(errors="replace"))
    return result.stdout


def sealed_members(root, expected):
    raw = ordinary(root / "seal.json")
    assert digest(raw)["sha256"] == expected
    rows = json.loads(raw)["members"]
    result = {safe_name(row["path"]): {k: row[k] for k in ("bytes", "sha256")} for row in rows}
    assert len(result) == len(rows)
    return result


def selected(root, members, name):
    data = ordinary(root / safe_name(name))
    assert digest(data) == members[name], name
    return data


assert __debug__ and not (HERE / "source").exists() and not (HERE / "receipt.json").exists()
assert run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == HEAD
run("git-version", ["git", "--version"])
seals = {CLI: "87cd2e4e14d0c444d308397dbd59dbe271419261f5d7fa2cd7201af35db18ecf",
         HOST: "c356544da794b1ae630ec2bb4522f8a9ed93fe1aedb9958676dc84f27188733a",
         PROBE: "04b282dbe16898d0a417286303c87a587b97da1153a3efaf3b564a895a16d8b7",
         PAIR: "088b6dd59bbfd91cd93e7c4cbb16ca1285018b0f6eb6045932b348f7beaf8864"}
packets = {root: sealed_members(root, seal) for root, seal in seals.items()}
inputs = {}


def add(target, root, source):
    target = safe_name(target)
    assert target not in inputs, target
    data = selected(root, packets[root], source)
    inputs[target] = {"data": data, "origin": str(root.relative_to(REPO) / source),
                      "packet_seal_sha256": seals[root]}


cli_rows = json.loads(selected(CLI, packets[CLI], "source-manifest.json"))["members"]
assert len(cli_rows) == 162
for row in cli_rows:
    assert row["path"].startswith("source/")
    assert packets[CLI][row["path"]] == {k: row[k] for k in ("bytes", "sha256")}
    add(row["path"].removeprefix("source/"), CLI, row["path"])
host_rows = json.loads(selected(HOST, packets[HOST], "test-targets.json"))["targets"]
assert len(host_rows) == 183
for row in host_rows:
    assert row["canonical_path"].startswith("native/android/tests/")
    assert packets[HOST][row["candidate_path"]] == {k: row[k] for k in ("bytes", "sha256")}
    add(row["canonical_path"], HOST, row["candidate_path"])

probe_rows = json.loads(selected(PROBE, packets[PROBE], "derivative-source-roster.json"))["records"]
assert len(probe_rows) == 8
probe_replacements = []
for row in probe_rows:
    target = LEAVES + safe_name(row["path"])
    previous = inputs.get(target)
    actual_original = None if previous is None else digest(previous["data"])
    if row["path"] == "dev/mixer/android/ConcreteHostProbe.java":
        assert actual_original == {"bytes": 3807, "sha256": "d7e71beb0b45f35296450170b83055744ebbc5f0185f8dfd1e60bcf351690190"}
        baseline_reason = "Root-reviewed actual host migration baseline; copied-original 3780-byte provenance exception preserved"
    else:
        assert actual_original == row["accepted_original"], target
        baseline_reason = "Exact accepted original or selected new file"
    if previous is not None:
        del inputs[target]
    add(target, PROBE, "inputs/host-leaves/" + row["path"])
    assert digest(inputs[target]["data"]) == row["derivative"]
    probe_replacements.append({"target": target, "previous": actual_original,
                               "selected": row["derivative"], "baseline_reason": baseline_reason})
assert len(inputs) == 346
probe_leaves = {name.removeprefix("inputs/host-leaves/"): value for name, value in packets[PROBE].items()
                if name.startswith("inputs/host-leaves/") and name.endswith(".java")}
assert len(probe_leaves) == 87
for name, expected in probe_leaves.items():
    assert digest(inputs[LEAVES + name]["data"]) == expected, name

profile_bytes = selected(PAIR, packets[PAIR], "profile5.json")
profile = json.loads(profile_bytes)
assert inputs["native/android/contracts/android-profile-v1.json"]["data"] == profile_bytes
pair_checks = []
for group, mapping in (("sdk", profile["sdk_files"]), ("adapter", profile["adapter_files"])):
    assert len(mapping) == (22 if group == "sdk" else 24)
    for name, expected in mapping.items():
        target = ("sdk/" if group == "sdk" else "native/android/engine/" if name.startswith("Sources/") else "native/android/") + name
        assert digest(inputs[target]["data"]) == expected, target
        assert selected(PAIR, packets[PAIR], "sources/" + group + "/" + name) == inputs[target]["data"]
        pair_checks.append({"target": target, "group": group, **expected})
extras = [name for name in packets[PAIR] if name.startswith("canonical-only-inputs/")]
assert len(extras) == 3
for name in extras:
    target = "native/android/" + name.removeprefix("canonical-only-inputs/")
    assert inputs[target]["data"] == selected(PAIR, packets[PAIR], name)

paths = sorted(inputs)
tree = run("selected-tree", ["git", "ls-tree", "-z", HEAD, "--", *paths])
tracked = {}
for entry in tree.split(b"\0"):
    if not entry:
        continue
    info, path_bytes = entry.split(b"\t", 1)
    mode, kind, object_id = info.decode().split()
    assert kind == "blob" and mode in ("100644", "100755")
    tracked[path_bytes.decode()] = {"mode": mode, "object": object_id}
objects = sorted({row["object"] for row in tracked.values()})
object_bytes = run("selected-base-objects", ["git", "cat-file", "--batch"], ("\n".join(objects) + "\n").encode())
blobs = {}
pos = 0
for expected in objects:
    end = object_bytes.index(b"\n", pos)
    object_id, kind, size_text = object_bytes[pos:end].decode().split()
    size = int(size_text)
    assert object_id == expected and kind == "blob"
    pos = end + 1
    blobs[object_id] = object_bytes[pos:pos + size]
    pos += size
    assert object_bytes[pos:pos + 1] == b"\n"
    pos += 1
assert pos == len(object_bytes)
source = HERE / "source"
source.mkdir()
rows, patch_parts = [], []
for name in paths:
    item = inputs[name]
    original = None if name not in tracked else blobs[tracked[name]["object"]]
    live = REPO / name
    if original is None:
        assert not live.exists() and not live.is_symlink(), ("refuse existing untracked target", name)
    else:
        assert ordinary(live) == original, ("refuse canonical drift", name)
        assert bool(live.stat().st_mode & 0o111) == (tracked[name]["mode"] == "100755")
    mode = tracked.get(name, {}).get("mode", "100644")
    output = source / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(item["data"])
    output.chmod(0o755 if mode == "100755" else 0o644)
    state = "new" if original is None else "unchanged" if original == item["data"] else "changed"
    rows.append({"path": name, "state": state, "mode": mode, "base": None if original is None else digest(original),
                 "candidate": digest(item["data"]), "origin": item["origin"], "packet_seal_sha256": item["packet_seal_sha256"]})
    if state != "unchanged":
        old_lines = (original or b"").decode().splitlines(keepends=True)
        new_lines = item["data"].decode().splitlines(keepends=True)
        patch_parts.append("diff --git a/" + name + " b/" + name + "\n")
        if state == "new":
            patch_parts.append("new file mode " + mode + "\n")
        for line in difflib.unified_diff(old_lines, new_lines, fromfile="/dev/null" if original is None else "a/" + name, tofile="b/" + name):
            patch_parts.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
patch = "".join(patch_parts).encode()
(HERE / "prospective.patch").write_bytes(patch)
save("composition.json", {"base_revision": HEAD, "targets": rows, "probe_replacements": probe_replacements,
                           "source_pair_members": pair_checks, "canonical_only_extras": extras})
run("prospective-apply-check", ["git", "apply", "--check", str(HERE / "prospective.patch")])
assert run("final-head", ["git", "rev-parse", "HEAD"]).decode().strip() == HEAD
for row in rows:
    live = REPO / row["path"]
    if row["base"] is None:
        assert not live.exists() and not live.is_symlink()
    else:
        assert digest(ordinary(live)) == row["base"]
save("receipt.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "status": "reviewed-component-byte-composition-and-prospective-patch-check-only",
                      "source_revision": HEAD, "source_tree": "b6dc1f9e74933989781e0acb5ee086717a596d9d",
                      "inputs": {str(k.relative_to(REPO)): v for k, v in seals.items()},
                      "target_count": len(rows), "target_states": {state: sum(row["state"] == state for row in rows) for state in ("new", "changed", "unchanged")},
                      "source_pair_sdk": 22, "source_pair_adapter": 24, "optional_canonical_only_extras": 3,
                      "all_concrete_host_leaf_sources_match_selected_v3": 87,
                      "mechanical_A_host_leaves_changed": False, "prospective_patch": digest(patch),
                      "canonical_sources_written": False, "Git_index_modified": False,
                      "product_code_or_test_artifacts_executed": False, "native_capture_or_process_inventory": False,
                      "pending": ["Final fresh compiled matrix and complete semantic/content/state joins", "Independent v5 interpreter/execution closure review and root selection", "Add selected final matrix and launcher files under native/android/tests/editor-boundaries plus the selected host runner", "Combined host/export/integration qualification before canonical promotion"],
                      "full_integration_native_OTA_GA_accepted": False, "python": sys.version,
                      "command": [sys.executable, "-B", str(Path(__file__).relative_to(REPO))],
                      "preparer": digest(Path(__file__).read_bytes())})
print(json.dumps(json.loads((HERE / "receipt.json").read_bytes()), indent=2))
