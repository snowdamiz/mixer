#!/usr/bin/env python3
"""Check frozen independent review evidence without tests or services."""
import hashlib
import json
import pathlib
import statistics
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORRECTION = ROOT / "verification/hosted-audit-key-bound-correction"
ORIGINAL = ROOT / "verification/hosted-audit-codec-integration"
sha = lambda body: hashlib.sha256(body).hexdigest()
tree_sha = lambda manifest: sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())


def read(path):
    return json.loads(path.read_text())


def archive_bytes(path, manifest):
    result = {}
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        assert len(members) == len(manifest) == len({m.name for m in members})
        for member in members:
            name = pathlib.PurePosixPath(member.name)
            assert member.isfile() and not name.is_absolute() and ".." not in name.parts
            body = archive.extractfile(member).read()
            assert member.name in manifest and sha(body) == manifest[member.name], member.name
            result[member.name] = body
    return result


def main():
    receipt = read(HERE / "receipt.json")
    for manifest in (read(HERE / "seal.json"), receipt):
        for name, digest in manifest["bindings"].items():
            assert sha((ROOT / name).read_bytes()) == digest, name
    assert receipt["status"] == "passed-independent-correction-review"
    assert receipt["findings"] == []
    assert receipt["liveIntegratedByReview"] is False and receipt["gaAccepted"] is False
    assert sha((CORRECTION / "receipt.json").read_bytes()) == receipt["frozenCorrectionReceiptSHA256"]
    for packet in (CORRECTION, ORIGINAL, ROOT / "verification/hosted-audit-codec-review"):
        for manifest in (read(packet / "seal.json"), read(packet / "receipt.json")):
            for name, digest in manifest["bindings"].items():
                assert sha((ROOT / name).read_bytes()) == digest, name
    run = read(HERE / "run-1/receipt.json")
    assert run["status"] == "passed" and all(run["cleanup"].values())
    assert run["dependencyCount"] == 21
    assert run["freshResults"] == receipt["freshResults"]
    for command in run["commands"]:
        assert command["exitCode"] == 0, command["label"]
        assert sha((HERE / "run-1" / command["log"]).read_bytes()) == command["sha256"]
    for name, count in (("producer-focused", 12), ("retained-independent", 6), ("new-independent", 2)):
        assert f"Result: {count} passed" in (HERE / "run-1" / (name + ".log")).read_text()
    review_manifest = read(HERE / "run-1/review-source.json")
    assert review_manifest == run["reviewInputs"]
    assert tree_sha(review_manifest) == receipt["reviewSourceTreeSHA256"]
    reviewed = archive_bytes(HERE / "run-1/review-source.tar.gz", review_manifest)
    inputs = read(CORRECTION / "run-1/overlay-source.json")
    assert inputs == run["sourceInputs"]
    assert tree_sha(inputs) == receipt["correctedSourceTreeSHA256"]
    corrected = archive_bytes(CORRECTION / "run-1/overlay-source.tar.gz", inputs)
    for name, body in corrected.items():
        assert reviewed[name] == body
    retained = read(CORRECTION / "run-1/independent-source.json")
    archive_bytes(CORRECTION / "run-1/independent-source.tar.gz", retained)
    for name, digest in retained.items():
        assert review_manifest[name] == digest
    original_run = read(ORIGINAL / "run-5/receipt.json")
    original = archive_bytes(ORIGINAL / "run-5/source.tar.gz", original_run["testedSource"])
    changed = sorted(name for name in corrected if original[name] != corrected[name])
    assert changed == run["integrity"]["onlyChangedFilesVersusOriginal"]
    module = "hosted/lib/mixer_hosted/audit/upload_event.ex"
    original_text = original[module].decode()
    expected = original_text.replace("Enum.sort(Map.keys(row)) == Enum.sort(@row_keys)",
                                     "Enum.all?(@row_keys, &Map.has_key?(row, &1))").replace(
        "Enum.sort(Map.keys(d)) == Enum.sort(@display_keys)",
        "Enum.all?(@display_keys, &Map.has_key?(d, &1))")
    assert corrected[module].decode() == expected
    assert sha(corrected[module]) == receipt["reviewedModuleSHA256"]
    assert reviewed["hosted/test/key_bound_review/original_upload_event.exs"].decode() == original_text.replace(
        "defmodule MixerHosted.Audit.UploadEvent do", "defmodule MixerHosted.Audit.OriginalUploadEventByReview do", 1)
    assert reviewed["hosted/test/key_bound_review/key_shape_review_test.exs"] == (HERE / "run-1/formatted-key_shape_review_test.exs").read_bytes()
    assert read(HERE / "run-1/dependencies.json") == read(CORRECTION / "run-1/dependencies.json")
    assert read(HERE / "run-1/dependencies.json") == read(ORIGINAL / "run-5/dependencies.json")
    full = read(CORRECTION / "run-1/full-hosted/receipt.json")
    assert sha((CORRECTION / "run-1/full-hosted/receipt.json").read_bytes()) == receipt["reusedFullHostedReceiptSHA256"]
    assert full["status"] == "passed" and all(full["cleanup"].values())
    assert full["inputs"] == inputs and full["source_tree_sha256"] == tree_sha(inputs)
    assert archive_bytes(CORRECTION / "run-1/full-hosted/source.tar.gz", full["inputs"]) == corrected
    for command in full["commands"]:
        assert command["exit_code"] == command.get("expected_exit_code", 0)
        assert sha((CORRECTION / "run-1/full-hosted" / command["log"]).read_bytes()) == command["sha256"]
    assert "Result: 105 passed, 2 skipped" in (CORRECTION / "run-1/full-hosted/tests.log").read_text()
    measurements = read(HERE / "run-1/key-bound-probe.log")["measurements"]
    assert len(measurements) == 36 and all(m["result"] == "rejected" and m["calls"] == 20 for m in measurements)
    medians = {label: {str(size): statistics.median(m["elapsed_microseconds"] for m in measurements
                       if m["label"] == label and m["key_or_value_bytes"] == size)
                       for size in (1024, 1048576, 4194304)} for label in {m["label"] for m in measurements}}
    assert medians == run["timingMediansMicrosecondsPer20Calls"] == receipt["timingMediansMicrosecondsPer20Calls"]
    new_log = (HERE / "run-1/new-independent.log").read_text()
    assert '"exact_cardinality_single_replacements":546' in new_log
    assert '"foreign_key_forms":21' in new_log
    assert '"producer_vectors":80' in new_log and '"captured_rows":185' in new_log
    assert '"independent_coherent_cases":107' in new_log and '"independent_edges":8' in new_log
    assert not (HERE / "__pycache__").exists()
    print(json.dumps({"verified": True, "bindings": len(receipt["bindings"]), "findings": 0,
                      "focusedTests": 12, "retainedIndependentTests": 6, "newReviewTests": 2,
                      "finiteExactCardinalityReplacements": 546,
                      "reusedHostedPassed": 105, "explicitLinuxOnlySkips": 2,
                      "liveIntegratedByReview": False, "gaAccepted": False}))


if __name__ == "__main__":
    main()
