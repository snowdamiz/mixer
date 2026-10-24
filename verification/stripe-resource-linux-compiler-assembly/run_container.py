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
SELECTION = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-compiler-assembly-selection.json"
SELECTION_SHA = "448788d165d55f062d56eda8f0c10403b7258127dae0aa9d33fc957341490f4b"
IMAGE = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
CHILD = "sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de"
LABEL = "com.mixer.private-compiler-assembly.owner"
LIMIT = 524288
EXPORTS = {"payload-manifest.json": 16777216, "notice-inventory.json": 8388608,
           "control-inventory.json": 8388608, "compiler-payload.tar": 268435456}
EXPORT_TOTAL = 301989888


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
            and host["Tmpfs"] == {"/tmp": "rw,noexec,nosuid,nodev,size=536870912,mode=1777"}
            and config["Entrypoint"] == ["/bin/sh"]
            and config["Cmd"] == ["-c", "exec sleep 120"]):
        raise ValueError("container isolation policy mismatch")
    mounts = info["Mounts"]
    if not (len(mounts) == 1 and mounts[0]["Type"] == "bind" and mounts[0]["Source"] == str(snapshot)
            and mounts[0]["Destination"] == "/inputs" and mounts[0]["RW"] is False):
        raise ValueError("container mount policy mismatch")


def export_limit(name):
    if name not in EXPORTS or "/" in name or "\\" in name:
        raise ValueError("unselected fixed artifact export")
    return EXPORTS[name]


def output_allowance(artifact, amount, export_total, ordinary, cleanup=False):
    if artifact is not None:
        return max(0, min(export_limit(artifact)-amount, EXPORT_TOTAL-export_total))
    return max(0, (LIMIT if cleanup else LIMIT-65536)-ordinary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"executeRequired": True, "staticAssemblyOnly": True}))
        return
    from inspect_packages import ACQUISITION, ACQUISITION_SHA, LOCK, LOCK_SHA
    if sha(SELECTION) != SELECTION_SHA or sha(ACQUISITION/"seal.json") != ACQUISITION_SHA or sha(LOCK) != LOCK_SHA:
        raise ValueError("selected immutable input changed")
    selection = json.loads(SELECTION.read_text())
    if (selection["fixedExports"] != EXPORTS or selection["selectedBounds"]["nativeAttempts"] != 1
            or selection["selectedBounds"]["fixedExportAggregateBytes"] != EXPORT_TOTAL
            or selection["requiredImage"] != IMAGE or selection["requiredPlatformChild"] != CHILD):
        raise ValueError("selected static assembly contract mismatch")
    inspection = json.loads((HERE/"inspection/receipt.json").read_text())
    if inspection["status"] != "host-data-inspection-completed":
        raise ValueError("host data inspection unsuccessful")
    for name, expected in json.loads((ACQUISITION/"seal.json").read_text())["localCacheFiles"].items():
        if sha(ROOT/name) != expected:
            raise ValueError("locked archive changed")
    attempt = HERE/"attempt"
    attempt.mkdir(mode=0o700, exist_ok=False)
    exports_directory = attempt/"exports"
    exports_directory.mkdir(mode=0o700)
    snapshot = Path(tempfile.mkdtemp(prefix="mixer-private-compiler-assembly-inputs-")).resolve()
    token = uuid.uuid4().hex
    name = "mixer-private-compiler-assembly-"+token[:12]
    identifier = None
    start = time.monotonic()
    deadline, final_deadline = start+105, start+120
    totals = {"stdout": 0, "stderr": 0}
    export_total = 0
    commands, artifacts = [], {}
    result = {"schema": 1, "status": "failed-prerequisite", "scope": "one selected offline static compiler/header assembly",
        "selectionSha256": SELECTION_SHA, "packageLockSha256": LOCK_SHA, "acquisitionSealSha256": ACQUISITION_SHA,
        "containerName": name, "ownerToken": token, "image": IMAGE, "requiredChild": CHILD,
        "commands": commands, "artifacts": artifacts, "cleanup": {}, "compilerExecuted": False,
        "helperExecuted": False, "nifLoaded": False, "BEAMExecuted": False, "packageScriptsExecuted": False,
        "rootfsOrRunnableImageConstructed": False, "resourceRuntimeRowsExecuted": 0,
        "LinuxArtifactAccepted": False, "LinuxResourceRuntimeAccepted": False, "gaAccepted": False,
        "gitOperations": 0, "cwd": str(ROOT)}

    def run(label, argv, cleanup=False, artifact=None):
        nonlocal export_total
        begin = time.monotonic()
        until = min(begin+30, final_deadline if cleanup else deadline)
        if begin >= until:
            raise TimeoutError("selected static attempt deadline")
        if artifact is not None:
            export_limit(artifact)
        paths = {stream: (exports_directory/(artifact+".partial") if stream == "stdout" and artifact else
                           attempt/f"{len(commands):02}-{label}.{stream}") for stream in totals}
        files = {stream: path.open("xb") for stream, path in paths.items()}
        proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        monitor = selectors.DefaultSelector()
        monitor.register(proc.stdout, selectors.EVENT_READ, "stdout")
        monitor.register(proc.stderr, selectors.EVENT_READ, "stderr")
        raw = {stream: bytearray() for stream in totals}
        amount = 0
        refusal = None
        entry = {"label": label, "argv": argv, "cwd": str(ROOT), "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "budget": "fixed-named-artifact" if artifact else "ordinary-cumulative"}
        try:
            while monitor.get_map():
                if time.monotonic() >= until:
                    refusal = "command-wall-limit"
                    break
                for key, _ in monitor.select(.1):
                    block = os.read(key.fd, 65536)
                    if not block:
                        monitor.unregister(key.fileobj)
                        continue
                    stream = key.data
                    if artifact and stream == "stdout":
                        allowed = output_allowance(artifact, amount, export_total, 0)
                    else:
                        allowed = output_allowance(None, 0, 0, totals[stream], cleanup)
                    kept = block[:max(0, allowed)]
                    files[stream].write(kept)
                    if artifact and stream == "stdout":
                        amount += len(kept)
                        export_total += len(kept)
                    else:
                        totals[stream] += len(kept)
                        raw[stream].extend(kept)
                    if len(kept) != len(block):
                        refusal = "stream-or-artifact-limit"
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
            for output in files.values():
                output.close()
            if artifact:
                destination = exports_directory/(artifact if proc.returncode == 0 and refusal is None else artifact+".failed-export")
                paths["stdout"].rename(destination)
                paths["stdout"] = destination
            entry.update({"exitCode": proc.returncode, "refusal": refusal, "elapsedSeconds": time.monotonic()-begin,
                "outputs": {stream: {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)}
                            for stream, path in paths.items()}})
            commands.append(entry)
            save(attempt/"commands.json", commands)
        if refusal:
            raise TimeoutError(refusal)
        return proc.returncode, bytes(raw["stdout"]), bytes(raw["stderr"]), entry["outputs"]["stdout"]

    try:
        for source in sorted((HERE/"inputs").iterdir()):
            if not source.is_file() or source.is_symlink():
                raise ValueError("invalid owned input source")
            shutil.copyfile(source, snapshot/source.name)
        for package in json.loads(LOCK.read_text())["packages"]:
            source = ACQUISITION/"attempt/packages"/Path(package["filename"]).name
            shutil.copyfile(source, snapshot/source.name)
        inputs = {path.name: sha(path) for path in sorted(snapshot.iterdir())}
        result["snapshotFiles"], result["snapshotDigest"] = inputs, digest(inputs)
        for path in snapshot.iterdir():
            path.chmod(0o444)
        snapshot.chmod(0o555)
        run("docker-version", ["docker", "version", "--format", "{{json .}}"])
        code, stdout, _, _ = run("image-inspect", ["docker", "image", "inspect", "--platform", "linux/arm64", IMAGE])
        if code:
            raise ValueError("selected existing image absent")
        checked_image(json.loads(stdout)[0])
        code, _, _, _ = run("name-before", ["docker", "container", "inspect", name])
        if code == 0:
            raise ValueError("owned name already exists")
        code, stdout, _, _ = run("create", ["docker", "create", "--name", name, "--label", LABEL+"="+token,
            "--label", "com.mixer.private-assembly.selection="+SELECTION_SHA,
            "--label", "com.mixer.private-assembly.inputs="+result["snapshotDigest"],
            "--pull=never", "--platform", "linux/arm64", "--network=none", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user=65534:65534",
            "--pids-limit=128", "--memory=1g", "--cpus=2", "--ulimit=core=0:0", "--log-driver=none",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=536870912,mode=1777",
            "--mount", "type=bind,src="+str(snapshot)+",dst=/inputs,readonly",
            "--entrypoint", "/bin/sh", IMAGE, "-c", "exec sleep 120"])
        if code:
            raise ValueError("container creation failed")
        identifier = stdout.decode("ascii").strip()
        if len(identifier) != 64 or any(c not in "0123456789abcdef" for c in identifier):
            raise ValueError("owned container ID unavailable")
        result["containerId"] = identifier
        code, stdout, _, _ = run("policy-before", ["docker", "container", "inspect", identifier])
        if code:
            raise ValueError("container policy unavailable")
        checked_policy(json.loads(stdout)[0], name, token, snapshot, identifier)
        result["policyVerifiedBeforeStart"] = True
        code, _, _, _ = run("start", ["docker", "start", identifier])
        if code:
            raise ValueError("owned container start failed")
        code, stdout, _, _ = run("assemble", ["docker", "exec", identifier, "/bin/sh", "/inputs/assemble.sh"])
        result["assemblyExitCode"] = code
        result["markers"] = [line for line in stdout.decode(errors="replace").splitlines() if line.startswith("MIXER_")]
        result["status"] = "native-static-assembly-completed-host-validation-pending" if code == 0 else "failed-prerequisite"
    except Exception as error:
        result["failure"] = {"type": type(error).__name__, "reason": str(error)}
        result["status"] = "failed-prerequisite"
    finally:
        if identifier:
            for filename in EXPORTS:
                try:
                    code, _, _, output = run("export-"+filename, ["docker", "exec", identifier, "/bin/cat", "/tmp/compiler-payload/"+filename], artifact=filename)
                    artifacts[filename] = {"available": code == 0, **output}
                    if code and result["status"] != "failed-prerequisite":
                        result["status"] = "failed-prerequisite"
                except Exception as error:
                    artifacts[filename] = {"available": False, "error": str(error)}
                    result["status"] = "failed-prerequisite"
        try:
            code, stdout, _, _ = run("cleanup-identity", ["docker", "container", "inspect", identifier or name], cleanup=True)
            if code == 0:
                info = json.loads(stdout)[0]
                if not owned(info, name, token, identifier):
                    raise ValueError("cleanup identity mismatch; no unrelated mutation")
                identifier = info["Id"]
                code, _, _, _ = run("cleanup-remove", ["docker", "rm", "--force", identifier], cleanup=True)
                if code:
                    raise ValueError("owned removal failed")
            code, _, _, _ = run("cleanup-absence", ["docker", "container", "inspect", identifier or name], cleanup=True)
            result["cleanup"]["ownedContainerAbsent"] = code != 0
            if code == 0:
                raise ValueError("owned container remains")
        except Exception as error:
            result["cleanup"]["failure"] = str(error)
            result["status"] = "failed-prerequisite"
        snapshot.chmod(0o700)
        shutil.rmtree(snapshot)
        result["cleanup"]["temporaryInputSnapshotRemoved"] = not snapshot.exists()
        result["ordinaryStreamBytes"] = totals
        result["fixedArtifactExportBytes"] = export_total
        result["elapsedSecondsIncludingCleanup"] = time.monotonic()-start
        result["runnerSha256"] = sha(Path(__file__))
        result["assemblyScriptSha256"] = sha(HERE/"inputs/assemble.sh")
        result["observedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(attempt/"receipt.json", result)
    print(json.dumps({"status": result["status"], "assemblyExitCode": result.get("assemblyExitCode"), "cleanup": result["cleanup"],
                      "artifactBytes": export_total, "resourceRuntimeRowsExecuted": 0}))


if __name__ == "__main__":
    main()


