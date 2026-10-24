#!/usr/bin/env python3
"""One root-selected, isolated tool/compile attempt. No resource-role execution."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-tool-payload-v2-selection.json"
SELECTION_SHA = "ac0d22b65171950bb448ae2b777243c1c2908165b654aa8a4a4d390d1bac9caf"
PREPARATION = ROOT / "verification/stripe-resource-linux-artifact-preparation/seal.json"
PREPARATION_SHA = "e72d9e750aceba69d22ec01d2e41d64897db60de37e48482aae944030fe53f9b"
IMAGE = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
CHILD = "sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de"
PREVIOUS = ROOT / "verification/stripe-resource-linux-tool-payload/seal.json"
PREVIOUS_SHA = "b63ac384fcfa6648321c4708d1b560dd2aa7d1001fc4306899a7b39d8289a340"
ADDRESS_REVIEW = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-image-address-review/receipt.json"
ADDRESS_REVIEW_SHA = "ea450083989d8f0ecc6780fee7e13c56dea73aa9f7a6c4737664903f58752655"
LABEL = "com.mixer.private-tool-payload-v2.owner"
LIMIT = 524288


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def checked_image(image):
    descriptor = image.get("Descriptor", {})
    if not (IMAGE in image.get("RepoDigests", []) and image.get("Id") == CHILD
            and descriptor.get("digest") == CHILD
            and descriptor.get("mediaType") == "application/vnd.oci.image.manifest.v1+json"
            and descriptor.get("platform") == {"architecture": "arm64", "os": "linux"}
            and image.get("Os") == "linux" and image.get("Architecture") == "arm64"):
        raise ValueError("selected parent address or platform image mismatch")


def owned(info, name, token, identifier=None):
    return (info.get("Name") == "/" + name and info.get("Config", {}).get("Labels", {}).get(LABEL) == token
            and info.get("Config", {}).get("Image") == IMAGE
            and (identifier is None or info.get("Id") == identifier))


def checked_policy(info, name, token, snapshot, identifier):
    if not owned(info, name, token, identifier):
        raise ValueError("container identity mismatch")
    if info.get("Image") != CHILD:
        raise ValueError("container platform image mismatch")
    host = info["HostConfig"]
    config = info["Config"]
    if not (config["User"] == "65534:65534" and host["NetworkMode"] == "none"
            and host["ReadonlyRootfs"] is True and host["CapDrop"] == ["ALL"]
            and host["SecurityOpt"] == ["no-new-privileges"]
            and host["PidsLimit"] == 128 and host["Memory"] == 1073741824
            and host["NanoCpus"] == 2000000000 and host["Privileged"] is False
            and not host.get("CapAdd") and not host.get("Devices") and not host.get("VolumesFrom")
            and not host.get("Binds") and host.get("PidMode", "") == ""
            and host["Ulimits"] == [{"Name": "core", "Hard": 0, "Soft": 0}]
            and host["Tmpfs"] == {"/tmp": "rw,noexec,nosuid,nodev,size=134217728,mode=1777"}
            and config["Entrypoint"] == ["/bin/sh"]
            and config["Cmd"] == ["-c", "exec sleep 120"]):
        raise ValueError("container isolation policy mismatch")
    mounts = info["Mounts"]
    if not (len(mounts) == 1 and mounts[0]["Type"] == "bind" and mounts[0]["Source"] == str(snapshot)
            and mounts[0]["Destination"] == "/inputs" and mounts[0]["RW"] is False):
        raise ValueError("container mount policy mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"selectedImage": IMAGE, "executeRequired": True, "runtimeResourceAuthorized": False}))
        return
    if (sha(SELECTION) != SELECTION_SHA or sha(PREPARATION) != PREPARATION_SHA
            or sha(PREVIOUS) != PREVIOUS_SHA or sha(ADDRESS_REVIEW) != ADDRESS_REVIEW_SHA):
        raise ValueError("root selection, preparation, previous attempt or address review mismatch")
    selection = json.loads(SELECTION.read_text())
    if not (selection["image"] == IMAGE and selection["requiredPlatformDescriptorDigest"] == CHILD
            and selection["previousAttemptSealSHA256"] == PREVIOUS_SHA
            and selection["runtimeResourceAuthorized"] is False
            and selection["limits"] == {"containerAttempts": 1, "wallSeconds": 120,
                "stdoutBytes": LIMIT, "stderrBytes": LIMIT, "tmpfsBytes": 134217728}):
        raise ValueError("selection policy mismatch")
    for seal in (PREPARATION, PREVIOUS):
        for name, expected in json.loads(seal.read_text())["files"].items():
            if sha(ROOT / name) != expected:
                raise ValueError("preserved packet changed: " + name)
    attempt = HERE / "attempt-1"
    attempt.mkdir(exist_ok=False)
    token = uuid.uuid4().hex
    name = "mixer-private-tool-payload-v2-" + token[:12]
    snapshot = Path(tempfile.mkdtemp(prefix="mixer-private-tool-inputs-")).resolve()
    deadline = time.monotonic() + 120
    commands = []
    totals = {"stdout": 0, "stderr": 0}
    retained_totals = {"stdout": 0, "stderr": 0}
    identifier = None
    result = {"schema": 1, "scope": "Actual isolated Linux tool/version and optional exact-argv compile prerequisite only",
        "selectionPath": str(SELECTION.relative_to(ROOT)), "selectionSha256": SELECTION_SHA,
        "preparationSealSha256": PREPARATION_SHA, "sourceRevisionContext": None,
        "sourceContext": "No Git operation; exact selected source/tool hashes are authoritative",
        "previousAttemptSealSha256": PREVIOUS_SHA, "addressReviewSha256": ADDRESS_REVIEW_SHA,
        "requiredPlatformDescriptorDigest": CHILD,
        "containerName": name, "ownershipToken": token, "image": IMAGE,
        "status": "failed-prerequisite", "runtimeResourceAuthorized": False,
        "LinuxArtifactAccepted": False, "LinuxResourceRuntimeAccepted": False,
        "resourceRuntimeRowsExecuted": 0, "all30RuntimeMatrixRows": "pending", "gaAccepted": False,
        "toolVersionBEAMExecutionSelected": True, "helperExecuted": False, "nifLoaded": False,
        "rootfsOrReleaseConstructed": False, "commands": commands, "cleanup": {}}

    def run(label, argv, timeout=None, cleanup=False):
        now = time.monotonic()
        remaining = 15 if cleanup else deadline - now
        if timeout is not None:
            remaining = min(remaining, timeout)
        if remaining <= 0:
            raise TimeoutError("attempt deadline")
        entry = {"label": label, "argv": argv, "cwd": str(ROOT),
            "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        output = {key: attempt / f"{len(commands):02}-{label}.{key}" for key in totals}
        streams = {key: path.open("xb") for key, path in output.items()}
        raw = {key: bytearray() for key in totals}
        proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        refused = None
        monitor = selectors.DefaultSelector()
        monitor.register(proc.stdout, selectors.EVENT_READ, "stdout")
        monitor.register(proc.stderr, selectors.EVENT_READ, "stderr")
        try:
            until = now + remaining
            while monitor.get_map():
                if time.monotonic() >= until:
                    refused = "wall-limit"
                    break
                for key, _ in monitor.select(min(0.1, max(0, until - time.monotonic()))):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        monitor.unregister(key.fileobj)
                        continue
                    channel = key.data
                    # Reserve bounded output for the identity-fenced cleanup
                    # even after a noisy probe has exhausted its allowance.
                    ceiling = LIMIT if cleanup else LIMIT - 65536
                    allowed = max(0, ceiling - retained_totals[channel])
                    retained = chunk[:allowed]
                    streams[channel].write(retained)
                    raw[channel].extend(retained)
                    retained_totals[channel] += len(retained)
                    totals[channel] += len(chunk)
                    if len(chunk) > allowed:
                        refused = "output-limit"
                        break
                if refused:
                    break
            if refused:
                proc.kill()
            code = proc.wait(timeout=2)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2)
            monitor.close()
            for pipe in (proc.stdout, proc.stderr):
                pipe.close()
            for stream in streams.values():
                stream.close()
            entry.update({"exitCode": proc.returncode, "refusal": refused,
                "elapsedSeconds": time.monotonic() - now,
                "outputs": {key: {"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                    "bytes": path.stat().st_size} for key, path in output.items()}})
            commands.append(entry)
            save(attempt / "commands.json", commands)
        if refused:
            raise TimeoutError(refused)
        return code, bytes(raw["stdout"]), bytes(raw["stderr"])

    try:
        for source, expected in (("fault_helper.c", "d0ffe3524d3ae41d95a4cffebb40806bc11f8a3a9361151490832761d64f17c8"),
                ("control_nif.c", "ffbb62dc0d5853a70a56b54565bfbe011b00e193adc2fb995e4d2c1645b212fb")):
            path = ROOT / "verification/stripe-webhook-linux-resource-harness/v5" / source
            if path.is_symlink() or sha(path) != expected:
                raise ValueError("selected V5 C source mismatch")
            shutil.copyfile(path, snapshot / source)
        shutil.copyfile(HERE / "probe.sh", snapshot / "probe.sh")
        inputs = {p.name: sha(p) for p in sorted(snapshot.iterdir())}
        result["snapshotFiles"] = inputs
        result["snapshotDigest"] = digest(inputs)
        for path in snapshot.iterdir():
            path.chmod(0o444)
        snapshot.chmod(0o555)
        run("docker-version", ["docker", "version", "--format", "{{json .}}"])
        code, stdout, _ = run("image-inspect", ["docker", "image", "inspect", "--platform", "linux/arm64", IMAGE])
        if code:
            raise ValueError("selected image absent locally")
        image = json.loads(stdout)[0]
        checked_image(image)
        result["observedImage"] = image
        code, _, _ = run("name-before", ["docker", "container", "inspect", name])
        if code == 0:
            raise ValueError("owned name already exists")
        argv = ["docker", "create", "--name", name, "--label", LABEL + "=" + token,
            "--label", "com.mixer.private-tool-payload.selection=" + SELECTION_SHA,
            "--label", "com.mixer.private-tool-payload.inputs=" + result["snapshotDigest"],
            "--pull=never", "--platform", "linux/arm64", "--network=none", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user=65534:65534",
            "--pids-limit=128", "--memory=1g", "--cpus=2", "--ulimit=core=0:0", "--log-driver=none",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=134217728,mode=1777",
            "--mount", "type=bind,src=" + str(snapshot) + ",dst=/inputs,readonly",
            "--entrypoint", "/bin/sh", IMAGE, "-c", "exec sleep 120"]
        code, stdout, _ = run("create", argv)
        if code:
            raise ValueError("container creation failed")
        identifier = stdout.decode("ascii").strip()
        if len(identifier) != 64 or any(c not in "0123456789abcdef" for c in identifier):
            raise ValueError("container ID unavailable")
        result["containerId"] = identifier
        code, stdout, _ = run("policy-before", ["docker", "container", "inspect", identifier])
        if code:
            raise ValueError("container identity unavailable")
        checked_policy(json.loads(stdout)[0], name, token, snapshot, identifier)
        result["containerPolicyVerifiedBeforeStart"] = True
        code, _, _ = run("start", ["docker", "start", identifier])
        if code:
            raise ValueError("container start failed")
        code, stdout, stderr = run("probe", ["docker", "exec", identifier, "/bin/sh", "/inputs/probe.sh"])
        result["probeExitCode"] = code
        result["stdoutMarkerLines"] = [line for line in stdout.decode("utf-8", errors="replace").splitlines()
            if line.startswith("MIXER_")]
        result["status"] = "tool-and-compile-prerequisite-completed" if code == 0 else "failed-prerequisite"
        result["compiledArtifacts"] = {}
        for marker, filename in ((b"MIXER_HELPER_COMPILED=1\n", "fault_helper"),
                (b"MIXER_NIF_COMPILED=1\n", "control_nif.so")):
            if marker not in stdout:
                continue
            artifacts = attempt / "artifacts"
            artifacts.mkdir(exist_ok=True)
            destination = artifacts / filename
            copied, _, _ = run("copy-" + filename, ["docker", "cp", identifier + ":/tmp/mixer-tool-payload/" + filename,
                str(destination)])
            if copied or destination.is_symlink() or not destination.is_file():
                raise ValueError("compiled artifact copy unavailable")
            header = destination.read_bytes()[:20]
            if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
                raise ValueError("compiled artifact ABI mismatch")
            result["compiledArtifacts"][filename] = {"path": str(destination.relative_to(ROOT)),
                "sha256": sha(destination), "bytes": destination.stat().st_size,
                "ELF64LittleEndianAarch64": True, "executed": False}
    except Exception as error:
        result["status"] = "failed-prerequisite"
        result["failure"] = {"type": type(error).__name__, "reason": str(error)}
    finally:
        try:
            code, stdout, _ = run("cleanup-identity", ["docker", "container", "inspect", identifier or name], cleanup=True)
            if code == 0:
                info = json.loads(stdout)[0]
                if not owned(info, name, token, identifier):
                    raise ValueError("cleanup identity mismatch; no mutation authorized")
                identifier = info["Id"]
                removed, _, _ = run("cleanup-remove", ["docker", "rm", "--force", identifier], cleanup=True)
                if removed:
                    raise ValueError("owned container removal failed")
            after, _, _ = run("cleanup-absence", ["docker", "container", "inspect", identifier or name], cleanup=True)
            result["cleanup"]["ownedContainerAbsent"] = after != 0
            if after == 0:
                raise ValueError("owned container still present")
        except Exception as error:
            result["cleanup"]["failure"] = {"type": type(error).__name__, "reason": str(error)}
            result["status"] = "failed-prerequisite"
        snapshot.chmod(0o700)
        shutil.rmtree(snapshot)
        result["cleanup"]["temporaryInputSnapshotRemoved"] = not snapshot.exists()
        result["preparationSealUnchanged"] = sha(PREPARATION) == PREPARATION_SHA
        result["previousAttemptSealUnchanged"] = sha(PREVIOUS) == PREVIOUS_SHA
        result["streamObservedBytes"] = totals
        result["streamRetainedBytes"] = retained_totals
        result["observedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result["runnerSha256"] = sha(Path(__file__))
        result["probeSha256"] = sha(HERE / "probe.sh")
        result["hostPython"] = {"version": sys.version, "executable": str(Path(sys.executable).resolve()),
            "executableSha256": sha(Path(sys.executable).resolve())}
        save(attempt / "receipt.json", result)
    print(json.dumps({"status": result["status"], "probeExitCode": result.get("probeExitCode"),
        "receipt": str((attempt / "receipt.json").relative_to(ROOT)), "cleanup": result["cleanup"],
        "resourceRuntimeRowsExecuted": 0}))


if __name__ == "__main__":
    main()
