#!/usr/bin/env python3
"""Guarded pure-data archive/profile derivation. No extraction, network or tools."""
from __future__ import annotations

import asyncio
import hashlib
import json
import multiprocessing
import os
from pathlib import Path, PurePosixPath
import resource
import signal
import socket
import subprocess
import sys
import threading
import time

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
ATTEMPTS = []


def install_guards():
    patched = []
    sys.dont_write_bytecode = True
    def deny(name):
        def blocked(*args, **kwargs):
            ATTEMPTS.append(name)
            raise AssertionError("active operation denied: " + name)
        return blocked
    def patch(obj, names, prefix):
        for name in names:
            if hasattr(obj, name):
                setattr(obj, name, deny(prefix + "." + name))
                patched.append(prefix + "." + name)
    patch(subprocess, ["Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"], "subprocess")
    patch(os, ["system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg", "setsid", "setpgid", "getpgid", "getsid", "wait", "waitpid", "waitid", "wait3", "wait4"], "os")
    patch(os, [n for n in dir(os) if n.startswith(("exec", "spawn"))], "os")
    patch(signal, ["alarm", "setitimer", "signal", "pthread_kill", "raise_signal", "sigwait", "sigwaitinfo", "sigtimedwait"], "signal")
    patch(socket, ["socket", "socketpair", "create_connection", "create_server", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"], "socket")
    patch(time, ["sleep"], "time")
    patch(threading.Thread, ["start", "join"], "threading.Thread")
    patch(threading.Timer, ["start", "run", "join"], "threading.Timer")
    patch(multiprocessing.Process, ["start", "join", "terminate", "kill"], "multiprocessing.Process")
    patch(asyncio, ["create_subprocess_exec", "create_subprocess_shell"], "asyncio")
    patch(asyncio.BaseEventLoop, ["call_later", "call_at", "run_forever", "run_until_complete"], "asyncio.BaseEventLoop")
    patch(resource, ["setrlimit"], "resource")
    def audit(event, args):
        if event.startswith(("subprocess.", "socket.")) or event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.wait", "os.waitpid", "os.setsid", "os.setpgid"}:
            ATTEMPTS.append("audit:" + event)
            raise AssertionError("active audit event denied: " + event)
    sys.addaudithook(audit)
    return sorted(patched)


def save(name, value):
    (OWN / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def identity(path):
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            assert size <= 256 * 1024 * 1024, "compressed/input byte cap"
            digest.update(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def main():
    guards = install_guards()
    # Archive/data parsers are loaded only after process/session/group/signal/
    # timer/wait/socket guards. No downloaded code is imported.
    import gzip
    import posixpath
    import struct
    import tarfile

    bounds = {"compressed_bytes": 256 * 1024 * 1024, "uncompressed_bytes": 768 * 1024 * 1024, "member_count": 4096, "single_file_bytes": 256 * 1024 * 1024, "path_bytes": 4096, "read_chunk_bytes": 1024 * 1024}
    metadata = json.loads((OWN / "release-metadata.json").read_text())
    archive_asset = next(a for a in metadata["assets"] if a["name"].endswith(".tar.gz"))
    checksum_asset = next(a for a in metadata["assets"] if a["name"].endswith(".sha256.txt"))
    archive = OWN / "local" / archive_asset["name"]
    assert identity(archive) == {"bytes": archive_asset["size"], "sha256": archive_asset["digest"].removeprefix("sha256:")}
    checksum_path = OWN / "local" / checksum_asset["name"]
    assert identity(checksum_path) == {"bytes": checksum_asset["size"], "sha256": checksum_asset["digest"].removeprefix("sha256:")}
    checksum = checksum_path.read_text().strip().split()
    assert checksum == [archive_asset["digest"].removeprefix("sha256:"), archive_asset["name"]]

    class LimitedReader:
        def __init__(self, stream):
            self.stream, self.total = stream, 0
        def read(self, size=-1):
            assert 0 <= size <= bounds["read_chunk_bytes"], "bounded decompression read"
            result = self.stream.read(size)
            self.total += len(result)
            assert self.total <= bounds["uncompressed_bytes"], "actual decompression cap"
            return result

    root_name = "jdk-17.0.21+9"
    topology = {}
    declared = 0
    with gzip.open(archive, "rb") as gz:
        limited = LimitedReader(gz)
        with tarfile.open(fileobj=limited, mode="r|") as tar:
            for member in tar:
                name = member.name.rstrip("/")
                assert name and len(name.encode()) <= bounds["path_bytes"]
                parts = name.split("/")
                assert not name.startswith("/") and all(p not in ("", ".", "..") for p in parts), "archive path traversal"
                assert parts[0] == root_name and name not in topology, "root/duplicate member"
                assert len(topology) < bounds["member_count"], "archive member count cap"
                assert member.isdir() or member.isfile() or member.issym() or member.islnk(), "nonordinary archive entry"
                assert 0 <= member.size <= bounds["single_file_bytes"]
                declared += member.size
                assert declared <= bounds["uncompressed_bytes"], "declared uncompressed cap"
                row = {"path": name, "type": "directory" if member.isdir() else "file" if member.isfile() else "symlink" if member.issym() else "hardlink", "bytes": member.size, "mode": member.mode}
                if member.issym() or member.islnk():
                    assert member.linkname and len(member.linkname.encode()) <= bounds["path_bytes"] and not member.linkname.startswith("/")
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), member.linkname)) if member.issym() else posixpath.normpath(member.linkname)
                    assert target == root_name or target.startswith(root_name + "/"), "archive link escapes root"
                    row.update(target=member.linkname, normalized_target=target)
                topology[name] = row
        # Account for all decompressed bytes, including ignored tar padding.
        while limited.read(bounds["read_chunk_bytes"]):
            pass
        decompressed_bytes = limited.total
    for name, row in topology.items():
        for parent in PurePosixPath(name).parents:
            if str(parent) == ".":
                break
            assert str(parent) in topology and topology[str(parent)]["type"] == "directory", "missing/nonordinary archive ancestor"
        if row["type"] in ("symlink", "hardlink"):
            target, seen = row["normalized_target"], {name}
            while True:
                assert target not in seen and target in topology, "cycle/dangling archive link"
                seen.add(target)
                target_row = topology[target]
                if target_row["type"] not in ("symlink", "hardlink"):
                    break
                target = target_row["normalized_target"]
            assert target_row["type"] == "file", "non-file archive link target"
            row["resolved_archive_path"] = target

    # Only now, after every topology/cap/link check passes, read member data.
    elf_data = {}
    release_text = None
    with gzip.open(archive, "rb") as gz:
        with tarfile.open(fileobj=LimitedReader(gz), mode="r|") as tar:
            for member in tar:
                name = member.name.rstrip("/")
                row = topology[name]
                if row["type"] != "file":
                    continue
                digest, read = hashlib.sha256(), 0
                data = bytearray() if name.endswith(".so") or name.endswith(("/bin/java", "/bin/javac", "/lib/jexec", "/lib/jspawnhelper", "/release")) else None
                stream = tar.extractfile(member)
                assert stream is not None
                with stream:
                    for chunk in iter(lambda: stream.read(bounds["read_chunk_bytes"]), b""):
                        read += len(chunk)
                        assert read <= member.size
                        digest.update(chunk)
                        if data is not None:
                            data.extend(chunk)
                assert read == member.size
                row["sha256"] = digest.hexdigest()
                if data is not None and data[:4] == b"\x7fELF":
                    elf_data[name[len(root_name) + 1:]] = bytes(data)
                if name.endswith("/release"):
                    release_text = bytes(data).decode("utf-8")
    for row in topology.values():
        if row["type"] in ("symlink", "hardlink"):
            target = topology[row["resolved_archive_path"]]
            row["target_identity"] = {k: target[k] for k in ("bytes", "sha256")}

    all_rows = [dict(row, path=name[len(root_name) + 1:]) for name, row in sorted(topology.items()) if name != root_name]
    runtime, excluded, symlinks = [], [], []
    for row in all_rows:
        path = row["path"]
        if row["type"] == "directory":
            continue
        selected = path in ("bin/java", "bin/javac", "release") or path.startswith(("lib/", "conf/"))
        if path == "lib/src.zip":
            selected = False
        if path == "lib/security/cacerts":
            selected = False
        if selected:
            if row["type"] == "file":
                runtime.append({k: row[k] for k in ("path", "bytes", "sha256")})
            else:
                symlinks.append(row)
        else:
            excluded.append({"path": path, "type": row["type"], "reason": "provider CA trust boundary; not used by offline focused test" if path == "lib/security/cacerts" else "source archive" if path == "lib/src.zip" else "nonselected tool/docs/include/jmods/legal/demo payload"})
    assert not symlinks, "selected archive symlink needs explicit profile treatment"
    by_path = {row["path"]: row for row in runtime}
    for path in ("lib/modules", "lib/ct.sym", "lib/jrt-fs.jar", "lib/jvm.cfg", "lib/server/libjvm.so", "lib/libjli.so", "lib/libjava.so", "lib/libjimage.so", "lib/libzip.so", "lib/libnet.so", "lib/libnio.so", "conf/security/java.security", "conf/security/java.policy"):
        assert path in by_path, "required runtime closure member absent: " + path
    observations = []
    for lane in ("orchestration", "renderer", "environment"):
        receipt_path = ROOT / "verification/android-view-api-boundary-toolchain-observation/local/extracted" / ("android-owner-" + lane) / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        for name in ("java", "javac"):
            launcher = by_path["bin/" + name]
            assert receipt["tools"]["/usr/lib/jvm/temurin-17-jdk-amd64/bin/" + name] == {k: launcher[k] for k in ("bytes", "sha256")}, "official archive launcher differs from hosted observation"
        observations.append({"path": str(receipt_path.relative_to(ROOT)), **identity(receipt_path), "launcher_match": True})

    def elf_dynamic(data):
        assert data[:6] == b"\x7fELF\x02\x01", "only bounded ELF64 little-endian data parser"
        hdr = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
        assert hdr[2] == 62, "x86_64 ELF required"
        phoff, phentsize, phnum = hdr[5], hdr[9], hdr[10]
        assert phentsize == 56 and phnum <= 128 and phoff + phnum * 56 <= len(data)
        loads, dynamic, interpreter = [], None, None
        for index in range(phnum):
            p = struct.unpack_from("<IIQQQQQQ", data, phoff + index * 56)
            assert p[2] + p[5] <= len(data)
            if p[0] == 1:
                loads.append(p)
            elif p[0] == 2:
                dynamic = p
            elif p[0] == 3:
                interpreter = data[p[2]:p[2]+p[5]].rstrip(b"\0").decode("ascii")
        assert dynamic is not None and dynamic[5] <= 65536 and dynamic[5] % 16 == 0
        entries = []
        for offset in range(dynamic[2], dynamic[2] + dynamic[5], 16):
            tag, value = struct.unpack_from("<qQ", data, offset)
            if tag == 0:
                break
            entries.append((tag, value))
        strings = next(value for tag, value in entries if tag == 5)
        string_size = next(value for tag, value in entries if tag == 10)
        load = next(p for p in loads if p[3] <= strings and strings + string_size <= p[3] + p[5])
        start = load[2] + strings - load[3]
        table = data[start:start + string_size]
        def string(index):
            assert 0 <= index < len(table)
            end = table.find(b"\0", index)
            assert end >= 0
            return table[index:end].decode("ascii")
        return {"needed": [string(value) for tag, value in entries if tag == 1], "rpath": [string(value) for tag, value in entries if tag == 15], "runpath": [string(value) for tag, value in entries if tag == 29], "interpreter": interpreter}
    elf_rows = {path: elf_dynamic(data) for path, data in sorted(elf_data.items()) if path in by_path}
    bundled_names = {PurePosixPath(path).name for path in elf_rows}
    external_names = sorted({dep for row in elf_rows.values() for dep in row["needed"] if dep not in bundled_names})
    manifest = {"schema": 1, "archive_root": root_name, "archive": identity(archive), "members": all_rows, "member_count": len(topology), "decompressed_bytes": decompressed_bytes, "declared_file_bytes": declared, "bounds": bounds, "topology_validated_before_member_reads": True}
    save("archive-manifest.json", manifest)
    save("runtime-members.json", runtime)
    save("runtime-exclusions.json", excluded)
    save("elf-dynamic-boundary.json", {"schema": 1, "parser": "bounded pure-data ELF64 little-endian PT_DYNAMIC/PT_INTERP; no ldd or execution", "members": elf_rows, "nonbundled_DT_NEEDED_names": external_names, "limitation": "Names are data evidence, not observed provider resolution. Provider must attest system image/loader/library resolution; optional dlopen providers are not exhaustively proven by DT_NEEDED."})
    packaging = json.loads((OWN / "packaging-sources.json").read_text())
    packaging_identities = []
    for source in packaging["sources"]:
        content = source["content"].encode()
        assert hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() == source["git_blob_sha"], "official packaging blob identity"
        packaging_identities.append({"path": source["path"], "git_blob_sha": source["git_blob_sha"], "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "url": source["api_blob_url"]})
    save("profile-boundary.json", {
        "schema": 1,
        "id": "official-temurin17.0.21+9-linux-x64-runtime-files-v1",
        "status": "expected-file-identities-known-provider-preflight-pending",
        "host_os": "linux", "host_machine": "x86_64", "provider_os": "Ubuntu24.04",
        "jdk_root": "/usr/lib/jvm/temurin-17-jdk-amd64",
        "runtime_manifest": {"path": "runtime-members.json", **identity(OWN / "runtime-members.json")},
        "required_members": len(runtime), "required_bytes": sum(row["bytes"] for row in runtime),
        "membership_scope": ["bin/java", "bin/javac", "release", "conf/**", "lib/**"],
        "excluded_named_paths_in_runtime_scope": ["lib/security/cacerts", "lib/src.zip"],
        "expected_file_policy": "Every expected path and ancestor under canonical JDK root is ordinary; exact content identities and exact scope membership required before/after every child. No automatically learned hashes or symlink targets.",
        "archive_provenance": {"url": archive_asset["browser_download_url"], **identity(archive)},
        "official_packaging_data": packaging_identities,
        "packaging_limit": "Templates name17.0.13+11. They document a tar repack without stripping, provider cacerts link, added source link and alternatives; they do not prove exact17.0.21+9 package or current installed tree.",
        "provider_ca_boundary": {"jdk_path": "lib/security/cacerts", "documented_historical_debian_literal_target": "/etc/ssl/certs/adoptium/cacerts", "hosted_topology_observed": False, "archive_identity": {k: topology[root_name + "/lib/security/cacerts"][k] for k in ("bytes", "sha256")}, "scope": "Provider-owned CA trust outside exact runtime profile; no TLS/network/certificate/signing qualification in offline focused test."},
        "provider_system_boundary": {"loader_from_launcher_PT_INTERP": "/lib64/ld-linux-x86-64.so.2", "nonbundled_DT_NEEDED_names": external_names, "hosted_resolution_observed": False, "exact_system_library_hashes_known": False, "requires_root_acceptance": "Selected Ubuntu provider-image, loader, system libraries and optional dlopen configuration remain ambient provider infrastructure; record that boundary explicitly rather than claim hermetic identity.", "environment": "Allowlisted child environment; omit LD_PRELOAD, LD_LIBRARY_PATH, LD_AUDIT, JAVA_TOOL_OPTIONS, _JAVA_OPTIONS, JDK_JAVA_OPTIONS and CLASSPATH. Use controlled user.home, working directory, tmp and explicit classpaths."},
        "hosted_runtime_files_observed": False, "all_three_hosted_java_javac_match_official_archive": True,
        "hosted_launcher_observations": observations,
        "runtime_dispatch_selected": False, "tool_install_or_execution": False,
    })
    save("derivation-receipt.json", {"schema": 1, "status": "official-archive-profile-derived-data-only", "command": "python3 verification/android-view-api-boundary-linux-tool-profile/analyze_archive.py", "python": sys.version, "source_context_revision": "5b6fc4f5", "source_context_is_parent_supplied_not_live_git": True, "source_analyzer": identity(Path(__file__)), "metadata": identity(OWN / "release-metadata.json"), "published_checksum": {"url": checksum_asset["browser_download_url"], "text": checksum_path.read_text(), **identity(checksum_path)}, "archive": {"url": archive_asset["browser_download_url"], **identity(archive)}, "archive_manifest": identity(OWN / "archive-manifest.json"), "runtime_manifest": identity(OWN / "runtime-members.json"), "runtime_members": len(runtime), "runtime_bytes": sum(row["bytes"] for row in runtime), "archive_symlinks": sum(row["type"] == "symlink" for row in all_rows), "runtime_symlinks": symlinks, "hosted_launcher_observations": observations, "guards": guards, "active_operation_attempts": ATTEMPTS, "release_text": release_text, "provider_runtime_files_observed": False, "remaining_gap": "Official archive runtime identities are known; hosted apt runtime/config/system-library identities beyond matched java/javac remain unobserved and must be checked against the selected manifest before any child."})
    packet_members = []
    for path in sorted(OWN.iterdir()):
        if path.name in {"local", "__pycache__", "seal.json"}:
            continue
        assert path.is_file() and not path.is_symlink(), "ordinary packet file required"
        packet_members.append({"path": path.name, **identity(path)})
    assert len(packet_members) <= 32
    save("seal.json", {"schema": 1, "scope": "Linux JDK expected-file profile, source/data only; not provider/run admission", "members": packet_members, "member_count": len(packet_members), "active_operation_attempts": ATTEMPTS})
    print(json.dumps({"status": "official-archive-profile-derived-data-only", "archive_members": len(topology), "runtime_members": len(runtime), "runtime_bytes": sum(row["bytes"] for row in runtime), "all_three_hosted_java_javac_match": True, "external_needed": external_names, "active_operation_attempts": ATTEMPTS}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
