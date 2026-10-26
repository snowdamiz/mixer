#!/usr/bin/env python3
"""Authored adversarial contract model, not Android or production implementation.

The model deliberately uses a native target that resolves the field's *current*
Editable on close. Its assertions test ordering and identity, not Android success.
"""
from __future__ import annotations
from dataclasses import dataclass
import unittest


class Fatal(BaseException):
    pass


@dataclass(eq=False)
class Attempt:
    editable: object
    target: "Target | None" = None
    retired: bool = False
    close_claimed: bool = False
    close_outcome: str = "not_requested"


class Target:
    def __init__(self, field):
        self.field = field
        self.close_calls = 0
        self.edited = []
        self.close_hook = lambda: None

    def close(self):
        self.close_calls += 1
        # Models EIC's retained TextView/current Editable hazard, not its body.
        self.edited.append(self.field.editable)
        self.close_hook()


class Field:
    def __init__(self):
        self.editable = object()
        self.current = None
        self.phase = "idle"
        self.native_frame = None
        self.callback_frame = None
        self.quarantined = self.terminal = False
        self.events = []
        self.close_order = []
        self.primary = self.first_fatal = None
        self.presentation = object()
        self.native_create_calls = self.native_dispatch_calls = 0
        self.max_native_depth = 0
        self.dispose_calls = 0
        self.owner_pending = self.owner_token = None
        self.queued = None
        self.permanent_sweep_claimed = False
        self.serial = 1
        self.lifecycle_frame = None
        self.lifecycle_denials = set()
        self.active_lifecycle_hooks = set()

    def remember(self, failure):
        if self.primary is None:
            self.primary = failure
        if isinstance(failure, Fatal) and self.first_fatal is None:
            self.first_fatal = failure

    def busy(self):
        return (self.phase in ("creating", "closing") or self.native_frame is not None
                or self.lifecycle_frame is not None)

    def dispose_once(self):
        # Central guard protects direct coordinator leave as well as owner close.
        if self.busy():
            return False
        if not self.dispose_calls:
            self.dispose_calls += 1
        return True

    def request_owner_close(self, token, scheduler="accept"):
        self.owner_pending, self.owner_token = self, token
        if self.busy():
            if scheduler == "accept":
                self.queued = (self, token)
            return
        self.settle_owner()

    def settle_owner(self):
        if self.owner_pending is None or self.busy():
            return
        resource, token = self.owner_pending, self.owner_token
        # Actual accepted owner clears before close; no callback may intervene
        # between its busy check and this synchronous close invocation.
        self.owner_pending = self.owner_token = None
        if not resource.dispose_once():
            raise AssertionError("owner would consume pending on a disposal no-op")
        return token

    def run_queued(self, resource=None, token=None):
        queued, self.queued = self.queued, None
        if queued is None:
            return
        resource, token = queued if resource is None else (resource, token)
        if self.owner_pending is resource and self.owner_token is token:
            return self.settle_owner()

    def quarantine(self, failure):
        self.remember(failure)
        self.quarantined = self.terminal = True
        if self.current:
            self.current.retired = True

    def create(self, creator_hook=lambda: None):
        if self.quarantined or self.terminal or self.busy() or self.lifecycle_denials:
            return None
        if self.current:
            self.revoke()
            if self.quarantined:
                return None
        attempt = Attempt(self.editable)
        self.current, self.phase = attempt, "creating"
        try:
            self.native_create_calls += 1
            creator_hook()
            attempt.target = Target(self)
            if self.editable is not attempt.editable:
                self.quarantine(RuntimeError("creation changed Editable"))
                return None
            if self.terminal or attempt.retired:
                return None
            self.phase = "open"
            return attempt
        except BaseException as failure:
            attempt.close_outcome = "failed_uncertain"
            self.quarantine(failure)
            raise
        finally:
            if self.phase == "creating":
                self.phase = "idle"
            if attempt.retired and attempt.target and not self.quarantined:
                self.flush_close()

    def revoke(self):
        attempt = self.current
        if attempt is None:
            return
        attempt.retired = True
        if self.native_frame is None and self.lifecycle_frame is None and self.phase != "creating":
            self.flush_close()

    def flush_close(self):
        attempt = self.current
        if attempt is None or attempt.close_claimed:
            return
        if self.busy():
            return
        attempt.close_claimed = True  # consume before externally controlled close
        attempt.close_outcome = "attempted"
        if self.editable is not attempt.editable or attempt.target is None:
            attempt.close_outcome = "failed_uncertain"
            self.quarantine(RuntimeError("not exact target and Editable"))
            return
        self.phase = "closing"
        try:
            self.close_order.append(attempt)
            attempt.target.close()
            if self.editable is not attempt.editable:
                raise RuntimeError("close changed Editable")
            attempt.close_outcome = "returned"  # never asserts batch reclamation
        except BaseException as failure:
            attempt.close_outcome = "failed_uncertain"
            self.quarantine(failure)
        finally:
            self.phase = "quarantined" if self.quarantined else "idle"
            if not self.quarantined:
                self.current = None

    def replace_editable(self):
        if self.busy() or self.current is not None or self.quarantined:
            return False
        self.editable = object()
        return True

    def dispatch(self, attempt, hook=lambda: None):
        if (self.busy() or self.terminal or self.quarantined or self.lifecycle_denials
                or attempt is not self.current or attempt.retired):
            return False
        self.native_frame = (attempt, attempt.target, attempt.editable)
        self.native_dispatch_calls += 1
        self.max_native_depth = max(self.max_native_depth, 1)
        failure = None
        result = False
        try:
            hook()
            # A captured delegate suffix can return after retirement, never
            # reacquiring a live token or doing fresh caller-requested input.
            assert self.editable is attempt.editable
            result = not attempt.retired and not self.terminal
        except BaseException as caught:
            failure = caught
            self.quarantine(caught)
            self.revoke()
        finally:
            self.native_frame = None
            if attempt.retired:
                self.flush_close()
        if self.first_fatal:
            raise self.first_fatal
        if failure:
            raise failure
        return result

    def lifecycle(self, reason, hook=lambda: None, main=True):
        # The main check precedes scalar retirement and native platform work.
        if not main:
            raise RuntimeError("main required")
        if reason in self.active_lifecycle_hooks or len(self.active_lifecycle_hooks) >= 8:
            # Same-hook reentry cannot grow the call stack without bound.
            return False
        outer = self.lifecycle_frame is None
        attempt = self.current
        if outer:
            self.lifecycle_frame = (reason, attempt, self.editable)
        self.active_lifecycle_hooks.add(reason)
        self.lifecycle_denials.add(reason)
        failure = None
        try:
            self.revoke()  # Must defer: lifecycle frame already counts as busy.
            hook()        # Standalone platform super and callbacks.
        except BaseException as caught:
            failure = caught
            self.quarantine(caught)
            self.revoke()
        finally:
            self.active_lifecycle_hooks.remove(reason)
            if outer:
                self.lifecycle_frame = None
            if outer and attempt and attempt.retired:
                self.flush_close()
        if self.first_fatal:
            raise self.first_fatal
        if failure:
            raise failure
        return True

    def observed_gain(self, reason, actual_current_facts):
        # This only removes a denial and cannot itself mint live authority.
        if actual_current_facts and not self.busy():
            self.lifecycle_denials.discard(reason)

    def selection_callback(self, hook=lambda: None):
        if self.native_frame is None or self.callback_frame is not None:
            return False
        captured = self.native_frame
        self.callback_frame = captured
        try:
            hook()
            # Original callback entered live may finish after revoke. Merely
            # installing a later cleanup Mutation does not repair this suffix.
            assert captured == self.native_frame and captured[2] is self.editable
            if not captured[0].retired and not self.terminal:
                self.events.append("interaction")
            return True
        finally:
            self.callback_frame = None

    def temporary_echo(self):
        self.serial += 1
        self.presentation = object()
        # Compatible binding and identity are intentionally retained.

    def permanent_sweep(self):
        # Must be separate from consumed temporary serial claims; terminal can
        # arrive at the same serial, including Long.MAX_VALUE.
        self.terminal = True
        if not self.permanent_sweep_claimed:
            self.permanent_sweep_claimed = True
            self.revoke()


class ContractTests(unittest.TestCase):
    def test_create_serialized_before_super_and_close(self):
        f = Field()
        nested = []
        first = f.create(lambda: nested.append(f.create()))
        self.assertEqual([None], nested)
        first.target.close_hook = lambda: nested.append(f.create())
        second = f.create()
        self.assertEqual([None, None], nested)
        self.assertEqual(2, f.native_create_calls)
        self.assertEqual([first.editable], first.target.edited)
        self.assertIs(second.editable, first.editable)
        self.assertEqual(1, first.target.close_calls)

    def test_scalar_revoke_and_exact_callback_postsuper_suffix(self):
        f = Field(); a = f.create(); trace = []
        def native():
            def callback():
                f.revoke()
                trace.extend([f.create(), f.dispatch(a), f.replace_editable(), a.target.close_calls])
            self.assertTrue(f.selection_callback(callback))
            self.assertEqual(0, a.target.close_calls)
        self.assertFalse(f.dispatch(a, native))
        self.assertEqual([None, False, False, 0], trace)
        self.assertEqual([], f.events)
        self.assertEqual(1, a.target.close_calls)
        self.assertEqual("returned", a.close_outcome)

    def test_compatible_echo_preserves_connection_and_buffer(self):
        f = Field(); a = f.create(); old = f.presentation
        self.assertTrue(f.dispatch(a, lambda: f.selection_callback(f.temporary_echo)))
        self.assertIsNot(old, f.presentation)
        self.assertIs(a, f.current)
        self.assertIs(a.editable, f.editable)
        self.assertEqual(0, a.target.close_calls)
        self.assertEqual(["interaction"], f.events)

    def test_stale_explicit_close_never_closes_successor(self):
        f = Field(); a = f.create(); b = f.create()
        a.retired = True  # stale proxy's local consumption only
        self.assertFalse(f.dispatch(a))
        self.assertIs(b, f.current)
        self.assertEqual(0, b.target.close_calls)
        self.assertEqual(1, a.target.close_calls)

    def test_editable_mismatch_quarantines_before_native_close(self):
        f = Field(); a = f.create(); f.editable = object()
        f.revoke()
        self.assertTrue(f.quarantined)
        self.assertEqual(0, a.target.close_calls)
        self.assertIsNone(f.create())
        self.assertEqual("failed_uncertain", a.close_outcome)

    def test_throwing_close_is_once_uncertain_and_first_fatal_retained(self):
        f = Field(); a = f.create(); ordinary = RuntimeError("primary"); fatal = Fatal("first fatal")
        f.remember(ordinary)
        def close():
            f.remember(fatal)
            raise Fatal("later fatal")
        a.target.close_hook = close
        f.revoke(); f.revoke()
        self.assertIs(ordinary, f.primary)
        self.assertIs(fatal, f.first_fatal)
        self.assertEqual(1, a.target.close_calls)
        self.assertEqual("failed_uncertain", a.close_outcome)
        self.assertIsNone(f.create())

    def test_creation_revoked_before_target_return_closes_after_creator_unwinds(self):
        f = Field(); nested = []
        def creator():
            f.revoke(); nested.extend([f.create(), f.replace_editable()])
        self.assertIsNone(f.create(creator))
        self.assertEqual([None, False], nested)
        self.assertEqual(1, len(f.close_order))
        self.assertEqual(1, f.close_order[0].target.close_calls)

    def test_terminal_same_serial_and_exhausted_serial_still_sweep(self):
        for serial in (7, 2**63 - 1):
            f = Field(); a = f.create(); f.serial = serial
            f.permanent_sweep(); f.permanent_sweep()
            self.assertEqual(1, a.target.close_calls)
            self.assertTrue(f.permanent_sweep_claimed)

    def test_direct_dispose_blocked_and_exact_owner_pending_resumes(self):
        f = Field(); a = f.create(); token = object()
        def native():
            f.permanent_sweep()
            f.request_owner_close(token)
            self.assertFalse(f.dispose_once())  # coordinator leave bypass attempt
            self.assertIs(token, f.owner_token)
            self.assertEqual(0, f.dispose_calls)
        f.dispatch(a, native)
        self.assertEqual(0, f.dispose_calls)
        self.assertIs(token, f.run_queued())
        self.assertEqual(1, f.dispose_calls)

    def test_rejected_scheduler_preserves_pending_without_completion_claim(self):
        for scheduler in ("reject", "throw"):
            f = Field(); a = f.create(); token = object()
            f.dispatch(a, lambda: f.request_owner_close(token, scheduler))
            self.assertIs(token, f.owner_token)
            self.assertEqual(0, f.dispose_calls)
            self.assertIsNone(f.queued)

    def test_stale_handler_work_cannot_consume_new_pending(self):
        f = Field(); a = f.create(); old, new = object(), object()
        f.dispatch(a, lambda: f.request_owner_close(old))
        f.owner_token = new
        self.assertIsNone(f.run_queued())
        self.assertIs(new, f.owner_token)
        self.assertEqual(0, f.dispose_calls)

    def test_reentrant_public_dispatch_is_bounded(self):
        f = Field(); a = f.create()
        self.assertTrue(f.dispatch(a, lambda: self.assertFalse(f.dispatch(a))))
        self.assertEqual(1, f.native_dispatch_calls)
        self.assertEqual(1, f.max_native_depth)

    def test_standalone_lifecycle_counts_before_revoke_through_super(self):
        for reason in ("focus", "window_focus", "visibility", "window_visibility", "aggregated", "detach"):
            f = Field(); a = f.create(); token = object(); observed = []
            def platform_super():
                observed.extend([a.target.close_calls, f.busy(), f.create(), f.dispose_once()])
                f.request_owner_close(token)
            f.lifecycle(reason, platform_super)
            self.assertEqual([0, True, None, False], observed)
            self.assertEqual(1, a.target.close_calls)
            self.assertIs(token, f.run_queued())
            self.assertEqual(1, f.dispose_calls)

    def test_lifecycle_loss_stays_unavailable_past_public_hook_return(self):
        f = Field(); a = f.create(); f.lifecycle("detach")
        # Models hidden TextView internal detach after public hook has returned;
        # attached/window getters may still reflect pre-detach facts here.
        self.assertIsNone(f.create())
        f.observed_gain("detach", False)
        self.assertIsNone(f.create())
        f.observed_gain("detach", True)
        successor = f.create()
        self.assertIsNotNone(successor)
        self.assertFalse(f.dispatch(a))

    def test_known_nested_lifecycle_joins_without_early_close_and_same_hook_is_bounded(self):
        f = Field(); a = f.create(); trace = []
        def visibility_super():
            trace.extend([a.target.close_calls, f.busy(), f.lifecycle("visibility")])
        def focus_super():
            self.assertTrue(f.lifecycle("visibility", visibility_super))
            self.assertEqual(0, a.target.close_calls)
        self.assertTrue(f.lifecycle("focus", focus_super))
        self.assertEqual([0, True, False], trace)
        self.assertEqual(1, a.target.close_calls)

    def test_lifecycle_offmain_refuses_before_revoke_or_native_super(self):
        f = Field(); a = f.create(); touched = []
        with self.assertRaisesRegex(RuntimeError, "main required"):
            f.lifecycle("focus", lambda: touched.append(True), main=False)
        self.assertEqual([], touched)
        self.assertEqual(0, a.target.close_calls)
        self.assertFalse(a.retired)

    def test_lifecycle_original_fatal_wins_later_cleanup_fatal(self):
        f = Field(); a = f.create(); first, second = Fatal("super"), Fatal("close")
        def throwing_close():
            raise second
        def platform_super():
            raise first
        a.target.close_hook = throwing_close
        with self.assertRaises(Fatal) as caught:
            f.lifecycle("focus", platform_super)
        self.assertIs(first, caught.exception)
        self.assertIs(first, f.first_fatal)
        self.assertEqual(1, a.target.close_calls)
        self.assertEqual("failed_uncertain", a.close_outcome)

    def test_plain_delegate_throw_retires_without_prior_retirement_request(self):
        f = Field(); a = f.create(); original = RuntimeError("delegate failed after prefix")
        def native():
            raise original
        with self.assertRaises(RuntimeError) as caught:
            f.dispatch(a, native)
        self.assertIs(original, caught.exception)
        self.assertIs(original, f.primary)
        self.assertTrue(f.terminal)
        self.assertEqual(1, a.target.close_calls)
        self.assertEqual("returned", a.close_outcome)
        self.assertIsNone(f.create())

    def test_plain_delegate_ordinary_primary_and_first_cleanup_fatal(self):
        f = Field(); a = f.create(); original, fatal = RuntimeError("delegate"), Fatal("close")
        def native():
            raise original
        def close():
            raise fatal
        a.target.close_hook = close
        with self.assertRaises(Fatal) as caught:
            f.dispatch(a, native)
        self.assertIs(fatal, caught.exception)
        self.assertIs(original, f.primary)
        self.assertIs(fatal, f.first_fatal)
        self.assertEqual(1, a.target.close_calls)
        self.assertEqual("failed_uncertain", a.close_outcome)
        self.assertIsNone(f.create())

    def test_inaccessible_creator_target_is_uncertain_without_fabricated_reclaim(self):
        f = Field(); inaccessible = []; original = Fatal("creator after allocation")
        def creator():
            inaccessible.append(Target(f))
            raise original
        with self.assertRaises(Fatal) as caught:
            f.create(creator)
        self.assertIs(original, caught.exception)
        self.assertEqual(0, inaccessible[0].close_calls)
        self.assertEqual("failed_uncertain", f.current.close_outcome)
        self.assertTrue(f.quarantined)
        self.assertIsNone(f.create())

    def test_entry_refusal_is_not_fabricated_native_uncertainty(self):
        f = Field(); a = f.create(); f.lifecycle_denials.add("window_focus")
        self.assertFalse(f.dispatch(a))
        self.assertEqual(0, f.native_dispatch_calls)
        self.assertIsNone(f.primary)
        self.assertFalse(f.quarantined)
        self.assertEqual(0, a.target.close_calls)

    def test_construction_callback_never_reads_unassigned_record_or_buffer(self):
        touched = []
        def constructor_callback(record, main):
            if not main:
                raise RuntimeError("main required")
            if record is None:
                touched.append("bootstrap super")
                return
            raise AssertionError("not a construction callback")
        constructor_callback(None, True)
        self.assertEqual(["bootstrap super"], touched)
        with self.assertRaisesRegex(RuntimeError, "main required"):
            constructor_callback(None, False)
        self.assertEqual(["bootstrap super"], touched)

    def test_counterexample_close_after_successor_changes_successor_buffer(self):
        f = Field(); a = f.create()
        successor = object(); f.editable = successor
        a.target.close()  # Intentionally unsafe old-target policy.
        self.assertIs(successor, a.target.edited[0])

    def test_counterexample_owner_only_guard_misses_direct_dispose(self):
        f = Field(); a = f.create(); token = object()
        def native():
            f.request_owner_close(token)
            # Intentionally unsafe canonical-style direct leave/dispose route.
            f.dispose_calls += 1
        f.dispatch(a, native)
        self.assertEqual(1, f.dispose_calls)
        self.assertIs(token, f.owner_token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
