#!/usr/bin/env python3
"""Run the frozen raw transport corpus through the public Swift consumer in CI."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "verification/guest-capability-contract"
CONTRACT_SHA = "052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439"
MANIFEST_SHA = "1b3813aba9f72c13ed8c6da498d75b89a1d6615a727b0309ea35ad4fc739c258"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", choices=["debug", "release"], default="debug")
    parser.add_argument("--scratch-path", type=Path)
    args = parser.parse_args()
    manifest_bytes = (CORPUS / "cases.json").read_bytes()
    require(sha(manifest_bytes) == MANIFEST_SHA, "frozen corpus manifest changed")
    require(sha((ROOT / "contracts/guest-capability-transport-v1.json").read_bytes()) == CONTRACT_SHA,
            "frozen transport contract changed")
    manifest = json.loads(manifest_bytes)
    require(len(manifest["cases"]) == 90, "expected all 90 cases")
    operations = {op["swiftCase"]: op for op in manifest["operations"]}
    build = ["swift", "build", "--package-path", str(ROOT / "capabilities"),
             "-c", args.configuration, "--product", "guest-transport-probe"]
    if args.scratch_path:
        build += ["--scratch-path", str(args.scratch_path)]
    subprocess.run(build, cwd=ROOT, check=True)
    directory = subprocess.check_output(build + ["--show-bin-path"], cwd=ROOT, text=True).strip()
    probe = Path(directory) / "guest-transport-probe"
    counts = {"accept": 0, "reject": 0}
    for case in manifest["cases"]:
        data = (CORPUS / case["file"]).read_bytes()
        require(len(data) == case["bytes"] and sha(data) == case["sha256"], case["id"] + ": fixture drift")
        operation = operations[case["operation"]]
        if case["phase"] in ("arguments", "payload-boundaries"):
            mode = "arguments"
        elif case["phase"] == "wrappers":
            mode = "completion"
        elif case["phase"] == "outcomes":
            mode = "completion"
            metadata = {"abi": 1, "capability": operation["capability"],
                        "schemaHash": operation["schemaHash"], "operation": operation["operation"]}
            # Keep original hostile bytes intact inside their fixed envelope.
            data = json.dumps(metadata, separators=(",", ":")).encode()[:-1] + b',"outcome":' + data + b"}"
        else:
            raise RuntimeError("unknown fixture phase: " + case["phase"])
        result = subprocess.run([str(probe), mode, str(operation["tag"])],
                                input=data, capture_output=True, timeout=10, cwd=ROOT)
        accepted = case["expected"] == "accept"
        require(result.returncode == (0 if accepted else 1), case["id"] + ": unexpected exit")
        require(len(result.stdout) <= 524288 and len(result.stderr) <= 256, case["id"] + ": output bound")
        if accepted:
            require(not result.stderr, case["id"] + ": unexpected diagnostics")
            # Compare JSON values without conflating booleans with integer tokens.
            require(json.dumps(json.loads(data), sort_keys=True) == json.dumps(json.loads(result.stdout), sort_keys=True),
                    case["id"] + ": round trip changed value")
        else:
            require(not result.stdout and result.stderr == b"guest transport probe rejected input\n",
                    case["id"] + ": rejection leaked output or changed diagnostics")
        counts[case["expected"]] += 1
    print(json.dumps({"configuration": args.configuration, "matched": sum(counts.values()), **counts,
                      "contractSHA256": CONTRACT_SHA, "probeSHA256": sha(probe.read_bytes())}))


if __name__ == "__main__":
    main()
