"""Bounded hostile archive and link graph controls; no host extraction."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

import inspect_packages as candidate


def tar_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for name, kind, data in entries:
            member = tarfile.TarInfo(name)
            member.mode = 0o755 if kind == "directory" else 0o644
            member.type = {"file": tarfile.REGTYPE, "directory": tarfile.DIRTYPE,
                           "symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE, "fifo": tarfile.FIFOTYPE}[kind]
            if kind == "file":
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            else:
                if kind in ("symlink", "hardlink"):
                    member.linkname = data
                archive.addfile(member)
    return output.getvalue()


def ar_bytes(entries):
    raw = bytearray(b"!<arch>\n")
    for name, data in entries:
        header = f"{name+'/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n".encode()
        assert len(header) == 60
        raw.extend(header+data+(b"\n" if len(data)%2 else b""))
    return bytes(raw)


def package_bytes(data_entries, extra_control=()):
    control = b"Package: fixture\nVersion: 1~ubuntu1\nArchitecture: arm64\nInstalled-Size: 1\n"
    return ar_bytes([("debian-binary", b"2.0\n"),
        ("control.tar.gz", gzip.compress(tar_bytes([("./control", "file", control), *extra_control]))),
        ("data.tar.gz", gzip.compress(tar_bytes(data_entries)))])


class InspectionControls(unittest.TestCase):
    def setUp(self):
        self.package = {"name": "fixture", "version": "1~ubuntu1", "architecture": "arm64", "installedSizeKiB": 1}
        self.budget = {"expanded": 0, "members": 0, "captured": 0, "deadline": time.monotonic()+10}

    def inspect(self, raw):
        graph, controls, notices = {}, [], []
        candidate.inspect_one(self.package, raw, self.budget, graph, controls, notices)
        return graph, controls, notices

    def test_data_only_control_script_never_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory)/"must-not-exist"
            raw = package_bytes([("./usr", "directory", ""), ("./usr/file", "file", b"data")],
                                [("./postinst", "file", ("#!/bin/sh\ntouch "+str(sentinel)).encode())])
            graph, controls, _ = self.inspect(raw)
            self.assertEqual(graph["usr/file"]["sha256"], hashlib.sha256(b"data").hexdigest())
            self.assertTrue(any(x["path"] == "postinst" for x in controls))
            self.assertFalse(sentinel.exists())

    def test_traversal_absolute_and_ambiguous_paths_refuse(self):
        for path in ("../x", "/usr/x", "usr/../x", "usr//x", "usr/x\ny", "usr/x\\y", "x"*4097):
            with self.assertRaises(ValueError):
                candidate.member_path(path)

    def test_symlink_hardlink_escape_and_cycles_refuse(self):
        for hard in (True, False):
            for target in ("../../escape", "/etc/passwd"):
                with self.assertRaises(ValueError):
                    candidate.target_path("usr/x", target, hard)
        graph = {"usr/a": {"path": "usr/a", "type": "symlink", "target": "b"},
                 "usr/b": {"path": "usr/b", "type": "symlink", "target": "a"}}
        with self.assertRaises(ValueError):
            candidate.validate_graph(graph)

    def test_alias_ancestor_and_cross_package_collision_refuse(self):
        graph = {"usr/link": {"path": "usr/link", "type": "symlink", "target": "real"},
                 "usr/link/file": {"path": "usr/link/file", "type": "file"}}
        with self.assertRaises(ValueError):
            candidate.validate_graph(graph)
        graph = {}
        base = {"path": "usr/file", "type": "file", "mode": 0o644, "bytes": 1, "sha256": "a", "packages": ["a"]}
        candidate.insert(graph, base)
        with self.assertRaises(ValueError):
            candidate.insert(graph, dict(base, sha256="b", packages=["b"]))

    def test_valid_relative_links_and_identical_directory_collisions(self):
        graph = {"usr/lib/file": {"path": "usr/lib/file", "type": "file", "bytes": 1, "sha256": "a"},
                 "usr/bin/link": {"path": "usr/bin/link", "type": "symlink", "target": "../lib/file"},
                 "usr/lib/hard": {"path": "usr/lib/hard", "type": "hardlink", "target": "./usr/lib/file"}}
        self.assertEqual(candidate.validate_graph(graph), [])
        self.assertEqual(graph["usr/lib/hard"]["sha256"], "a")
        graph = {}
        item = {"path": "usr", "type": "directory", "mode": 0o755, "bytes": 0, "packages": ["a"]}
        candidate.insert(graph, item)
        candidate.insert(graph, dict(item, packages=["b"]))
        self.assertEqual(graph["usr"]["packages"], ["a", "b"])

    def test_inside_prefix_missing_link_target_is_explicit(self):
        graph = {"usr/lib/link": {"path": "usr/lib/link", "type": "symlink", "target": "base-runtime.so"}}
        self.assertEqual(candidate.validate_graph(graph), [{"path": "usr/lib/link", "targetInsidePrefix": "usr/lib/base-runtime.so"}])

    def test_special_node_and_duplicate_members_refuse(self):
        for entries in ([("./fifo", "fifo", "")], [("./x", "file", b"x"), ("./x", "file", b"x")]):
            with self.assertRaises(ValueError):
                self.inspect(package_bytes(entries))

    def test_ar_magic_truncation_ambiguity_and_malformed_header_refuse(self):
        raw = package_bytes([])
        for bad in (b"invalid", raw[:-1], raw[:66]+b"x"+raw[67:], ar_bytes([("debian-binary", b"2.0\n")])):
            with self.assertRaises((ValueError, UnicodeError)):
                candidate.ar_members(bad)

    def test_compression_bomb_expanded_member_and_capture_limits(self):
        with patch.object(candidate, "LIMIT", 1024):
            reader = candidate.decompressed("data.tar.gz", gzip.compress(b"x"*4096), self.budget)
            with self.assertRaises(ValueError):
                reader.read(4096)
        self.budget["expanded"] = 0
        with self.assertRaises(ValueError):
            self.inspect(package_bytes([], [("postinst", "file", b"x"*1048577)]))

    def test_member_count_and_deadline_limits(self):
        self.budget["members"] = 100000
        with self.assertRaises(ValueError):
            self.inspect(package_bytes([]))
        self.budget["deadline"] = time.monotonic()-1
        with self.assertRaises(ValueError):
            candidate.BoundedReader(io.BytesIO(b"x"), self.budget).read(1)

    def test_control_aggregate_and_long_header_rejected_before_body(self):
        self.budget["captured"] = 16777216
        with self.assertRaises(ValueError):
            self.inspect(package_bytes([]))
        member = tarfile.TarInfo("long")
        member.type = tarfile.GNUTYPE_LONGNAME
        member.size = 4098
        with self.assertRaises(ValueError):
            candidate.BoundedTarInfo.frombuf(member.tobuf(format=tarfile.GNU_FORMAT), "utf-8", "strict")

    def test_exclusive_metadata_output_and_export_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"manifest.json"
            candidate.save(path, {"value": 1})
            with self.assertRaises(FileExistsError):
                candidate.save(path, {"value": 2})
            with self.assertRaises(ValueError):
                candidate.save(Path(directory)/"too-big.json", {"x": "too large"}, maximum=2)


if __name__ == "__main__":
    unittest.main()
