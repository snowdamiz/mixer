import unittest
import format_model as f

class FormatPreparation(unittest.TestCase):
    def change(self,data,offset,value):
        b=bytearray(data); b[offset:offset+8]=f.words([value]); return bytes(b)
    def refuses(self,data):
        with self.assertRaises(f.Refused): f.parse(data)
    def test_fixed_sizes_and_maximum(self):
        self.assertEqual((f.HEADER,f.SNAPSHOT_CAP),(2560,69765152))
        self.assertEqual(len(f.USAGE),10); self.assertEqual(len(f.OBSERVATIONS),20)
        self.assertEqual(len(f.RUN_LIMITS),17); self.assertEqual(len(f.DIGESTS),6)
        self.assertEqual(len(f.FILE_FIELDS),8); self.assertEqual(len(f.SECTIONS),9)
    def test_complete_synthetic_snapshot_and_spare_capacity(self):
        for wasi in (False,True):
            for spare in (0,3):
                data=f.assemble_unverified_fixture(wasi,spare)
                result=f.parse(data)
                self.assertEqual(result['source'],bytes(range(64)))
                self.assertEqual(result['total'],len(data))
                self.assertEqual(len(data),len(f.assemble_unverified_fixture(wasi,0)))
    def test_resolved_imports_are_distinct_from_metadata_imports(self):
        a=f.assemble_unverified_fixture();r=f.parse(a)
        self.assertEqual(r['resolved_imports'],list(range(1,35)))
        for i in range(34):
            for invalid in (0,35):self.refuses(self.change(a,2176+i*8,invalid))
        # Recognized but reordered resolved imports are representable untrusted data.
        b=self.change(a,2176,34)
        self.assertEqual(f.parse(b)['resolved_imports'][0],34)
    def test_all_eight_buffer_inventory_checks(self):
        a=f.assemble_unverified_fixture()
        for sid in range(1,9):
            base=1600+sid*64
            for slot,value in [(0,99),(2,0),(3,0),(4,0),(5,1),(6,0),(7,1)]:
                self.refuses(self.change(a,base+8*slot,value))
    def test_sections_are_exact_contiguous_and_bounded(self):
        a=f.assemble_unverified_fixture()
        self.refuses(a[:-1]);self.refuses(a+b'\0')
        for sid,_,_,cap in f.SECTIONS:
            self.refuses(self.change(a,1600+sid*64+8,cap+1))
        self.refuses(self.change(a,24,f.U64))
        self.refuses(self.change(a,1600+16,f.U64))
    def test_all_reserved_ranges_and_absent_option_payloads(self):
        a=f.assemble_unverified_fixture()
        for start,end in [(136,144),(488,512),(1032,1088),(1424,1600),(2448,2560)]:
            for offset in (start,end-1):
                b=bytearray(a);b[offset]=1;self.refuses(bytes(b))
        for offset in [224+15*8,384+7*8,1264,1320]:
            self.refuses(self.change(a,offset,1))
    def test_enum_options_and_integer_widths(self):
        a=f.assemble_unverified_fixture(True)
        for offset,value in [(224+14*8,2),(224+15*8,f.U32+1),(384,2),(1112,2),(1320,2),(1208,769)]:
            self.refuses(self.change(a,offset,value))
        with self.assertRaises(f.Refused):f.words([f.U64+1])
        with self.assertRaises(f.Refused):f.words([-1])
    def test_provenance_and_runtime_cross_record_equalities(self):
        a=f.assemble_unverified_fixture()
        for offset in [64,96,536,544,1360,144]:
            self.refuses(self.change(a,offset,65))
        for offset in [512,1088]:
            b=bytearray(a);b[offset]^=1;self.refuses(bytes(b))
    def test_native_capacity_inventory_and_usage(self):
        a=f.assemble_unverified_fixture()
        self.refuses(self.change(a,144+2*8,0))
        self.refuses(self.change(a,1600+64+2*8,f.U64))
        self.refuses(self.change(a,1600+64+3*8,65))
        self.refuses(self.change(a,1600+64+4*8,f.METADATA_CAP+1))
    def test_unknown_magics_versions_and_padding(self):
        a=f.assemble_unverified_fixture()
        for offset in [0,8,16,32,40,48,56,520,528,1096,1104]:
            b=bytearray(a);b[offset]^=128;self.refuses(bytes(b))
    def test_partial_write_32nd_call_and_no_33rd(self):
        self.assertEqual(f.model_bounded_write(4096,[1]*31+[4065]),('complete',4096,32))
        self.assertEqual(f.model_bounded_write(4096,[1]*32+[4064]),('attempts',32,32))
        self.assertEqual(f.model_bounded_write(4096,['interrupted']*32+[4096]),('attempts',0,32))
        self.assertEqual(f.model_bounded_write(4097,[4096,1]),('complete',4097,2))
    def test_partial_write_preserves_observed_progress(self):
        for result,code in [('io','io'),(0,'zero'),(4090,'overreported')]:
            self.assertEqual(f.model_bounded_write(4096,[12,result]),(code,12,2))
        self.assertEqual(f.model_bounded_write(0,[]),('complete',0,0))

if __name__ == '__main__': unittest.main(verbosity=2)
