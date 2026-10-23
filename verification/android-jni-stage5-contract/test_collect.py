"""Failure-only tests of proposal audit logic. No product/native proof is minted."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("stage5_collect", HERE / "collect.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class ProposalAuditTests(unittest.TestCase):
    def setUp(self):
        self.matrix = json.loads((HERE / "acceptance-matrix.json").read_text())
        self.api = json.loads((HERE / "api.json").read_text())
        self.doc = (collector.ROOT / collector.DOC).read_text()
        self.header = (collector.ROOT / "native/android/signed-guest-ui/binding/include/mixer_ui_binding.h").read_text()

    def test_current_inventory(self):
        self.assertEqual(collector.validate_matrix(self.matrix), [])
        self.assertEqual(collector.validate_api(self.api, self.doc, self.header), [])

    def test_missing_case_rejected(self):
        self.matrix["cases"].pop(25)
        self.assertTrue(collector.validate_matrix(self.matrix))

    def test_duplicate_case_rejected(self):
        self.matrix["cases"][2] = copy.deepcopy(self.matrix["cases"][1])
        self.assertTrue(collector.validate_matrix(self.matrix))

    def test_native_success_claim_rejected(self):
        self.matrix["native_android_authority"] = True
        self.matrix["cases"][25]["status"] = "passed"
        self.assertTrue(collector.validate_matrix(self.matrix))

    def test_device_action_rejected(self):
        physical = next(c for c in self.matrix["cases"] if c["scope"] == "physical")
        physical["runner"] = "adb"
        self.assertTrue(collector.validate_matrix(self.matrix))

    def test_descriptor_drift_rejected(self):
        self.api["java_origin_methods"][2]["descriptor"] = "(JLjava/lang/Object;)I"
        self.assertTrue(collector.validate_api(self.api, self.doc, self.header))

    def test_bound_widening_rejected(self):
        self.api["bounds"]["nodes"] = 4096
        self.assertTrue(collector.validate_api(self.api, self.doc, self.header))

    def test_immutable_c_abi_drift_rejected(self):
        header = self.header.replace("uint32_t enabled", "uint64_t enabled")
        self.assertTrue(collector.validate_api(self.api, self.doc, header))

    def test_input_hash_drift_rejected(self):
        lock = json.loads((HERE / "input-lock.json").read_text())
        first = next(iter(lock["files_sha256"]))
        lock["files_sha256"][first] = "0" * 64
        _, errors = collector.validate_lock(lock)
        self.assertTrue(errors)

    def test_missing_input_rejected(self):
        lock = json.loads((HERE / "input-lock.json").read_text())
        lock["files_sha256"]["verification/android-jni-stage5-contract/never-an-input"] = "0" * 64
        _, errors = collector.validate_lock(lock)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
