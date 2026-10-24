"""Root finite correction review; no native tools, dispatch or device queries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIX = ROOT / "verification/android-pointer-timing-correction"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    assert not (HERE / "receipt.json").exists(), "preserve existing review"
    support = load("root_timing_support", FIX / "support.py")
    sys.modules["support"] = support
    packet = load("root_timing_packet", FIX / "check_packet.py")
    before = packet.check()
    tests = load("root_timing_fixtures", FIX / "test_host.py")
    oracle = load("root_corrected_timing", FIX / "oracle.py")
    wrapper = load("root_corrected_wrapper", FIX / "run.py")
    runner, concrete, _ = wrapper.load_runner()
    assert concrete.encode() == (support.PRIOR / "runner-source-4/transformed_runner.py").read_bytes()
    assert runner._pointer_validate_native.__code__.co_filename == str(FIX / "oracle.py")
    assert runner._pointer_runtime_directory is support.runtime_directory
    write(HERE / "loaded-adaptation.json", runner._ADAPTATION)
    work = Path(tempfile.mkdtemp(prefix="mixer-pointer-timing-root-", dir="/private/tmp"))
    identity = work.stat().st_dev, work.stat().st_ino
    results = []

    def pair(rows, action="P01-1", index=0):
        sends = [r for r in rows if r["kind"] == "worker-send" and r["actionId"] == action]
        sent = sends[index]
        time = sent["event"]["eventTime"]
        entry = next(r for r in rows if r["kind"] == "activity-entry" and r["actionId"] == action and r["event"]["eventTime"] == time)
        exit_ = next(r for r in rows if r["kind"] == "activity-exit" and r["actionId"] == action and r["event"]["eventTime"] == time)
        return sent, entry, exit_

    def lower(native, rows):
        sent, entry, exit_ = pair(rows)
        entry["workerIndependentUptime"] = exit_["uptime"] = sent["workerBefore"]

    def upper(native, rows):
        sent, entry, exit_ = pair(rows)
        entry["workerIndependentUptime"] = exit_["uptime"] = sent["workerAfter"]

    def shortened_send(native, rows):
        sent, entry, exit_ = pair(rows)
        sent["workerAfter"] = entry["workerIndependentUptime"]

    def late_send_start(native, rows):
        sent, entry, exit_ = pair(rows)
        sent["workerBefore"] = exit_["uptime"]

    def wrong_worker(native, rows):
        sent, entry, exit_ = pair(rows)
        other, _, _ = pair(rows, index=1)
        entry["workerIndependentUptime"] = exit_["uptime"] = other["workerBefore"]

    def delayed_batch(native, rows):
        tests.PRIOR_TESTS.coalesce(native, rows)
        entry = next(r for r in rows if r["kind"] == "activity-entry" and r["event"]["history"])
        action, time = entry["actionId"], entry["event"]["eventTime"]
        sent = next(r for r in rows if r["kind"] == "worker-send" and r["actionId"] == action and r["event"]["eventTime"] == time)
        exit_ = next(r for r in rows if r["kind"] == "activity-exit" and r["actionId"] == action and r["event"]["eventTime"] == time)
        sent["workerBefore"] += 10
        sent["workerAfter"] += 10
        entry["workerIndependentUptime"] += 10
        exit_["uptime"] += 10

    try:
        cases = [("baseline", None, True), ("inclusive-lower", lower, True),
                 ("inclusive-upper", upper, True), ("delayed-current-batched-move", delayed_batch, True),
                 ("worker-end-before-delivery-exit", shortened_send, False),
                 ("worker-start-after-delivery-entry", late_send_start, False),
                 ("delivery-inside-next-worker-only", wrong_worker, False)]
        for name, mutate, expected in cases:
            directory = work / name
            native, metadata = tests.PRIOR_TESTS.synthetic_oracle_fixture(directory)
            rows = [json.loads(line) for line in (directory / "pointer-observations.jsonl").read_text().splitlines()]
            if mutate:
                mutate(native, rows)
            tests.PRIOR_TESTS.rewrite_rows(directory, native, rows)
            write(directory / "native.json", native)
            write(directory / "metadata.json", metadata)
            try:
                result = oracle.validate(native, directory, metadata)
                accepted, failure = True, None
            except ValueError as error:
                result, accepted, failure = None, False, str(error)
            results.append({"case": name, "expectedAccepted": expected, "accepted": accepted,
                            "failure": failure, "result": result})
            assert accepted == expected, results[-1]
            if not expected:
                assert "matching current-event synchronous worker interval" in failure
        findings = json.loads((support.REVIEW / "findings.json").read_text())
        for finding in findings:
            for name in finding["falseAcceptanceCases"]:
                directory = support.REVIEW / "host-review-2/reproductions" / name
                native = json.loads((directory / "native.json").read_text())
                metadata = json.loads((directory / "metadata.json").read_text())
                try:
                    oracle.validate(native, directory, metadata)
                except ValueError as error:
                    results.append({"case": name, "expectedAccepted": False, "accepted": False,
                                    "failure": str(error), "immutableFixture": str(directory.relative_to(ROOT))})
                else:
                    raise AssertionError("retained invalid observation accepted " + name)
        assert len(results) == 12
        assert packet.check() == before
        status = "passed-private-oracle-correction-root-review"
    finally:
        write(HERE / "results.json", results)
        files = [p for p in sorted(work.rglob("*")) if p.is_file()]
        manifest = {str(p.relative_to(work)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in files}
        write(HERE / "case-files.json", manifest)
        with tarfile.open(HERE / "cases.tar.gz", "w:gz") as archive:
            for path in files:
                archive.add(path, arcname=str(path.relative_to(work)), recursive=False)
        command = ["lsof", "-nP", "+D", str(work)]
        holders = subprocess.run(command, capture_output=True, timeout=30)
        (HERE / "cleanup-open-holders.log").write_bytes(holders.stdout + holders.stderr)
        assert holders.returncode == 1 and not holders.stdout and not holders.stderr
        assert (work.stat().st_dev, work.stat().st_ino) == identity
        shutil.rmtree(work)
        write(HERE / "cleanup.json", {"command": command, "exitCode": holders.returncode,
              "holderOutputEmpty": True, "device": identity[0], "inode": identity[1],
              "files": len(files), "bytes": sum(v["bytes"] for v in manifest.values()),
              "scratch": str(work), "scratchRemoved": not work.exists(), "nativeStarted": False})
    bound = dict(json.loads((FIX / "packet-seal.json").read_text())["files"])
    for path in [FIX / "packet-seal.json", HERE / "results.json", HERE / "cases.tar.gz", HERE / "case-files.json",
                 HERE / "cleanup.json", HERE / "cleanup-open-holders.log", HERE / "loaded-adaptation.json", Path(__file__)]:
        bound[str(path.relative_to(ROOT))] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    write(HERE / "receipt.json", {"schema": 1, "observedUTC": datetime.now(timezone.utc).isoformat(),
          "command": [sys.executable, "-B", str(Path(__file__))], "pythonVersion": sys.version,
          "status": status, "rootAcceptedForNativeDispatch": True, "nativeRuntime": "NOT RUN",
          "finiteIndependentControls": 12, "validAccepted": 4, "invalidRejected": 8,
          "producerTests": 55, "nativeAccepted": False, "gaAccepted": False, "bindings": bound})
    print(json.dumps({"status": status, "controls": 12, "bindings": len(bound), "scratchRemoved": True}))


if __name__ == "__main__":
    main()
