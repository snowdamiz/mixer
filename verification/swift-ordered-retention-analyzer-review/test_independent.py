"""Finite review oracles, not an implementation of the proposed analyzer.

The exhaustive policy oracle uses ordered eligible prefixes rather than the
producer's repeated minimum scan. The transition oracle tests source order and
does not claim wire parsing, custody, full inventory or original-result coverage.
"""
import copy
import importlib.util
import itertools
import hashlib
import json
import os
from pathlib import Path
import struct
import unittest

BASE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get('REVIEW_DESIGN_SNAPSHOT', str(BASE / 'inputs'))) / 'verification/swift-ordered-retention-analyzer-design'


def load(name, path):
    import sys
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


m = load('review_frozen_model', SOURCE / 'model.py')
s = load('review_frozen_schema', SOURCE / 'interface_schema.py')
MAX = (1 << 64) - 1
POLICY_CASES = 0


def ordered_prefix_plan(slots, base, capacity, requested):
    """One sorted order and prefix sums, independent of repeated source scan."""
    occupied = [(i, row) for i, row in enumerate(slots) if row is not None]
    total = sum(row.bytes for _, row in occupied)
    holes = [i for i, row in enumerate(slots) if row is None]
    eligible = sorted(((row.timestamp, i, row.bytes) for i, row in occupied
                       if not row.pins))
    removed = 0
    for n in range(len(eligible) + 1):
        if (holes or n) and base + total - removed + requested <= capacity:
            selected = tuple(i for _, i, _ in eligible[:n])
            destination = selected[-1] if n else holes[0]
            return selected, tuple(sorted(selected)), destination
        if n < len(eligible):
            removed += eligible[n][2]
    raise ValueError('obstruction')


class Transitions:
    """Source-seam control model; every failed transition preserves state."""
    EDGES = {
        'idle': {'AcquireBegin': 'acquiring', 'Release': 'idle', 'Phase': 'idle',
                 'TerminalFailure': 'terminal'},
        'acquiring': {'LookupHit': 'hit', 'LookupMiss': 'miss', 'Failure': 'failed'},
        'hit': {'PinPublished': 'idle', 'Failure': 'failed'},
        'miss': {'PlanBegin': 'scanning', 'Failure': 'failed'},
        'scanning': {'PlanEnd': 'scanned', 'Failure': 'failed'},
        'scanned': {'MissReady': 'planned', 'Failure': 'failed'},
        'planned': {'EvictBegin': 'evicting', 'BuildBegin': 'building',
                    'Failure': 'failed'},
        'evicting': {'EvictTaken': 'taken', 'Failure': 'failed'},
        'taken': {'EvictCommit': 'planned', 'Failure': 'failed'},
        'building': {'BuildReady': 'ready', 'Failure': 'failed'},
        'ready': {'PinPublished': 'idle', 'Failure': 'failed'},
        'failed': {'Release': 'failed', 'Phase': 'failed',
                   'TerminalFailure': 'terminal'},
        'terminal': {'Release': 'terminal', 'Phase': 'terminal'},
    }

    def __init__(self):
        self.state = 'idle'
        self.taken = self.committed = 0
        self.resident = True

    def apply(self, event):
        if event not in self.EDGES[self.state]:
            raise ValueError((self.state, event))
        next_state = self.EDGES[self.state][event]
        if event == 'EvictTaken':
            self.resident = False
            self.taken += 1
        if event == 'EvictCommit':
            self.committed += 1
        self.state = next_state


class AtomicRecord:
    def __init__(self, remaining):
        self.remaining = remaining
        self.accepted = 0
        self.state = (0, 0)

    def attempt(self, actual_cost, valid=True, commit_valid=True):
        if self.remaining < 8192:
            return 'Steps'
        if not 0 <= actual_cost <= 8192:
            raise ValueError('implementation-cost-contract')
        self.remaining -= actual_cost
        candidate = (self.state[0] + 1, self.state[1] + 3)
        if not valid:
            return 'Replay'
        if not commit_valid:
            # A commit bug invalidates metrics; no valid-state serialization.
            self.state = None
            return 'Internal'
        self.state = candidate
        self.accepted += 1
        return 'Accepted'


def checked_access(base, capacity, stride, index, field, width, region_end):
    if not 0 <= index < capacity or not 0 <= field <= stride - width:
        raise ValueError('index-or-field')
    start = base + index * stride + field
    end = start + width
    if not 0 <= start <= MAX or not 0 <= end <= MAX or end > region_end:
        raise ValueError('overflow-or-region')
    return start, end


def join_verdict(decision, rust_flag, records_complete, original, custody,
                 selection_verified=True):
    # Rust has no authority to assert acceptance; such a claim is inconsistency.
    if rust_flag != 0:
        return 'Invalid', False
    if not selection_verified:
        return 'Unavailable', False
    if not original or not custody:
        return 'Invalid', False
    if not records_complete:
        return 'AnalysisLimited', False
    return decision, decision in ('CompleteRecords', 'TruncatedPrefix')


class IndependentReview(unittest.TestCase):
    def test_scalar_boundaries_names_and_reserved_tail(self):
        self.assertEqual([len(s.CONTROL), len(s.ACTIVE), len(s.PLANNER),
                          len(s.LIFECYCLE), len(s.COUNTERS)], [64, 64, 32, 24, 128])
        self.assertEqual([s.SCALARS[i] for i in (0, 64, 128, 160, 184, 312)],
                         ['control.step_limit', 'active.state', 'planner.selected_mask',
                          'lifecycle.terminal_seen', 'counter.acquire_attempts',
                          'reserved.reserved_0'])
        self.assertEqual(len(s.SCALARS), len(set(s.SCALARS)))
        self.assertEqual(s.SCALARS[-1], 'reserved.reserved_199')

    def test_report_offsets_and_closed_ids(self):
        self.assertEqual(s.offsets(s.REPORT_REGIONS), [
            ('header', 0, 512), ('counters', 512, 1024), ('histograms', 1536, 4096),
            ('windows', 5632, 16384), ('top', 22016, 4096),
            ('residents', 26112, 4096), ('pins', 30208, 3072),
            ('reserved', 33280, 15872)])
        self.assertEqual(sum(n for _, n in s.HOST_REGIONS), 8192)
        self.assertEqual(s.offsets(s.HOST_REGIONS), [
            ('header', 0, 512), ('custody', 512, 3840), ('digests', 4352, 512),
            ('bindings_and_result', 4864, 2048), ('observations', 6912, 1024),
            ('reserved', 7936, 256)])
        self.assertEqual(s.DECISIONS, dict(CompleteRecords=1, TruncatedPrefix=2,
                                         Invalid=3, AnalysisLimited=4, Unavailable=5))
        self.assertEqual(sorted(s.STOP_REASONS.values()), list(range(12)))
        self.assertEqual(s.REPORT_HEADER[4], 'full_replay_accepted')
        self.assertEqual(49152 + 8192, 57344)

    def test_arena_rows_and_candidate_payload(self):
        self.assertEqual(struct.calcsize('<QQIIIIIIIIQQQQQQ'), 96)
        regions = [80000*96, 64*64, 64*48, 512*40, 64*8, 128*128,
                   6*66*8, 32*64, 512*8, 8192, 65536, 65536]
        self.assertEqual(sum(regions), 7873120)
        self.assertEqual(8388608 - sum(regions), 515488)
        payload = 96 + 64 + 48 + 40 + 128 + 512 + 32*8 + 6*8
        self.assertEqual(payload, 1192)
        self.assertLess(payload, 2048)
        self.assertEqual(sum([3072, 2048, 4096, 4096, 12288, 8192, 8192]), 41984)

    def test_checked_access_last_cell_and_adversity(self):
        self.assertEqual(checked_access(0, 80000, 96, 79999, 88, 8, 7680000),
                         (7679992, 7680000))
        for args in [(0, 80000, 96, 80000, 0, 8, 7680000),
                     (0, 80000, 96, -1, 0, 8, 7680000),
                     (0, 80000, 96, 1, 92, 8, 7680000),
                     (MAX-7, 2, 8, 1, 0, 8, MAX),
                     (0, 2, 8, 1, 0, 8, 15)]:
            with self.assertRaises(ValueError):
                checked_access(*args)

    def test_exhaustive_policy_against_ordered_prefix_oracle(self):
        global POLICY_CASES
        choices = [None, m.Resident(0, 1, 0, 0), m.Resident(0, 2, 0, 0),
                   m.Resident(0, 1, 0, 1), m.Resident(0, 1, 1, 0),
                   m.Resident(0, 2, 1, 1)]
        for count in range(1, 5):
            for state in itertools.product(choices, repeat=count):
                rows = [None if r is None else m.Resident(i, r.bytes, r.pins, r.timestamp)
                        for i, r in enumerate(state)]
                original = copy.deepcopy(rows)
                for base, headroom, request in itertools.product(range(2), range(3), range(1, 5)):
                    capacity = base + sum(r.bytes for r in rows if r) + headroom
                    if base + request > capacity:
                        continue
                    POLICY_CASES += 1
                    try:
                        expected = ordered_prefix_plan(rows, base, capacity, request)
                    except ValueError:
                        with self.assertRaises(ValueError):
                            m.plan(rows, base, capacity, request)
                    else:
                        self.assertEqual(m.plan(rows, base, capacity, request), expected)
                    self.assertEqual(rows, original)
        self.assertGreater(POLICY_CASES, 30000)
        print(f'INDEPENDENT_POLICY_CASES={POLICY_CASES}')

    def test_full_64_slot_reverse_order_and_obstruction(self):
        rows = [m.Resident(i, 1, 0, 63-i) for i in range(64)]
        selected, emitted, destination = m.plan(rows, 0, 64, 64)
        self.assertEqual(selected, tuple(reversed(range(64))))
        self.assertEqual(emitted, tuple(range(64)))
        self.assertEqual(destination, 0)
        with self.assertRaises(ValueError):
            m.plan([m.Resident(i, 1, 1, 0) for i in range(64)], 0, 64, 1)

    def test_selection_emission_destination_are_distinct(self):
        rows = [m.Resident(0, 2, 0, 2), m.Resident(1, 2, 0, 0),
                m.Resident(2, 2, 0, 1), None]
        self.assertEqual(m.plan(rows, 0, 6, 5), ((1, 2, 0), (0, 1, 2), 0))

    def test_source_fsm_success_paths(self):
        for path in [('AcquireBegin', 'LookupHit', 'PinPublished', 'Release'),
                     ('AcquireBegin', 'LookupMiss', 'PlanBegin', 'PlanEnd', 'MissReady',
                      'EvictBegin', 'EvictTaken', 'EvictCommit', 'BuildBegin',
                      'BuildReady', 'PinPublished')]:
            state = Transitions()
            for event in path:
                state.apply(event)
            self.assertEqual(state.state, 'idle')

    def test_release_cannot_interleave_synchronous_acquisition(self):
        for state in ('acquiring', 'hit', 'miss', 'scanning', 'scanned', 'planned',
                      'evicting', 'taken', 'building', 'ready'):
            instance = Transitions(); instance.state = state
            prior = copy.deepcopy(instance.__dict__)
            with self.assertRaises(ValueError):
                instance.apply('Release')
            self.assertEqual(instance.__dict__, prior)

    def test_failed_and_terminal_operations_cannot_resume(self):
        for state in ('failed', 'terminal'):
            for event in ('AcquireBegin', 'LookupHit', 'PlanEnd', 'EvictCommit',
                          'BuildReady', 'PinPublished', 'Failure'):
                instance = Transitions(); instance.state = state
                with self.assertRaises(ValueError):
                    instance.apply(event)

    def test_eviction_failure_keeps_irrevocable_take(self):
        for taken in (False, True):
            instance = Transitions(); instance.state = 'planned'
            instance.apply('EvictBegin')
            if taken:
                instance.apply('EvictTaken')
            instance.apply('Failure')
            self.assertEqual(instance.resident, not taken)
            self.assertEqual((instance.taken, instance.committed), (int(taken), 0))

    def test_reserve_refuses_before_semantic_mutation(self):
        instance = AtomicRecord(8191)
        before = copy.deepcopy(instance.__dict__)
        self.assertEqual(instance.attempt(1), 'Steps')
        self.assertEqual(instance.__dict__, before)
        instance = AtomicRecord(8192)
        self.assertEqual(instance.attempt(8192), 'Accepted')
        self.assertEqual((instance.remaining, instance.accepted, instance.state), (0, 1, (1, 3)))

    def test_failed_preflight_spends_steps_without_state_commit(self):
        instance = AtomicRecord(16384)
        self.assertEqual(instance.attempt(4096, valid=False), 'Replay')
        self.assertEqual((instance.remaining, instance.accepted, instance.state), (12288, 0, (0, 0)))

    def test_unexpected_commit_bug_invalidates_metrics(self):
        instance = AtomicRecord(8192)
        self.assertEqual(instance.attempt(50, commit_valid=False), 'Internal')
        self.assertIsNone(instance.state)
        self.assertEqual(instance.accepted, 0)

    def test_historical_estimate_and_io_reserve_arithmetic(self):
        a, miss, evict = 599204, 61628, 61564
        records = 4*a + 5*miss + 3*evict + 8
        self.assertEqual(records, 2889656)
        cost = (22*records + 256*a + 64*(miss+evict) + 1048576 +
                640000 + 3000000 + 263584 + 65536)
        self.assertEqual(cost, 229870640)
        self.assertEqual(268435456-cost, 38564816)
        self.assertEqual(((536871936+65535)//65536 + 1)*32, 262208)
        self.assertEqual(((2560512+65535)//65536 + 1)*32, 1312)
        self.assertEqual(262208 + 1312 + 64, 263584)

    def test_full_record_cap_has_no_budget_guarantee(self):
        # Even record fixed groups alone do not bound resident/planner costs.
        worst = 4194304 * (22 + 64 + 64*64)
        self.assertGreater(worst, 268435456)
        self.assertGreater(129*8192, 128*8192)

    def test_frame_arithmetic_overflow_flags_and_buffer_loss(self):
        self.assertEqual(1024 + 128*4194304, 536871936)
        self.assertEqual(m.classify(128, 9, 100, 9, 0, 1024), 'invalid')
        for bad_flags in range(2, 512):
            self.assertEqual(m.classify(bad_flags, 2, 2, 3, 1, 1280), 'invalid')
        self.assertEqual(m.classify(1, 2, 2, 3, 1, 1280), 'truncated-prefix')
        self.assertEqual(m.classify(0, 1, 1, 1, 0, 1152), 'complete-records')

    def test_host_authority_never_comes_from_rust_flag(self):
        for decision in ('CompleteRecords', 'TruncatedPrefix', 'Invalid',
                         'AnalysisLimited', 'Unavailable'):
            self.assertEqual(join_verdict(decision, 1, True, True, True), ('Invalid', False))
        self.assertEqual(join_verdict('CompleteRecords', 0, False, True, True),
                         ('AnalysisLimited', False))
        for original, custody in ((False, True), (True, False), (False, False)):
            self.assertEqual(join_verdict('CompleteRecords', 0, True, original, custody),
                             ('Invalid', False))
        self.assertEqual(join_verdict('CompleteRecords', 0, True, True, True,
                                      selection_verified=False), ('Unavailable', False))

    def test_guest_tokens_are_not_consuming_ledger_zeros(self):
        replay = m.Replay([m.Resident(7, 9, 0, 2)])
        replay.publish(0, 1, 0, 1, 12)
        final_consuming = (0,)*15
        self.assertEqual(sum(final_consuming), 0)
        self.assertEqual(replay.slots[0].pins, 1)
        self.assertEqual(len(replay.pins), 1)

    def test_interval_credit_never_adds_overlapping_total(self):
        scan = m.interval(10, end=30)
        operation = m.interval(5, failure=35)
        self.assertEqual(scan['completed'], 20)
        self.assertEqual(operation['partial'], 30)
        # Both are true endpoint observations; 50 is not disjoint used work.
        self.assertGreater(scan['completed'] + operation['partial'], 35-5)

    def test_all_seventeen_historical_sidecars_remain_invalid(self):
        rows = json.loads((BASE / 'historical-sidecars.json').read_bytes())
        self.assertEqual(len(rows), 17)
        for row in rows:
            local = BASE.parents[1] / row['snapshot']
            raw = local.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            sidecar = json.loads(raw)
            self.assertEqual((sidecar['status'], sidecar['failure']), ('invalid', 15))

    def test_amended_host_hash_and_descriptor_envelope(self):
        # Deliberately conservative: hash every bounded small input twice even
        # if a future implementation closes a one-pass prerequisite earlier.
        extents = [536871936, 2560512, 8192, 8192, 8192, 8192, 8388608]
        byte_units = 2*sum((n+63)//64 for n in extents) + 2*(2560000//64)
        attempt_units = 2*sum((((n+65535)//65536)+1)*32 for n in extents)
        self.assertEqual(byte_units, 17200432)
        self.assertEqual(attempt_units, 535808)
        self.assertEqual(18000000 - byte_units - attempt_units, 263760)
        self.assertEqual(5 + 3 + 1 + 1 + 3, 13)
        self.assertEqual(7733856 + 8192, 7742048)  # Reuse existing arena context region.
        self.assertEqual(5*8 + 2*8 + 4, 60)
        self.assertEqual(512 + 60*64 + 512 + 2048 + 1024 + 256, 8192)
        self.assertEqual(s.wrapper_budget(), (byte_units, attempt_units, 896, 65536))
        self.assertEqual(sum(s.wrapper_budget()), 17802672)
        self.assertEqual(s.RUST_IO_ATTEMPTS, 263584)

    def test_amended_operation_gate_against_independent_closed_edges(self):
        names = dict(idle='Idle', acquiring='Acquire', hit='Hit', miss='Miss',
                     scanning='Scan', scanned='Plan', planned='Ready',
                     evicting='EvictBegin', taken='EvictTaken', building='Build',
                     ready='Built')
        events = ['AcquireBegin', 'LookupHit', 'LookupMiss', 'PlanBegin', 'PlanEnd',
                  'MissReady', 'EvictBegin', 'EvictTaken', 'EvictCommit',
                  'BuildBegin', 'BuildReady', 'PinPublished', 'Release',
                  'Failure', 'TerminalFailure']
        self.assertEqual(s.ACTIVE_STATES, dict(zip(names.values(), range(11))))
        checked = 0
        for reference, frozen in names.items():
            allowed = Transitions.EDGES[reference]
            for event in events:
                gate = m.OperationGate(); gate.state = frozen
                actual_event = 'PinFailure' if event == 'Failure' else event
                checked += 1
                if event not in allowed:
                    with self.assertRaises(AssertionError):
                        gate.event(actual_event)
                    self.assertEqual(gate.state, frozen)
                else:
                    gate.event(actual_event)
                    after = allowed[event]
                    self.assertEqual(gate.state, names.get(after, 'Idle'))
        self.assertEqual(checked, 165)
        print(f'INDEPENDENT_CLOSED_TRANSITIONS={checked}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
