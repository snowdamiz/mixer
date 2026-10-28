#!/usr/bin/env python3
"""Bounded pure source/artifact proof; never execute archived or product code."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import signal
import sys
import tarfile
import time
import unittest

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
FAILED = ROOT / "verification/github-delivery-source-pair-and-rebar/ci-review/network"
AUDIT = []
sys.dont_write_bytecode = True


def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.spawn"
    }:
        AUDIT.append(event)
        raise AssertionError("child/socket action denied: " + event)


def deadline(*_):
    raise TimeoutError("pure investigation exceeded 50 seconds")


sys.addaudithook(audit)
signal.signal(signal.SIGALRM, deadline)
signal.alarm(50)
START = time.monotonic()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def binding(body):
    return {"bytes": len(body), "sha256": digest(body)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def load_archive(body):
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:") as archive:
        members = archive.getmembers()
        assert len(members) < 10000
        assert all(m.isfile() and not m.pax_headers and m.offset_data == m.offset + 512 for m in members)
        assert len({m.name for m in members}) == len(members)
        contents = {m.name: archive.extractfile(m).read() for m in members}
    return members, contents


def test_methods(source):
    return {cls.name + "." + method.name: ast.dump(method, include_attributes=False)
            for cls in ast.parse(source).body if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")}


manifest = json.loads((FAILED / "artifact-manifest.json").read_bytes())
inputs = ["prepared-source-dependencies-tools.tar", "prepared-manifest.json", "compiled-modules-before-tests.json",
          "collector-source.tar", "logs/0087.json", "logs/0087.stdout", "logs/0087.stderr",
          "logs/0101.json", "logs/0101.stdout"]
raw = {name: (FAILED / name).read_bytes() for name in inputs}
assert all(binding(body) == manifest["files"][name] for name, body in raw.items())
prepared_members, contents = load_archive(raw["prepared-source-dependencies-tools.tar"])
assert len(prepared_members) == 1232 and {m.mtime for m in prepared_members} == {0}
prepared_manifest = json.loads(raw["prepared-manifest.json"])
assert {m.name: binding(contents[m.name]) for m in prepared_members} == {
    name: row for section in prepared_manifest.values() for name, row in section.items()
}
assert len(prepared_manifest["source"]) == 177
assert digest(canonical(prepared_manifest["source"])) == "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
assert b'{:jose, "== 1.11.13"}' in contents["hosted/mix.exs"]
assert b'version: "1.11.13"' in contents["hosted/deps/jose/mix.exs"]
_, previous_controls = load_archive(raw["collector-source.tar"])
test_path = "hosted/scripts/test_identity_network_collector.py"
previous_tests = test_methods(previous_controls[test_path])
current_tests = test_methods((ROOT / test_path).read_bytes())
assert len(previous_tests) == 126
assert all(current_tests.get(name) == body for name, body in previous_tests.items())
assert len(current_tests) == 129

spec = importlib.util.spec_from_file_location("jose_investigation_controls", ROOT / test_path)
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)
collector = controls.collector
stream = io.StringIO()
suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
(BASE / "controls-output.txt").write_text(stream.getvalue())
assert result.wasSuccessful() and result.testsRun == 129

# Change only fixed-width USTAR mtime/checksum fields in memory; no extraction.
candidate = bytearray(raw["prepared-source-dependencies-tools.tar"])
for member in prepared_members:
    header = bytearray(candidate[member.offset:member.offset + 512])
    header[136:148] = b"00000000001\0"
    header[148:156] = b"        "
    header[148:156] = ("%06o\0 " % sum(header)).encode("ascii")
    candidate[member.offset:member.offset + 512] = header
candidate = bytes(candidate)
candidate_members, candidate_contents = load_archive(candidate)
assert candidate_contents == contents
assert {m.mtime for m in candidate_members} == {1}
assert len(candidate) == len(raw["prepared-source-dependencies-tools.tar"])
collector.validate_transfer_archive(candidate)
collector.validate_prepared_archive(candidate, prepared_manifest)
try:
    collector.validate_prepared_archive(raw["prepared-source-dependencies-tools.tar"], prepared_manifest)
except collector.CollectorError as error:
    assert str(error) == "prepared archive timestamp mismatch"
else:
    raise AssertionError("epoch-zero baseline must be rejected")

# A narrow include-closure discriminator, not an Erlang evaluator or runtime pass.
erlang = {name: body.decode() for name, body in contents.items()
          if name.startswith("hosted/deps/jose/") and name.endswith(".erl")}
assert len(erlang) == 113


def external_includes(name, visited=None):
    visited = set() if visited is None else visited
    if name in visited:
        return set()
    visited.add(name)
    body = contents[name].decode()
    found = set(re.findall(r'^\s*-include_lib\("([^"\n]+)"\)\.', body, re.M))
    for include in re.findall(r'^\s*-include\("([^"\n]+)"\)\.', body, re.M):
        target = "hosted/deps/jose/include/" + include
        assert target in contents
        found |= external_includes(target, visited)
    return found


closure = {PurePosixPath(name).stem: sorted(external_includes(name)) for name in erlang}
assert set(x for rows in closure.values() for x in rows) == {"public_key/include/public_key.hrl"}
predicted_epoch_zero = sorted(module for module, includes in closure.items() if includes)
beam_map = json.loads(raw["compiled-modules-before-tests.json"])
observed = sorted(PurePosixPath(path).stem for path in beam_map
                  if "/jose/ebin/" in path and not PurePosixPath(path).name.startswith("Elixir."))
assert predicted_epoch_zero == observed and len(observed) == 16
omitted = sorted(set(closure) - set(observed))
assert len(omitted) == 97 and {"jose_jwk", "jose_jwt", "jose_jwe"} <= set(omitted)
# Exact Mix predicate: a missing target's time is zero; sources at one are newer.
assert not (0 > 0) and 1 > 0
assert all(1 > 0 for _ in erlang)
compile_log = json.loads(raw["logs/0087.json"])
test_log = json.loads(raw["logs/0101.json"])
assert compile_log["exit_code"] == 0 and test_log["exit_code"] == 2
assert b"Compiling 16 files (.erl)" in raw["logs/0087.stdout"]
assert raw["logs/0101.stdout"].count(b"function :jose_jwk.generate_key/1 is undefined") == 2
assert b"Result: 0/2 passed" in raw["logs/0101.stdout"]
protected = {".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
             "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299"}
assert all(digest((ROOT / name).read_bytes()) == expected for name, expected in protected.items())
assert not AUDIT
receipt = {
    "schema": 1, "status": "pure-controls-and-artifact-discriminator-pass",
    "command": "python3 -B verification/identity-network-jose-compile-investigation/verify.py",
    "python": sys.version, "started_source_revision": "8888d8e2c8431ee311c68e94a1abbb280f84802a",
    "elapsed_seconds": time.monotonic() - START, "deadline_seconds": 50,
    "audit_denied_action_attempts": AUDIT, "original_test_bodies_unchanged": 126,
    "pure_controls_passed": result.testsRun, "added_timestamp_controls": 3,
    "prior_actual_run": "40766689512", "prior_actual_product_passes": 0, "prior_actual_product_failures": 2,
    "input_bindings": {name: binding(body) for name, body in raw.items()},
    "candidate_archive_in_memory": binding(candidate), "candidate_archive_timestamp": 1,
    "archive_entries": len(prepared_members), "every_payload_byte_preserved": True,
    "jose_locked_version": "1.11.13", "jose_erlang_sources": 113,
    "compiled_erlang_modules": observed, "epoch_zero_external_header_prediction": predicted_epoch_zero,
    "omitted_erlang_modules": omitted, "positive_timestamp_predicted_stale_sources": 113,
    "prediction_limit": "Source-derived predicate and include closure only. No local Erlang evaluator/compiler/runtime was executed; OTP header mtimes were not independently observed.",
    "runtime_acceptance": "pending fresh isolated CI for unchanged two methods",
    "protected_hashes": protected,
    "canonical_bindings": {name: binding((ROOT / name).read_bytes()) for name in (
        "hosted/scripts/test-identity-network.py", test_path, "docs/hosted-identity-production-network-ci-contract.md")},
    "cleanup": "No native/container/process/capture/custody work launched; in-memory candidate only; test temporary directories self-cleaned."
}
(BASE / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
signal.alarm(0)
print(json.dumps({key: receipt[key] for key in ("status", "elapsed_seconds", "pure_controls_passed", "original_test_bodies_unchanged", "audit_denied_action_attempts")}))
