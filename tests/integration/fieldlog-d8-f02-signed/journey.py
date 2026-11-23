#!/usr/bin/env python3
"""Publish the F02 pair and exercise five cold host launches against stock delivery."""
import argparse
from hashlib import sha256
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fieldlog-entry-sync"))
from resume import require_group_closed, run, UnknownCustody

PROJECT = "/v3/orgs/mixer-local/projects/fieldlog"
PUBLISH = ("prior", "exact", "rollback")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run_journey(args):
    args.output.mkdir(mode=0o700)
    output = args.output.resolve(strict=True)
    tmp = output / "tmp"
    tmp.mkdir()
    env = dict(PATH="/usr/bin:/bin:/usr/sbin:/sbin", HOME=str(output), TMPDIR=str(tmp),
               NO_PROXY="127.0.0.1", PYTHONDONTWRITEBYTECODE="1")
    report = {"status": "failed", "originSHA256": digest(args.origin), "cliSHA256": digest(args.cli),
              "hostSHA256": digest(args.control), "vmSHA256": digest(args.vm),
              "commands": [], "phases": {}, "publications": {}}
    child = None
    hold = False

    def record(name, argv, command_env):
        command = {"name": name, "argv": list(map(str, argv))}
        report["commands"].append(command)
        log = output / (name + ".log")
        try:
            raw = run(*argv, cwd=output, env=command_env, timeout=18)
        except (RuntimeError, subprocess.TimeoutExpired, UnknownCustody) as failure:
            log.write_text(str(failure))
            command["failure"] = str(failure).splitlines()[0]
            raise
        else:
            log.write_bytes(raw)
            command["outputSHA256"] = digest(log)
            return raw

    def get(path, token=None):
        client = HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            client.request("GET", path, headers={"Authorization": "Bearer " + token} if token else {})
            with client.getresponse() as response:
                return response.status, response.read(65_537)
        finally:
            client.close()

    def close_origin():
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
        try:
            status = child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            status = child.wait(timeout=4)
        require_group_closed(child.pid)
        report["originCleanup"] = {"pid": child.pid, "exit": status, "groupAbsent": True}
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                raise RuntimeError("Origin port remained reachable")
        except ConnectionRefusedError:
            report["originCleanup"]["portRefused"] = True

    try:
        record("prepare", [args.control, "prepare", output, args.fixtures, args.guests, args.vm], env)
        host = load(output / "host.json")
        require((host["protocol"], host["guest_abi"], host["ui_schema"]) == (3, 2, 1), "Ordinary host profile")
        report["hostProfile"] = host
        report["packets"] = {
            phase: {name: digest(output / phase / name)
                    for name in ("signed-manifest.json", "payload.wasm", "assignment.json")}
            for phase in PUBLISH
        }
        token = secrets.token_urlsafe(32)
        with socket.socket() as ephemeral:
            ephemeral.bind(("127.0.0.1", 0))
            port = ephemeral.getsockname()[1]
        config = output / "origin.json"
        config.write_text(json.dumps({
            "developer_mode": True, "listen": f"127.0.0.1:{port}",
            "data_directory": str(output / "origin-store"), "hosts": [host], "roots": load(output / "roots.json"),
            "tokens": [dict(organization="mixer-local", project="fieldlog", actor="f02-host", role="publisher",
                            sha256=sha256(token.encode()).hexdigest())],
        }))
        with (output / "origin.log").open("xb") as log:
            try:
                child = subprocess.Popen([args.origin], cwd=output, stdout=log, stderr=subprocess.STDOUT,
                                         env=dict(env, MIXER_SERVICE_CONFIG=str(config)), start_new_session=True)
            except OSError as failure:
                raise UnknownCustody(f"Origin launch did not return an owned process ID: {failure}") from failure
        deadline = time.monotonic() + 4
        while True:
            require(child.poll() is None and time.monotonic() < deadline, "Stock origin readiness")
            try:
                status, raw = get("/healthz")
                require(status == 200 and json.loads(raw)["mode"] == "developer", "Developer health")
                break
            except ConnectionRefusedError:
                time.sleep(0.05)
        publisher_env = dict(env, MIXER_RELEASE_ORIGIN=f"http://127.0.0.1:{port}", MIXER_RELEASE_TOKEN=token)
        expected_audit = []
        for sequence, phase in enumerate(PUBLISH, 1):
            packet = output / phase
            artifact = load(packet / "assignment.json")["assignment"]["artifact_sha256"]
            if phase == "rollback":
                verb, target, options = "rollback", artifact, ["--reason", "local F02 restores prior"]
            else:
                verb, target, options = "publish", packet, ["--rollout", "100"]
                expected_audit.extend([f"PUT {PROJECT}/artifacts/{artifact}", f"POST {PROJECT}/releases/validate"])
            expected_audit.append(f"POST {PROJECT}/channels/beta/{verb}")
            result = json.loads(record(verb + "-" + phase, [
                args.cli, "update", verb, target, "--channel", "beta", *options, "--assignment",
                packet / "assignment.json", "--organization", "mixer-local", "--project", "fieldlog",
            ], publisher_env))
            require(result == dict(status="ok", action=verb, artifact_sha256=artifact, sequence=sequence,
                                   rollout_basis_points=10_000, delivery="local_only"), "Stock CLI receipt")
            report["publications"][phase] = result
            for launch in ["down", "up"] if phase == "exact" else [phase]:
                evidence = json.loads(record(launch, [args.control, launch, output, str(port)], env))
                require(evidence["sequence"] == sequence and evidence["artifact"] == artifact, "Launch release identity")
                report["phases"][launch] = evidence
        status, raw = get(PROJECT + "/audit", token)
        actions = [entry["action"] for entry in json.loads(raw)["events"]]
        require(status == 200 and actions == expected_audit, "Stock origin publication audit")
        report["audit"] = actions
        close_origin()
        child = None
        phases = report["phases"]
        phases["offline"] = json.loads(record("offline", [args.control, "offline", output, str(port)], env))
        prior, down, up, rollback, offline = phases.values()
        require([row["revision"] for row in phases.values()] == [3, 4, 5, 5, 5], "Cold readback revisions")
        require(len({row["pid"] for row in phases.values()}) == 5 and
                len({row["launch"] for row in phases.values()}) == 5, "Distinct cold processes and launches")
        require(prior["artifact"] == rollback["artifact"] == offline["artifact"] != up["artifact"]
                and down["candidate"] == up["candidate"] == rollback["previous"]
                and rollback["candidate"] == offline["candidate"] != prior["candidate"]
                and down["previous"] == prior["candidate"], "Rollback candidate or artifact chain")
        require([event["revision"] for event in offline["outboxMoves"]] == [4, 5]
                and prior["coldOrder"] == up["coldOrder"] == list(reversed(down["coldOrder"]))
                and up["workspaceSHA256"] == rollback["workspaceSHA256"] == offline["workspaceSHA256"],
                "Exact outbox and rollback persistence")
        report["status"] = "passed"
    except (UnknownCustody, subprocess.TimeoutExpired) as failure:
        hold = isinstance(failure, UnknownCustody)
        report["failure"] = str(failure)
        raise
    except (OSError, RuntimeError, ValueError, KeyError) as failure:
        report["failure"] = str(failure)
        raise
    finally:
        try:
            if child is not None and "originCleanup" not in report:
                close_origin()
        except (OSError, subprocess.TimeoutExpired, UnknownCustody) as failure:
            hold = True
            report["originCleanupFailure"] = str(failure)
            raise
        finally:
            report["hold"] = hold
            (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "fixtures", "guests", "vm", "origin", "cli", "output"):
        parser.add_argument(name, type=lambda value: Path(value).resolve())
    run_journey(parser.parse_args())
