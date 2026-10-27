"""One-time mechanical migration into OWN directory; never edits frozen inputs.

Explicit API adaptations are documented in README; original packets remain input.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract"
REVIEW = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-independent"
assert not (HERE / "test_legacy.py").exists()
raw = (OLD / "test_model.py").read_bytes()
text = raw.decode()
start = text.index("def policy(")
end = text.index("class ModelTests", start)
text = text[:start] + '''from helpers import policy, reservation, handle, complete_owner, own_handle, selected_result
from model import AllocationContract


def adopted(data=b"abc", **kw):
    # Fixture name retained; safe adoption now needs the actual paid owner.
    return handle(data, **kw)


def read_owned(paid, h, *args, **kw):
    if not paid.outcome.adoption_started:
        own_handle(paid, h)
    return acquire_body(paid, h, *args, **kw)


''' + text[end:]
# Read-only flags can no longer fabricate File ownership. Each ordinary reader
# explicitly installs and adopts all13 slots with the reservation first.
text = text.replace("acquire_body(paid,", "read_owned(paid,")
text = text.replace("def read_owned(paid,", "def read_owned(paid,")
text = text.replace("return read_owned(paid, h,", "return acquire_body(paid, h,")
# The unadopted negative must retain direct call semantics.
text = text.replace('read_owned(paid, handle(), "source", 100)', 'acquire_body(paid, handle(), "source", 100)')
text = text.replace("root.reserve(work, storage)", "root.reserve(work, storage, cleanup_work=1)")
text = text.replace("root.reserve(1, 1)", "root.reserve(1, 1, cleanup_work=1)")
text = text.replace("TestFileIdentity(11, 2, 3, False)", "TestFileIdentity(11, 2, 3, mode=0)")
text = text.replace("TestFileIdentity(11, 1, 3, False)", "TestFileIdentity(11, 1, 3, mode=0)")
text = text.replace("metadata_version=2", "mtime_ns=2")
text = text.replace("self.assertEqual(paid.owned, [])", "self.assertFalse(any(type(b) is TestBody for b in paid.owned))")
text = text.replace("allocation_bound=4", "allocation_contract=AllocationContract(3, 1)")
text = text.replace("self.assertEqual(len(paid.owned), 1)", "self.assertEqual(len([b for b in paid.owned if type(b) is TestBody]), 1)")
text = text.replace('root.used_work, root.used_storage, root.peak), (1000000, 0, 1000000)',
                    'root.used_work, root.used_storage, root.peak), (1001000, 0, 1000000)')
text = text.replace("r.reserve(100000, 100000)", "r.reserve(99000, 100000, cleanup_work=1000)")
start = text.index('        expected = {"source":')
end = text.index("\n    def test_storage_held", start)
text = text[:start] + '''        expected = view.correspondence.mapping()
        for field in expected:
            # Each attempt consumes its own owner, including a refusal.
            _, trial = reservation()
            bs, ps = complete_owner(trial)
            admitted = admit_model_only(trial, bs, ps, trusted_local_launch_contract=True,
                all_actual_correspondence=True, review_provenance=True)
            changed = admitted.correspondence.mapping()
            changed[field] = None
            selected = selected_result(trial, admitted, changed)
            with self.assertRaises(Refused): correlate_before_leaf(trial, admitted, selected)
            self.assertNotIn("leaf-model-only", trial.effects)
        self.assertIn("model leaf", correlate_before_leaf(paid, view, selected_result(paid, view)))
''' + text[end:]
# Reservation/adoption refusal now retains its ORIGINAL diagnostic. Atomicity
# means counters/effects unchanged, not destruction of the new failure object.
# Already-owning File resources are expected in the roster before body reads.
(HERE / "test_legacy.py").write_text(text)

raw_review = (REVIEW / "review_controls.py").read_bytes()
text2 = raw_review.decode()
start = text2.index('spec = importlib.util.spec_from_file_location')
end = text2.index('MAX = ', start)
text2 = text2[:start] + 'import model\nfrom helpers import own_handle, admitted_owner\n' + text2[end:]
start = text2.index('def candidate_paid():')
end = text2.index('\n\nclass IndependentControls', start)
text2 = text2[:start] + '''def candidate_paid():
    from helpers import reservation
    return reservation()


def candidate_owner(paid):
    return admitted_owner(paid)
''' + text2[end:]
text2 = text2.replace("            h.adopted = True", "            own_handle(paid, h)")
text2 = text2.replace('; h.adopted = True', '; own_handle(paid, h)')
text2 = text2.replace('allocation_bound=4', 'allocation_contract=model.AllocationContract(3, 1)')
# Original sixteen independent methods and four returned desired-property names
# stay present. The sixteen specification controls use the original contract.
(HERE / "test_independent_migrated.py").write_text(text2)

for path in ("contract.json", "interface.inc.rs"):
    (HERE / path).write_bytes((OLD / path).read_bytes())
interface = (HERE / "interface.inc.rs").read_text()
interface = interface.replace("    // -> scoped shared binding -> reserve all6 child components -> output setup\n    // -> SAME-handle loader/leaf -> consume original result -> end all views",
    "    // -> scoped shared binding -> reserve all6 child components\n    // -> existing setup/loader opens -> private admitted-owner correlation\n    // -> leaf only after complete correlation -> consume result -> end all views\n    // SAME-handle loading above is OPTIONAL, a larger unselected route.")
interface = interface.replace("        total_work: u64,", "        acquisition_work: u64,\n        cleanup_work: u64, // separately unavailable to acquisition, reserved first")
interface = interface.replace("    enum AcquisitionOutcomeV1 {", "    // One affine carrier includes all13 raw/validated/adopted/retired slots,\n    // adoption bitmap, every partial File and path-packet owner/buffer. Raw slots\n    // without reviewed safe retirement retain the ENTIRE reservation; no close.\n    enum AcquisitionOutcomeV1 {")
interface = interface.replace("        expected: &AdmittedLoaderCorrespondenceV1,", "        expected: &AdmittedLoaderCorrespondenceV1, // private verified-owner derivation only")
(HERE / "interface.inc.rs").write_text(interface)
report = {"old_test_sha256": hashlib.sha256(raw).hexdigest(),
          "review_controls_sha256": hashlib.sha256(raw_review).hexdigest(),
          "legacy_method_names_preserved": text.count("    def test_"),
          "independent_control_and_desired_method_names_preserved": text2.count("    def test_"),
          "edits": "only own-directory files; safe owning fixture API; full FileIdentity64 fields; separately reserved cleanup; consuming complete provenance; explicit original coverage retained"}
(HERE / "test-migration.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
