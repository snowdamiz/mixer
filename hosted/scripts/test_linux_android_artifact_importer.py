from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hosted" / "priv" / "development"))
from compiler_worker import Refusal, digest, literal
import linux_android_artifact_importer as importer


CAPS = (32 * 1024 * 1024, 16 * 1024 * 1024, 16 * 1024 * 1024)
RECEIPT = ROOT / "verification/receipts/managed-android-linux-retained-products-20261120.json"
RECEIPT_SHA = "6c97dc344d5413fc07d5dd976dfa791e93388b7c33d1af811efc83654f63b89a"


def operator_identity(inputs):
    recipe = digest(literal({"test_recipe": "closed Linux bundle", **asdict(inputs)}).encode())
    ref = dict(organization_id="operator", project_id="pair25", application_id="starter",
               build_id="retained-product-control", platform="android", attempt=1, fence=1)
    spec = dict(ref, source={"sha256": inputs.source_tree_sha256},
                toolchain_lock_sha256=inputs.linux_lock_sha256, build_definition_sha256=recipe)
    identity = ["mixer-build-operation-v1", "import-control", ref["organization_id"], ref["project_id"],
                ref["application_id"], ref["build_id"], ref["platform"], ref["attempt"], ref["fence"]]
    binding = dict(ref=ref, spec=spec, deadline_ms=2_000_000_000_000)
    return dict(operation_id=digest(literal(identity).encode()), binding_sha256=digest(literal(binding).encode()),
                recipe_sha256=recipe, store_id=digest(b"operator import control store"))


def completed(identity, inputs, readback_sha):
    # The fixture operator vouches for success and closure. A runner v1 stop
    # observation cannot construct this result.
    return importer.ClosedLinuxResult(identity.copy(), inputs, readback_sha, 0, True, True, True, True)


class ImportTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="mixer-linux-artifact-test-")
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve()
        self.bundle = self.root / "bundle"
        self.bundle.mkdir(mode=0o700)
        self.apk, self.symbols, self.inventory = (
            "Example-unsigned.apk", "debug-symbols.zip", "resource-inventory.json",
        )
        apk, symbols, lock = b"test apk payload", b"test symbols payload", b"test Linux lock"
        inventory = literal({"formatVersion": 1, "apkSHA256": digest(apk),
                             "debugSymbolsSHA256": digest(symbols)}).encode()
        (self.bundle / "linux-mixer.lock").write_bytes(lock)
        files = (self.apk, self.symbols, self.inventory)
        self.rows = []
        for kind, name, data in zip(importer.KINDS, files, (apk, symbols, inventory), strict=True):
            (self.bundle / name).write_bytes(data)
            self.rows.append(dict(kind=kind, file=name, sizeBytes=len(data), sha256=digest(data)))
        self.inputs = importer.VerifiedLinuxInputs(digest(b"source"), digest(lock), digest(b"driver"))
        self.identity = operator_identity(self.inputs)
        self.operation = self.root / self.identity["operation_id"]
        self.operation.mkdir(mode=0o700)
        self.index = {
            "unsigned": True,
            "zipCRCVerified": True,
            "build": {
                "source_tree_sha256": self.inputs.source_tree_sha256,
                "source_tree_after_sha256": self.inputs.source_tree_sha256,
            },
            "artifacts": self.rows,
        }
        self.terminal = completed(self.identity, self.inputs, self.write_index())
        self.store = self.operation / importer.STORE

    def write_index(self):
        data = literal(self.index).encode()
        (self.bundle / "readback.json").write_bytes(data)
        return digest(data)

    def run_import(self, **overrides):
        args = dict(expected_identity=self.identity, verified_inputs=self.inputs, terminal=self.terminal)
        return importer.import_closed_bundle(self.bundle, self.operation, **(args | overrides))

    def reopen(self, manifest_sha):
        return importer.reopen_linux_artifacts(self.operation, expected_identity=self.identity,
                                                manifest_sha256=manifest_sha)

    def refused(self, *, error="uncertain", **overrides):
        with self.assertRaisesRegex(Refusal, "^" + error + "$"):
            self.run_import(**overrides)
        self.assertEqual([], list(self.operation.iterdir()))

    def test_requires_all_four_runner_identity_fields_and_separate_inputs(self):
        for field in self.identity:
            with self.subTest(field=field):
                other = self.identity | {field: digest(field.encode())}
                self.refused(error="unavailable", terminal=replace(self.terminal, identity=other))
        other_inputs = replace(self.inputs, rendered_driver_sha256=digest(b"other driver"))
        self.refused(error="unavailable", terminal=replace(self.terminal, inputs=other_inputs))
        self.index["identity"] = self.identity
        self.index["terminal"] = {
            "status": "stopped",
            "request": {"identity": self.identity},
            "terminal": {"stop_fenced": True, "container_absent": True,
                         "processes_absent": True, "resources_removed": True},
        }
        self.write_index()
        self.refused(error="unavailable", terminal=self.index["terminal"])

    def test_refuses_failed_exit_or_incomplete_positive_closure(self):
        incomplete = {"exit_code": 1, "start_fenced": False, "container_absent": False,
                      "processes_absent": False, "resources_removed": False}
        for field, value in incomplete.items():
            with self.subTest(field=field):
                self.refused(error="unavailable", terminal=replace(self.terminal, **{field: value}))

    def test_receipt_pin_source_lock_and_payload_digests_are_checked(self):
        readback = self.bundle / "readback.json"
        readback.write_bytes(readback.read_bytes() + b" ")
        self.refused()
        self.write_index()
        lock = self.bundle / "linux-mixer.lock"
        lock.write_bytes(b"wrong Linux lock")
        self.refused()
        lock.write_bytes(b"test Linux lock")
        source = self.index["build"]
        original = source["source_tree_after_sha256"]
        source["source_tree_after_sha256"] = digest(b"modified source")
        self.refused(terminal=replace(self.terminal, readback_sha256=self.write_index()))
        source["source_tree_after_sha256"] = original
        self.write_index()
        (self.bundle / self.symbols).write_bytes(b"test symbols payloae")
        self.refused()

    def test_refuses_artifact_above_each_public_cap(self):
        for row, cap in zip(self.rows, CAPS, strict=True):
            with self.subTest(kind=row["kind"]):
                original = row["sizeBytes"]
                row["sizeBytes"] = cap + 1
                self.refused(terminal=replace(self.terminal, readback_sha256=self.write_index()))
                row["sizeBytes"] = original

    def test_refuses_symlink_and_relative_traversal(self):
        apk = self.bundle / self.apk
        away = self.root / self.apk
        apk.rename(away)
        apk.symlink_to(away)
        self.refused()
        self.rows[0]["file"] = "../" + self.apk
        self.refused(terminal=replace(self.terminal, readback_sha256=self.write_index()))

    def test_truncated_destination_stays_unpublished_and_retry_succeeds(self):
        write = importer.write_owned

        def short_write(path, data):
            if path.name == self.rows[1]["sha256"]:
                data = data[:-1]
            return write(path, data)

        with patch.object(importer, "write_owned", side_effect=short_write):
            self.refused()
        result = self.run_import()
        self.assertEqual(result, self.reopen(result["manifest_sha256"]))
        self.assertEqual(result, self.run_import())

    def test_uncertain_sync_after_publication_preserves_complete_store_for_retry(self):
        sync = importer.sync_directory

        def fail_parent_sync(path):
            if path == self.operation:
                raise OSError("simulated failure to sync the publication")
            sync(path)

        with patch.object(importer, "sync_directory", side_effect=fail_parent_sync), self.assertRaises(Refusal):
            self.run_import()
        inode = self.store.stat().st_ino
        result = self.run_import()
        self.assertEqual(inode, self.store.stat().st_ino)
        self.assertEqual(result, self.reopen(result["manifest_sha256"]))
        self.assertEqual([self.store], list(self.operation.iterdir()))

    def test_reopen_rejects_partial_or_substituted_store(self):
        result = self.run_import()
        pin = result["manifest_sha256"]
        with self.assertRaises(Refusal):
            self.reopen(digest(b"wrong worker manifest"))
        displaced = self.operation / "displaced"
        self.store.rename(displaced)
        shutil.copytree(displaced, self.store)
        with self.assertRaises(Refusal):
            self.reopen(pin)
        shutil.rmtree(self.store)
        displaced.rename(self.store)
        (self.store / self.rows[1]["sha256"]).unlink()
        with self.assertRaises(Refusal):
            self.reopen(pin)
        with self.assertRaises(Refusal):
            self.run_import()
        self.assertEqual([self.store], list(self.operation.iterdir()))

    def test_existing_mac_store_is_preserved(self):
        self.store.mkdir(mode=0o700)
        marker = self.store / "android-build-v1.json"
        marker.write_bytes(b"pre-existing report")
        with self.assertRaises(Refusal):
            self.run_import()
        self.assertEqual([marker], list(self.store.iterdir()))
        self.assertEqual(b"pre-existing report", marker.read_bytes())

    @unittest.skipUnless(os.environ.get("MIXER_PAIR25_BUNDLE"), "requires the operator's retained Pair25 bundle")
    def test_operator_pair25_real_product_readback(self):
        payload = RECEIPT.read_bytes()
        self.assertEqual(RECEIPT_SHA, digest(payload))
        receipt = json.loads(payload)
        bundle = Path(os.environ["MIXER_PAIR25_BUNDLE"])
        inputs = importer.VerifiedLinuxInputs(
            receipt["build"]["source_tree_sha256"], receipt["inputHashes"]["localLinuxLockSHA256"],
            receipt["inputHashes"]["renderedBuildDriverSHA256"],
        )
        identity = operator_identity(inputs)
        terminal = completed(identity, inputs, receipt["readbackChecks"]["readbackSHA256"])
        state = self.root / "pair25-worker"
        state.mkdir(mode=0o700)
        operation = state / identity["operation_id"]
        operation.mkdir(mode=0o700)
        args = dict(expected_identity=identity, verified_inputs=inputs, terminal=terminal)
        write_owned = importer.write_owned
        symbols_sha = receipt["artifacts"][1]["sha256"]

        def short_write(path, data):
            return write_owned(path, data[:-1] if path.name == symbols_sha else data)

        with patch.object(importer, "write_owned", side_effect=short_write), self.assertRaises(Refusal):
            importer.import_closed_bundle(bundle, operation, **args)
        self.assertEqual([], list(operation.iterdir()))
        result = importer.import_closed_bundle(bundle, operation, **args)
        reopened = importer.reopen_linux_artifacts(operation, expected_identity=identity,
                                                    manifest_sha256=result["manifest_sha256"])
        expected = [{k: v for k, v in row.items() if k != "file"} for row in receipt["artifacts"]]
        self.assertEqual(expected, reopened["artifacts"])
        self.assertEqual(result, reopened)
        self.assertEqual([27_804_143, 537_200, 10_317], [row["sizeBytes"] for row in reopened["artifacts"]])
        store = operation / importer.STORE
        self.assertEqual(0o700, stat.S_IMODE(store.stat().st_mode))
        for row in receipt["artifacts"]:
            retained = store / row["sha256"]
            self.assertEqual(0o400, stat.S_IMODE(retained.stat().st_mode))
            self.assertEqual((bundle / row["file"]).read_bytes(), retained.read_bytes())
        print("\nPair25 readback " + literal(reopened), flush=True)


if __name__ == "__main__":
    unittest.main()
