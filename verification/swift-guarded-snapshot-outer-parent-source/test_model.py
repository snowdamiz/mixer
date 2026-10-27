#!/usr/bin/env python3
"""Pure synthetic owner/control model and source checks, never authority."""
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
from prepare import source_data, HERE, PROFILE

class BadTrace(ValueError): pass

@dataclass
class Model:
    # The boolean charge is a synthetic state bit, not a price or budget.
    charged: bool = False
    payload: bool = False
    carrier: bool = False
    borrowed: bool = False
    token: bool = False
    inspected: int = 0
    snapshots: list = field(default_factory=list)
    events: list = field(default_factory=list)
    def apply(self, event):
        if event == 'snapshot':
            if len(self.snapshots) >= 3: raise BadTrace('unbounded snapshots')
            self.snapshots.append(self.charged)
        elif event == 'dispatch':
            if self.charged or self.payload or self.carrier: raise BadTrace('repeat dispatch')
            self.charged = self.payload = self.carrier = True
        elif event == 'borrow':
            if not (self.charged and self.payload and self.carrier) or self.inspected:
                raise BadTrace('invalid inspect')
            self.borrowed = True
            self.inspected += 1
        elif event == 'end_borrow':
            if not self.borrowed: raise BadTrace('missing borrow')
            self.borrowed = False
        elif event == 'destroy_payload':
            if self.borrowed or not (self.payload and self.charged): raise BadTrace('early owner end')
            self.payload = False
        elif event == 'destroy_carrier':
            if self.payload or self.borrowed or not self.carrier: raise BadTrace('live payload/carrier')
            self.carrier = False
        elif event == 'return_token':
            if self.payload or self.carrier or self.borrowed or self.token or not self.charged:
                raise BadTrace('premature token')
            self.token = True
        elif event == 'release':
            if not self.token or self.payload or self.carrier or self.borrowed:
                raise BadTrace('release without retired owners')
            self.token = self.charged = False
        elif event == 'unwind':
            # Frozen ordinary destruction cannot refund a charge.
            self.borrowed = self.payload = self.carrier = False
        else: raise BadTrace('unknown event')
        self.events.append(event)

def execute(events):
    model = Model()
    for event in events: model.apply(event)
    return model

RETURNED = ['snapshot', 'dispatch', 'snapshot', 'borrow', 'end_borrow',
            'destroy_payload', 'destroy_carrier']

class OwnershipAndControlTests(unittest.TestCase):
    def test_all_original_payload_kinds_retain_until_destruction(self):
        for payload in ['setup-ready-in-refusal', 'setup-io-refusal',
                        'setup-invariant-refusal', 'loader-refusal',
                        'prescope-refusal', 'leaf-returned', 'missing-payload']:
            for returned_token in [False, True]:
                with self.subTest(payload=payload, token=returned_token):
                    events = RETURNED + (['return_token', 'release'] if returned_token else []) + ['snapshot']
                    m = execute(events)
                    self.assertEqual(m.snapshots, [False, True, not returned_token])
                    self.assertEqual(m.inspected, 1)
                    self.assertFalse(m.payload or m.carrier or m.borrowed)
    def test_entry_refusal_has_no_dispatch_or_inspection(self):
        m = execute(['snapshot', 'snapshot'])
        self.assertEqual(m.snapshots, [False, False])
        self.assertEqual(m.inspected, 0)
    def test_pending_selectors_admit_nothing(self):
        for _ in ['binding-pending', 'account-refused']:
            m = execute([])
            self.assertFalse(m.charged or m.payload or m.carrier)
            self.assertEqual(m.snapshots, [])
    def test_early_release_rejected_at_every_live_owner_boundary(self):
        for prefix in [[], ['snapshot'], RETURNED[:2], RETURNED[:3],
                       RETURNED[:4], RETURNED[:5], RETURNED[:6], RETURNED]:
            with self.subTest(prefix=prefix):
                with self.assertRaises(BadTrace): execute(prefix+['release'])
    def test_token_cannot_return_before_payload_and_carrier_end(self):
        for prefix in [[], RETURNED[:2], RETURNED[:4], RETURNED[:5], RETURNED[:6]]:
            with self.subTest(prefix=prefix):
                with self.assertRaises(BadTrace): execute(prefix+['return_token'])
    def test_borrow_blocks_owner_and_carrier_destruction(self):
        for event in ['destroy_payload', 'destroy_carrier', 'return_token', 'release']:
            with self.subTest(event=event):
                with self.assertRaises(BadTrace): execute(RETURNED[:4]+[event])
    def test_second_inspect_dispatch_token_or_release_is_rejected(self):
        for events in [RETURNED[:5]+['borrow'], RETURNED[:2]+['dispatch'],
                       RETURNED+['return_token', 'return_token'],
                       RETURNED+['return_token', 'release', 'release']]:
            with self.subTest(events=events):
                with self.assertRaises(BadTrace): execute(events)
    def test_more_than_three_usage_calls_is_rejected(self):
        with self.assertRaises(BadTrace): execute(['snapshot']*4)
    def test_unwind_never_obtains_release_authority(self):
        for prefix in [RETURNED[:2], RETURNED[:4], RETURNED[:6]]:
            with self.subTest(prefix=prefix):
                m = execute(prefix+['unwind'])
                self.assertTrue(m.charged)
                self.assertFalse(m.token)
                with self.assertRaises(BadTrace): m.apply('release')
    def test_source_is_inline_addition_without_rewriting_old_bodies(self):
        source, manifest, _, old = source_data()
        candidate = source[PROFILE]
        self.assertEqual(len(manifest['members']), 146)
        self.assertTrue(candidate.startswith(old[:-2]))
        self.assertTrue(candidate.endswith(b'}\n'))
        self.assertEqual(candidate.count(b'fn consume_outer_request_v1('), 1)
    def test_source_has_no_public_mint_or_diagnostic_callback(self):
        source = (HERE/'outer-parent.inc.rs').read_text()
        for forbidden in ['pub fn', 'pub(crate)', '#[no_mangle]', 'extern "C"',
                          'Box::', '::leak(', '.clone(', '.to_string(', '.source(',
                          'std::env', 'unsafe {', 'catch_unwind']:
            with self.subTest(forbidden=forbidden): self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('match owned.inspect_v1()'), 1)
        self.assertEqual(source.count('match run_one_fixture_v1(&account, fixture)'), 1)
        self.assertEqual(source.count('match destroy_returned_fixture_v1(owned)'), 1)
        self.assertEqual(source.count('release_after_retirement_v1(destroyed);'), 1)
    def test_selected_input_constraint_matches_frozen_root_receipt(self):
        receipt = json.loads((HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-host-fixture-source-selection.json').read_bytes())
        self.assertEqual(receipt['source']['bytes'], 1947)
        source_bytes = bytes.fromhex(receipt['source']['sha256'])
        source = (HERE/'outer-parent.inc.rs').read_text()
        literal = source.split('const SELECTED_SOURCE_SHA256_V1:', 1)[1].split('];', 1)[0].split('= [', 1)[1]
        actual = bytes(int(value.strip(), 16) for value in literal.split(',') if value.strip())
        self.assertEqual(actual, source_bytes)
        self.assertEqual(list(receipt['original_validation_limits'].values()),
                         [1947, 1_000_000, 65_536, 1_000_000, 10_000])

if __name__ == '__main__': unittest.main(verbosity=2)
