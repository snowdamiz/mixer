"""One root-released isolated model compile/test operation; no retries."""
import time
START = time.monotonic()
from pathlib import Path
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LANE = ROOT / "verification/swift-root-bound-dispatch-region-model-v2"
OUT = Path(__file__).with_name("dispatch-region-model-v2-runtime")
PLAN_SHA = "5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8"
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
SEEN = []
OWNED = []
ERRORS = []

def deadline(offset):
    if time.monotonic() - START >= offset:
        raise RuntimeError("deadline exceeded: " + str(offset))

def digest(path, offset=53.5):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(262144):
            deadline(offset)
            h.update(chunk)
    return h.hexdigest()

def save(name, value):
    deadline(55)
    with (OUT / name).open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")

def absent(pid):
    try:
        os.killpg(pid, 0)
        return False
    except ProcessLookupError:
        return True

def exited(child):
    return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None

def close(record):
    child = record["child"]
    if record.get("reaped"):
        record["group_absent"] = absent(child.pid)
        return record["group_absent"]
    if not record.get("custody"):
        return False
    # Keep the original leader unreaped until every group signal is finished.
    for sig, grace in [(signal.SIGTERM, 0.1), (signal.SIGKILL, 0.0)]:
        deadline(49)
        try:
            os.killpg(child.pid, sig)
            record.setdefault("signals", []).append(sig.name)
        except ProcessLookupError:
            pass
        until = min(START + 49, time.monotonic() + grace)
        while time.monotonic() < until:
            time.sleep(0.005)
    while not exited(child):
        deadline(49)
        time.sleep(0.005)
    child.wait(timeout=0)
    record.update(reaped=True, returncode=child.returncode)
    while not absent(child.pid):
        deadline(49)
        time.sleep(0.005)
    record["group_absent"] = True
    return True

def command(spec, environment, offset):
    deadline(offset)
    if SEEN:
        raise RuntimeError("signal before command")
    child = subprocess.Popen(spec["argv"], cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    record = {"child": child, "pid": child.pid, "kind": spec["kind"], "argv": spec["argv"],
              "environment": environment, "cwd": str(ROOT), "start_seconds": time.monotonic() - START}
    OWNED.append(record)
    record.update(pgid=os.getpgid(child.pid), sid=os.getsid(child.pid))
    record["custody"] = record["pid"] == record["pgid"] == record["sid"]
    if not record["custody"]:
        raise RuntimeError("child group/session mismatch")
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    for key, stream in [("stdout", child.stdout), ("stderr", child.stderr)]:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, key)
    try:
        while selector.get_map() or not record.get("reaped"):
            deadline(offset)
            if SEEN:
                raise RuntimeError("signal during command")
            if not record.get("reaped") and exited(child):
                if not close(record):
                    raise RuntimeError("unknown child closure")
            for key, _ in selector.select(0.025):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = buffers[key.data]
                cap = 262144 if key.data == "stdout" else 524288
                room = cap - len(target)
                target.extend(chunk[:room])
                if len(chunk) > room:
                    raise RuntimeError(key.data + " output cap exceeded")
        if record["returncode"] != spec["expected_exit"]:
            raise RuntimeError(spec["kind"] + " unexpected exit")
    finally:
        selector.close()
        for stream in [child.stdout, child.stderr]:
            stream.close()
        for key, data in buffers.items():
            name = spec["kind"] + "." + key
            with (OUT / name).open("xb") as handle:
                handle.write(data)
            record[key] = {"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        record["end_seconds"] = time.monotonic() - START
    return buffers

def main():
    assert sys.dont_write_bytecode
    for sig in SIGNALS:
        signal.signal(sig, lambda number, _frame: SEEN.append(number))
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    plan = json.loads((LANE / "host-test-plan.json").read_bytes())
    assert digest(LANE / "host-test-plan.json", 30) == PLAN_SHA
    release = json.loads((ROOT / plan["root_release_required"]["path"]).read_bytes())
    assert release["plan_sha256"] == PLAN_SHA and release["isolated_model_host_lane_released"] is True
    assert release["compiler_invocations"] == release["host_test_invocations"] == 1
    assert release["automatic_retries"] == 0
    assert release["controller_sha256"] == digest(Path(__file__), 30)
    OUT.mkdir(exist_ok=False)
    build = Path(plan["owned_outputs"]["directory"])
    assert not build.exists()
    manifest = json.loads((LANE / "input-manifest.json").read_bytes())
    pins = {str(ROOT / item["path"]): item for item in manifest["inputs"] + plan["source_files"]}
    for key in ["compiler", "linker_driver", "link_editor", "compiler_manifest", "SDK_manifest"]:
        item = plan[key]
        pins[str(ROOT / item["path"])] = item
    toolchain = json.loads((ROOT / plan["compiler_manifest"]["path"]).read_bytes())
    for item in toolchain["members"]:
        pins[str(Path(toolchain["root"]) / item["path"])] = item
    for item in json.loads((ROOT / plan["SDK_manifest"]["path"]).read_bytes())["settings"]:
        pins[item["path"]] = item
    outcome = {"plan_sha256": PLAN_SHA, "model_only": True, "source_files": plan["source_files"],
               "compiler_version": plan["compiler_version_from_prior_receipt"], "pins": len(pins)}
    def verify(offset):
        for name, pin in pins.items():
            path = Path(name)
            assert path.stat().st_size == pin["bytes"] and digest(path, offset) == pin["sha256"], name
    try:
        verify(30)
        build.mkdir()
        Path(plan["owned_outputs"]["temporary_directory"]).mkdir()
        command(plan["commands"][0], plan["environment"], 30)
        binary = Path(plan["owned_outputs"]["binary"])
        outcome["binary_sha256_before"] = digest(binary, 45)
        buffers = command(plan["commands"][1], plan["environment"], 45)
        outcome["binary_sha256_after"] = digest(binary, 45)
        assert outcome["binary_sha256_before"] == outcome["binary_sha256_after"]
        expected = {"tests::" + x["rust_test"] for x in json.loads((LANE / "test-family-map.json").read_bytes())["families"]}
        output = buffers["stdout"].decode("utf-8")
        actual = re.findall(r"^test (\S+) \.\.\. ok$", output, re.M)
        assert len(expected) == len(actual) == 24 and set(actual) == expected
        assert "test result: ok. 24 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;" in output
        outcome["tests_passed"] = 24
    except BaseException as error:
        ERRORS.append(type(error).__name__ + ": " + str(error))
    finally:
        for record in OWNED:
            try:
                if not close(record):
                    ERRORS.append("unknown owned group closure")
            except BaseException as error:
                ERRORS.append("cleanup: " + repr(error))
        closed = all(r.get("reaped") and r.get("group_absent") for r in OWNED)
        try:
            deadline(49)
            generated = []
            if build.exists():
                for path in sorted(build.rglob("*")):
                    deadline(49)
                    assert not path.is_symlink()
                    if path.is_file():
                        generated.append({"path": str(path.relative_to(build)), "bytes": path.stat().st_size,
                                          "sha256": digest(path, 49)})
                        assert len(generated) <= 64 and sum(x["bytes"] for x in generated) <= 33554432
                if closed:
                    shutil.rmtree(build)
            outcome.update(generated=generated, generated_directory_removed=not build.exists())
            verify(53.5)
            outcome["all_pins_rechecked"] = True
        except BaseException as error:
            ERRORS.append("post: " + repr(error))
        outcome.update(commands=[{k: v for k, v in r.items() if k != "child"} for r in OWNED],
                       errors=ERRORS, owned_groups_closed=closed)
        save("observations.json", outcome)
        signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        observed = SEEN + [int(s) for s in signal.sigpending() if s in SIGNALS]
        cutoff = time.monotonic() - START
        for sig in SIGNALS:
            signal.signal(sig, signal.SIG_IGN)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, SIGNALS)
        passed = not ERRORS and not observed and cutoff < 53.5 and outcome.get("tests_passed") == 24
        save("receipt.json", {"status": "passed" if passed else "failed", "plan_sha256": PLAN_SHA,
             "signal_cutoff_seconds": cutoff, "observed_signals": observed, "observations_sha256": digest(OUT / "observations.json", 55),
             "model_only": True, "product_physical_funding_or_GA_acceptance": False})
        print(json.dumps({"status": "passed" if passed else "failed", "tests": outcome.get("tests_passed", 0),
                          "elapsed_seconds": time.monotonic() - START, "receipt": str(OUT / "receipt.json")}))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
