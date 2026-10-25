#!/usr/bin/env python3
"""Read-only, standard-library evidence audit; never imports or executes packet code."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import sys
import tarfile
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "verification/swift-cost-retention-candidate"
PIN = "a71d7d9b4405b37e2130c464e0e149d82b2a1ff57f9f75f36cc0e8401bb50702"
LIVE = "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def safe_name(name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts, f"unsafe path {name}")
    require(not any(term in name.lower() for term in
                    ("hosted", "catalog", "authority", "worker", "outbound")),
            f"out-of-scope archive member {name}")


def test_results(stdout):
    rows = re.findall(r"^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; "
                      r"(\d+) ignored; (\d+) measured; (\d+) filtered out; "
                      r"finished in (\d+(?:\.\d+)?)s$", stdout, re.M)
    require(bool(rows), "missing test result")
    return [{"status": row[0], "passed": int(row[1]), "failed": int(row[2]),
             "ignored": int(row[3]), "measured": int(row[4]),
             "filtered": int(row[5]), "elapsedSecondsText": row[6]} for row in rows]


def traces(stdout):
    rows = [json.loads(line.split("COST_TRACE ", 1)[1])
            for line in stdout.splitlines() if "COST_TRACE " in line]
    result = {row["case"]: row for row in rows}
    require(len(result) == len(rows) == 6, "expected six unique raw trace rows")
    return result


def methods(stdout):
    return set(re.findall(r"^test (\S+) \.\.\.", stdout, re.M))


def main():
    seal_bytes = (PACKET / "seal.json").read_bytes()
    require(sha(seal_bytes) == PIN, "packet seal does not match assigned pin")
    require((PACKET / "seal.sha256").read_text().strip() == PIN, "seal sidecar mismatch")
    seal = json.loads(seal_bytes)
    require(seal["decision"] == "root-rejected-no-full-target-no-live-integration",
            "unexpected packet decision")
    inputs = {}
    for name, expected in seal["members"].items():
        safe_name(name)
        path = PACKET / name
        require(path.is_file() and not path.is_symlink(), f"not a regular member: {name}")
        data = path.read_bytes()
        observed = {"bytes": len(data), "sha256": sha(data)}
        require(observed == expected, f"sealed member mismatch: {name}")
        inputs[name] = observed
    actual = {str(p.relative_to(PACKET)) for p in PACKET.rglob("*") if p.is_file()}
    require(actual == set(inputs) | {"seal.json", "seal.sha256"}, "packet member-set mismatch")
    doc = ROOT / "docs/swift-cost-retention-candidate.md"
    require(sha(doc.read_bytes()) == seal["docSHA256"], "producer document mismatch")

    source_seals = load(PACKET / "source-seals.json")
    sources = {}
    for label, count in (("live-baseline", 132), ("baseline", 133), ("candidate", 134)):
        manifest_path = PACKET / f"{label}-source-manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        require(len(manifest) == count, f"source count mismatch: {label}")
        archive_path = PACKET / f"{label}-source.tar.gz"
        observed_members = {}
        total_bytes = 0
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            require(len(members) == count, f"archive member count mismatch: {label}")
            require(len({m.name for m in members}) == count, f"duplicate members: {label}")
            require({m.name for m in members} == set(manifest), f"archive names mismatch: {label}")
            for member in members:
                safe_name(member.name)
                require(member.isfile(), f"non-file archive member: {member.name}")
            # Names and allowed scope are checked before any member content is opened.
            for member in members:
                data = archive.extractfile(member).read()
                require(len(data) == member.size, f"short archive member: {member.name}")
                observed_members[member.name] = sha(data)
                total_bytes += len(data)
        require(observed_members == manifest, f"archive content mismatch: {label}")
        observed = {"archiveSHA256": sha(archive_path.read_bytes()), "fileCount": count,
                    "manifestSHA256": sha(manifest_bytes), "sourceBytes": total_bytes}
        require(observed == source_seals[label], f"source-seal mismatch: {label}")
        require(canonical(observed_members) == manifest_bytes, f"manifest encoding mismatch: {label}")
        sources[label] = observed

    live_manifest = load(PACKET / "live-baseline-source-manifest.json")
    require(sha(canonical(live_manifest)) == LIVE, "ordinary source manifest pin mismatch")
    live_names = {"Cargo.toml", "Cargo.lock"}
    for base in ("src", "include", "tests"):
        live_names |= {str(p.relative_to(ROOT / "vm"))
                       for p in (ROOT / "vm" / base).rglob("*") if p.is_file()}
    require(live_names == set(live_manifest), "current ordinary live file-set mismatch")
    current_live = {}
    for name in sorted(live_names):
        safe_name(name)
        path = ROOT / "vm" / name
        require(not path.is_symlink(), f"live source symlink: {name}")
        current_live[name] = sha(path.read_bytes())
    require(current_live == live_manifest, "current ordinary live source content mismatch")
    require(sha(canonical(current_live)) == LIVE, "current ordinary live manifest digest mismatch")

    commands = {}
    command_text = {}
    for directory in sorted((PACKET / "commands").iterdir()):
        require(directory.is_dir(), "unexpected command file")
        command = load(directory / "command.json")
        result = load(directory / "result.json")
        stdout = (directory / "stdout").read_bytes()
        stderr = (directory / "stderr").read_bytes()
        require(sha(stdout) == result["stdoutSHA256"], f"stdout mismatch: {directory.name}")
        require(sha(stderr) == result["stderrSHA256"], f"stderr mismatch: {directory.name}")
        manifest_sha = sha((directory / "source-manifest.json").read_bytes())
        require(manifest_sha == command["sourceManifestSHA256"], f"command source mismatch: {directory.name}")
        require(not result["timedOut"], f"timed out: {directory.name}")
        require("test" in command["argv"] and "--offline" in command["argv"]
                and "--release" in command["argv"], f"unexpected historical invocation: {directory.name}")
        text = stdout.decode()
        commands[directory.name] = {"exitCode": result["exitCode"],
                                    "sourceManifestSHA256": manifest_sha,
                                    "stdoutSHA256": sha(stdout), "stderrSHA256": sha(stderr),
                                    "testResults": test_results(text)}
        command_text[directory.name] = text

    expected_counts = {"baseline-original-swift": [39], "baseline-common": [3],
                       "baseline-final-swift": [42], "candidate-expanded-2": [49],
                       "baseline-generic-unit": [5], "candidate-generic-unit": [5],
                       "baseline-generic-integration": [9, 1],
                       "candidate-generic-integration": [9, 1]}
    for label, counts in expected_counts.items():
        observed = commands[label]
        require(observed["exitCode"] == 0, f"expected historical success: {label}")
        require([x["passed"] for x in observed["testResults"]] == counts, f"count mismatch: {label}")
        require(all(x["status"] == "ok" and x["failed"] == x["ignored"] == x["measured"] == 0
                    for x in observed["testResults"]), f"unexpected result scope: {label}")
    for label, passed, needle in (("candidate-original-swift", 38, "plan_reuse_observation"),
                                  ("candidate-expanded-1", 46, "cost_retention_all_pinned_and_hit_metadata_unchanged")):
        observed = commands[label]
        require(observed["exitCode"] == 101 and len(observed["testResults"]) == 1,
                f"missing preserved intermediate failure: {label}")
        row = observed["testResults"][0]
        require(row["status"] == "FAILED" and row["passed"] == passed and row["failed"] == 1,
                f"unexpected intermediate failure counts: {label}")
        require(needle in command_text[label], f"missing named failure: {label}")
    original = methods(command_text["baseline-original-swift"])
    common = methods(command_text["baseline-final-swift"])
    candidate = methods(command_text["candidate-expanded-2"])
    require((len(original), len(common), len(candidate)) == (39, 42, 49), "method-set count mismatch")
    require(original < common < candidate, "historical method sets are not nested")
    require(len(common - original) == 3 and len(candidate - common) == 7, "added method scope mismatch")
    require(commands["baseline-original-swift"]["sourceManifestSHA256"] == LIVE,
            "pristine command source mismatch")
    for label in expected_counts:
        source_label = "candidate" if label.startswith("candidate-") else "baseline"
        expected = LIVE if label == "baseline-original-swift" else sources[source_label]["manifestSHA256"]
        require(commands[label]["sourceManifestSHA256"] == expected, f"final command source mismatch: {label}")

    baseline_traces = traces(command_text["baseline-final-swift"])
    candidate_traces = traces(command_text["candidate-expanded-2"])
    require(set(baseline_traces) == set(candidate_traces), "trace pairing mismatch")
    paired = []
    summary = load(PACKET / "result-summary.json")
    recorded_traces = {row["case"]: row for row in summary["traces"]}
    for name in sorted(baseline_traces):
        baseline, candidate_row = baseline_traces[name], candidate_traces[name]
        require(baseline["instructions"] == candidate_row["instructions"] == 0, "guest execution claimed")
        ratio = Fraction(candidate_row["traceWork"], baseline["traceWork"])
        change = 100 * (ratio - 1)
        require(ratio > 1, f"trace is not a regression: {name}")
        recorded = recorded_traces[name]
        require(recorded["baseline"] == baseline and recorded["candidate"] == candidate_row,
                f"summary differs from raw trace: {name}")
        require(abs(recorded["workRatio"] - float(ratio)) < 1e-12
                and abs(recorded["workChangePercent"] - float(change)) < 1e-9,
                f"summary arithmetic mismatch: {name}")
        paired.append({"case": name, "baseline": baseline, "candidate": candidate_row,
                       "savedDecodes": baseline["decodes"] - candidate_row["decodes"],
                       "workRatioExact": str(ratio), "workRatio": float(ratio),
                       "workChangePercentExact": str(change), "workChangePercent": float(change)})

    parity = []
    for scope in ("generic-unit", "generic-integration"):
        left = command_text[f"baseline-{scope}"]
        right = command_text[f"candidate-{scope}"]
        # Exactly the elapsed-seconds token in Cargo result lines may change.
        pattern = r"(?m)(^test result: .*; finished in )\d+(?:\.\d+)?(s$)"
        left_normal = re.sub(pattern, r"\1<elapsed>\2", left)
        right_normal = re.sub(pattern, r"\1<elapsed>\2", right)
        require(left_normal == right_normal, f"generic stdout parity failure: {scope}")
        parity.append({"scope": scope, "rawIdentical": left == right,
                       "elapsedSecondsOnlyNormalizedSHA256": sha(left_normal.encode()),
                       "normalizationPattern": pattern})

    cleanup = load(PACKET / "cleanup.json")
    preflight = load(PACKET / "cleanup-preflight.json")
    require(not (PACKET / ".scratch").exists() and not (PACKET / ".scratch").is_symlink(),
            "scratch remains")
    require(cleanup["removed"] and cleanup["signalsSent"] == [] and cleanup["holderChecks"] == 2
            and cleanup["identityAndMutationCheck"] and preflight["sourceArchivesVerified"],
            "cleanup receipt incomplete")
    for label in ("first", "second"):
        check = preflight[label]
        require(check["processMatches"] == [] and check["holderExit"] == 1
                and check["holderStdout"] == check["holderStderr"] == "", "cleanup preflight not clear")
    entries = preflight["inventory"]["entries"]
    require(len([x for x in entries if not x["directory"]]) == cleanup["regularFiles"] == 438,
            "cleanup file count mismatch")
    require(len([x for x in entries if x["directory"]]) + 1 == cleanup["directories"] == 68
            and set(preflight["inventory"]["root"]) == {"device", "inode", "mtimeNs"},
            "cleanup directory count mismatch")
    require(sum(x["bytes"] for x in entries if not x["directory"]) == cleanup["logicalBytes"] == 218566668,
            "cleanup bytes mismatch")
    decision = load(PACKET / "root-decision.json")
    require(decision["decision"] == "rejected-on-finite-evidence" and not decision["fullTargetRun"]
            and not decision["liveIntegration"], "root rejection scope mismatch")
    print(json.dumps({"schema": 1, "verdict": "accept-recorded-rejection", "findings": [],
                      "scope": "independent read-only retained-evidence audit; no correctness acceptance",
                      "packetSealSHA256": PIN, "producerDocSHA256": seal["docSHA256"],
                      "inputMembers": inputs, "sourceArchives": sources,
                      "currentLive": {"fileCount": 132, "manifestSHA256": LIVE},
                      "historicalCommands": commands, "pairedRawTraces": paired,
                      "methodScope": {"pristine": 39, "commonAddedBaseline": 42, "candidate": 49,
                                      "sharedAddedNames": sorted(common-original),
                                      "candidateOnlyNames": sorted(candidate-common)},
                      "genericParity": parity, "cleanup": {"currentScratchAbsent": True,
                                                               "historicalReceipt": cleanup},
                      "tools": {"python": sys.version, "executable": sys.executable,
                                "executableSHA256": sha(Path(sys.executable).read_bytes()),
                                "platform": platform.platform(), "machine": platform.machine(),
                                "auditSHA256": sha(Path(__file__).read_bytes())},
                      "limitations": ["No product or candidate test was executed, no archive extracted, and no scratch restored.",
                                      "Historical stdout and command receipts were verified; runtime behavior and policy correctness were not independently rerun or accepted.",
                                      "Named-value accounting and preserved-body implementation claims were not independently audited.",
                                      "Cleanup process/holder and stable-identity checks are retained historical evidence; current scratch absence was directly checked.",
                                      "No full target/reactor, native/UI/capture, physical device, network/provider, signing, publication, customer, FieldLog release, or GA qualification.",
                                      "No Git command or frozen hosted/rejected Worker V2 lane access."]},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
