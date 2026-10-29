#!/usr/bin/env python3
"""Independent source/mock review only; effects denied before subject imports."""
import unittest.mock  # Preload stdlib socket subclasses before replacing socket.socket.
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import _thread
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKET = ROOT / "verification/swift-pin-bitmap-lint-independent-admission"
ATTEMPTS = []
sys.dont_write_bytecode = True


def denied(*args, **kwargs):
    ATTEMPTS.append("denied-live-api")
    raise AssertionError("Independent host proposal review: live API denied")


def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.", "ctypes.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec",
        "os.kill", "os.killpg", "os.chdir",
    }:
        denied()
    if event == "open":
        name, mode, flags = args
        writing = isinstance(mode, str) and any(c in mode for c in "wax+")
        writing |= isinstance(flags, int) and bool(flags & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        ))
        if writing and (not isinstance(name, (str, bytes, os.PathLike)) or
                        not Path(os.fsdecode(name)).resolve().is_relative_to(HERE)):
            denied()
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.chmod", "os.symlink", "os.link"}:
        targets = args[:2] if event in {"os.rename", "os.link"} else args[:1]
        if event == "os.symlink":
            targets = args[1:2]
        for target in targets:
            if not Path(os.fsdecode(target)).resolve().is_relative_to(HERE):
                denied()


sys.addaudithook(audit)
subprocess.Popen = subprocess.run = subprocess.call = denied
subprocess.check_call = subprocess.check_output = denied
socket.socket = socket.create_connection = socket.socketpair = denied
for name in dir(os):
    if name.startswith(("exec", "spawn", "posix_spawn")) or name in {
        "system", "fork", "forkpty", "kill", "killpg", "wait", "waitpid", "wait3",
        "wait4", "waitid", "popen", "setsid", "setpgid", "getpgid", "getsid",
    }:
        setattr(os, name, denied)
for name in ("signal", "setitimer", "alarm", "getsignal", "raise_signal", "pthread_kill",
             "sigwait", "sigwaitinfo", "sigtimedwait"):
    if hasattr(signal, name):
        setattr(signal, name, denied)
resource.getrusage = denied
threading.Thread.start = _thread.start_new_thread = time.sleep = denied


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


b = load("bounded_commands", PACKET / "bounded_commands.py")
a = load("review_subject_admit", PACKET / "admit.py")
OBSERVATIONS = {}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def passed_text():
    names = list(a.ORACLES) + ["fixture_" + str(i) for i in range(690)]
    return "".join("test " + n + " ... ok\n" for n in names) + (
        "test result: ok. 699 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n"
    )


class Controls(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="pure-", dir=HERE))

    def tearDown(self):
        for path in sorted(self.work.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                path.rmdir()
        self.work.rmdir()

    def fixture(self):
        paths = {n: self.work / n for n in ("source", "target", "cargo", "home", "nodebin")}
        for p in paths.values():
            p.mkdir()
        raw = {n: ("fn fixture() {} // " + n + "\n").encode() for n in a.OVERLAYS}
        raw["Cargo.toml"] = b"[package]\n"
        for n, value in raw.items():
            p = paths["source"] / n
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(value)
        expected = {n: a.file_row(v) for n, v in raw.items()}
        toolbin = self.work / "tools"
        toolbin.mkdir()
        for n in a.TOOLS:
            p = toolbin / n
            p.write_text("mock " + n)
            p.chmod(0o700)
        tools = {n: a.binary_row(toolbin / n) for n in a.TOOLS}
        external = self.work / "external"
        external.mkdir()
        binary = external / "node"
        binary.write_text("mock node")
        binary.chmod(0o700)
        node = a.binary_row(binary)
        (paths["nodebin"] / "node").symlink_to(binary)
        config = self.work / "rustfmt.toml"
        config.write_text('edition = "2021"\n')
        out = self.work / "evidence"
        out.mkdir()
        return paths, expected, raw, toolbin, tools, node, config, out

    def fake_command(self, spec, text="", code=0, mutation=None, failure=None):
        c = types.SimpleNamespace(receipt={"commands": []}, save=mock.Mock())
        def run(*args, **kwargs):
            row = {"name": spec["name"], "exit": code}
            c.receipt["commands"].append(row)
            if mutation:
                mutation()
            if failure:
                raise failure
            return text, "", row
        c.run = mock.Mock(side_effect=run)
        return c

    def test_frozen_packet_exact(self):
        raw = (PACKET / "seal.json").read_bytes()
        self.assertEqual(digest(raw), "2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238")
        seal = json.loads(raw)
        self.assertEqual(len(seal["files"]), 18)
        for name, row in seal["files"].items():
            actual = (PACKET / name).read_bytes()
            self.assertEqual({"bytes": len(actual), "sha256": digest(actual)}, row)
        closure = digest("".join(n + "\0" + seal["files"][n]["sha256"] + "\n" for n in sorted(seal["files"])).encode())
        self.assertEqual(closure, "b3bb8c60d2a14213b48e7a203b97618cce8214fd78b09219f9d779fd3ef7359c")
        self.assertEqual(closure, seal["treeSHA256"])
        OBSERVATIONS["inputPacket"] = {"members": 18, "sealSHA256": digest(raw), "treeSHA256": closure}

    def test_imports_guarded_and_no_live_calls(self):
        self.assertIs(b.subprocess.Popen, denied)
        self.assertIs(b.os.setsid, denied)
        self.assertIs(b.os.waitpid, denied)
        self.assertIs(b.os.killpg, denied)
        self.assertIs(a.signal.setitimer, denied)
        self.assertIs(b.resource.getrusage, denied)
        self.assertIs(socket.socket, denied)
        self.assertEqual(ATTEMPTS, [])

    def test_source_admission_reproduces_candidate_without_runtime(self):
        manifest, data = a.inputs()
        self.assertEqual(len(data), 136)
        self.assertEqual(len(a.OVERLAYS), 15)
        self.assertEqual(a.closure(manifest["candidateFiles"]), a.CANDIDATE)
        self.assertEqual(a.CANDIDATE, "7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748")
        OBSERVATIONS["candidate"] = {"members": 136, "overlays": 15, "treeSHA256": a.CANDIDATE}

    def test_exact_plan_and_environment_strip(self):
        p, e, raw, toolsdir, tools, node, config, out = self.fixture()
        plan = a.command_plan(p, toolsdir, config, node)
        self.assertEqual([s["seconds"] for s in plan], [30, 30, 60, 300, 600, 600])
        self.assertEqual(sum(s["seconds"] for s in plan), 1620)
        self.assertEqual((a.ACTIVE_SECONDS, a.CLEANUP_SECONDS, b.MAX_COMMANDS, b.OUTPUT_CAP, b.AGGREGATE_OUTPUT_CAP),
                         (1800, 60, 6, 8388608, 33554432))
        self.assertEqual(plan[2]["argv"][-15:], [str(p["source"] / n) for n in a.OVERLAYS])
        self.assertEqual(plan[3]["argv"][-6:], ["--all-features", "--all-targets", "--message-format=json", "--", "-D", "warnings"])
        with mock.patch.dict(os.environ, {
            "NODE_OPTIONS": "--require unsafe", "NODE_PATH": "unsafe", "LD_PRELOAD": "unsafe",
            "LD_AUDIT": "unsafe", "DYLD_INSERT_LIBRARIES": "unsafe", "RUSTC_WORKSPACE_WRAPPER": "unsafe",
            "CARGO_ENCODED_RUSTFLAGS": "unsafe", "RUSTDOCFLAGS": "unsafe",
        }, clear=False):
            env = b.environment(a.arm_environment(p, toolsdir, node))
        for n in ("NODE_OPTIONS", "NODE_PATH", "LD_PRELOAD", "LD_AUDIT", "DYLD_INSERT_LIBRARIES",
                  "RUSTC_WORKSPACE_WRAPPER", "CARGO_ENCODED_RUSTFLAGS", "RUSTDOCFLAGS"):
            self.assertNotIn(n, env)
        self.assertEqual(env["MIXER_NODE"], node["path"])

    def test_private_node_directory_injection_refuses_before_launch(self):
        p, e, raw, toolsdir, tools, node, config, out = self.fixture()
        (p["nodebin"] / "node-extra").write_text("unselected")
        spec = a.command_plan(p, toolsdir, config, node)[1]
        c = self.fake_command(spec)
        with self.assertRaisesRegex(RuntimeError, "Private Node directory changed"):
            a.checked_command(c, spec, p, toolsdir, tools, node, e, out, raw, config)
        c.run.assert_not_called()
        self.assertFalse(c.receipt["unregisteredPostflights"][0]["binaryPostflight"]["verified"])

    def test_bad_node_identity_and_two_postflight_failures_keep_primary(self):
        p, e, raw, toolsdir, tools, node, config, out = self.fixture()
        spec = a.command_plan(p, toolsdir, config, node)[1]
        info = {"execPath": "/wrong/node", "version": "v22.20.0", "versions": {"node": "22.20.0"}, "platform": "linux", "arch": "x64"}
        def mutate():
            (p["source"] / "Cargo.toml").write_text("changed source")
            Path(node["path"]).write_text("changed node")
        c = self.fake_command(spec, text=json.dumps(info), mutation=mutate)
        with self.assertRaisesRegex(RuntimeError, "Node identity child mismatch"):
            a.checked_command(c, spec, p, toolsdir, tools, node, e, out, raw, config)
        row = c.receipt["commands"][0]
        self.assertFalse(row["sourcePostflight"]["verified"])
        self.assertFalse(row["binaryPostflight"]["verified"])
        c.save.assert_called_once()

    def test_clippy_failure_retains_diagnostics_and_cannot_admit_tests(self):
        p, e, raw, toolsdir, tools, node, config, out = self.fixture()
        spec = a.command_plan(p, toolsdir, config, node)[3]
        text = json.dumps({"reason": "compiler-message", "message": {"message": "independent fixture", "level": "error", "code": {"code": "clippy::independent"}, "spans": []}}) + "\n" + json.dumps({"reason": "build-finished", "success": False}) + "\n"
        c = self.fake_command(spec, text=text, code=101)
        with self.assertRaisesRegex(RuntimeError, "regression not admitted"):
            a.checked_command(c, spec, p, toolsdir, tools, node, e, out, raw, config)
        evidence = json.loads((out / "clippy-candidate.json").read_text())
        self.assertFalse(evidence["lintPassed"])
        self.assertEqual(len(evidence["diagnostics"]), 1)
        self.assertTrue(c.receipt["commands"][0]["binaryPostflight"]["verified"])

    def test_partial_formatter_failure_retains_fifteen_exact_files(self):
        p, e, raw, toolsdir, tools, node, config, out = self.fixture()
        spec = a.command_plan(p, toolsdir, config, node)[2]
        primary = RuntimeError("independent format failure")
        def mutate():
            (p["source"] / a.OVERLAYS[0]).write_text("partial formatter output\n")
        c = self.fake_command(spec, mutation=mutate, failure=primary)
        with self.assertRaisesRegex(RuntimeError, "independent format failure"):
            a.checked_command(c, spec, p, toolsdir, tools, node, e, out, raw, config)
        for name in a.OVERLAYS:
            self.assertEqual((out / "format/candidate/before" / name).read_bytes(), raw[name])
            self.assertEqual((out / "format/candidate/after" / name).read_bytes(), (p["source"] / name).read_bytes())
        self.assertTrue((out / "formatted-source-manifest.json").is_file())

    def test_formatter_roster_change_fails_before_retention(self):
        p, e, raw, toolsdir, tools, node, config, out = self.fixture()
        spec = a.command_plan(p, toolsdir, config, node)[2]
        c = self.fake_command(spec, mutation=lambda: (p["source"] / "unexpected.rs").write_text("unexpected\n"))
        with self.assertRaisesRegex(RuntimeError, "Formatter source roster changed"):
            a.checked_command(c, spec, p, toolsdir, tools, node, e, out, raw, config)
        self.assertFalse((out / "format/candidate/receipt.json").exists())
        self.assertFalse((out / "format/candidate/before").exists())
        self.assertFalse(c.receipt["commands"][0]["sourcePostflight"]["verified"])
        OBSERVATIONS["formatterRosterRetention"] = {
            "failsClosed": True, "beforeAfterFilesRetained": False,
            "scope": "Unexpected source addition before formatting postflight; custody-safe outer cleanup can remove scratch",
        }

    def test_test_parser_rejects_missing_duplicate_and_ignored_oracles(self):
        self.assertEqual(a.test_evidence(passed_text())["passed"], 699)
        for value in (
            passed_text().replace(a.ORACLES[0], a.ORACLES[1]),
            passed_text().replace("0 ignored", "9 ignored"),
            passed_text().replace("0 failed", "1 failed"),
            passed_text().replace(" ... ok", " ... ignored", 1),
        ):
            with self.assertRaises(RuntimeError):
                a.test_evidence(value)

    def test_test_parser_contradictory_failure_summary_is_not_scanned(self):
        value = passed_text() + "test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n"
        self.assertEqual(a.test_evidence(value)["passed"], 699)
        OBSERVATIONS["contradictorySummary"] = {
            "parserAccepts": True, "managedCargoExitStillMustBeZero": True,
            "scope": "Defensive parser gap only; honest Cargo failure remains rejected by accepted exit (0,)",
        }


if __name__ == "__main__":
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    (HERE / "test-output.txt").write_text(stream.getvalue())
    sys.stderr.write(stream.getvalue())
    record = {
        "schema": 1, "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "guardBeforeSubjectImports": True, "liveApiAttempts": ATTEMPTS,
        "realNestedProcessSessionGroupSignalTimerWaitSocketCalls": 0,
        "RustNodeSwiftElixirCompilerProductRuntimeRuns": 0, "nativeUICaptureRuns": 0,
        "GitGhDispatchActions": 0, "producerPacketWritten": False, "observations": OBSERVATIONS,
        "pythonVersion": sys.version, "scratchRemaining": [p.name for p in HERE.glob("pure-*")],
    }
    (HERE / "controls-result.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    if not result.wasSuccessful():
        raise SystemExit(1)
