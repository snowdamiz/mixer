"""Read-only verifier for the exact/normalized isolated transport composition."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODULE = "hosted/lib/mixer_hosted/billing/webhook_transport.ex"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())
digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def manifest(base, entries):
    for name, row in entries.items():
        path = base / name
        assert path.is_file() and not path.is_symlink(), name
        assert sha(path) == (row["sha256"] if isinstance(row, dict) else row), name
        if isinstance(row, dict):
            assert path.stat().st_size == row["bytes"], name


def archive(path, expected):
    with tarfile.open(path) as stream:
        seen = {}
        for member in stream.getmembers():
            name = PurePosixPath(member.name)
            assert member.isfile() and not name.is_absolute() and ".." not in name.parts and member.name not in seen
            seen[member.name] = hashlib.sha256(stream.extractfile(member).read()).hexdigest()
        assert seen == expected, path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preseal", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.preseal:
        seal = read(HERE / "seal.json")
        actual = {str(p.relative_to(ROOT)) for p in HERE.rglob("*") if p.is_file() and p != HERE / "seal.json"}
        actual.add("docs/stripe-webhook-transport-composition.md")
        assert actual == set(seal), "top-level file set changed"
        manifest(ROOT, seal)
    receipt = read(HERE / "receipt.json")
    assert receipt["acceptedAttempt"] == "attempt-4"
    assert receipt["producerSealSHA256"] == sha(ROOT / "verification/stripe-webhook-transport/seal.json") == "a36676ab1ab9bf1d0f98077d86d7f375b7c46a18c13cdb4bcd1adb24ce5d430d"
    assert receipt["reviewSealSHA256"] == sha(ROOT / "verification/stripe-webhook-transport-review/seal.json") == "a3d8b7677ce58b23246c61e76e0db13806c5cc53a41c44fd06aa3a75376a4f81"
    for attempt in receipt["attempts"]:
        folder = HERE / attempt["attempt"]
        seal = read(folder / "seal.json")
        actual = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() and p != folder / "seal.json"}
        assert actual == set(seal), folder
        manifest(folder, seal)
        r = read(folder / "receipt.json")
        assert r["status"] == attempt["status"] and r.get("failure") == attempt["failure"]
        clean = r["scratchCleanup"]
        assert clean["identityMatched"] and clean["pathAbsent"] and clean["ownedProcessGroupsEmpty"] and not clean["openHolders"]
        assert not Path(clean["path"]).exists()
        for command in r["commands"]:
            assert sha(folder / command["output"]) == command["sha256"]
            assert not command["timedOut"] and not command["groupCleanup"]["after"]
            expected = 1 if command["label"] == "scratch-holders" else 0
            if attempt["attempt"] == "attempt-1" and command["label"] == "format-check": expected = 1
            if attempt["attempt"] == "attempt-2" and command["label"] == "formatter-equivalence": expected = 1
            assert command["exitCode"] == expected, command["label"]
        baseline = read(folder / "baseline-inputs.json")
        assert len(baseline) == 71 and digest(baseline) == "ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc"
        if (folder / "source-inputs.json").exists():
            inputs = read(folder / "source-inputs.json")
            assert len(inputs) == 72 and {k: v for k, v in inputs.items() if k != MODULE} == baseline
            archive(folder / "source-closure.tar.gz", inputs)
            manifest(folder / "source", inputs)
    assert len(receipt["attempts"]) == len(list(HERE.glob("attempt-*"))) == 4
    assert [row["attempt"] for row in receipt["attempts"] if row["failure"]] == ["attempt-1", "attempt-2", "attempt-3"]
    for attempt in ["attempt-2", "attempt-3"]:
        folder = HERE / "source-recovery" / attempt
        recovered = read(folder / "receipt.json")
        assert recovered["status"] == "explicit-source-reconstruction-not-original-run-archive"
        assert not recovered["failedAttemptPromoted"] and recovered["exactDiffMatchesAcceptedNormalizedSource"]
        assert recovered["originalSealSHA256"] == sha(HERE / attempt / "seal.json")
        assert recovered["observedActualDiffSHA256"] == sha(HERE / attempt / "formatter-only.patch")
        inputs = read(folder / "source-inputs.json")
        assert len(inputs) == 72 and digest(inputs) == recovered["sourceDigest"] == receipt["sourceDigest"]
        archive(folder / "reconstructed-source-closure.tar.gz", inputs)
        assert sha(folder / "reconstructed-source-closure.tar.gz") == recovered["archiveSHA256"]
    chosen = HERE / "attempt-4"
    r = read(chosen / "receipt.json")
    inputs = read(chosen / "source-inputs.json")
    assert digest(inputs) == receipt["sourceDigest"] == r["sourceDigest"] == "789b7de9b46ef2ce65ad83a4c916dde9a513a8eaa68dfc073e4c65ec97e2ee93"
    raw = (chosen / "reviewed-webhook-transport.ex").read_text()
    normalized = (chosen / "source" / MODULE).read_text()
    assert sha(chosen / "reviewed-webhook-transport.ex") == receipt["reviewedCandidateSHA256"] == "62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0"
    assert sha(chosen / "source" / MODULE) == receipt["normalizedCandidateSHA256"] == "56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5"
    assert "".join(raw.split()) == "".join(normalized.split())
    exact_diff = "".join(difflib.unified_diff(raw.splitlines(keepends=True), normalized.splitlines(keepends=True), fromfile="reviewed/webhook_transport.ex", tofile="normalized/webhook_transport.ex"))
    assert (chosen / "formatter-only.patch").read_text() == exact_diff
    equivalence = read(chosen / "formatter-equivalence.json")
    assert equivalence["ast_equivalent"] and equivalence["token_stream_equivalent_ignoring_positions_and_eol"] and equivalence["tokens"] == 4344
    nested = read(chosen / "hosted/receipt.json")
    assert nested["status"] == "passed" and nested["inputs"] == inputs and nested["source_tree_sha256"] == receipt["sourceDigest"]
    assert nested["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
    archive(chosen / "hosted/source.tar.gz", inputs)
    assert sha(chosen / "hosted/source.tar.gz") == nested["source_archive_sha256"]
    for command in nested["commands"]:
        assert command["exit_code"] == command.get("expected_exit_code", 0)
        assert sha(chosen / "hosted" / command["log"]) == command["sha256"]
    assert "Result: 142 passed, 2 skipped" in (chosen / "hosted/tests.log").read_text()
    assert "test_clock_absent: true" in (chosen / "hosted/release-test-exclusion.log").read_text()
    assert "test_adapter_absent: true" in (chosen / "hosted/release-test-exclusion.log").read_text()
    assert "invalid or missing hosted setting: MIXER_HOSTED_ROLE" in (chosen / "hosted/release-missing-config.log").read_text()
    policy = read(chosen / "production-policy.json")
    assert policy["status"] == "passed" and len(policy["candidate_modules"]) == 4
    assert all(row["test_helper_atom_absent"] for row in policy["candidate_modules"])
    assert not any(policy[k] for k in ["test_helpers_loaded", "transport_capture_clock_or_adapter_argument", "role_started", "listener_started"])
    for row in policy["candidate_modules"]:
        filename = row["module"] + ".beam"
        assert (chosen / "production-app-ebin" / filename).is_file()
        assert (chosen / "test-app-ebin" / filename).is_file()
    archive(chosen / "dependency-source-closure.tar.gz", read(chosen / "dependency-source-inputs.json"))
    release = read(chosen / "production-release-inputs.json")
    archive(chosen / "production-release.tar.gz", release)
    for row in policy["candidate_modules"]:
        name = row["module"] + ".beam"
        assert release["lib/mixer_hosted-0.1.0/ebin/" + name] == sha(chosen / "production-app-ebin" / name)
    cleanup = read(HERE / "supplemental-cleanup.json")
    assert cleanup["postgresPortRefused"] and cleanup["postgresDataDirectoryAbsent"] and cleanup["postgresScratchDirectoryAbsent"]
    assert not any(receipt[k] for k in ["liveIntegrated", "publicAdmissionAccepted", "gaAccepted", "providerContacted", "nativeStarted", "catalogInspectorOrAuthorityReviewRetried"])
    if args.live:
        manifest(ROOT, inputs)
    print(json.dumps({"verified": True, "acceptedAttempt": "attempt-4", "failedAttemptsPreserved": 3,
                      "sourceInputs": 72, "hostPassed": 142, "hostSkipped": 2,
                      "productionTransportModules": 4, "testHelpersAbsent": True,
                      "liveChecked": args.live, "publicAdmissionAccepted": False, "gaAccepted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
