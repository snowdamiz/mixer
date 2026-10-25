#!/usr/bin/env python3
"""Retain the single selected attempt; retire only its restored owned products."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREP = ROOT / "verification/swift-retention-target-preparation"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    with (HERE / name).open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def no_holders(path, label):
    args = ["/usr/sbin/lsof", "-nP"]
    if path.is_dir():
        args += ["+D"]
    args.append(str(path))
    observed = subprocess.run(args, capture_output=True, timeout=30)
    (HERE / (label + ".stdout")).write_bytes(observed.stdout)
    (HERE / (label + ".stderr")).write_bytes(observed.stderr)
    assert observed.returncode == 1 and not observed.stdout and not observed.stderr
    return {"argv": args, "exitCode": observed.returncode, "holders": 0}


def main():
    assert not (HERE / "cleanup.json").exists()
    command = read(PREP / "commands/target-once/receipt.json")
    assert command["started"] and command["processGroupEmpty"]
    ps = subprocess.run(["/bin/ps", "-axo", "pid=,pgid=,stat=,command="],
                        capture_output=True, text=True, timeout=10)
    assert ps.returncode == 0 and not ps.stderr
    groups = [int(line.split(None, 3)[1]) for line in ps.stdout.splitlines() if line.strip()]
    assert command["processGroup"] not in groups

    shutil.copytree(PREP / "commands/target-once", HERE / "target-command")
    for name in ["root-selection.json", "target-attempt-started.json",
                 "target-once-events.json", "target-once-result.json"]:
        shutil.copyfile(PREP / name, HERE / name)
    for path in (HERE / "target-command").rglob("*"):
        if path.is_file():
            assert sha(path) == sha(PREP / "commands/target-once" / path.relative_to(HERE / "target-command"))

    scratch, binary = PREP / "owned-scratch", PREP / "bin/exact-tests"
    assert scratch.is_dir() and not scratch.is_symlink()
    assert scratch.resolve() == scratch and binary.is_file() and not binary.is_symlink()
    scratch_stat, binary_stat = scratch.stat(), binary.stat()
    retained = read(PREP / "binary.json")["retained"]
    assert sha(binary) == retained["sha256"] and binary.stat().st_size == retained["bytes"]
    compressed = Path(str(binary) + ".gz")
    compressed_before = sha(compressed)
    with gzip.open(compressed, "rb") as stream:
        payload = stream.read(retained["bytes"] + 1)
    assert len(payload) == retained["bytes"]
    assert hashlib.sha256(payload).hexdigest() == retained["sha256"]
    members = list(scratch.rglob("*"))
    assert all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in members)
    files = [path for path in members if path.is_file()]
    amount = sum(path.stat().st_size for path in files) + binary.stat().st_size
    checks = [no_holders(scratch, "scratch-holders"), no_holders(binary, "binary-holders")]
    assert (scratch.stat().st_dev, scratch.stat().st_ino) == (scratch_stat.st_dev, scratch_stat.st_ino)
    assert (binary.stat().st_dev, binary.stat().st_ino) == (binary_stat.st_dev, binary_stat.st_ino)
    shutil.rmtree(scratch)
    binary.unlink()
    assert not scratch.exists() and not binary.exists() and sha(compressed) == compressed_before
    # Preparation output and its compressed artifact must remain byte exact.
    seal = read(PREP / "prepared-seal.json")
    assert all(sha(PREP / name) == expected for name, expected in seal["files"].items())
    assert all(sha(ROOT / name) == expected for name, expected in seal["externalFiles"].items())
    save("cleanup.json", {"observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "processGroup": command["processGroup"], "processGroupAbsent": True,
         "signalSent": [], "holderChecks": checks, "deviceInodesStable": True,
         "ownedScratchAbsent": True, "restoredBinaryAbsent": True,
         "logicalBytesRemoved": amount, "filesRemoved": len(files) + 1,
         "existingGzipSHA256": compressed_before, "existingGzipUnchanged": True,
         "sealedPreparationMembersUnchanged": True,
         "nativeInstancesCreated": 0, "otherProjectsTouched": False})
    print(json.dumps({"attemptRetained": True, "ownedProductsRemoved": True,
                      "logicalBytesRemoved": amount, "preparationUnchanged": True}))


if __name__ == "__main__":
    main()
