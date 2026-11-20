#!/usr/bin/env python3
"""Replay the sealed Android delivery on macOS with the host presentation witness."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import uuid


def read(path):
    return json.loads(path.read_bytes())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("packet", "probe", "work"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    packet, probe, work = args.packet.resolve(), args.probe.resolve(), args.work.resolve()
    work.mkdir()
    recipe = Path(__file__).resolve().parent
    delivery = packet / "delivery-android"
    install = str(uuid.uuid4())
    port = int((delivery / "Installed/port.txt").read_text())
    phase = work / "phase.txt"
    probe_hash = hashlib.sha256(probe.read_bytes()).hexdigest()
    receipt = read(packet / "build-receipt.json")
    seed_hash = receipt["apkMembersSHA256"]["assets/ChecklistRelease/calculation-seed.json"]
    phases = []

    def verify(sequence, mode):
        result = subprocess.run([probe, delivery / "Installed", work, install, str(sequence), mode],
                                capture_output=True, text=True, timeout=32)
        (work / f"{sequence}-{mode}.log").write_text(result.stdout + result.stderr)
        require(result.returncode == 0, f"{mode} {sequence} failed: {result.stdout[-3000:]} {result.stderr[-3000:]}")
        observation = json.loads(result.stdout.splitlines()[-1])
        require(hashlib.sha256(probe.read_bytes()).hexdigest() == probe_hash, "Host probe changed between launches")
        recovery_path = work / "signed-checklist/recovery/state.json"
        state = read(recovery_path)
        candidate = state["candidates"][observation["candidate"]]
        assignment = read(delivery / f"sequence-{sequence}.assignment.json")["assignment"]
        variant = "reviewed" if sequence == 2 else "baseline"
        require(state["fingerprint"] == state["host"]["runtime"] == receipt["androidRuntime"]
                and state["installation"] == install and state["channel"] == "beta"
                and state["acceptedSequence"] == sequence == candidate["sequence"]
                and state["attempt"] is None and state["pending"] is None and state["staged"] is None
                and state["lastRecovery"] == "effects_closed"
                and state["healthy"]["candidateID"] == observation["candidate"]
                and state["healthy"]["launchID"] == observation["launchID"]
                and set(state["healthy"]["completedMilestones"]) == {"feature_started", "first_screen"}
                and candidate["artifactSHA256"] == assignment["artifact_sha256"]
                and candidate["payloadSHA256"] == receipt["guestSHA256"][variant],
                "Durable health, scope or candidate digest differs")
        observation["artifactSHA256"] = candidate["artifactSHA256"]
        observation["payloadSHA256"] = candidate["payloadSHA256"]
        observation["retiredStateSHA256"] = hashlib.sha256(recovery_path.read_bytes()).hexdigest()
        phases.append(observation)

    phase.write_text("1\n")
    with (work / "origin.log").open("w") as origin_log:
        origin = subprocess.Popen([sys.executable, "-B", recipe / "origin.py", delivery, phase, "--port", str(port)],
                                  stdout=subprocess.PIPE, stderr=origin_log, text=True)
        try:
            import select
            ready, _, _ = select.select([origin.stdout], [], [], 5)
            require(ready and origin.stdout.readline().strip() == str(port), "Owned origin did not report readiness")
            for sequence in range(1, 4):
                next_phase = phase.with_suffix(".new")
                next_phase.write_text(f"{sequence}\n")
                next_phase.replace(phase)
                verify(sequence, "online")
        finally:
            if origin.poll() is None:
                origin.terminate()
                try:
                    origin.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    origin.kill()
                    origin.wait(timeout=5)
            origin.stdout.close()

    with socket.socket() as connection:
        connection.settimeout(2)
        try:
            connection.connect(("127.0.0.1", port))
        except ConnectionRefusedError:
            pass
        else:
            raise ValueError("Origin loopback port still accepts connections")
    verify(3, "offline")
    baseline, correction, rollback, offline = phases
    require(len({p["candidate"] for p in phases[:3]}) == 3
            and len({p["launchID"] for p in phases}) == 4
            and correction["previous"] == baseline["candidate"]
            and rollback["previous"] == offline["previous"] == correction["candidate"]
            and rollback["candidate"] == offline["candidate"]
            and baseline["artifactSHA256"] == rollback["artifactSHA256"] == offline["artifactSHA256"]
            and len({p["pid"] for p in phases}) == 4
            and {p["workspaceSHA256"] for p in phases} == {seed_hash},
            "Rollback or cold offline outcome differs")
    result = {"status": "passed", "runtime": receipt["androidRuntime"], "installation": install,
              "hostProbeSHA256": probe_hash, "originExit": origin.returncode, "offlineLoopbackRefused": True,
              "witness": "macOS presentation test witness", "phases": phases}
    with (packet / "host-receipt.json").open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print("Verified baseline, correction, rollback, cold offline reopen and exact workspace readback")


if __name__ == "__main__":
    main()
