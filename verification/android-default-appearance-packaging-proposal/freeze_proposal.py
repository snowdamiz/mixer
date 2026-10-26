#!/usr/bin/env python3
"""Audit retained bounded evidence and seal this documentation-only handoff."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
DOC = ROOT / "docs/android-default-appearance-packaging-proposal.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    probe = json.loads((OUT / "probe-2/receipt.json").read_text())
    manifest = json.loads((OUT / "probe-2/source-manifest.json").read_text())
    assert probe["status"] == "proposal-host-observations-passed-no-product-implementation"
    assert not any(probe[key] for key in ["native_runtime_or_capture_started", "generated_app_built", "public_routing_changed", "release_or_GA_qualified"])
    assert probe["selected_inputs_unchanged"]
    assert sha(OUT / "probe-2/source-manifest.json") == probe["source_manifest_sha256"]
    source_root = OUT / "probe-2/source-inputs"
    for row in manifest:
        assert sha(source_root / row["path"]) == row["sha256"]
        assert sha(ROOT / row["path"]) == row["sha256"]
        assert (source_root / row["path"]).stat().st_size == row["bytes"]
    process_runner = "cli/Sources/MixerBuild/ProcessRunner.swift"
    supplemental = OUT / "supplemental-source-inputs" / process_runner
    supplemental.parent.mkdir(parents=True, exist_ok=True)
    supplemental.write_bytes((ROOT / process_runner).read_bytes())
    supplemental_identity = {"path": process_runner, "sha256": sha(supplemental), "bytes": supplemental.stat().st_size}
    (OUT / "supplemental-source-manifest.json").write_text(json.dumps([supplemental_identity], indent=2, sort_keys=True) + "\n")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    (OUT / "delivery-revision.txt").write_text(revision.stdout)
    assert hashlib.sha256("".join(row["path"] + "\0" + row["sha256"] + "\n" for row in manifest).encode()).hexdigest() == probe["selected_input_tree_sha256"]
    for attempt in ["probe-1", "probe-2"]:
        receipt = json.loads((OUT / attempt / "receipt.json").read_text())
        assert receipt["cleanup"]["removed"]
        assert not pathlib.Path(receipt["cleanup"]["owned_scratch"]).exists()
        for command in receipt["commands"]:
            assert sha(OUT / command["output"]) == command["output_sha256"]
            assert command["exit_code"] == (1 if command["output"].endswith("aapt-link-help.txt") else 0)
    for name, identity in probe["artifacts"].items():
        assert sha(OUT / "probe-2" / name) == identity["sha256"]
        assert (OUT / "probe-2" / name).stat().st_size == identity["bytes"]
    descriptor = OUT / "probe-2/descriptor.json"
    with zipfile.ZipFile(OUT / "probe-2/asset-probe-unsigned.apk") as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert names.count("assets/MixerAppearanceV2/descriptor.json") == 1
        assert archive.read("assets/MixerAppearanceV2/descriptor.json") == descriptor.read_bytes()
        assert {name: hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(names)} == probe["synthetic_apk_entries"]
    ranges = {
        "cli/Sources/MixerBuild/AndroidProject.swift": [(27,77),(97,106),(132,144)],
        "cli/Sources/MixerBuild/Resources/android-build.py": [(62,86),(207,231),(280,294),(306,328)],
        "cli/Sources/MixerBuild/ProjectGenerator.swift": [(26,49),(242,251)],
        "sdk/Sources/MixerUI/AppearanceDefaultV2.swift": [(6,10)],
        "sdk/Sources/MixerUI/AppearanceDescriptorV2.swift": [(3,34),(879,909)],
        "native/android/app/src/dev/mixer/android/InstalledAppearanceV2.java": [(11,60)],
        "native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java": [(67,74),(121,130)],
        "mixer-product-plan.md": [(332,342),(661,669)],
    }
    with (OUT / "source-excerpts.txt").open("w") as stream:
        for name, sections in ranges.items():
            lines = (source_root / name).read_text().splitlines()
            for start, end in sections:
                stream.write(f"{name}:{start}-{end}\n")
                for index in range(start, min(end, len(lines)) + 1):
                    stream.write(f"{index}: {lines[index-1]}\n")
                stream.write("\n")
        lines = supplemental.read_text().splitlines()
        stream.write(process_runner + ":14-35\n")
        for index in range(14, 36):
            stream.write(f"{index}: {lines[index-1]}\n")
    audit = {"status": "passed", "selected_source_files": len(manifest),
             "source_copies_and_live_inputs_match": True, "command_output_bindings_match": True,
             "exact_synthetic_archive_asset_matches": True, "owned_scratch_removed_both_attempts": True,
             "product_implementation_or_acceptance": False}
    (OUT / "audit-output.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    exclude = {"receipt.json", "seal.sha256"}
    files = [DOC] + sorted(p for p in OUT.rglob("*") if p.is_file() and p.relative_to(OUT).as_posix() not in exclude)
    handoff = {p.relative_to(ROOT).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in files}
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "status": "frozen-proposal-host-observations-only", "base_revision": probe["base_revision"],
               "delivery_revision": revision.stdout.strip(), "delivery_revision_command": ["git", "rev-parse", "HEAD"],
               "supplemental_source_manifest": "supplemental-source-manifest.json",
               "selected_input_tree_sha256": probe["selected_input_tree_sha256"], "python": sys.version,
               "audit_command": ["python3", "verification/android-default-appearance-packaging-proposal/freeze_proposal.py"],
               "audit_output": "audit-output.json", "files": handoff,
               "scope": "Proposal and bounded pure host feasibility evidence; no product implementation, installed/native authority, public routing, release or GA promotion.",
               "native_runtime_or_capture_started": False, "root_metadata_modified": False,
               "cleanup": probe["cleanup"]}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    seal_files = files + [OUT / "receipt.json"]
    (OUT / "seal.sha256").write_text("".join(sha(p) + "  " + p.relative_to(ROOT).as_posix() + "\n" for p in seal_files))
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
