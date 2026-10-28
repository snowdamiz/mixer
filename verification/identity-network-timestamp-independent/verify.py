#!/usr/bin/env python3
"""Independent offline timestamp admission review; no child or socket actions."""
import ast
from collections import Counter
import copy
import difflib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import signal
import sys
import tarfile
import time
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
FAILED = ROOT / "verification/github-delivery-source-pair-and-rebar/ci-review/network"
PRODUCER = ROOT / "verification/identity-network-jose-compile-investigation"
sys.dont_write_bytecode = True
START = time.monotonic()
AUDIT_COUNTS = Counter()
DENIED = []
READSET = {}
OBSERVATIONS = {}


def audit(event, args):
    AUDIT_COUNTS[event] += 1
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.spawn"
    }:
        DENIED.append(event)
        raise AssertionError("child/socket action denied: " + event)
    if event == "open":
        path, mode, flags = args
        writing = isinstance(mode, str) and any(c in mode for c in "wax+")
        writing |= isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR))
        if writing and isinstance(path, (str, bytes, os.PathLike)):
            assert Path(path).resolve().is_relative_to(BASE), "write outside owned review directory"


sys.addaudithook(audit)


def deadline(*_):
    raise TimeoutError("independent pure review exceeded 50 seconds")


signal.signal(signal.SIGALRM, deadline)
signal.alarm(50)


def binding(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def read(path):
    path = Path(path).resolve()
    body = path.read_bytes()
    name = str(path.relative_to(ROOT))
    row = binding(body)
    assert name not in READSET or READSET[name] == row, "input changed during review: " + name
    READSET[name] = row
    return body


def write_json(name, value):
    (BASE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def unpack(body):
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:") as archive:
        members = archive.getmembers()
        assert len(members) < 10000
        contents = {member.name: archive.extractfile(member).read() for member in members}
    assert len(contents) == len(members)
    return members, contents


CANONICAL = {
    "hosted/scripts/test-identity-network.py": "d9d750256b2734c80577f58b4eb9c8cfd0adf177ba12a453ecb1c050d0942c0e",
    "hosted/scripts/test_identity_network_collector.py": "8d3b37474fc132aa91d02f643956f87cfa2d177305aee167819ce3c5edd68691",
    "docs/hosted-identity-production-network-ci-contract.md": "37d2b3679bdedf9fbc7621f8ebaec81b27bb0d6de18b4d1dea0d3cfe3fc631db",
}
canonical_bytes = {name: read(ROOT / name) for name in CANONICAL}
assert all(binding(body)["sha256"] == CANONICAL[name] for name, body in canonical_bytes.items())
producer_inputs = {name: read(PRODUCER / name) for name in (
    "verify.py", "findings.md", "receipt.json", "controls-output.txt", "platform-source-evidence.json")}
producer_receipt = json.loads(producer_inputs["receipt.json"])
artifact_manifest = json.loads(read(FAILED / "artifact-manifest.json"))
artifact_names = (
    "prepared-source-dependencies-tools.tar", "prepared-manifest.json", "collector-source.tar",
    "compiled-modules-before-tests.json", "prepare-prerequisites.json", "test-prerequisites.json",
    "state.json", "logs/0087.json", "logs/0087.stdout", "logs/0101.json", "logs/0101.stdout",
)
artifact = {name: read(FAILED / name) for name in artifact_names}
assert all(binding(body) == artifact_manifest["files"][name] for name, body in artifact.items())
raw = artifact["prepared-source-dependencies-tools.tar"]
members, bodies = unpack(raw)
manifest = json.loads(artifact["prepared-manifest.json"])
assert len(members) == 1232 and len(raw) == 15196160
assert all(member.mtime == 0 and member.isfile() and not member.pax_headers for member in members)
expected = {path: row for section in manifest.values() for path, row in section.items()}
assert {name: binding(body) for name, body in bodies.items()} == expected
_, archived_controls = unpack(artifact["collector-source.tar"])
state = json.loads(artifact["state.json"])
assert state["sha"] == "8888d8e2c8431ee311c68e94a1abbb280f84802a"
for name in ("prepare-prerequisites.json", "test-prerequisites.json"):
    value = json.loads(artifact[name])
    assert value["elixir"] == "1.20.4" and "Mix 1.20.4" in value["mix"]
    assert value["otp_patch"] == "29.1.1"

spec = importlib.util.spec_from_file_location("timestamp_independent_collector", ROOT / "hosted/scripts/test-identity-network.py")
collector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = collector
spec.loader.exec_module(collector)


def reheader(body, changes):
    value = bytearray(body)
    for member in members:
        if member.name not in changes:
            continue
        header = bytearray(value[member.offset:member.offset + 512])
        stamp = changes[member.name]
        header[136:148] = stamp if isinstance(stamp, bytes) else tarfile.itn(stamp, 12, tarfile.GNU_FORMAT)
        assert len(header) == 512
        header[148:156] = b"        "
        header[148:156] = ("%06o\0 " % sum(header)).encode()
        value[member.offset:member.offset + 512] = header
    return bytes(value)


candidate = reheader(raw, {member.name: 1 for member in members})
member_map = {member.name: member for member in members}
section_paths = {section: sorted(rows)[0] for section, rows in manifest.items()}


def rejected(body, expected_message=None, manifest_value=None):
    try:
        collector.validate_transfer_archive(body)
        collector.validate_prepared_archive(body, manifest if manifest_value is None else manifest_value)
    except (collector.CollectorError, tarfile.TarError, ValueError) as error:
        if expected_message is not None:
            assert expected_message in str(error), str(error)
        return type(error).__name__ + ": " + str(error)
    raise AssertionError("invalid prepared archive admitted")


def methods(source):
    return {cls.name + "." + method.name: ast.dump(method, include_attributes=False)
            for cls in ast.parse(source).body if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")}


class TimestampIndependentTests(unittest.TestCase):
    def test_01_actual_archive_only_header_time_and_checksum_change(self):
        candidate_members, candidate_bodies = unpack(candidate)
        self.assertEqual(candidate_bodies, bodies)
        self.assertEqual(len(candidate), len(raw))
        self.assertEqual({member.mtime for member in candidate_members}, {1})
        for old, new in zip(members, candidate_members):
            self.assertEqual({k: v for k, v in old.get_info().items() if k not in {"mtime", "chksum"}},
                             {k: v for k, v in new.get_info().items() if k not in {"mtime", "chksum"}})
            start = old.offset
            self.assertEqual(raw[start:start + 136], candidate[start:start + 136])
            self.assertEqual(raw[start + 156:start + 512], candidate[start + 156:start + 512])
            next_start = start + 512 + ((old.size + 511) // 512) * 512
            self.assertEqual(raw[start + 512:next_start], candidate[start + 512:next_start])
        self.assertEqual(collector.validate_transfer_archive(candidate), candidate)
        self.assertEqual(collector.validate_prepared_archive(candidate, manifest), expected)
        self.assertEqual(rejected(raw, "prepared archive timestamp mismatch"),
                         "CollectorError: prepared archive timestamp mismatch")
        OBSERVATIONS["same_artifact_candidate"] = binding(candidate)

    def test_02_one_invalid_timestamp_per_actual_section_rejected(self):
        results = []
        for section, path in section_paths.items():
            for stamp in (-1, 0, 2, 4294967295):
                with self.subTest(section=section, timestamp=stamp):
                    error = rejected(reheader(candidate, {path: stamp}), "prepared archive timestamp mismatch")
                    results.append({"section": section, "path": path, "timestamp": stamp, "refusal": error})
        OBSERVATIONS["timestamp_matrix"] = results

    def test_03_fractional_pax_and_malformed_octal_rejected(self):
        path = section_paths["deps"]
        offset = member_map[path].offset
        # A real, valid PAX fractional timestamp on an actual prepared member.
        # PAX records count their own decimal length, including the prefix.
        length = len(b" mtime=1.5\n") + 2
        while len(str(length).encode() + b" mtime=1.5\n") != length:
            length = len(str(length).encode() + b" mtime=1.5\n")
        pax_body = str(length).encode() + b" mtime=1.5\n"
        info = tarfile.TarInfo("././@PaxHeader")
        info.type, info.size = tarfile.XHDTYPE, len(pax_body)
        pax = info.tobuf(format=tarfile.USTAR_FORMAT) + pax_body + bytes((-len(pax_body)) % 512)
        fraction = candidate[:offset] + pax + candidate[offset:]
        with tarfile.open(fileobj=io.BytesIO(fraction), mode="r:") as archive:
            self.assertEqual(archive.getmember(path).mtime, 1.5)
        OBSERVATIONS["fractional_refusal"] = rejected(fraction, "extended archive metadata refused")
        bad = reheader(candidate, {path: b"not-octal!!\0"})
        OBSERVATIONS["malformed_timestamp_refusal"] = rejected(bad)

    def test_04_payload_manifest_membership_and_budget_controls_remain(self):
        path = section_paths["deps"]
        member = member_map[path]
        mutation = bytearray(candidate)
        mutation[member.offset_data] ^= 1
        self.assertIn("prepared archive hash mismatch", rejected(bytes(mutation)))
        end = member.offset + 512 + ((member.size + 511) // 512) * 512
        missing = candidate[:member.offset] + candidate[end:]
        self.assertIn("prepared archive path mismatch", rejected(missing))
        wrong_manifest = copy.deepcopy(manifest)
        wrong_manifest["deps"][path]["sha256"] = "0" * 64
        self.assertIn("prepared archive hash mismatch", rejected(candidate, manifest_value=wrong_manifest))
        contaminated = copy.deepcopy(manifest)
        contaminated["deps"]["hosted/deps/fixture/_build/injected.beam"] = {"bytes": 1, "sha256": "0" * 64}
        self.assertIn("forbidden prepared payload", rejected(candidate, manifest_value=contaminated))
        with mock.patch.object(collector, "MAX_ARCHIVE_BYTES", len(candidate) - 1):
            self.assertIn("transfer archive byte cap/type", rejected(candidate))
        OBSERVATIONS["unchanged_negative_controls"] = ["payload hash", "missing membership", "manifest hash", "build contamination", "archive byte budget"]

    def test_05_collector_only_expected_three_ast_changes(self):
        path = "hosted/scripts/test-identity-network.py"
        old = ast.parse(archived_controls[path])
        new = ast.parse(canonical_bytes[path])
        removed = Counter()
        class Normalize(ast.NodeTransformer):
            def visit_Assign(self, node):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "PREPARED_MTIME":
                    self.assert_exact(node.value, ast.Constant(1))
                    removed["positive constant"] += 1
                    return None
                return self.generic_visit(node)
            def assert_exact(self, left, right):
                assert ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)
            def visit_Expr(self, node):
                call = node.value
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "require" and len(call.args) == 2 and isinstance(call.args[1], ast.Constant) and call.args[1].value == "prepared archive timestamp mismatch":
                    exact = ast.parse('require(type(member.mtime) is int and member.mtime == PREPARED_MTIME, "prepared archive timestamp mismatch")').body[0]
                    self.assert_exact(node, exact)
                    removed["exact timestamp admission"] += 1
                    return None
                return self.generic_visit(node)
            def visit_JoinedStr(self, node):
                exact = ast.parse('f"--mtime=@{PREPARED_MTIME}"', mode="eval").body
                if ast.dump(node, include_attributes=False) == ast.dump(exact, include_attributes=False):
                    removed["preparation tar argument"] += 1
                    return ast.Constant("--mtime=@0")
                return self.generic_visit(node)
        normalized = Normalize().visit(new)
        self.assertEqual(dict(removed), {"positive constant": 1, "exact timestamp admission": 1, "preparation tar argument": 1})
        self.assertEqual(ast.dump(old, include_attributes=False), ast.dump(normalized, include_attributes=False))
        transfer_members, _ = unpack(collector.source_tar({"hosted/fixture.ex": b"unchanged transfer behavior"}))
        self.assertEqual({member.mtime for member in transfer_members}, {0})
        test_path = "hosted/scripts/test_identity_network_collector.py"
        before, after = methods(archived_controls[test_path]), methods(canonical_bytes[test_path])
        self.assertEqual(len(before), 126)
        self.assertTrue(all(after.get(name) == body for name, body in before.items()))
        self.assertEqual(len(after) - len(before), 3)
        self.assertEqual(len(manifest["source"]), 177)
        self.assertEqual(collector.FROZEN_MANIFEST, manifest["source"])
        for name, row in manifest["source"].items():
            self.assertEqual(binding(bodies[name]), row)
        for name, expected_hash in producer_receipt["protected_hashes"].items():
            self.assertEqual(binding(read(ROOT / name))["sha256"], expected_hash)
        OBSERVATIONS["collector_ast_delta"] = dict(removed)
        OBSERVATIONS["original_test_methods_unchanged"] = len(before)
        OBSERVATIONS["frozen_archive_product_files_unchanged"] = len(manifest["source"])
        OBSERVATIONS["protected_checkout_hashes_unchanged"] = producer_receipt["protected_hashes"]
        diff = "".join(difflib.unified_diff(archived_controls[path].decode().splitlines(True), canonical_bytes[path].decode().splitlines(True), fromfile="8888/" + path, tofile="candidate/" + path))
        (BASE / "collector-change.diff").write_text(diff)

    def test_06_official_exact_version_causal_chain_and_observed_closure(self):
        metadata = json.loads(read(BASE / "platform-acquisition.json"))
        prior = json.loads(producer_inputs["platform-source-evidence.json"])
        prior_files = {row["path"]: row for row in prior["files"]}
        platform = {}
        for row in metadata["files"]:
            body = read(BASE / row["saved_path"])
            blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            self.assertEqual(blob, row["git_blob_sha"])
            self.assertEqual(blob, prior_files[row["path"]]["git_blob_sha"])
            platform[row["path"]] = body.decode()
            for excerpt in prior_files[row["path"]]["excerpts"]:
                selected = "".join(body.decode().splitlines(True)[excerpt["start_line"] - 1:excerpt["end_line"]])
                self.assertEqual(selected.rstrip(), excerpt["text"].rstrip())
        utils = platform["lib/mix/lib/mix/utils.ex"]
        self.assertIn("last_modified(source) > modified_target", utils)
        self.assertIn("{:error, _} ->\n        {0, -1}", utils)
        erlang = platform["lib/mix/lib/mix/tasks/compile.erlang.ex"]
        self.assertIn("if force || Mix.Utils.stale?([erl.file | erl.includes], [beam]) do", erlang)
        deps_compile = platform["lib/mix/lib/mix/tasks/deps.compile.ex"]
        options = deps_compile.split("options = [", 1)[1].split("]", 1)[0]
        self.assertIn('"--no-warnings-as-errors"', options)
        self.assertNotIn('"--force"', options)
        self.assertIn('res = Mix.Task.run("compile", options)', deps_compile)
        self.assertIn("env = opts[:env] || :prod", platform["lib/mix/lib/mix/dep.ex"])
        self.assertIn(b'version: "1.11.13"', bodies["hosted/deps/jose/mix.exs"])
        self.assertIn(b'{:jose, "== 1.11.13"}', bodies["hosted/mix.exs"])
        self.assertIn(b"if(Mix.env() == :prod, do: [], else: [:warnings_as_errors])", bodies["hosted/deps/jose/mix.exs"])
        sources = sorted(name for name in bodies if name.startswith("hosted/deps/jose/") and name.endswith(".erl"))
        self.assertEqual(len(sources), 113)
        def external_headers(path, visiting=frozenset()):
            if path in visiting:
                return set()
            headers = set()
            for line in bodies[path].decode().splitlines():
                line = line.strip()
                if line.startswith("%") or "-include" not in line:
                    continue
                if line.startswith('-include_lib('):
                    self.assertTrue(line.endswith(")."))
                    headers.add(json.loads(line[len('-include_lib('):-2]))
                else:
                    self.assertTrue(line.startswith('-include(') and line.endswith(")."))
                    name = json.loads(line[len('-include('):-2])
                    candidates = {str(PurePosixPath(path).parent / name), "hosted/deps/jose/include/" + name} & set(bodies)
                    self.assertEqual(len(candidates), 1)
                    headers |= external_headers(candidates.pop(), visiting | {path})
            return headers
        closure = {PurePosixPath(path).stem: sorted(external_headers(path)) for path in sources}
        self.assertEqual({header for rows in closure.values() for header in rows}, {"public_key/include/public_key.hrl"})
        observed = sorted(PurePosixPath(path).stem for path in json.loads(artifact["compiled-modules-before-tests.json"])
                          if "/jose/ebin/" in path and not PurePosixPath(path).name.startswith("Elixir."))
        predicted = sorted(module for module, headers in closure.items() if headers)
        self.assertEqual(predicted, observed)
        self.assertEqual(len(observed), 16)
        self.assertEqual(len(set(closure) - set(observed)), 97)
        self.assertTrue({"jose_jwk", "jose_jwt", "jose_jwe"} <= set(closure) - set(observed))
        self.assertFalse(0 > 0)
        self.assertTrue(1 > 0)
        self.assertEqual(json.loads(artifact["logs/0087.json"])["exit_code"], 0)
        self.assertIn(b"Compiling 16 files (.erl)", artifact["logs/0087.stdout"])
        self.assertEqual(json.loads(artifact["logs/0101.json"])["exit_code"], 2)
        self.assertEqual(artifact["logs/0101.stdout"].count(b"function :jose_jwk.generate_key/1 is undefined"), 2)
        self.assertIn(b"Result: 0/2 passed", artifact["logs/0101.stdout"])
        OBSERVATIONS["independent_include_closure"] = closure
        OBSERVATIONS["observed_and_predicted_erl_modules"] = observed
        OBSERVATIONS["causal_limit"] = "Source-derived stale predicate and exact include-closure agreement; historical OTP header timestamps unavailable; no Erlang evaluator or compiler executed."


suite = unittest.defaultTestLoader.loadTestsFromTestCase(TimestampIndependentTests)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
(BASE / "audit-output.txt").write_text(stream.getvalue())
assert result.wasSuccessful(), stream.getvalue()
assert not DENIED
for name, row in list(READSET.items()):
    assert binding((ROOT / name).read_bytes()) == row, "readset drift before seal: " + name
write_json("readset.json", {"schema": 1, "files": READSET})
write_json("observations.json", OBSERVATIONS)
write_json("audit.json", {"schema": 1, "events_seen": dict(AUDIT_COUNTS), "denied_child_socket_attempts": DENIED, "write_scope": str(BASE)})
receipt = {
    "schema": 1, "decision": "accept-minimal-timestamp-correction-for-isolated-CI",
    "command": "python3 -B verification/identity-network-timestamp-independent/verify.py",
    "python": sys.version, "tests_passed": result.testsRun,
    "elapsed_seconds": time.monotonic() - START, "deadline_seconds": 50,
    "current_revision_observed_before_review": "dfd0e3196543cc1749c9cc924cc7accf28c9dc25",
    "current_git_tree_observed_before_review": "3cc58d6744649fdd138b9d3963b436db62480ecf",
    "failed_source_revision": state["sha"], "failed_run": "40766689512", "failed_product_methods_passed": 0,
    "candidate_canonical_hashes": CANONICAL,
    "original_archive": binding(raw), "candidate_archive_in_memory": binding(candidate),
    "actual_archive_files": len(members), "all_payload_bytes_and_metadata_except_mtime_checksum_preserved": True,
    "original_test_bodies_unchanged": 126, "frozen_archive_product_files_unchanged": 177,
    "protected_checkout_hashes_unchanged": producer_receipt["protected_hashes"],
    "denied_child_socket_attempts": DENIED, "archive_extraction": "none; in-memory reads and reheader only",
    "runtime_acceptance": "pending fresh isolated CI compilation and independent evidence for both unchanged methods",
    "holds": "No local compiler/runtime/container/PostgreSQL/native/UI/capture/custody or held-process probes; no git writes, push, dispatch or canonical edits.",
    "cleanup": "No persistent resources or extracted archive; candidate remained in memory; only owned review files written.",
    "producer_packet_binding": "All five producer packet files bound in readset.json; independent official sources acquired separately.",
}
write_json("receipt.json", receipt)
signal.alarm(0)
print(json.dumps({key: receipt[key] for key in ("decision", "tests_passed", "elapsed_seconds", "denied_child_socket_attempts", "runtime_acceptance")}))
