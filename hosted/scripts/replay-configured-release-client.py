"""Run the stock macOS CLI through the owned guest fixture's Unix socket."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import select
import shlex
import subprocess
import sys
import tempfile
import time


def read_input(stream):
    deadline = time.monotonic() + 25
    data = bytearray()
    while len(data) <= 131_072:
        ready, _, _ = select.select([stream], [], [], max(0, deadline - time.monotonic()))
        chunk = os.read(stream.fileno(), 8192) if ready else b""
        if not chunk or time.monotonic() >= deadline:
            break
        data.extend(chunk)
        if data.endswith(b"\n") and len(data) <= 131_072:
            return json.loads(data)
    raise RuntimeError("Guest bootstrap was unavailable or exceeded its deadline")


def decoded_receipt(data):
    if len(data) <= 4096:
        try:
            value = json.loads(data)
            if isinstance(value, dict):
                return value
        except ValueError:
            pass
    return {}


ROLLBACK_REASON = "Restore the signed FieldLog calculation baseline"


def mutate_twice(mixer, port, inputs, phase):
    action = "rollback" if phase == 3 else "publish"
    assignment = json.loads(inputs["assignment"])["assignment"]
    scope = assignment["scope"]
    if phase is not None and (
        assignment["sequence"] != phase
        or assignment["channel"] != "beta"
        or scope != {
            "organization": "mixer-local", "project": "fieldlog", "app": "fieldlog",
            "environment": "development", "platform": "android",
        }
    ):
        raise RuntimeError("Guest bootstrap does not identify the requested FieldLog phase")
    rollout, remainder = divmod(assignment["rollout_basis_points"], 100)
    if remainder or not 1 <= rollout <= 100:
        raise RuntimeError("The signed fixture needs a whole-percent rollout")
    expected = {
        "status": "ok",
        "action": action,
        "artifact_sha256": assignment["artifact_sha256"],
        "sequence": assignment["sequence"],
        "rollout_basis_points": assignment["rollout_basis_points"],
        "delivery": "local_only",
    }

    with tempfile.TemporaryDirectory(prefix="mixer-release-client-", dir="/tmp") as scratch:
        directory = Path(scratch)
        signed_assignment = directory / "signed-assignment.json"
        signed_assignment.write_bytes(inputs["assignment"].encode("utf-8"))
        if action == "publish":
            (directory / "signed-manifest.json").write_bytes(inputs["manifest"].encode("utf-8"))
            (directory / "payload.wasm").write_bytes(base64.b64decode(inputs["payload"], validate=True))
            action_args = [scratch, "--rollout", str(rollout)]
        else:
            action_args = [assignment["artifact_sha256"], "--reason", ROLLBACK_REASON]
        command = [
            mixer, "update", action, *action_args, "--channel", assignment["channel"],
            "--organization", scope["organization"], "--project", scope["project"],
            "--assignment", str(signed_assignment),
        ]
        env = {
            "HOME": scratch,
            "TMPDIR": scratch,
            "MIXER_RELEASE_ORIGIN": f"http://127.0.0.1:{port}",
            "MIXER_RELEASE_TOKEN": inputs["token"],
        }
        receipts = {}
        for stage in ("first", "replay"):
            try:
                process = subprocess.run(
                    command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, timeout=95, check=False,
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"Stock CLI {stage} timed out") from None
            receipt = decoded_receipt(process.stdout)
            if process.returncode:
                code = receipt.get("code")
                if isinstance(code, str) and re.fullmatch(
                    r"update\.(upload|validate|publish|rollback)\.(rejected|response|transport)", code
                ):
                    raise RuntimeError(f"Stock CLI {stage} exited {process.returncode} ({code})")
                raise RuntimeError(f"Stock CLI {stage} exited {process.returncode}")
            if receipt != expected:
                raise RuntimeError(f"Stock CLI {stage} returned an unexpected receipt")
            receipts[stage] = expected
        return json.dumps(receipts).encode("utf-8")


def run(args):
    # The guest's parent SSH daemon can reach a filesystem socket across the
    # network namespace. Only the fixture user can traverse its directory.
    directory = args.guest_scratch
    if args.phase is not None:
        directory += f"/phase-{args.phase}"
    remote = shlex.join([
        "sh", "-eu", "-c",
        'umask 077; mkdir "$1/cli-claimed"; cat "$1/cli-input.json";'
        ' head -c 8193 > "$1/cli-result.tmp";'
        ' mv "$1/cli-result.tmp" "$1/cli-result.json"',
        "sh", directory,
    ])
    command = [
        "/usr/bin/ssh", "-F", args.ssh_config, "-T",
        "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no",
        "-o", "ControlPath=none", "-o", "ControlMaster=no", "-o", "ForkAfterAuthentication=no",
        "-o", "ProxyCommand=none", "-o", "ProxyJump=none",
        "-o", "ForwardAgent=no", "-o", "ForwardX11=no",
        "-o", "PermitLocalCommand=no", "-o", "ExitOnForwardFailure=yes",
        "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
        "-L", f"127.0.0.1:{args.port}:{args.guest_scratch}/cli.sock", "--", args.guest, remote,
    ]
    ssh = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    try:
        inputs = read_input(ssh.stdout)
        receipts = mutate_twice(args.mixer, args.port, inputs, args.phase)
        extra, _ = ssh.communicate(receipts, timeout=15)
        if extra or ssh.returncode:
            raise RuntimeError("SSH did not confirm receipt delivery and forwarding closure")
    finally:
        if ssh.poll() is None:
            ssh.kill()
        ssh.wait(timeout=5)
        ssh.stdin.close()
        ssh.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", required=True)
    parser.add_argument("--ssh-config", required=True)
    parser.add_argument("--guest", required=True)
    parser.add_argument("--guest-scratch", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--phase", type=int, choices=(1, 2, 3), help="Run the indicated FieldLog phase")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("Run this client on macOS with the stock macOS mixer executable")
    if not 1024 <= args.port <= 65535:
        parser.error("Choose an unused unprivileged IPv4 loopback port")
    if not re.fullmatch(r"/tmp/mixer-configured-release\.[A-Za-z0-9]{6}", args.guest_scratch):
        parser.error("Use the guest scratch path printed by this fixture run")
    if not os.path.isabs(args.mixer) or not os.access(args.mixer, os.X_OK):
        parser.error("Pass the absolute path of the built mixer executable")
    os.umask(0o077)
    try:
        run(args)
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
        parser.exit(1, "Fixture client failed while reading inputs or closing its subprocesses\n")
    print("Both stock CLI invocations succeeded and the SSH forward closed.")


if __name__ == "__main__":
    main()
