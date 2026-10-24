#!/usr/bin/env python3
"""V2 host-model controls. No Linux backend, listener, namespace or helper."""
import copy
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace
import checkpoint
import lifecycle as life


class Clock:
    def __init__(self):
        self.now = 1_000_000_000
    def __call__(self):
        return self.now


def proof():
    value = {key: 0 for key in life.PROOF_FIELDS}
    value.update(identityMatched=1, cgroupRemoved=1, mountTargetRemoved=1, controlClosed=1, rowScratchRemoved=1)
    return value


def phase_observation(phase):
    number = life.PHASES.index(phase) + 1
    owners = int(phase != "idle")
    captures = int(phase == "blocked_response")
    arm = dict.fromkeys(life.ARM_FIELDS, 0)
    arm.update(phase=number, owners=owners, readerSuspended=int(phase == "h2_reader_frozen"),
               responseBlocked=int(phase == "blocked_response"), queuedMessages=int(phase == "h2_reader_frozen"),
               queuedSocketBytes=int(phase == "blocked_response"), wireSentBytes=100, roleRelativeNs=10, preInitDumpable=1)
    stopped = dict.fromkeys(life.RESULT_FIELDS, 0)
    stopped.update(phase=number, gateClosed=1, gateClosedNs=20, killRequestedNs=21,
                   ownersExpected=owners, ownersDown=owners, peersExpected=owners, peersClosed=owners,
                   capturesBeforeStop=captures, capturesAfterStop=captures, observedStopNs=30,
                   ownersAliveAtTerm=owners, phaseArmedAtTerm=1, termObservedCount=1, termObservedNs=21)
    gate = {"phase": number, "gateClosed": 1, "gateClosedNs": 20, "ownersAliveAtGate": owners,
            "phaseArmedAtGate": 1, "capturesAtGate": captures}
    callback = {"phase": number, "completed": 1, "elapsedNs": 1_000}
    termination = {"stopStartedMonotonicNs": 1_000, "termSentMonotonicNs": 1_000, "termSentCount": 1,
                   "emptyObservedMonotonicNs": 1_100, "allResourcesObservedMonotonicNs": 1_101,
                   "killUsed": 0, "killSentMonotonicNs": 0}
    return {"arm": arm, "gate": gate, "callback": callback, "stopped": stopped, "termination": termination}


class ModelBackend:
    kind = "host-model-only-not-linux"
    def __init__(self, clock):
        self.clock = clock
        self.cleanup_calls = 0
        self.budgets = []
        self.resources = 0
        self.advance_ns = 1
    def phase(self, phase, budget):
        self.budgets.append(budget)
        self.resources += 1
        self.clock.now += self.advance_ns
        return phase_observation(phase)
    def lifecycle(self, selected, observe, budget):
        self.budgets.append(budget)
        self.resources += 1
        for stage in life.Stage:
            self.clock.now += self.advance_ns
            observe(stage)
    def cleanup(self, budget):
        self.cleanup_calls += 1
        self.resources = 0
        return proof()


class HostControls(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.budget = life.Budget(self.clock.now, self.clock.now, self.clock)
        self.model = ModelBackend(self.clock)
    def reject(self, callback):
        with self.assertRaises(life.Unavailable):
            callback()
    def test_immutable_checkpoint_archive_and_current_bindings(self):
        self.assertEqual(checkpoint.verify()["sealedFiles"], 98)
    def test_four_exact_observed_phases_and_single_budget(self):
        rows = life.run_r14(self.model, self.budget)
        self.assertEqual([r["phase"] for r in rows], [1, 2, 3, 4])
        self.assertEqual(self.model.cleanup_calls, 4)
        self.assertTrue(all(value is self.budget for value in self.model.budgets))
        self.assertEqual(self.model.resources, 0)
    def test_r14_deadline_not_reset_between_phases(self):
        self.model.advance_ns = 31_000_000_000
        self.reject(lambda: life.run_r14(self.model, self.budget))
        self.assertEqual(self.model.cleanup_calls, 4)
        self.assertEqual(self.model.resources, 0)
    def test_all34_injections_reach_exact_boundary_and_cleanup(self):
        rows = life.run_r18(self.model, self.budget)
        self.assertEqual(len(rows), 34)
        self.assertEqual([r["stage"] for r in rows], list(range(1, 35)))
        self.assertEqual(self.model.cleanup_calls, 34)
        self.assertTrue(all(value is self.budget for value in self.model.budgets))
        self.assertEqual(self.model.resources, 0)
    def test_r18_deadline_not_reset_between_subcases(self):
        self.model.advance_ns = 1_000_000_000
        self.reject(lambda: life.run_r18(self.model, self.budget))
        self.assertLess(self.model.cleanup_calls, 34)
        self.assertEqual(self.model.resources, 0)
    def test_missing_boundary_cannot_be_replaced_with_smoke_success(self):
        self.model.lifecycle = lambda selected, observe, budget: None
        self.reject(lambda: life.run_r18(self.model, self.budget))
        self.assertEqual(self.model.cleanup_calls, 1)
    def test_wrong_order_and_duplicate_boundary_rejected(self):
        def bad(selected, observe, budget):
            observe(life.Stage.SOURCE_VALIDATED)
            observe(life.Stage.SOURCE_VALIDATED)
        self.model.lifecycle = bad
        self.reject(lambda: life.run_r18(self.model, self.budget))
        self.assertEqual(self.model.cleanup_calls, 1)
    def test_unknown_stage_cannot_select_code_or_path(self):
        for value in ("/bin/sh", "none", 1, True, None):
            self.reject(lambda: life.InjectedFailure(value))
    def test_unknown_numeric_and_boolean_fields_rejected(self):
        p = proof()
        for bad in (True, -1, 0.0, "0", None, 2**63):
            q = dict(p, socketHolders=bad)
            self.reject(lambda: life.validate_cleanup(q))
        q = dict(p, raw="MIXER_BODY_SENTINEL")
        self.reject(lambda: life.validate_cleanup(q))
    def test_every_cleanup_obligation_is_required(self):
        p = proof()
        for field in life.PROOF_FIELDS:
            bad = dict(p)
            bad[field] = 1 - p[field]
            self.reject(lambda: life.validate_cleanup(bad))
    def test_intended_h2_setup_is_not_an_armed_reader(self):
        event = phase_observation("h2_reader_frozen")
        for field in ("readerSuspended", "queuedMessages"):
            bad = copy.deepcopy(event)
            bad["arm"][field] = 0
            self.reject(lambda: life.validate_phase("h2_reader_frozen", **bad, proof=proof()))
    def test_response_progress_alone_is_not_observed_backpressure(self):
        event = phase_observation("blocked_response")
        event["arm"]["queuedSocketBytes"] = 0
        self.reject(lambda: life.validate_phase("blocked_response", **event, proof=proof()))
    def test_wrong_phase_unclosed_peer_and_late_success_fail(self):
        for section, field, value in (("arm", "phase", 1), ("stopped", "ownersDown", 0),
                                      ("stopped", "peersClosed", 0), ("stopped", "capturesAfterStop", 2),
                                      ("stopped", "gateClosed", 0), ("stopped", "killRequestedNs", 19)):
            event = phase_observation("blocked_response")
            event[section][field] = value
            self.reject(lambda: life.validate_phase("blocked_response", **event, proof=proof()))
    def test_stop_deadline_and_grace_are_never_widened(self):
        event = phase_observation("idle")
        event["termination"].update(killUsed=1, killSentMonotonicNs=1_001)
        self.reject(lambda: life.validate_phase("idle", **event, proof=proof()))
        event["termination"].update(killSentMonotonicNs=2_000_001_000, emptyObservedMonotonicNs=2_500_001_001)
        self.reject(lambda: life.validate_phase("idle", **event, proof=proof()))
    def test_graceful_disposal_without_actual_term_cannot_pass_r14(self):
        event = phase_observation("idle")
        event["termination"].update(termSentMonotonicNs=0, termSentCount=0)
        self.reject(lambda: life.validate_phase("idle", **event, proof=proof()))
    def test_suite_deadline_takes_precedence_over_new_row(self):
        self.clock.now += 899_000_000_000
        budget = life.Budget(1_000_000_000, self.clock.now, self.clock)
        self.assertEqual(budget.check(), 1_000_000_000)
        self.clock.now += 1_000_000_000
        self.reject(budget.check)
    def test_cleanup_runs_even_after_phase_backend_exception(self):
        def fail(phase, budget):
            self.model.resources = 1
            raise life.Unavailable()
        self.model.phase = fail
        self.reject(lambda: life.run_r14(self.model, self.budget))
        self.assertEqual(self.model.cleanup_calls, 1)
        self.assertEqual(self.model.resources, 0)
    def test_original_owner_must_still_be_armed_at_actual_term(self):
        for field in ("ownersAliveAtTerm", "phaseArmedAtTerm", "termObservedCount"):
            event = phase_observation("h2_reader_frozen")
            event["stopped"][field] = 0
            self.reject(lambda: life.validate_phase("h2_reader_frozen", **event, proof=proof()))
    def test_socket_namespace_and_pipe_proof_has_actual_deadline(self):
        event = phase_observation("idle")
        event["termination"]["allResourcesObservedMonotonicNs"] = 2_500_001_001
        self.reject(lambda: life.validate_phase("idle", **event, proof=proof()))
    def test_no_created_resources_need_no_unrelated_process_scan(self):
        import linux_backend
        with mock.patch.object(Path, "iterdir", side_effect=AssertionError("no owned resources exist")):
            self.assertEqual(linux_backend.holder_counts(set(), set()), {
                "namespaceHolders": 0, "socketHolders": 0, "pipeHolders": 0, "listenerHolders": 0})
    def test_pidfd_signal_requires_current_owned_membership(self):
        import linux_backend
        cg = SimpleNamespace(path=Path("/sys/fs/cgroup/delegated/mixer-wh-owned"), pids=lambda: [123])
        with mock.patch.object(linux_backend.os, "pidfd_open", return_value=99, create=True), \
             mock.patch.object(linux_backend.os, "close") as closed, \
             mock.patch.object(linux_backend.signal, "pidfd_send_signal", create=True) as sent, \
             mock.patch.object(Path, "read_text", return_value="0::/unrelated\n"):
            self.reject(lambda: linux_backend.owned_signal(cg, 15))
            sent.assert_not_called()
            closed.assert_called_once_with(99)
    def test_pidfd_signal_uses_verified_stable_handle(self):
        import linux_backend
        cg = SimpleNamespace(path=Path("/sys/fs/cgroup/delegated/mixer-wh-owned"), pids=lambda: [123])
        with mock.patch.object(linux_backend.os, "pidfd_open", return_value=99, create=True), \
             mock.patch.object(linux_backend.os, "close") as closed, \
             mock.patch.object(linux_backend.signal, "pidfd_send_signal", create=True) as sent, \
             mock.patch.object(Path, "read_text", return_value="0::/delegated/mixer-wh-owned\n"):
            self.assertEqual(linux_backend.owned_signal(cg, 15), 1)
            sent.assert_called_once_with(99, 15, None, 0)
            closed.assert_called_once_with(99)
    def test_output_allowance_is_shared_across_subcases(self):
        import linux_backend
        totals = {"stdout": 0, "stderr": 0}
        first, second = linux_backend.Audit(totals), linux_backend.Audit(totals)
        raw = b'{"schema":1,"event":"sample","beamTotalBytes":1,"heapWords":2,"referencedBinaryBytes":3,"mailboxLength":4,"processes":5}\n'
        first.feed("stdout", raw)
        second.feed("stdout", raw)
        self.assertEqual(totals["stdout"], 2 * len(raw))
        totals["stdout"] = 1_048_576
        with self.assertRaises(linux_backend.base.Refusal) as error:
            second.feed("stdout", b"x")
        self.assertEqual(error.exception.reason, "output_overflow")
        self.assertFalse(second.buffers["stdout"])
    def test_cleanup_failure_still_calls_noninjectable_emergency_path(self):
        import linux_backend
        owner = SimpleNamespace(output_totals={"stdout": 0, "stderr": 0}, history=[])
        session = linux_backend.Session(owner, "idle")
        session.stop_started = self.clock.now
        session.disposal_steps = mock.Mock(side_effect=linux_backend.base.Refusal("output_schema"))
        session.emergency_dispose = mock.Mock()
        self.reject(lambda: session.cleanup(self.budget))
        session.emergency_dispose.assert_called_once_with()
        self.assertEqual(session.stop_started, self.clock.now)
        self.assertTrue(session.failed)
        self.assertEqual(session.error_reason, "output_schema")
        self.assertFalse(session.cleaned)
    def test_expired_row_budget_cannot_disable_independent_cleanup(self):
        import linux_backend
        owner = SimpleNamespace(output_totals={"stdout": 0, "stderr": 0}, history=[])
        session = linux_backend.Session(owner, "idle")
        session.stop_started = self.clock.now
        session.empty_at = self.clock.now
        session.disposal_steps = mock.Mock()
        budget = SimpleNamespace(check=mock.Mock(side_effect=AssertionError("must clean after expiry")))
        with mock.patch.object(linux_backend.time, "monotonic_ns", return_value=self.clock.now):
            self.assertEqual(session.cleanup(budget)["identityMatched"], 1)
        budget.check.assert_not_called()
        session.disposal_steps.assert_called_once_with(inject=False)
    def test_output_scope_rejects_traversal_and_unowned_paths_before_creation(self):
        import run as v2run
        for path in (v2run.HERE / "results/../escape", Path("/tmp/mixer-resource-unowned-output")):
            with self.assertRaises(v2run.base.Refusal) as error:
                v2run.output_directory(path)
            self.assertEqual(error.exception.reason, "ownership")
        target = v2run.HERE / "results/never-created-by-host-control"
        self.assertEqual(v2run.output_directory(target), target)
        self.assertFalse(target.exists())
    def test_fresh_compiler_output_requires_exact_sealed_linux_elf_identity(self):
        import linux_backend
        header = bytearray(20)
        header[:6] = b"\x7fELF\x02\x01"
        header[18:20] = (62).to_bytes(2, "little")
        linux_backend.compiled_identity(header, "a" * 64, "a" * 64, "x86_64")
        for raw, actual, expected, arch in ((b"\xcf\xfa\xed\xfe" + bytes(16), "a", "a", "x86_64"),
                                           (header, "a", "b", "x86_64"),
                                           (header, "a", None, "x86_64"),
                                           (header, "a", "a", "aarch64"),
                                           (header, "a", "a", "unknown")):
            self.reject(lambda: linux_backend.compiled_identity(raw, actual, expected, arch))
    def test_holder_inventory_stops_at_original_disposal_deadline(self):
        import linux_backend
        with mock.patch.object(linux_backend.time, "monotonic_ns", return_value=self.clock.now), \
             mock.patch.object(Path, "iterdir", side_effect=AssertionError("deadline already expired")):
            self.reject(lambda: linux_backend.holder_counts({7}, {8}, self.clock.now))
    def test_gate_and_signal_and_callback_are_observed_in_local_causal_order(self):
        for section, field, value in (("gate", "phaseArmedAtGate", 0), ("gate", "gateClosed", 0),
                                      ("gate", "gateClosedNs", 22), ("stopped", "termObservedNs", 19),
                                      ("stopped", "termObservedCount", 2), ("callback", "completed", 0),
                                      ("callback", "elapsedNs", 1_000_000_001),
                                      ("termination", "termSentCount", 2), ("termination", "stopStartedMonotonicNs", 999)):
            event = phase_observation("h1_body")
            event[section][field] = value
            self.reject(lambda: life.validate_phase("h1_body", **event, proof=proof()))
    def test_role_term_uses_exact_namespace_pid2_and_one_owned_pidfd_signal(self):
        import linux_backend
        cg = SimpleNamespace(path=Path("/sys/fs/cgroup/delegated/mixer-wh-owned"), pids=lambda: [123, 124])
        def read(path):
            if path.name == "cgroup":
                return "0::/delegated/mixer-wh-owned\n"
            return "NSpid:\t123 2\nUid:\t65534 65534 65534 65534\n" if path.parent.name == "123" else "NSpid:\t124 1\nUid:\t65534 65534 65534 65534\n"
        with mock.patch.object(linux_backend.os, "pidfd_open", return_value=99, create=True) as opened, \
             mock.patch.object(linux_backend.os, "close") as closed, \
             mock.patch.object(linux_backend.signal, "pidfd_send_signal", create=True) as sent, \
             mock.patch.object(Path, "read_text", autospec=True, side_effect=read), \
             mock.patch.object(Path, "stat", return_value=SimpleNamespace(st_ino=7)), \
             mock.patch.object(linux_backend.time, "monotonic_ns", return_value=8):
            self.assertEqual(linux_backend.role_term(cg, 7), (1, 8))
            opened.assert_called_once_with(123, 0)
            sent.assert_called_once_with(99, linux_backend.signal.SIGTERM, None, 0)
            closed.assert_called_once_with(99)
    def test_role_term_refuses_wrong_namespace_and_duplicate_pid2(self):
        import linux_backend
        cg = SimpleNamespace(path=Path("/sys/fs/cgroup/delegated/mixer-wh-owned"), pids=lambda: [123])
        with mock.patch.object(Path, "read_text", return_value="NSpid:\t123 2\nUid:\t65534 65534 65534 65534\n"), \
             mock.patch.object(Path, "stat", return_value=SimpleNamespace(st_ino=7)), \
             mock.patch.object(linux_backend.os, "pidfd_open", create=True) as opened:
            self.reject(lambda: linux_backend.role_term(cg, 8))
            cg.pids = lambda: [123, 123]
            self.reject(lambda: linux_backend.role_term(cg, 7))
            opened.assert_not_called()
        cg.pids = lambda: [123]
        status = "NSpid:\t123 2\nUid:\t65534 65534 65534 65534\n"
        with mock.patch.object(Path, "read_text", side_effect=[status, status.replace("65534", "0")]), \
             mock.patch.object(Path, "stat", return_value=SimpleNamespace(st_ino=7)), \
             mock.patch.object(linux_backend.os, "pidfd_open", return_value=99, create=True), \
             mock.patch.object(linux_backend.os, "close") as closed, \
             mock.patch.object(linux_backend.signal, "pidfd_send_signal", create=True) as sent:
            self.reject(lambda: linux_backend.role_term(cg, 7))
            sent.assert_not_called()
            closed.assert_called_once_with(99)
        with mock.patch.object(Path, "read_text", return_value="Uid:\t65534 65534 65534 65534\n"):
            self.reject(lambda: linux_backend.role_term(cg, 7))


if __name__ == "__main__":
    unittest.main(verbosity=2)
