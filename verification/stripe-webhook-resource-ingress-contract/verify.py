#!/usr/bin/env python3
"""Read-only contract/evidence checks. Does not test Linux/server behavior."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXPECTED_BASELINE = "1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997"


def read(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def same_json(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same_json(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same_json(a, b) for a, b in zip(actual, expected))
    return actual == expected


def locations(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from locations(child, path + (key,))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from locations(child, path + (key,))


def replaced(value, path, replacement):
    if not path:
        return replacement
    value = copy.deepcopy(value)
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    return value


def reject_mutations(profile):
    count = 0
    for path, value in locations(profile):
        require(not same_json(replaced(profile, path, None), profile), f"null accepted at {path}")
        count += 1
        if isinstance(value, dict):
            candidate = dict(value, unexpected="fail-closed")
            require(not same_json(replaced(profile, path, candidate), profile), f"unknown key accepted at {path}")
            count += 1
            for key in value:
                candidate = dict(value)
                del candidate[key]
                require(not same_json(replaced(profile, path, candidate), profile), f"missing key accepted at {path}")
                count += 1
        elif isinstance(value, list):
            require(not same_json(replaced(profile, path, value + ["unexpected"]), profile), f"extra list item accepted at {path}")
            count += 1
        elif type(value) is int:
            for invalid in [value - 1, value + 1, str(value), bool(value), float(value)]:
                require(not same_json(replaced(profile, path, invalid), profile), f"nonexact integer accepted at {path}")
                count += 1
        elif type(value) is bool:
            require(not same_json(replaced(profile, path, int(value)), profile), f"integer accepted for boolean at {path}")
            require(not same_json(replaced(profile, path, not value), profile), f"changed boolean accepted at {path}")
            count += 2
        elif isinstance(value, str):
            for invalid in ["", value + "-override", {"value": value}]:
                require(not same_json(replaced(profile, path, invalid), profile), f"changed string accepted at {path}")
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="also compare current repository and installed dependency inputs")
    args = parser.parse_args()
    seal = read("seal.json")
    require(seal["schema"] == 1, "seal schema")
    actual_packet = {str(p.relative_to(ROOT)) for p in HERE.rglob("*") if p.is_file() and p.name != "seal.json"}
    expected_packet = {p for p in seal["files"] if p.startswith(str(HERE.relative_to(ROOT)) + "/")}
    require(actual_packet == expected_packet, "unsealed/missing packet file")
    for path, expected in seal["files"].items():
        p = ROOT / path
        require(not p.is_symlink() and p.resolve().is_relative_to(ROOT), f"unsafe binding {path}")
        require(sha(p) == expected, f"packet binding mismatch: {path}")

    profile, schema, matrix = read("profile.json"), read("profile.schema.json"), read("matrix.json")
    require(schema["type"] == "object" and same_json(profile, schema["const"]), "closed const schema mismatch")
    require(profile["selection"] == "proposal-root-selection-pending", "proposal selection changed")
    require(profile["publicTrailerPolicy"] == "unselected", "public trailer choice changed")
    require(profile["productionActivated"] is False and profile["dependenciesAdded"] == [], "activation or dependency drift")
    require(profile["logical"] == {"connections": 16, "streamsPerConnection": 1, "requestsPerConnection": 1,
                                   "handshakeMs": 1000, "headersMs": 1000, "captureMs": 5000,
                                   "outerMs": 7000, "maxBodyBytes": 1048576}, "logical profile changed")
    require(profile["cgroup"] == {"version": 2, "memory.max": 1073741824, "memory.high": 805306368,
                                  "memory.swap.max": 0, "memory.oom.group": 1,
                                  "cpu.max": "25000 100000", "cpu.weight": 100, "pids.max": 128}, "proposed OS profile changed")
    negative_checks = reject_mutations(profile)
    rows = matrix["rows"]
    expected_ids = {f"R{i:02}" for i in range(1, 19)} | {f"T{i:02}" for i in range(1, 6)} | {f"I{i:02}" for i in range(1, 8)}
    require(len(rows) == 30 and {r["id"] for r in rows} == expected_ids, "finite matrix incomplete")
    require(all(r["status"] == "pending-runtime" and r["requiredEvidence"] for r in rows), "runtime claim introduced")
    require(matrix["runtimeCasesExecuted"] == 0 and matrix["gaAccepted"] is False, "runtime/GA claim introduced")
    require({r["gate"] for r in rows} == {"P11", "P12", "P14"}, "scope drift")
    sources = read("external-sources.json")
    require(len(sources["sources"]) == 5, "external source count changed")
    require(all(s["url"].startswith("https://developers.cloudflare.com/") for s in sources["sources"]), "nonofficial external fact source")
    require(sources["runtimeProviderContacted"] is False, "provider runtime claim")
    bindings = read("source-bindings.json")
    require(bindings["baselineSourceDigest"] == EXPECTED_BASELINE and len(bindings["baselineInputs"]) == 73, "baseline closure changed")
    canonical = json.dumps(bindings["baselineInputs"], sort_keys=True, separators=(",", ":")).encode()
    require(hashlib.sha256(canonical).hexdigest() == EXPECTED_BASELINE, "baseline map digest mismatch")
    require(bindings["noGitOperation"] is True, "Git scope changed")
    source_map = read("source-map.json")
    for row in source_map["files"]:
        for finding in row["findings"]:
            require(1 <= finding["start"] <= finding["end"] <= row["lineCount"], "invalid source finding range")
    if args.live:
        for path, expected in {**bindings["baselineInputs"], **bindings["additionalInputs"]}.items():
            require(sha(ROOT / path) == expected, f"live input changed: {path}")
        for row in source_map["files"]:
            p = ROOT / row["path"]
            require(sha(p) == row["sha256"], f"source map drift: {p}")
            lines = p.read_text().splitlines()
            for finding in row["findings"]:
                require("\n".join(lines[finding["start"]-1:finding["end"]]) == finding["excerpt"], "source excerpt drift")
    receipt = read("authoring-receipt.json")
    require(receipt["runtimeCasesExecuted"] == 0 and receipt["productionActivated"] is False and receipt["providerContacted"] is False, "authoring scope drift")
    require(all(receipt["cleanup"][name] is False for name in ["roleStarted", "listenerStarted", "stressHelperStarted", "databaseStarted", "daemonStarted", "nativeInstanceStarted", "ownedScratchCreated"]), "cleanup scope drift")
    print(json.dumps({"status": "passed-contract-and-evidence-checks-only", "live": args.live,
                      "sealedFiles": len(seal["files"]), "baselineSourceInputs": 73,
                      "additionalSourceInputs": len(bindings["additionalInputs"]),
                      "inspectedSourceFiles": len(source_map["files"]),
                      "negativeContractMutationsRejected": negative_checks,
                      "pendingRuntimeMatrixCases": len(rows), "runtimeCasesExecuted": 0,
                      "rootSelection": "pending", "publicTrailerPolicy": "unselected",
                      "gaAccepted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
