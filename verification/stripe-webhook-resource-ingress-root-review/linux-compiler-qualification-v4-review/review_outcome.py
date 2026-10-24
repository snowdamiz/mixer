#!/usr/bin/env python3
"""Read retained compiler/export evidence without launching any native process."""
import hashlib
import io
import json
import platform
import struct
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "verification/stripe-resource-linux-compiler-qualification-v4"


def check(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main(expected_seal):
    seal_path = PACKET / "execution-seal.json"
    check(sha(seal_path) == expected_seal, "selected execution seal changed")
    seal = read(seal_path)
    for name, expected in seal["files"].items():
        check(sha(ROOT / name) == expected, "sealed binding changed: " + name)
    receipt = read(PACKET / "attempt-1/receipt.json")
    check(receipt["status"] == "C6-private-compiler-qualification-completed-root-review-pending" and "failure" not in receipt, "attempt failed")
    check(receipt["selectionSHA256"] == "dec210062e47258d4e241c5131b3a0972eb7b2728b71138a962b23136f48c359", "different selected attempt")
    commands = {c["label"]: c for c in receipt["commands"]}
    check(len(commands) == len(receipt["commands"]) == 27, "command inventory differs")
    for command in commands.values():
        for output in command["outputs"].values():
            file = ROOT / output["path"]
            check(sha(file) == output["sha256"] and file.stat().st_size == output["bytes"], "output binding changed")

    def text(label, stream="stdout"):
        return (ROOT / commands[label]["outputs"][stream]["path"]).read_text()

    check(commands["qualify"]["exitCode"] == 0 and commands["start"]["exitCode"] == 0, "native compile incomplete")
    native = text("qualify")
    check(native.count("Machine:                           AArch64") == 4, "native ELF observations differ")
    for marker in ("MIXER_C6_COMPILES=4", "MIXER_HELPER_EXECUTED=0", "MIXER_NIF_LOADED=0", "MIXER_BEAM_EXECUTED=0", "MIXER_RESOURCE_ROWS_EXECUTED=0"):
        check(native.splitlines().count(marker) == 1, "native terminal marker missing")
    name = receipt["containerName"]
    products = {}
    for iteration in (1, 2):
        for filename in ("fault_helper", "control_nif.so"):
            command = commands[f"product-{iteration}-{filename}"]
            check(command["exitCode"] == 0 and command["argv"] == ["docker", "exec", name, "/usr/bin/tar", "--create", "--file=-", f"--directory=/tmp/mixer-compiler-qualification/run-{iteration}", filename], "product export differs")
            raw = (ROOT / command["outputs"]["stdout"]["path"]).read_bytes()
            check(0 < len(raw) <= 3 * 1024 * 1024, "product envelope bound")
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
                members = archive.getmembers()
                check(len(members) == 1, "ambiguous export")
                member = members[0]
                check(member.name == filename and member.isfile() and not member.pax_headers and member.sparse is None and 0 < member.size <= 2 * 1024 * 1024, "unsafe export member")
                body = archive.extractfile(member).read()
                tail = member.offset_data + ((member.size + 511) // 512) * 512
                check(not any(raw[tail:]), "nonzero trailing export data")
            check(body[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<HH", body, 16) == (3, 183), "product is not ELF64 little-endian AArch64 DYN")
            digest = hashlib.sha256(body).hexdigest()
            record = receipt["products"][f"{iteration}/{filename}"]
            check(record["sha256"] == digest and record["bytes"] == len(body), "export body differs from receipt")
            check(native.splitlines().count(f"{digest}  /tmp/mixer-compiler-qualification/run-{iteration}/{filename}") == 1, "export differs from native product")
            products[f"{iteration}/{filename}"] = {"sha256": digest, "bytes": len(body)}
    for filename in ("fault_helper", "control_nif.so"):
        check(products[f"1/{filename}"] == products[f"2/{filename}"], "repeat products differ")
    check(sum(p["bytes"] for p in products.values()) == 288864, "product byte count differs")
    check(len(receipt["ERTSHeaders"]) == 10 and len(receipt["baseExportObservations"]) == 7 and len(receipt["inheritedBaseNotices"]) == 5, "preflight inventory differs")
    check(receipt["compilerAndProductELFClosureVerified"] is True and receipt["baseClosure"]["GNUVersionProvidersVerified"] is True, "ELF closure failed")
    providers = read(PACKET / "data-audit-final.json")["compilerClosure"]["payloadClosure"]
    providers = {p["soname"]: p for p in providers.values() if p.get("soname")}
    providers.update(receipt["baseClosure"]["ELF"])
    for record in receipt["products"].values():
        elf = record["ELF"]
        check(not elf["rpath"] and not elf["runpath"], "unexpected product search path")
        check(set(elf["needed"]) <= set(providers), "missing product dependency")
        for dependency, versions in elf["versionNeeds"].items():
            check(set(versions) <= set(providers[dependency]["versionDefinitions"]), "missing product symbol version")

    identity = json.loads(text("cleanup-identity"))[0]
    policy = json.loads(text("policy-before"))[0]
    host = policy["HostConfig"]
    check(policy["Config"]["User"] == "65534:65534" and host["NetworkMode"] == "none" and host["ReadonlyRootfs"] is True and host["Privileged"] is False, "container isolation differs")
    check(host["Memory"] == 1073741824 and host["NanoCpus"] == 2000000000 and host["PidsLimit"] == 128, "container resource limits differ")
    check(host["CapDrop"] == ["ALL"] and host["SecurityOpt"] == ["no-new-privileges"], "container privileges differ")
    check(host["Tmpfs"] == {"/tmp": "rw,noexec,nosuid,nodev,size=268435456,mode=1777", "/opt/mixer-compiler": "rw,exec,nosuid,nodev,size=268435456,mode=1777"}, "tmpfs placement differs")
    check(identity["Id"] == text("create").strip() and identity["Name"] == "/" + name, "foreign cleanup target")
    check(identity["Config"]["Labels"]["com.mixer.private-compiler-qualification.owner"] == receipt["ownerToken"] and identity["Config"]["Image"] == receipt["requiredImage"], "foreign cleanup owner/image")
    check(commands["cleanup-remove"]["exitCode"] == 0 and commands["cleanup-absence"]["exitCode"] == 1, "cleanup command failed")
    check(json.loads(text("cleanup-absence")) == [] and text("cleanup-absence", "stderr").strip() == "error: no such object: " + name, "absence unproved")
    snapshots = [Path(m["Source"]) for m in identity["Mounts"] if m["Destination"] == "/inputs"]
    check(len(snapshots) == 1 and not snapshots[0].exists(), "input snapshot remains")
    check(receipt["cleanup"] == {"ownedContainerAbsent": True, "temporaryInputSnapshotRemoved": True}, "cleanup receipt differs")
    check(all(receipt[field] is False for field in ("BEAMExecuted", "NIFLoaded", "helperExecuted", "GAaccepted", "V5ControllerAccepted")) and receipt["resourceRuntimeRowsExecuted"] == 0, "unexpected scope claim")
    print(json.dumps({
        "schema": 1, "status": "accepted-private-compiler-and-export-qualification", "accountableReviewer": "/root",
        "observedUTC": datetime.now(timezone.utc).isoformat(), "command": [sys.executable, "-B", str(Path(__file__).resolve()), expected_seal],
        "pythonVersion": platform.python_version(), "reviewerSHA256": sha(Path(__file__)), "executionSealSHA256": expected_seal,
        "verifiedFiles": len(seal["files"]), "sourceDigest": receipt["sourceDigest"], "sourceRevisionContext": "384e22ac22165fa309d8fcb628cc7a1ccb16eb2d",
        "nativeCommandsVerified": 27, "completedCompilationCommands": 4, "nativeRepeatComparisonsPassed": 2,
        "products": products, "exportedProductBytes": 288864, "compilerQualificationAccepted": True,
        "ownedContainerAbsent": True, "snapshotRemoved": True, "nativeRerunPerformed": False,
        "controllerIntegrationAccepted": False, "resourceRuntimeRowsExecuted": 0, "GAaccepted": False,
        "limitations": ["Compiler invocation is under the reviewed /opt prefix; the V5 /usr/bin/cc controller remains unqualified.", "No helper execution, NIF loading, BEAM execution or resource runtime row."],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    check(len(sys.argv) == 2, "expected execution seal SHA256 argument required")
    main(sys.argv[1])
