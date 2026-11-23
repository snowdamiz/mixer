"""Check recovery and ownership on the fixture from verify_ios_native_generation.py."""

import json
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from verify_ios_native_generation import sha256


@contextmanager
def immutable(path):
    flags = path.stat().st_flags
    os.chflags(path, flags | stat.UF_IMMUTABLE)
    try:
        yield
    finally:
        os.chflags(path, flags)


def verify(mixer, fixture, legacy_path):
    root = fixture / "app"
    config = root / "mixer.yml"
    platform = root / "Platforms/iOS"
    project = platform / "FieldLog.xcodeproj"
    pbxproj = project / "project.pbxproj"
    receipt = project / "mixer-generated.sha256"
    plist = project / "MixerNativeInfo.plist"
    store = root / ".mixer/ios-plists"
    starter_config = config.read_bytes()

    def replace_file(path, data):
        replacement = path.with_name(path.name + ".replacement")
        replacement.write_bytes(data)
        assert replacement.stat().st_ino != path.stat().st_ino
        replacement.replace(path)
        return path.stat().st_ino

    def set_native(fields):
        config.write_text(json.dumps({**json.loads(starter_config), "iosNative": fields}))

    def artifacts():
        return tuple(path.read_bytes() if path.exists() else None for path in (pbxproj, receipt, plist))

    outcomes = {}

    def build(label, refusal=None):
        result = subprocess.run(
            [str(mixer), "build", "--platform", "ios", "--directory", str(root)],
            cwd=fixture, capture_output=True, text=True,
        )
        (fixture / f"{label}.json").write_text(result.stdout)
        (fixture / f"{label}.stderr").write_text(result.stderr)
        assert result.returncode == (1 if refusal else 0), (label, result.stdout, result.stderr)
        output = json.loads(result.stdout)
        if refusal:
            assert output["code"] == refusal, (label, output)
            outcomes[label] = refusal
        else:
            assert output["exitCode"] == 0, (label, output)
            outcomes[label] = "built"

    def plist_inputs():
        return {path.name: (path.stat().st_ino, path.read_bytes()) for path in store.glob("*.plist")}

    starter = artifacts()
    initial_inputs = plist_inputs()
    assert starter[2] is None
    native = {"localNetworkUsageDescription": "Connect to the developer checklist service on this local network."}
    set_native(native)
    with immutable(receipt):
        build("immutable-receipt", "operation.failed")
        assert artifacts() == starter and plist_inputs() == initial_inputs
    config.write_bytes(starter_config)
    build("immutable-receipt-retry")
    assert artifacts() == starter

    set_native(native)
    with immutable(pbxproj):
        build("partial-transaction", "operation.failed")
        old_project, pending_receipt, raw = artifacts()
        assert old_project == starter[0] and raw is None
        assert pending_receipt.startswith(b"mixer-ios-generation-transaction-v2\n")
        new_inputs = plist_inputs().items() - initial_inputs.items()
        assert len(new_inputs) == 1
        name, (_, pending_plist) = new_inputs.pop()
        assert name == sha256(pending_plist) + ".plist"
        generated_input = store / name
    config.write_bytes(starter_config)
    edited = old_project + b"// app-owned edit after failed generation\n"
    pbxproj.write_bytes(edited)
    build("edit-during-pending-transaction", "generate.modified")
    assert artifacts() == (edited, pending_receipt, None)
    pbxproj.write_bytes(old_project)

    for label, data in (
        ("pending-same-bytes-raw-replacement", pending_plist),
        ("pending-changed-bytes-raw-replacement", b"app-owned replacement\n"),
    ):
        # A writer outside Mixer's lock replaces the fixed path while recovery is pending.
        plist.write_bytes(pending_plist)
        original_inode = plist.stat().st_ino
        replacement_inode = replace_file(plist, data)
        assert replacement_inode != original_inode
        before_refusal = artifacts()
        build(label, "generate.modified")
        assert artifacts() == before_refusal
        assert plist.stat().st_ino == replacement_inode and plist.read_bytes() == data
        outcomes[label] = {"code": "generate.modified", "originalInode": original_inode,
                           "preservedReplacementInode": replacement_inode, "sha256": sha256(data)}
        plist.unlink()

    inputs_before_retry = plist_inputs()
    build("partial-transaction-restored-config")
    assert artifacts() == starter and plist_inputs() == inputs_before_retry

    plist.write_bytes(pending_plist)
    set_native(native)
    build("byte-identical-unowned-plist", "generate.modified")
    assert artifacts() == (starter[0], starter[1], pending_plist)
    config.write_bytes(starter_config)
    build("unowned-plist-with-stock-config", "generate.modified")
    assert artifacts() == (starter[0], starter[1], pending_plist)
    plist.unlink()

    for path in ("One/Probe.swift", "Two/pROBE.swift", "Two/FieldLogApp.swift"):
        file = platform / path
        file.parent.mkdir(exist_ok=True)
        file.write_text("// Fixture\n")
    set_native({"swiftSources": ["One/Probe.swift", "Two/pROBE.swift"]})
    build("duplicate-swift-basename", "config.ios-native")
    set_native({"swiftSources": ["Two/FieldLogApp.swift"]})
    build("duplicate-entry-point-basename", "config.ios-native")
    assert artifacts() == starter

    # Render AppleProject.source from revision 2825001fa2 for this name and identifier.
    legacy = legacy_path.read_bytes()
    assert sha256(legacy) == "c356581b83eece8677570c766d4158ce77601d627318979dbe19914593d63885"
    config.write_bytes(starter_config)
    edited_legacy = legacy + b"// app-owned legacy edit\n"
    pbxproj.write_bytes(edited_legacy)
    receipt.write_text(sha256(edited_legacy) + "\n")
    rejected_legacy = artifacts()
    build("edited-self-receipted-ios17", "generate.modified")
    assert artifacts() == rejected_legacy
    pbxproj.write_bytes(legacy)
    receipt.write_text(sha256(legacy) + "\n")
    build("exact-ios17-migration")
    assert artifacts() == starter

    set_native(native)
    with immutable(pbxproj):
        build("partial-transaction-with-retained-config", "operation.failed")
        _, pending_receipt, _ = artifacts()
    build("partial-transaction-retry")
    generated_project, generated_receipt, raw = artifacts()
    assert generated_project != starter[0] and generated_receipt != starter[1]
    assert raw is None and generated_input.read_bytes() == pending_plist
    assert name.encode() in generated_project

    # Recreate the state after both output writes and before the final receipt rename.
    receipt.write_bytes(pending_receipt)
    config.write_bytes(starter_config)
    build("interrupted-before-final-receipt")
    assert artifacts() == starter
    set_native(native)
    build("native-project-before-removal")
    native_artifacts = artifacts()
    config.write_bytes(starter_config)
    with immutable(pbxproj):
        build("partial-plist-unreference", "operation.failed")
        assert artifacts()[0] == native_artifacts[0] and artifacts()[2] is None
        assert receipt.read_bytes().startswith(b"mixer-ios-generation-transaction-v2\n")
        assert plist_inputs() == inputs_before_retry

    replacement_inode = replace_file(generated_input, pending_plist)
    set_native(native)
    build("recover-with-identical-content-addressed-replacement")
    assert artifacts() == native_artifacts and generated_input.stat().st_ino == replacement_inode

    corrupted = b"conflicting content at the digest path\n"
    replacement_inode = replace_file(generated_input, corrupted)
    build("refuse-changed-content-addressed-replacement", "generate.modified")
    assert artifacts() == native_artifacts and generated_input.stat().st_ino == replacement_inode
    assert generated_input.read_bytes() == corrupted
    replacement_inode = replace_file(generated_input, pending_plist)

    config.write_bytes(starter_config)
    build("unreference-plist")
    assert artifacts() == starter and generated_input.stat().st_ino == replacement_inode
    assert generated_input.read_bytes() == pending_plist
    print(json.dumps(outcomes, indent=2))


if __name__ == "__main__":
    verify(*(Path(value).resolve() for value in sys.argv[1:]))
