"""Host-only controls for C6 data/prelaunch/ownership boundaries. No Docker calls."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
import unittest
from unittest import mock

import prepare as p
import qualification as q
import run_qualification as run


def archive(records, tail=b""):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w", format=tarfile.GNU_FORMAT) as writer:
        for name, body, kind in records:
            member = tarfile.TarInfo(name)
            member.type, member.mode = kind, 0o644
            if kind == tarfile.REGTYPE:
                member.size = len(body)
                writer.addfile(member, io.BytesIO(body))
            else:
                member.linkname = body.decode()
                writer.addfile(member)
    return data.getvalue()+tail


def elf_image(needed="libc.so.6", definition="GLIBC_2.17", *, version_need=True):
    data = bytearray(2048)
    data[:16] = b"\x7fELF\x02\x01\x01"+bytes(9)
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, 3, 183, 1, 0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 4, 0, 0x10000, 0, len(data), len(data), 4096)
    strings = b"\0"+needed.encode()+b"\0"+definition.encode()+b"\0"
    data[512:512+len(strings)] = strings
    tags = [(5, 0x10200), (10, len(strings)), (1, 1), (14, 1), (0x6ffffffc, 0x10300), (0x6ffffffd, 1)]
    if version_need:
        tags.extend([(0x6ffffffe, 0x10400), (0x6fffffff, 1)])
        struct.pack_into("<HHIII", data, 1024, 1, 1, 1, 16, 0)
        struct.pack_into("<IHHII", data, 1040, 0, 0, 1, len(needed)+2, 0)
    tags.append((0, 0))
    struct.pack_into("<IIQQQQQQ", data, 120, 2, 4, 256, 0x10100, 0, len(tags)*16, len(tags)*16, 8)
    for i, pair in enumerate(tags):
        struct.pack_into("<qQ", data, 256+i*16, *pair)
    struct.pack_into("<HHHHIII", data, 768, 1, 0, 2, 1, 0, 20, 0)
    struct.pack_into("<II", data, 788, len(needed)+2, 0)
    return data


class ELFControls(unittest.TestCase):
    def test_reads_needed_and_version_metadata(self):
        value = p.elf(elf_image())
        self.assertEqual(value["needed"], ["libc.so.6"])
        self.assertEqual(value["versionNeeds"], {"libc.so.6": ["GLIBC_2.17"]})
        self.assertEqual(value["versionDefinitions"], ["GLIBC_2.17"])

    def test_rejects_other_machine_and_endian(self):
        for offset, replacement in ((18, b"\x3e\x00"), (5, b"\x02")):
            data = elf_image()
            data[offset:offset+len(replacement)] = replacement
            with self.assertRaises(ValueError):
                p.elf(data)

    def test_rejects_truncated_program_segment(self):
        with self.assertRaises(ValueError):
            p.elf(elf_image()[:700])

    def test_rejects_oversized_program_table(self):
        data = elf_image()
        struct.pack_into("<H", data, 56, 129)
        with self.assertRaises(ValueError):
            p.elf(data)

    def test_rejects_dependency_paths(self):
        with self.assertRaises(ValueError):
            p.elf(elf_image("../../libc.so.6"))

    def test_rejects_unmapped_dynamic_string_address(self):
        data = elf_image()
        struct.pack_into("<Q", data, 264, 0x999999)
        with self.assertRaises(ValueError):
            p.elf(data)

    def test_rejects_unterminated_dynamic_string(self):
        data = elf_image()
        data[512:512+31] = b"x"*31
        with self.assertRaises(ValueError):
            p.elf(data)

    def test_rejects_version_definition_nontermination(self):
        data = elf_image()
        struct.pack_into("<I", data, 784, 20)
        with self.assertRaises(ValueError):
            p.elf(data)

    def test_rejects_version_need_nontermination(self):
        data = elf_image()
        struct.pack_into("<I", data, 1036, 16)
        with self.assertRaises(ValueError):
            p.elf(data)


class TarControls(unittest.TestCase):
    def test_one_regular_file_is_returned_as_data(self):
        self.assertEqual(q.one_file_tar(archive([("library", b"bytes", tarfile.REGTYPE)]), "library"), b"bytes")

    def test_rejects_duplicate_member(self):
        with self.assertRaises(ValueError):
            q.one_file_tar(archive([("library", b"1", tarfile.REGTYPE)]*2), "library")

    def test_rejects_special_link_directory_and_wrong_path(self):
        for typ in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE, tarfile.FIFOTYPE):
            with self.subTest(typ=typ), self.assertRaises(ValueError):
                q.one_file_tar(archive([("library", b"target", typ)]), "library")
        with self.assertRaises(ValueError):
            q.one_file_tar(archive([("../library", b"1", tarfile.REGTYPE)]), "library")

    def test_rejects_member_byte_limit(self):
        with self.assertRaises(ValueError):
            q.one_file_tar(archive([("library", b"123", tarfile.REGTYPE)]), "library", maximum=2)

    def test_rejects_nonzero_tail(self):
        with self.assertRaises(ValueError):
            q.one_file_tar(archive([("library", b"1", tarfile.REGTYPE)], b"hidden"), "library")

    def test_header_original_hashes_and_duplicate_members(self):
        path = "/usr/local/lib/erlang/usr/include/erl_nif.h"
        expected = {path: hashlib.sha256(b"header").hexdigest()}
        raw = archive([("./erl_nif.h", b"header", tarfile.REGTYPE)])
        self.assertEqual(run.inspect_headers(raw, expected), expected)
        with self.assertRaises(ValueError):
            run.inspect_headers(archive([("./erl_nif.h", b"header", tarfile.REGTYPE)]*2), expected)

    def test_header_missing_or_changed_pin(self):
        for expected in ({"/usr/local/lib/erlang/usr/include/absent.h": "0"*64},
                         {"/usr/local/lib/erlang/usr/include/erl_nif.h": "0"*64}):
            with self.assertRaises(ValueError):
                run.inspect_headers(archive([("erl_nif.h", b"header", tarfile.REGTYPE)]), expected)


def node(needed=(), definitions=(), requirements=None, soname=None):
    return {"interpreter": None, "needed": list(needed), "rpath": None, "runpath": None,
            "versionNeeds": requirements or {}, "versionDefinitions": list(definitions), "soname": soname}


class ClosureControls(unittest.TestCase):
    def report(self):
        return {"compilerClosure": {"requiredBaseSonames": ["libc.so.6"], "payloadClosure": {
            "tool": node(["libc.so.6"], requirements={"libc.so.6": ["GLIBC_2.17"]})}}}

    def test_missing_base_is_a_requirement(self):
        self.assertEqual(q.required_base(self.report(), {}), ["libc.so.6", "libgcc_s.so.1"])

    def test_transitive_missing_dependency_is_retained(self):
        base = {"libc.so.6": node(["ld-linux-aarch64.so.1"])}
        self.assertEqual(q.required_base(self.report(), base), ["ld-linux-aarch64.so.1", "libgcc_s.so.1"])

    def test_symbol_versions_must_have_actual_provider_definitions(self):
        base = {"libc.so.6": node(), "libgcc_s.so.1": node()}
        with self.assertRaisesRegex(ValueError, "symbol versions"):
            q.verify_complete_base(self.report(), base)
        base["libc.so.6"]["versionDefinitions"] = ["GLIBC_2.17"]
        self.assertTrue(q.verify_complete_base(self.report(), base))

    def test_rejects_unselected_base_and_library_search_override(self):
        with self.assertRaises(ValueError):
            q.required_base(self.report(), {"unselected.so": node()})
        bad = node()
        bad["runpath"] = "/host"
        with self.assertRaises(ValueError):
            q.required_base(self.report(), {"libc.so.6": bad})

    def test_base_file_and_path_limits(self):
        for name in ("../libc.so", "/libc.so", ".", "a"*129, "bad\nname"):
            with self.assertRaises(ValueError):
                q.base_path(name)
        report = self.report()
        report["compilerClosure"]["requiredBaseSonames"] = ["lib"+str(i)+".so" for i in range(17)]
        with self.assertRaises(ValueError):
            q.required_base(report, {})

    def test_symlink_cycle_and_escape_are_rejected(self):
        for graph in ({"a": {"type": "symlink", "target": "a"}}, {"a": {"type": "symlink", "target": "../b"}}):
            with self.assertRaises(ValueError):
                p.resolve("a", graph)

    def test_symlink_ancestor_alias_resolves_before_missing_classification(self):
        graph = {"doc/gcc": {"type": "symlink", "target": "gcc-base"},
                 "doc/alias": {"type": "symlink", "target": "gcc/README"},
                 "doc/gcc-base/README": {"type": "file"}}
        self.assertEqual(p.resolve("doc/alias", graph), "doc/gcc-base/README")


def selection():
    return {"schema": 1, "accountableReviewer": "/root", "phase": "C6",
            "status": "selected-bounded-private-compiler-qualification", "proposalSHA256": "a"*64,
            "sourceDigest": "b"*64, "requiredImage": p.IMAGE, "requiredPlatformChild": p.CHILD,
            "assemblySealSHA256": p.SEAL_SHA, "payloadSHA256": p.PAYLOAD_SHA, "packageLockSHA256": p.LOCK_SHA,
            "bounds": copy.deepcopy(q.BOUNDS), "compilerPrefix": p.PREFIX, "compilerExecutionSelected": True,
            "resourceRuntimeSelected": False, "helperExecutionSelected": False, "NIFLoadSelected": False,
            "BEAMExecutionSelected": False}


class AuthorityControls(unittest.TestCase):
    def test_exact_selection_is_accepted(self):
        self.assertTrue(q.validate_selection(selection(), {"bounds": q.BOUNDS}, "a"*64, "b"*64))

    def test_rejects_source_pin_and_scope_drift(self):
        for field, value in (("sourceDigest", "c"*64), ("accountableReviewer", "/other"),
                             ("payloadSHA256", "0"*64), ("compilerExecutionSelected", False),
                             ("helperExecutionSelected", True), ("resourceRuntimeSelected", True),
                             ("BEAMExecutionSelected", True), ("NIFLoadSelected", True)):
            candidate = selection()
            candidate[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                q.validate_selection(candidate, {"bounds": q.BOUNDS}, "a"*64, "b"*64)

    def test_rejects_budget_increase(self):
        candidate = selection()
        candidate["bounds"]["wallSeconds"] += 1
        with self.assertRaises(ValueError):
            q.validate_selection(candidate, {"bounds": q.BOUNDS}, "a"*64, "b"*64)

    def test_unselected_adapter_launches_no_command(self):
        with mock.patch.object(run.subprocess, "Popen", side_effect=AssertionError("unexpected process")) as launch:
            with self.assertRaises((ValueError, FileNotFoundError)):
                run.authority("0"*64)
            run.main([])
            launch.assert_not_called()

    def test_one_owned_mount_and_unchanged_total_tmpfs(self):
        argv = q.container_argv("mixer-private-compiler-qualification-0123456789ab", "0"*32, "/tmp/owned")
        self.assertEqual(argv.count("--mount"), 1)
        self.assertIn("--pull=never", argv)
        self.assertIn("/tmp:rw,noexec,nosuid,nodev,size=268435456,mode=1777", argv)
        self.assertEqual(q.BOUNDS["privateTmpfsBytes"], q.BOUNDS["compilerExecutableTmpfsBytes"]+q.BOUNDS["noexecTemporaryTmpfsBytes"])

    def test_cleanup_ownership_is_exact(self):
        value = {"Name": "/owned", "Id": "id", "Config": {"Image": p.IMAGE, "Labels": {run.LABEL: "token"}}}
        self.assertTrue(run.owned(value, "owned", "token", "id"))
        for name, token, identifier in (("other", "token", "id"), ("owned", "bad", "id"), ("owned", "token", "other")):
            self.assertFalse(run.owned(value, name, token, identifier))

    def test_create_side_effect_survives_failed_client_observation(self):
        # Simulate daemon creation followed by a client timeout before ID assignment.
        name, token, identifier = "owned", "token", None
        daemon = {}
        def failed_create():
            daemon[name] = {"Name": "/owned", "Id": "a"*64, "Image": p.IMAGE.split("@")[1],
                            "ImageManifestDescriptor": {"digest": p.CHILD},
                            "Config": {"Image": p.IMAGE, "Labels": {run.LABEL: token}}}
            raise TimeoutError("create response not observed")
        with self.assertRaises(TimeoutError):
            identifier = failed_create()
        self.assertIsNone(identifier)
        recovered = run.cleanup_resolution(json.dumps([daemon[name]]).encode(), 0, b"", name, token, identifier)
        self.assertEqual(recovered, "a"*64)
        del daemon[name]  # Represents only the exact recovered owned ID being removed.
        self.assertIsNone(run.cleanup_resolution(b"[]\n", 1, b"Error: No such object: owned\n", name, token, recovered))

    def test_cleanup_refuses_foreign_identity_and_ambiguous_failure(self):
        fixture = {"Name": "/owned", "Id": "a"*64, "Image": p.IMAGE.split("@")[1],
                   "ImageManifestDescriptor": {"digest": p.CHILD},
                   "Config": {"Image": p.IMAGE, "Labels": {run.LABEL: "token"}}}
        for mutate in (lambda x: x["Config"]["Labels"].update({run.LABEL: "foreign"}),
                       lambda x: x.update(Name="/foreign"), lambda x: x.update(Image="sha256:foreign"),
                       lambda x: x["ImageManifestDescriptor"].update(digest="sha256:foreign")):
            candidate = copy.deepcopy(fixture)
            mutate(candidate)
            with self.assertRaises(ValueError):
                run.cleanup_resolution(json.dumps([candidate]).encode(), 0, b"", "owned", "token")
        with self.assertRaises(ValueError):
            run.cleanup_resolution(b"[]\n", 1, b"Cannot connect to Docker daemon\n", "owned", "token")

    def test_image_child_and_platform_are_pinned(self):
        original = json.loads((p.ROOT/p.C5/"attempt/01-image-inspect.stdout").read_text())[0]
        run.checked_image(original)
        for mutate in (lambda x: x.update(Id="sha256:other"), lambda x: x["Descriptor"]["platform"].update(architecture="amd64")):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            with self.assertRaises(ValueError):
                run.checked_image(candidate)

    def test_container_policy_rejects_privilege_mount_or_tmpfs_drift(self):
        fixture = json.loads((p.ROOT/p.C5/"attempt/04-policy-before.stdout").read_text())[0]
        fixture["Name"], fixture["Id"] = "/owned", "identity"
        fixture["Config"]["Labels"] = {run.LABEL: "token"}
        fixture["HostConfig"]["Tmpfs"] = {"/tmp": "rw,noexec,nosuid,nodev,size=268435456,mode=1777",
                                          "/opt/mixer-compiler": "rw,exec,nosuid,nodev,size=268435456,mode=1777"}
        fixture["Mounts"][0]["Source"] = "/tmp/owned"
        run.checked_policy(fixture, "owned", "token", Path("/tmp/owned"), "identity")
        for mutate in (lambda x: x["HostConfig"].update(Privileged=True),
                       lambda x: x["HostConfig"].update(NetworkMode="bridge"),
                       lambda x: x["Mounts"][0].update(RW=True),
                       lambda x: x["HostConfig"]["Tmpfs"].update({"/tmp": "rw,exec,size=268435456"}),
                       lambda x: x["HostConfig"].update(PidsLimit=256)):
            candidate = copy.deepcopy(fixture)
            mutate(candidate)
            with self.assertRaises(ValueError):
                run.checked_policy(candidate, "owned", "token", Path("/tmp/owned"), "identity")


if __name__ == "__main__":
    unittest.main()
