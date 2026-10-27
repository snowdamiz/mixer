"""Amend the reviewed source overlay with the selected two-return-wrapper delta."""
from pathlib import Path
import collections
import datetime
import difflib
import hashlib
import json
import subprocess
import sys

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
HEAD = "6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2"
BASE = ROOT / "verification/android-source-pair5-coherent-integration-preparation"
V4 = ROOT / "verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v4"
TARGET = "native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/view/inputmethod/BaseInputConnection.java"
commands = []


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(name, value):
    (D / name).write_text(json.dumps(value, indent=2) + "\n")


def packet(path, expected):
    raw = (path / "seal.json").read_bytes()
    assert digest(raw)["sha256"] == expected
    seal = json.loads(raw)
    members = seal["members"]
    if isinstance(members, list):
        mapped = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in members}
        assert len(mapped) == len(members)
        members = mapped
    for name, identity in members.items():
        relative = Path(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        assert not (path / relative).is_symlink()
        assert digest((path / relative).read_bytes()) == identity
    assert len(members) == seal["member_count"]
    assert {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()} == set(members) | {"seal.json"}
    return {"path": str(path.relative_to(ROOT)), "seal_sha256": expected, "members_verified": len(members)}


def run(name, argv, input_bytes=None):
    result = subprocess.run(argv, cwd=ROOT, input=input_bytes, capture_output=True, timeout=30)
    (D / (name + ".stdout")).write_bytes(result.stdout)
    (D / (name + ".stderr")).write_bytes(result.stderr)
    commands.append({"name": name, "argv": argv, "exit": result.returncode,
                     "stdout": digest(result.stdout), "stderr": digest(result.stderr), "terminal_reaped": True})
    save("commands.json", commands)
    assert result.returncode == 0
    return result.stdout


def diff(name, old, new, mode):
    if old == new:
        return ""
    lines = ["diff --git a/" + name + " b/" + name + "\n"]
    if old is None:
        lines.append("new file mode " + mode + "\n")
    for line in difflib.unified_diff((old or b"").decode().splitlines(True), new.decode().splitlines(True),
                                     fromfile="/dev/null" if old is None else "a/" + name, tofile="b/" + name):
        lines.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(lines)


def main():
    assert not (D / "receipt.json").exists() and not (D / "seal.json").exists()
    assert run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == HEAD
    assert run("index", ["git", "diff", "--cached", "--name-only"]) == b""
    run("git-version", ["git", "--version"])
    inputs = [packet(BASE, "0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b"),
              packet(V4, "8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8")]
    for name, expected in (("coherent-source-overlay-acceptance.json", "a66b29de853bdc166ad41313bb6473f3bb205a846e86c7c1d0f412cc091e275d"),
                           ("passive-return-probe-v4-acceptance.json", "cb9b8481827d4e5966e68292b447f610f67061cff9b997bf32da8c26f0ffec16")):
        path = ROOT / "verification/android-editor-boundary-root-review" / name
        assert digest(path.read_bytes())["sha256"] == expected
        inputs.append({"root_selection": str(path.relative_to(ROOT)), "sha256": expected})
    composition = json.loads((BASE / "composition.json").read_bytes())
    assert composition["base_revision"] == HEAD and len(composition["targets"]) == 346
    rows = {row["path"]: row for row in composition["targets"]}
    assert len(rows) == 346 and TARGET in rows
    source = {name: (BASE / "source" / name).read_bytes() for name in rows}
    assert all(digest(source[name]) == row["candidate"] for name, row in rows.items())
    replacement = (V4 / "inputs/host-leaves/android/view/inputmethod/BaseInputConnection.java").read_bytes()
    assert source[TARGET] == (V4 / "baseline-v3/android/view/inputmethod/BaseInputConnection.java").read_bytes()
    assert replacement != source[TARGET]
    (D / "amendment.patch").write_text(diff(TARGET, source[TARGET], replacement, rows[TARGET]["mode"]))
    override = D / "override" / TARGET
    override.parent.mkdir(parents=True)
    override.write_bytes(replacement)
    source[TARGET] = replacement
    concrete = "native/android/tests/NativeOwnerV2ConcreteHostLeaves/"
    leaves = {name[len(concrete):]: value for name, value in source.items() if name.startswith(concrete)}
    assert len(leaves) == 87
    assert all(value == (V4 / "inputs/host-leaves" / name).read_bytes() for name, value in leaves.items())
    tree = run("selected-tree", ["git", "ls-tree", "-z", HEAD, "--", *sorted(rows)])
    tracked = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        info, name = entry.split(b"\t", 1)
        mode, kind, object_id = info.decode().split()
        assert kind == "blob" and mode in ("100644", "100755")
        tracked[name.decode()] = {"mode": mode, "object": object_id}
    objects = sorted({row["object"] for row in tracked.values()})
    raw = run("selected-base-objects", ["git", "cat-file", "--batch"], ("\n".join(objects) + "\n").encode())
    blobs, position = {}, 0
    for expected in objects:
        end = raw.index(b"\n", position)
        object_id, kind, size = raw[position:end].decode().split()
        assert object_id == expected and kind == "blob"
        position = end + 1
        blobs[object_id] = raw[position:position + int(size)]
        position += int(size)
        assert raw[position:position + 1] == b"\n"
        position += 1
    assert position == len(raw)
    patch, resolved = [], []
    for name, selected in sorted(rows.items()):
        old = blobs[tracked[name]["object"]] if name in tracked else None
        path = ROOT / name
        assert not path.is_symlink()
        if old is None:
            assert not path.exists() and selected["base"] is None
        else:
            assert path.read_bytes() == old and digest(old) == selected["base"]
            assert bool(path.stat().st_mode & 0o111) == (tracked[name]["mode"] == "100755")
        mode = tracked[name]["mode"] if name in tracked else "100644"
        assert mode == selected["mode"]
        new = source[name]
        state = "new" if old is None else "unchanged" if old == new else "changed"
        patch.append(diff(name, old, new, mode))
        resolved.append({"path": name, "mode": mode, "state": state, "base": selected["base"],
                         "candidate": digest(new), "layer": "override" if name == TARGET else "accepted-base"})
    full_patch = "".join(patch).encode()
    (D / "prospective.patch").write_bytes(full_patch)
    save("resolved-source-map.json", {"base_seal": inputs[0], "override_target": TARGET, "targets": resolved})
    run("prospective-apply-check", ["git", "apply", "--check", str(D / "prospective.patch")])
    assert run("final-head", ["git", "rev-parse", "HEAD"]).decode().strip() == HEAD
    assert run("final-index", ["git", "diff", "--cached", "--name-only"]) == b""
    for row in resolved:
        path = ROOT / row["path"]
        assert not path.exists() if row["base"] is None else digest(path.read_bytes()) == row["base"]
    save("receipt.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "selected-v4-layer-byte-composition-and-prospective-patch-check-passed",
        "source_revision": HEAD, "inputs": inputs, "target_count": 346,
        "target_states": dict(collections.Counter(row["state"] for row in resolved)),
        "base_targets_preserved_exactly": 345, "override_target": TARGET,
        "exact_selected_concrete_host_leaves": 87,
        "all_product_SDK_adapter_mechanical_A_and_original_test_bytes_unchanged_from_accepted_overlay": True,
        "resolved_source_map": digest((D / "resolved-source-map.json").read_bytes()), "prospective_patch": digest(full_patch),
        "canonical_sources_or_index_modified": False, "native_capture_process_inventory_or_product_execution": False,
        "python": sys.version, "command": [sys.executable, "-B", str(Path(__file__))],
        "pending": ["Selected final matrix/launcher additions and complete semantic/typed outcome/execution-closure qualification", "Combined host/export/integration checks before canonical promotion"],
        "full_integration_native_OTA_GA_accepted": False})
    members = [{"path": p.relative_to(D).as_posix(), **digest(p.read_bytes())} for p in sorted(D.rglob("*")) if p.is_file()]
    save("seal.json", {"schema": 1, "scope": "One selected immutable overlay amendment; byte composition only", "members": members,
                       "member_count": len(members), "member_bytes": sum(row["bytes"] for row in members), "full_integration_accepted": False})
    print(json.dumps({"members": len(members), "seal": digest((D / "seal.json").read_bytes()), "target_count": 346, "changed_layers": 1}))


if __name__ == "__main__":
    main()
