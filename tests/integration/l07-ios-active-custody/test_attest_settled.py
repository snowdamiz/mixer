"""Inert admission controls. No network, database server, or subprocess runs."""

import base64
from contextlib import closing
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

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
        self.enterContext(patch.object(step.native, "OwnedBuildProcess", side_effect=AssertionError("process")))
        self.enterContext(patch.object(step.subprocess, "check_output", side_effect=AssertionError("subprocess")))
        self.enterContext(patch.object(step.subprocess, "run", side_effect=AssertionError("subprocess")))

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
        self.logs = self.work / "commands/go-build"
        self.child = SimpleNamespace(pid=989898, returncode=None)
        self.launch = self.enterContext(patch.object(step.native, "OwnedBuildProcess", side_effect=self.fake_launch))
        self.waitpid = self.enterContext(patch.object(step.os, "waitpid", return_value=(self.child.pid, 0)))
        self.killpg = self.enterContext(patch.object(step.os, "killpg", side_effect=ProcessLookupError))

    def fake_launch(self, argv, *, stdout, stderr, stdin, **kwargs):
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(json.loads(self.hold.read_bytes())["custody"], "UNKNOWN")
        self.stdin = stdin
        if stdin != step.subprocess.DEVNULL:
            self.assertEqual(os.read(stdin, 1024), b"synthetic-token\n")
        stdout.write(b"partial output\n")
        stderr.write(b"partial diagnostic\n")
        return self.child

    def command(self, *, seconds=1, secret=None):
        return step.run_command(self.work, "go-build", ["go", "build"],
                                env={}, seconds=seconds, secret=secret)

    def test_denied_group_signal_stops_without_probe_or_retry(self):
        self.killpg.side_effect = PermissionError(1, "synthetic denied signal")
        with self.assertRaisesRegex(step.CustodyUnknown, "Preserve") as error:
            self.command(seconds=0, secret=b"synthetic-token\n")
        receipt = json.loads(self.hold.read_bytes())
        self.assertIsInstance(error.exception.__cause__, PermissionError)
        self.assertEqual((receipt["custody"], receipt["pid"], receipt["pgid"], receipt["stop"],
                          receipt["signalOutcome"], receipt["errorType"], receipt["stage"]),
                         ("UNKNOWN", self.child.pid, self.child.pid, "timeout", "denied", "PermissionError",
                          "stop-owned-group"))
        self.assertFalse(receipt["directChildReaped"] or receipt["groupAbsent"])
        self.assertEqual((self.logs / "stdout").read_bytes(), b"partial output\n")
        self.assertEqual((self.logs / "stderr").read_bytes(), b"partial diagnostic\n")
        self.assertNotIn(b"synthetic-token", self.hold.read_bytes())
        with self.assertRaises(OSError):
            os.fstat(self.stdin)
        with self.assertRaisesRegex(RuntimeError, "prior command custody"):
            step.run_command(self.work, "sign", ["inert"], env={}, seconds=1)
        self.launch.assert_called_once()
        self.killpg.assert_called_once_with(self.child.pid, signal.SIGKILL)
        self.waitpid.assert_not_called()

    def test_denied_group_probe_after_exit_zero_preserves_unknown(self):
        self.killpg.side_effect = PermissionError(1, "synthetic denied probe")
        with self.assertRaises(step.CustodyUnknown):
            self.command()
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual((receipt["custody"], receipt["exit"], receipt["errorType"], receipt["stage"]),
                         ("UNKNOWN", 0, "PermissionError", "observe-group-absence"))
        self.assertTrue(receipt["directChildReaped"])
        self.assertFalse(receipt["groupAbsent"] or receipt["signalAttempted"])
        self.killpg.assert_called_once_with(self.child.pid, 0)
        self.waitpid.assert_called_once_with(self.child.pid, os.WNOHANG)

    def test_failed_constructor_has_no_inferred_identity_or_cleanup(self):
        self.launch.side_effect = PermissionError(1, "synthetic launch failure")
        with self.assertRaises(step.CustodyUnknown):
            self.command()
        receipt = json.loads(self.hold.read_bytes())
        self.assertEqual(receipt["custody"], "UNKNOWN")
        self.assertNotIn("pid", receipt)
        self.waitpid.assert_not_called()
        self.killpg.assert_not_called()

    def test_signal_then_positive_closure_still_refuses_timeout(self):
        self.killpg.side_effect = [None, ProcessLookupError()]
        self.waitpid.return_value = (self.child.pid, signal.SIGKILL)
        with self.assertRaisesRegex(RuntimeError, "exceeded its budget"):
            self.command(seconds=0)
        receipt = json.loads((self.logs / "result.json").read_bytes())
        self.assertEqual((receipt["custody"], receipt["exit"], receipt["stop"], receipt["signalOutcome"]),
                         ("TERMINAL", -signal.SIGKILL, "timeout", "sent"))
        self.assertTrue(receipt["directChildReaped"] and receipt["groupAbsent"] and receipt["descriptorsClosed"])
        self.assertFalse(self.hold.exists())
        self.assertEqual(self.killpg.call_args_list, [call(self.child.pid, signal.SIGKILL), call(self.child.pid, 0)])


if __name__ == "__main__":
    unittest.main()
