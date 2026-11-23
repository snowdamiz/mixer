#!/usr/bin/env python3
"""Publish the F04 pair and exercise four cold host launches against stock delivery."""
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
PUBLISH = ("prior", "successor", "rollback")


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
            "tokens": [dict(organization="mixer-local", project="fieldlog", actor="f04-host", role="publisher",
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
                verb, target, options = "rollback", artifact, ["--reason", "local F04 restores prior"]
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
            try:
                raw_evidence = record(phase, [args.control, phase, output, str(port)], env)
            except UnknownCustody:
                raise
            except RuntimeError as refusal:
                require(phase == "successor" and "Error raised at top level: Initial guest frame" in str(refusal),
                        "Unexpected host failure")
                recovery = load(output / "recovery/state.json")
                prior = report["phases"]["prior"]
                require(recovery["lastRecovery"] == "ui_protocol_after_effects"
                        and recovery["acceptedSequence"] == 2 and recovery["attempt"] is None
                        and recovery["healthy"]["candidateID"] == prior["candidate"]
                        and digest(output / "workspace/workspace.json") == prior["workspaceSHA256"],
                        "Expected ordinary signed editor refusal with preserved workspace")
                report["refusal"] = {"reason": recovery["lastRecovery"], "sequence": 2,
                    "healthyCandidate": recovery["healthy"]["candidateID"],
                    "workspaceSHA256": prior["workspaceSHA256"]}
                continue
            evidence = json.loads(raw_evidence)
            require(phase != "successor" and evidence["sequence"] == sequence and evidence["artifact"] == artifact,
                    "Launch release identity or editable frame unexpectedly accepted")
            report["phases"][phase] = evidence
        status, raw = get(PROJECT + "/audit", token)
        actions = [entry["action"] for entry in json.loads(raw)["events"]]
        require(status == 200 and actions == expected_audit, "Stock origin publication audit")
        report["audit"] = actions
        close_origin()
        child = None
        phases = report["phases"]
        phases["offline"] = json.loads(record("offline", [args.control, "offline", output, str(port)], env))
        prior, rollback, offline = phases.values()
        require([row["revision"] for row in phases.values()] == [4, 4, 4]
                and len({row["pid"] for row in phases.values()}) == 3
                and len({row["launch"] for row in phases.values()}) == 3
                and prior["artifact"] == rollback["artifact"] == offline["artifact"]
                and rollback["candidate"] == offline["candidate"]
                and len({row["workspaceSHA256"] for row in phases.values()}) == 1,
                "Rollback or cold readback changed committed state")
        report["status"] = "observed_signed_editor_refusal"
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
