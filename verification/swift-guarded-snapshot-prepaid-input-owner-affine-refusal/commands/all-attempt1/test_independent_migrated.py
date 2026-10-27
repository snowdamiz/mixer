"""Independent pure-host contract controls. No OS descriptors or product execution.

The read automaton and lifecycle model below are newly authored specifications,
not copies of the candidate model. Candidate imports are adversarial comparisons.
All numeric funding and descriptors are synthetic and select no product policy.
"""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract"
import model
from helpers import own_handle, admitted_owner
MAX = (1 << 64) - 1


def checked_total(values, maximum=MAX):
    total = 0
    for value in values:
        if type(value) is not int or value < 0 or value > maximum - total:
            raise ValueError("checked sum")
        total += value
    return total


def read_call_ceiling(extent):
    if type(extent) is not int or not 0 < extent <= MAX:
        raise ValueError("positive u64 extent")
    # Avoid the potentially overflowing extent + BLOCK - 1 expression.
    quotient, tail = divmod(extent, 4096)
    return checked_total([quotient, int(tail != 0), 1]) * 32


def read_spec(extent, replies, block=4096, attempts=32):
    """Independent request-state automaton; short reads consume attempts.

    Returns (accepted, calls, completed_bytes). End of supplied replies means
    adversary supplies Interrupted forever. Cleanup is a separate paid stage.
    """
    if extent < 0 or block <= 0 or attempts <= 0:
        raise ValueError("shape")
    stream = iter(replies)
    calls = completed = 0
    requests = [min(block, extent - start) for start in range(0, extent, block)] + [0]
    for target in requests:
        filled = 0
        for _ in range(attempts):
            calls += 1
            answer = next(stream, "I")
            if answer == "I":
                continue
            if type(answer) is not int or answer < 0:
                return False, calls, completed + filled
            if target == 0:
                return answer == 0, calls, completed
            if answer == 0 or answer > target - filled:
                return False, calls, completed + filled
            filled += answer
            if filled == target:
                completed += filled
                break
        else:
            return False, calls, completed + filled
    return True, calls, completed


def worst_success(extent):
    replies = []
    for start in range(0, extent, 4096):
        replies.extend(["I"] * 31 + [min(4096, extent - start)])
    return replies + ["I"] * 31 + [0]


class Lifecycle:
    """Independent affine model with raw/adopted slots and live owner binding.

    A complete quote includes all13 slots' retirement, including slots not yet
    converted to File. Native close success remains outside this host model.
    """
    def __init__(self, quote, operation_budget, retirement_budget):
        if min(quote, operation_budget, retirement_budget) < 0 or quote < operation_budget + retirement_budget:
            raise ValueError("unfunded retirement")
        self.left = operation_budget
        self.retirement_left = retirement_budget
        self.charge = quote
        self.slots = ["raw"] * 13
        self.bodies = []
        self.failures = []
        self.state = "acquiring"
        self.identity = object()
        self.events = ["reserve"]

    def effect(self, name):
        if self.left < 1 or self.state != "acquiring":
            raise ValueError("effect unavailable")
        self.left -= 1
        self.events += ["debit:" + name, "effect:" + name]

    def adopt(self, bad_index=None):
        for slot in range(13):
            self.effect("validate" + str(slot))
            if slot == bad_index:
                self.failures.append(("bad-slot", slot))
                return False
            self.effect("adopt" + str(slot))
            self.slots[slot] = "adopted"
        return True

    def admit(self):
        if self.state != "acquiring" or any(s != "adopted" for s in self.slots):
            raise ValueError("not acquired")
        self.state = "admitted"
        self.bodies = [object() for _ in range(22)]
        return self.identity

    def correlate(self, token, actual, expected):
        if self.state != "admitted" or token is not self.identity or len(self.bodies) != 22:
            raise ValueError("detached admission")
        if actual != expected:
            self.failures.append(("correlation", actual))
            return False
        return True

    def retire(self, fail_at=None):
        self.state = "retiring"
        # Native retirement/refusal work is separate, reserved before adoption.
        for slot in range(13):
            if self.retirement_left <= 0:
                raise ValueError("retirement exhausted")
            self.retirement_left -= 1
            self.events += ["retirement-debit", "retirement-attempt"]
            if slot == fail_at:
                self.failures.append(("original-retirement", slot))
                self.state = "unqualified-retirement"
                return False
            self.slots[slot] = "retired"
        self.bodies.clear()
        self.failures.clear()
        self.state = "retired"
        return True

    def release(self):
        if self.state != "retired" or self.bodies or self.failures or any(s != "retired" for s in self.slots):
            raise ValueError("live/unqualified owner")
        self.state = "released"
        self.charge = 0


def acyclic(edges):
    remaining = {node: set(deps) for node, deps in edges.items()}
    known = set(remaining)
    for dependencies in remaining.values():
        if not dependencies <= known:
            raise ValueError("unbound predecessor")
    done = set()
    while remaining:
        ready = {node for node, deps in remaining.items() if deps <= done}
        if not ready:
            raise ValueError("cycle")
        done |= ready
        for node in ready:
            del remaining[node]
    return done


def candidate_paid():
    from helpers import reservation
    return reservation()


def candidate_owner(paid):
    return admitted_owner(paid)


class IndependentControls(unittest.TestCase):
    def test_read_bound_arbitrary_small_short_read_and_interrupt_schedules(self):
        cases = 0
        for extent in range(1, 7):
            bound = 3 * ((extent + 2) // 3 + 1)
            # Exhaustive bounded prefixes include zeros, negative/error, short,
            # overreported and Interrupted replies. No candidate oracle is used.
            for replies in itertools.product(("I", 0, 1, 2, 3, 4, -1), repeat=5):
                ok, calls, completed = read_spec(extent, replies, 3, 3)
                self.assertLessEqual(calls, bound)
                self.assertLessEqual(completed, extent)
                if ok:
                    self.assertEqual(completed, extent)
                cases += 1
        print(json.dumps({"exhaustive_read_schedules": cases}))

    def test_exact_4096_32_bound_is_attainable(self):
        for extent in (1, 31, 32, 33, 4095, 4096, 4097, 8192, 8193, 16385):
            self.assertEqual(read_spec(extent, worst_success(extent)), (True, read_call_ceiling(extent), extent))

    def test_partial_and_interrupted_eof_refuse_finitely(self):
        for extent in (1, 4096, 4097, 8193):
            patterns = (["I"] * 33, [0], [4097], [1] * 33,
                        worst_success(extent)[:-1] + ["I"], worst_success(extent)[:-1] + [1])
            for pattern in patterns:
                ok, count, _ = read_spec(extent, pattern)
                self.assertFalse(ok)
                self.assertLessEqual(count, read_call_ceiling(extent))

    def test_full_block_33_one_byte_reads_refuses_after32(self):
        self.assertEqual(read_spec(33, [1] * 33), (False, 32, 32))
        self.assertEqual(read_spec(32, [1] * 32 + [0]), (True, 33, 32))

    def test_candidate_read_counts_match_independent_adverse_schedules(self):
        for extent, responses in ((1, ["I"] * 31 + [1] + ["I"] * 31 + [0]),
                (33, [1] * 33), (4097, worst_success(4097)), (3, [0]), (3, [4]),
                (3, [3] + ["I"] * 32), (3, [1, 2, 1])):
            root, paid = candidate_paid()
            h = model.TestHandle(b"x" * extent, model.TestFileIdentity(1, 1, extent),
                responses=["Interrupted" if v == "I" else v for v in responses])
            own_handle(paid, h)
            accepted = True
            try:
                model.acquire_body(paid, h, "source", 100000)
            except model.Refused:
                accepted = False
            expected = read_spec(extent, responses)
            self.assertEqual(accepted, expected[0])
            self.assertEqual(sum(e in ("read:source", "eof:source") for e in paid.effects), expected[1])

    def test_extent_formula_no_round_up_overflow_and_checked_price_multiplication(self):
        self.assertEqual(read_call_ceiling(MAX), 144115188075855904)
        for invalid in (-1, 0, MAX + 1, True):
            with self.assertRaises(ValueError): read_call_ceiling(invalid)
        with self.assertRaises(ValueError): checked_total([MAX, 1])
        # Calls fit u64 at max u64 extent; a future per-call price product might
        # not. It must be checked rather than inferred from finite calls.
        with self.assertRaises(ValueError): checked_total([read_call_ceiling(MAX) * 129])

    def test_every_partial_adoption_has_paid_retirement_for_all13_slots(self):
        for failed in range(13):
            life = Lifecycle(100, 60, 13)
            self.assertFalse(life.adopt(failed))
            self.assertEqual(life.slots[:failed], ["adopted"] * failed)
            self.assertEqual(life.slots[failed:], ["raw"] * (13 - failed))
            with self.assertRaises(ValueError): life.release()
            self.assertTrue(life.retire())
            self.assertEqual(life.charge, 100)
            life.release()
            self.assertEqual(life.charge, 0)

    def test_operation_exhaustion_cannot_consume_retirement_reserve(self):
        life = Lifecycle(15, 2, 13)
        with self.assertRaises(ValueError): life.adopt()
        self.assertEqual(life.retirement_left, 13)
        self.assertTrue(life.retire())
        life.release()

    def test_retirement_failure_never_reports_release_or_healthy_close(self):
        for failed in range(13):
            life = Lifecycle(100, 60, 13)
            life.adopt()
            self.assertFalse(life.retire(failed))
            with self.assertRaises(ValueError): life.release()
            self.assertEqual(life.charge, 100)

    def test_live_admission_cannot_outlive_original_owners(self):
        life = Lifecycle(100, 60, 13)
        life.adopt()
        token = life.admit()
        self.assertTrue(life.correlate(token, {"x": 1}, {"x": 1}))
        self.assertFalse(life.correlate(token, {"x": 2}, {"x": 1}))
        life.retire()
        with self.assertRaises(ValueError): life.correlate(token, {}, {})
        other = Lifecycle(100, 60, 13)
        other.adopt(); other.admit()
        with self.assertRaises(ValueError): other.correlate(token, {}, {})

    def test_precompile_then_external_postcompile_dag_and_cycle_controls(self):
        graph = {"p0": (), "policy": (), "source_host_tools": ("policy",),
            "compile_manifest": ("source_host_tools",), "compile_env_minus5": (),
            "executable": ("compile_manifest", "compile_env_minus5"),
            "build": ("executable", "compile_manifest"), "process_env_minus2": (),
            "nonce": (), "session": ("build", "executable", "nonce", "process_env_minus2"),
            "review": ("session", "build", "source_host_tools", "policy"),
            "acquisition": ("p0", "policy"), "admit": ("review", "session", "acquisition")}
        self.assertEqual(len(acyclic(graph)), len(graph))
        for node, dependency in (("p0", "admit"), ("source_host_tools", "review"),
                ("compile_manifest", "executable"), ("review", "review")):
            changed = dict(graph); changed[node] += (dependency,)
            with self.assertRaises(ValueError): acyclic(changed)
        with self.assertRaises(ValueError): acyclic({"authority": ("unbound_label",)})

    def test_ten_caps_are_finite_limits_not_policy_and_fixture_paths_independent(self):
        c = json.loads((CANDIDATE / "contract.json").read_bytes())
        values = [v["cap"] for v in c["identity_caps"] if v["cap"] is not None]
        self.assertEqual((len(values), sum(values)), (10, 67454875))
        self.assertEqual(c["path_caps"], [None] * 5)
        self.assertIsNone(c["path_packet_cap"])
        self.assertIsNone(c["inherited_transfer"]["FD_BASE"])
        self.assertFalse(c["known_caps_are_prices_or_authority"])
        self.assertFalse(c["root_funding_selected"])
        self.assertFalse(c["path_packet_schema"]["fixture_path_cap_is_loader4096"])

    def test_packet_shapes_raw_paths_and_no_tail_against_independent_encoder(self):
        root, paid = candidate_paid()
        paths = (b"x" * 4500, b"/a\xff", b"/c", b"/d", b"/e")
        header = b"MIXPTH01" + (1).to_bytes(8, "little") + (64 + sum(map(len, paths))).to_bytes(8, "little")
        body = header + b"".join(len(p).to_bytes(8, "little") for p in paths) + b"".join(paths)
        self.assertEqual(model.decode_path_packet(paid, body), paths)
        native, retained = model.acquire_native_paths(paid, paths)
        self.assertEqual(len({id(b) for b in native + retained}), 10)
        self.assertEqual(sum(b.allocation_bound for b in native + retained), 2 * sum(map(len, paths)))
        for corrupt in (body[:-1], body + b"tail", body[:24] + bytes(8) + body[32:],
                body[:24] + MAX.to_bytes(8, "little") + body[32:], body[:-1] + b"\0"):
            _, trial = candidate_paid()
            with self.assertRaises(model.Refused): model.decode_path_packet(trial, corrupt)

    def test_allocation_slack_prepaid_before_effect_and_error_original_retained(self):
        _, paid = candidate_paid()
        paid.storage_left = 3
        h = model.TestHandle(b"abc", model.TestFileIdentity(1, 1, 3)); own_handle(paid, h)
        with self.assertRaises(model.Refused): model.acquire_body(paid, h, "source", 100, allocation_contract=model.AllocationContract(3, 1))
        self.assertNotIn("allocate:source", paid.effects)
        _, paid = candidate_paid()
        original = OSError(5, "independent synthetic original")
        h = model.TestHandle(b"abc", model.TestFileIdentity(1, 1, 3), responses=[original]); own_handle(paid, h)
        with self.assertRaises(model.Refused): model.acquire_body(paid, h, "source", 100)
        self.assertIs(paid.diagnostics[0], original)

    def test_existing_source_checks_and_exact_missing_preleaf_boundary(self):
        c = json.loads((CANDIDATE / "contract.json").read_bytes())
        for anchor in c["source_anchors"]:
            raw = (ROOT / anchor["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), anchor["sha256"])
            for line in anchor["lines"]:
                self.assertIn(anchor["exact_anchor"], raw.decode().splitlines()[line - 1])
        base = ROOT / "verification/swift-guarded-snapshot-scoped-binding-source/source/vm/src/experimental_swift_reactor"
        loader = (base / "retained_profile_loader_v1.rs").read_text()
        entry = (base / "cache/initial_profile_v1.rs").read_text()
        for anchor in ("for i in 0..4 {", "b.sections[i].bytes", "s.sections[i].bytes",
                "claim != embedded[index]", "s.budget != budget", "s.nonce != observed.nonce",
                "s.sections[0].bytes != identities[0].encode()", "s.sections[1].bytes != observed.argv.slice()",
                "s.sections[2].bytes != observed.environment.slice()", "s.sections[3].bytes != observed.cwd.slice()",
                "final_metadata_recheck_v1(files, &identities)?", "source_bytes_equal(&proof, &input)"):
            self.assertIn(anchor, loader)
        provenance = loader.split("pub(crate) struct LoaderProvenanceV1 {", 1)[1].split("\n}", 1)[0]
        fields = tuple(row.strip().split(":", 1)[0] for row in provenance.splitlines() if ":" in row)
        self.assertEqual(fields, ("validation_budget", "source_extent", "source", "manifest", "build", "session", "executable", "nonce", "identities"))
        self.assertIn("Ok(selected) => PrimaryOutcomeV1::Leaf(invoke_loaded_leaf_once_v1(", entry)
        self.assertNotIn("correlate_admitted_loader_v1", entry)
        self.assertFalse(c["existing_route"]["different_handle_is_automatically_failure"])

    def test_all_production_selectors_original_claims_and_fields_stay_pending(self):
        c = json.loads((CANDIDATE / "contract.json").read_bytes())
        self.assertEqual((c["actual_selected_parent_account"], c["actual_selected_whole_quote"], c["actual_selected_binding"]),
            ("RootPolicyPending", "WholeQuotePending", "ImmutableBindingAndP0ReviewPending"))
        self.assertTrue(c["preserved_originals"]["all17_product_fields_explicit"])
        self.assertTrue(c["preserved_originals"]["eight_claims_unverified"])
        self.assertFalse(c["preserved_originals"]["old_prices_apply_to_new_source"])


class CandidateDesiredPropertyRegressions(unittest.TestCase):
    """Intentionally failing desired-property tests; preserve failures as findings."""
    def test_partial_adoption_owned_by_returned_retirement_roster(self):
        _, paid = candidate_paid()
        slots = [model.TestHandle(b"x", model.TestFileIdentity(1, i + 1, 1)) for i in range(13)]
        slots[2].slot_valid = False
        with self.assertRaises(model.Refused):
            model.adopt_slots(paid, slots, single_threaded=True, no_prior_owners=True, no_close_handlers=True)
        self.assertEqual(len([h for h in paid.owned if isinstance(h, model.TestHandle)]), 2,
            "already adopted handles have no owning reservation/returned roster")

    def test_storage_cannot_release_while_adopted_descriptors_remain_live(self):
        root, paid = candidate_paid()
        slots = [model.TestHandle(b"x", model.TestFileIdentity(1, i + 1, 1)) for i in range(13)]
        model.adopt_slots(paid, slots, single_threaded=True, no_prior_owners=True, no_close_handlers=True)
        paid.destroy().release()
        self.assertFalse(root.used_storage == 0 and any(h.adopted and h.slot_valid for h in slots),
            "release clears charge without retiring a single handle")

    def test_detached_admitted_view_cannot_dispatch_after_owner_retirement(self):
        _, paid = candidate_paid()
        _, _, view = candidate_owner(paid)
        paid.destroy().release()
        _, different_paid = candidate_paid()
        with self.assertRaises(model.Refused):
            model.correlate_before_leaf(different_paid, view, {}, {})

    def test_correlation_expected_fields_derive_from_live_admitted_owner(self):
        _, paid = candidate_paid()
        _, _, view = candidate_owner(paid)
        # Equal caller dictionaries omit every promised provenance field and
        # are unrelated to the admitted bodies. Equality alone still dispatches.
        with self.assertRaises(model.Refused):
            model.correlate_before_leaf(paid, view, {}, {})


if __name__ == "__main__":
    cls = CandidateDesiredPropertyRegressions if "--candidate-regressions" in sys.argv else IndependentControls
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(cls)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
