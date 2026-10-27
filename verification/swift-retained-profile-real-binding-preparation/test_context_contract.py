import hashlib
import unittest
import context_contract as c

class ContextContract(unittest.TestCase):
    def setUp(self):
        self.raw=c.blank_selection()+c.blank_result()+c.blank_custody()

    def changed_word(self,index,value):
        b=bytearray(self.raw);b[index*8:index*8+8]=c.u64(value);return bytes(b)

    def test_exact_partition_and_no_authority(self):
        self.assertEqual(c.PARTITIONS,((0,4096),(4096,2048),(6144,2048)))
        o=c.observe_framing(self.raw)
        self.assertTrue(o["data_framing_observed"])
        self.assertTrue(all(not v for k,v in o.items() if k!="data_framing_observed"))

    def test_all_extent_version_offset_count_reserved_fields(self):
        for i in (1,2,3,4,5,6,7,8,9,10,11,12,15):
            with self.subTest(word=i),self.assertRaises(c.Refusal):
                c.observe_framing(self.changed_word(i,c.word(self.raw,i)+1))

    def test_extent_failures_and_unknown_context_magic(self):
        for raw in (self.raw[:-1],self.raw+b"\0",b"MIXFIX01"+self.raw[8:],b"MIXRBC01"+self.raw[8:]):
            with self.assertRaises(c.Refusal):c.observe_framing(raw)

    def test_all_reserved_tail_regions(self):
        for offset in (1120,4095,4096+224,4096+255,6144+320,8191):
            raw=bytearray(self.raw);raw[offset]=1
            with self.subTest(offset=offset),self.assertRaises(c.Refusal):c.observe_framing(bytes(raw))

    def test_target_width_and_noncanonical_padding(self):
        for n in (0,129,c.U64):
            with self.assertRaises(c.Refusal):c.observe_framing(self.changed_word(14,n))
        raw=bytearray(self.raw);raw[1039]=1
        with self.assertRaises(c.Refusal):c.observe_framing(bytes(raw))

    def test_u32_and_boolean_widths_do_not_truncate(self):
        for offset in (720,840,848,856):
            with self.subTest(offset=offset),self.assertRaises(c.Refusal):c.observe_framing(self.changed_word(offset//8,1<<32))
        for offset in range(872,912,8):
            with self.assertRaises(c.Refusal):c.observe_framing(self.changed_word(offset//8,2))

    def test_wasi_budget_none_differs_from_some_zero(self):
        some_zero=self.changed_word(13,1)
        self.assertNotEqual(self.raw,some_zero)
        self.assertTrue(c.observe_framing(some_zero)["data_framing_observed"])
        for value in (2,c.U64):
            with self.assertRaises(c.Refusal):c.observe_framing(self.changed_word(13,value))
        for offset in range(816,912,8):
            with self.assertRaises(c.Refusal):c.observe_framing(self.changed_word(offset//8,1))

    def test_absent_snapshots_and_original_tags(self):
        for tag in range(1,9):
            raw=self.changed_word((4096+40)//8,tag)
            self.assertTrue(c.observe_framing(raw)["data_framing_observed"])
        with self.assertRaises(c.Refusal):c.observe_framing(self.changed_word((4096+40)//8,9))
        for offset in (4096+256,4096+512,4096+1024,4096+1536):
            raw=bytearray(self.raw);raw[offset]=1
            with self.assertRaises(c.Refusal):c.observe_framing(bytes(raw))
        with self.assertRaises(c.Refusal):c.observe_framing(self.changed_word((4096+32)//8,2))

    def test_custody_scope_and_counts_fail_closed(self):
        for word,value in ((1,2),(2,2049),(3,2),(4,0),(4,33),(5,0),(5,65537),(6,33),(7,1)):
            with self.subTest(word=word,value=value),self.assertRaises(c.Refusal):c.observe_framing(self.changed_word(6144//8+word,value))

    def test_each_digest_is_joined_independently(self):
        artifacts={name:name.encode() for name in c.DIGESTS}
        expected={k:hashlib.sha256(v).digest() for k,v in artifacts.items()}
        o=c.digest_join(artifacts,expected)
        self.assertFalse(o["producer_provenance_verified"])
        for name in c.DIGESTS:
            altered=dict(artifacts);altered[name]+=b"different"
            with self.subTest(name=name),self.assertRaises(c.Refusal):c.digest_join(altered,expected)

    def test_colluding_digest_bytes_still_have_no_provenance(self):
        artifacts={name:b"deliberately synthetic" for name in c.DIGESTS}
        expected={k:hashlib.sha256(v).digest() for k,v in artifacts.items()}
        self.assertFalse(c.digest_join(artifacts,expected)["producer_provenance_verified"])
        self.assertFalse(c.observe_framing(self.raw)["real_binding_verified"])

    def test_integer_widths_refuse_instead_of_coercing(self):
        for value in (True,False,-1,1.0,1<<64):
            with self.assertRaises(c.Refusal):c.u64(value)
        self.assertEqual(len(c.u64(c.U64)),8)

if __name__=="__main__":unittest.main(verbosity=2)
