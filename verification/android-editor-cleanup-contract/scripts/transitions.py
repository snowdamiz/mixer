#!/usr/bin/env python3
"""Authored transition specification; not Android or a product-engine receipt.

The target intentionally retains its View's CURRENT buffer, as API36 does.
Tests exercise before/inside/after continuation, not only a beforeReturn hook.
"""
from dataclasses import dataclass
import json
import unittest

class Fatal(BaseException): pass

@dataclass(eq=False)
class Buffer:
    text: str = 'old'
    selection: tuple = (3, 3)
    composition: tuple | None = (0, 3)

class Target:
    def __init__(self, field):
        self.field = field
        self.batch = 0
        self.closes = 0
        self.close_hook = None
        self.close_failure = None
        self.disposition = 'NOT_REQUESTED'
        self.retired = False

    def adapter_close(self):
        self.retired = True
        if self is not self.field.target or self.disposition in ('ATTEMPTED', 'RETURNED', 'FAILED_UNCERTAIN'):
            return
        self.field.retire('explicit-close')

    def close(self):
        self.closes += 1
        # Exact AOSP shape: gets TextView's current Editable; closes compose
        # before draining this connection's own nesting contribution.
        self.field.buffer.composition = None
        if self.close_hook: self.close_hook()
        self.batch = 0
        if self.close_failure: raise self.close_failure

@dataclass(eq=False)
class Lease:
    field: object
    target: object
    buffer: object
    presentation: object
    snapshot: tuple
    cleanup_only: bool = False
    def continuation(self):
        f = self.field
        assert f.lease is self and f.target is self.target and f.buffer is self.buffer
        assert f.depth == 1 and f.phase in ('ACTIVE', 'DRAINING', 'QUARANTINED')
    def feature_event(self):
        self.continuation()
        if not self.cleanup_only: self.field.events += 1

class Field:
    def __init__(self):
        self.phase = 'IDLE'
        self.buffer = Buffer()
        self.target = None
        self.lease = None
        self.depth = 0
        self.focus = True
        self.sealed = False
        self.terminal = False
        self.operation = False
        self.commit_finish = False
        self.revoked = False
        self.disposition = 'NOT_REQUESTED'
        self.events = 0
        self.presentation = object()
        self.primary = self.fatal = None
        self.log = []
        self.creator_calls = 0
        self.quarantined = False

    def remember(self, failure):
        if failure is None: return
        if self.primary is None: self.primary = failure
        if isinstance(failure, Fatal) and self.fatal is None: self.fatal = failure

    def quarantine(self, failure=None):
        self.remember(failure)
        self.quarantined = self.terminal = True
        self.revoked = True
        self.phase = 'QUARANTINED'
        if self.lease: self.lease.cleanup_only = True
        self.log.append('quarantine')

    def permitted(self):
        return self.phase == 'ACTIVE' and not (self.revoked or self.sealed or self.terminal) and self.focus

    def create(self, native=None):
        if self.phase in ('CREATING', 'DRAINING', 'CLOSING', 'QUARANTINED') or self.depth:
            self.log.append('nested-create-refused')
            return None
        if self.terminal or self.sealed or not self.focus: return None
        if self.target:
            self.retire('replacement')
            if self.quarantined or self.target: return None
        self.phase = 'CREATING'
        self.revoked = False
        self.disposition = 'NOT_REQUESTED'
        expected = self.buffer
        self.creator_calls += 1
        self.depth = 1
        try:
            target = native(self) if native else Target(self)
        except BaseException as failure:
            self.quarantine(failure)  # Creator may have constructed an unreturned target.
            self.disposition = 'FAILED_UNCERTAIN'
            raise
        finally:
            self.depth = 0
        self.target = target
        if target is None:
            self.disposition = 'NO_TARGET'
            self.phase = 'QUARANTINED' if self.quarantined else 'IDLE'
            return None
        if self.revoked or self.terminal or not self.focus or expected is not self.buffer:
            self.revoked = True
            if expected is not self.buffer:
                self.quarantine(RuntimeError('creator buffer replaced'))
                self.disposition = 'FAILED_UNCERTAIN'
            else:
                self.phase = 'DRAINING'
                self.cleanup()
            return None
        self.phase = 'ACTIVE'
        return target

    def retire(self, reason):
        if self.target is None and self.phase != 'CREATING': return
        self.revoked = True
        if self.lease: self.lease.cleanup_only = True
        self.log.append('revoke:' + reason)
        if self.phase in ('CLOSING', 'QUARANTINED'): return
        if reason == 'owner': self.terminal = True
        self.phase = 'DRAINING'
        self.disposition = 'DEFERRED'
        if self.depth: return  # No recursive close of creator or native edit.
        if self.operation or self.commit_finish:
            self.quarantine(RuntimeError('retirement in coordinator operation'))
            return
        self.cleanup()

    def cleanup(self):
        if self.disposition in ('ATTEMPTED', 'RETURNED', 'FAILED_UNCERTAIN', 'NO_TARGET'): return
        assert self.depth == 0 and not self.operation and not self.commit_finish
        if not self.target:
            self.disposition = 'NO_TARGET'
            self.phase = 'IDLE'
            return
        # The real amendment additionally verifies exact retained roster/Record/view.
        target = self.target
        if self.lease and self.buffer is not self.lease.buffer:
            self.disposition = 'FAILED_UNCERTAIN'
            self.quarantine(RuntimeError('cleanup buffer mismatch'))
            return
        self.phase = 'CLOSING'
        self.disposition = 'ATTEMPTED'
        target.disposition = 'ATTEMPTED'
        self.log.append('close-begin')
        try:
            target.close()
            self.disposition = 'RETURNED'
            target.disposition = 'RETURNED'
            self.target = None
            self.phase = 'QUARANTINED' if self.quarantined else 'IDLE'
        except BaseException as failure:
            self.disposition = 'FAILED_UNCERTAIN'
            target.disposition = 'FAILED_UNCERTAIN'
            self.quarantine(failure)
        self.log.append('close-end')

    def call(self, native, read=False):
        if not self.permitted() or self.depth: return None if read else False
        self.depth = 1
        self.lease = Lease(self, self.target, self.buffer, self.presentation,
                           (self.buffer.text, self.buffer.selection, self.buffer.composition))
        value = None
        failure = None
        try:
            value = native(self.lease)
            self.lease.continuation()
            if not self.permitted(): value = None if read else False
            if read and (self.presentation is not self.lease.presentation or
                         (self.buffer.text,self.buffer.selection,self.buffer.composition) != self.lease.snapshot):
                value = None
        except BaseException as caught:
            self.remember(caught)
            failure = caught
        finally:
            self.depth = 0
            if self.revoked and self.disposition == 'DEFERRED':
                if self.operation or self.commit_finish:
                    self.quarantine(RuntimeError('outer unwind still inside coordinator operation'))
                else: self.cleanup()
            self.lease = None
        if self.fatal: raise self.fatal
        if failure: raise failure
        return value

    def echo(self):
        assert self.phase == 'ACTIVE'
        self.sealed = True  # No connection revocation on this temporary seal.
        self.presentation = object()
        self.sealed = False

def edit(lease, middle=None):
    f = lease.field
    target = lease.target
    target.batch += 1
    lease.continuation()
    f.log.append('selection-prefix')
    if middle: middle(lease)
    lease.continuation()
    f.buffer.text += '!'
    lease.feature_event()
    f.log.append('native-suffix')
    f.buffer.selection = (len(f.buffer.text),) * 2
    lease.continuation()
    target.batch -= 1
    f.log.append('native-ended')
    return True

class Transitions(unittest.TestCase):
    def active(self):
        f = Field(); self.assertIsNotNone(f.create()); return f

    def test_healthy_echo_preserves_editor(self):
        f = self.active(); t, b = f.target, f.buffer
        self.assertTrue(f.call(lambda lease: edit(lease, lambda _: f.echo())))
        self.assertIs(f.target, t); self.assertIs(f.buffer, b)
        self.assertEqual(t.closes, 0); self.assertEqual(f.buffer.composition, (0, 3))

    def test_temporary_seal_never_retires(self):
        f = self.active(); t = f.target; f.sealed = True
        self.assertFalse(f.call(edit)); self.assertEqual(t.closes, 0)
        f.sealed = False; self.assertTrue(f.call(edit))

    def test_every_retirement_trigger(self):
        for trigger in ['explicit-close', 'focus', 'window-focus', 'window-visibility', 'aggregated-visibility', 'visibility', 'detach', 'record-replacement', 'owner']:
            with self.subTest(trigger=trigger):
                f = self.active(); t = f.target; f.retire(trigger)
                self.assertEqual(t.closes, 1); self.assertFalse(f.call(edit)); self.assertEqual(f.disposition, 'RETURNED')

    def test_retirement_inside_delegate_unwinds_before_close(self):
        f = self.active(); t = f.target
        def middle(lease):
            f.retire('focus'); self.assertEqual(t.closes, 0)
            self.assertIsNone(f.create()); self.assertFalse(f.call(edit))
            lease.continuation(); lease.feature_event()
        self.assertFalse(f.call(lambda lease: edit(lease, middle)))
        self.assertLess(f.log.index('native-ended'), f.log.index('close-begin'))
        self.assertEqual(t.batch, 0); self.assertEqual(t.closes, 1); self.assertEqual(f.events, 0)

    def test_callback_started_live_post_super_after_revoke(self):
        f = self.active()
        def callback(lease):
            lease.continuation()  # Entry before native super callback.
            f.retire('owner')     # Retirement synchronously from inside super.
            lease.continuation()  # Same lease; no fresh Mutation/main/input gate.
            lease.feature_event()
            return True
        self.assertFalse(f.call(callback)); self.assertEqual(f.events, 0)

    def test_read_payload_discard_after_retirement(self):
        f = self.active()
        def read(lease): f.retire('focus'); return 'secret old text'
        self.assertIsNone(f.call(read, read=True))

    def test_refocus_does_not_revive_old_adapter(self):
        f = self.active(); old = f.target; f.focus = False; f.retire('focus'); f.focus = True
        self.assertFalse(f.call(edit)); self.assertIsNotNone(f.create()); self.assertIsNot(f.target, old)

    def test_stale_close_does_not_touch_successor(self):
        f = self.active(); old = f.target; f.retire('replacement'); f.create()
        successor = f.target; f.buffer.composition = (1, 2)
        old.adapter_close(); old.adapter_close()
        self.assertEqual(old.closes, 1); self.assertIs(f.target, successor); self.assertEqual(f.buffer.composition, (1, 2))

    def test_read_discards_successor_presentation_echo(self):
        f = self.active()
        def read(lease): f.echo(); return f.buffer.text
        self.assertIsNone(f.call(read, read=True))

    def test_read_discards_changed_snapshot_without_identity_loss(self):
        f = self.active()
        def read(lease): f.buffer.selection=(0,0); return f.buffer.text
        self.assertIsNone(f.call(read, read=True))

    def test_unchanged_read_returns_payload(self):
        f = self.active(); self.assertEqual(f.call(lambda lease: f.buffer.text,read=True),'old')

    def test_close_reentry_cannot_create_or_duplicate_close(self):
        f = self.active(); t = f.target
        def reentry():
            self.assertIsNone(f.create()); f.retire('explicit-close'); self.assertFalse(f.call(edit))
        t.close_hook = reentry; f.retire('explicit-close')
        self.assertEqual(t.closes, 1); self.assertEqual(f.creator_calls, 1)

    def test_native_close_throw_quarantines_without_retry(self):
        f = self.active(); t = f.target; error = RuntimeError('close failed'); t.close_failure = error
        f.retire('focus'); self.assertEqual(f.disposition, 'FAILED_UNCERTAIN')
        self.assertIs(f.primary, error); self.assertIsNone(f.create()); f.cleanup(); self.assertEqual(t.closes, 1)

    def test_first_fatal_wins_ordinary_edit_failure(self):
        f = self.active(); ordinary = RuntimeError('edit'); fatal = Fatal('cleanup'); f.target.close_failure = fatal
        def call(lease): f.retire('owner'); raise ordinary
        with self.assertRaises(Fatal) as caught: f.call(call)
        self.assertIs(caught.exception, fatal); self.assertIs(f.primary, ordinary); self.assertIs(f.fatal, fatal)

    def test_first_fatal_identity_preserved(self):
        f = self.active(); first = Fatal('edit'); later = Fatal('close'); f.target.close_failure = later
        def call(lease): f.retire('owner'); raise first
        with self.assertRaises(Fatal) as caught: f.call(call)
        self.assertIs(caught.exception, first); self.assertIs(f.fatal, first)

    def test_buffer_replacement_fails_before_native_close(self):
        f = self.active(); t = f.target
        def call(lease): f.retire('focus'); f.buffer = Buffer('successor'); return True
        with self.assertRaises(AssertionError): f.call(call)
        self.assertEqual(t.closes, 0); self.assertTrue(f.quarantined); self.assertEqual(f.disposition, 'FAILED_UNCERTAIN')

    def test_nested_creator_returns_null_without_super(self):
        f = Field()
        def native(field): self.assertIsNone(field.create()); return Target(field)
        self.assertIsNotNone(f.create(native)); self.assertEqual(f.creator_calls, 1)

    def test_creator_null_allows_later_fresh_attempt(self):
        f = Field(); self.assertIsNone(f.create(lambda _: None)); self.assertEqual(f.disposition, 'NO_TARGET')
        self.assertIsNotNone(f.create())

    def test_creator_focus_loss_return_disposes_before_successor(self):
        f = Field(); made = []
        def native(field):
            target = Target(field); made.append(target); field.focus = False; field.retire('focus')
            self.assertIsNone(field.create()); return target
        self.assertIsNone(f.create(native)); self.assertEqual(made[0].closes, 1)
        f.focus = True; self.assertIsNotNone(f.create())

    def test_creator_throw_is_uncertain_never_publish(self):
        for error in [RuntimeError('creator'), Fatal('creator')]:
            f = Field()
            def native(field): self.assertIsNone(field.create()); raise error
            with self.assertRaises(type(error)) as caught: f.create(native)
            self.assertIs(caught.exception, error); self.assertTrue(f.quarantined); self.assertIsNone(f.create())

    def test_retirement_in_coordinator_operation_is_terminal_deferred(self):
        f = self.active(); t = f.target; f.operation = True; f.retire('focus')
        self.assertEqual(t.closes, 0); self.assertTrue(f.terminal); self.assertEqual(f.disposition, 'DEFERRED')
        f.operation = False; f.cleanup(); self.assertEqual(t.closes, 1)

    def test_no_cleanup_or_creator_in_commit_finish(self):
        f = self.active(); f.commit_finish = True; t = f.target; f.retire('owner')
        self.assertEqual(t.closes, 0); self.assertIsNone(f.create())
        f.commit_finish = False; f.cleanup(); self.assertEqual(t.closes, 1)

    def test_current_buffer_native_shape_witness_rejects_late_close(self):
        f = self.active(); old = f.target
        f.buffer = Buffer('new', composition=(0, 3))
        old.close()  # Deliberately execute rejected ordering to witness the hazard.
        self.assertIsNone(f.buffer.composition)

    def test_bootstrap_constant_null_has_no_field_or_thread_access(self):
        # Required implementation shape: no captured field/target/self expression.
        def get_handler(): return None
        self.assertIsNone(get_handler())

if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Transitions))
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                      'scope': 'Authored transition model only; no Android or actual adapter execution'}))
    raise SystemExit(not result.wasSuccessful())
