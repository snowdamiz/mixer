#!/usr/bin/env python3
"""One root-selected offline metadata attempt. No package or compiler execution."""
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
SELECTION = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-compiler-metadata-v3-selection.json"
SELECTION_SHA = "7babe8a2b2298b9ae0104124cbae46b4426a5733c06d8f642bfd2a538a0fa836"
PREPARATION = ROOT / "verification/stripe-resource-linux-compiler-preparation/seal.json"
PREPARATION_SHA = "408e9c893150e9d92788591bae9d200514773e1ddbd94ed04a8ffc61c0157178"
IMAGE = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
CHILD = "sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de"
PREVIOUS = ROOT / "verification/stripe-resource-linux-tool-payload-v3/seal.json"
PREVIOUS_SHA = "0286c4cf72503a913520b19bdd7f1b877da995d5d95cf62cc85744015603bf87"
ADDRESS_REVIEW = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-image-address-review/receipt.json"
ADDRESS_REVIEW_SHA = "ea450083989d8f0ecc6780fee7e13c56dea73aa9f7a6c4737664903f58752655"
LABEL = "com.mixer.private-compiler-metadata-v3.owner"
LIMIT = 524288
ADDENDUM = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-compiler-metadata-v2-export-addendum.json"
ADDENDUM_SHA = "3a8096882bd2e3ecfa5962b2836648e457567f61ca671ff7b3ca1e894cda9074"
METADATA = ROOT / "verification/stripe-resource-linux-compiler-metadata/seal.json"
METADATA_SHA = "7e3f66f09d7b7515f941dbb2a8f98301b1f7504761b82c1083e64ac535653745"
EXPORT_BASE_SELECTION_SHA = "7606c060ab4685ef37b0480ab421d2da196cd4e4cfe6a47aca7628e17b25ded6"
PRIOR_FAILURE = ROOT / "verification/stripe-resource-linux-compiler-metadata-v2/seal.json"
PRIOR_FAILURE_SHA = "605e64b6841bbbdfaf9ed0072b80c4bf3a49fad531358d1418ee685bdc856809"


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
    descriptor = info.get("ImageManifestDescriptor", {})
    if not (info.get("Image") == IMAGE.split("@")[1] and info.get("Platform") == "linux"
            and descriptor.get("digest") == CHILD
            and descriptor.get("mediaType") == "application/vnd.oci.image.manifest.v1+json"
            and descriptor.get("platform") == {"architecture": "arm64", "os": "linux"}):
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


def checked_export(name, data, allowed):
    if name not in allowed or "/" in name or "\\" in name or name in (".", ".."):
        raise ValueError("unselected export path")
    rule = allowed[name]
    if len(data) > min(LIMIT, rule.get("maximumBytes", rule.get("bytes", 0))):
        raise ValueError("export byte bound exceeded")
    if "bytes" in rule and len(data) != rule["bytes"]:
        raise ValueError("export exact length mismatch")
    if "sha256" in rule and hashlib.sha256(data).hexdigest() != rule["sha256"]:
        raise ValueError("export exact digest mismatch")


def checked_budgets(addendum):
    if not (addendum["selectionSHA256"] == EXPORT_BASE_SELECTION_SHA
            and addendum["ordinaryStdoutBytes"] == LIMIT
            and addendum["ordinaryStderrBytes"] == LIMIT
            and addendum["perExportCommandStdoutBytes"] == LIMIT
            and addendum["fixedArtifactAggregateBytes"] == 2097152):
        raise ValueError("export budget authority mismatch")
    expected = {"base-status", "base-keyring.gpg", "solver.stdout", "solver.stderr",
                "negative-signature.status", "negative-signature.stderr"}
    expected.update(suite + suffix for suite in ("noble", "noble-updates", "noble-security")
                    for suffix in (".Release", ".gpg.status", ".gpg.stderr"))
    allowed = addendum["allowedExports"]
    if set(allowed) != expected:
        raise ValueError("fixed export set changed")
    maximum = sum(rule.get("maximumBytes", rule.get("bytes", 0)) for rule in allowed.values())
    if maximum != 929433 or maximum > addendum["fixedArtifactAggregateBytes"]:
        raise ValueError("finite export maxima changed")
    return allowed


def checked_inputs(directory):
    inherited = ROOT / "verification/stripe-resource-linux-compiler-metadata/inputs-C2"
    names = {suite + suffix for suite in ("noble", "noble-updates", "noble-security")
             for suffix in (".InRelease", ".Packages.xz")}
    names.update(("expected-tools.sha256", "offline.conf"))
    if {path.name for path in directory.iterdir()} != names | {"prepare.sh", "authenticate.sh", "resolve.sh"}:
        raise ValueError("unexpected input source set")
    for name in names:
        if sha(directory/name) != sha(inherited/name):
            raise ValueError("selected offline input bytes changed: "+name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"executeRequired": True, "nativeAttemptsSelected": 1, "networkSelected": False}))
        return
    for path, expected in ((SELECTION, SELECTION_SHA), (ADDENDUM, ADDENDUM_SHA),
                           (METADATA, METADATA_SHA), (PRIOR_FAILURE, PRIOR_FAILURE_SHA), (PREPARATION, PREPARATION_SHA),
                           (PREVIOUS, PREVIOUS_SHA), (ADDRESS_REVIEW, ADDRESS_REVIEW_SHA)):
        if sha(path) != expected:
            raise ValueError("selected authority or preserved seal changed")
    for seal in (METADATA, PRIOR_FAILURE, PREPARATION, PREVIOUS):
        for name, expected in json.loads(seal.read_text())["files"].items():
            if sha(ROOT / name) != expected:
                raise ValueError("preserved file changed: " + name)
    selection = json.loads(SELECTION.read_text())
    if not (selection["containerAttempts"] == 1 and selection["policy"]["image"] == IMAGE
            and selection["policy"]["childDigest"] == CHILD
            and selection["perContainerWallSeconds"] == 120
            and selection["hostHTTPSRequests"] == 0
            and selection["packageTransferSelected"] is False
            and selection["compilerOrHelperOrNifExecutionSelected"] is False
            and selection["resourceRuntimeSelected"] is False
            and selection["previousSelectionSHA256"] == EXPORT_BASE_SELECTION_SHA
            and selection["metadataSealSHA256"] == PRIOR_FAILURE_SHA
            and selection["fixedExportAddendumSHA256"] == ADDENDUM_SHA):
        raise ValueError("selected offline scope mismatch")
    addendum = json.loads(ADDENDUM.read_text())
    allowed = checked_budgets(addendum)
    checked_inputs(HERE/"inputs")
    attempt = HERE / "attempt"
    attempt.mkdir(exist_ok=False)  # A repeated invocation cannot launch again.
    artifacts = attempt / "artifacts"
    artifacts.mkdir()
    token = uuid.uuid4().hex
    name = "mixer-private-compiler-metadata-v3-" + token[:12]
    snapshot = Path(tempfile.mkdtemp(prefix="mixer-private-metadata-v3-inputs-")).resolve()
    begin = time.monotonic()
    deadline = begin + 105  # Reserve final 15 seconds for identity-fenced cleanup.
    final_deadline = begin + 120
    commands, exports = [], {}
    totals = {"stdout": 0, "stderr": 0}
    artifact_total = 0
    identifier = None
    result = {"schema": 1, "scope": "One isolated offline metadata authentication and APT simulation",
              "selectionSha256": SELECTION_SHA, "exportAddendumSha256": ADDENDUM_SHA,
              "preservedMetadataSealSha256": METADATA_SHA, "preservedFailureSealSha256": PRIOR_FAILURE_SHA,
              "image": IMAGE, "requiredPlatformDescriptorDigest": CHILD,
              "containerName": name, "ownershipToken": token, "status": "failed-prerequisite",
              "commands": commands, "metadataArtifacts": exports, "phases": {}, "cleanup": {},
              "hostHTTPSRequests": 0, "packageRequests": 0, "installExecuted": False,
              "compilerExecuted": False, "helperExecuted": False, "nifLoaded": False,
              "rootfsOrReleaseConstructed": False, "resourceRuntimeRowsExecuted": 0,
              "LinuxArtifactAccepted": False, "LinuxResourceRuntimeAccepted": False,
              "gaAccepted": False, "gitOperations": 0,
              "sourceContext": "Exact runner and readonly input hashes; no Git operation"}

    def run(label, argv, cleanup=False, export_name=None):
        nonlocal artifact_total
        now = time.monotonic()
        until = final_deadline if cleanup else deadline
        if now >= until:
            raise TimeoutError("attempt wall limit")
        if export_name is not None and export_name not in allowed:
            raise ValueError("unselected export command")
        entry = {"label": label, "argv": argv, "cwd": str(ROOT),
                 "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "outputBudget": "fixed-metadata-export" if export_name else "ordinary-cumulative"}
        paths = {key: attempt / f"{len(commands):02}-{label}.{key}" for key in totals}
        files = {key: path.open("xb") for key, path in paths.items()}
        raw = {key: bytearray() for key in totals}
        proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        monitor = selectors.DefaultSelector()
        monitor.register(proc.stdout, selectors.EVENT_READ, "stdout")
        monitor.register(proc.stderr, selectors.EVENT_READ, "stderr")
        refusal = None
        try:
            while monitor.get_map():
                if time.monotonic() >= until:
                    refusal = "wall-limit"
                    break
                for key, _ in monitor.select(min(.1, max(0, until-time.monotonic()))):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        monitor.unregister(key.fileobj)
                        continue
                    stream = key.data
                    if export_name is not None and stream == "stdout":
                        rule = allowed[export_name]
                        remaining = min(LIMIT-len(raw[stream]),
                                        rule.get("maximumBytes", rule.get("bytes", 0))-len(raw[stream]),
                                        addendum["fixedArtifactAggregateBytes"]-artifact_total)
                    else:
                        ceiling = LIMIT if cleanup else LIMIT-65536
                        remaining = ceiling-totals[stream]
                    kept = chunk[:max(0, remaining)]
                    raw[stream].extend(kept)
                    files[stream].write(kept)
                    if export_name is not None and stream == "stdout":
                        artifact_total += len(kept)
                    else:
                        totals[stream] += len(kept)
                    if len(kept) != len(chunk):
                        refusal = "output-limit"
                        break
                if refusal:
                    break
            if refusal:
                proc.kill()
            proc.wait(timeout=2)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2)
            monitor.close()
            for pipe in (proc.stdout, proc.stderr):
                pipe.close()
            for stream in files.values():
                stream.close()
            entry.update({"exitCode": proc.returncode, "refusal": refusal,
                          "elapsedSeconds": time.monotonic()-now,
                          "outputs": {key: {"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                                            "bytes": path.stat().st_size} for key, path in paths.items()}})
            commands.append(entry)
            save(attempt / "commands.json", commands)
        if refusal:
            raise TimeoutError(refusal)
        return proc.returncode, bytes(raw["stdout"]), bytes(raw["stderr"])

    def export(filename, required=True):
        code, data, _ = run("export-"+filename,
                            ["docker", "exec", identifier, "/bin/cat", "/tmp/compiler-metadata/"+filename],
                            export_name=filename)
        if code:
            if required:
                raise ValueError("required metadata export missing: "+filename)
            exports[filename] = {"available": False, "exitCode": code}
            return
        checked_export(filename, data, allowed)
        destination = artifacts / filename
        destination.write_bytes(data)
        exports[filename] = {"available": True, "path": str(destination.relative_to(ROOT)),
                             "bytes": len(data), "sha256": sha(destination)}

    def phase(label, script):
        code, stdout, _ = run(label, ["docker", "exec", identifier, "/bin/sh", "/inputs/"+script])
        result["phases"][label] = {"exitCode": code, "markers": [line for line in
            stdout.decode(errors="replace").splitlines() if line.startswith("MIXER_")]}
        return code

    try:
        for source in sorted((HERE/"inputs").iterdir()):
            if not source.is_file() or source.is_symlink():
                raise ValueError("input must be regular owned file")
            shutil.copyfile(source, snapshot/source.name)
        inputs = {path.name: sha(path) for path in sorted(snapshot.iterdir())}
        result["snapshotFiles"], result["snapshotDigest"] = inputs, digest(inputs)
        for path in snapshot.iterdir():
            path.chmod(0o444)
        snapshot.chmod(0o555)
        run("docker-version", ["docker", "version", "--format", "{{json .}}"])
        code, stdout, _ = run("image-inspect", ["docker", "image", "inspect", "--platform", "linux/arm64", IMAGE])
        if code:
            raise ValueError("selected local image absent")
        checked_image(json.loads(stdout)[0])
        code, _, _ = run("name-before", ["docker", "container", "inspect", name])
        if code == 0:
            raise ValueError("owned name already exists")
        code, stdout, _ = run("create", ["docker", "create", "--name", name,
            "--label", LABEL+"="+token, "--label", "com.mixer.private-metadata-v3.selection="+SELECTION_SHA,
            "--label", "com.mixer.private-metadata-v3.inputs="+result["snapshotDigest"],
            "--pull=never", "--platform", "linux/arm64", "--network=none", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user=65534:65534",
            "--pids-limit=128", "--memory=1g", "--cpus=2", "--ulimit=core=0:0", "--log-driver=none",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=134217728,mode=1777",
            "--mount", "type=bind,src="+str(snapshot)+",dst=/inputs,readonly",
            "--entrypoint", "/bin/sh", IMAGE, "-c", "exec sleep 120"])
        if code:
            raise ValueError("container create failed")
        identifier = stdout.decode("ascii").strip()
        if len(identifier) != 64 or any(c not in "0123456789abcdef" for c in identifier):
            raise ValueError("container ID unavailable")
        result["containerId"] = identifier
        code, stdout, _ = run("policy-before", ["docker", "container", "inspect", identifier])
        if code:
            raise ValueError("container policy unavailable")
        checked_policy(json.loads(stdout)[0], name, token, snapshot, identifier)
        result["containerPolicyVerifiedBeforeStart"] = True
        code, _, _ = run("start", ["docker", "start", identifier])
        if code:
            raise ValueError("container start failed")
        if phase("prepare", "prepare.sh"):
            raise ValueError("base tool/status preparation failed")
        export("base-status")
        export("base-keyring.gpg")
        auth_code = phase("authenticate", "authenticate.sh")
        for suite in ("noble", "noble-updates", "noble-security"):
            for suffix in (".gpg.status", ".gpg.stderr", ".Release"):
                export(suite+suffix, required=auth_code == 0)
        if auth_code:
            raise ValueError("offline native authentication failed")
        solver_code = phase("resolve", "resolve.sh")
        result["resolverPhaseExitCode"] = solver_code
        for filename in ("negative-signature.status", "negative-signature.stderr"):
            export(filename, required=solver_code == 0)
        result["status"] = "offline-metadata-resolution-completed" if solver_code == 0 else "failed-prerequisite"
    except Exception as error:
        result["status"] = "failed-prerequisite"
        result["failure"] = {"type": type(error).__name__, "reason": str(error)}
    finally:
        # The files were initialized in prepare, so retain them after every later
        # failure, including a control failure that never started the solver.
        if identifier:
            for filename in ("solver.stdout", "solver.stderr"):
                try:
                    export(filename, required=False)
                except Exception as error:
                    result.setdefault("exportFailures", {})[filename] = str(error)
                    result["status"] = "failed-prerequisite"
        try:
            code, stdout, _ = run("cleanup-identity", ["docker", "container", "inspect", identifier or name], cleanup=True)
            if code == 0:
                info = json.loads(stdout)[0]
                if not owned(info, name, token, identifier):
                    raise ValueError("cleanup identity mismatch; no mutation authorized")
                identifier = info["Id"]
                code, _, _ = run("cleanup-remove", ["docker", "rm", "--force", identifier], cleanup=True)
                if code:
                    raise ValueError("owned container removal failed")
            code, _, _ = run("cleanup-absence", ["docker", "container", "inspect", identifier or name], cleanup=True)
            result["cleanup"]["ownedContainerAbsent"] = code != 0
            if code == 0:
                raise ValueError("owned container remains")
        except Exception as error:
            result["cleanup"]["failure"] = str(error)
            result["status"] = "failed-prerequisite"
        snapshot.chmod(0o700)
        shutil.rmtree(snapshot)
        result["cleanup"]["temporaryInputSnapshotRemoved"] = not snapshot.exists()
        result["ordinaryStreamRetainedBytes"] = totals
        result["fixedExportStreamRetainedBytes"] = artifact_total
        result["runnerSha256"] = sha(Path(__file__))
        result["elapsedSecondsIncludingCleanup"] = time.monotonic()-begin
        result["observedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result["preservedMetadataSealUnchanged"] = sha(METADATA) == METADATA_SHA
        result["preservedFailureSealUnchanged"] = sha(PRIOR_FAILURE) == PRIOR_FAILURE_SHA
        result["hostPython"] = {"version": sys.version, "executable": str(Path(sys.executable).resolve()),
                                "sha256": sha(Path(sys.executable).resolve())}
        save(attempt/"receipt.json", result)
    print(json.dumps({"status": result["status"], "receipt": str((attempt/"receipt.json").relative_to(ROOT)),
                      "cleanup": result["cleanup"], "resourceRuntimeRowsExecuted": 0}))


if __name__ == "__main__":
    main()


