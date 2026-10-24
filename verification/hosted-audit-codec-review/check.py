#!/usr/bin/env python3
"""Read-only independent review packet verification; no services/tests started."""
import hashlib
import json
import pathlib
import statistics
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHA = lambda b: hashlib.sha256(b).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main():
    seal = load(HERE / "seal.json")
    for path, digest in seal["bindings"].items():
        assert SHA((ROOT / path).read_bytes()) == digest, path
    review = load(HERE / "receipt.json")
    for path, digest in review["bindings"].items():
        assert SHA((ROOT / path).read_bytes()) == digest, path
    producer = load(ROOT / "verification/hosted-audit-codec-integration/receipt.json")
    for path, digest in producer["bindings"].items():
        assert SHA((ROOT / path).read_bytes()) == digest, path
    assert len(producer["bindings"]) == 101
    assert review["status"] == "correction-required" and not review["integrationAccepted"]
    runs = []
    for number in (1, 2):
        output = HERE / ("run-" + str(number))
        receipt = load(output / "receipt.json")
        assert receipt["status"] == ("failed" if number == 1 else "passed")
        assert receipt["cleanup"] == {"ownedScratchRemoved": True}
        for command in receipt["commands"]:
            assert SHA((output / command["log"]).read_bytes()) == command["sha256"]
            if command["label"] == "independent-focused" and number == 1:
                assert command["exitCode"] == 2
            else:
                assert command["exitCode"] == 0
        for prefix, key in (("overlay-source", "overlayInputs"), ("independent-source", "independentInputs")):
            expected = load(output / (prefix + ".json"))
            assert expected == receipt[key]
            with tarfile.open(output / (prefix + ".tar.gz")) as archive:
                members = archive.getmembers()
                assert len(members) == len(expected)
                assert len({m.name for m in members}) == len(members)
                for member in members:
                    assert member.isfile() and member.name in expected
                    assert SHA(archive.extractfile(member).read()) == expected[member.name]
            for path, digest in receipt["baselineInputs"].items():
                assert expected[path] == digest, "baseline altered: " + path
        assert receipt["dependencyCount"] == 21
        assert load(output / "dependencies.json") == load(ROOT / "verification/hosted-audit-codec-integration/run-5/dependencies.json")
        assert "Result: 11 passed" in (output / "producer-focused.log").read_text()
        runs.append(receipt)
    assert runs[0]["overlayInputs"] == runs[1]["overlayInputs"]
    for run, source in zip(runs, review["sourceManifests"]):
        assert source["revision"] == run["sourceRevision"] == review["candidateRevision"]
        for name, key in (("overlayTreeSHA256", "overlayInputs"), ("independentTreeSHA256", "independentInputs")):
            assert source[name] == SHA(json.dumps(run[key], sort_keys=True, separators=(",", ":")).encode())
        assert run["independentInputs"]["hosted/test/independent_review/independent-vectors.json"] == SHA((HERE / "independent-vectors.json").read_bytes())
    assert any(c["label"] == "full-hosted" for c in runs[0]["commands"])
    assert not runs[1]["fullHostedReplay"]
    full = load(HERE / "run-1/full-hosted/receipt.json")
    assert full["status"] == "passed" and all(full["cleanup"].values())
    assert full["inputs"] == runs[0]["overlayInputs"]
    assert "Result: 104 passed, 2 skipped" in (HERE / "run-1/full-hosted/tests.log").read_text()
    for command in full["commands"]:
        assert command["exit_code"] == command.get("expected_exit_code", 0)
        assert SHA((HERE / "run-1/full-hosted" / command["log"]).read_bytes()) == command["sha256"]
    with tarfile.open(HERE / "run-1/full-hosted/source.tar.gz") as archive:
        assert len(archive.getmembers()) == len(full["inputs"])
        for member in archive.getmembers():
            assert member.isfile() and member.name in full["inputs"]
            assert SHA(archive.extractfile(member).read()) == full["inputs"][member.name]
    assert "not an already existing atom" in (HERE / "run-1/independent-focused.log").read_text()
    assert "Result: 1/6 passed" in (HERE / "run-1/independent-focused.log").read_text()
    assert "Result: 6 passed" in (HERE / "run-2/independent-focused.log").read_text()
    vectors = load(HERE / "independent-vectors.json")
    assert len(vectors["cases"]) == 107 and len(vectors["edges"]) == 8
    assert sum(case["accepted"] for case in vectors["cases"]) == 46
    for case in vectors["cases"]:
        row = case["row"]
        expected = hashlib.sha256(b"mixer.hosted.audit.v1\0" + bytes.fromhex(row["event_cbor"])).hexdigest()
        assert expected == row["event_hash"] == row["display_json"]["hash"].lower()
    for edge in vectors["edges"]:
        for row in (edge["current"], edge["previous"]):
            if row:
                assert hashlib.sha256(b"mixer.hosted.audit.v1\0" + bytes.fromhex(row["event_cbor"])).hexdigest() == row["event_hash"]
    measurements = load(HERE / "run-2/key-bound-probe.log")["measurements"]
    assert len(measurements) == 36 and all(m["result"] == "rejected" and m["calls"] == 20 for m in measurements)
    medians = {}
    for label in sorted({m["label"] for m in measurements}):
        medians[label] = {str(size): statistics.median(m["elapsed_microseconds"] for m in measurements
                          if m["label"] == label and m["key_or_value_bytes"] == size)
                          for size in (1024, 1048576, 4194304)}
    assert medians == review["keyBoundObservation"]["medianMicrosecondsPer20Calls"]
    assert len(review["findings"]) == 1 and review["findings"][0]["priority"] == "P2"
    print(json.dumps({"verified": True, "reviewStatus": review["status"], "producerBindings": 101,
                      "hostedPassed": 104, "explicitLinuxOnlySkips": 2, "independentTests": 6,
                      "independentCases": 107, "independentEdges": 8, "requiredCorrections": 1,
                      "ownedAttemptsCleaned": 2, "integrationAccepted": False}))


if __name__ == "__main__":
    main()
