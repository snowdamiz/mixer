#!/usr/bin/env python3
"""Replay the installed-recovery halt control with private macOS resources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime, timezone


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
        listener.listen(1)
        return listener.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xctest", type=Path, required=True, help="MixerCapabilityActivationTests.xctest bundle")
    parser.add_argument("--service", type=Path, required=True, help="Freshly built mixer-service executable")
    parser.add_argument("--cli", type=Path, required=True, help="Public mixer executable")
    parser.add_argument("--scratch-parent", type=Path, required=True, help="Owned directory for disposable state")
    parser.add_argument("--output", type=Path, required=True, help="New private JSON receipt")
    parser.add_argument("--legacy-http", action="store_true", help="Exercise the original HTTP mode for comparison")
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output.resolve()
    if output.exists():
        parser.error("--output must name a new file")
    xctest = args.xctest.resolve(strict=True)
    service = args.service.resolve(strict=True)
    cli = args.cli.absolute()
    resolved_cli = cli.resolve(strict=True)
    runner = subprocess.check_output(("/usr/bin/xcrun", "--find", "xctest"), text=True, timeout=10).strip()
    run = Path(tempfile.mkdtemp(prefix="run-", dir=args.scratch_parent.resolve(strict=True)))
    (run / "custody").mkdir()
    (run / "tmp").mkdir()
    (run / "mixer-service").symlink_to(service)
    port = bind(0)
    tests = "MixerCapabilityActivationTests.CapabilityRecoveryTransitionTests"
    command = [runner, "-XCTest", tests, str(xctest)]
    environment = {"PATH": "/usr/bin:/bin", "TMPDIR": str(run / "tmp"),
                   "MIXER_ROTATION_HALT_RUN": str(run), "MIXER_ROTATION_HALT_PORT": str(port)}
    if not args.legacy_http:
        environment["MIXER_ROTATION_HALT_CLI"] = str(cli)
    expected_children = {"service-before-rotation": (0, run / "mixer-service"),
                         "service-after-rotation": (0, run / "mixer-service"),
                         "service-reopened": (0, run / "mixer-service")}
    if not args.legacy_http:
        expected_children.update({"cli-stale": (1, cli), "cli-halt": (0, cli), "cli-retry": (0, cli)})
    receipt = {"status": "FAILED", "command": command, "environment": environment,
               "cliSHA256": sha256(cli), "cliResolvedPath": str(resolved_cli), "serviceSHA256": sha256(service),
               "xctestSHA256": sha256(xctest / "Contents/MacOS/MixerCapabilityActivationTests"),
               "port": port, "scratch": str(run), "scratchRemoved": False}
    try:
        log = run / "xctest.log"
        with log.open("xb") as stream:
            process = subprocess.Popen(command, env=environment, cwd=run, stdin=subprocess.DEVNULL, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            receipt["xctestPID"] = process.pid
            try:
                receipt["exitCode"] = process.wait(timeout=55)
            except subprocess.TimeoutExpired:
                process.kill()
                receipt["exitCode"] = process.wait(timeout=3)
                raise
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            receipt["xctestGroupAbsent"] = True
        else:
            raise RuntimeError("XCTest process group remains present")
        children = {path.stem: json.loads(path.read_text()) for path in (run / "custody").glob("*.json")}
        receipt["children"] = children
        for name, (exit_code, executable) in expected_children.items():
            child = children.get(name, {})
            if not (child.get("state") == "CLOSED" and child.get("directChildReaped") is True
                    and child.get("ownedGroupAbsent") is True and child.get("exitCode") == exit_code
                    and isinstance(child.get("pid"), int) and child["pid"] > 1
                    and child["pid"] == child.get("pgid") and child.get("executable") == str(executable)
                    and child.get("parentPID") == process.pid):
                raise RuntimeError(f"Missing successful closure for {name}")
        if children.keys() != expected_children.keys():
            raise RuntimeError("Unexpected xctest child receipt")
        bind(port)
        receipt["portRebound"] = True
        receipt["xctestLogSHA256"] = sha256(log)
        lines = log.read_text().splitlines()
        receipt["observations"] = [line for line in lines if line.startswith(("ROTATION ", "ROLLOUT "))]
        summary = next((line for line in reversed(lines) if re.search(r"Executed \d+ tests?, with 0 failures", line)), "")
        if receipt["exitCode"] != 0 or not summary or not any(
                line.startswith("ROLLOUT offline ") for line in receipt["observations"]):
            raise RuntimeError("Installed recovery scenario did not pass")
        receipt["xctestSummary"] = summary.strip()
        if not args.legacy_http:
            receipt["cliResults"] = {name: json.loads((run / "custody" / (name + ".log")).read_text())
                                     for name in ("cli-stale", "cli-halt", "cli-retry")}
        shutil.rmtree(run)
        receipt.update(status="PASS", scratchRemoved=True)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        receipt.update(error=str(error), preserved=str(run))
        raise
    finally:
        receipt["observedAtUTC"] = datetime.now(timezone.utc).isoformat()
        with output.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
