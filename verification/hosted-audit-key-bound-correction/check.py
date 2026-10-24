#!/usr/bin/env python3
"""Verify frozen source/evidence without executing tests or starting services."""
import hashlib
import json
import pathlib
import statistics
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    for manifest in (read(HERE / "seal.json"), read(HERE / "receipt.json")):
        for path, digest in manifest["bindings"].items():
            assert sha((ROOT / path).read_bytes()) == digest, path
    receipt = read(HERE / "receipt.json")
    run = read(HERE / "run-1/receipt.json")
    assert run["status"] == "passed" and all(run["cleanup"].values())
    assert run["dependencyCount"] == 21 and run["fullHostedReplay"]
    for command in run["commands"]:
        assert command["exitCode"] == 0, command["label"]
        assert sha((HERE / "run-1" / command["log"]).read_bytes()) == command["sha256"]
    for name, field in (("overlay-source", "overlayInputs"), ("independent-source", "independentInputs")):
        expected = read(HERE / "run-1" / (name + ".json"))
        assert expected == run[field]
        with tarfile.open(HERE / "run-1" / (name + ".tar.gz")) as archive:
            members = archive.getmembers()
            assert len(members) == len(expected) == len({m.name for m in members})
            for member in members:
                assert member.isfile() and member.name in expected
                assert sha(archive.extractfile(member).read()) == expected[member.name]
        for path, digest in run["baselineInputs"].items():
            assert expected[path] == digest
    for path, digest in receipt["overlay"].items():
        assert sha((HERE / "candidate" / path).read_bytes()) == digest
        assert run["overlayInputs"]["hosted/" + path] == digest
    full = read(HERE / "run-1/full-hosted/receipt.json")
    assert full["status"] == "passed" and all(full["cleanup"].values())
    assert full["inputs"] == run["overlayInputs"]
    for command in full["commands"]:
        assert command["exit_code"] == command.get("expected_exit_code", 0)
        assert sha((HERE / "run-1/full-hosted" / command["log"]).read_bytes()) == command["sha256"]
    with tarfile.open(HERE / "run-1/full-hosted/source.tar.gz") as archive:
        assert len(archive.getmembers()) == len(full["inputs"])
        for member in archive.getmembers():
            assert member.isfile() and member.name in full["inputs"]
            assert sha(archive.extractfile(member).read()) == full["inputs"][member.name]
    assert "Result: 12 passed" in (HERE / "run-1/producer-focused.log").read_text()
    assert "Result: 105 passed, 2 skipped" in (HERE / "run-1/full-hosted/tests.log").read_text()
    assert "Result: 6 passed" in (HERE / "run-1/independent-focused.log").read_text()
    review = ROOT / "verification/hosted-audit-codec-review"
    for name in ("independent_test.exs", "independent-vectors.json", "key-bound-probe.exs"):
        assert (HERE / name).read_bytes() == (review / name).read_bytes()
    original = ROOT / "verification/hosted-audit-codec-integration/candidate"
    for name in ("coherent-vectors.json", "retained-chains.json"):
        path = pathlib.Path("test/fixtures/audit") / name
        assert (HERE / "candidate" / path).read_bytes() == (original / path).read_bytes()
    source = pathlib.Path("lib/mixer_hosted/audit/upload_event.ex")
    expected = (original / source).read_text().replace(
        "Enum.sort(Map.keys(row)) == Enum.sort(@row_keys)",
        "Enum.all?(@row_keys, &Map.has_key?(row, &1))"
    ).replace(
        "Enum.sort(Map.keys(d)) == Enum.sort(@display_keys)",
        "Enum.all?(@display_keys, &Map.has_key?(d, &1))"
    )
    assert (HERE / "candidate" / source).read_text() == expected
    measurements = read(HERE / "run-1/key-bound-probe.log")["measurements"]
    assert len(measurements) == 36 and all(m["result"] == "rejected" for m in measurements)
    medians = {label: {str(size): statistics.median(m["elapsed_microseconds"] for m in measurements
               if m["label"] == label and m["key_or_value_bytes"] == size)
               for size in (1024, 1048576, 4194304)} for label in {m["label"] for m in measurements}}
    assert medians == receipt["timingMediansMicrosecondsPer20Calls"]
    print(json.dumps({"verified": True, "bindings": len(receipt["bindings"]), "focusedTests": 12,
                      "hostedPassed": 105, "explicitLinuxOnlySkips": 2, "independentCases": 107,
                      "independentEdges": 8, "liveIntegrated": False, "independentCorrectionReviewPending": True}))


if __name__ == "__main__":
    main()
