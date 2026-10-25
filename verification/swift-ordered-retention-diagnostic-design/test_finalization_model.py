import itertools
import unittest
from finalization_model import Gate


class FinalizationTests(unittest.TestCase):
    def test_valid_end_has_no_admitted_callbacks(self):
        gate = Gate()
        token = gate.enter()
        gate.check_owner(token)
        gate.leave(token)
        self.assertEqual(gate.end(), 0)
        self.assertIsNone(gate.enter(owner=False))
        self.assertEqual(gate.footer, 0)

    def test_wrong_thread_latch_publishes_before_count_zero(self):
        gate = Gate()
        token = gate.enter(owner=False)
        gate.check_owner(token)
        gate.leave(token)
        self.assertEqual(gate.end(), Gate.CONTEXT)

    def test_end_refuses_live_borrow_without_writer_access(self):
        gate = Gate()
        token = gate.enter()
        self.assertIsNone(gate.end())
        self.assertTrue(gate.end_refused)
        self.assertIsNone(gate.footer)
        gate.borrow_failure(token)
        gate.leave(token)
        self.assertIsNone(gate.footer)

    def test_failed_quiescence_and_wrong_end_owner_fail_closed(self):
        for kwargs in ({'owner': False}, {'quiescence_proven': False}):
            gate = Gate()
            self.assertIsNone(gate.end(**kwargs))
            self.assertTrue(gate.end_refused)

    def test_duplicate_end_and_release_are_rejected(self):
        gate = Gate()
        token = gate.enter()
        gate.leave(token)
        with self.assertRaises(ValueError):
            gate.leave(token)
        gate.end()
        with self.assertRaises(ValueError):
            gate.end()

    def test_all_140_two_callback_end_interleavings(self):
        checked = 0
        # owner and wrong-thread enter/check/leave chains; one independent End.
        for order in itertools.permutations(('ae', 'ac', 'al', 'be', 'bc', 'bl', 'end')):
            if not (order.index('ae') < order.index('ac') < order.index('al') and
                    order.index('be') < order.index('bc') < order.index('bl')):
                continue
            gate, tokens = Gate(), {}
            admitted_wrong = False
            for step in order:
                if step == 'end':
                    gate.end()
                elif step[1] == 'e':
                    tokens[step[0]] = gate.enter(owner=step[0] == 'a')
                    admitted_wrong |= step[0] == 'b' and tokens[step[0]] is not None
                elif tokens[step[0]] is not None:
                    if step[1] == 'c':
                        gate.check_owner(tokens[step[0]])
                    else:
                        gate.leave(tokens[step[0]])
            if gate.footer == 0:
                self.assertFalse(admitted_wrong)
                self.assertFalse(gate.end_refused)
            if admitted_wrong:
                self.assertTrue(gate.footer == Gate.CONTEXT or gate.end_refused)
            checked += 1
        self.assertEqual(checked, 140)


if __name__ == '__main__':
    unittest.main(verbosity=2)
