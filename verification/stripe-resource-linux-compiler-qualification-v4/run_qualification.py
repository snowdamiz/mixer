#!/usr/bin/env python3
"""One root-selected C6 attempt. Default is a data-only refusal to execute."""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

import prepare
import qualification as q

HERE, ROOT = prepare.HERE, prepare.ROOT
SELECTION = ROOT/"verification/stripe-webhook-resource-ingress-root-review/linux-compiler-qualification-v4-selection.json"
LABEL = "com.mixer.private-compiler-qualification.owner"
SOURCES = ["prepare.py", "qualification.py", "run_qualification.py", "native-qualify.sh", "test_preparation.py"]


def source_files():
    return {str((HERE/name).relative_to(ROOT)): prepare.sha(HERE/name) for name in SOURCES}


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def authority(expected_sha):
    prepare.require(len(expected_sha) == 64 and prepare.sha(SELECTION) == expected_sha, "selected C6 authority absent/changed")
    proposal = json.loads((HERE/"proposal.json").read_text())
    selection = json.loads(SELECTION.read_text())
    q.validate_selection(selection, proposal, prepare.sha(HERE/"proposal.json"), prepare.digest(source_files()))
    return selection, proposal


def owned(info, name, token, identifier=None):
    return (info.get("Name") == "/"+name and info.get("Config", {}).get("Labels", {}).get(LABEL) == token
            and info.get("Config", {}).get("Image") == prepare.IMAGE and
            (identifier is None or info.get("Id") == identifier))


def checked_image(image):
    descriptor = image.get("Descriptor", {})
    prepare.require(prepare.IMAGE in image.get("RepoDigests", []) and image.get("Id") == prepare.CHILD
        and descriptor.get("digest") == prepare.CHILD
        and descriptor.get("mediaType") == "application/vnd.oci.image.manifest.v1+json"
        and descriptor.get("platform") == {"architecture": "arm64", "os": "linux"}
        and image.get("Os") == "linux" and image.get("Architecture") == "arm64", "base image identity drift")


def checked_policy(info, name, token, snapshot, identifier):
    prepare.require(owned(info, name, token, identifier), "owned container identity drift")
    descriptor, host, config = info.get("ImageManifestDescriptor", {}), info["HostConfig"], info["Config"]
    prepare.require(info.get("Image") == prepare.IMAGE.split("@")[1] and descriptor.get("digest") == prepare.CHILD
        and descriptor.get("platform") == {"architecture": "arm64", "os": "linux"}, "container image child drift")
    prepare.require(config["User"] == "65534:65534" and host["NetworkMode"] == "none" and host["ReadonlyRootfs"] is True
        and host["CapDrop"] == ["ALL"] and host["SecurityOpt"] == ["no-new-privileges"]
        and host["PidsLimit"] == 128 and host["Memory"] == 1073741824 and host["NanoCpus"] == 2000000000
        and host["Privileged"] is False and not host.get("CapAdd") and not host.get("Devices")
        and not host.get("VolumesFrom") and not host.get("Binds") and host.get("PidMode", "") == ""
        and host["Ulimits"] == [{"Name": "core", "Hard": 0, "Soft": 0}]
        and host["Tmpfs"] == {"/tmp": "rw,noexec,nosuid,nodev,size=268435456,mode=1777",
                               "/opt/mixer-compiler": "rw,exec,nosuid,nodev,size=268435456,mode=1777"}
        and config["Entrypoint"] == ["/bin/sh"] and config["Cmd"] == ["-c", "exec sleep 120"], "container isolation drift")
    mounts = info["Mounts"]
    prepare.require(len(mounts) == 1 and mounts[0]["Type"] == "bind" and mounts[0]["Source"] == str(snapshot)
                    and mounts[0]["Destination"] == "/inputs" and mounts[0]["RW"] is False, "container mounts drift")


def cleanup_resolution(raw, exit_code, stderr, name, token, identifier=None):
    """Recover creation side effects without ever adopting/removing foreign state."""
    if exit_code:
        allowed = {"Error: No such object: "+name, "Error response from daemon: No such container: "+name,
                   "error: no such object: "+name}
        prepare.require(exit_code == 1 and raw.strip() == b"[]" and stderr.decode().strip() in allowed,
                        "cleanup cannot prove absence from failed inspection")
        return None
    values = json.loads(raw)
    prepare.require(isinstance(values, list) and len(values) == 1, "cleanup inspection cardinality")
    info = values[0]
    recovered = info.get("Id", "")
    prepare.require(len(recovered) == 64 and all(c in "0123456789abcdef" for c in recovered)
                    and owned(info, name, token, identifier)
                    and info.get("Image") == prepare.IMAGE.split("@")[1]
                    and info.get("ImageManifestDescriptor", {}).get("digest") == prepare.CHILD,
                    "cleanup identity fence mismatch")
    return recovered


def inspect_headers(data, expected):
    prepare.require(len(data) <= q.MAX_HEADER_BYTES+1048576, "header export envelope")
    files, total = {}, 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r|") as archive:
        for member in archive:
            name = member.name.removeprefix("./").removeprefix("include/")
            if name in ("", ".", "include") and member.isdir():
                continue
            prepare.safe_path(name)
            path = "/usr/local/lib/erlang/usr/include/"+name
            prepare.require(member.isfile() and not member.pax_headers and not member.sparse
                            and path not in files and member.size <= 1048576, "header tar graph/member")
            body = archive.extractfile(member).read(1048577)
            prepare.require(len(body) == member.size, "header truncated")
            total += len(body)
            prepare.require(total <= q.MAX_HEADER_BYTES and len(files) < q.MAX_HEADERS, "header export aggregate")
            files[path] = hashlib.sha256(body).hexdigest()
        while block := archive.fileobj.read(65536):
            prepare.require(not any(block), "header export tail")
    prepare.require(all(files.get(p) == h for p, h in expected.items()), "original ERTS header pin mismatch")
    return files


def product_export_argv(name, iteration, filename):
    """Read one fixed product through pinned tar in the owned mount namespace."""
    prefix = "mixer-private-compiler-qualification-"
    prepare.require(isinstance(name, str) and name.startswith(prefix)
                    and len(name[len(prefix):]) == 12
                    and all(c in "0123456789abcdef" for c in name[len(prefix):]), "product export container name")
    prepare.require(type(iteration) is int and iteration in (1, 2)
                    and filename in ("fault_helper", "control_nif.so"), "unselected product export")
    directories = {1: "/tmp/mixer-compiler-qualification/run-1", 2: "/tmp/mixer-compiler-qualification/run-2"}
    return ["docker", "exec", name, "/usr/bin/tar", "--create", "--file=-",
            "--directory="+directories[iteration], filename]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--selection-sha", default="")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"executeRequired": True, "rootSelectionRequired": str(SELECTION.relative_to(ROOT)), "nativeAttemptExecuted": False}))
        return
    selection, proposal = authority(args.selection_sha)  # Before any native command.
    report = prepare.audit()
    prepare.require(prepare.digest(source_files()) == selection["sourceDigest"], "source changed after authority")
    attempt = HERE/"attempt-1"
    attempt.mkdir(mode=0o700, exist_ok=False)
    exports = attempt/"exports"
    exports.mkdir(mode=0o700)
    snapshot = Path(tempfile.mkdtemp(prefix="mixer-private-compiler-qualification-inputs-")).resolve()
    token = uuid.uuid4().hex
    name, identifier = "mixer-private-compiler-qualification-"+token[:12], None
    create_attempted = False
    start = time.monotonic()
    deadline, final_deadline = start+105, start+120
    ordinary, export_total, commands = {"stdout": 0, "stderr": 0}, 0, []
    receipt = {"schema": 1, "status": "failed-C6-prerequisite", "selectionSHA256": args.selection_sha,
               "sourceFiles": source_files(), "sourceDigest": prepare.digest(source_files()),
               "requiredImage": prepare.IMAGE, "requiredPlatformChild": prepare.CHILD,
               "compilerPayloadSHA256": prepare.PAYLOAD_SHA, "packageLockSHA256": prepare.LOCK_SHA,
               "containerName": name, "ownerToken": token, "commands": commands, "cleanup": {},
               "compilerAttempted": False, "helperExecuted": False, "NIFLoaded": False, "BEAMExecuted": False,
               "resourceRuntimeRowsExecuted": 0, "V5ControllerAccepted": False, "serviceImageCreated": False,
               "GAaccepted": False, "limitations": ["Private compiler prerequisite only; V5 /usr/bin/cc integration pending.",
                   "Base notice availability/redistribution review remains root-owned and pending."]}

    def run(label, command, *, export=None, maximum=0, check=True, cleanup=False):
        nonlocal export_total
        until = min(time.monotonic()+30, final_deadline if cleanup else deadline)
        prepare.require(time.monotonic() < until, "C6 wall deadline exhausted")
        index = len(commands)
        paths = {s: (exports/export if s == "stdout" and export else attempt/f"{index:02}-{label}.{s}") for s in ordinary}
        files = {s: p.open("xb") for s, p in paths.items()}
        proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        monitor = selectors.DefaultSelector()
        monitor.register(proc.stdout, selectors.EVENT_READ, "stdout")
        monitor.register(proc.stderr, selectors.EVENT_READ, "stderr")
        amount, error, begun = 0, None, time.monotonic()
        try:
            while monitor.get_map():
                if time.monotonic() >= until:
                    raise TimeoutError("C6 command deadline")
                for key, _ in monitor.select(.05):
                    block = os.read(key.fd, 65536)
                    if not block:
                        monitor.unregister(key.fileobj)
                        continue
                    stream = key.data
                    if stream == "stdout" and export:
                        allowed = min(maximum-amount, q.BOUNDS["fixedExportAggregateBytes"]-export_total)
                    else:
                        allowed = q.BOUNDS["ordinary"+stream.title()+"Bytes"]-ordinary[stream]-(0 if cleanup else 65536)
                    if len(block) > max(0, allowed):
                        raise ValueError("C6 output bound")
                    files[stream].write(block)
                    if stream == "stdout" and export:
                        amount += len(block)
                        export_total += len(block)
                    else:
                        ordinary[stream] += len(block)
            proc.wait(timeout=max(.01, until-time.monotonic()))
        except Exception as exc:
            error = str(exc)
            proc.kill()
            proc.wait(timeout=2)
        finally:
            monitor.close()
            for f in files.values():
                f.close()
            entry = {"label": label, "argv": command, "cwd": str(ROOT), "exitCode": proc.returncode,
                     "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "elapsedSeconds": time.monotonic()-begun, "error": error,
                     "outputs": {s: {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": prepare.sha(p)} for s, p in paths.items()}}
            commands.append(entry)
            save(attempt/"commands-partial-{:02}.json".format(index), entry)
        if error:
            raise ValueError(error)
        if check:
            prepare.require(proc.returncode == 0, "C6 command failed: "+label)
        return paths["stdout"].read_bytes()

    try:
        # Exact immutable local cache only. No downloader or archive extraction on host.
        shutil.copyfile(ROOT/prepare.C5/"attempt/exports/compiler-payload.tar", snapshot/"compiler-payload.tar")
        shutil.copyfile(HERE/"native-qualify.sh", snapshot/"native-qualify.sh")
        for source in report["reviewedSources"]:
            shutil.copyfile(ROOT/source, snapshot/Path(source).name)
        payload_graph = json.loads((ROOT/prepare.C5/"inspection/expected-manifest.json").read_text())["files"]
        (snapshot/"payload-files.sha256").write_text("".join(x["sha256"]+"  "+prepare.PREFIX+"/"+x["path"]+"\n" for x in payload_graph if x["type"] == "file"))
        storage_ceiling = (sum(p.stat().st_size for p in snapshot.iterdir())+q.BOUNDS["privateTmpfsBytes"]
                           +q.BOUNDS["fixedExportAggregateBytes"]+2*524288+4194304
                           +sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file()))
        prepare.require(storage_ceiling <= q.BOUNDS["ownedStorageBytes"], "C6 conservative owned storage ceiling")
        receipt["conservativeOwnedStorageCeilingBytes"] = storage_ceiling
        run("docker-version", ["docker", "version", "--format", "{{json .}}"])
        image = json.loads(run("image-inspect", ["docker", "image", "inspect", "--platform=linux/arm64", prepare.IMAGE]))[0]
        checked_image(image)
        # Random identity plus explicit observed absence, never adopt an existing name.
        before = run("name-before", ["docker", "inspect", name], check=False)
        prepare.require(commands[-1]["exitCode"] != 0, "owned name already exists")
        create_attempted = True  # A failed CLI observation can still create daemon state.
        created = run("create", q.container_argv(name, token, snapshot)).decode().strip()
        prepare.require(len(created) == 64 and all(c in "0123456789abcdef" for c in created), "container ID")
        identifier = created  # Malformed/truncated observations retain recovery mode.
        info = json.loads(run("policy-before", ["docker", "inspect", name]))[0]
        checked_policy(info, name, token, snapshot, identifier)
        base, base_hashes, base_bytes = {}, {}, 0
        inherited_hashes = dict(report["baseFileHashesAlreadyObserved"])
        inherited_hashes.update(json.loads((ROOT/prepare.C5/"native-tool-observations.json").read_text())["sha256"])
        while pending := q.required_base(report, base):
            for soname in pending:
                source = q.base_path(soname)
                raw = run("base-"+soname, ["docker", "cp", "-L", name+":"+source, "-"],
                          export="base-"+soname+".tar", maximum=q.MAX_FILE_BYTES+1048576)
                observation = {"requestedPath": source, "requestedSONAME": soname,
                               "exportTar": commands[-1]["outputs"]["stdout"], "decoderStatus": "pending"}
                receipt.setdefault("baseExportObservations", []).append(observation)
                try:
                    body, observed_member = q.base_file_tar(raw, soname)
                except Exception as exc:
                    observation.update(decoderStatus="rejected", decoderError=str(exc))
                    raise
                h = hashlib.sha256(body).hexdigest()
                observation.update(decoderStatus="accepted", observedMemberName=observed_member,
                                   bodyBytes=len(body), bodySHA256=h)
                base_bytes += len(body)
                prepare.require(base_bytes <= q.MAX_BASE_BYTES, "base bytes aggregate")
                item = prepare.elf(body)
                prepare.require(item["soname"] == soname, "base SONAME mismatch")
                old = inherited_hashes.get(source) or inherited_hashes.get(source.replace("/usr/lib/", "/lib/", 1))
                prepare.require(old is None or h == old, "retained base runtime byte hash changed")
                base[soname], base_hashes[source] = item, h
        q.verify_complete_base(report, base)
        receipt["baseClosure"] = {"files": base_hashes, "ELF": base, "bytes": base_bytes, "GNUVersionProvidersVerified": True}
        headers_raw = run("erts-headers", ["docker", "cp", "-L", name+":/usr/local/lib/erlang/usr/include/.", "-"],
                          export="erts-headers.tar", maximum=q.MAX_HEADER_BYTES+1048576)
        header_hashes = inspect_headers(headers_raw, report["matchingERTSHeaders"])
        receipt["ERTSHeaders"] = header_hashes
        receipt["inheritedBaseNotices"] = {}
        for package in ("libc6", "libgcc-s1", "libgmp10", "libzstd1", "zlib1g"):
            # Availability is recorded without claiming component-license acceptance.
            raw = run("notice-"+package, ["docker", "cp", "-L", name+":/usr/share/doc/"+package+"/copyright", "-"],
                      export="notice-"+package+".tar", maximum=1048576+1048576, check=False)
            record = {"path": "/usr/share/doc/"+package+"/copyright", "available": commands[-1]["exitCode"] == 0}
            if record["available"]:
                body = q.one_file_tar(raw, "copyright", maximum=1048576)
                record.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
            receipt["inheritedBaseNotices"][package] = record
        (snapshot/"base-libraries.sha256").write_text("".join(h+"  "+p+"\n" for p, h in sorted(base_hashes.items())))
        prelaunch = {"/inputs/"+p.name: prepare.sha(p) for p in snapshot.iterdir()}
        prelaunch.update(base_hashes)
        prelaunch.update(header_hashes)
        # Independently pin the loader alias and native tar/sha/timeout bytes too.
        for p in ("/usr/bin/tar", "/usr/bin/sha256sum", "/usr/bin/timeout"):
            prelaunch[p] = inherited_hashes[p]
        prelaunch["/lib/ld-linux-aarch64.so.1"] = base_hashes[q.base_path("ld-linux-aarch64.so.1")]
        (snapshot/"prelaunch.sha256").write_text("".join(h+"  "+p+"\n" for p, h in sorted(prelaunch.items())))
        save(attempt/"prelaunch-inputs.json", {"snapshotFiles": {p.name: prepare.sha(p) for p in snapshot.iterdir()},
             "baseFiles": base_hashes, "headers": header_hashes, "prefix": prepare.PREFIX})
        for p in snapshot.iterdir():
            p.chmod(0o444)
        snapshot.chmod(0o555)
        run("start", ["docker", "start", name])
        # Only this named script can execute compiler tools, after complete base preflight.
        receipt["compilerAttempted"] = True
        trace = run("qualify", ["docker", "exec", name, "/bin/sh", "/inputs/native-qualify.sh"])
        prepare.require(b"MIXER_C6_COMPILES=4\n" in trace and b"MIXER_RESOURCE_ROWS_EXECUTED=0\n" in trace, "compile completion markers")
        products = {}
        for iteration in (1, 2):
            for filename in ("fault_helper", "control_nif.so"):
                raw = run("product-{}-{}".format(iteration, filename),
                          product_export_argv(name, iteration, filename),
                          export="product-{}-{}.tar".format(iteration, filename), maximum=2097152+1048576)
                body = q.one_file_tar(raw, filename, maximum=2097152)
                products[str(iteration)+"/"+filename] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "ELF": prepare.elf(body)}
        for filename in ("fault_helper", "control_nif.so"):
            prepare.require(products["1/"+filename]["sha256"] == products["2/"+filename]["sha256"], "repeat compile bytes differ")
        prepare.require(products["1/fault_helper"]["ELF"]["interpreter"] == "/lib/ld-linux-aarch64.so.1"
                        and products["1/control_nif.so"]["ELF"]["interpreter"] is None
                        and products["1/control_nif.so"]["ELF"]["type"] == 3, "compiled product ELF contract")
        composed = json.loads(json.dumps(report))
        for filename in ("fault_helper", "control_nif.so"):
            composed["compilerClosure"]["payloadClosure"]["product/"+filename] = products["1/"+filename]["ELF"]
        q.verify_complete_base(composed, base)
        receipt["compilerAndProductELFClosureVerified"] = True
        receipt["products"] = products
        receipt["status"] = "C6-private-compiler-qualification-completed-root-review-pending"
    except Exception as exc:
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            if create_attempted:
                raw = run("cleanup-identity", ["docker", "inspect", name], check=False, cleanup=True)
                last = commands[-1]
                error_bytes = (ROOT/last["outputs"]["stderr"]["path"]).read_bytes()
                recovered = cleanup_resolution(raw, last["exitCode"], error_bytes, name, token, identifier)
                if recovered:
                    receipt["cleanupRecoveredContainerID"] = recovered
                    run("cleanup-remove", ["docker", "rm", "-f", name], cleanup=True)
                    raw = run("cleanup-absence", ["docker", "inspect", name], check=False, cleanup=True)
                    last = commands[-1]
                    error_bytes = (ROOT/last["outputs"]["stderr"]["path"]).read_bytes()
                    prepare.require(cleanup_resolution(raw, last["exitCode"], error_bytes, name, token, recovered) is None,
                                    "owned container still present after removal")
                receipt["cleanup"]["ownedContainerAbsent"] = True
            else:
                receipt["cleanup"]["ownedContainerAbsent"] = True
        except Exception as exc:
            receipt["cleanup"]["error"] = str(exc)
        snapshot.chmod(0o700)
        shutil.rmtree(snapshot)
        receipt["cleanup"]["temporaryInputSnapshotRemoved"] = not snapshot.exists()
        receipt["ordinaryStreamBytes"], receipt["fixedArtifactExportBytes"] = ordinary, export_total
        receipt["createAttempted"] = create_attempted
        receipt["elapsedSecondsIncludingCleanup"] = time.monotonic()-start
        save(attempt/"commands.json", commands)
        save(attempt/"receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "receiptSHA256": prepare.sha(attempt/"receipt.json"), "helperExecuted": False}))
    prepare.require(receipt["status"] == "C6-private-compiler-qualification-completed-root-review-pending"
                    and receipt["cleanup"] == {"ownedContainerAbsent": True, "temporaryInputSnapshotRemoved": True}, "C6 failed or cleanup incomplete")


if __name__ == "__main__":
    main()
