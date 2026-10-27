import copy
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import prototype as p
import schema as s

ROOT = Path(__file__).resolve().parent
SCRATCH = ROOT / "owned-scratch"
SCRATCH.mkdir(exist_ok=True)
REPORTS = []


def snapshot_fixture(source=b"s" * 128):
    def buffer(items):
        return dict(capacity=len(items), charged=len(items) * 32, category="Metadata", items=items)
    metadata = {
        "signatures": buffer([dict(first=0, count=1, result="I32")]),
        "parameters": buffer(["I32"]),
        "imports": buffer([dict(module=[0, 4], name=[4, 4], type_index=0) for _ in range(34)]),
        "functions": buffer([dict(body=[8, 16], type_index=0)]),
        "globals": buffer([dict(type="I32", mutable=0, initializer=[24, 2])]),
        "exports": buffer([dict(name=[26, 4], kind=0, index=34)]),
        "data": buffer([dict(payload=[30, 4], destination=0, count=4)]),
        "elements": buffer([dict(payload=[34, 1], destination=0, count=1)]),
        "memory": [1, 768], "table": [1, 65536],
        "declarations": dict(memory_maximum=None, table_maximum=65536, memory_offset=35, table_offset=36),
        "instructions": 1,
    }
    observations = dict(zip(s.OBSERVATIONS, (1, 1, 34, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None, 768, 1, 65536)))
    return dict(schema=1, validator_revision=1, decoder_revision=1, policy="swift-reactor-experiment-v1", source=dict(bytes=len(source), sha256=hashlib.sha256(source).hexdigest()), metadata=metadata, resolved_imports=list(s.IMPORTS), usage={k: 0 for k in s.USAGE}, observations=observations, provenance=dict(schema=1, session_sha256="11" * 32, owner_ordinal=1, candidate_manifest_sha256="22" * 32, validator_binary_sha256="33" * 32, exporter_source_sha256="44" * 32, build_receipt_sha256="55" * 32, validation_budget=dict(source_bytes=67108864, metadata_bytes=16777216, scratch_bytes=1048576, work_credits=512000000, deadline_ms=120000), validation_terminal="success"))


def header(claims, source_bytes=128):
    words = [1, 512, 32, 80000, source_bytes, 1, 1, 1, 1, 137264, 16777216, 8388608, 0, 0, 0]
    return b"MIXPRF01" + struct.pack("<15Q", *words) + b"".join(claims) + bytes(128)


def fixture(directory):
    paths, sizes, claims = {}, {}, []
    values = [s.source_manifest(dict(schema=1, role="baseline", members=[dict(path="vm/a.rs", bytes=1, sha256="66" * 32, role="distribution")])), s.source_manifest(dict(schema=1, role="candidate", members=[dict(path="vm/b.rs", bytes=1, sha256="77" * 32, role="distribution")])), b"s" * 128, b"synthetic event schema - no real writer provenance\n", b"synthetic non-executable adapter bytes\n", b"synthetic layout receipt - no compiler provenance\n", s.snapshot(snapshot_fixture())]
    for name, data in zip(p.NAMES, values):
        path = directory / name
        path.write_bytes(data)
        paths[name], sizes[name] = path, len(data)
        claims.append(hashlib.sha256(data).digest())
    path = directory / p.NAMES[7]
    h = hashlib.sha256()
    with path.open("xb") as file:
        for _ in range(625):
            chunk = bytes([93]) * 4096
            file.write(chunk)
            h.update(chunk)
    paths[p.NAMES[7]], sizes[p.NAMES[7]] = path, p.BODY
    claims.append(h.digest())
    return paths, sizes, header(claims), claims


class OwnedTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="control-", dir=SCRATCH)
        self.dir = Path(self.temp.name)
        self.assertEqual(p.OPEN_FDS, set())

    def tearDown(self):
        self.assertEqual(p.OPEN_FDS, set(), "all owned retained fds closed")
        self.assertEqual(p.STDIO_FDS, set(), "owned child stdio contexts closed")
        self.assertEqual(p.QUARANTINES, [], "no child quarantine on executed controls")
        self.temp.cleanup()

    def refusal(self, function, code=None):
        with self.assertRaises(p.Refusal) as caught:
            function()
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        return caught.exception


class SchemaControls(unittest.TestCase):
    def test_independent_literal_canonical_bytes_and_frozen_snapshot_digest(self):
        self.assertEqual(s.canonical(b"MIXTST01", {"z":2,"a":[None,0,"I32"]}), b'MIXTST01\n{"a":[null,0,"I32"],"z":2}\n')
        self.assertEqual(hashlib.sha256(s.snapshot(snapshot_fixture())).hexdigest(), "af8fc4a404a34155bc3717637142f344c9a37d109a5306694e4798d39fc9fb9f")

    def test_snapshot_closed_complete_roundtrip(self):
        value = snapshot_fixture()
        raw = s.snapshot(value)
        self.assertEqual(s.snapshot(s.decode(b"MIXSNB01", raw)), raw)
        REPORTS.append({"snapshot_fixture_sha256": hashlib.sha256(raw).hexdigest(), "snapshot_fixture_bytes": len(raw), "authority": False})

    def test_snapshot_every_leaf_is_in_digest_preimage(self):
        value = snapshot_fixture()
        raw = s.snapshot(value)
        leaves = []
        def scan(v, path):
            if type(v) is dict:
                for k, item in v.items():
                    scan(item, path + [k])
            elif type(v) is list:
                for k, item in enumerate(v):
                    scan(item, path + [k])
            else:
                leaves.append((path, v))
        scan(value, [])
        for path, leaf in leaves:
            with self.subTest(path=path):
                changed = copy.deepcopy(value)
                parent = changed
                for k in path[:-1]:
                    parent = parent[k]
                parent[path[-1]] = leaf + 1 if type(leaf) is int else (0 if leaf is None else leaf + "x")
                # Mutation tests the canonical preimage inclusion, not validity.
                self.assertNotEqual(s.digest_bytes(raw), s.digest_bytes(s.canonical(b"MIXSNB01", changed)))
        REPORTS.append({"snapshot_leaf_mutations": len(leaves), "scope": "preimage inclusion; mutated objects need not be valid"})

    def test_snapshot_missing_private_fields_refuse(self):
        for path in (("metadata", "declarations"), ("usage", "elapsed_micros"), ("observations", "table_declared_maximum"), ("metadata", "functions", "capacity"), ("provenance", "build_receipt_sha256")):
            with self.subTest(path=path):
                value = snapshot_fixture()
                obj = value
                for k in path[:-1]:
                    obj = obj[k]
                del obj[path[-1]]
                with self.assertRaises(s.SchemaError):
                    s.snapshot(value)

    def test_snapshot_wrong_span_import_count_and_bool_refuse(self):
        for mutate in (lambda v: v["metadata"]["functions"]["items"][0].update(body=[127, 2]), lambda v: v["resolved_imports"].pop(), lambda v: v["metadata"]["globals"]["items"][0].update(mutable=True), lambda v: v["observations"].update(defined_functions=2), lambda v: v["provenance"].update(validation_terminal="failure")):
            value = snapshot_fixture()
            mutate(value)
            with self.assertRaises(s.SchemaError):
                s.snapshot(value)

    def test_canonical_encoding_duplicate_float_trailing_version_refuse(self):
        for data in (b'MIXSNB01\n{"a":1,"a":2}\n', b'MIXSNB01\n{"a":1.5}\n', b'MIXSNB01\n{"a":true}\n', b'MIXSNB01\n{ "a":1}\n', b'MIXSNB01\n{"a":1}\n\n', b'MIXSNB02\n{}\n'):
            with self.subTest(data=data), self.assertRaises(s.SchemaError):
                s.decode(b"MIXSNB01", data)

    def test_manifest_order_paths_and_role_refuse(self):
        base = dict(schema=1, role="candidate", members=[dict(path="vm/a.rs", bytes=1, sha256="00" * 32, role="distribution")])
        for bad in ("/a", "../a", "a//b", "a/./b", "a\\b"):
            value = copy.deepcopy(base)
            value["members"][0]["path"] = bad
            with self.assertRaises(s.SchemaError):
                s.source_manifest(value)
        value = copy.deepcopy(base)
        value["members"] *= 2
        with self.assertRaises(s.SchemaError):
            s.source_manifest(value)

    def test_event_schema_and_layout_are_versioned_closed_preimages(self):
        event = dict(schema=1, event_magic="SYNTEV01", record_bytes=16, byte_order="little", fields=[dict(name="magic", offset=0, bytes=8, kind="magic"), dict(name="phase", offset=8, bytes=8, kind="enum")], enums=[dict(field="phase", values=[dict(value=1, name="fixture")])], writer_source=dict(path="fixture.rs", sha256="11" * 32))
        raw = s.event_schema(event)
        self.assertEqual(s.event_schema(s.decode(b"MIXEVS01", raw)), raw)
        event["fields"][1]["offset"] = 9
        with self.assertRaises(s.SchemaError):
            s.event_schema(event)
        layout = dict(schema=1, target="synthetic-host", configuration="synthetic", rustc_sha256="11" * 32, rustc_vv_sha256="22" * 32, candidate_manifest_sha256="33" * 32, adapter_binary_sha256="44" * 32, type_inventory_sha256="55" * 32, types=[dict(id=1, name="SyntheticOnly", bytes=16, alignment=8)], totals=dict(foundation=0, constructor_union=0, prepared_bound=0, headroom=0, row_union=0, cleanup_union=0))
        raw = s.layout_receipt(layout)
        self.assertEqual(s.layout_receipt(s.decode(b"MIXLAY01", raw)), raw)
        layout["types"][0]["alignment"] = 3
        with self.assertRaises(s.SchemaError):
            s.layout_receipt(layout)


class IOControls(OwnedTest):
    def test_read_and_write_last_permitted_success(self):
        class Last:
            def __init__(self): self.n = 0
            def read(self, _fd, view):
                self.n += 1
                if self.n < 32: raise InterruptedError()
                return len(view)
            write = read
        for writing in (False, True):
            counts = p.IOCount()
            p.transfer(Last(), -1, memoryview(bytearray(17)), counts, writing)
            self.assertEqual(counts.write_calls if writing else counts.read_calls, 32)
            self.assertEqual(counts.write_requested if writing else counts.read_requested, 32 * 17)

    def test_read_write_zero_error_overreport_exhaustion(self):
        for writing in (False, True):
            for behavior in ("zero", "error", "overreport", "interrupt"):
                with self.subTest(writing=writing, behavior=behavior):
                    class Fault:
                        def read(self, _fd, view):
                            if behavior == "error": raise OSError("synthetic")
                            if behavior == "interrupt": raise InterruptedError()
                            return 0 if behavior == "zero" else len(view) + 1
                        write = read
                    counts = p.IOCount()
                    self.refusal(lambda: p.transfer(Fault(), -1, memoryview(bytearray(17)), counts, writing))
                    self.assertEqual(counts.write_calls if writing else counts.read_calls, 32 if behavior == "interrupt" else 1)
                    self.assertEqual(counts.write_acknowledged if writing else counts.read_acknowledged, 0)

    def test_eof_last_permitted_success_extra_and_exhaustion(self):
        for behavior in ("last", "extra", "interrupt", "overreport", "error"):
            class EOF:
                def __init__(self): self.n = 0
                def read(self, _fd, view):
                    self.n += 1
                    if behavior == "error": raise OSError("synthetic")
                    if behavior == "interrupt" or behavior == "last" and self.n < 32: raise InterruptedError()
                    return 0 if behavior == "last" else (2 if behavior == "overreport" else 1)
            counts = p.IOCount()
            if behavior == "last":
                p.eof(EOF(), -1, bytearray(4096), counts)
                self.assertEqual(counts.read_calls, 32)
            else:
                self.refusal(lambda: p.eof(EOF(), -1, bytearray(4096), counts))

    def test_physical_partial_output_survives_failed_composition(self):
        paths, sizes, head, _ = fixture(self.dir)
        class Partial(p.IO):
            def __init__(self): self.n = 0
            def write(self, fd, view):
                self.n += 1
                if self.n == 2: return os.write(fd, view[:13])
                if self.n == 3: raise OSError("synthetic after actual partial write")
                return os.write(fd, view)
        out = self.dir / "partial-profile"
        with patch.object(p, "IO", Partial):
            error = self.refusal(lambda: p.compose_fixture(paths, sizes, head, out, self.dir), "io-error")
        self.assertEqual(out.stat().st_size, 512 + 13)
        self.assertEqual(error.progress["write_acknowledged"], 512 + 13)
        self.assertEqual(out.read_bytes(), head + bytes([93]) * 13)


class CustodyControls(OwnedTest):
    def test_injected_timeout_kills_and_reaps_actual_fixed_child(self):
        paths, sizes, head, _ = fixture(self.dir)
        original = subprocess.Popen
        children = []
        class FirstWaitTimeout:
            def __init__(self, *args, **kwargs):
                self.real = original(*args, **kwargs)
                self.first = True
                children.append(self.real)
            @property
            def returncode(self): return self.real.returncode
            def wait(self, timeout):
                if self.first:
                    self.first = False
                    raise subprocess.TimeoutExpired("injected finite control", timeout)
                return self.real.wait(timeout=timeout)
            def kill(self): return self.real.kill()
            def poll(self): return self.real.poll()
        out = self.dir / "timeout-profile"
        with patch.object(p.subprocess, "Popen", FirstWaitTimeout):
            self.refusal(lambda: p.compose_fixture(paths, sizes, head, out, self.dir), "child-timeout")
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].returncode)
        self.assertEqual(out.stat().st_size, p.PROFILE)
        REPORTS.append({"child_timeout_signal": "injected at first wait; not actual five-second expiry", "actual_fixed_child_killed_and_terminal_reaped": True})

    def test_wrong_retained_input_offsets_refuse(self):
        paths, sizes, head, _ = fixture(self.dir)
        for index in (0, 7):
            with ExitStack() as stack:
                inputs = [stack.enter_context(p.Retained(paths[name], sizes[name])) for name in p.NAMES]
                os.lseek(inputs[index].fd, 17, os.SEEK_SET)
                self.refusal(lambda: p.compose_from_retained_fixture(inputs, head, self.dir / "wrong-offset", self.dir), "input-offset")
                self.assertFalse((self.dir / "wrong-offset").exists())

    def test_same_body_descriptor_retained_from_synthetic_writer_through_child(self):
        paths, sizes, head, claims = fixture(self.dir)
        body_path = paths[p.NAMES[7]]
        body_path.unlink()  # Disposable test body only; recreate once exclusively.
        with ExitStack() as stack:
            inputs = [stack.enter_context(p.Retained(paths[name], sizes[name])) for name in p.NAMES[:7]]
            body = stack.enter_context(p.Retained(body_path, p.BODY, output=True))
            writer_fd = body.fd
            counts = p.IOCount()
            buffer = bytearray([93]) * 4096
            for _ in range(625):
                p.transfer(p.IO(), body.fd, memoryview(buffer), counts, True)
            self.assertEqual(os.lseek(body.fd, 0, os.SEEK_CUR), p.BODY)
            body.initial = p.identity(os.fstat(body.fd))
            inputs.append(body)
            opened = []
            original_open = p._open
            def observed_open(path, *args, **kwargs):
                opened.append(str(path))
                return original_open(path, *args, **kwargs)
            with patch.object(p, "_open", observed_open):
                result = p.compose_from_retained_fixture(inputs, head, self.dir / "same-fd-profile", self.dir)
            self.assertEqual(body.fd, writer_fd)
            self.assertNotIn(p.NAMES[7], opened)
            self.assertEqual(result["body_sha256"], claims[7].hex())
            self.assertTrue(result["child"]["terminal_reaped"])
            REPORTS.append({"same_body_fd_from_synthetic_writer_through_composition_child": True, "body_reopened": False, "actual_rust_producer": False})

    def test_zero_claim_transport_is_preserved_and_final_header_is_separate(self):
        paths, sizes, head, claims = fixture(self.dir)
        raw = header([bytes(32)] * 8)
        transport_path = self.dir / "original-transport-header"
        transport_path.write_bytes(raw)
        final = p.bind_fixture_template(raw, claims, sizes["original_input"])
        self.assertEqual(final, head)
        self.assertEqual(transport_path.read_bytes(), raw)
        self.assertEqual(final[:128], raw[:128])
        self.assertEqual(final[384:], raw[384:])
        self.assertNotEqual(final, raw)
        self.refusal(lambda: p.bind_fixture_template(head, claims, 128), "digest-slot-0")
        self.refusal(lambda: p.bind_fixture_template(raw, claims[:-1], 128), "digest-count-width")
        REPORTS.append({"transport_header_sha256": hashlib.sha256(raw).hexdigest(), "final_header_sha256": hashlib.sha256(final).hexdigest(), "original_transport_bytes": 512, "nonclaim_bytes_verified_identical": 256, "claims_replaced_only_in_distinct_header": True, "amendment_selected_for_product": False})

    def test_complete_actual_lengths_subrange_pre_post_and_child(self):
        paths, sizes, head, claims = fixture(self.dir)
        out = self.dir / "profile"
        result = p.compose_fixture(paths, sizes, head, out, self.dir)
        self.assertEqual(result["profile_bytes"], 2560512)
        self.assertEqual(result["output_acknowledged_bytes"], 2560512)
        self.assertEqual(result["claims"], [x.hex() for x in claims])
        self.assertEqual(result["io"]["write_calls"], 626)
        self.assertEqual(result["io"]["write_requested"], 2560512)
        self.assertTrue(result["child"]["terminal_reaped"])
        self.assertFalse(any(result["authority"].values()))
        # This independent test read is after terminal child reap and owner close.
        raw = out.read_bytes()
        self.assertEqual(raw[:512], head)
        self.assertEqual(raw[512:], bytes([93]) * p.BODY)
        self.assertEqual(hashlib.sha256(raw[512:]).digest(), claims[7])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result["profile_sha256"])
        REPORTS.append(result)

    def test_all_eight_slot_mismatches_and_swaps_refuse_before_output(self):
        paths, sizes, head, _ = fixture(self.dir)
        for index in range(8):
            bad = bytearray(head)
            bad[128 + index * 32] ^= 1
            out = self.dir / ("bad" + str(index))
            self.refusal(lambda: p.compose_fixture(paths, sizes, bytes(bad), out, self.dir), "digest-slot-" + str(index))
            self.assertFalse(out.exists())
        bad = head[:128] + head[160:192] + head[128:160] + head[192:]
        self.refusal(lambda: p.compose_fixture(paths, sizes, bad, self.dir / "swap", self.dir), "digest-slot-0")

    def test_short_extra_nonregular_symlink_parent_and_leaf_refuse(self):
        path = self.dir / "file"
        path.write_bytes(b"abc")
        for size in (2, 4):
            self.refusal(lambda: p.Retained(path, size), "regular-length-links")
        fifo = self.dir / "fifo"
        os.mkfifo(fifo)
        self.refusal(lambda: p.Retained(fifo, 0), "regular-length-links")
        leaf = self.dir / "leaf"
        leaf.symlink_to(path)
        with self.assertRaises(OSError): p.Retained(leaf, 3)
        real = self.dir / "real"
        real.mkdir()
        (real / "file").write_bytes(b"abc")
        link = self.dir / "link"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(OSError): p.Retained(link / "file", 3)

    def test_hard_link_and_output_existing_refuse(self):
        path = self.dir / "file"
        path.write_bytes(b"abc")
        os.link(path, self.dir / "alias")
        self.refusal(lambda: p.Retained(path, 3), "regular-length-links")
        paths, sizes, head, _ = fixture(self.dir)
        out = self.dir / "existing"
        out.write_bytes(b"preserve")
        with self.assertRaises(FileExistsError): p.compose_fixture(paths, sizes, head, out, self.dir)
        self.assertEqual(out.read_bytes(), b"preserve")

    def test_path_replacement_and_inplace_metadata_drift_refuse(self):
        path = self.dir / "file"
        path.write_bytes(b"abc")
        with p.Retained(path, 3) as held:
            path.rename(self.dir / "moved")
            path.write_bytes(b"abc")
            self.refusal(held.check, "path-identity")
        with p.Retained(path, 3) as held:
            path.write_bytes(b"abd")
            self.refusal(held.check, "metadata-drift")

    def test_parent_read_seek_close_denied_while_shared_OFD_live(self):
        path = self.dir / "file"
        path.write_bytes(b"abc")
        with p.Retained(path, 3) as held:
            with p.child_lease(held):
                self.refusal(lambda: p.hash_range(held, bytearray(4096), p.IOCount(), p.IO()), "shared-OFD-live")
                self.refusal(held.check, "shared-OFD-live")
                self.refusal(held.close, "child-live")
            held.check()

    def test_mutation_after_child_refuses_and_output_stays(self):
        paths, sizes, head, _ = fixture(self.dir)
        original = p.child_consume
        def mutation(profile, body, scratch):
            result = original(profile, body, scratch)
            os.pwrite(profile.fd, b"x", 512)
            return result
        out = self.dir / "mutated"
        with patch.object(p, "child_consume", mutation):
            self.refusal(lambda: p.compose_fixture(paths, sizes, head, out, self.dir), "metadata-drift")
        self.assertEqual(out.stat().st_size, p.PROFILE)

    def test_unsupported_custody_and_authority_flags_never_admit(self):
        self.refusal(lambda: p.compose_fixture({}, {}, b"", self.dir / "out", self.dir, scope="hostile-rewrite"), "unsupported-custody")
        self.refusal(lambda: p.compose_fixture({}, {}, b"", self.dir / "out", self.dir, scope=True), "unsupported-custody")

    def test_header_reserved_scalar_extent_and_length_refuse(self):
        paths, sizes, head, claims = fixture(self.dir)
        for coordinate in (0, 8, 16, 24, 32, 40, 56, 64, 72, 104, 112, 120, 384, 511):
            bad = bytearray(head)
            bad[coordinate] ^= 0xff
            self.refusal(lambda: p.header_check(bytes(bad), claims, 128))
        self.refusal(lambda: p.header_check(head[:-1], claims, 128))

    def test_child_adoption_duplicate_descriptor_refuses(self):
        spec = importlib.util.spec_from_file_location("fixture_consumer", ROOT / "consumer.py")
        consumer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(consumer)
        path = self.dir / "adopt"
        path.write_bytes(b"abc")
        fd = os.open(path, os.O_RDONLY)
        with consumer.adopt(str(fd), 3):
            with self.assertRaises(ValueError): consumer.adopt(str(fd), 3)
        with self.assertRaises(OSError): os.fstat(fd)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    (ROOT / "test-results.json").write_text(json.dumps({"schema": 1, "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped), "observations": REPORTS, "owned_descriptor_registry_final": len(p.OPEN_FDS), "owned_stdio_registry_final": len(p.STDIO_FDS), "owned_child_quarantines_final": len(p.QUARANTINES), "owned_scratch_entries_final": len(list(SCRATCH.iterdir())), "real_binding_accepted": False}, indent=2, sort_keys=True) + "\n")
    raise SystemExit(not result.wasSuccessful())
