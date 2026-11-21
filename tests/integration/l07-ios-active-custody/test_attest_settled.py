"""Inert admission controls. No network, database server, or subprocess runs."""

import base64
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import attest_settled as step


class ReadyToBuildSigner(Exception):
    """Stop just before the first Go process."""


class SettledAdmissionTests(unittest.TestCase):
    def setUp(self):
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
        output = worker / operation / "native"
        output.mkdir(parents=True)
        manifest = json.dumps(dict(
            formatVersion=2, scope="unsigned-simulator/local-development", commandResult={"exitCode": 0},
            binding=dict(authoritativeSourceDigest=pins[step.PINS[0]], lockSHA256=pins[step.PINS[1]],
                         command=["/usr/bin/xcodebuild", "-sdk", "iphonesimulator",
                                  "-destination", "generic/platform=iOS Simulator",
                                  "CODE_SIGNING_ALLOWED=NO", "build"]),
        )).encode()
        (output / "native-build.json").write_bytes(manifest)
        compiler_digest = "5" * 64
        manifest_digest = step.sha(manifest)
        with closing(sqlite3.connect(worker / "operations.sqlite")) as database, database:
            database.execute("CREATE TABLE operations (id TEXT PRIMARY KEY, value TEXT)")
            database.execute("INSERT INTO operations VALUES (?,?)", (operation, json.dumps(dict(
                binding=row_binding, status="native_ready", starts=1, artifacts=subjects,
                manifest_sha256=manifest_digest, closure=dict(
                    closed=True, exit=0, cli_reaped=True, cli_group_absent=True, commands=[
                        dict(command="/usr/bin/xcodebuild", receipt_sha256=compiler_digest,
                             stop_reason=None, group_terminate_sent=False),
                    ]),
            ))))
        receipt = json.dumps(dict(
            base=step.BASE, xcodeInvocations=1, liveCustodyPending=False,
            liveClosure=dict(xcodeExit=0, xcodeReceiptSHA256=compiler_digest),
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
        self.assertFalse((self.args.run_root / "attestation").exists())

    def test_all_three_downloads_precede_first_go_process(self):
        with self.assertRaises(ReadyToBuildSigner):
            step.prove(self.args)
        self.assertEqual([call.args[1].split("?", 1)[0] for call in self.get.call_args_list], [
            "/console-api/v1/build-attestation-completion",
            *("/console-api/v1/build-artifacts/" + kind for kind in step.KINDS),
        ])
        self.build.assert_called_once_with(self.args.run_root / "attestation")


if __name__ == "__main__":
    unittest.main()
