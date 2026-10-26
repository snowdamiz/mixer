#!/usr/bin/env python3
"""One-shot source-only profile rebinding after root inventory selection."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "verification/android-editor-integration-protocol"
CANDIDATE = ROOT / "verification/android-editor-preservation-membership-correction"
REVIEW = ROOT / "verification/android-editor-boundary-root-review"


def identity(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_text())


def write(name, data):
    path = OUT / name
    assert not path.exists(), path
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def projection(files):
    return hashlib.sha256("".join(
        name + "\0" + files[name]["sha256"] + "\n"
        for name in sorted(files)
    ).encode("utf-8")).hexdigest()


assert not (OUT / "seal.json").exists(), "Already finalized; never replay"
acceptance = REVIEW / "preservation-membership-acceptance.json"
assert identity(acceptance)["sha256"] == "2d7d9515ef7a6dd4ceeb7c5d61b951d06b4720c1fffdfd5988938d5e47b34e75"
inventory_selection = REVIEW / "integration-canonical-extras-selection.json"
selection = read(inventory_selection)
assert selection["status"] == "selected-optional-pinned-canonical-extras"
extras = selection["canonical_only_optional_files"]
assert len(extras) == 3
profile4 = read(PROTOCOL / "current-profile4.json")
proposed = read(PROTOCOL / "proposed-profile5.json")
for relative, expected in profile4["adapter_files"].items():
    canonical = ROOT / "native/android" / ("engine/" + relative if relative.startswith("Sources/") else relative)
    assert identity(canonical) == expected, canonical
profile5 = {key: proposed[key] for key in profile4}
assert profile5["id"] == "mixer.android-source-pair.5"
assert identity(CANDIDATE / "seal.json")["sha256"] == "620bfefe8cde4b63c2101db76af991fcc1933276f9c1e8d8d1aa1e3db8f0bf0e"
accepted = {row["path"]: {key: row[key] for key in ("bytes", "sha256")}
            for row in read(CANDIDATE / "seal.json")["members"]
            if row["path"].startswith("source/") and row["path"].endswith(".java")}
assert len(accepted) == 16
bindings = []
for group, expected_count in (("sdk", 22), ("adapter", 24)):
    files = profile5[group + "_files"]
    assert len(files) == expected_count
    for relative in sorted(files):
        if group == "sdk":
            source = ROOT / "sdk" / relative
            assert identity(source) == profile4["sdk_files"][relative]
            origin = "unchanged-canonical-profile4"
        elif "source/" + Path(relative).name in accepted:
            source = CANDIDATE / "source" / Path(relative).name
            assert identity(source) == accepted["source/" + source.name]
            origin = "root-accepted-membership-candidate"
        else:
            source = ROOT / "native/android" / ("engine/" + relative if relative.startswith("Sources/") else relative)
            assert identity(source) == profile4["adapter_files"][relative]
            origin = "unchanged-canonical-profile4"
        copied = OUT / "sources" / group / relative
        assert identity(copied) == identity(source)
        files[relative] = identity(copied)
        bindings.append({"group": group, "exported_path": relative,
                         "source": str(source.relative_to(ROOT)), "origin": origin,
                         "copy": str(copied.relative_to(OUT)), **identity(copied)})
    actual = {str(p.relative_to(OUT / "sources" / group))
              for p in (OUT / "sources" / group).rglob("*") if p.is_file()}
    assert actual == set(files)
    profile5[group + "_compatibility_sha256"] = projection(files)
assert profile5["sdk_files"] == profile4["sdk_files"]
assert profile5["sdk_compatibility_sha256"] == "4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7"
assert profile5["adapter_compatibility_sha256"] == "9d47585c18c325888c6d87914808449f1a92e4a3839d02ce5c4ae8f15801c10c"
changed = sorted(p for p in profile4["adapter_files"] if profile4["adapter_files"][p] != profile5["adapter_files"][p])
assert [Path(p).name for p in changed] == ["NativeAppearanceViewsV2.java", "NativeCoordinatorV2.java", "NativeRenderer.java"]
added = sorted(set(profile5["adapter_files"]) - set(profile4["adapter_files"]))
assert [Path(p).name for p in added] == ["NativeEditorConnectionV2.java"]
java = {p for p in profile5["adapter_files"] if p.endswith(".java")}
assert len(java) == 18
current = {str(p.relative_to(ROOT / "native/android")) for p in (ROOT / "native/android/app/src").rglob("*.java")}
assert current == (java - set(added)) | set(extras)
for relative, expected in extras.items():
    source = ROOT / "native/android" / relative
    assert identity(source) == expected
    target = OUT / "canonical-only-inputs" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    target.write_bytes(source.read_bytes())
descriptor = ROOT / "verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json"
assert identity(descriptor) == profile4["default_descriptor"] == profile5["default_descriptor"]
(OUT / "descriptor.json").write_bytes(descriptor.read_bytes())
write("profile4.json", profile4)
write("profile5.json", profile5)
write("rebinding.json", {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, str(Path(__file__).relative_to(ROOT))],
    "python_version": sys.version, "source_revision_context_only": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "accepted-source-rebound-for-selected-integration",
    "candidate_acceptance": {"path": str(acceptance.relative_to(ROOT)), **identity(acceptance)},
    "canonical_extras_selection": {"path": str(inventory_selection.relative_to(ROOT)), **identity(inventory_selection)},
    "profile": identity(OUT / "profile5.json"), "bindings": bindings,
    "changed_existing_adapter_members": changed, "added_adapter_members": added,
    "canonical_only_optional_files": extras,
    "canonical_product_changed": False, "integration_tested_or_accepted": False,
    "native_runtime_public_V2_OTA_or_GA_accepted": False,
})
members = [{"path": str(p.relative_to(OUT)), **identity(p)}
           for p in sorted(OUT.rglob("*")) if p.is_file()]
write("manifest.json", {"schema": 1, "members": members})
members.append({"path": "manifest.json", **identity(OUT / "manifest.json")})
members.sort(key=lambda x: x["path"])
write("seal.json", {"schema": 1, "scope": "Root accepted source identities and selected profile5 rebinding, no integration acceptance",
                    "member_count": len(members), "member_bytes": sum(x["bytes"] for x in members), "members": members})
for member in members:
    assert identity(OUT / member["path"]) == {key: member[key] for key in ("bytes", "sha256")}
assert {str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()} == {x["path"] for x in members} | {"seal.json"}
print(json.dumps({"seal_sha256": identity(OUT / "seal.json")["sha256"], "members": len(members),
                  "bytes": sum(x["bytes"] for x in members), "adapter_projection": profile5["adapter_compatibility_sha256"]}))
