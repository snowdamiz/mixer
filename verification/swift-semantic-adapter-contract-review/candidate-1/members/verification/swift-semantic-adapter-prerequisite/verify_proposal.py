"""Finite source/custody/declaration/arithmetic checks only; no semantic replay."""
import hashlib
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def read_json(name):
    return json.loads((BASE / name).read_text())

def sha(data):
    return hashlib.sha256(data).hexdigest()

class ProposalChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read_json("input-manifest.json")
        cls.extra = read_json("supplemental-inputs.json")
        cls.rows = cls.manifest["members"] + cls.extra["members"]
        cls.by_path = {r["path"]: r for r in cls.rows}
        cls.contract = read_json("contract.json")
        cls.tests = read_json("test-design.json")

    def test_01_input_snapshot_custody(self):
        self.assertEqual(len(self.rows), 30)
        self.assertEqual(len(self.by_path), 30)
        for row in self.rows:
            raw = (BASE / row["snapshot"]).read_bytes()
            self.assertEqual(len(raw), row["bytes"], row["path"])
            self.assertEqual(sha(raw), row["sha256"], row["path"])
            if not row.get("context_mutable", False):
                self.assertEqual((ROOT / row["path"]).read_bytes(), raw, row["path"])
        tree = "".join("%s\t%d\t%s\n" % (r["path"], r["bytes"], r["sha256"])
                       for r in sorted(self.manifest["members"], key=lambda r:r["path"]))
        self.assertEqual(sha(tree.encode()), self.manifest["consulted_tree_sha256"])

    def test_02_accepted_pack_exact_86_byte_identities(self):
        base = ROOT / "verification/swift-envelope-ci-pack"
        raw = (base / "manifest.json").read_bytes()
        self.assertEqual(sha(raw), self.contract["immutable_inputs"]["pack_manifest_sha256"])
        manifest = json.loads(raw)
        self.assertEqual(len(manifest["members"]), 86)
        expected = {"manifest.json"}
        for row in manifest["members"]:
            relative = Path(row["path"])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            expected.add(row["path"])
            data = (base / relative).read_bytes()
            self.assertEqual(len(data), row["bytes"], row["path"])
            self.assertEqual(sha(data), row["sha256"], row["path"])
        actual = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()}
        self.assertEqual(actual, expected)

    def test_03_exact_source_seams(self):
        seal_row = self.by_path["verification/swift-ordered-retention-analyzer-design/seal.json"]
        seal_raw = (BASE / seal_row["snapshot"]).read_bytes()
        self.assertEqual(sha(seal_raw), "c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8")
        accepted = {r["path"]:r for r in json.loads(seal_raw)["members"]}
        seams = read_json("source-seams.json")["seams"]
        self.assertEqual(len(seams), 14)
        for seam in seams:
            row = self.by_path[seam["path"]]
            raw = (BASE / row["snapshot"]).read_bytes()
            self.assertEqual(sha(raw), seam["source_sha256"])
            self.assertEqual(accepted[seam["path"]]["sha256"], seam["source_sha256"])
            excerpt = b"".join(raw.splitlines(keepends=True)[seam["first_line"]-1:seam["last_line"]])
            self.assertEqual(sha(excerpt), seam["excerpt_sha256"])
            self.assertEqual(excerpt.decode(), seam["excerpt_utf8"])
            self.assertIn("no claim about current live VM", seam["authority"]) if "candidate__" in seam["path"] else None

    def test_04_old_source_declared_caps_and_no_authority(self):
        row = self.by_path["verification/swift-envelope-ci-pack/source/library/analyzer.rs"]
        text = (BASE / row["snapshot"]).read_text()
        for term in ["pub const ARENA_BYTES: usize = 8_388_608;",
                     "pub const TRANSIENT_CAP: usize = 65_536;",
                     "pub const STEP_LIMIT: u64 = 268_435_456;",
                     "pub const REPORT_BYTES: usize = 49_152;",
                     "const RECORD_PREFLIGHT: u64 = 8_192;",
                     "pub const fn full_replay_accepted(&self) -> bool { false }",
                     "pub const fn stored_prefix_validated(&self) -> bool { false }"]:
            self.assertIn(term, text)
        self.assertEqual(self.contract["immutable_inputs"]["new_report_fields"], 0)
        self.assertEqual(self.contract["immutable_inputs"]["new_report_validity_bits"], 0)

    def test_05_proposed_observation_fixed_declarations(self):
        c = self.contract
        self.assertEqual(len(c["observation"]["words"]), 32)
        self.assertEqual(len(set(c["observation"]["words"])), 32)
        self.assertEqual(c["observation"]["bytes"], 32*8)
        self.assertEqual(c["observation"]["words"][26:], ["stored_prefix_validated", "full_replay_accepted", "semantic_metrics_valid", "real_binding_verified", "reserved0", "reserved1"])
        self.assertEqual(set(c["authority"].values()), {False})
        self.assertEqual(c["predicted_new_layouts"]["FixtureCacheStateOutcomeV1"], 104+128+256)
        self.assertFalse(c["predicted_new_layouts"]["verified_by_compiler_in_this_slice"])

    def test_06_disjoint_named_scalar_ownership(self):
        p = self.contract["private_contract"]
        old = set(p["envelope_owned_scalar_indices"])
        new = {int(x) for x in p["semantic_owned_scalar_indices"]}
        self.assertFalse(old & new)
        self.assertTrue(all(0 <= x < 184 for x in old | new))
        self.assertEqual(p["delta_upper"], {"resident_rows":1,"pin_rows":1,"plan_rows":1,"scalar_words":32})
        self.assertFalse(p["other_scalar_mutation_allowed"])

    def test_07_candidate_regions_and_restore_ranges(self):
        end = 0
        for region in self.contract["candidate_regions"]:
            self.assertEqual(region["offset"], end)
            end += region["bytes"]
        self.assertEqual(end, 2048)
        self.assertEqual(984-888, 12*8)
        for cell in self.contract["private_contract"]["envelope_owned_scalar_indices"]:
            self.assertLessEqual(7_729_760+cell*8+8, 8_388_608)
        cleanup = self.contract["private_contract"]["candidate_cleanup"]
        self.assertTrue(cleanup["all_actual_moves_and_lexical_lifetimes_pending"])
        self.assertIn("both leaves disabled", cleanup["unexpected_commit_or_cleanup_fault"])

    def test_08_proposed_work_arithmetic_only(self):
        w = self.contract["work"]
        self.assertEqual(sum(x[1] for x in w["semantic_groups"]), 7680)
        self.assertEqual(471+7680, 8151)
        self.assertEqual(8192-8151, 41)
        self.assertEqual(w["new_combined_record"], 8151)
        self.assertEqual(6446+256+128, w["new_report_work_upper"])
        self.assertLess(w["new_report_work_upper"], 3_000_000)
        self.assertTrue(w["all_ceilings_unverified_against_missing_implementation"])

    def test_09_proposed_memory_arithmetic_only(self):
        m = self.contract["memory"]
        self.assertEqual(m["baseline_complete_union"]+sum(m["extra_groups"].values()), 29344)
        self.assertEqual(sum(m["complete_new_report_roles"].values()), 2896)
        for name, extra in m["extra_groups"].items():
            prior, reserved = m["existing_groups"][name]
            self.assertLessEqual(prior+extra, reserved, name)
        self.assertLessEqual(m["proposed_union"], 41984)
        self.assertFalse(m["uses_unassigned_global_margin"])
        self.assertFalse(m["physical_stack_rss_verified"])

    def test_10_future_test_design_identity_and_raw_width(self):
        t = self.tests
        cases = t["cases"]
        self.assertEqual(len(cases), 52)
        self.assertEqual(len({c["id"] for c in cases}), 52)
        self.assertTrue(t["not_a_test_pass_count"])
        self.assertFalse(t["implementation_runtime_or_native_executed"])
        basic = cases[0]
        self.assertEqual(len(basic["records16"]), 13)
        for index, words in enumerate(basic["records16"], 1):
            self.assertEqual(len(words), 16)
            self.assertEqual(words[0], index)
            self.assertTrue(all(type(v) is int and 0 <= v < 2**64 for v in words))
        self.assertEqual(len(basic["expected"]["observation_words"]), 32)
        self.assertEqual(basic["expected"]["observation_words"][26:], [0]*6)
        self.assertEqual(basic["expected"]["pin_rows"]["1"], [0,2,2,2,11,0])

    def test_11_limited_arithmetic_nonpromise(self):
        w = self.contract["work"]
        self.assertEqual(w["conservative_fixed_nonrecord_allowance"], 5_017_696)
        self.assertEqual((268_435_456-5_017_696)//8151, 32317)
        self.assertEqual(w["arithmetic_record_upper"], 32317)
        self.assertEqual(w["historical_record_charge"], 2_889_656*8151)
        self.assertGreater(w["historical_record_charge"], 268_435_456)

    def test_12_scope_and_pending_diagnostic_declarations(self):
        c = self.contract
        self.assertTrue(c["execution"]["source_checks_only"])
        for key in ["old_model_or_harness_imported", "product_rust_native_target_run", "new_semantic_tests_executed", "root_selection"]:
            self.assertFalse(c["execution"][key])
        self.assertIn("first Failure is terminal ApplicabilityUnavailable", c["private_contract"]["failure"])
        self.assertFalse(c["private_contract"]["dispatch_after_refusal"])
        doc = (ROOT / "docs/swift-semantic-adapter-prerequisite.md").read_text()
        for term in ["32,317", "ApplicabilityUnavailable", "proposed admissible source-work ceilings", "No policy", "no commit or push"]:
            self.assertIn(term, doc)

if __name__ == "__main__":
    unittest.main(verbosity=2)
