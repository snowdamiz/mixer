"""Independent executable callback-contract models, never product runtime tests.

These deliberately ordinary Python models validate the reviewer's transition
predicates and adversarial examples. They do not import, translate, or execute
Mixer product code, SQL, BEAM dependencies, provider code, or native tools.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import unittest


def source_snapshot():
    browser = {
        "id": "synthetic-browser",
        "cookie_digest": "synthetic-cookie-digest",
        "status": "preauth",
        "epoch": 2,
        "revision": 2,
        "generation": "synthetic-generation",
        "csrf_digest": "synthetic-csrf-digest",
        "created_at": 100,
        "last_seen_at": 100,
        "absolute_expires_at": 400,
        "idle_expires_at": 400,
        "expected_profile_id": "synthetic-profile",
        "expected_profile_version": 1,
        "initial_config_digest": "synthetic-config-digest",
        "config_digest": "synthetic-config-digest",
        "profile_id": None,
        "profile_version": None,
        "principal_id": None,
        "family_id": None,
        "credential_ref": None,
        "credential_revision": None,
        "audit_sequence": 2,
    }
    attempt = {
        "state_digest": "synthetic-state-digest",
        "browser_id": browser["id"],
        "browser_epoch": browser["epoch"],
        "browser_revision": browser["revision"],
        "cookie_digest": browser["cookie_digest"],
        "generation": browser["generation"],
        "config_digest": browser["config_digest"],
        "profile_id": browser["expected_profile_id"],
        "profile_version": browser["expected_profile_version"],
        "issuer": "https://synthetic.invalid",
        "client_id": "synthetic-client",
        "redirect_uri": "https://console.invalid/auth/callback",
        "return_route": "workspace",
        "nonce_digest": "synthetic-nonce-digest",
        "created_at": 101,
        "expires_at": 390,
        "status": "pending",
        "claim_digest": None,
        "claimed_at": None,
        "claim_expires_at": None,
        "completion_reason": None,
        "ciphertext_version": 1,
        "key_id": "synthetic-key",
        "iv": "synthetic-postgresql-hex-iv",
        "tag": "synthetic-postgresql-hex-tag",
        "ciphertext": "synthetic-postgresql-hex-ciphertext",
    }
    context = {
        "purpose": "preauth",
        "browser_id": browser["id"],
        "cookie_digest": browser["cookie_digest"],
        "csrf_digest": browser["csrf_digest"],
        "epoch": browser["epoch"],
        "revision": browser["revision"],
        "generation": browser["generation"],
        "vault_generation": 2,
        "config_digest": browser["config_digest"],
        "profile_id": browser["expected_profile_id"],
        "profile_version": browser["expected_profile_version"],
        "principal_id": None,
        "family_id": None,
        "credential_ref": None,
        "credential_revision": None,
    }
    sealed = {
        "version": 1,
        "key_id": "synthetic-key",
        "iv": "synthetic-decoded-iv",
        "tag": "synthetic-decoded-tag",
        "ciphertext": "synthetic-decoded-ciphertext",
    }
    attempt_context = {
        "purpose": "attempt",
        "state_digest": attempt["state_digest"],
        "browser_id": browser["id"],
        "cookie_digest": browser["cookie_digest"],
        "epoch": browser["epoch"],
        "revision": browser["revision"],
        "generation": browser["generation"],
        "config_digest": browser["config_digest"],
        "profile_id": browser["expected_profile_id"],
        "profile_version": browser["expected_profile_version"],
        "issuer": attempt["issuer"],
        "client_id": attempt["client_id"],
        "redirect_uri": attempt["redirect_uri"],
        "expires_at": attempt["expires_at"],
    }
    return {
        "browser": browser,
        "attempt": attempt,
        "session_envelope": {"context": context, "sealed": sealed},
        "attempt_envelope": {"context": attempt_context, "sealed": deepcopy(sealed)},
    }


def claim_expiry(source, entry):
    b, a = source["browser"], source["attempt"]
    return min(entry + 60, a["expires_at"], b["idle_expires_at"], b["absolute_expires_at"])


def expected_transition(source, outcome, entry=110, claimed_at=112):
    result = deepcopy(source)
    result["browser"]["audit_sequence"] += 1
    attempt = result["attempt"]
    for key in ("key_id", "iv", "tag", "ciphertext"):
        attempt[key] = None
    result["attempt_envelope"] = None
    if outcome == "claimed":
        attempt.update(
            status="claimed",
            claim_digest="synthetic-independent-claim-digest",
            claimed_at=claimed_at,
            claim_expires_at=claim_expiry(source, entry),
        )
    elif outcome == "provider_rejected":
        attempt.update(status="provider_rejected", completion_reason="provider_rejected")
    else:
        raise ValueError("closed transition")
    return result


def accepted_poststate(source, actual, outcome, entry=110, now=114):
    try:
        claimed_at = actual["attempt"]["claimed_at"]
        if outcome == "claimed" and not entry <= claimed_at <= now:
            return False
        expected = expected_transition(source, outcome, entry, claimed_at)
        return actual == expected and now < min(
            source["browser"]["idle_expires_at"],
            source["browser"]["absolute_expires_at"],
            source["attempt"]["expires_at"],
            claim_expiry(source, entry) if outcome == "claimed" else 9_007_199_254_740_991,
        )
    except (KeyError, TypeError, ValueError):
        return False


def leaf_paths(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaf_paths(child, path + (key,))
    else:
        yield path


def corrupt(value, path):
    result = deepcopy(value)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = ("synthetic-mismatch", target[path[-1]])
    return result


@dataclass
class Slot:
    caller: str
    reference: str
    timer: str
    operation_deadline: int
    claim_deadline: int
    phase: str = "operation"
    child: str | None = None
    used: bool = False
    sql_attempts: int = 0


@dataclass
class Slots:
    entries: dict[str, Slot] = field(default_factory=dict)

    def reserve(self, reference, caller, now=0):
        if len(self.entries) >= 32 or reference in self.entries:
            return False
        self.entries[reference] = Slot(caller, reference, "timer-" + reference, now + 5000, now + 60000)
        return True

    def stage(self, reference, caller, child, now):
        s = self.entries.get(reference)
        if not s or s.phase != "operation" or s.caller != caller or now >= s.operation_deadline:
            return False
        s.phase, s.child = "staged_claim", child
        return True

    def retain(self, reference, caller, child, confirmed_commit, now):
        s = self.entries.get(reference)
        if not s or s.phase != "staged_claim" or s.caller != caller or s.child != child:
            return False
        if not confirmed_commit or now >= s.operation_deadline:
            self.entries.pop(reference)
            return False
        s.phase = "retained_claim"
        return True

    def fail_once(self, reference, caller, child, now):
        s = self.entries.get(reference)
        if not s or s.phase != "retained_claim" or s.used or s.caller != caller or s.child != child:
            return False
        if now >= s.claim_deadline:
            self.entries.pop(reference)
            return False
        s.used, s.phase = True, "terminal_cleanup"
        s.sql_attempts += 1
        return True

    def cleanup_finish(self, reference, child):
        s = self.entries.get(reference)
        if not s or s.phase != "terminal_cleanup" or s.child != child:
            return False
        self.entries.pop(reference)
        return True

    def expire(self, reference, timer):
        s = self.entries.get(reference)
        if not s or s.timer != timer:
            return False
        self.entries.pop(reference)
        return True


@dataclass
class StartupGraph:
    owner: str = "runtime-owner"
    supervisor: str = "owned-claim-supervisor"
    helper: str = "owned-startup-helper"
    token: str = "private-startup-token"
    slot_live: bool = True
    supervisor_live: bool = True
    children: dict[str, tuple[str, str]] = field(default_factory=dict)
    stopped: set[str] = field(default_factory=set)

    def child_report(self, child, actual_parent, helper, token):
        # A process report is actionable only with the retained helper, exact
        # supervisor/parent identity, and private startup token. This is an
        # abstract lifecycle model, not observation of actual OTP processes.
        if (actual_parent, helper, token) != (self.supervisor, self.helper, self.token):
            return False
        if not self.supervisor_live:
            return False
        self.children[child] = (actual_parent, token)
        if not self.slot_live:
            self.children.pop(child)
            self.stopped.add(child)
            return False
        return True

    def owner_shutdown(self):
        self.slot_live = False
        self.supervisor_live = False
        for child, (parent, token) in list(self.children.items()):
            if (parent, token) == (self.supervisor, self.token):
                self.children.pop(child)
                self.stopped.add(child)
        self.stopped.update((self.supervisor, self.helper))


class ContractModels(unittest.TestCase):
    def test_source_whole_snapshot_comparison_rejects_every_leaf_mutation(self):
        source = source_snapshot()
        paths = list(leaf_paths(source))
        self.assertGreater(len(paths), 80)
        for path in paths:
            with self.subTest(path=path):
                self.assertNotEqual(corrupt(source, path), source)
        self.assertNotEqual({**source, "extra": None}, source)

    def test_revision_only_cas_misses_audit_only_claim_race(self):
        source = source_snapshot()
        actual = expected_transition(source, "claimed")
        self.assertEqual(actual["browser"]["revision"], source["browser"]["revision"])
        self.assertNotEqual(actual, source)
        audit_only = deepcopy(source)
        audit_only["browser"]["audit_sequence"] += 1
        self.assertNotEqual(audit_only, source)

    def test_claim_exact_poststate_rejects_every_leaf_mutation_and_extra_key(self):
        source = source_snapshot()
        result = expected_transition(source, "claimed")
        self.assertTrue(accepted_poststate(source, result, "claimed"))
        for path in leaf_paths(result):
            with self.subTest(path=path):
                self.assertFalse(accepted_poststate(source, corrupt(result, path), "claimed"))
        self.assertFalse(accepted_poststate(source, {**result, "extra": None}, "claimed"))

    def test_reject_exact_poststate_rejects_every_leaf_mutation_and_extra_key(self):
        source = source_snapshot()
        result = expected_transition(source, "provider_rejected")
        self.assertTrue(accepted_poststate(source, result, "provider_rejected"))
        for path in leaf_paths(result):
            with self.subTest(path=path):
                self.assertFalse(accepted_poststate(source, corrupt(result, path), "provider_rejected"))
        self.assertFalse(accepted_poststate(source, {**result, "extra": None}, "provider_rejected"))

    def test_claim_time_bounds_and_exclusive_expiry(self):
        source = source_snapshot()
        for claimed_at in (109, 115):
            self.assertFalse(accepted_poststate(source, expected_transition(source, "claimed", claimed_at=claimed_at), "claimed"))
        result = expected_transition(source, "claimed")
        self.assertFalse(accepted_poststate(source, result, "claimed", now=170))
        self.assertTrue(accepted_poststate(source, result, "claimed", now=169))

    def test_claim_expiry_uses_initial_entry_and_never_rebases_after_wait(self):
        source = source_snapshot()
        fixed = claim_expiry(source, 110)
        self.assertEqual(fixed, 170)
        self.assertLess(fixed, claim_expiry(source, 119))
        for field_name in ("idle_expires_at", "absolute_expires_at"):
            shorter = deepcopy(source)
            shorter["browser"][field_name] = 150
            self.assertEqual(claim_expiry(shorter, 110), 150)
        source["attempt"]["expires_at"] = 140
        self.assertEqual(claim_expiry(source, 110), 140)

    def test_combined_slot_cap_is_unchanged_through_staging_and_retention(self):
        slots = Slots()
        for n in range(32):
            self.assertTrue(slots.reserve(str(n), "caller-" + str(n)))
        self.assertFalse(slots.reserve("33", "foreign"))
        self.assertTrue(slots.stage("0", "caller-0", "child-0", 100))
        self.assertEqual(len(slots.entries), 32)
        self.assertTrue(slots.retain("0", "caller-0", "child-0", True, 200))
        self.assertEqual(len(slots.entries), 32)
        self.assertFalse(slots.reserve("33", "foreign"))

    def test_foreign_caller_child_or_reference_cannot_transfer_a_slot(self):
        slots = Slots()
        self.assertTrue(slots.reserve("r", "caller"))
        self.assertFalse(slots.stage("r", "foreign", "child", 100))
        self.assertFalse(slots.stage("foreign", "caller", "child", 100))
        self.assertTrue(slots.stage("r", "caller", "child", 100))
        self.assertFalse(slots.retain("r", "foreign", "child", True, 200))
        self.assertFalse(slots.retain("r", "caller", "foreign", True, 200))
        self.assertEqual(len(slots.entries), 1)

    def test_unknown_commit_has_no_retained_or_resumable_claim(self):
        slots = Slots()
        self.assertTrue(slots.reserve("r", "caller"))
        self.assertTrue(slots.stage("r", "caller", "child", 100))
        self.assertFalse(slots.retain("r", "caller", "child", False, 200))
        self.assertNotIn("r", slots.entries)
        self.assertFalse(slots.retain("r", "caller", "child", True, 201))

    def test_late_setup_and_retention_cannot_reset_original_deadline(self):
        slots = Slots()
        self.assertTrue(slots.reserve("r", "caller"))
        self.assertFalse(slots.stage("r", "caller", "child", 5000))
        self.assertTrue(slots.stage("r", "caller", "child", 4999))
        self.assertFalse(slots.retain("r", "caller", "child", True, 5000))
        self.assertNotIn("r", slots.entries)

    def test_explicit_failure_consumes_before_one_sql_attempt_and_denies_second_use(self):
        slots = Slots()
        slots.reserve("r", "caller")
        slots.stage("r", "caller", "child", 100)
        slots.retain("r", "caller", "child", True, 200)
        self.assertFalse(slots.fail_once("r", "foreign", "child", 6000))
        self.assertFalse(slots.fail_once("r", "caller", "foreign", 6000))
        self.assertTrue(slots.fail_once("r", "caller", "child", 6000))
        self.assertEqual(slots.entries["r"].phase, "terminal_cleanup")
        self.assertEqual(len(slots.entries), 1)
        self.assertFalse(slots.fail_once("r", "caller", "child", 6001))
        self.assertEqual(slots.entries["r"].sql_attempts, 1)
        self.assertFalse(slots.cleanup_finish("r", "foreign"))
        self.assertTrue(slots.cleanup_finish("r", "child"))
        self.assertFalse(slots.cleanup_finish("r", "child"))
        self.assertEqual(len(slots.entries), 0)

    def test_spoofed_timer_cannot_retire_slot_and_expiry_never_executes_sql(self):
        slots = Slots()
        slots.reserve("r", "caller")
        self.assertFalse(slots.expire("r", "foreign-timer"))
        saved = slots.entries["r"]
        self.assertTrue(slots.expire("r", "timer-r"))
        self.assertEqual(saved.sql_attempts, 0)
        self.assertFalse(slots.expire("r", "timer-r"))

    def test_late_child_cleanup_requires_owned_parent_helper_and_token(self):
        graph = StartupGraph(slot_live=False)
        for parent, helper, token in (
            ("foreign-parent", graph.helper, graph.token),
            (graph.supervisor, "foreign-helper", graph.token),
            (graph.supervisor, graph.helper, "foreign-token"),
        ):
            self.assertFalse(graph.child_report("foreign-child", parent, helper, token))
            self.assertNotIn("foreign-child", graph.stopped)
        self.assertFalse(graph.child_report("late-owned-child", graph.supervisor, graph.helper, graph.token))
        self.assertIn("late-owned-child", graph.stopped)
        self.assertEqual(graph.children, {})

    def test_owned_parent_shutdown_retires_children_and_refuses_later_start(self):
        graph = StartupGraph()
        self.assertTrue(graph.child_report("owned-child", graph.supervisor, graph.helper, graph.token))
        graph.children["foreign-child"] = ("foreign-parent", "foreign-token")
        graph.owner_shutdown()
        self.assertIn("owned-child", graph.stopped)
        self.assertIn(graph.supervisor, graph.stopped)
        self.assertIn(graph.helper, graph.stopped)
        self.assertNotIn("foreign-child", graph.stopped)
        self.assertIn("foreign-child", graph.children)
        self.assertFalse(graph.child_report("later-child", graph.supervisor, graph.helper, graph.token))


if __name__ == "__main__":
    unittest.main(verbosity=2)
