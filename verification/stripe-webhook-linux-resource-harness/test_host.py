#!/usr/bin/env python3
"""Executable controller negative controls; never Linux enforcement evidence."""
import array
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("resource_controller", HERE / "run.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class HostControls(unittest.TestCase):
    def setUp(self):
        self.sockets = []

    def tearDown(self):
        for sock in self.sockets:
            sock.close()

    def channel(self):
        # Isolated host parser/SCM_RIGHTS fixture. This packet transport is NOT
        # selected for the role and is never a runtime fallback for SEQPACKET.
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sockets.extend((a, b))
        return controller.Control(a, "a" * 32), b

    def test_selected_seqpacket_capability_or_explicit_skip(self):
        try:
            a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        except OSError as error:
            if error.errno in (43, 93, 94):
                self.skipTest("selected Unix SEQPACKET unavailable; host fixtures do not qualify it")
            raise
        a.close()
        b.close()

    def reject(self, callback, reason):
        with self.assertRaises(controller.Refusal) as e:
            callback()
        self.assertEqual(e.exception.reason, reason)

    def test_profile_exact_and_no_boolean_integer_confusion(self):
        p = controller.load(controller.CONTRACT / "profile.json")
        self.assertTrue(controller.same(p, copy.deepcopy(p)))
        for replacement in (True, 256.0, "256", None, 255, 257):
            mutated = copy.deepcopy(p)
            mutated["rlimits"]["nofileHard"] = replacement
            self.assertFalse(controller.same(mutated, p))
        mutated = copy.deepcopy(p)
        mutated["controller"]["unexpected"] = 1
        self.assertFalse(controller.same(mutated, p))

    def test_json_duplicate_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory(prefix="mixer-resource-host-control-", dir=HERE) as tmp:
            p = Path(tmp) / "input.json"
            for raw in ('{"schema":1,"schema":1}', '{"schema":NaN}', '{"schema":Infinity}'):
                p.write_text(raw)
                self.reject(lambda: controller.load(p), "profile_invalid")

    def test_control_ready_stop_stopped_exact(self):
        channel, peer = self.channel()
        peer.send(b"ready " + b"a" * 32 + b" 18080")
        channel.receive()
        self.assertEqual(channel.port, 18080)
        channel.send_stop()
        self.assertEqual(peer.recv(256), b"stop " + b"a" * 32)
        peer.send(b"stopped " + b"a" * 32 + b" completed")
        channel.receive()
        self.assertTrue(channel.stopped)

    def test_control_wrong_generation_closed_types_and_lengths(self):
        for raw in (b"ready " + b"b" * 32 + b" 1234", b"ready " + b"a" * 32 + b" 0",
                    b"ready " + b"a" * 32 + b" 65536", b"ready " + b"a" * 32 + b" -1",
                    b"ready " + b"a" * 32 + b" 1.0", b"unknown", b"\xff", b"x" * 257,
                    b"stopped " + b"a" * 32 + b" completed"):
            channel, peer = self.channel()
            peer.send(raw)
            self.reject(channel.receive, "output_schema")

    def test_replayed_control_rejected(self):
        channel, peer = self.channel()
        for _ in range(2):
            peer.send(b"ready " + b"a" * 32 + b" 18080")
        channel.receive()
        self.reject(channel.receive, "output_schema")

    def test_rights_rejected_and_received_descriptor_closed(self):
        channel, peer = self.channel()
        # Real SCM_RIGHTS transfer, not a string/syntax assertion.
        fd = os.open("/dev/null", os.O_RDONLY)
        try:
            before = set(os.listdir("/dev/fd" if os.path.isdir("/dev/fd") else "/proc/self/fd"))
            peer.sendmsg([b"ready " + b"a" * 32 + b" 18080"],
                         [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [fd]))])
            self.reject(channel.receive, "output_schema")
            after = set(os.listdir("/dev/fd" if os.path.isdir("/dev/fd") else "/proc/self/fd"))
            self.assertEqual(before, after)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(socket, "SCM_CREDENTIALS"), "Linux SCM_CREDENTIALS unavailable on this host")
    def test_credentials_are_unexpected_ancillary(self):
        channel, peer = self.channel()
        channel.sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        peer.send(b"ready " + b"a" * 32 + b" 18080")
        self.reject(channel.receive, "output_schema")

    def test_output_allowlist_reconstructs_and_fragments(self):
        audit = controller.OutputAudit()
        raw = b'{"schema":1,"event":"sample","beamTotalBytes":1,"heapWords":2,"referencedBinaryBytes":3,"mailboxLength":4,"processes":5}\n'
        audit.feed("stdout", raw[:30])
        audit.feed("stdout", raw[30:])
        audit.finish()
        self.assertEqual(audit.receipt()["allowedSchemaCount"], 1)
        self.assertEqual(audit.events[0]["mailboxLength"], 4)

    def test_unknown_raw_output_not_retained(self):
        for raw in (b"MIXER_BODY_SENTINEL\n", b'{"schema":1,"event":"sample","request":"MIXER_SIGNATURE_SENTINEL"}\n',
                    b"{bad json}\n", b'[]\n', b'{"schema":1,"event":"sample"}\n'):
            audit = controller.OutputAudit()
            self.reject(lambda: audit.feed("stderr", raw), "output_schema")
            self.assertEqual(audit.events, [])
            self.assertNotIn(raw.decode().strip(), json.dumps(audit.receipt()))
            self.assertEqual(audit.receipt()["rejectedOutputCount"], 1)

    def test_output_numeric_types_and_unknown_fields_rejected(self):
        base = {"schema": 1, "event": "sample", "beamTotalBytes": 1, "heapWords": 2,
                "referencedBinaryBytes": 3, "mailboxLength": 4, "processes": 5}
        for bad in (True, -1, 1.5, "1", None, 2**63):
            v = dict(base, mailboxLength=bad)
            self.reject(lambda: controller.OutputAudit().feed("stdout", json.dumps(v).encode() + b"\n"), "output_schema")
        v = dict(base, raw="MIXER_TRAILER_SENTINEL")
        self.reject(lambda: controller.OutputAudit().feed("stdout", json.dumps(v).encode() + b"\n"), "output_schema")
        duplicate = b'{"schema":1,"schema":1,"event":"sample","beamTotalBytes":1,"heapWords":2,"referencedBinaryBytes":3,"mailboxLength":4,"processes":5}\n'
        self.reject(lambda: controller.OutputAudit().feed("stdout", duplicate), "output_schema")

    def test_profile_rejection_precedes_role_process_creation(self):
        with tempfile.TemporaryDirectory(prefix="mixer-resource-host-control-", dir=HERE) as tmp:
            path = Path(tmp) / "profile.json"
            changed = controller.load(controller.CONTRACT / "profile.json")
            changed["cgroup"]["memory.max"] -= 1
            path.write_text(json.dumps(changed))
            with mock.patch.object(controller.subprocess, "Popen", side_effect=AssertionError("role must not launch")):
                self.reject(lambda: controller.profile(path), "profile_invalid")

    def test_every_profile_field_mutation_rejected(self):
        original = controller.load(controller.CONTRACT / "profile.json")
        count = 0
        def walk(value, path=()):
            yield path, value
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from walk(item, path + (key,))
            elif isinstance(value, list):
                for key, item in enumerate(value):
                    yield from walk(item, path + (key,))
        def changed(path, replacement):
            if not path:
                return replacement
            clone = copy.deepcopy(original)
            cursor = clone
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = replacement
            return clone
        for path, value in walk(original):
            candidates = [None]
            if isinstance(value, dict):
                candidates.append(dict(value, unexpected=1))
                for key in value:
                    deleted = dict(value)
                    del deleted[key]
                    candidates.append(deleted)
            elif isinstance(value, list):
                candidates.append(value + ["unexpected"])
            elif type(value) is int:
                candidates.extend((value - 1, value + 1, str(value), bool(value), float(value)))
            elif type(value) is bool:
                candidates.extend((int(value), not value))
            elif isinstance(value, str):
                candidates.extend(("", value + "-override", {"value": value}))
            for replacement in candidates:
                self.assertFalse(controller.same(changed(path, replacement), original), path)
                count += 1
        self.assertGreaterEqual(count, 650)

    def test_output_overflow_separate_pipes_and_unterminated(self):
        audit = controller.OutputAudit()
        self.reject(lambda: audit.feed("stdout", b"x" * 1048577), "output_overflow")
        self.assertEqual(audit.receipt()["stderrBytes"], 0)
        self.assertFalse(audit.buffers["stdout"])
        audit = controller.OutputAudit()
        audit.feed("stdout", b"{")
        self.reject(audit.finish, "output_schema")

    def test_receipt_closed_shape_and_unavailable_not_pass(self):
        row = controller.receipt("R01", controller.linux_capabilities())
        p = controller.load(controller.CONTRACT / "profile.json")
        self.assertEqual(set(row), set(p["caseReceiptFields"]))
        self.assertEqual(row["status"], "unavailable")
        self.assertFalse(row["cleanup"]["roleStarted"])

    def test_relative_paths_fail_closed(self):
        for p in ("../secret", "/etc/passwd", "a/../b", "a//b", "./a", ""):
            self.assertFalse(controller.safe_relative(p))
        self.assertTrue(controller.safe_relative("usr/lib/libssl.so.3"))

    def test_counter_parser_exact(self):
        self.assertEqual(controller.counter_file("oom_kill 2\nhigh 10"), {"oom_kill": 2, "high": 10})
        self.reject(lambda: controller.counter_file("oom_kill nope"), "cgroup_readback")


if __name__ == "__main__":
    unittest.main(verbosity=2)
