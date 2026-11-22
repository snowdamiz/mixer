"""Inert regressions for replay inputs, process settlement, and publication."""

import io
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
import commands
from replay import export_vm, finish, guard_cargo, select_stateful_block, selected_cases


class Held(BaseException):
    pass


class ReplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="standards-replay-inert-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        self.commands = commands.Commands(self.scratch, {
            "PATH": "/usr/bin:/bin", "HOME": str(self.scratch),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        })

    def test_stateful_selection_requires_adjacent_commands_in_the_same_module(self):
        module = {"type": "module", "line": 258, "filename": "commands.6.wasm"}
        mutation = {
            "type": "action", "line": 267,
            "action": {"type": "invoke", "field": "test", "args": []}, "expected": [],
        }
        read = {
            "type": "assert_return", "line": 269,
            "action": {"type": "invoke", "field": "load8_u", "args": [{"type": "i32", "value": "0"}]},
            "expected": [{"type": "i32", "value": "0"}],
        }

        def select(*rows):
            return select_stateful_block(
                {"commands": [module, *rows]}, 258, "commands.6.wasm", (267, 269),
                mutation_line=267,
            )

        self.assertEqual(select(mutation, read), (module, [mutation, read]))
        cases = [
            ([read, mutation], "out of order"),
            ([mutation, {**read, "line": 268}, read], "not adjacent"),
            ([mutation, {**module, "line": 268}, read], "missing or duplicate"),
            ([{**mutation, "type": "assert_return"}, read], "unexpected mutation"),
            ([mutation, {**read, "action": {**read["action"], "module": "other"}}],
             "unexpected assertion"),
        ]
        for rows, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                select(*rows)

    def test_named_invocation_must_match_the_selected_module(self):
        module = {"type": "module", "line": 573, "filename": "commands.1.wasm", "name": "$module1"}
        row = {"type": "assert_trap", "line": 593,
               "action": {"type": "invoke", "field": "call-7", "args": [], "module": "$module1"},
               "text": "uninitialized element"}
        fixture = {"actions": {593: ("assert_trap", "call-7")}, "modules": {573: "unsupported"},
                   "invalid": {}}
        self.assertEqual(list(selected_cases("elem", [module, row], fixture)), [(module, row)])
        mismatched = {**row, "action": {**row["action"], "module": "$other"}}
        with self.assertRaisesRegex(RuntimeError, "unexpected assertion or module context"):
            list(selected_cases("elem", [module, mismatched], fixture))

    def test_signal_during_timeout_settlement_waits_and_proves_group_absence(self):
        child = Mock(pid=123, returncode=-signal.SIGKILL)
        events = []
        child.wait.side_effect = lambda **_: events.append("reaped")
        child.stdout.close.side_effect = lambda: events.append("closed")

        def kill_group(pgid, signum):
            self.assertEqual(pgid, child.pid)
            if signum == signal.SIGKILL:
                events.append("killed")
                self.commands.interrupt(signal.SIGTERM, None)
            else:
                events.append("group absent")
                raise ProcessLookupError

        with patch.object(commands, "OwnedChild", return_value=child), \
                patch.object(commands.os, "killpg", side_effect=kill_group):
            with self.assertRaisesRegex(InterruptedError, f"signal {signal.SIGTERM}"):
                self.commands.run("timeout", ["inert"], timeout=0)
        self.assertEqual(events, ["killed", "reaped", "closed", "group absent"])
        self.assertEqual(self.commands.rows[0]["custody"], "child reaped and group absent")

    def test_interrupted_group_operation_writes_hold_and_retains_scratch(self):
        child = Mock(pid=123)
        with patch.object(commands, "OwnedChild", return_value=child), \
                patch.object(commands.os, "killpg", side_effect=KeyboardInterrupt("inert interrupt")), \
                patch.object(commands.os, "_exit", side_effect=Held) as stop, \
                patch.object(commands.os, "write"):
            with self.assertRaises(Held):
                self.commands.run("timeout", ["inert"], timeout=0)
        stop.assert_called_once_with(74)
        child.wait.assert_not_called()
        hold = json.loads((self.scratch / "HOLD.json").read_text())
        self.assertEqual(hold["command"]["custody"], "unknown")
        self.assertEqual(hold["command"]["pgid"], child.pid)
        self.assertEqual(hold["command"]["problem"], "deadline exceeded")
        self.assertTrue((self.scratch / "timeout.log").is_file())

    def test_competing_receipt_and_failed_write_retain_own_logs_and_custody(self):
        record = {"status": "passed_scoped_replay", "commands": [{"custody": "terminal"}]}
        receipt = self.root / "receipt.json"
        log = self.scratch / "run.log"
        log.write_bytes(b"own output")
        unpublished = self.scratch / "receipt-unpublished.json"
        receipt.write_bytes(b"other run")
        with patch.object(commands.os, "write"), redirect_stderr(io.StringIO()):
            self.assertEqual(finish(self.scratch, receipt, record), 74)
            self.assertEqual(receipt.read_bytes(), b"other run")
            self.assertEqual(log.read_bytes(), b"own output")
            self.assertEqual(json.loads(unpublished.read_text())["commands"], record["commands"])
            unpublished.unlink()
            receipt.unlink()
            with patch.object(commands.os, "fsync",
                              side_effect=[OSError("inert write failure"), None, None]):
                self.assertEqual(finish(self.scratch, receipt, record), 74)
        self.assertFalse(receipt.exists())
        self.assertEqual(log.read_bytes(), b"own output")
        fallback = json.loads(unpublished.read_text())
        self.assertEqual(fallback["commands"], record["commands"])
        self.assertIn("inert write failure", fallback["receipt_publication_error"])

    def test_committed_tree_supplies_examples_and_excludes_live_checkout_inputs(self):
        repo = self.root / "repo"
        repo.mkdir()
        git = ["/usr/bin/git", "-C", repo]
        self.commands.run("init", [*git, "init", "-q"])
        example = repo / "vm/examples/demo.rs"
        example.parent.mkdir(parents=True)
        example.write_text("fn main() {}\n")
        self.commands.run("add", [*git, "add", "vm"])
        self.commands.run("commit", [*git, "-c", "user.name=Replay", "-c",
                                     "user.email=replay@example.invalid", "commit", "-qm", "fixture"])
        example.unlink()
        (example.parent / "untracked.rs").touch()
        record = {}
        source, files = export_vm(self.commands, repo, self.scratch, record)
        self.assertEqual(files, {source / "examples/demo.rs"})
        self.assertEqual((source / "examples/demo.rs").read_text(), "fn main() {}\n")
        self.assertEqual(record["vm_export_files"], 1)

    def test_cargo_guards_both_config_names_workspace_ancestors_and_cargo_home(self):
        cwd = self.root / "outer/build"
        cwd.mkdir(parents=True)
        source = self.scratch / "vm"
        source.mkdir()
        cargo_home = self.scratch / "cargo-home"
        cargo_home.mkdir()
        config = cwd.parent / ".cargo"
        config.mkdir()
        guard_cargo(source, cwd, cargo_home)
        for path, label in ((config / "config", "configuration"),
                            (config / "config.toml", "configuration"),
                            (cargo_home / "config.toml", "configuration"),
                            (self.root / "Cargo.toml", "ancestor manifest")):
            with self.subTest(path=path):
                path.symlink_to(self.root / "missing")
                with self.assertRaisesRegex(RuntimeError, label):
                    guard_cargo(source, cwd, cargo_home)
                path.unlink()

    def test_successful_publication_allows_scratch_cleanup(self):
        receipt = self.root / "receipt.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(finish(self.scratch, receipt, {"status": "passed_scoped_replay"}), 0)
        self.assertTrue(receipt.is_file())
        self.assertFalse(self.scratch.exists())


if __name__ == "__main__":
    unittest.main()
