#!/usr/bin/env python3
"""Bounded C6 selection and data-preflight helpers; no process launch on import."""
import io
import json
import re
import tarfile
from pathlib import Path

from prepare import CHILD, IMAGE, LOCK_SHA, PAYLOAD_SHA, PREFIX, SEAL_SHA, TOOLS, digest, elf, require, sha

MAX_BASE_FILES = 16
MAX_BASE_BYTES = 67108864
MAX_FILE_BYTES = 16777216
MAX_HEADERS = 128
MAX_HEADER_BYTES = 8388608
SELECTED_TOOLS = TOOLS
BOUNDS = {"nativeAttempts": 1, "wallSeconds": 120, "commandSeconds": 30, "compilerCommandSeconds": 20,
          "pids": 128, "memoryBytes": 1073741824, "CPUs": 2, "coreBytes": 0,
          "privateTmpfsBytes": 536870912, "compilerExecutableTmpfsBytes": 268435456,
          "noexecTemporaryTmpfsBytes": 268435456, "ownedStorageBytes": 805306368,
          "ordinaryStdoutBytes": 524288, "ordinaryStderrBytes": 524288,
          "baseELFFiles": MAX_BASE_FILES, "baseELFBytes": MAX_BASE_BYTES,
          "headerFiles": MAX_HEADERS, "headerBytes": MAX_HEADER_BYTES,
          "productCompiles": 4, "resourceRuntimeRows": 0,
          "compiledArtifactBytes": 8388608, "fixedExportAggregateBytes": 83886080}


def one_file_tar(data, basename, maximum=MAX_FILE_BYTES):
    """docker cp -L streams as data; reject links, ambiguity, sparse and tail bytes."""
    require(0 < len(data) <= maximum+1048576, "base export envelope bound")
    files = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r|") as archive:
        for member in archive:
            require(member.isfile() and member.name == basename and not member.pax_headers
                    and not member.sparse and 0 < member.size <= maximum, "base export member")
            require(not files, "duplicate base export member")
            files.append(archive.extractfile(member).read(maximum+1))
            require(len(files[0]) == member.size, "truncated base data")
        while block := archive.fileobj.read(65536):
            require(not any(block), "ambiguous base export tail")
    require(len(files) == 1, "base export file absent")
    return files[0]


def base_path(name):
    require(re.fullmatch(r"[A-Za-z0-9_+.-]{1,128}", name) and name not in (".", ".."), "base library name")
    return "/usr/lib/aarch64-linux-gnu/"+name


def required_base(report, observed):
    """Deterministic bounded worklist; only needed providers plus GCC link input."""
    required = set(report["compilerClosure"]["requiredBaseSonames"]) | {"libgcc_s.so.1"}
    for name, item in observed.items():
        require(name in required, "unsolicited base ELF input")
        require(item["interpreter"] in (None, "/lib/ld-linux-aarch64.so.1")
                and not item["rpath"] and not item["runpath"], "base ELF search/interpreter")
        for dependency in item["needed"]:
            base_path(dependency)
            # Prefer exact C5 providers already in the selected closure.
            supplied = any(node.get("soname") == dependency for node in report["compilerClosure"]["payloadClosure"].values())
            if not supplied:
                required.add(dependency)
    require(len(required) <= MAX_BASE_FILES, "base closure file bound")
    return sorted(required-set(observed))


def verify_complete_base(report, observed):
    require(not required_base(report, observed), "base dependency closure incomplete")
    providers = dict(observed)
    for node in report["compilerClosure"]["payloadClosure"].values():
        if node.get("soname"):
            providers[node["soname"]] = node
    for node in list(report["compilerClosure"]["payloadClosure"].values())+list(observed.values()):
        for name in node["needed"]:
            require(name in providers, "missing transitive provider")
        for name, versions in node["versionNeeds"].items():
            require(name in providers, "missing GNU version provider")
            # Definitions must come from an independent bounded parser/readelf
            # observation before this function can authorize compiler execution.
            require(set(versions) <= set(providers[name].get("versionDefinitions", [])), "unproved GNU symbol versions")
    return True


def validate_selection(selection, proposal, proposal_sha, source_digest):
    require(selection.get("schema") == 1 and selection.get("accountableReviewer") == "/root"
            and selection.get("phase") == "C6" and selection.get("status") == "selected-bounded-private-compiler-qualification", "root selection identity")
    require(selection.get("proposalSHA256") == proposal_sha and selection.get("sourceDigest") == source_digest, "selection source/proposal binding")
    require(selection.get("requiredImage") == IMAGE and selection.get("requiredPlatformChild") == CHILD
            and selection.get("assemblySealSHA256") == SEAL_SHA and selection.get("payloadSHA256") == PAYLOAD_SHA
            and selection.get("packageLockSHA256") == LOCK_SHA, "selection immutable pins")
    require(selection.get("bounds") == BOUNDS and selection.get("compilerPrefix") == PREFIX, "selection bounds/placement")
    require(selection.get("compilerExecutionSelected") is True and selection.get("resourceRuntimeSelected") is False
            and selection.get("helperExecutionSelected") is False and selection.get("NIFLoadSelected") is False
            and selection.get("BEAMExecutionSelected") is False, "selection scope")
    require(proposal.get("bounds") == BOUNDS, "proposal bounds drift")
    return True


def container_argv(name, token, snapshot):
    require(name.startswith("mixer-private-compiler-qualification-") and re.fullmatch("[0-9a-f]{32}", token), "owned identity")
    snapshot = Path(snapshot).resolve()
    return ["docker", "create", "--pull=never", "--platform=linux/arm64", "--name", name,
            "--label", "com.mixer.private-compiler-qualification.owner="+token,
            "--network=none", "--read-only", "--user", "65534:65534", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=128", "--memory=1073741824", "--cpus=2",
            "--ulimit", "core=0:0", "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=268435456,mode=1777",
            "--tmpfs", "/opt/mixer-compiler:rw,exec,nosuid,nodev,size=268435456,mode=1777",
            "--mount", "type=bind,src="+str(snapshot)+",dst=/inputs,readonly",
            "--entrypoint", "/bin/sh", IMAGE, "-c", "exec sleep 120"]


def main():
    # This preparation module deliberately cannot launch native work. The root
    # selection must precede a separately reviewed command-driving adapter.
    print(json.dumps({"status": "source-preparation-only", "nativeExecutionAvailable": False,
                      "bounds": BOUNDS, "requiredImage": IMAGE, "requiredPlatformChild": CHILD}, sort_keys=True))


if __name__ == "__main__":
    main()
