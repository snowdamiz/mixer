"""Independent host tests for a proposal; synthetic money/handles only."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

from model import (ATTEMPTS, KNOWN_CAPS, ROLES, U64_MAX, Refused, TestBody,
                   TestFileIdentity, TestHandle, TestPolicy, TestRoot,
                   acquire_body, acquire_native_paths, add, admit_model_only,
                   adopt_slots, check_dependency_dag, correlate_before_leaf,
                   decode_path_packet)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


from helpers import policy, reservation, handle, complete_owner, own_handle, selected_result
from model import AllocationContract


def adopted(data=b"abc", **kw):
    # Fixture name retained; safe adoption now needs the actual paid owner.
    return handle(data, **kw)


def read_owned(paid, h, *args, **kw):
    if not paid.outcome.adoption_started:
        own_handle(paid, h)
    return acquire_body(paid, h, *args, **kw)


class ModelTests(unittest.TestCase):
    def test_unverified_input_cannot_construct_bootstrap_policy(self):
        for x in ({"work": 999999, "sha256": "a" * 64}, b"review accepts", 42):
            with self.assertRaises(Refused):
                TestRoot(x, startup_already_provisioned=True)

    def test_startup_provision_and_all_native_diagnostics_contract_required(self):
        with self.assertRaises(Refused):
            TestRoot(policy(), startup_already_provisioned=False)
        with self.assertRaises(Refused):
            TestRoot(policy(complete=False), startup_already_provisioned=True)

    def test_whole_reserve_exact_and_atomic(self):
        for work, storage in ((11, 10), (10, 11), (U64_MAX + 1, 1), (0, 1)):
            root = TestRoot(policy(10, 10), startup_already_provisioned=True)
            with self.assertRaises(Refused):
                root.reserve(work, storage, cleanup_work=1)
            self.assertEqual((root.used_work, root.used_storage, root.trace), (0, 0, []))
        root, paid = reservation(10, 10)
        self.assertEqual((root.used_work, root.used_storage), (1010, 10))
        with self.assertRaises(Refused):
            root.reserve(1, 1, cleanup_work=1)

    def test_operation_checks_both_dimensions_before_effect(self):
        root, paid = reservation(7, 11)
        for work, storage in ((8, 1), (1, 12), (U64_MAX + 1, 0)):
            before = (paid.work_left, paid.storage_left, list(paid.effects), list(root.trace))
            with self.assertRaises(Refused):
                paid.operation("forbidden", work, storage)
            self.assertEqual((paid.work_left, paid.storage_left, paid.effects, root.trace), before)

    def test_every_actual_effect_has_immediately_preceding_prepaid_ticket(self):
        root, paid = reservation()
        complete_owner(paid)
        for index, row in enumerate(root.trace):
            if row[0] == "effect":
                self.assertEqual(root.trace[index - 1][0:2], ("prepay", row[1]))

    def test_unadopted_handle_cannot_be_acquired(self):
        _, paid = reservation()
        with self.assertRaises(Refused):
            acquire_body(paid, handle(), "source", 100)
        self.assertEqual(paid.effects, [])

    def test_adoption_one_time_single_thread_no_handler_and_unique_slots(self):
        for kwargs in (dict(single_threaded=False), dict(no_prior_owners=False),
                       dict(no_close_handlers=False)):
            _, paid = reservation()
            args = dict(single_threaded=True, no_prior_owners=True, no_close_handlers=True)
            args.update(kwargs)
            with self.assertRaises(Refused):
                adopt_slots(paid, [handle(inode=i) for i in range(13)], **args)
            self.assertEqual(paid.effects, [])
        _, paid = reservation()
        hs = [handle(inode=i) for i in range(13)]
        adopt_slots(paid, hs, single_threaded=True, no_prior_owners=True, no_close_handlers=True)
        with self.assertRaises(Refused):
            adopt_slots(paid, hs, single_threaded=True, no_prior_owners=True, no_close_handlers=True)

    def test_bad_fd_alias_and_nonregular_refuse_with_partial_adoption_retained(self):
        for failure in ("invalid", "alias", "nonregular", "same_slot"):
            _, paid = reservation()
            hs = [handle(inode=i) for i in range(13)]
            if failure == "invalid": hs[2].slot_valid = False
            if failure == "alias": hs[2].identity = hs[1].identity
            if failure == "nonregular": hs[2].identity = TestFileIdentity(11, 2, 3, mode=0)
            if failure == "same_slot": hs[2] = hs[1]
            with self.assertRaises(Refused):
                adopt_slots(paid, hs, single_threaded=True, no_prior_owners=True, no_close_handlers=True)
            if failure != "same_slot":
                self.assertTrue(hs[0].adopted and hs[1].adopted)

    def test_metadata_cap_offset_and_nonregular_before_allocation(self):
        for h, cap in ((adopted(size=1001), 1000), (adopted(size=0), 1000),
                       (adopted(size=U64_MAX + 1), U64_MAX)):
            _, paid = reservation()
            with self.assertRaises(Refused): read_owned(paid, h, "source", cap)
            self.assertFalse(any(x.startswith("allocate:") or x.startswith("read:") for x in paid.effects))
        for condition in ("offset", "regular"):
            h = adopted()
            if condition == "offset": h.position = 1
            else: h.identity = TestFileIdentity(11, 1, 3, mode=0)
            _, paid = reservation()
            with self.assertRaises(Refused): read_owned(paid, h, "source", 100)
            self.assertFalse(any(type(b) is TestBody for b in paid.owned))

    def test_allocation_actual_available_budget_and_capacity_bound_before_effect(self):
        _, paid = reservation(100, 3)
        with self.assertRaises(Refused):
            read_owned(paid, adopted(), "source", 100, allocation_contract=AllocationContract(3, 1))
        self.assertFalse(any(x.startswith("allocate:") for x in paid.effects))
        _, paid = reservation(100, 4)
        b, _ = read_owned(paid, adopted(), "source", 100, allocation_contract=AllocationContract(3, 1))
        self.assertEqual((b.length, b.allocation_bound, paid.storage_left), (3, 4, 0))

    def test_read_and_eof_attempt_caps_count_interrupts_no33rd_call(self):
        for eof in (False, True):
            _, paid = reservation()
            h = adopted(responses=([3] if eof else []) + ["Interrupted"] * ATTEMPTS)
            with self.assertRaisesRegex(Refused, "attempt cap"):
                read_owned(paid, h, "source", 100)
            self.assertEqual(paid.effects.count(("eof:" if eof else "read:") + "source"), 32)

    def test_short_extra_overreported_refuse_and_original_error_not_flattened(self):
        for h in (adopted(b"ab", size=3), adopted(b"abcd", size=3),
                  adopted(responses=[4]), adopted(responses=[0])):
            _, paid = reservation()
            with self.assertRaises(Refused): read_owned(paid, h, "source", 100)
        original = OSError(7, "synthetic original error")
        _, paid = reservation()
        with self.assertRaises(Refused):
            read_owned(paid, adopted(responses=[original]), "source", 100)
        self.assertIs(paid.diagnostics[0], original)
        self.assertEqual(len([b for b in paid.owned if type(b) is TestBody]), 1)

    def test_metadata_changed_refuses_before_hash_or_admission(self):
        _, paid = reservation()
        h = adopted()
        h.final_identity = TestFileIdentity(11, 1, 3, mtime_ns=2)
        with self.assertRaisesRegex(Refused, "metadata changed"):
            read_owned(paid, h, "source", 100)
        self.assertNotIn("hash:source", paid.effects)

    def test_finite_block_read_and_hash_actual_full_bytes(self):
        _, paid = reservation()
        data = b"x" * 8193
        b, digest = read_owned(paid, adopted(data), "source", 10000)
        self.assertEqual(digest, hashlib.sha256(data).digest())
        self.assertEqual(paid.effects.count("read:source"), 3)
        with self.assertRaises(Refused): b.set_once(data)

    def test_path_copies_are_independent_and_raw_nonutf8_is_retained(self):
        _, paid = reservation()
        path = b"/same/nonutf8-\xff"
        native, retained = acquire_native_paths(paid, (path,) * 5)
        self.assertEqual(len({id(x) for x in native + retained}), 10)
        self.assertEqual(sum(x.allocation_bound for x in native + retained), 10 * len(path))
        self.assertTrue(all(x.data == path for x in native + retained))

    def test_paths_nul_empty_and_missing_independent_backing_refuse(self):
        for bad in (b"", b"/nul\0", b"x" * 10001):
            _, paid = reservation()
            with self.assertRaises(Refused): acquire_native_paths(paid, (bad,) * 5)
        _, paid = reservation()
        bodies, paths = complete_owner(paid)
        native, retained = paths
        with self.assertRaises(Refused):
            admit_model_only(paid, bodies, (native, native), trusted_local_launch_contract=True,
                             all_actual_correspondence=True, review_provenance=True)

    def test_hash_and_review_labels_do_not_create_authority(self):
        for key in ("trusted_local_launch_contract", "all_actual_correspondence", "review_provenance"):
            _, paid = reservation()
            bodies, paths = complete_owner(paid)
            args = dict(trusted_local_launch_contract=True, all_actual_correspondence=True,
                        review_provenance=True)
            args[key] = "a" * 64
            with self.assertRaises(Refused): admit_model_only(paid, bodies, paths, **args)

    def test_all12_full_bodies_no_digest_only_and_owner_live(self):
        _, paid = reservation()
        bodies, paths = complete_owner(paid)
        with self.assertRaises(Refused):
            admit_model_only(paid, bodies[:-1], paths, trusted_local_launch_contract=True,
                             all_actual_correspondence=True, review_provenance=True)
        bodies[0].live = False
        with self.assertRaises(Refused):
            admit_model_only(paid, bodies, paths, trusted_local_launch_contract=True,
                             all_actual_correspondence=True, review_provenance=True)

    def test_reopened_loader_correspondence_before_leaf(self):
        _, paid = reservation()
        bodies, paths = complete_owner(paid)
        view = admit_model_only(paid, bodies, paths, trusted_local_launch_contract=True,
                                all_actual_correspondence=True, review_provenance=True)
        expected = view.correspondence.mapping()
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

    def test_storage_held_through_original_result_and_external_retirement_only(self):
        root, paid = reservation()
        complete_owner(paid)
        original = OSError(5, "synthetic retained")
        paid.fail(original)
        self.assertEqual(root.used_storage, 1000000)
        token = paid.destroy()
        self.assertEqual(root.used_storage, 1000000)
        token.release()
        self.assertEqual((root.used_work, root.used_storage, root.peak), (1001000, 0, 1000000))
        with self.assertRaises(Refused): token.release()
        with self.assertRaises(Refused): paid.operation("late", 1)

    def test_unwind_or_missing_token_never_refunds(self):
        root, paid = reservation()
        complete_owner(paid)
        del paid
        self.assertEqual(root.used_storage, 1000000)

    def test_checked_add_and_computable_caps_are_limits_not_prices(self):
        with self.assertRaises(Refused): add(U64_MAX, 1)
        self.assertEqual(len([x for x in KNOWN_CAPS if x is not None]), 10)
        self.assertIsNone(KNOWN_CAPS[4])
        self.assertIsNone(KNOWN_CAPS[11])

    def test_bounded_path_packet_exact5_sections_and_no4096_assumption(self):
        paths = tuple(b"/test/" + bytes([65 + i]) for i in range(5))
        head = b"MIXPTH01" + struct.pack("<QQ", 1, 64 + sum(map(len, paths)))
        packet = head + b"".join(struct.pack("<Q", len(x)) for x in paths) + b"".join(paths)
        _, paid = reservation()
        self.assertEqual(decode_path_packet(paid, packet), paths)
        for altered in (packet + b"tail", packet[:-1], packet[:24] + struct.pack("<Q", U64_MAX) + packet[32:],
                        b"wrong!00" + packet[8:]):
            _, paid = reservation()
            with self.assertRaises(Refused): decode_path_packet(paid, altered)
        # Fixture path caps are explicitly source-policy inputs;4096 is not an
        # inherited constraint. An independently selected test policy can be larger.
        p = TestPolicy(100000, 100000, (10000,) * 12, (5000,) * 5, 30000)
        r = TestRoot(p, startup_already_provisioned=True)
        native, retained = acquire_native_paths(r.reserve(99000, 100000, cleanup_work=1000), (b"x" * 4500,) * 5)
        self.assertEqual(native[0].length, 4500)

    def test_external_postcompile_review_and_preexisting_root_break_all_cycles(self):
        graph = {"acquisition": ("external_p0",), "compile_manifest": ("source146", "host11"),
                 "compile_environment": ("environment_without5keys",),
                 "output_executable": ("compile_manifest", "compile_environment"),
                 "build": ("output_executable", "compile_manifest"),
                 "session": ("build", "output_executable", "fresh_nonce", "process_without2keys"),
                 "review": ("session", "build", "source146", "output_executable"),
                 "acquisition_authentication": ("review", "session", "acquisition")}
        self.assertIn("review", check_dependency_dag(graph))
        for node, added in (("external_p0", "acquisition"),
                            ("compile_manifest", "output_executable"),
                            ("source146", "review"), ("review", "review")):
            changed = dict(graph)
            changed[node] = tuple(changed.get(node, ())) + (added,)
            with self.assertRaises(Refused): check_dependency_dag(changed)


class FrozenInputTests(unittest.TestCase):
    def test_contract_caps_authority_and_route_choice_align(self):
        value = json.loads((HERE / "contract.json").read_bytes())
        self.assertEqual(tuple(row["cap"] for row in value["identity_caps"]), KNOWN_CAPS)
        self.assertEqual(value["known_identity_cap_subtotal"], sum(x for x in KNOWN_CAPS if x is not None))
        self.assertFalse(value["root_funding_selected"])
        self.assertFalse(value["known_caps_are_prices_or_authority"])
        self.assertTrue(value["existing_route"]["retain_setup_and_loader_opens"])
        self.assertFalse(value["existing_route"]["different_handle_is_automatically_failure"])
        self.assertEqual(value["minimum_private_boundary"]["numeric_or_digest_or_payload_arguments"], 0)
        for anchor in value["source_anchors"]:
            data = (ROOT / anchor["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), anchor["sha256"])
            lines = data.decode().splitlines()
            for line in anchor["lines"]:
                self.assertIn(anchor["exact_anchor"], lines[line - 1])

    def test_three_frozen_input_seals_and_all_members(self):
        for stem, expected in (
            ("swift-guarded-snapshot-owned-binding-provider", "7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de"),
            ("swift-guarded-snapshot-scoped-binding-source", "84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2"),
            ("swift-guarded-snapshot-scoped-binding-independent", "e11d9eff0eda83ccf46563526e3c7025172cc8e05513b4a9ba1a5a0d9c13344a")):
            base = ROOT / "verification" / stem
            seal_bytes = (base / "seal.json").read_bytes()
            self.assertEqual(hashlib.sha256(seal_bytes).hexdigest(), expected)
            seal = json.loads(seal_bytes)
            for row in seal["members"]:
                data = (base / row["path"]).read_bytes()
                self.assertEqual((len(data), hashlib.sha256(data).hexdigest()),
                                 (row["bytes"], row["sha256"]))

    def test_actual146_custody_and_host11_rosters(self):
        base = ROOT / "verification/swift-guarded-snapshot-owned-binding-provider"
        manifest = json.loads((base / "proposed-source-manifest.json").read_bytes())
        custody = json.loads((base / "proposed-source-custody.json").read_bytes())
        self.assertEqual(manifest["member_count"], len(custody))
        self.assertEqual(manifest["member_count"], 146)
        self.assertEqual(manifest["tree_sha256"], "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d")
        for expected, actual in zip(manifest["members"], custody):
            self.assertEqual(expected, {k: actual[k] for k in ("path", "bytes", "sha256")})
            data = (ROOT / actual["origin"]).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()),
                             (expected["bytes"], expected["sha256"]))
        host = json.loads((ROOT / "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json").read_bytes())
        self.assertEqual((host["member_count"], len(host["members"])), (11, 11))
        self.assertEqual(host["tree_sha256"], "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2")
        for row in host["members"]:
            data = (ROOT / "verification/swift-real-profile-loader-binding/host" / row["path"]).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (row["bytes"], row["sha256"]))

    def test_source_contract_anchors_current_pending_and_existing_loader_checks(self):
        src = ROOT / "verification/swift-guarded-snapshot-scoped-binding-source/source/vm/src/experimental_swift_reactor"
        account = (src / "cache/initial_profile_v1/host_account_v1.rs").read_text()
        profile = (src / "cache/initial_profile_v1.rs").read_text()
        loader = (src / "retained_profile_loader_v1.rs").read_text()
        self.assertIn("Err(RefusalV1::RootPolicyPending)", account)
        self.assertIn("Err(RefusalV1::WholeQuotePending)", account)
        self.assertIn("Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)", profile)
        for anchor in ("word(b, 32) != 146", "word(b, 40) != 11",
                       "if session_digest != observed.expected_session",
                       "if s.nonce != observed.nonce", "if s.build != build_digest",
                       "s.sections[0].bytes != identities[0].encode()",
                       "final_metadata_recheck_v1(files, &identities)?",
                       "let source_digest = platform::hash(&input, usage)?",
                       "let executable_digest = platform::hash(&executable, usage)?"):
            self.assertIn(anchor, loader)
        source = (ROOT / "verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm").read_bytes()
        self.assertEqual((len(source), hashlib.sha256(source).hexdigest()),
                         (1947, "9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
