"""Pure host input-model controls; no compiler, executable, loader or native call."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import unittest

from input_model import (
    COMPILE_KEYS, IDENTITIES, InvalidInput, Identity, PRODUCT_FIELDS,
    SESSION_KEYS, SOURCE_SHA256, STATUS, U64_MAX, VALIDATION,
    canonical, check_compile_closure, check_correspondence, check_product_budget,
    checked_roster, checked_sum, describe_candidate, digest, parse_record, unpack_list,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / "verification"
SOURCE = V / "swift-real-profile-loader-binding/source-preimages/genuine.wasm"
BASE = V / "swift-guarded-snapshot-outer-parent-source"
HOST = V / "swift-guarded-snapshot-host-composition"


def pack_list(values):
    # Independent test encoder, not imported from an old operational runner.
    return struct.pack("<Q", len(values)) + b"".join(struct.pack("<Q", len(x)) + x for x in values)


def set_word(data, offset, value):
    out = bytearray(data)
    struct.pack_into("<Q", out, offset, value)
    return bytes(out)


def flip(data, offset):
    return data[:offset] + bytes((data[offset] ^ 1,)) + data[offset + 1:]


def identity(role, data):
    return Identity(role, data, hashlib.sha256(data).digest())


def roster():
    return json.loads((BASE / "source-manifest.json").read_bytes())


def host_roster():
    return json.loads((HOST / "host-support-manifest.json").read_bytes())


def test_closure():
    # Real accepted frozen rosters in a synthetic uncompiled protocol record.
    return {"schema": 1, "distribution": roster(), "compiled_source": roster(),
            "host_support": host_roster(), "test_overlay": False,
            "private_route_cfg": "mixer_bootstrap_one_fixture_v1"}


def bundle():
    # These compiler/executable/review bytes are explicitly synthetic opaque
    # test inputs, never an executable, review acceptance or selected binding.
    source = SOURCE.read_bytes()
    compiler = b"synthetic-nonexecutable-compiler-preimage-for-format-tests"
    executable = b"synthetic-nonexecutable-output-preimage-for-format-tests"
    version = b"synthetic-retained-version-output-for-format-tests\n"
    manifest = canonical(test_closure())
    argv = pack_list([b"/synthetic/rustc", b"--target", b"aarch64-apple-darwin"])
    env = pack_list([b"PATH=/synthetic/compiler-support"])
    parts = (manifest, argv, env, version)
    head = bytearray(512)
    head[:8] = b"MIXLBD01"
    for at, value in ((8, 1), (16, 512), (24, 512 + sum(map(len, parts))), (32, 146), (40, 11), (80, len(executable))):
        struct.pack_into("<Q", head, at, value)
    for i, part in enumerate(parts):
        struct.pack_into("<Q", head, 48 + i * 8, len(part))
        head[152 + i * 32:184 + i * 32] = hashlib.sha256(part).digest()
    target = b"aarch64-apple-darwin"
    head[88:88 + len(target)] = target
    head[280:312] = hashlib.sha256(compiler).digest()
    head[312:344] = hashlib.sha256(executable).digest()
    build = bytes(head) + b"".join(parts)
    file_identity = struct.pack("<QQQQqqqq", 7, 13, 1947, 0o100444, 123456, 789, 123456, 789)
    process_argv = pack_list([b"/synthetic/future-output", b"--format-test-only"])
    process_env = pack_list([b"A=raw-\xff", b"PATH=/synthetic/runtime"])
    nonce = hashlib.sha256(b"deterministic synthetic nonce; not OS randomness").digest()
    session_parts = (file_identity, process_argv, process_env, b"/synthetic/cwd-\xff")
    head = bytearray(512)
    head[:8] = b"MIXLSE01"
    for at, value in ((8, 1), (16, 512), (24, 512 + sum(map(len, session_parts))), (32, 1947)):
        struct.pack_into("<Q", head, at, value)
    for i, part in enumerate(session_parts):
        struct.pack_into("<Q", head, 40 + i * 8, len(part))
        head[240 + i * 32:272 + i * 32] = hashlib.sha256(part).digest()
    for i, value in enumerate(VALIDATION):
        struct.pack_into("<Q", head, 72 + i * 8, value)
    head[112:144] = nonce
    head[144:176] = hashlib.sha256(source).digest()
    head[176:208] = hashlib.sha256(build).digest()
    head[208:240] = hashlib.sha256(executable).digest()
    session = bytes(head) + b"".join(session_parts)
    values = (source, build, session, executable, compiler, version, manifest,
              argv, env, process_argv, process_env, b"synthetic-unreviewed-artifact")
    return tuple(identity(name, data) for name, data in zip(IDENTITIES, values)), nonce, file_identity


class InputModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identities, cls.nonce, cls.file_identity = bundle()
        cls.paths = (b"/synthetic/source.wasm", b"/synthetic/build.bin", b"/synthetic/session.bin",
                     b"/synthetic/new-rows-\xff", b"/synthetic/new-snapshot")

    def correlate(self, identities=None, **overrides):
        args = dict(expected_session=self.identities[2].sha256, expected_nonce=self.nonce,
                    source_file_identity=self.file_identity)
        args.update(overrides)
        return check_correspondence(self.identities if identities is None else identities, **args)

    def changed(self, role, data):
        return tuple(identity(item.role, data) if item.role == role else item for item in self.identities)

    def test_actual_known_source(self):
        data = SOURCE.read_bytes()
        self.assertEqual(len(data), 1947)
        self.assertEqual(hashlib.sha256(data).hexdigest(), SOURCE_SHA256)

    def test_actual_base_all146_custody_and_host11(self):
        actual = roster()
        checked_roster(actual, 146)
        self.assertEqual(actual["tree_sha256"], "27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3")
        custody = json.loads((BASE / "source-custody.json").read_bytes())
        self.assertEqual(len(custody), 146)
        observed = []
        for item in custody:
            data = (ROOT / item["origin"]).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (item["bytes"], item["sha256"]))
            observed.append({k: item[k] for k in ("path", "bytes", "sha256")})
        self.assertEqual(observed, actual["members"])
        host = host_roster()
        checked_roster(host, 11)
        for item in host["members"]:
            data = (V / "swift-real-profile-loader-binding/host" / item["path"]).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (item["bytes"], item["sha256"]))

    def test_exact_known_source_and_loader_hashes(self):
        for path, expected in ((BASE / "overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs", "b19bca0a2f5ad193fc782061a2f345bd75b9414408643823b8f7691c89bc150f"),
                               (HOST / "overlay/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs", "ebe88f37d2721c41371c9f726aeefaf533451cc9b6309b296053bc3b327240b9")):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_fresh_synthetic_record_is_explicitly_unqualified(self):
        result = self.correlate()
        self.assertEqual(result["status"], STATUS)
        for key in ("actual_binary_embedded_values_observed", "launcher_or_file_custody_authenticated", "review_authenticated", "operational_grant"):
            self.assertIs(result[key], False)

    def test_all12_exact_counts_and_two_path_copies(self):
        result = describe_candidate(self.identities, self.paths, self.paths)
        self.assertEqual(result["input_backing_bytes"], sum(len(x.data) for x in self.identities) + 2 * sum(map(len, self.paths)))
        self.assertEqual(result["identity_bytes"], tuple(len(x.data) for x in self.identities))
        self.assertIs(result["authenticated_owner"], False)
        self.assertIs(result["operational_grant"], False)

    def test_aliasing_never_discounts_backing(self):
        paths = (self.paths[0],) * 5
        result = describe_candidate(self.identities, paths, paths)
        self.assertEqual(result["input_backing_bytes"], sum(len(x.data) for x in self.identities) + 10 * len(paths[0]))

    def test_no_unselected4096_limit_for_five_input_paths(self):
        paths = (b"/" + b"p" * 5000,) * 5
        self.assertEqual(describe_candidate(self.identities, paths, paths)["native_path_bytes"], (5001,) * 5)

    def test_all12_missing_empty_digest_mutable_and_order_controls(self):
        for i in range(12):
            with self.subTest(position=i):
                for altered in (self.identities[:i] + self.identities[i + 1:],
                                self.identities[:i] + (replace(self.identities[i], role="wrong-role"),) + self.identities[i + 1:],
                                self.identities[:i] + (replace(self.identities[i], sha256=flip(self.identities[i].sha256, 0)),) + self.identities[i + 1:],
                                self.identities[:i] + (identity(IDENTITIES[i], b""),) + self.identities[i + 1:],
                                self.identities[:i] + (replace(self.identities[i], data=bytearray(self.identities[i].data)),) + self.identities[i + 1:]):
                    with self.assertRaises(InvalidInput):
                        describe_candidate(altered, self.paths, self.paths)
        with self.assertRaises(InvalidInput):
            describe_candidate(self.identities[::-1], self.paths, self.paths)

    def test_five_native_path_controls(self):
        for i in range(5):
            for value in (b"", b"/has\0nul", b"/different", bytearray(self.paths[i])):
                paths = self.paths[:i] + (value,) + self.paths[i + 1:]
                with self.assertRaises(InvalidInput):
                    describe_candidate(self.identities, paths, self.paths)
        for size in (0, 4, 6):
            with self.assertRaises(InvalidInput):
                describe_candidate(self.identities, self.paths[:size] if size < 5 else self.paths + (b"/extra",), self.paths)

    def test_checked_nonzero_no_boolean_and_overflow(self):
        self.assertEqual(checked_sum((U64_MAX - 1, 1)), U64_MAX)
        for values in ((U64_MAX, 1), (0,), (True,), (-1,), ("4096",)):
            with self.assertRaises(InvalidInput):
                checked_sum(values)
        total = describe_candidate(self.identities, self.paths, self.paths)["input_backing_bytes"]
        with self.assertRaises(InvalidInput):
            describe_candidate(self.identities, self.paths, self.paths, limit=total - 1)

    def test_historical144_runner_output_is_incompatible(self):
        data = (V / "swift-real-profile-loader-binding/build-preimage-optimized.bin").read_bytes()
        self.assertEqual(struct.unpack_from("<Q", data, 32)[0], 144)
        with self.assertRaisesRegex(InvalidInput, "fresh146"):
            parse_record(data)

    def test_build_header_and_six_digest_controls(self):
        data = self.identities[1].data
        for offset, value in ((8, 2), (16, 511), (24, len(data) + 1), (32, 144), (40, 12), (48, 0), (80, 0), (80, 67108865)):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("build", set_word(data, offset, value)))
        for offset in (0, 88, 107, 344, 511):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("build", flip(data, offset)))
        for i in range(6):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("build", flip(data, 152 + i * 32)))
        for suffix in (b"x", b"\0" * 131072):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("build", data + suffix))

    def test_session_header_budget_digest_and_commitment_controls(self):
        data = self.identities[2].data
        for offset, value in ((8, 2), (16, 511), (24, len(data) + 1), (32, 1948), (40, 63), (48, 0)):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("session", set_word(data, offset, value)))
        for i in range(5):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("session", set_word(data, 72 + 8 * i, VALIDATION[i] + 1)))
        for offset in (0, 112, 144, 176, 208, 240, 272, 304, 336, 368, 511):
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed("session", flip(data, offset)))
        for name, value in (("expected_session", flip(self.identities[2].sha256, 0)), ("expected_nonce", flip(self.nonce, 0)),
                            ("source_file_identity", flip(self.file_identity, 0)), ("source_file_identity", self.file_identity[:-1])):
            with self.assertRaises(InvalidInput):
                self.correlate(**{name: value})

    def test_each_corresponding_full_preimage_is_required(self):
        for name in ("executable", "compiler", "compiler_version", "compile_manifest", "compile_argv", "compile_environment", "process_argv", "process_environment"):
            item = next(x for x in self.identities if x.role == name)
            with self.assertRaises(InvalidInput):
                self.correlate(self.changed(name, item.data + b"changed"))
        with self.assertRaises(InvalidInput):
            self.correlate(self.changed("source", flip(self.identities[0].data, 0)))

    def test_raw_lists_exact_boundary_and_bad_encodings(self):
        self.assertEqual(unpack_list(pack_list([b"raw-\xff", b""])), (b"raw-\xff", b""))
        self.assertEqual(unpack_list(pack_list([]), environment=True), ())
        self.assertEqual(len(unpack_list(pack_list([b"x" * 4095]))[0]), 4095)
        for value in (pack_list([]), pack_list([b"x\0"]), pack_list([b"x" * 4096]),
                      pack_list([b"x"] * 65), pack_list([b"x"]) + b"tail", struct.pack("<Q", 1),
                      struct.pack("<QQ", 1, U64_MAX), b"" * 8):
            with self.assertRaises(InvalidInput):
                unpack_list(value)
        for values in ([b"B=2", b"A=1"], [b"A=1", b"A=2"], [b"=x"], [b"A"], [b"A=x\0"]):
            with self.assertRaises(InvalidInput):
                unpack_list(pack_list(values), environment=True)
        for key in COMPILE_KEYS:
            with self.assertRaises(InvalidInput):
                unpack_list(pack_list([key + b"=" + b"a" * 64]), environment=True, compile=True)
        for key in SESSION_KEYS:
            with self.assertRaises(InvalidInput):
                unpack_list(pack_list([key + b"=" + b"a" * 64]), environment=True)
        # Runtime environment excludes two keys, not the five compile keys.
        self.assertEqual(len(unpack_list(pack_list([COMPILE_KEYS[0] + b"=x"]), environment=True)), 1)

    def test_compile_closure_exact_rosters(self):
        closure = test_closure()
        check_compile_closure(canonical(closure), expected_distribution=roster(), expected_compiled_source=roster(), expected_host=host_roster())
        for name in ("distribution", "compiled_source", "host_support"):
            altered = json.loads(canonical(closure))
            altered[name]["member_count"] -= 1
            with self.assertRaises(InvalidInput):
                check_compile_closure(canonical(altered), expected_distribution=roster(), expected_compiled_source=roster(), expected_host=host_roster())
        for name, value in (("test_overlay", True), ("private_route_cfg", "public"), ("artifact", {"sha256": "postcompile"})):
            altered = closure | {name: value}
            with self.assertRaises(InvalidInput):
                check_compile_closure(canonical(altered), expected_distribution=roster(), expected_compiled_source=roster(), expected_host=host_roster())
        with self.assertRaises(InvalidInput):
            check_compile_closure(json.dumps(closure, indent=2).encode(), expected_distribution=roster(), expected_compiled_source=roster(), expected_host=host_roster())

    def test_product_all17_without_policy_selection(self):
        # Explicit synthetic shape inputs; values are neither selected policy
        # nor arbitrary prices supplied to a root account.
        fields = {name: 12345 for name in PRODUCT_FIELDS}
        fields.update(execution_work=1_000_000_000, combined_bytes=268_435_456)
        self.assertEqual(check_product_budget(fields), "shape-only-policy-selection-pending")
        for name in PRODUCT_FIELDS:
            for altered in ({k: v for k, v in fields.items() if k != name}, fields | {name: True}, fields | {name: 0}):
                with self.assertRaises(InvalidInput):
                    check_product_budget(altered)
        for name in ("execution_work", "combined_bytes"):
            with self.assertRaises(InvalidInput):
                check_product_budget(fields | {name: fields[name] + 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
