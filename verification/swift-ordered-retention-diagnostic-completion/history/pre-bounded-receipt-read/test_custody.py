"""Independent finite adversaries for the new helper, not event replay tests."""
from pathlib import Path
import json, os, struct, tarfile, tempfile, unittest
import custody as c

class Script(c.IO):
    def __init__(self,read_size=None,write_size=None,interrupts=0,zero=None,error=None,mutate=None):
        self.read_size=read_size;self.write_size=write_size;self.interrupts=interrupts
        self.zero=zero;self.error=error;self.mutate=mutate;self.done=False
    def readinto(self,f,v):
        if self.interrupts:self.interrupts-=1;raise InterruptedError()
        if self.error=='read':raise OSError('owned read injection')
        if self.zero=='read':return 0
        return f.readinto(v if self.read_size is None else v[:self.read_size])
    def write(self,f,v):
        if self.error=='write':raise OSError('owned write injection')
        if self.zero=='write':return 0
        return f.write(v if self.write_size is None else v[:self.write_size])
    def observe(self,point,source,destination):
        if not self.done and self.mutate and point=='final':
            self.done=True;self.mutate(source,destination)

class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.owner=tempfile.TemporaryDirectory(prefix='custody-control-',dir=Path(__file__).resolve().parent/'.scratch')
        self.root=Path(self.owner.name)
    def tearDown(self):
        evidence=Path(__file__).resolve().parent/'custody-controls';evidence.mkdir(exist_ok=True)
        with tarfile.open(evidence/(self._testMethodName+'.tar.gz'),'w:gz') as t:
            for p in sorted(self.root.rglob('*')):t.add(p,arcname=p.relative_to(self.root),recursive=False)
        self.owner.cleanup()
    def fixture(self,mutation=None):
        p=self.root/'input.bin';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        initial=c.metadata(os.fstat(fd))
        h=bytearray(512);struct.pack_into('<10Q',h,0,0x315244524f58494d,1,512,128,512,2,80000,64,512,49);h[128:256]=bytes([7])*128
        events=bytearray(256);struct.pack_into('<Q',events,0,1);struct.pack_into('<Q',events,128,2)
        f=bytearray(512);struct.pack_into('<10Q',f,0,0x31444e454f58494d,1,2,3,1,2,0,0,0,1)
        raw=h+events+f
        if mutation:mutation(raw)
        self.assertEqual(os.write(fd,raw),len(raw));final=c.metadata(os.fstat(fd));os.close(fd)
        p.with_suffix('.initial.json').write_text(json.dumps(initial));p.with_suffix('.final.json').write_text(json.dumps(final))
        p.with_suffix('.original.txt').write_text('original_failure=None\noriginal_final_usage=synthetic custody-only fixture\n')
        return p
    def capture(self,p,ops=None):
        result=c.capture(p,self.root/'copy.bin',ops);(self.root/'capture-result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');return result
    def invalid(self,receipt):
        self.assertEqual(receipt['status'],'captured-invalid');self.assertFalse(receipt['fullReplayAccepted'])
        s=json.loads((self.root/'copy.sidecar.json').read_bytes());self.assertEqual(set(s),set(c.SIDECAR_KEYS));self.assertEqual((s['status'],s['failure']),('invalid',15));self.assertNotIn('fullReplayAccepted',s)
    def test_cap_only_never_promotes(self):self.invalid(self.capture(self.fixture()))
    def test_corrupt_cap_header_version_never_promotes(self):self.invalid(self.capture(self.fixture(lambda b:struct.pack_into('<Q',b,8,2))))
    def test_corrupt_cap_record_sequence_never_promotes(self):self.invalid(self.capture(self.fixture(lambda b:struct.pack_into('<Q',b,512,9))))
    def test_corrupt_cap_footer_stored_count_never_promotes(self):self.invalid(self.capture(self.fixture(lambda b:struct.pack_into('<Q',b,784,1))))
    def test_short_reads_and_writes_complete_within_bound(self):
        r=self.capture(self.fixture(),Script(read_size=17,write_size=3));self.invalid(r);self.assertLessEqual(r['maxCombinedAttempts'],32)
    def test_interrupted_at_combined_boundary(self):
        r=self.capture(self.fixture(),Script(interrupts=30));self.invalid(r);self.assertEqual(r['maxCombinedAttempts'],32)
    def test_interrupted_budget_refuses_retains_exclusive_destination(self):
        p=self.fixture();r=self.capture(p,Script(interrupts=31));self.assertEqual(r['error'],'attempt-cap');self.assertTrue(r['destinationRetained']);self.assertEqual(r['copyAttempts'],1);self.assertEqual((self.root/'copy.bin').stat().st_size,0)
    def test_write_quantum_exhausts_combined_attempt_cap(self):
        r=self.capture(self.fixture(),Script(write_size=1));self.assertEqual(r['error'],'attempt-cap');self.assertTrue(r['destinationRetained']);self.assertEqual((self.root/'copy.bin').stat().st_size,31)
    def test_zero_read_refuses(self):
        r=self.capture(self.fixture(),Script(zero='read'));self.assertEqual(r['error'],'source-short');self.assertTrue(r['destinationRetained'])
    def test_zero_write_refuses(self):
        r=self.capture(self.fixture(),Script(zero='write'));self.assertEqual(r['error'],'destination-short');self.assertTrue(r['destinationRetained'])
    def test_read_error_refuses(self):self.assertEqual(self.capture(self.fixture(),Script(error='read'))['error'],'OSError')
    def test_write_error_refuses(self):self.assertEqual(self.capture(self.fixture(),Script(error='write'))['error'],'OSError')
    def test_source_path_identity_drift_refuses(self):
        p=self.fixture()
        def change(source,destination):p.rename(p.with_suffix('.displaced'));p.write_bytes(b'x'*1280)
        self.assertEqual(self.capture(p,Script(mutate=change))['error'],'source-final-drift')
    def test_source_length_drift_refuses(self):
        p=self.fixture()
        def change(source,destination):os.truncate(p,1200)
        self.assertEqual(self.capture(p,Script(mutate=change))['error'],'source-final-drift')
    def test_destination_path_identity_drift_refuses(self):
        p=self.fixture();dest=self.root/'copy.bin'
        def change(source,destination):dest.rename(dest.with_suffix('.displaced'));dest.write_bytes(b'x'*1280)
        self.assertEqual(self.capture(p,Script(mutate=change))['error'],'destination-final-drift')
    def test_destination_length_drift_refuses(self):
        def change(source,destination):os.ftruncate(destination.fileno(),1200)
        self.assertEqual(self.capture(self.fixture(),Script(mutate=change))['error'],'destination-final-drift')
    def test_nonregular_initial_source_refuses_without_copy(self):
        p=self.fixture();p.unlink();p.mkdir();r=self.capture(p);self.assertEqual(r['error'],'writer-path-drift');self.assertEqual(r['copyAttempts'],0);self.assertFalse(r['destinationRetained'])
    def test_initial_path_drift_refuses_without_copy(self):
        p=self.fixture();p.rename(p.with_suffix('.displaced'));p.write_bytes(b'x'*1280);r=self.capture(p);self.assertEqual(r['copyAttempts'],0);self.assertFalse(r['destinationRetained'])
    def test_no_retry_into_existing_destination(self):
        p=self.fixture();dest=self.root/'copy.bin';dest.write_bytes(b'preserve');r=self.capture(p);self.assertEqual(r['error'],'FileExistsError');self.assertEqual(dest.read_bytes(),b'preserve');self.assertEqual(r['copyAttempts'],1)
    def test_complete_host_inventory_below_unchanged_ceiling(self):self.assertLessEqual(c.inventory()['peak'],131072)

if __name__=='__main__':unittest.main(verbosity=2)
