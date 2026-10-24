#!/usr/bin/env python3
"""Verify the immutable codec/source/command packet and optionally seal it once."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument("--seal", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
output = Path(__file__).resolve().parent
run = output / "run-1"
receipt = json.loads((run / "receipt.json").read_text())
host = json.loads((run / "host/receipt.json").read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_archive(path, expected_sha, inputs):
    assert sha(path.read_bytes()) == expected_sha, str(path)
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == len(inputs)
        assert {m.name for m in members} == set(inputs)
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            assert not member.name.startswith("/") and ".." not in Path(member.name).parts
            assert sha(archive.extractfile(member).read()) == inputs[member.name], member.name


assert receipt["status"] == "passed"
assert receipt["cleanup"] == {"nested_postgres_stopped": True, "scratch_removed": True}
inputs = receipt["sourceInputs"]
assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["sourceTreeSHA256"]
check_archive(run / "source.tar.gz", receipt["sourceArchiveSHA256"], inputs)
for command in receipt["commands"]:
    assert command["exitCode"] == 0, command["label"]
    assert sha((run / command["output"]).read_bytes()) == command["sha256"], command["label"]
assert len(receipt["commands"]) == 9

names = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", receipt["baseRevision"], "hosted", "services"],
    cwd=root, text=True).splitlines()
assert set(inputs) == set(names) | set(receipt["liveOverrides"])
for name in names:
    if name not in receipt["liveOverrides"]:
        assert sha(subprocess.check_output(["git", "show", f'{receipt["baseRevision"]}:{name}'], cwd=root)) == inputs[name]
for name, expected in receipt["liveOverrides"].items():
    assert inputs[name] == expected and sha((root / name).read_bytes()) == expected, name

assert host["schema"] == 2 and host["status"] == "passed"
assert host["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert sha(json.dumps(host["inputs"], sort_keys=True, separators=(",", ":")).encode()) == host["source_tree_sha256"]
for name, expected in host["inputs"].items():
    assert inputs[name] == expected, name
fixture = "services/protocol/testdata/signed-release-v3.json"
assert fixture in host["inputs"] and sha((root / fixture).read_bytes()) == inputs[fixture]
check_archive(run / "host/source.tar.gz", host["source_archive_sha256"], host["inputs"])
for command in host["commands"]:
    assert command["exit_code"] == command.get("expected_exit_code", 0), command["label"]
    assert sha((run / "host" / command["log"]).read_bytes()) == command["sha256"], command["label"]
assert "Result: 35 passed" in (run / "host/tests.log").read_text()
go = (run / "go-shared-vectors.log").read_text()
assert "--- PASS: TestCanonicalRFC8949Subset" in go
assert "--- PASS: TestV3SharedCanonicalAndSignatureVector" in go
assert "FAIL" not in go

acceptance_path = output / "acceptance.json"
if args.seal:
    assert not acceptance_path.exists(), "Do not replace an existing acceptance seal"
    paths = set(receipt["liveOverrides"]) | {fixture}
    paths.update(str(p.relative_to(root)) for p in output.rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and p.name not in {"acceptance.json", "verification.log"})
    acceptance = {
        "schema": 1, "status": "accepted-host-artifact-encoding-component",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceRevision": receipt["baseRevision"],
        "sourceTreeSHA256": receipt["sourceTreeSHA256"],
        "hostedSourceTreeSHA256": host["source_tree_sha256"],
        "checks": {"newCodecTests": 11, "fullHostedTests": 35, "goVectorTests": 2,
                   "packagedRelease": "built; missing runtime configuration rejected with exit1",
                   "sourceInputs": len(inputs), "hostedInputsIncludingWireFixture": len(host["inputs"]),
                   "cleanup": receipt["cleanup"]},
        "review": [
            "Every data item, including encoded map keys, consumes a shared item budget; all headers and payload bytes consume output budget before final allocation.",
            "List scan is bounded before recursion; map size is bounded before pair materialization; text byte budget precedes UTF-8 validation.",
            "Map ordering compares encoded binary keys; no implicit atom/struct/number conversion or Unicode normalization.",
            "Existing exact v3 bytes, public test signatures and digest vectors are independently retained in the Go suite.",
            "Qualification uses committed hosted baseline plus six explicit owned overrides, excluding the concurrent identity owner and pending Mint dependency change."
        ],
        "limitations": receipt["limitations"] + [
            "Logical work/output bounds are not a total heap/RSS claim.",
            "Linux CI for the forthcoming product commit remains pending; no GA gate is closed."
        ],
        "bindings": {p: sha((root / p).read_bytes()) for p in sorted(paths)}
    }
    acceptance_path.write_text(json.dumps(acceptance, indent=2) + "\n")
else:
    acceptance = json.loads(acceptance_path.read_text())
    assert acceptance["sourceTreeSHA256"] == receipt["sourceTreeSHA256"]
    for name, expected in acceptance["bindings"].items():
        assert sha((root / name).read_bytes()) == expected, name

print(json.dumps({"status": "passed", "sourceInputs": len(inputs),
                  "hostedInputs": len(host["inputs"]), "bindings": len(acceptance["bindings"]),
                  "hostedTests": 35, "goVectorTests": 2}))
