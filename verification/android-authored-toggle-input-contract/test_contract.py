#!/usr/bin/env python3
"""Finite host checks of the proposed contract, explicitly not native acceptance."""
import json
import pathlib
import unittest
from contract_model import Geometry, Toggle

BASE = pathlib.Path(__file__).resolve().parent

class PolicyTests(unittest.TestCase):
    def endpoint(self, initial=False, rtl=False, density=3):
        g = Geometry(density=density, width=338*density, height=44*density, rtl=rtl)
        t = Toggle(initial, g, slop=8*density)
        start, end, y = g.endpoint(initial), g.endpoint(not initial), g.height/2
        self.assertTrue(t.down(start, y))
        for i in range(1, 9):
            self.assertTrue(t.sample(start + (end-start)*i/8, y))
            self.assertEqual(t.proposals, 0)
            self.assertEqual(t.native, initial)
        self.assertTrue(t.up(end, y))
        self.assertEqual((t.native, t.bound, t.proposals, t.commits), (not initial, not initial, 1, 1))
        self.assertEqual((t.parent_acquires, t.parent_releases), (1, 1))
        self.assertEqual(t.move_jni_calls, 0)

    def test_endpoint_matrix(self):
        for density in (1, 1.25, 2, 3, 4):
            for initial in (False, True):
                for rtl in (False, True):
                    with self.subTest(density=density, initial=initial, rtl=rtl):
                        self.endpoint(initial, rtl, density)

    def test_original_p03_coordinates_and_schedule(self):
        path = BASE / 'inputs/verification/android-pointer-timing-correction/runtime/runtime-1/pointer-sequence-3.json'
        sequence = json.loads(path.read_text())
        self.assertEqual([e['offsetMilliseconds'] for e in sequence['events']], [0,80,160,240,320,400,480,560,640,790])
        self.assertEqual([e['action'] for e in sequence['events']], [0]+[2]*8+[1])
        self.assertEqual((sequence['geometry']['offX'], sequence['geometry']['onX'], sequence['geometry']['thumbY']), (982.5,1048.5,1632))
        t = Toggle()
        for i, event in enumerate(sequence['events']):
            x, y = event['x']-96, event['y']-1566
            if event['action'] == 0: self.assertTrue(t.down(x,y))
            elif event['action'] == 2:
                self.assertTrue(t.sample(x,y))
                self.assertEqual(t.proposals, 0)
                if i == 3: self.assertEqual(t.preview, .375) # Full crossing movement retained.
            else: self.assertTrue(t.up(x,y))
        self.assertEqual((t.proposals, t.commits, t.native), (1,1,True))

    def test_label_tap_and_hold_release_same_policy(self):
        for hold in (80, 500, 1500):
            for initial in (False, True):
                with self.subTest(hold=hold, initial=initial):
                    t = Toggle(initial)
                    self.assertTrue(t.down(200,66))
                    self.assertEqual(t.proposals, 0) # Host arithmetic has no timer or event delivery claim.
                    self.assertTrue(t.pressed)
                    self.assertTrue(t.up(200,66))
                    self.assertEqual((t.native,t.proposals,t.commits),(not initial,1,1))

    def test_slop_strict_and_vertical_tie_yields(self):
        t=Toggle(); x=t.geometry.endpoint(False); t.down(x,66)
        t.sample(x+24,66); self.assertEqual(t.mode,'pending')
        t.sample(x+24.0001,66); self.assertEqual(t.mode,'drag')
        self.assertGreater(t.preview,24/66)
        t=Toggle(); t.down(x,66); t.sample(x+25,91)
        self.assertEqual((t.mode,t.proposals,t.parent_acquires),('drain',0,0))

    def test_midpoint_ties_keep_initial_both_directions(self):
        for rtl in (False,True):
            for initial in (False,True):
                t=Toggle(initial,Geometry(rtl=rtl)); g=t.geometry; a=g.endpoint(initial); b=g.endpoint(not initial)
                t.down(a,66); self.assertTrue(t.up((a+b)/2,66))
                self.assertEqual((t.native,t.proposals),(initial,0))

    def test_return_to_original_side_does_not_toggle(self):
        t=Toggle(); g=t.geometry; x=g.endpoint(False)
        t.down(x,66); t.sample(g.endpoint(True),66); t.up(x,66)
        self.assertEqual((t.native,t.proposals,t.parent_releases),(False,0,1))

    def test_horizontal_outside_release_clamps(self):
        for rtl in (False,True):
            for initial in (False,True):
                t=Toggle(initial,Geometry(rtl=rtl)); g=t.geometry
                a,b=g.endpoint(initial),g.endpoint(not initial); t.down(a,66)
                end=g.width+1000 if b>a else -1000
                self.assertTrue(t.up(end,66))
                self.assertEqual((t.native,t.proposals,t.parent_releases),(not initial,1,1))

    def test_vertical_corridor_boundaries_and_reentry(self):
        for y,accepted in ((-66,True),(198,True),(-66.001,False),(198.001,False)):
            t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66)
            t.up(g.endpoint(True),y)
            self.assertEqual(t.commits,1 if accepted else 0)
            self.assertEqual(t.parent_acquires,t.parent_releases)
        t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66)
        t.sample(g.endpoint(True),300); t.up(g.endpoint(True),66)
        self.assertEqual(t.commits,1)

    def test_label_vertical_scroll_and_horizontal_drift(self):
        for x,y in ((200,30),(240,66)):
            t=Toggle(); t.down(200,66); self.assertFalse(t.sample(x,y)); t.up(x,y)
            self.assertEqual((t.native,t.proposals,t.parent_acquires),(False,0,0))

    def test_cancel_disable_stale_retirement_lifecycle_and_pointer_loss(self):
        reasons=('ACTION_CANCEL','ACTION_OUTSIDE','disabled','stale-environment','retired','detach','window-focus-loss','focus-loss','hidden','frame-change','parent-rebind')
        for reason in reasons:
            t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66)
            if reason in ('disabled','stale-environment','retired'):t.invalidate(reason)
            else:t.cancel(reason)
            t.up(g.endpoint(True),66)
            self.assertEqual((t.native,t.proposals,t.pressed,t.preview,t.parent_releases),(False,0,False,None,1))
        for pointer,count in ((9,1),(0,2),(None,1)):
            t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66,pointer,count); t.up(g.endpoint(True),66)
            self.assertEqual(t.proposals,0)

    def test_binding_replacement_never_commits_old_touch(self):
        for value in (False,True):
            t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66); t.bind(value)
            t.up(g.endpoint(True),66)
            self.assertEqual((t.native,t.proposals),(value,0))

    def test_nonpointer_activation_cancels_touch_and_late_up(self):
        for name in ('keyboard','accessibility','ordinary-performClick'):
            t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66)
            self.assertTrue(t.click()); self.assertFalse(t.up(g.endpoint(True),66))
            self.assertEqual((t.native,t.proposals,t.commits,t.parent_releases),(True,1,1,1))

    def test_rejected_click_restores_latest_authority_and_no_second_proposal(self):
        t=Toggle(); self.assertTrue(t.click(reject=True))
        self.assertEqual((t.native,t.bound,t.proposals,t.commits,t.raw_checked_callbacks),(False,False,1,0,2))
        self.assertFalse(t.click()); self.assertEqual(t.proposals,1)
        t=Toggle(True); self.assertTrue(t.click(rebind_to=True))
        self.assertEqual((t.native,t.bound,t.proposals),(True,True,1))

    def test_closed_and_invalid_begin_fail_without_mutation(self):
        for x,y,count in ((-1,66,1),(1014,66,1),(200,-1,1),(200,132,1),(float('nan'),66,1),(200,66,2)):
            t=Toggle(); self.assertFalse(t.down(x,y,count=count)); self.assertEqual(t.proposals,0)
        t=Toggle(); t.open=False; self.assertFalse(t.down(200,66)); self.assertFalse(t.click())

    def test_cancel_release_is_idempotent_and_fresh_touch_survives(self):
        t=Toggle(); g=t.geometry; t.down(g.endpoint(False),66); t.sample(g.endpoint(True),66)
        t.cancel(); t.cancel(); t.clear(); self.assertEqual(t.parent_releases,1)
        t.down(200,66); t.up(200,66); self.assertEqual(t.proposals,1)

    def test_fling_velocity_is_not_a_selection_input(self):
        for alleged_velocity in (-100000,-150,0,150,100000):
            t=Toggle(); g=t.geometry; x=g.endpoint(False); t.down(x,66); t.up(x+30,66)
            self.assertEqual((t.native,t.proposals),(False,0))

if __name__ == '__main__':
    unittest.main(verbosity=2)
