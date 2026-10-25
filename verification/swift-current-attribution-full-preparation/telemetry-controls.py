# Additional finite parser controls; inherited ten process-observation controls remain intact.
import copy
import json
import tempfile

class TelemetryTests(unittest.TestCase):
    def row(self,label,sequence):
        payload={'invalid':0,'credits':[0]*16,'calls':[0]*16,'plans':[0]*4,'completed':0,'distinct':0,'repeated':0,'scan_credits':[0,0],'scan_calls':[0,0],'scan_published':[0,0],'build_credits':[0,0],'build_calls':[0,0],'first_rejection':None}
        return dict(lifecycle=label,sequence=sequence,reset_count=1,formatted=True,observer_invalid=0,invariant_mask=0,adapter_invalid=0,prior_write_failed=False,valid=True,cache_work=0,cache_decodes=0,decodes_bound_before_consumption=label=='final_cleanup',payload=payload)
    def fixture(self):
        original=[{'event':'constructed','payload':{'usage':{'cache_work':0},'cache':{'decodes':0}}},{'event':'runtime_failure','payload':{'kind':'WorkExhausted','attempted':64000001,'limit':64000000}},{'event':'final_cleanup_usage','payload':{'cache_work':0}}]
        return original,[self.row('constructed',1),self.row('final_cleanup',2)]
    def classify(self,rows,original,extra=b''):
        with tempfile.TemporaryDirectory(dir=driver.SCRATCH/'tmp') as td:
            path=Path(td)/'stdout';path.write_bytes(b''.join(b'MIXER_ATTRIBUTION '+json.dumps(r,separators=(',',':')).encode()+b'\n' for r in rows)+extra)
            return driver.telemetry.classify(path,original)
    def test_valid_telemetry_leaves_original_failure_authoritative(self):
        original,rows=self.fixture();before=copy.deepcopy(original);r=self.classify(rows,original)
        self.assertEqual(r['status'],'valid');self.assertFalse(r['originalResultReplaced']);self.assertEqual(original,before)
    def test_missing_malformed_and_closed_order_are_separate_invalidity(self):
        original,rows=self.fixture()
        for changed in (rows[:1],rows[::-1],rows+[rows[0]],[self.row('guest_controlled',1),rows[1]]):
            self.assertEqual(self.classify(changed,original)['status'],'invalid_or_missing')
        self.assertEqual(self.classify(rows,original,b'MIXER_ATTRIBUTION {broken\n')['status'],'invalid_or_missing')
    def test_false_formatter_and_true_sticky_invalid_discard_payload(self):
        original,rows=self.fixture()
        for mode in range(3):
            changed=copy.deepcopy(rows);changed[0].update(valid=False,payload=None)
            if mode==0:changed[0].update(formatted=False,observer_invalid=8)
            elif mode==1:changed[0]['observer_invalid']=4
            else:changed[0]['prior_write_failed']=True
            r=self.classify(changed,original);self.assertEqual(r['status'],'invalid_or_missing')
            self.assertFalse(r['originalResultReplaced'])
        changed=copy.deepcopy(rows);changed[0].update(formatted=False,observer_invalid=8)
        self.assertIn('invalid_payload_not_discarded',self.classify(changed,original)['issues'])
    def test_output_and_final_usage_bindings(self):
        original,rows=self.fixture()
        for key,value in [('reset_count',2),('cache_work',1),('decodes_bound_before_consumption',False)]:
            changed=copy.deepcopy(rows);changed[1][key]=value
            self.assertEqual(self.classify(changed,original)['status'],'invalid_or_missing')
        changed=copy.deepcopy(rows);changed[0]['padding']='x'*driver.telemetry.ENVELOPE
        self.assertIn('envelope_overflow',self.classify(changed,original)['issues'])
        self.assertIn('lifetime_output_overflow',self.classify(rows*4,original)['issues'])
