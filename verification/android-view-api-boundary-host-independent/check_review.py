#!/usr/bin/env python3
"""Independent bounded data controls; never run a compiler, child, timer or socket.

All subject modules are imported only after install_guards(). Scratch is unique,
kept beneath ignored local/, and retained for both success and failure.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import resource
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
from types import SimpleNamespace
import zlib

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
CHECKS: list[dict] = []
ATTEMPTS: list[str] = []


def install_guards() -> list[str]:
    """Deny active APIs before subject import, independently of subject mocks."""
    patched: list[str] = []
    sys.dont_write_bytecode = True

    def deny(name):
        def blocked(*args, **kwargs):
            ATTEMPTS.append(name)
            raise AssertionError("active operation denied by independent review: " + name)
        return blocked

    def patch(obj, names, prefix):
        for name in names:
            if hasattr(obj, name):
                setattr(obj, name, deny(prefix + "." + name))
                patched.append(prefix + "." + name)

    patch(subprocess, ["Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"], "subprocess")
    patch(os, ["system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "startfile", "kill", "killpg", "setsid", "setpgid", "getpgid", "getsid", "wait", "waitpid", "waitid", "wait3", "wait4"], "os")
    patch(os, [name for name in dir(os) if name.startswith(("spawn", "exec"))], "os")
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
        if event.startswith(("subprocess.", "socket.")) or event in {
            "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec",
            "os.kill", "os.killpg", "os.wait", "os.waitpid", "os.setsid", "os.setpgid",
        }:
            ATTEMPTS.append("audit:" + event)
            raise AssertionError("active audit event denied: " + event)
    sys.addaudithook(audit)
    return sorted(patched)


def load_subject(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("subject module spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path: Path) -> dict:
    assert path.stat().st_size <= 8 * 1024 * 1024, "independent input identity byte bound"
    data = path.read_bytes()
    name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def check_inspector_seal():
    packet = ROOT / "verification/android-view-api-boundary-bytecode-inspection"
    seal_id = identity(packet / "seal.json")
    assert seal_id["sha256"] == "26b405d4e8a92120283e8e77084bde55beb2b1f37b2297d975f9b353fe472d35"
    seal = json.loads((packet / "seal.json").read_text())
    expected = {row["path"] for row in seal["members"]}
    assert len(expected) == 7 == seal["member_count"]
    observed = set()
    nodes = 1
    for base, dirs, names in os.walk(packet, followlinks=False):
        nodes += len(dirs) + len(names)
        assert nodes <= 256, "independent packet walk node bound"
        for name in list(dirs):
            path = Path(base) / name
            assert not path.is_symlink()
            if name == "local": dirs.remove(name)
        for name in names:
            path = Path(base) / name
            assert path.is_file() and not path.is_symlink()
            rel = path.relative_to(packet).as_posix()
            if rel != "seal.json": observed.add(rel)
    assert observed == expected
    total = 0
    for row in seal["members"]:
        actual = identity(packet / row["path"])
        assert actual["bytes"] == row["bytes"] and actual["sha256"] == row["sha256"]
        total += actual["bytes"]
    assert total == 84495 == seal["member_bytes"]
    assert identity(packet / "inspect_artifacts.py")["sha256"] == "7e15cfa979f19a72443436dc3f64bba2a6b88c2ed652e8956e96dd454380d83b"
    return {"seal": seal_id, "members": 7, "member_bytes": total}


def check_final_admission_seal():
    packet = ROOT / "verification/android-view-api-boundary-host-admission"
    seal_id = identity(packet / "seal.json")
    assert seal_id["sha256"] == "67216246e69f0fed1c3861a9ff6134f944924544f62d8f1e0704edfc90e60445"
    seal = json.loads((packet / "seal.json").read_text())
    expected = {row["path"] for row in seal["members"]}
    assert len(expected) == 17 == seal["member_count"]
    observed = set()
    nodes = 1
    for base, dirs, names in os.walk(packet, followlinks=False):
        nodes += len(dirs) + len(names)
        assert nodes <= 512
        for name in list(dirs):
            path = Path(base) / name
            assert not path.is_symlink()
            if name == "local": dirs.remove(name)
        for name in names:
            path = Path(base) / name
            assert path.is_file() and not path.is_symlink()
            rel = path.relative_to(packet).as_posix()
            if rel != "seal.json": observed.add(rel)
    assert observed == expected
    total = 0
    for row in seal["members"]:
        value = identity(packet / row["path"])
        assert value["bytes"] == row["bytes"] and value["sha256"] == row["sha256"]
        total += value["bytes"]
    assert total == 169455 == seal["member_bytes"]
    assert identity(packet / "collect.py")["sha256"] == "2adba2ad9051d5db3dab3ccf970f2557765f2de5abf6054313c488dd73dd6387"
    assert identity(packet / "custody.py")["sha256"] == "c59b3d398156df26c713f012022fd83134b7dd34dcccc814779272acc36d96bb"
    assert identity(packet / "workflow.DRAFT.yml")["sha256"] == "637d03949cab0e9a4517b1f7b2ece05a809ddd21ce71d32af72b5ad1693c3a96"
    return {"seal": seal_id, "members": len(expected), "member_bytes": total, "source_data_acceptance_only": True}


def check_linux_profile_data():
    """Compare derived data only; never extract or execute a JDK archive."""
    packet = ROOT / "verification/android-view-api-boundary-linux-tool-profile"
    runtime = json.loads((packet / "runtime-members.json").read_text())
    archive = json.loads((packet / "archive-manifest.json").read_text())
    receipt = json.loads((packet / "derivation-receipt.json").read_text())
    elf = json.loads((packet / "elf-dynamic-boundary.json").read_text())
    assert len(runtime) == 74 == receipt["runtime_members"]
    assert archive["archive"] == {"bytes": 193594705, "sha256": "8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711"}
    archived = {row["path"]: row for row in archive["members"]}
    assert len(archived) == len(archive["members"]) <= 4096
    paths = []
    total = 0
    for row in runtime:
        name = row["path"]
        assert isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts
        assert len(name.encode()) <= 4096 and name not in paths
        paths.append(name)
        source = archived[name]
        assert source["type"] == "file" and source["bytes"] == row["bytes"] and source["sha256"] == row["sha256"]
        total += row["bytes"]
    expected = {name for name, row in archived.items() if row["type"] == "file" and
                (name in {"bin/java", "bin/javac", "release"} or name.startswith(("conf/", "lib/")))
                and name not in {"lib/src.zip", "lib/security/cacerts"}}
    assert set(paths) == expected and paths == sorted(paths)
    assert total == 198674633 == receipt["runtime_bytes"]
    assert receipt["runtime_symlinks"] == [] and receipt["active_operation_attempts"] == []
    assert receipt["provider_runtime_files_observed"] is False
    assert all(row["launcher_match"] is True for row in receipt["hosted_launcher_observations"])
    assert len(receipt["hosted_launcher_observations"]) == 3
    basenames = {Path(name).name for name in paths}
    needed = set()
    for name, dynamic in elf["members"].items():
        assert name in expected
        needed.update(dynamic["needed"])
    assert sorted(needed - basenames) == elf["nonbundled_DT_NEEDED_names"]
    assert "not observed provider resolution" in elf["limitation"]
    for field, name in [("runtime_manifest", "runtime-members.json"), ("archive_manifest", "archive-manifest.json")]:
        actual = identity(packet / name)
        assert {"bytes": actual["bytes"], "sha256": actual["sha256"]} == receipt[field]
    return {"runtime_members": len(runtime), "runtime_bytes": total, "json_archive_runtime_subset_exact": True,
            "provider_runtime_observed": False, "external_elf_names": elf["nonbundled_DT_NEEDED_names"],
            "scope": "derived data-map consistency only; no independent archive checksum/extraction/ELF parse or provider validation"}


def scan_tar_gzip(raw, *, hash_payloads=False):
    """Independent raw USTAR/GNU/PAX scanner; never extracts any member.

    Header/topology pass and payload-hash pass are separate. The raw archive
    remains open to the same file; every gzip byte is consumed for CRC checking.
    """
    import gzip  # Standard-library parser import occurs after install_guards().
    root_name = "jdk-17.0.21+9"
    decompressed_limit = 768 * 1024 * 1024
    max_file = 256 * 1024 * 1024
    pending = {}
    rows = []
    used = 0
    headers = 0

    def field(block):
        value = block.split(b"\0", 1)[0]
        assert len(value) <= 4096 and not any(c < 32 or c == 127 for c in value)
        return value.decode("utf-8")

    def octal(block):
        assert not block[0] & 128, "unreviewed base-256 tar numeric field"
        value = block.strip(b" \0")
        assert not value or all(c in b"01234567" for c in value)
        return int(value or b"0", 8)

    def clean(name):
        assert name and len(name.encode()) <= 4096 and not name.startswith("/")
        parts = name.rstrip("/").split("/")
        assert all(part not in ("", ".", "..") for part in parts)
        assert parts[0] == root_name
        return "/".join(parts[1:])

    def pax(data):
        assert len(data) <= 65536
        values = {}
        at = 0
        while at < len(data):
            end = data.find(b" ", at, min(len(data), at + 16))
            assert end > at and data[at:end].isdigit()
            length = int(data[at:end])
            assert 1 <= length <= 8192 and at + length <= len(data)
            record = data[end + 1:at + length]
            assert record.endswith(b"\n") and b"=" in record
            key, value = record[:-1].split(b"=", 1)
            assert key in (b"path", b"linkpath", b"size", b"mtime", b"atime", b"ctime", b"uid", b"gid", b"uname", b"gname")
            key, value = key.decode("ascii"), value.decode("utf-8")
            assert key not in values and len(value.encode()) <= 4096
            values[key] = value
            at += length
        return values

    raw.seek(0)
    with gzip.GzipFile(fileobj=raw, mode="rb") as stream:
        def read(n):
            nonlocal used
            assert 0 <= n <= 1024 * 1024 and used + n <= decompressed_limit, "tar decompression/read bound"
            data = stream.read(n)
            used += len(data)
            return data

        def exact(n):
            data = read(n)
            assert len(data) == n, "truncated tar"
            return data

        while True:
            header = exact(512)
            if header == b"\0" * 512:
                assert exact(512) == b"\0" * 512 and not pending, "tar terminal blocks/pending extension"
                while True:
                    assert used < decompressed_limit, "decompression budget exhausted before EOF"
                    trailer = read(min(1024 * 1024, decompressed_limit - used))
                    if not trailer: break
                    assert not any(trailer), "hidden nonzero tar trailer"
                assert used % 512 == 0
                break
            headers += 1
            assert headers <= 4096, "tar raw-header bound"
            assert octal(header[148:156]) == sum(header[:148]) + 8 * 32 + sum(header[156:]), "tar header checksum"
            gnu = header[257:265] == b"ustar  \0"
            assert gnu or header[257:263] == b"ustar\0", "unreviewed tar header magic"
            name = field(header[:100])
            if not gnu:
                prefix = field(header[345:500])
                if prefix: name = prefix + "/" + name
            link = field(header[157:257])
            size, mode = octal(header[124:136]), octal(header[100:108])
            kind = header[156:157]
            assert size <= max_file, "tar single-file bound"
            extension = kind in (b"L", b"K", b"x", b"g")
            if extension: assert size <= 65536, "tar extension bound"
            else:
                assert kind in (b"0", b"\0", b"5", b"2", b"1"), "tar special member refused"
                name = pending.get("path", name)
                link = pending.get("linkpath", link)
                if "size" in pending:
                    assert pending["size"].isdigit() and int(pending["size"]) == size, "ambiguous PAX size override"
                pending = {}
                relative = clean(name)
                assert len(rows) < 4096
                if kind not in (b"0", b"\0"): assert size == 0
            digest = hashlib.sha256() if hash_payloads and not extension and kind in (b"0", b"\0") else None
            payload = bytearray() if extension else None
            remaining = size
            while remaining:
                chunk = exact(min(remaining, 1024 * 1024))
                remaining -= len(chunk)
                if digest is not None: digest.update(chunk)
                if payload is not None: payload += chunk
            padding = (-size) % 512
            assert exact(padding) == b"\0" * padding, "nonzero tar member padding"
            if extension:
                if kind in (b"L", b"K"):
                    assert payload and payload[-1] == 0
                    value = field(bytes(payload))
                    key = "path" if kind == b"L" else "linkpath"
                    assert key not in pending
                    pending[key] = value
                else:
                    values = pax(bytes(payload))
                    if kind == b"g":
                        assert not {"path", "linkpath", "size"}.intersection(values), "global PAX identity override"
                    else:
                        assert not set(values).intersection(pending), "duplicate pending tar identity"
                        pending.update(values)
                continue
            row = {"path": relative, "type": "file" if kind in (b"0", b"\0") else "directory" if kind == b"5" else "symlink" if kind == b"2" else "hardlink", "bytes": size, "mode": mode}
            if row["type"] in ("symlink", "hardlink"):
                assert link and len(link.encode()) <= 4096 and not link.startswith("/")
                row["target"] = link
            if digest is not None: row["sha256"] = digest.hexdigest()
            rows.append(row)
    return rows, {"raw_headers": headers, "logical_members": len(rows), "decompressed_bytes": used}


def tar_topology(rows):
    indexed = {row["path"]: row for row in rows}
    assert len(indexed) == len(rows), "duplicate tar member"
    assert indexed.get("", {}).get("type") == "directory", "exact archive root absent"
    links = 0
    for name, row in indexed.items():
        parts = name.split("/") if name else []
        for n in range(1, len(parts)):
            assert indexed.get("/".join(parts[:n]), {}).get("type") == "directory", "non-directory archive parent"
        if row["type"] not in ("symlink", "hardlink"): continue
        links += 1
        current = name
        seen = set()
        while indexed[current]["type"] in ("symlink", "hardlink"):
            assert current not in seen and len(seen) <= 4096, "archive link cycle"
            seen.add(current)
            target = indexed[current]["target"]
            if indexed[current]["type"] == "symlink":
                stack = current.split("/")[:-1]
                for part in target.split("/"):
                    if part in ("", "."): continue
                    if part == "..":
                        assert stack, "archive link escapes root"
                        stack.pop()
                    else: stack.append(part)
                current = "/".join(stack)
            else:
                prefix = "jdk-17.0.21+9/"
                assert target.startswith(prefix)
                current = target[len(prefix):]
                assert all(p not in ("", ".", "..") for p in current.split("/"))
            assert current in indexed, "missing archive link target"
        assert indexed[current]["type"] == "file", "archive link must resolve to ordinary file"
    return {"logical_members": len(rows), "links": links, "all_parents_directories": True, "all_links_internal_acyclic_regular": True}


def check_independent_linux_archive(scratch):
    packet = ROOT / "verification/android-view-api-boundary-linux-tool-profile"
    archive = packet / "local/OpenJDK17U-jdk_x64_linux_hotspot_17.0.21_9.tar.gz"
    checksum = Path(str(archive) + ".sha256.txt")
    assert not archive.is_symlink() and archive.is_file() and archive.stat().st_size == 193594705
    checksum_data = checksum.read_bytes()
    assert len(checksum_data) == 116 and hashlib.sha256(checksum_data).hexdigest() == "c6bc155a92bfda8b0aea9d05819318e8721f9723ecbd4fded4b04aa88308c8fc"
    published, filename = checksum_data.decode("ascii").strip().split()
    assert filename == archive.name and published == "8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711"

    def compressed_hash(stream):
        stream.seek(0)
        size = 0
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk: break
            size += len(chunk)
            assert size <= 256 * 1024 * 1024, "compressed archive byte bound"
            digest.update(chunk)
        assert size == 193594705 and digest.hexdigest() == published
        return {"bytes": size, "sha256": digest.hexdigest()}

    with archive.open("rb") as raw:
        before = compressed_hash(raw)
        first_rows, first_stats = scan_tar_gzip(raw)
        topology = tar_topology(first_rows)  # Must complete before hashing payloads.
        final_rows, final_stats = scan_tar_gzip(raw, hash_payloads=True)
        after = compressed_hash(raw)
    assert before == after and first_stats == final_stats
    assert [{k: v for k, v in row.items() if k != "sha256"} for row in final_rows] == first_rows
    assert topology["logical_members"] == 543 and topology["links"] == 208
    expected_archive = json.loads((packet / "archive-manifest.json").read_text())
    expected = {row["path"]: row for row in expected_archive["members"]}
    actual = {row["path"]: row for row in final_rows if row["path"]}
    assert set(actual) == set(expected)
    for name, row in actual.items():
        assert all(expected[name][key] == value for key, value in row.items()), "independent archive member mismatch: " + name
    runtime = json.loads((packet / "runtime-members.json").read_text())
    for row in runtime:
        found = actual[row["path"]]
        assert found["type"] == "file" and found["bytes"] == row["bytes"] and found["sha256"] == row["sha256"]
    computed = json.dumps(final_rows, sort_keys=True, separators=(",", ":")).encode()
    (scratch / "independent-archive-members.json").write_bytes(computed + b"\n")
    report = {"archive_before_after": before, "published_checksum_copy": identity(checksum), "topology": topology,
              "stream": final_stats, "runtime_members": len(runtime), "all_selected_runtime_bytes_matched": True,
              "all_archive_member_rows_matched": True, "independent_members_sha256": hashlib.sha256(computed).hexdigest(),
              "topology_completed_before_payload_hashing": True, "extraction_install_execution": False,
              "source": "retained official published checksum copy; no independent network fetch",
              "provider_runtime_config_loader_validation": "pending separately; not inferred from archive data"}
    (OWN / "archive-review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def check_frozen_candidate():
    base = ROOT / "verification/android-view-api-boundary-candidate"
    freeze = identity(base / "freeze.json")
    manifest_id = identity(base / "manifest.json")
    assert freeze["sha256"] == "c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff"
    assert manifest_id["sha256"] == "e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834"
    manifest = json.loads((base / "manifest.json").read_text())
    members = manifest["members"]
    assert len(members) == 115 == manifest["member_count"]
    seen = set()
    product = {}
    host_count = cross_count = test_count = total = 0
    for row in members:
        rel = Path(row["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and row["path"] not in seen
        seen.add(row["path"])
        path = base / rel
        assert not path.is_symlink() and path.is_file()
        data = path.read_bytes()
        assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
        total += len(data)
        if row["path"].startswith("source/"):
            product[rel.name] = {"bytes": len(data), "sha256": row["sha256"]}
        host_count += row["path"].startswith("tests/host-leaves/")
        cross_count += row["path"].startswith("tests/cross-leaf/")
        test_count += row["path"] == "tests/ViewApiBoundaryTests.java"
    assert total == 584851 == manifest["member_bytes"]
    tree = hashlib.sha256(json.dumps(product, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert len(product) == 16 and host_count == 86 and cross_count == 1 and test_count == 1
    assert tree == "d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e"
    return {"members": len(members), "bytes": total, "product_tree": tree, "host_compile_sources": len(product) + host_count + test_count, "sdk_compile_sources": len(product) + cross_count}


def check(name: str, fn):
    before = len(ATTEMPTS)
    try:
        detail = fn()
        if len(ATTEMPTS) != before:
            raise AssertionError("subject attempted an active operation")
        CHECKS.append({"name": name, "accepted": True, "detail": detail})
    except BaseException as exc:
        CHECKS.append({"name": name, "accepted": False, "error": str(exc), "traceback": traceback.format_exc()})


def rejects(fn, description: str):
    try:
        result = fn()
    except (ValueError, AssertionError, KeyError, IndexError, UnicodeError) as exc:
        return {"rejected": True, "reason": str(exc), "case": description}
    if isinstance(result, dict) and result.get("accepted") is False:
        return {"rejected": True, "result": result, "case": description}
    raise AssertionError("corruption accepted: " + description + "; result=" + repr(result))


def u1(n):
    return struct.pack(">B", n)


def u2(n):
    return struct.pack(">H", n)


def u4(n):
    return struct.pack(">I", n)


class ClassBuilder:
    """Independent small ClassFile encoder; it does not invoke Java tooling."""
    def __init__(self, owner, source="NativeAppearanceViewsV2.java"):
        self.entries = []
        self.indices = {}
        self.owner = owner
        self.source = source
        self.methods = []

    def cp(self, key, data):
        if key not in self.indices:
            self.indices[key] = len(self.entries) + 1
            self.entries.append(data)
        return self.indices[key]

    def utf(self, value):
        data = value.encode("utf-8")
        return self.cp(("utf", value), u1(1) + u2(len(data)) + data)

    def clazz(self, value):
        return self.cp(("class", value), u1(7) + u2(self.utf(value)))

    def nat(self, name, desc):
        return self.cp(("nat", name, desc), u1(12) + u2(self.utf(name)) + u2(self.utf(desc)))

    def ref(self, owner, name, desc, field=False):
        tag = 9 if field else 10
        return self.cp(("ref", tag, owner, name, desc), u1(tag) + u2(self.clazz(owner)) + u2(self.nat(name, desc)))

    def method(self, name, desc, code, locals=3, stack=8, handlers=b"", handler_count=0, access=0x0008):
        self.methods.append((name, desc, bytes(code), locals, stack, handlers, handler_count, access))

    def constructor(self):
        ref = self.ref("java/lang/Object", "<init>", "()V")
        self.method("<init>", "()V", b"\x2a\xb7" + u2(ref) + b"\xb1", locals=1, stack=1, access=0x0002)

    def build(self):
        this = self.clazz(self.owner)
        parent = self.clazz("java/lang/Object")
        code_name = self.utf("Code")
        source_name = self.utf("SourceFile")
        source_value = self.utf(self.source)
        nested = self.owner in {VIEWS + "$Api29", VIEWS + "$Api30", "dev/mixer/android/NativeRenderer$Api30"}
        nested_attrs = b""
        if nested:
            outer, inner = self.owner.rsplit("$", 1)
            inner_attr = self.utf("InnerClasses")
            nest_attr = self.utf("NestHost")
            outer_index = self.clazz(outer)
            inner_index = self.utf(inner)
            nested_attrs = (u2(inner_attr) + u4(10) + u2(1) + u2(this) + u2(outer_index) + u2(inner_index) + u2(0x1a)
                            + u2(nest_attr) + u4(2) + u2(outer_index))
        out_methods = []
        for name, desc, code, locals, stack, handlers, handler_count, access in self.methods:
            data = u2(stack) + u2(locals) + u4(len(code)) + code + u2(handler_count) + handlers + u2(0)
            out_methods.append(u2(access) + u2(self.utf(name)) + u2(self.utf(desc)) + u2(1) + u2(code_name) + u4(len(data)) + data)
        return (b"\xca\xfe\xba\xbe" + u2(0) + u2(61) + u2(len(self.entries) + 1) + b"".join(self.entries)
                + u2(0x0030) + u2(this) + u2(parent) + u2(0) + u2(0)
                + u2(len(out_methods)) + b"".join(out_methods)
                + u2(3 if nested else 1) + u2(source_name) + u4(2) + u2(source_value) + nested_attrs)


VIEWS = "dev/mixer/android/NativeAppearanceViewsV2"
MUTATION = VIEWS + "$Mutation"
VIEW = "android/view/View"
STATE_DESC = "(Ljava/lang/CharSequence;)V"


def api30_class(*, mutation_local=2, mutation_name="require", mutation_owner=MUTATION,
                setter_owner=VIEW, setter_desc=STATE_DESC, extra_after_setter=b"", truncate=False):
    builder = ClassBuilder(VIEWS + "$Api30")
    builder.constructor()
    setter = builder.ref(setter_owner, "setStateDescription", setter_desc)
    require = builder.ref(mutation_owner, mutation_name, "()V")
    body = bytes([0x2a, 0x2b, 0xb6]) + u2(setter) + extra_after_setter + bytes([0x2a + mutation_local, 0xb6]) + u2(require) + bytes([0xb1])
    if truncate:
        body = body[:-3] + b"\xb6"
    desc = "(Landroid/view/View;Ljava/lang/CharSequence;L" + MUTATION + ";)V"
    builder.method("stateDescription", desc, body)
    return builder.build(), desc


def api29_class(*, order=None, mutation_local=2, record_local=1, receiver_local=0,
                omit_postcheck=None, wrong_drawable=None):
    builder = ClassBuilder(VIEWS + "$Api29")
    builder.constructor()
    setter_order = order or ["setTextCursorDrawable", "setTextSelectHandle", "setTextSelectHandleLeft", "setTextSelectHandleRight"]
    body = bytearray()
    for n, name in enumerate(setter_order):
        drawable = VIEWS + ("$Cursor" if n == 0 or wrong_drawable == n else "$Handle")
        new_type = builder.clazz(drawable)
        ctor = builder.ref(drawable, "<init>", "(L" + VIEWS + "$Record;)V")
        setter = builder.ref(VIEWS + "$NativeField", name, "(Landroid/graphics/drawable/Drawable;)V")
        require = builder.ref(MUTATION, "require", "()V")
        body += bytes([0x2a + receiver_local, 0xbb]) + u2(new_type) + bytes([0x59, 0x2a + record_local, 0xb7]) + u2(ctor)
        body += b"\xb6" + u2(setter)
        if omit_postcheck != n:
            body += bytes([0x2a + mutation_local, 0xb6]) + u2(require)
    body += b"\xb1"
    desc = "(L" + VIEWS + "$NativeField;L" + VIEWS + "$Record;L" + MUTATION + ";)V"
    builder.method("authoredSelection", desc, body, locals=3)
    return builder.build()


def legacy_class():
    builder = ClassBuilder("dev/mixer/android/NativeRenderer$Api30", "NativeRenderer.java")
    builder.constructor()
    setter = builder.ref(VIEW, "setStateDescription", STATE_DESC)
    builder.method("stateDescription", "(Landroid/view/View;Ljava/lang/CharSequence;)V", b"\x2a\x2b\xb6" + u2(setter) + b"\xb1", locals=2)
    return builder.build()


def uleb(n):
    assert 0 <= n < 2**32
    out = bytearray()
    while n >= 128:
        out.append((n & 127) | 128)
        n >>= 7
    out.append(n)
    return bytes(out)


def api30_dex(*, mutation_reg=2, setter_first=True, mutation_name="require",
              mutation_owner=MUTATION, extra_words=(), bad_method_index=False,
              with_guard=False, sdk_alias=False, bypass_sdk_read=False, legacy=False,
              api29=False, hoist_allocations=False, record_reg=5, receiver_reg=4,
              api29_mutation_reg=6, omit_api29_postcheck=None, api29_order=None,
              reuse_handle=False):
    """Encode a selected static helper and real method_ids/code_item references.

    This synthetic valid-format binary is parser/control data, not compiled
    product evidence. No source, BCI receipt or text string can authorize it.
    """
    assert not (api29 and (legacy or with_guard))
    owner = "L" + ("dev/mixer/android/NativeRenderer" if legacy else VIEWS) + ("$Api29;" if api29 else "$Api30;")
    view = "L" + VIEWS + "$NativeField;" if api29 else "Landroid/view/View;"
    value_type = "L" + VIEWS + "$Record;" if api29 else "Ljava/lang/CharSequence;"
    mutation = "L" + MUTATION + ";"
    refs = [
        (owner, "authoredSelection" if api29 else "stateDescription", (view, value_type) + (() if legacy else (mutation,))),
        (view, "setTextCursorDrawable" if api29 else "setStateDescription", ("Landroid/graphics/drawable/Drawable;" if api29 else value_type,)),
        ("L" + mutation_owner + ";", mutation_name, ()),
        (owner, "<init>", ()),
        ("Ljava/lang/Object;", "<init>", ()),
    ]
    guard_owner = "Lreview/Guard;"
    if with_guard:
        refs.append((guard_owner, "run", refs[0][2]))
    if api29:
        refs += [(view, name, ("Landroid/graphics/drawable/Drawable;",)) for name in ("setTextSelectHandle", "setTextSelectHandleLeft", "setTextSelectHandleRight")]
        refs += [("L" + VIEWS + suffix, "<init>", (value_type,)) for suffix in ("$Cursor;", "$Handle;")]
    types = {"V", "Ljava/lang/Object;", view, value_type, mutation, owner, "L" + mutation_owner + ";"}
    types |= {p for _, _, params in refs for p in params} | {o for o, _, _ in refs}
    if with_guard:
        types |= {guard_owner, "Landroid/os/Build$VERSION;", "I"}
    protos = {params for _, _, params in refs}
    strings = sorted(types | {name for _, name, _ in refs} | {"V" + "L" * len(params) for params in protos} | {"NativeAppearanceViewsV2.java"})
    if with_guard:
        strings = sorted(set(strings) | {"SDK_INT", "Guard.java"})
    si = {s: i for i, s in enumerate(strings)}
    typelist = sorted(types, key=si.__getitem__)
    ti = {s: i for i, s in enumerate(typelist)}
    protolist = sorted(protos, key=lambda p: (ti["V"], tuple(ti[x] for x in p)))
    pi = {p: i for i, p in enumerate(protolist)}
    methodlist = sorted(refs, key=lambda m: (ti[m[0]], si[m[1]], pi[m[2]]))
    mi = {m: i for i, m in enumerate(methodlist)}
    off = 112
    string_off = off; off += 4 * len(strings)
    type_off = off; off += 4 * len(typelist)
    proto_off = off; off += 12 * len(protolist)
    field_off = off if with_guard else 0
    off += 8 if with_guard else 0
    method_off = off; off += 8 * len(methodlist)
    class_off = off; off += 32 * (2 if with_guard else 1)
    data_off = off
    data = bytearray()

    def absolute():
        return data_off + len(data)

    def align():
        while absolute() % 4:
            data.append(0)

    string_offsets = []
    for s in strings:
        string_offsets.append(absolute())
        data += uleb(len(s)) + s.encode() + b"\0"
    param_offsets = {}
    for params in protolist:
        if params:
            align()
            param_offsets[params] = absolute()
            data += struct.pack("<I", len(params)) + b"".join(struct.pack("<H", ti[p]) for p in params)
        else:
            param_offsets[params] = 0
    align()
    code_off = absolute()
    setter_index = mi[refs[1]]
    if bad_method_index:
        setter_index = len(methodlist) + 10
    setter = [0x206e, setter_index, 0x0010]
    require = [0x106e, mi[refs[2]], mutation_reg]
    words = (setter + list(extra_words) if legacy else setter + list(extra_words) + require if setter_first else require + setter) + [0x000e]
    if api29:
        allocations = []
        native_calls = []
        order = api29_order or [0, 1, 2, 3]
        for n in range(4):
            temp_reg = n if hoist_allocations else 0
            allocation = ([0x22 | temp_reg << 8, ti[refs[8 if n == 0 else 9][0]]]
                          + [0x2070, mi[refs[8 if n == 0 else 9]], temp_reg | record_reg << 4])
            if reuse_handle and n >= 2:
                allocation = []
            allocations.append(allocation)
            setter_ref = refs[1 if order[n] == 0 else 4 + order[n]]
            invocation = [0x206e, mi[setter_ref], receiver_reg | temp_reg << 4]
            if n != omit_api29_postcheck:
                invocation += [0x106e, mi[refs[2]], api29_mutation_reg]
            native_calls.append(invocation)
        if hoist_allocations:
            words = sum(allocations, []) + sum(native_calls, []) + [0x000e]
        else:
            words = sum((allocation + invocation for allocation, invocation in zip(allocations, native_calls)), []) + [0x000e]
    data += struct.pack("<HHHHII", 7 if api29 else 2 if legacy else 3, 3 if api29 else 2 if legacy else 3, 2, 0, 0, len(words))
    data += b"".join(struct.pack("<H", n) for n in words)
    align()
    ctor_code_off = absolute()
    ctor_words = [0x1070, mi[refs[4]], 0x0000, 0x000e]
    data += struct.pack("<HHHHII", 1, 1, 1, 0, 0, len(ctor_words))
    data += b"".join(struct.pack("<H", n) for n in ctor_words)
    guard_code_off = None
    if with_guard:
        align()
        guard_code_off = absolute()
        prelude = [0x0013, 127, 0x0029, 4] if bypass_sdk_read else []
        constreg = 0 if sdk_alias else 1
        guard_words = prelude + [0x0060, 0, 0x13 | constreg << 8, 30,
                                 0x34 | constreg << 12, 5, 0x2071 if legacy else 0x3071, mi[refs[0]], 0x0032 if legacy else 0x0432, 0x000e]
        data += struct.pack("<HHHHII", 4 if legacy else 5, 2 if legacy else 3, 2 if legacy else 3, 0, 0, len(guard_words))
        data += b"".join(struct.pack("<H", n) for n in guard_words)
    class_data_off = absolute()
    data += b"\0\0\x02\0"
    previous = 0
    for method_index, flags, method_code_off in sorted([(mi[refs[0]], 0x8, code_off), (mi[refs[3]], 0x10002, ctor_code_off)]):
        data += uleb(method_index - previous) + uleb(flags) + uleb(method_code_off)
        previous = method_index
    guard_data_off = None
    if with_guard:
        guard_data_off = absolute()
        data += b"\0\0\x01\0" + uleb(mi[refs[5]]) + uleb(0x8) + uleb(guard_code_off)
    align()
    map_off = absolute()
    maps = [
        (0x0000, 1, 0), (0x0001, len(strings), string_off), (0x0002, len(typelist), type_off),
        (0x0003, len(protolist), proto_off), (0x0005, len(methodlist), method_off), (0x0006, 2 if with_guard else 1, class_off),
        (0x2002, len(strings), string_offsets[0]),
    ]
    if with_guard:
        maps.append((0x0004, 1, field_off))
    if any(protolist):
        maps.append((0x1001, sum(bool(p) for p in protolist), min(v for v in param_offsets.values() if v)))
    maps += [(0x2001, 3 if with_guard else 2, code_off), (0x2000, 2 if with_guard else 1, class_data_off), (0x1000, 1, map_off)]
    maps.sort(key=lambda row: row[2])
    data += struct.pack("<I", len(maps)) + b"".join(struct.pack("<HHII", kind, 0, size, offset) for kind, size, offset in maps)
    header = bytearray(112)
    header[:8] = b"dex\n039\0"
    struct.pack_into("<20I", header, 32, data_off + len(data), 112, 0x12345678, 0, 0, map_off,
                     len(strings), string_off, len(typelist), type_off, len(protolist), proto_off,
                     1 if with_guard else 0, field_off, len(methodlist), method_off, 2 if with_guard else 1, class_off, len(data), data_off)
    tables = b"".join(struct.pack("<I", x) for x in string_offsets)
    tables += b"".join(struct.pack("<I", si[x]) for x in typelist)
    tables += b"".join(struct.pack("<III", si["V" + "L" * len(p)], ti["V"], param_offsets[p]) for p in protolist)
    if with_guard:
        tables += struct.pack("<HHI", ti["Landroid/os/Build$VERSION;"], ti["I"], si["SDK_INT"])
    tables += b"".join(struct.pack("<HHI", ti[o], pi[p], si[n]) for o, n, p in methodlist)
    class_rows = [(owner, "NativeAppearanceViewsV2.java", class_data_off)]
    if with_guard:
        class_rows.append((guard_owner, "Guard.java", guard_data_off))
    for class_owner, source, data_at in sorted(class_rows, key=lambda row: ti[row[0]]):
        tables += struct.pack("<8I", ti[class_owner], 0x30, ti["Ljava/lang/Object;"], 0, si[source], 0, data_at, 0)
    binary = bytearray(header + tables + data)
    binary[12:32] = hashlib.sha1(binary[32:]).digest()
    struct.pack_into("<I", binary, 8, zlib.adler32(binary[12:]) & 0xffffffff)
    return bytes(binary), refs, mi[refs[0]]


def guard_class(*, bypass_sdk_read=False, sdk_owner="android/os/Build$VERSION", field_tag=True):
    builder = ClassBuilder("review/Guard", "Guard.java")
    field = builder.ref(sdk_owner, "SDK_INT", "I", field=field_tag)
    desc = "(Landroid/view/View;Ljava/lang/CharSequence;)V"
    helper = builder.ref("dev/mixer/android/NativeRenderer$Api30", "stateDescription", desc)
    body = bytearray()
    if bypass_sdk_read:
        # Push a fake supported value, then jump over getstatic to bipush 30.
        body += b"\x10\x7f\xa7\x00\x06"
    body += b"\xb2" + u2(field) + b"\x10\x1e"
    branch_pc = len(body)
    body += b"\xa1\x00\x00"
    body += b"\x2a\x2b\xb8" + u2(helper)
    low_pc = len(body)
    body += b"\xb1"
    body[branch_pc + 1:branch_pc + 3] = struct.pack(">h", low_pc - branch_pc)
    builder.method("run", desc, body, locals=2)
    return builder.build(), ("run", desc)


def main() -> int:
    # Atomic mkdir chooses a unique scratch without randomness, clocks or cleanup.
    local = OWN / "local"
    local.mkdir(exist_ok=True)
    scratch = None
    for n in range(1, 65):
        candidate = local / ("data-run-%03d" % n)
        try:
            candidate.mkdir()
            scratch = candidate
            break
        except FileExistsError:
            pass
    if scratch is None:
        raise AssertionError("bounded scratch slots exhausted; retain prior evidence")
    guards = install_guards()
    result = {
        "schema": 1,
        "scope": "independent pure Python binary/filesystem controls; no compiler/runtime/process/timer/socket activity",
        "scratch": str(scratch.relative_to(ROOT)),
        "scratch_retained": True,
        "guarded_before_subject_import": True,
        "guards": guards,
        "tool": {"executable": sys.executable, "version": sys.version, "identity": identity(Path(sys.executable).resolve())},
        "command": "/opt/homebrew/opt/python@3.14/bin/python3.14 -I -B verification/android-view-api-boundary-host-independent/check_review.py",
        "script": identity(Path(__file__)),
        "checks": CHECKS,
        "active_attempts": ATTEMPTS,
    }
    try:
        check("exact-frozen-candidate-115-member-closure", check_frozen_candidate)
        check("exact-final-inspector-seven-member-seal", check_inspector_seal)
        check("exact-final-admission-seventeen-member-seal", check_final_admission_seal)
        if not all(row["accepted"] for row in CHECKS):
            raise AssertionError("sealed inputs refused before any subject import")
        linux_profile = ROOT / "verification/android-view-api-boundary-linux-tool-profile"
        if (linux_profile / "runtime-members.json").exists():
            check("linux-tool-profile-derived-data-subset-and-ELF-boundary", check_linux_profile_data)
            check("linux-official-published-checksum-and-independent-tar-runtime-bytes", lambda: check_independent_linux_archive(scratch))
        admission = load_subject("independent_view_api_collect", ROOT / "verification/android-view-api-boundary-host-admission/collect.py")
        custody = load_subject("independent_view_api_custody", ROOT / "verification/android-view-api-boundary-host-admission/custody.py")
        result["admission"] = identity(ROOT / "verification/android-view-api-boundary-host-admission/collect.py")
        result["custody"] = identity(ROOT / "verification/android-view-api-boundary-host-admission/custody.py")
        run_admission_controls(admission, custody, scratch)
        inspect = load_subject("independent_view_api_inspect", ROOT / "verification/android-view-api-boundary-bytecode-inspection/inspect_artifacts.py")
        result["inspector"] = identity(ROOT / "verification/android-view-api-boundary-bytecode-inspection/inspect_artifacts.py")
        run_inspector_controls(inspect, scratch)
    except BaseException as exc:
        result["setup_error"] = str(exc)
        result["setup_traceback"] = traceback.format_exc()
    result["all_pass"] = bool(CHECKS) and all(c["accepted"] for c in CHECKS) and not ATTEMPTS and "setup_error" not in result
    encoded = json.dumps(result, indent=2) + "\n"
    (scratch / "result.json").write_text(encoded)
    (OWN / "data-checks.json").write_text(encoded)
    print(json.dumps({"checks": len(CHECKS), "all_pass": result["all_pass"], "scratch": result["scratch"]}))
    return 0 if result["all_pass"] else 1


def run_admission_controls(admission, custody, scratch: Path):
    packet = ROOT / "verification/android-view-api-boundary-host-admission"
    manifest = json.loads((packet / "input-manifest.json").read_text())
    profile = json.loads((packet / "tool-profile.json").read_text())
    check("admission-frozen-input-closure", admission.verify_frozen_inputs)

    def selected_profile():
        linux = ROOT / "verification/android-view-api-boundary-linux-tool-profile"
        assert profile["id"] == "official-temurin17.0.21+9-linux-x64-sdk37-d8-084a89126ae0-exact-v1"
        assert profile["identity_mode"] == "official-jdk-runtime-files-v1"
        assert profile["host_os"] == "linux" and profile["host_machine"] == "x86_64"
        assert (packet / profile["jdk_runtime_manifest"]).read_bytes() == (linux / "runtime-members.json").read_bytes()
        seal_id = identity(linux / "seal.json")
        assert profile["jdk_profile_seal"] == {"path": seal_id["path"], "bytes": seal_id["bytes"], "sha256": seal_id["sha256"]}
        seal = json.loads((linux / "seal.json").read_text())
        assert seal["member_count"] == len(seal["members"]) == 13
        observed = set()
        nodes = 1
        for base, dirs, names in os.walk(linux, followlinks=False):
            nodes += len(dirs) + len(names)
            assert nodes <= 256
            for name in list(dirs):
                path = Path(base) / name
                assert not path.is_symlink()
                if name == "local": dirs.remove(name)
            for name in names:
                path = Path(base) / name
                assert path.is_file() and not path.is_symlink()
                rel = path.relative_to(linux).as_posix()
                if rel != "seal.json": observed.add(rel)
        assert observed == {row["path"] for row in seal["members"]}
        for row in seal["members"]:
            value = identity(linux / row["path"])
            assert value["bytes"] == row["bytes"] and value["sha256"] == row["sha256"]
        assert profile["packaging_boundary"]["hosted_runtime_files_observed"] is False
        assert profile["packaging_boundary"]["provider_system_boundary"]["exact_system_library_hashes_known"] is False
        assert profile["collector_python"]["boundary"] == "root-admitted-ubuntu-provider-infrastructure"
        assert profile["collector_python"]["bootstrap_stdlib_OS_and_GitHub_actions_independently_pinned"] is False
        assert profile["collector_python"]["path"] == "/usr/bin/python3" and profile["collector_python"]["version"] == [3, 12, 3]
        assert profile["files"][profile["android_platform"] + "/android.jar"] == {"bytes": 43044472, "sha256": "bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177"}
        assert profile["files"][profile["android_build_tools"] + "/lib/d8.jar"] == {"bytes": 20528803, "sha256": "a26ee56252adcff6752c379ae255a0ad538ebec60189e078ec6855487107637d"}
        admitted = json.loads((packet / "admission.json").read_text())
        assert admitted["tool_profile_id"] == profile["id"]
        assert admitted["dispatch_authorized_by_this_packet"] is False and admitted["workflow_installed"] is False
        assert admitted["inspector"]["file_sha256"] == "7e15cfa979f19a72443436dc3f64bba2a6b88c2ed652e8956e96dd454380d83b"
        workflow = (packet / "workflow.DRAFT.yml").read_text()
        assert "runs-on: ubuntu-24.04" in workflow and "timeout-minutes: 22" in workflow
        uses = [line.strip() for line in workflow.splitlines() if "uses:" in line]
        assert uses == ["- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"]
        assert "/usr/bin/python3 -I -B" in workflow
        return {"profile": profile["id"], "jdk_profile_seal": seal_id, "runtime_members": 74,
                "source_only_preparation": True, "ambient_provider_bootstrap_system_boundary": True}
    check("admission-selected-linux-profile-exact-runtime-data-boundary", selected_profile)

    def finite_plan():
        plan = admission.build_plan(ROOT, scratch / "selected-future-output", profile, manifest)
        commands = plan["commands"]
        assert [row["name"] for row in commands] == ["java-version", "javac-version", "d8-version", "host-compile", "focused-main", "sdk37-compile"]
        assert plan["command_count"] == 7 and plan["version_commands"] == 3 and plan["work_commands"] == 4
        host = commands[3]["argv"]
        sdk = commands[5]["argv"]
        assert len([a for a in host if a.endswith(".java")]) == 103
        assert len([a for a in sdk if a.endswith(".java")]) == 17
        assert sum("/tests/host-leaves/" in a for a in host) == 86
        assert not any("/tests/host-leaves/" in a or "ViewApiBoundaryTests.java" in a for a in sdk)
        for argv in (host, sdk):
            assert argv[argv.index("--release") + 1] == "17"
            assert all(flag in argv for flag in ("-proc:none", "-Xlint:all", "-Werror", "-sourcepath", "-classpath"))
            assert not any(a.startswith("@") for a in argv)
        main = commands[4]["argv"]
        assert main[-2] == "dev.mixer.android.ViewApiBoundaryTests" and main[-1].endswith("/tests/descriptor.json")
        d8 = plan["d8_prefix"]
        assert d8[d8.index("--min-api") + 1] == "28"
        assert "com.android.tools.r8.D8" in d8 and not d8[0].endswith("/d8")
        assert all(Path(c["argv"][0]).is_absolute() for c in commands)
        return {"host_sources": 103, "sdk_sources": 17, "children": 7, "main": main[-2], "d8_min_api": 28}
    check("admission-finite-explicit-plan-no-matrix-or-installer", finite_plan)
    rowroot = scratch / "row-control"
    rowroot.mkdir()
    (rowroot / "input").write_bytes(b"frozen")
    row = {"path": "input", "bytes": 6, "sha256": hashlib.sha256(b"frozen").hexdigest()}
    check("admission-row-positive-exact-data", lambda: admission.verify_rows(rowroot, [row]))
    for name, rows in [
        ("duplicate-member", [row, row]),
        ("escaping-member", [{**row, "path": "../input"}]),
        ("stale-member-digest", [{**row, "sha256": "0" * 64}]),
    ]:
        check("admission-rejects-" + name, lambda rows=rows, name=name: runtime_refusal(lambda: admission.verify_rows(rowroot, rows), name))
    closed = scratch / "closed-map-control"
    closed.mkdir()
    (closed / "Synthetic.class").write_bytes(b"data-only identity fixture")
    check("admission-emitted-map-positive-ordinary-file", lambda: assert_true(len(admission.emitted_map(closed)) == 1))
    (closed / "directory-link").symlink_to(rowroot, target_is_directory=True)
    check("admission-emitted-map-rejects-directory-symlink", lambda: runtime_refusal(lambda: admission.emitted_map(closed), "unreviewed directory symlink"))
    check("admission-scratch-rejects-directory-symlink", lambda: runtime_refusal(lambda: admission.scratch_bound(closed, profile), "unreviewed scratch directory symlink"))
    nodes = scratch / "node-limit-control"
    nodes.mkdir()
    for n in range(4):
        (nodes / str(n)).mkdir()
    check("admission-discovery-bounds-empty-directories", lambda: runtime_refusal(lambda: admission.bounded_files(nodes, 3), "empty-directory node budget exceeded"))
    pruned = scratch / "pruned-history-control"
    (pruned / "local").mkdir(parents=True)
    (pruned / "member").write_bytes(b"exact")
    for n in range(4):
        (pruned / "local" / str(n)).mkdir()
    check("admission-prunes-local-history-before-descent", lambda: assert_true(admission.bounded_files(pruned, 3, prune_local=True) == [pruned / "member"]))
    selection = {"purpose": "android-view-api-focused-hosted-only", "dispatch_selected": True, "github_sha": "1" * 40, "dispatch_nonce": "2" * 64}
    environment = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "snowdamiz/mixer", "GITHUB_SHA": "1" * 40, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}
    for name, selected, env in [
        ("no-explicit-dispatch", {**selection, "dispatch_selected": False}, environment),
        ("foreign-repository", selection, {**environment, "GITHUB_REPOSITORY": "review/other"}),
        ("workflow-retry", selection, {**environment, "GITHUB_RUN_ATTEMPT": "2"}),
        ("missing-once-only-nonce", {**selection, "dispatch_nonce": ""}, environment),
        ("different-workflow-revision", selection, {**environment, "GITHUB_SHA": "3" * 40}),
    ]:
        check("admission-selection-rejects-" + name, lambda selected=selected, env=env, name=name: runtime_refusal(lambda: admission.validate_selection(selected, env), name))

    terminal = {key: True for key in ("spawned", "direct_exit_observed_without_reap", "signals_retired", "direct_reaped", "group_absent", "stdout_eof", "stderr_eof", "preflight_ok", "postflight_ok")}
    terminal.update(exit_code=0, errors=[], group_probe_count=1)
    check("custody-terminal-positive-all-independent-requirements", lambda: assert_true(custody.terminal_verdict(terminal)))
    for key in ("spawned", "direct_exit_observed_without_reap", "signals_retired", "direct_reaped", "group_absent", "stdout_eof", "stderr_eof", "preflight_ok", "postflight_ok"):
        check("custody-refuses-missing-" + key, lambda key=key: assert_true(not custody.terminal_verdict({**terminal, key: False})))
    check("custody-refuses-nonzero-exit", lambda: assert_true(not custody.terminal_verdict({**terminal, "exit_code": 1})))
    check("custody-refuses-preserved-error", lambda: assert_true(not custody.terminal_verdict({**terminal, "errors": ["output overflow"]})))

    real_subject_os = custody.os
    fake_calls = []

    def fake_killpg(pgid, sig):
        fake_calls.append([pgid, sig])
        if behavior[0] == "absent":
            raise ProcessLookupError("synthetic ESRCH")
        if behavior[0] == "inaccessible":
            raise PermissionError("synthetic EPERM")

    behavior = ["absent"]
    custody.os = SimpleNamespace(killpg=fake_killpg)
    try:
        def observation(case):
            fake_calls.clear()
            behavior[0] = case
            state = {"signals_retired": True, "direct_reaped": True, "spawned": True, "pid": 101, "pgid": 101, "signals": []}
            if case == "inaccessible":
                runtime_refusal(lambda: custody.observe_terminal_group(state), "EPERM held")
            else:
                assert custody.observe_terminal_group(state) is (case == "absent")
            assert fake_calls == [[101, 0]] and state["group_probe_count"] == 1
            runtime_refusal(lambda: custody.observe_terminal_group(state), "second terminal probe")
            runtime_refusal(lambda: custody.signal_owned(state, 15, "late"), "signal after permanent retirement")
            assert fake_calls == [[101, 0]]
            return {"synthetic_observation": case, "calls": list(fake_calls), "later_signal_probe_denied": True}
        for case in ("absent", "present", "inaccessible"):
            check("custody-one-terminal-observation-" + case, lambda case=case: observation(case))
        for name, state in [
            ("unspawned", {"spawned": False, "pid": 101, "pgid": 101}),
            ("foreign-group", {"spawned": True, "pid": 101, "pgid": 102}),
            ("already-reaped", {"spawned": True, "pid": 101, "pgid": 101, "direct_reaped": True}),
            ("retired", {"spawned": True, "pid": 101, "pgid": 101, "signals_retired": True}),
        ]:
            check("custody-denies-signal-" + name, lambda state=state, name=name: runtime_refusal(lambda: custody.signal_owned(state, 15, "invalid"), name))
    finally:
        custody.os = real_subject_os
    run_mock_custody_controls(custody, profile["bounds"], scratch)


def run_mock_custody_controls(custody, bounds, scratch):
    """Exercise actual custody loop with local objects, never OS activity."""
    real = custody.os, custody.subprocess, custody.selectors, custody.time

    def scenario(case):
        directory = scratch / ("mock-custody-" + case)
        calls = []
        reaped = [False]
        ticks = [0.0]
        spawn_count = [0]
        chunks = {101: [b"stdout data\n", b""], 102: [b"stderr data\n", b""]}

        class Stream:
            def __init__(self, fd): self.fd = fd
            def fileno(self): return self.fd
            def close(self): pass

        class Child:
            pid = 101
            stdout = Stream(101)
            stderr = Stream(102)
            def poll(self): raise AssertionError("early reaping poll forbidden")
            def wait(self, timeout):
                assert timeout == 2 and not reaped[0]
                retired = json.loads((directory / "signal-authority-retired.json").read_text())
                assert retired["irreversible"] is True and retired["before_direct_reap"] is True
                reaped[0] = True
                calls.append(["wait", timeout])
                return 0

        class Selector:
            def __init__(self): self.entries = {}
            def register(self, stream, events, key): self.entries[stream.fd] = key
            def unregister(self, stream): del self.entries[stream.fd]
            def select(self, timeout):
                assert timeout == 0.05
                return [(SimpleNamespace(data=key), 1) for fd, key in sorted(self.entries.items())]
            def close(self): pass

        def popen(argv, **kwargs):
            spawn_count[0] += 1
            assert spawn_count[0] == 1 and kwargs["shell"] is False and kwargs["start_new_session"] is True
            assert kwargs["close_fds"] is True and kwargs["stdin"] == -3 and kwargs["stdout"] == kwargs["stderr"] == -1
            # Never call preexec_fn: it belongs only to a real future child.
            assert callable(kwargs["preexec_fn"])
            calls.append(["spawn", 101])
            return Child()

        def waitid(pid_type, pid, flags):
            assert pid == 101 and not reaped[0]
            return SimpleNamespace(si_pid=102 if case == "wrong-waitid-pid" else 101,
                                   si_code=99 if case == "wrong-waitid-status" else 1,
                                   si_status=1 if case == "reaped-status-mismatch" else 0)

        def read(fd, count):
            assert count == 65536
            if case == "missing-stderr-eof" and fd == 102 and len(chunks[102]) == 1:
                return b"x"
            return chunks[fd].pop(0) if chunks[fd] else b""

        def killpg(pgid, sig):
            assert pgid == 101
            calls.append(["killpg", pgid, sig])
            if sig:
                assert not reaped[0], "signal after reap"
            else:
                assert reaped[0], "group probe before reap"
                assert len([c for c in calls if c[0] == "killpg" and c[2] == 0]) == 1
                if case == "present-group": return
                if case == "inaccessible-group": raise PermissionError("mock EPERM")
                raise ProcessLookupError("mock ESRCH")

        def clock():
            ticks[0] += 1.0
            assert ticks[0] <= 80, "finite mocked loop budget"
            return ticks[0]

        def preflight():
            if case == "preflight-failure": raise RuntimeError("mock input changed")
            return {"exact": True}

        fake_os = SimpleNamespace(P_PID=1, WEXITED=4, WNOHANG=1, WNOWAIT=0x100000,
                                  CLD_EXITED=1, CLD_KILLED=2, CLD_DUMPED=3,
                                  waitid=waitid, killpg=killpg, read=read, set_blocking=lambda fd, value: None)
        if case == "unsupported-nonreaping-wait": del fake_os.WNOWAIT
        custody.os = fake_os
        custody.subprocess = SimpleNamespace(Popen=popen, DEVNULL=-3, PIPE=-1)
        custody.selectors = SimpleNamespace(DefaultSelector=Selector, EVENT_READ=1)
        custody.time = SimpleNamespace(monotonic=clock)
        accepted = None
        try:
            accepted = custody.run_command("synthetic", ["/synthetic/never-executed-java"], scratch, {}, directory, bounds, preflight, lambda: {"exact": True})
        except custody.Refusal:
            assert case != "success"
        state = json.loads((directory / "result.json").read_text())
        assert state["accepted"] is (case == "success")
        assert state["retries"] == 0 and state["postflight_ok"] is True
        if case in ("preflight-failure", "unsupported-nonreaping-wait"):
            assert spawn_count[0] == 0 and not state["spawned"] and not calls
        else:
            assert spawn_count[0] == 1 and state["direct_reaped"] and state["signals_retired"]
            if case in ("wrong-waitid-pid", "wrong-waitid-status"):
                assert not state["stdout_eof"] and not state["stderr_eof"]
            else:
                assert state["stdout_eof"] and state["stderr_eof"] is (case != "missing-stderr-eof")
            assert len([c for c in calls if c[0] == "killpg" and c[2] == 0]) == 1
            last = calls[-1]
            assert last[0] == "killpg" and last[2] == 0
        return {"case": case, "synthetic_calls": calls, "accepted": state["accepted"], "retained_result": str((directory / "result.json").relative_to(ROOT))}

    try:
        for case in ("success", "missing-stderr-eof", "present-group", "inaccessible-group", "preflight-failure", "unsupported-nonreaping-wait", "wrong-waitid-pid", "wrong-waitid-status", "reaped-status-mismatch"):
            check("custody-actual-loop-pure-mock-" + case, lambda case=case: scenario(case))
    finally:
        custody.os, custody.subprocess, custody.selectors, custody.time = real


def runtime_refusal(fn, description):
    try:
        fn()
    except RuntimeError as exc:
        return {"rejected": True, "case": description, "reason": str(exc)}
    raise AssertionError("expected bounded refusal: " + description)


def assert_true(value):
    assert value is True
    return True


def run_inspector_controls(inspect, scratch: Path):
    # The producer's documented low-level binary parsers let independent fixtures
    # distinguish real method references from source strings or stale text.
    good_class, state_desc = api30_class()
    (scratch / "synthetic-api30.class").write_bytes(good_class)

    def class_positive():
        parsed = inspect.ClassFile(good_class)
        assert parsed.name == VIEWS + "$Api30"
        method = parsed.methods[("stateDescription", state_desc)]
        assert method["code"]
        refs = [i["ref"] for i in method["instructions"] if i.get("ref")]
        assert any("setStateDescription" in str(ref) for ref in refs)
        assert any("require" in str(ref) for ref in refs)
        return {"class": parsed.name, "instruction_refs": refs, "fixture": "hand-encoded; not product output"}

    check("class-binary-positive-actual-code-methodrefs", class_positive)
    class_root = scratch / "incomplete-class-output"
    class_path = class_root / (VIEWS + "$Api30.class")
    class_path.parent.mkdir(parents=True)
    class_path.write_bytes(good_class)
    check("public-classes-refuses-incomplete-product-topology", lambda: rejects(lambda: inspect.inspect_classes(class_root), "one helper cannot stand in for all16 product groups"))
    wrong_root = scratch / "wrong-owner-path-output"
    wrong_root.mkdir()
    (wrong_root / "stale.class").write_bytes(good_class)
    check("public-classes-refuses-stale-owner-path", lambda: rejects(lambda: inspect.inspect_classes(wrong_root), "binary owner differs from emitted relative path"))
    check("class-helper-positive-original-parameters-postcheck", lambda: inspect._class_helper(inspect.ClassFile(good_class), VIEWS + "$Api30"))
    wrong_inner_flags = good_class[:-10] + b"\x00\x19" + good_class[-8:]
    missing_nested_metadata = good_class[:-34] + b"\x00\x01" + good_class[-32:-24]
    check("class-helper-rejects-wrong-private-static-final-inner-flags", lambda: rejects(lambda: inspect._class_helper(inspect.ClassFile(wrong_inner_flags), VIEWS + "$Api30"), "helper InnerClasses flags altered"))
    check("class-helper-rejects-missing-nesting-metadata", lambda: rejects(lambda: inspect._class_helper(inspect.ClassFile(missing_nested_metadata), VIEWS + "$Api30"), "helper InnerClasses/NestHost metadata missing"))
    check("class-api29-helper-positive-four-setters-original-parameters", lambda: inspect._class_helper(inspect.ClassFile(api29_class()), VIEWS + "$Api29"))
    check("class-legacy-api30-positive-original-no-mutation-contract", lambda: inspect._class_helper(inspect.ClassFile(legacy_class()), "dev/mixer/android/NativeRenderer$Api30"))
    for name, kwargs in [
        ("changed-setter-order", {"order": ["setTextSelectHandle", "setTextCursorDrawable", "setTextSelectHandleLeft", "setTextSelectHandleRight"]}),
        ("wrong-record-parameter", {"record_local": 0}),
        ("wrong-receiver-parameter", {"receiver_local": 1}),
        ("wrong-mutation-parameter", {"mutation_local": 0}),
        ("cursor-in-place-of-handle", {"wrong_drawable": 2}),
        *[("missing-postcheck-" + str(n), {"omit_postcheck": n}) for n in range(4)],
    ]:
        data = api29_class(**kwargs)
        check("class-api29-helper-rejects-" + name, lambda data=data, name=name: rejects(lambda: inspect._class_helper(inspect.ClassFile(data), VIEWS + "$Api29"), name))
    for name, kwargs in [
        ("wrong-mutation-local", {"mutation_local": 0}),
        ("entry-authority-name-in-place-of-postcheck", {"mutation_name": "requireMutation"}),
        ("same-name-foreign-mutation-owner", {"mutation_owner": "review/Mutation"}),
        ("same-name-foreign-setter-owner", {"setter_owner": "review/View"}),
        ("wrong-native-descriptor", {"setter_desc": "(Ljava/lang/Object;)V"}),
        ("extra-instruction-before-postcheck", {"extra_after_setter": b"\x00"}),
    ]:
        data, _ = api30_class(**kwargs)
        check("class-helper-rejects-" + name, lambda data=data, name=name: rejects(lambda: inspect._class_helper(inspect.ClassFile(data), VIEWS + "$Api30"), name))
    check("class-rejects-bad-magic", lambda: rejects(lambda: inspect.ClassFile(b"BAD!" + good_class[4:]), "invalid ClassFile magic"))
    check("class-rejects-invalid-constant-pool-tag", lambda: rejects(lambda: inspect.ClassFile(good_class[:10] + b"\xff" + good_class[11:]), "invalid CP tag"))
    check("class-rejects-truncated-body", lambda: rejects(lambda: inspect.ClassFile(good_class[:-1]), "truncated class attributes"))
    check("class-rejects-trailing-data", lambda: rejects(lambda: inspect.ClassFile(good_class + b"unowned"), "extra trailing ClassFile data"))
    bad_code, _ = api30_class(truncate=True)
    check("class-rejects-truncated-instruction", lambda: rejects(lambda: inspect.ClassFile(bad_code), "partial invokevirtual operands"))
    branch_builder = ClassBuilder("review/Branch")
    branch_builder.method("run", "()V", b"\xa7\x00\x02\xb1", locals=0)
    check("class-rejects-branch-into-operand", lambda: rejects(lambda: inspect.ClassFile(branch_builder.build()), "goto target inside its own operand"))
    guard_target = "dev/mixer/android/NativeRenderer$Api30"
    guard_data, guard_key = guard_class()
    check("class-guard-positive-real-sdk-branch", lambda: inspect._class_guard(inspect.ClassFile(guard_data), guard_key, guard_target, 30))
    for name, kwargs in [
        ("jump-over-sdk-read", {"bypass_sdk_read": True}),
        ("same-name-foreign-sdk-field", {"sdk_owner": "review/Build$VERSION"}),
        ("methodref-in-place-of-fieldref", {"field_tag": False}),
    ]:
        data, key = guard_class(**kwargs)
        check("class-guard-rejects-" + name, lambda data=data, key=key, name=name: rejects(lambda: inspect._class_guard(inspect.ClassFile(data), key, guard_target, 30), name))

    dex_data, refs, definition_index = api30_dex()
    (scratch / "synthetic-api30.dex").write_bytes(dex_data)
    check("public-dex-refuses-incomplete-product-topology", lambda: rejects(lambda: inspect.inspect_dex(scratch / "synthetic-api30.dex"), "one helper DEX cannot stand in for product16 and three helpers"))

    def dex_positive():
        parsed = inspect.Dex(dex_data)
        assert definition_index in parsed.code
        assert len(parsed.methods) == 5
        method = parsed.code[definition_index]
        assert method["instructions"]
        return {"methods": parsed.methods, "fixture": "hand-encoded; not D8/product output"}

    check("dex-binary-positive-real-method-ids-code-item", dex_positive)
    check("dex-helper-positive-original-parameters-postcheck", lambda: inspect._dex_helper(inspect.Dex(dex_data), VIEWS + "$Api30"))
    api29_data, _, _ = api30_dex(api29=True)
    (scratch / "synthetic-api29.dex").write_bytes(api29_data)
    check("dex-api29-positive-sequential-allocation-setter-postcheck", lambda: inspect._dex_helper(inspect.Dex(api29_data), VIEWS + "$Api29"))
    for name, kwargs in [
        ("future-constructor-hoisting", {"hoist_allocations": True}),
        ("reused-handle-allocation", {"reuse_handle": True}),
        ("changed-setter-order", {"api29_order": [1, 0, 2, 3]}),
        ("wrong-record-register", {"record_reg": 4}),
        ("wrong-receiver-register", {"receiver_reg": 5}),
        ("wrong-mutation-register", {"api29_mutation_reg": 4}),
        *[("missing-postcheck-" + str(n), {"omit_api29_postcheck": n}) for n in range(4)],
    ]:
        corrupted, _, _ = api30_dex(api29=True, **kwargs)
        check("dex-api29-rejects-" + name, lambda corrupted=corrupted, name=name: rejects(lambda: inspect._dex_helper(inspect.Dex(corrupted), VIEWS + "$Api29"), name))
    for name, kwargs in [
        ("wrong-mutation-register", {"mutation_reg": 0}),
        ("postcheck-before-setter", {"setter_first": False}),
        ("entry-authority-name-in-place-of-postcheck", {"mutation_name": "requireMutation"}),
        ("same-name-foreign-mutation-owner", {"mutation_owner": "review/Mutation"}),
        ("extra-effect-before-postcheck", {"extra_words": [0x0000]}),
    ]:
        data, _, _ = api30_dex(**kwargs)
        check("dex-helper-rejects-" + name, lambda data=data, name=name: rejects(lambda: inspect._dex_helper(inspect.Dex(data), VIEWS + "$Api30"), name))
    check("dex-rejects-bad-magic", lambda: rejects(lambda: inspect.Dex(b"BAD!" + dex_data[4:]), "invalid DEX magic"))
    check("dex-rejects-truncated-file", lambda: rejects(lambda: inspect.Dex(dex_data[:-1]), "truncated DEX data/map"))
    check("dex-rejects-trailing-data", lambda: rejects(lambda: inspect.Dex(dex_data + b"unowned"), "DEX header file_size mismatch"))
    flipped = bytearray(dex_data)
    flipped[-1] ^= 1
    check("dex-rejects-integrity-corruption", lambda: rejects(lambda: inspect.Dex(bytes(flipped)), "unchanged DEX checksum/signature after changed payload"))
    bad_dex, _, _ = api30_dex(bad_method_index=True)
    check("dex-rejects-bad-invoke-method-index", lambda: rejects(lambda: inspect.Dex(bad_dex), "invoke references nonexistent method_id"))
    def dex_guard(data):
        parsed = inspect.Dex(data)
        indices = [i for i, row in enumerate(parsed.methods) if row[0] == "review/Guard" and row[1] == "run"]
        assert len(indices) == 1
        return inspect._dex_guard(parsed, indices[0], guard_target, 30)
    data, _, _ = api30_dex(with_guard=True, legacy=True)
    check("dex-guard-positive-real-sdk-distinct-registers", lambda: dex_guard(data))
    for name, kwargs in [
        ("sdk-threshold-register-alias", {"sdk_alias": True}),
        ("jump-over-sdk-read", {"bypass_sdk_read": True}),
    ]:
        corrupted, _, _ = api30_dex(with_guard=True, legacy=True, **kwargs)
        check("dex-guard-rejects-" + name, lambda corrupted=corrupted, name=name: rejects(lambda: dex_guard(corrupted), name))


if __name__ == "__main__":
    raise SystemExit(main())
