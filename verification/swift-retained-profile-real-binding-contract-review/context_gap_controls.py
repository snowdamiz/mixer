"""Confirm the frozen framing scope, without claiming it is a real decoder."""
import unittest
import context_contract as c

class ExistingFramingBoundary(unittest.TestCase):
    def observe_result(self, result):
        observation=c.observe_framing(c.blank_selection()+bytes(result)+c.blank_custody())
        self.assertTrue(observation['data_framing_observed'])
        self.assertFalse(any(value for key,value in observation.items() if key!='data_framing_observed'))
    def test_present_failure_with_zero_invalid_payload_is_only_framed(self):
        r=bytearray(c.blank_result());r[32:40]=c.u64(1);self.observe_result(r)
    def test_present_final_usage_with_zero_invalid_origin_is_only_framed(self):
        r=bytearray(c.blank_result());r[32:40]=c.u64(4);self.observe_result(r)
    def test_constructor_participation_with_no_receipt_is_only_framed(self):
        for tag in range(1,9):
            r=bytearray(c.blank_result());r[40:48]=c.u64(tag);self.observe_result(r)

if __name__=='__main__':unittest.main(verbosity=2)
