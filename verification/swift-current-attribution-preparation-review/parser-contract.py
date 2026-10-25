#!/usr/bin/env python3
"""Six independent negative schema cases. Failure is retained review evidence."""
from pathlib import Path
import copy,importlib.util,json,unittest
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('independent_telemetry_snapshot',H/'input-snapshots/telemetry.py')
telemetry=importlib.util.module_from_spec(spec);spec.loader.exec_module(telemetry)
original=json.loads((H/'parser-original-events.json').read_text());observations=[]
class IndependentParserContract(unittest.TestCase):
    def check(self,mode):
        before=copy.deepcopy(original);path=H/'parser-reproductions'/(mode+'.stdout')
        result=telemetry.classify(path,original)
        observations.append({'mode':mode,'path':str(path.relative_to(H)),'classification':result})
        self.assertEqual(original,before);self.assertFalse(result['originalResultReplaced']);self.assertFalse(result['cleanupTruthInferredFromTelemetry'])
        self.assertEqual(result['status'],'invalid_or_missing','Impossible fixed unsigned telemetry must not be valid attribution')
    def test_float_in_integer_contract(self):self.check('integer_as_float')
    def test_bool_sequence_is_not_integer(self):self.check('bool_sequence')
    def test_negative_successful_credits(self):self.check('negative_credit')
    def test_wrong_fixed_array_length(self):self.check('wrong_calls_length')
    def test_unknown_aggregate_field(self):self.check('unknown_aggregate')
    def test_malformed_optional_rejection(self):self.check('invalid_first_rejection')
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentParserContract)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (H/'parser-classifications.json').write_text(json.dumps({'cases':observations,'testsRun':result.testsRun,'failed':len(result.failures),'errors':len(result.errors),'candidateSnapshot':'c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1'},indent=2,sort_keys=True)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
