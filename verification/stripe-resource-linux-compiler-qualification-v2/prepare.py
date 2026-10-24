#!/usr/bin/env python3
"""Data-only compiler prerequisite audit. Never extracts or loads an executable."""
import argparse
import datetime
import hashlib
import json
import posixpath
from pathlib import Path
import struct
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C5 = "verification/stripe-resource-linux-compiler-assembly"
SEAL_SHA = "3ab8ace95199d687132e0709e033cd219a6f5053780a2b3c4ef16b732f5f0dfd"
PAYLOAD_SHA = "30583d60dc1206350578b75b34aa93af77de321c6efb606fe51c5c5371e1347b"
LOCK = "verification/stripe-resource-linux-compiler-metadata-v3/package-lock.json"
LOCK_SHA = "4db8b41afffdf796acaec18bcc3b5574be593af0c11c4cb860b39da5d64a36b4"
IMAGE = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
CHILD = "sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de"
PREFIX = "/opt/mixer-compiler/toolchain"
MAX_ELF = 33554432
MAX_TAR = 177326080
TOOLS = ["usr/bin/aarch64-linux-gnu-gcc-13", "usr/libexec/gcc/aarch64-linux-gnu/13/cc1",
         "usr/libexec/gcc/aarch64-linux-gnu/13/collect2", "usr/bin/aarch64-linux-gnu-as",
         "usr/bin/aarch64-linux-gnu-ld.bfd", "usr/bin/aarch64-linux-gnu-readelf",
         "usr/libexec/gcc/aarch64-linux-gnu/13/liblto_plugin.so"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def safe_path(name):
    require(isinstance(name, str) and len(name.encode()) <= 4096, "path length/type")
    name = name.removeprefix("./").rstrip("/")
    require(name and not name.startswith("/") and all(x not in ("", ".", "..") for x in name.split("/")), "unsafe path")
    require(not any(ord(x) < 32 or x in "\\\"'" for x in name), "unsafe path character")
    return name


def elf(data):
    """Read only ELF64 little-endian AArch64 load/dynamic/version metadata."""
    require(len(data) <= MAX_ELF and len(data) >= 64, "ELF size")
    require(data[:7] == b"\x7fELF\x02\x01\x01", "unsupported ELF class/endian/version")
    fields = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    kind, machine, version, _, phoff, _, _, ehsize, phsize, phnum, *_ = fields
    require(machine == 183 and version == 1 and ehsize == 64 and kind in (1, 2, 3), "ELF identity")
    require(phnum <= 128 and (not phnum or phsize == 56), "ELF program table")
    require(phoff + phnum * phsize <= len(data), "truncated program table")
    loads, dynamic, interp = [], None, None
    for i in range(phnum):
        typ, flags, off, va, _, size, memsize, align = struct.unpack_from("<IIQQQQQQ", data, phoff+i*56)
        require(off + size <= len(data) and size <= memsize, "program segment bounds")
        if typ == 1:
            loads.append((va, off, size))
        elif typ == 2:
            require(dynamic is None and size % 16 == 0, "ambiguous dynamic segment")
            dynamic = (off, size)
        elif typ == 3:
            require(interp is None and 0 < size <= 4096 and data[off+size-1] == 0, "ELF interpreter")
            interp = data[off:off+size-1].decode("ascii")
    def address(va, amount):
        found = [(off+va-start) for start, off, size in loads if start <= va and va+amount <= start+size]
        require(len(found) == 1, "unmapped/ambiguous dynamic address")
        return found[0]
    result = {"type": kind, "machine": machine, "interpreter": interp, "needed": [], "soname": None,
              "rpath": None, "runpath": None, "versionNeeds": {}, "versionDefinitions": []}
    if dynamic is None:
        return result
    tags, ended = {}, False
    off, size = dynamic
    for at in range(off, off+size, 16):
        tag, value = struct.unpack_from("<qQ", data, at)
        if tag == 0:
            ended = True
            break
        tags.setdefault(tag, []).append(value)
    require(ended, "unterminated dynamic table")
    for tag in (5, 10, 14, 15, 29, 0x6ffffffc, 0x6ffffffd, 0x6ffffffe, 0x6fffffff):
        require(len(tags.get(tag, [])) <= 1, "ambiguous singleton dynamic tag")
    require(5 in tags and 10 in tags, "dynamic string table absent")
    strings_size = tags[10][0]
    require(0 < strings_size <= MAX_ELF, "string table bound")
    strings = address(tags[5][0], strings_size)
    def string(index):
        require(0 <= index < strings_size, "dynamic string index")
        end = data.find(b"\0", strings+index, strings+strings_size)
        require(end >= 0 and end-strings-index <= 4096, "dynamic string termination/bound")
        text = data[strings+index:end].decode("ascii")
        require(all(32 <= ord(c) < 127 for c in text), "dynamic string character")
        return text
    result["needed"] = [string(i) for i in tags.get(1, [])]
    require(len(result["needed"]) <= 64 and len(set(result["needed"])) == len(result["needed"]), "needed count/duplicates")
    for name in result["needed"]:
        require(name and "/" not in name and name not in (".", ".."), "unsupported dynamic dependency name")
    for tag, name in ((14, "soname"), (15, "rpath"), (29, "runpath")):
        if tag in tags:
            result[name] = string(tags[tag][0])
    count = tags.get(0x6fffffff, [0])[0]
    require(count <= 64 and bool(count) == bool(tags.get(0x6ffffffe)), "version need table count")
    current = tags.get(0x6ffffffe, [0])[0]
    seen = set()
    for i in range(count):
        require(current not in seen, "version need cycle")
        seen.add(current)
        at = address(current, 16)
        ver, cnt, file, aux, nxt = struct.unpack_from("<HHIII", data, at)
        require(ver == 1 and 0 < cnt <= 128, "version need header")
        library, requirements = string(file), []
        require(library not in result["versionNeeds"], "duplicate version provider")
        auxiliary, aux_seen = current+aux, set()
        for j in range(cnt):
            require(auxiliary not in aux_seen, "version auxiliary cycle")
            aux_seen.add(auxiliary)
            _, _, _, name, following = struct.unpack_from("<IHHII", data, address(auxiliary, 16))
            requirements.append(string(name))
            require(bool(following) == (j+1 < cnt), "version auxiliary termination")
            auxiliary += following
        result["versionNeeds"][library] = sorted(requirements)
        require(bool(nxt) == (i+1 < count), "version need termination")
        current += nxt
    count = tags.get(0x6ffffffd, [0])[0]
    require(count <= 512 and bool(count) == bool(tags.get(0x6ffffffc)), "version definition table count")
    current, seen = tags.get(0x6ffffffc, [0])[0], set()
    for i in range(count):
        require(current not in seen, "version definition cycle")
        seen.add(current)
        ver, flags, index, cnt, hashed, aux, nxt = struct.unpack_from("<HHHHIII", data, address(current, 20))
        require(ver == 1 and 0 < cnt <= 128, "version definition header")
        auxiliary, aux_seen = current+aux, set()
        for j in range(cnt):
            require(auxiliary not in aux_seen, "version definition auxiliary cycle")
            aux_seen.add(auxiliary)
            name, following = struct.unpack_from("<II", data, address(auxiliary, 8))
            result["versionDefinitions"].append(string(name))
            require(bool(following) == (j+1 < cnt), "version definition auxiliary termination")
            auxiliary += following
        require(bool(nxt) == (i+1 < count), "version definition termination")
        current += nxt
    result["versionDefinitions"] = sorted(set(result["versionDefinitions"]))
    return result


def resolve(path, graph):
    safe_path(path)
    remaining, resolved, seen = path.split("/"), [], set()
    while remaining:
        current = "/".join(resolved+[remaining.pop(0)])
        if current in graph and graph[current]["type"] == "symlink":
            state = (current, tuple(remaining))
            require(state not in seen and len(seen) < 64, "symlink cycle/count")
            seen.add(state)
            target = graph[current]["target"]
            require(not target.startswith("/"), "absolute payload link")
            target = posixpath.normpath(posixpath.join(posixpath.dirname(current), target, *remaining))
            safe_path(target)
            remaining, resolved = target.split("/"), []
        else:
            resolved = current.split("/")
    return "/".join(resolved)


def runtime_closure(metadata, graph):
    """Explicit search path only. Missing image files are requirements, never passes."""
    queue, visited, base = list(TOOLS), {}, set()
    while queue:
        path = resolve(queue.pop(0), graph)
        if path in visited:
            continue
        require(path in metadata, "selected tool/library lacks parsed ELF")
        item = metadata[path]
        require(item["interpreter"] in (None, "/lib/ld-linux-aarch64.so.1"), "unexpected interpreter")
        require(not item["rpath"] and not item["runpath"], "unselected ELF library search path")
        dependencies = {}
        for name in item["needed"]:
            candidate = "usr/lib/aarch64-linux-gnu/"+name
            target = resolve(candidate, graph)
            if target in graph:
                require(graph[target]["type"] == "file" and target in metadata, "non-ELF runtime provider")
                dependencies[name] = {"origin": "payload", "path": target, "sha256": graph[target]["sha256"]}
                queue.append(target)
            else:
                base.add(name)
                dependencies[name] = {"origin": "pinned-base-required-not-yet-inspected", "path": "/usr/lib/aarch64-linux-gnu/"+name}
        visited[path] = {"sha256": graph[path]["sha256"], **item, "providers": dependencies}
    return {"selectedToolRoots": TOOLS, "payloadClosure": visited, "requiredBaseSonames": sorted(base),
            "baseTransitiveClosureComplete": False, "GNUVersionProvidersVerified": False}


def verify_seal(root, relative, expected):
    path = root/relative
    require(sha(path) == expected, "upstream seal pin changed: "+relative)
    seal = json.loads(path.read_text())
    for name, expected_hash in {**seal["files"], **seal.get("localCacheFiles", {})}.items():
        safe_path(name)
        require(sha(root/name) == expected_hash, "upstream sealed file changed: "+name)
    return {"path": relative, "sha256": expected, "filesVerified": len(seal["files"]), "localCacheFilesVerified": len(seal.get("localCacheFiles", {}))}


def audit(root=ROOT):
    started, deadline = time.monotonic(), time.monotonic()+30
    seals = [verify_seal(root, C5+"/seal.json", SEAL_SHA)]
    c5receipt = json.loads((root/C5/"receipt.json").read_text())
    for key in ("inputAcquisitionSeal",):
        record = c5receipt[key]
        seals.append(verify_seal(root, record["path"], record["sha256"]))
    acquisition = json.loads((root/c5receipt["inputAcquisitionSeal"]["path"]).with_name("receipt.json").read_text())
    metadata = acquisition["preservedMetadataSeal"]
    seals.append(verify_seal(root, metadata["path"], metadata["sha256"]))
    require(sha(root/LOCK) == LOCK_SHA, "package lock pin changed")
    lock = json.loads((root/LOCK).read_text())
    require(lock["packageCount"] == len(lock["packages"]) == 36 and lock["prospectivePackageTransferBytes"] == 50997408,
            "exact official package set changed")
    require(not lock["basePackageChanges"] and not lock["baseRuntimeUpgradeDelta"], "base upgrade delta changed")
    require(sha(root/lock["baseStatus"]["path"]) == lock["baseStatus"]["sha256"], "baseline inventory changed")
    graph_list = json.loads((root/C5/"inspection/expected-manifest.json").read_text())["files"]
    graph = {safe_path(x["path"]): x for x in graph_list}
    require(len(graph) == len(graph_list) == 2313 and "usr/bin/cc" not in graph, "payload graph/cc fact changed")
    payload = root/C5/"attempt/exports/compiler-payload.tar"
    require(payload.stat().st_size == MAX_TAR and sha(payload) == PAYLOAD_SHA, "local payload pin changed")
    metadata, scripts, seen, total = {}, {}, set(), 0
    with tarfile.open(payload, mode="r|") as archive:
        for member in archive:
            require(time.monotonic() < deadline, "data inspection wall bound")
            if member.name == ".":
                require(member.isdir(), "invalid root entry")
                continue
            path = safe_path(member.name)
            require(not member.pax_headers and path in graph and path not in seen, "unknown/duplicate/extended tar member")
            seen.add(path)
            entry = graph[path]
            require(member.mode == entry["mode"] and member.uid == member.gid == 0 and member.mtime == 0, "archive metadata mismatch")
            if member.isfile():
                require(entry["type"] == "file" and member.size == entry["bytes"] <= MAX_ELF, "member type/size")
                source = archive.extractfile(member)
                require(source is not None, "regular data missing")
                data = source.read(MAX_ELF+1)
                require(len(data) == member.size and hashlib.sha256(data).hexdigest() == entry["sha256"], "regular bytes mismatch")
                total += len(data)
                require(total <= 175622203, "payload expanded bound")
                if data.startswith(b"\x7fELF"):
                    metadata[path] = elf(data)
                elif path in ("usr/lib/aarch64-linux-gnu/libc.so", "usr/lib/aarch64-linux-gnu/libm.so", "usr/lib/gcc/aarch64-linux-gnu/13/libgcc_s.so"):
                    scripts[path] = {"sha256": entry["sha256"], "text": data.decode("ascii")}
            elif member.isdir():
                require(entry["type"] == "directory", "directory type mismatch")
            elif member.issym():
                require(entry["type"] == "symlink" and member.linkname == entry["target"], "symlink mismatch")
            else:
                raise ValueError("unsupported archive type")
        # Read all remaining record padding; tarfile otherwise accepts hidden tail bytes.
        while block := archive.fileobj.read(65536):
            require(not any(block), "nonzero archive tail")
    require(set(graph) == seen and total == 175622203, "payload graph incomplete")
    missing = []
    for path, item in graph.items():
        if item["type"] == "symlink":
            target = resolve(path, graph)
            if target not in graph:
                missing.append({"path": path, "target": target,
                                "class": "documentation" if path.startswith("usr/share/") else "library-link-target",
                                "requiredBySelectedCompilerClosure": False})
    require(len(missing) == 23 and sum(x["class"] == "documentation" for x in missing) == 14, "full-chain missing dependency partition changed")
    original_missing = json.loads((root/C5/"qualification-boundary.json").read_text())["danglingInsidePrefixLinks"]
    require(len(original_missing) == 23, "original direct dependency receipt changed")
    closure = runtime_closure(metadata, graph)
    for item in missing:
        item["requiredBySelectedCompilerClosure"] = any(dep["path"].lstrip("/") in (item["path"], item["target"])
            for node in closure["payloadClosure"].values() for dep in node["providers"].values())
    image = json.loads((root/C5/"attempt/01-image-inspect.stdout").read_text())[0]
    require(IMAGE in image["RepoDigests"] and image["Id"] == CHILD and image["Descriptor"]["digest"] == CHILD
            and image["Descriptor"]["platform"] == {"architecture": "arm64", "os": "linux"}, "retained base image identity")
    observed_path = "verification/stripe-resource-linux-tool-payload-v3/observed-tools.json"
    observed = json.loads((root/observed_path).read_text())
    require(sha(root/"verification/stripe-resource-linux-tool-payload-v3/attempt-1/06-probe.stdout") == observed["sourceSha256"]
            == "677459e089373f27de4c254a0ae7b1afc27ef799f291482e6a6fead270905b9e", "original runtime/header observation changed")
    headers = {p: h for p, h in observed["linuxFileSha256"].items() if p.startswith("/usr/local/lib/erlang/usr/include/")}
    require(headers == {
        "/usr/local/lib/erlang/usr/include/erl_drv_nif.h": "e9d4280779e8fd4ac463144f310b4da2346dd3a18e73d445bf1f88ae3c1f1312",
        "/usr/local/lib/erlang/usr/include/erl_int_sizes_config.h": "b8aa9cc9cb9f2fd427dd22c4a8354b9e99f28138ff78088cb6286fda6c4e3846",
        "/usr/local/lib/erlang/usr/include/erl_nif.h": "6cb96c37d306a173ef71946e823829fc21e47cb4a19288b221129eac2f13b689"
    } and observed["versions"]["erts"] == "17.1" and observed["versions"]["otp"] == "29.1.1", "matching ERTS evidence")
    sources = {
        "verification/stripe-webhook-linux-resource-harness/v5/fault_helper.c": "d0ffe3524d3ae41d95a4cffebb40806bc11f8a3a9361151490832761d64f17c8",
        "verification/stripe-webhook-linux-resource-harness/v5/control_nif.c": "ffbb62dc0d5853a70a56b54565bfbe011b00e193adc2fb995e4d2c1645b212fb",
    }
    for name, expected_hash in sources.items():
        require(sha(root/name) == expected_hash, "reviewed compiler input changed")
    return {"schema": 1, "status": "C6-data-only-source-preparation", "upstreamSeals": seals,
            "payload": {"path": str(payload.relative_to(root)), "sha256": PAYLOAD_SHA, "bytes": MAX_TAR,
                        "paths": len(seen), "regularBytes": total, "ELFObjectsParsed": len(metadata)},
            "packageLock": {"path": LOCK, "sha256": LOCK_SHA, "packages": 36, "basePackages": len(lock["baselinePackages"])},
            "signedMetadataScope": "Exact sealed native signature/index/stanza/lock byte graph preserved; no fresh cryptographic verifier executed.",
            "image": IMAGE, "platformChild": CHILD, "ccPresent": False,
            "missingLinks": missing, "originalDirectMissingLinks": original_missing,
            "linkerScripts": scripts, "compilerClosure": closure,
            "matchingERTSHeaders": headers, "reviewedSources": sources,
            "allPayloadELF": metadata, "baseFileHashesAlreadyObserved": observed["linuxFileSha256"],
            "elapsedSeconds": time.monotonic()-started,
            "compilerExecuted": False, "nativeAttemptExecuted": False, "hostExtractionExecuted": False,
            "toolchainClosureAccepted": False, "resourceRuntimeRowsExecuted": 0,
            "limitations": ["Base package inventory is not a base-file or transitive ELF closure.",
                "C6 prefix invocation does not satisfy the unchanged V5 absolute /usr/bin/cc controller contract.",
                "The 23 sealed missing links remain preserved, including full symlink-ancestor resolution.",
                "Fourteen documentation links and nine unreferenced library links need no repair for selected compiler roots.",
                "Root must separately select the bounded base-byte observation and compiler attempt."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve().parent == HERE, "output outside owned packet")
    require(not args.output.exists(), "immutable output exists")
    report = audit()
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "reportSha256": sha(args.output), "ELFObjectsParsed": report["payload"]["ELFObjectsParsed"],
                      "requiredBaseSonames": report["compilerClosure"]["requiredBaseSonames"], "compilerExecuted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
