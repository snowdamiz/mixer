"""Inert admission and process controls. No product services or native tools."""

import base64
from contextlib import closing, redirect_stderr
import io
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import attest_settled as step
from live import CLOSED_FACTS

V74_COMPILER_WORKER = sys.modules["compiler_worker"]


class ReadyToBuildSigner(Exception):
    """Stop just before the first Go process."""


class SettledAdmissionTests(unittest.TestCase):
    def setUp(self):
        # The adjacent live tests load an older compiler worker under this name.
        self.enterContext(patch.dict(sys.modules, compiler_worker=V74_COMPILER_WORKER))
        parent = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        root = parent / "run"
        root.mkdir(mode=0o700)
        self.args = SimpleNamespace(run_root=root, api_port=18431)
        spki = bytes.fromhex("302a300506032b6570032100") + b"k" * 32
        self.args.enrolled_spki_sha256 = step.sha(spki)
        for key, data in {
            "session": b"A" * 43,
            "bearer": b"synthetic.jwt.fixture",
            "private_key": b"inert",
            "public_key": b"-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(spki)
            + b"\n-----END PUBLIC KEY-----\n",
        }.items():
            path = parent / key
            path.write_bytes(data)
            path.chmod(0o600)
            setattr(self.args, key, path)

        scope = dict(zip(step.IDS, ("org", "project", "app", "build", "ios"), strict=True))
        pins = dict(zip(step.PINS, ("1" * 64, "2" * 64, "3" * 64), strict=True))
        spec = scope | {k: pins[k] for k in step.PINS[1:]} | {
            "source": dict(kind="revision", reference="starter-fixture", sha256=pins[step.PINS[0]]),
        }
        ref = scope | {"attempt": 1, "fence": 1}
        record = "b607b0d8-dc90-4c28-9182-fd5c1ed72d21"
        operation = step.sha(json.dumps(
            ["mixer-build-operation-v1", record, *scope.values(), 1, 1], separators=(",", ":"),
        ).encode())
        row_binding = dict(spec=spec, ref=ref, deadline_ms=1000)
        subjects = []
        self.bodies = {}

        def add(kind, body):
            subjects.append(dict(kind=kind, sha256=step.sha(body), sizeBytes=len(body)))
            self.bodies["/console-api/v1/build-artifacts/" + kind] = body

        app, symbols, inventory = step.KINDS
        add(app, b"inert app")
        add(symbols, b"inert symbols")
        add(inventory, json.dumps(dict(version=1, kind=inventory, parentApp=subjects[0],
                                      parentSymbols=subjects[1], bindingSHA256="4" * 64)).encode())

        journal = [
            dict(id="coordinator:1:0:start", now_ms=10, event=dict(type="start", ref=ref)),
            dict(id="coordinator:1:1:completed", now_ms=20, event=dict(
                type="completed", ref=ref, result=dict(outcome="native_succeeded", artifacts=[
                    dict(kind=a["kind"], sha256=a["sha256"], size_bytes=a["sizeBytes"]) for a in subjects
                ]),
            )),
        ]
        self.snapshot = dict(
            scope=list(scope.values()), revision=2, journal=dict(creation={"spec": spec}, events=journal),
            reservation=[1, 1, False, journal[-1]["id"]], dataDirectory=str(root / "pg"),
            leaseClosed=True, attachments=[],
        )
        selection = dict(zip(step.WIRE, (scope | pins).values(), strict=True))
        query = step.urlencode(scope | pins)
        detail = selection | dict(state="native_succeeded", revision=2, attempt=1,
                                  workerOperationId=operation, workerCompletionPending=False,
                                  artifacts=[a | {"downloadPath":
                                      "/console-api/v1/build-artifacts/" + a["kind"] + "?" + query}
                                             for a in subjects])
        self.bodies["/console-api/v1/build-attestation-completion"] = json.dumps({"build": detail}).encode()

        worker = root / "worker"
        output = worker / operation
        output.mkdir(parents=True, mode=0o700)
        native = output / "native"
        native.mkdir(mode=0o700)
        project, tmp = output / "project", output / "tmp"
        project.mkdir(mode=0o700)
        tmp.mkdir(mode=0o700)
        config = b'{"name":"Starter"}'
        (project / "mixer.yml").write_bytes(config)
        inputs = {"mixer.yml": step.sha(config)}
        xcode = step.ios.retained_xcode_command(step.native, project, inputs)
        receipt_root = "mixer-command-receipts-00000000-0000-0000-0000-000000000001"
        (tmp / "cli-closed").write_text(receipt_root)
        (tmp / receipt_root).mkdir(mode=0o700)
        commands = []
        for pid, argv in enumerate((["/usr/bin/swift", "--version"], xcode), start=201):
            receipt_dir = tmp / receipt_root / f"command-00000000-0000-0000-0000-{pid:012}"
            receipt_dir.mkdir(mode=0o700)
            command_receipt = dict(schema="mixer.owned-command.2", state="TERMINAL", released=True,
                                   pid=pid, ownedPGID=pid, ownedSession=pid, command=argv,
                                   directory=str(project), exitCode=0, runtimeStartedNS=2*pid, terminalNS=2*pid+1,
                                   **dict.fromkeys(CLOSED_FACTS, True))
            raw = json.dumps(command_receipt).encode()
            self.compiler_receipt = receipt_dir / "receipt.json"
            self.compiler_receipt.write_bytes(raw)
            commands.append(dict(command=argv[0], pid=pid, receipt_sha256=step.sha(raw),
                                 stop_reason=None, group_terminate_sent=False))
        compiler_digest = commands[-1]["receipt_sha256"]
        launch = dict(pid=102, pgid=102, sid=102)
        terminal = dict(outer=launch | dict(parent_pid=101, exit=0, direct_child_reaped=True,
                                           group_absent=True, descriptors_closed=True),
                        nested=dict(receipt_root=receipt_root,
                                    receipt_sha256s=[cmd["receipt_sha256"] for cmd in commands]),
                        outcome="succeeded")
        guard = {"owner_id": "fixture-owner", "expires_at": 500}
        intent = dict(guard=guard, recipe={"inputs": inputs}, configuration="6" * 64)
        plan = step.sha(step.native.literal(dict(operation_id=operation, binding=row_binding, intent=intent)).encode())
        manifest = json.dumps(dict(
            formatVersion=2, scope="unsigned-simulator/local-development", commandResult={"exitCode": 0},
            binding=dict(authoritativeSourceDigest=pins[step.PINS[0]], lockSHA256=pins[step.PINS[1]],
                         command=xcode),
        )).encode()
        (native / "native-build.json").write_bytes(manifest)
        manifest_digest = step.sha(manifest)
        self.ledger = worker / "operations.sqlite"
        self.operation = operation
        self.subjects = subjects
        self.selection = selection
        self.original_claim = (plan, 101, json.dumps(terminal))
        with closing(sqlite3.connect(self.ledger)) as database, database:
            database.execute("CREATE TABLE operations (id TEXT PRIMARY KEY, value TEXT)")
            database.execute("""CREATE TABLE ios_custody_claims (
                operation TEXT PRIMARY KEY, plan_sha256 TEXT NOT NULL, guard TEXT NOT NULL,
                parent_pid INTEGER NOT NULL, launch TEXT, terminal TEXT,
                uncertain INTEGER NOT NULL DEFAULT 0) WITHOUT ROWID""")
            database.execute("INSERT INTO operations VALUES (?,?)", (operation, json.dumps(dict(
                binding=row_binding, status="native_ready", starts=1, artifacts=subjects,
                ios_custody=intent, manifest_sha256=manifest_digest, closure=dict(
                    closed=True, started=True, pid=102, exit=0, cli_reaped=True, cli_group_absent=True,
                    ios_outcome="succeeded", ios_custody=terminal, commands=commands),
            ))))
            database.execute("INSERT INTO ios_custody_claims VALUES (?,?,?,?,?,?,0)",
                             (operation, plan, step.native.literal(guard), 101, json.dumps(launch), json.dumps(terminal)))
        receipt = json.dumps(dict(
            base=step.BASE, xcodeInvocations=1, liveCustodyPending=False,
            liveClosure=dict(xcodeExit=0, xcodeReceiptSHA256=compiler_digest, claim=terminal),
            commands={name: dict(exit=0, groupAbsent=True) for name in ("worker", "processor")},
            binding=row_binding | {"record_id": record, "operation_id": operation},
            settled=dict(artifacts=subjects, journal=journal, manifestSHA256=manifest_digest),
        )).encode()
        (root / "settlement.json").write_bytes(receipt)
        (root / "settlement.json").chmod(0o600)
        self.args.settlement_sha256 = step.sha(receipt)
        self.postgres = self.enterContext(patch.object(step, "inspect_postgres", return_value=self.snapshot))
        self.get = self.enterContext(patch.object(step, "get", side_effect=self.fixture_get))
        self.build = self.enterContext(patch.object(step, "build_signer", side_effect=ReadyToBuildSigner))
        self.enterContext(patch.object(step.os, "fork", side_effect=AssertionError("process")))

    def fixture_get(self, port, target, token, media, limit):
        self.assertEqual((port, token), (self.args.api_port, "A" * 43))
        return self.bodies[target.split("?", 1)[0]]

    def test_unpinned_settlement_makes_no_requests(self):
        self.args.settlement_sha256 = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "settlement receipt digest differs"):
            step.prove(self.args)
        self.postgres.assert_not_called()
        self.get.assert_not_called()
        self.build.assert_not_called()

    def test_invalid_last_download_cannot_start_signer(self):
        self.bodies["/console-api/v1/build-artifacts/resource_inventory"] = b"corrupt last download"
        with self.assertRaisesRegex(RuntimeError, "download differs"):
            step.prove(self.args)
        self.assertEqual(self.get.call_count, 4)
        self.build.assert_not_called()
        self.assertFalse((self.args.run_root / "attestation/expected-statement.json").exists())

    def test_all_three_downloads_precede_first_go_process(self):
        with self.assertRaises(ReadyToBuildSigner):
            step.prove(self.args)
        self.assertEqual([call.args[1].split("?", 1)[0] for call in self.get.call_args_list], [
            "/console-api/v1/build-attestation-completion",
            *("/console-api/v1/build-artifacts/" + kind for kind in step.KINDS),
        ])
        self.build.assert_called_once_with(self.args.run_root / "attestation")

    def test_uncertain_claim_refuses_even_with_ready_worker(self):
        with closing(sqlite3.connect(self.ledger)) as database, database:
            database.execute("UPDATE ios_custody_claims SET uncertain=1, terminal=NULL")
        self.assert_claim_refused()

    def test_positive_terminal_cannot_override_uncertain_flag(self):
        with closing(sqlite3.connect(self.ledger)) as database, database:
            database.execute("UPDATE ios_custody_claims SET uncertain=1")
        self.assert_claim_refused()

    def test_other_operations_claim_does_not_authorize(self):
        with closing(sqlite3.connect(self.ledger)) as database, database:
            database.execute("UPDATE ios_custody_claims SET operation=?", ("e" * 64,))
        self.assert_claim_refused()

    def test_launch_plan_and_outer_closure_must_match(self):
        with closing(sqlite3.connect(self.ledger)) as database:
            for sql in ("plan_sha256=hex(randomblob(32))", "parent_pid=103",
                        "terminal=json_set(terminal, '$.outer.group_absent', json('false'))"):
                with self.subTest(sql=sql):
                    database.execute("UPDATE ios_custody_claims SET " + sql)
                    database.commit()
                    self.assert_claim_refused()
                    # Restore the original claim before changing another binding.
                    database.execute("UPDATE ios_custody_claims SET plan_sha256=?, parent_pid=?, terminal=?",
                                     self.original_claim)
                    database.commit()

    def test_terminal_nested_receipt_bytes_must_match(self):
        with self.compiler_receipt.open("ab") as stream:
            stream.write(b"\n")
        self.assert_claim_refused()

    def assert_claim_refused(self):
        with self.assertRaisesRegex(RuntimeError, "worker custody claim"):
            step.prove(self.args)
        self.postgres.assert_not_called()
        self.get.assert_not_called()
        self.build.assert_not_called()
        self.assertFalse((self.args.run_root / "attestation").exists())

    def test_admitted_input_reaches_only_guarded_sign(self):
        self.build.side_effect = None
        self.build.return_value = (self.args.run_root / "attestation/mixer-native-attest", "inert go")
        with patch.object(step, "run_command", side_effect=RuntimeError("stock refused")) as command:
            with self.assertRaisesRegex(RuntimeError, "stock refused"):
                step.prove(self.args)
        command.assert_called_once()
        work, name, args = command.call_args.args
        self.assertEqual(name, "sign")
        self.assertEqual(args[-2:], ["-expected-statement", work / "expected-statement.json"])
        expected = json.loads(args[-1].read_bytes())
        self.assertEqual(args[-1].stat().st_mode & 0o777, 0o400)
        self.assertEqual(expected, dict(profile=step.PROFILE, origin="http://127.0.0.1:18431",
                                        keyId=self.args.enrolled_spki_sha256, selection=self.selection,
                                        provenance=dict(journalRevision=2, attempt=1, nativeBindingSha256="4" * 64,
                                                        workerOperationId=self.operation), subjects=self.subjects))
        self.postgres.assert_called_once()


class CommandCustodyTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.work = root / "attestation"
        self.work.mkdir(mode=0o700)
        self.hold = root / "HOLD.json"
        self.logs = self.work / "commands/control"

    def command(self, source="pass", *, seconds=4, secret=None, name="control"):
        return step.run_command(self.work, name, [sys.executable, "-I", "-c", source],
                                env={}, seconds=seconds, secret=secret)

    def test_token_stdin_after_durable_admission(self):
        token = b"synthetic-token\n"
        # The control checks the received bytes without echoing them, and
        # verifies the actual tool is the group leader recorded before exec.
        output = self.command(f"""
import hashlib, json, os, sys
from pathlib import Path
r = json.loads(Path({str(self.hold)!r}).read_bytes())
assert r["custody"] == "UNKNOWN" and r["stage"] == "await-exec"
assert r["pid"] == r["pgid"] == os.getpid() == os.getpgrp() == os.getsid(0)
assert hashlib.sha256(sys.stdin.buffer.read()).hexdigest() == {step.sha(token)!r}
print("admitted")
""", secret=token)
        self.assertEqual(output, b"admitted\n")
        for path in self.logs.iterdir():
            self.assertNotIn(token.rstrip(), path.read_bytes())
        self.assert_terminal()

    def assert_terminal(self):
        self.assertFalse(self.hold.exists())
        receipt = json.loads((self.logs / "result.json").read_bytes())
        self.assertEqual(receipt["custody"], "TERMINAL")
        self.assertTrue(all(receipt[field] for field in
                            ("execPipeEOF", "directChildReaped", "groupAbsent", "descriptorsClosed",
                             "stdoutEOF", "stderrEOF")))
        return receipt

    def test_exec_stall_cuts_off_and_preserves_unknown(self):
        marker = self.work / "inert-exec-entered"

        def stalled_exec(*args):
            marker.touch()
            time.sleep(8)
            os._exit(126)

        start = time.monotonic()
        with patch.object(step.os, "execvpe", side_effect=stalled_exec):
            with self.assertRaisesRegex(step.CustodyUnknown, "Preserve"):
                self.command(seconds=1)
        self.assertLess(time.monotonic() - start, 4)
        self.assertTrue(marker.is_file())
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["stage"], receipt["stop"]),
                         ("UNKNOWN", "await-exec", "timeout"))
        self.assertEqual(receipt["pgid"], receipt["pid"])
        self.assertTrue(receipt["directChildReaped"] and receipt["groupAbsent"] and receipt["descriptorsClosed"])
        self.assertFalse(receipt["execPipeEOF"])
        self.assertFalse((self.logs / "result.json").exists())
        with self.assertRaisesRegex(RuntimeError, "prior command custody"):
            self.command()

    def test_slow_admission_cannot_release_a_command(self):
        save_record = step.save_record

        def delayed_save(path, value):
            save_record(path, value)
            if path == self.hold and "pid" not in value:
                time.sleep(0.15)

        with (patch.object(step, "save_record", side_effect=delayed_save),
              patch.object(step.os, "fork") as fork):
            with self.assertRaises(step.CustodyUnknown) as error:
                self.command(seconds=0.1)
            self.assertRegex(str(error.exception.__cause__), "admission exceeded")
            fork.assert_not_called()

    def test_session_stall_never_signals_an_unconfirmed_group(self):
        pipes = []
        real_pipe = os.pipe
        pid = 989898

        def record_pipe():
            pipes.append(real_pipe())
            return pipes[-1]

        def fake_fork():
            launch_writer = os.dup(pipes[1][1])
            self.addCleanup(os.close, launch_writer)
            return pid

        with (patch.object(step.os, "pipe", side_effect=record_pipe),
              patch.object(step.os, "fork", side_effect=fake_fork),
              patch.object(step.os, "waitpid") as waitpid,
              patch.object(step.os, "killpg") as killpg):
            with self.assertRaises(step.CustodyUnknown):
                self.command(seconds=0.25)
            waitpid.assert_not_called()
            killpg.assert_not_called()
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["pid"], receipt["stage"], receipt["stop"]),
                         ("UNKNOWN", pid, "await-session", "timeout"))
        self.assertNotIn("pgid", receipt)

    def test_fast_overrun_has_hard_cap_on_each_stream(self):
        for fd in (1, 2):
            with self.subTest(fd=fd):
                name = f"control-{fd}"
                self.logs = self.work / "commands" / name
                with self.assertRaisesRegex(RuntimeError, "exceeded its budget"):
                    self.command(f"""
import os
for _ in range(256):
    os.write({fd}, b"x" * 65536)
""", name=name)
                receipt = self.assert_terminal()
                stream = "stdout" if fd == 1 else "stderr"
                other_stream = "stderr" if fd == 1 else "stdout"
                self.assertEqual((receipt["stop"], receipt["outputLimitExceeded"]), ("output-limit", True))
                self.assertEqual((self.logs / stream).read_bytes(), b"x" * step.COMMAND_LOG_LIMIT)
                self.assertEqual(receipt["logBytes"], {stream: step.COMMAND_LOG_LIMIT, other_stream: 0})

    def test_exact_output_cap_is_accepted(self):
        self.assertEqual(self.command(f"""
import sys
sys.stdout.buffer.write(b"x" * {step.COMMAND_LOG_LIMIT})
"""), b"x" * step.COMMAND_LOG_LIMIT)
        self.assertFalse(self.assert_terminal()["outputLimitExceeded"])

    def test_denied_group_signal_stops_without_probe_or_retry(self):
        pipes = []
        real_pipe = os.pipe
        pid = 989898

        def record_pipe():
            pipes.append(real_pipe())
            return pipes[-1]

        def fake_fork():
            gate, launch, stdout, stderr, _ = pipes
            reader = os.dup(gate[0])
            self.addCleanup(os.close, reader)
            os.write(launch[1], b"R")
            os.write(stdout[1], b"partial output\n")
            os.write(stderr[1], b"partial diagnostic\n")
            return pid

        token = b"synthetic-token\n"
        with (patch.object(step.os, "pipe", side_effect=record_pipe),
              patch.object(step.os, "fork", side_effect=fake_fork),
              patch.object(step.os, "waitpid", return_value=(0, 0)),
              patch.object(step.os, "killpg", side_effect=PermissionError("synthetic denial")) as killpg):
            with self.assertRaises(step.CustodyUnknown) as error:
                self.command(seconds=0.25, secret=token)
            self.assertIsInstance(error.exception.__cause__, PermissionError)
            killpg.assert_called_once_with(pid, signal.SIGKILL)
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["pid"], receipt["pgid"], receipt["stop"],
                          receipt["signalOutcome"], receipt["errorType"], receipt["stage"]),
                         ("UNKNOWN", pid, pid, "timeout", "denied", "PermissionError", "stop-owned-group"))
        self.assertFalse(receipt["directChildReaped"] or receipt["groupAbsent"])
        self.assertEqual((self.logs / "stdout").read_bytes(), b"partial output\n")
        self.assertEqual((self.logs / "stderr").read_bytes(), b"partial diagnostic\n")
        self.assertNotIn(token.rstrip(), self.hold.read_bytes())

    def test_denied_group_probe_after_exit_zero_preserves_unknown(self):
        with patch.object(step.os, "killpg", side_effect=PermissionError("synthetic denial")) as killpg:
            with self.assertRaises(step.CustodyUnknown):
                self.command()
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["exit"], receipt["errorType"], receipt["stage"]),
                         ("UNKNOWN", 0, "PermissionError", "observe-group-absence"))
        self.assertTrue(receipt["directChildReaped"])
        self.assertFalse(receipt["groupAbsent"] or receipt["signalAttempted"])
        killpg.assert_called_once_with(receipt["pid"], 0)

    def test_failed_fork_has_no_inferred_identity_or_cleanup(self):
        with (patch.object(step.os, "fork", side_effect=OSError("synthetic launch failure")),
              patch.object(step.os, "waitpid") as waitpid,
              patch.object(step.os, "killpg") as killpg):
            with self.assertRaises(step.CustodyUnknown):
                self.command()
            waitpid.assert_not_called()
            killpg.assert_not_called()
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual(receipt["custody"], "UNKNOWN")
        self.assertNotIn("pid", receipt)

    def test_signal_then_positive_closure_still_refuses_timeout(self):
        with self.assertRaisesRegex(RuntimeError, "exceeded its budget"):
            self.command("import time; time.sleep(8)", seconds=1)
        receipt = self.assert_terminal()
        self.assertEqual((receipt["custody"], receipt["exit"], receipt["stop"], receipt["signalOutcome"]),
                         ("TERMINAL", -signal.SIGKILL, "timeout", "sent"))

    def test_late_group_absence_refuses_timeout_but_records_terminal(self):
        group_absent = step.group_absent
        started = time.monotonic()

        def delayed_observation(pid):
            absent = group_absent(pid)
            if absent:
                time.sleep(max(0, started + 1.34 - time.monotonic()))
            return absent

        with patch.object(step, "group_absent", side_effect=delayed_observation):
            with self.assertRaisesRegex(RuntimeError, "exceeded its budget"):
                self.command(seconds=1)
        receipt = self.assert_terminal()
        self.assertEqual((receipt["exit"], receipt["stop"], receipt["signalAttempted"]),
                         (0, "timeout", False))

    def test_interrupted_go_group_does_not_prove_nested_closure(self):
        with self.assertRaises(step.CustodyUnknown):
            self.command("import time; time.sleep(8)", seconds=1, name="go-build")
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["stage"], receipt["stop"]),
                         ("UNKNOWN", "observe-go-descendants", "timeout"))
        self.assertTrue(receipt["directChildReaped"] and receipt["groupAbsent"])
        self.assertFalse((self.work / "commands/go-build/result.json").exists())

    def test_nonzero_go_exit_preserves_root_hold_and_cli_exit_74(self):
        argv = ["attest_settled.py", "--run-root", str(self.work.parent),
                "--api-port", "18431", "--pg-port", "18432",
                "--settlement-sha256", "0" * 64, "--enrolled-spki-sha256", "1" * 64]
        for name in ("session", "bearer", "private-key", "public-key"):
            argv.extend(("--" + name, str(self.work.parent / name)))
        self.addCleanup(os.umask, os.umask(0o077))
        with (patch.object(sys, "argv", argv),
              patch.object(step, "prove", side_effect=lambda args: self.command(
                  "raise SystemExit(7)", name="go-build")),
              redirect_stderr(io.StringIO()) as stderr):
            self.assertEqual(step.main(), 74)
        self.assertIn(f"Preserve {self.work.parent}", stderr.getvalue())
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["stage"], receipt["exit"], receipt["signalAttempted"]),
                         ("UNKNOWN", "observe-go-descendants", 7, False))
        self.assertTrue(all(receipt[field] for field in
                            ("execPipeEOF", "directChildReaped", "groupAbsent", "descriptorsClosed",
                             "stdoutEOF", "stderrEOF")))
        self.assertFalse((self.work / "commands/go-build/result.json").exists())

    def test_zero_go_exit_still_records_terminal(self):
        self.logs = self.work / "commands/go-build"
        self.assertEqual(self.command("print('built')", name="go-build"), b"built\n")
        self.assertEqual(self.assert_terminal()["exit"], 0)

    def test_nonzero_other_tool_still_records_terminal(self):
        with self.assertRaisesRegex(RuntimeError, "control failed or exceeded its budget"):
            self.command("raise SystemExit(7)")
        self.assertEqual(self.assert_terminal()["exit"], 7)


if __name__ == "__main__":
    unittest.main()
