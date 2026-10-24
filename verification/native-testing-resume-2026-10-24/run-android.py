#!/usr/bin/env python3
"""Resume one owned Android appearance run and always retire its emulator."""
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LANE = ROOT / "verification/android-native-appearance-v2"
SDK = Path("/opt/homebrew/share/android-commandlinetools")
SERIAL = "emulator-5586"


def main():
    out = HERE / "android-candidate-16-lifecycle"
    out.mkdir()
    commands = []
    process = None
    status = "failed"
    error = None
    session_path = LANE / "emulator-session.json"
    previous = session_path.read_bytes()
    (out / "previous-session.json").write_bytes(previous)
    previous_session = json.loads(previous)
    argv = previous_session["argv"]
    assert argv == [str(SDK / "emulator/emulator"), "-avd", "megpt-parity-api37",
                    "-port", "5586", "-read-only", "-no-snapshot", "-no-window",
                    "-no-audio", "-no-boot-anim", "-gpu", "swiftshader_indirect"]
    assert not (LANE / "candidate-16").exists()

    def run(name, args, timeout=30):
        result = subprocess.run(list(map(str, args)), cwd=ROOT, capture_output=True,
                                timeout=timeout)
        log = out / (name + ".log")
        log.write_bytes(result.stdout + result.stderr)
        commands.append({"name": name, "argv": list(map(str, args)),
                         "exitCode": result.returncode, "log": log.name,
                         "sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
        return result

    try:
        run("python-version", [sys.executable, "--version"])
        run("emulator-version", [SDK / "emulator/emulator", "-version"])
        run("adb-version", [SDK / "platform-tools/adb", "version"])
        for port in (5586, 5587):
            result = run("port-before-" + str(port),
                         ["lsof", "-nP", "-iTCP:" + str(port), "-sTCP:LISTEN"])
            assert result.returncode == 1 and not result.stdout, "Owned port in use"
        inventory = run("processes-before", ["ps", "-axo", "pid,ppid,command"])
        owned = [line for line in inventory.stdout.decode().splitlines()
                 if "qemu-system" in line and "-port 5586" in line]
        assert not owned, "Existing instance must be retired or reused first"
        for path, digest in previous_session["metadataSHA256"].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
        with (out / "emulator.log").open("wb") as log:
            process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            session = {"serial": SERIAL, "pid": process.pid, "argv": argv,
                       "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       "scope": "One read-only/no-snapshot owned instance reuses the existing AVD; physical phones and other projects untouched.",
                       "metadataSHA256": previous_session["metadataSHA256"]}
            session_path.write_text(json.dumps(session, indent=2) + "\n")
            (out / "session.json").write_bytes(session_path.read_bytes())
            deadline = time.monotonic() + 180
            attempt = 0
            while True:
                assert process.poll() is None, "Emulator exited before boot"
                attempt += 1
                boot = run("boot-" + str(attempt), [SDK / "platform-tools/adb", "-s",
                           SERIAL, "shell", "getprop", "sys.boot_completed"], timeout=10)
                if boot.returncode == 0 and boot.stdout.strip() == b"1":
                    break
                assert time.monotonic() < deadline, "Boot deadline exceeded"
                time.sleep(3)
            print("Owned emulator booted; running candidate-16", flush=True)
            result = run("qualification", [sys.executable, LANE / "qualify.py", "--output",
                         "candidate-16", "--emulator", SERIAL, "--paired-viewport"], timeout=900)
            result.check_returncode()
            status = "qualified"
    except Exception as exc:
        error = repr(exc)
        raise
    finally:
        if process is not None:
            identity = run("owned-process-before-cleanup", ["ps", "-p", str(process.pid),
                           "-o", "pid=,command="])
            if process.poll() is None:
                assert b"-port 5586" in identity.stdout and b"-avd megpt-parity-api37" in identity.stdout
                run("stop-owned-emulator", [SDK / "platform-tools/adb", "-s", SERIAL, "emu", "kill"])
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=20)
            stopped = run("owned-process-after-cleanup", ["ps", "-p", str(process.pid),
                          "-o", "pid=,command="])
            assert stopped.returncode == 1, "Owned process remains active"
        ports = [run("port-after-" + str(port), ["lsof", "-nP", "-iTCP:" + str(port),
                     "-sTCP:LISTEN"]) for port in (5586, 5587)]
        cleanup = all(p.returncode == 1 and not p.stdout for p in ports)
        receipt = {"status": status, "error": error, "cleanup": "stopped" if cleanup else "pending",
                   "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "collectorSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "commands": commands, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "scope": "One API37 emulator development run; no physical phones, other-project process changes, cross-platform parity or GA acceptance."}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        assert cleanup, "Owned ports remain active"
        print(json.dumps({"status": status, "cleanup": receipt["cleanup"], "error": error}), flush=True)


if __name__ == "__main__":
    main()
