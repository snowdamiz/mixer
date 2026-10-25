"""Independent finite custody and actual-output assertions, never full replay."""
from pathlib import Path
import gc, importlib.util, json, os, re, struct, sys, unittest, weakref
from unittest.mock import patch

P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('completion_custody_review',P/'.scratch/host/custody.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
ATTEMPT=sys.argv[1] if len(sys.argv)>1 else '1'
assert ATTEMPT.isdigit()
ROOT=P/('.scratch/host/independent-'+ATTEMPT);ROOT.mkdir(exist_ok=False)
observations={}
def dump(name,value):(P/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def fixture(root):
    root.mkdir(exist_ok=False);p=root/'stream.bin'
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);initial=c.metadata(os.fstat(fd))
    raw=bytearray(1280);struct.pack_into('<Q',raw,0,0x315244524f58494d);raw[128:256]=bytes([7])*128
    struct.pack_into('<Q',raw,768+72,1);os.write(fd,raw);final=c.metadata(os.fstat(fd));os.close(fd)
    p.with_suffix('.initial.json').write_text(json.dumps(initial));p.with_suffix('.final.json').write_text(json.dumps(final));p.with_suffix('.original.txt').write_text('original_failure=None\noriginal_final_usage=owned finite custody fixture\n')
    return p

class IndependentControls(unittest.TestCase):
    def test_01_actual_source_owners_retire_before_next_copy_phase(self):
        source=fixture(ROOT/'owners');original=c.io.FileIO
        counts={'live':0,'open':0,'maxLive':0,'maxOpen':0,'created':0,'closed':0,'destroyed':0}
        class Tracked:
            def __init__(self,*args,**kwargs):
                self.file=original(*args,**kwargs);self.closed=False
                counts['created']+=1;counts['live']+=1;counts['open']+=1
                counts['maxLive']=max(counts['maxLive'],counts['live']);counts['maxOpen']=max(counts['maxOpen'],counts['open'])
                weakref.finalize(self,retire)
            def close(self):
                if not self.closed:self.closed=True;counts['open']-=1;counts['closed']+=1
                return self.file.close()
            def __getattr__(self,name):return getattr(self.file,name)
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        def retire():counts['live']-=1;counts['destroyed']+=1
        with patch.object(c.io,'FileIO',Tracked):receipt=c.capture(source,source.parent/'copy.bin')
        gc.collect();self.assertEqual(receipt['status'],'captured-invalid');self.assertEqual(counts['maxLive'],2);self.assertEqual(counts['maxOpen'],2);self.assertEqual(counts['live'],0);self.assertEqual(counts['open'],0);self.assertEqual(counts['created'],counts['destroyed']);self.assertEqual(counts['created'],counts['closed'])
        observations['ownerScopes']={'counts':counts,'receipt':receipt}

    def test_02_growth_after_fstat_cannot_request_an_unbounded_read(self):
        root=ROOT/'growth';root.mkdir();p=root/'receipt';p.write_bytes(b'{}');original=c.io.FileIO;requested=[]
        class Grow:
            def __init__(self,*args,**kwargs):self.file=original(*args,**kwargs)
            def __getattr__(self,name):return getattr(self.file,name)
            def __enter__(self):return self
            def __exit__(self,*args):self.file.close()
            def read(self,n=-1):
                requested.append(n);p.write_bytes(b'x'*200000);return self.file.read(n)
        with patch.object(c.io,'FileIO',Grow):
            with self.assertRaises(c.Refusal) as caught:c.load_bounded(p,2048)
        self.assertEqual(caught.exception.code,'receipt-cap');self.assertEqual(requested,[2049])
        observations['receiptGrowth']={'requested':requested,'ownedFileBytes':p.stat().st_size,'error':caught.exception.code}

    def test_03_receipt_symlink_is_refused(self):
        root=ROOT/'symlink';root.mkdir();p=root/'actual';p.write_bytes(b'{}');link=root/'receipt';link.symlink_to(p)
        with self.assertRaises(OSError):c.load_bounded(link,2048)
        observations['receiptSymlink']={'refused':True,'targetUnchanged':p.read_bytes()==b'{}'}

    def test_04_combined_attempt_budget_counts_actual_calls(self):
        source=fixture(ROOT/'attempts')
        class Interrupt(c.IO):
            reads=0;writes=0
            def readinto(self,file,view):
                self.reads+=1
                if self.reads<=31:raise InterruptedError()
                return file.readinto(view)
            def write(self,file,view):self.writes+=1;return file.write(view)
        ops=Interrupt();receipt=c.capture(source,source.parent/'copy.bin',ops)
        self.assertEqual((ops.reads,ops.writes),(32,0));self.assertEqual(receipt['error'],'attempt-cap');self.assertEqual(receipt['copyAttempts'],1);self.assertTrue(receipt['destinationRetained']);self.assertEqual((source.parent/'copy.bin').stat().st_size,0)
        observations['combinedAttempts']={'reads':ops.reads,'writes':ops.writes,'receipt':receipt}

    def test_05_unknown_cap_payload_never_promotes(self):
        source=fixture(ROOT/'unknown-cap');receipt=c.capture(source,source.parent/'copy.bin')
        self.assertEqual(receipt['status'],'captured-invalid');sidecar=json.loads((source.parent/'copy.sidecar.json').read_bytes())
        self.assertEqual((sidecar['status'],sidecar['failure']),('invalid',15));self.assertEqual(set(sidecar),set(c.SIDECAR_KEYS));self.assertFalse(receipt['fullReplayAccepted']);self.assertNotIn('fullReplayAccepted',sidecar)
        observations['unknownCap']={'receipt':receipt,'sidecar':sidecar}

    def test_06_actual_hook_prefixes_and_original_parity(self):
        output=(P/'commands/candidate-swift/stdout.txt').read_text();cases=[]
        for name,pattern in [('publication',r'COMPLETION publication originalParity=true stream=(\S+)'),('eviction',r'COMPLETION evictTaken originalParity=true stream=(\S+)'),('wrong-owner',r'COMPLETION release stale=false originalParity=true stream=(\S+)'),('stale',r'COMPLETION release stale=true originalParity=true stream=(\S+)')]:
            match=re.search(pattern,output);self.assertIsNotNone(match);path=Path(match.group(1));raw=path.read_bytes();self.assertLessEqual(len(raw),16384);self.assertGreaterEqual(len(raw),1024);self.assertEqual((len(raw)-1024)%128,0)
            rows=[struct.unpack('<16Q',raw[i:i+128]) for i in range(512,len(raw)-512,128)];footer=struct.unpack('<64Q',raw[-512:]);kinds=[r[1] for r in rows]
            self.assertEqual(footer[16:31],(0,)*15);self.assertEqual(footer[31],1 if name=='eviction' else 0)
            if name=='publication':
                self.assertEqual(footer[9],0);self.assertTrue(all(k in kinds for k in [1,9,10,14,13]));self.assertNotIn(11,kinds)
                failures=[r for r in rows if r[1]==14];self.assertEqual(len(failures),2);self.assertGreater(failures[0][3],0);self.assertEqual(failures[1][3],0);self.assertTrue(all(r[13:]==(2,1,2) for r in failures))
            elif name=='eviction':
                self.assertEqual(len(rows),32);self.assertEqual(kinds[-2:],[6,7]);self.assertNotIn(8,kinds);self.assertEqual(kinds.count(11),5);self.assertEqual(footer[9],128);self.assertEqual(footer[12:15],(21,0,6))
            else:
                self.assertEqual(rows,[]);self.assertEqual(footer[2],9);self.assertEqual(footer[9],128);self.assertEqual(footer[12:15],(21,0,2))
            ident=int(path.stem.split('-')[1]);off=path.with_name('completion-'+str(ident-1)+'.semantic.txt');on=path.with_suffix('.semantic.txt');self.assertEqual(off.read_bytes(),on.read_bytes())
            for src in [path,path.with_suffix('.original.txt'),path.with_suffix('.details.txt'),on,off]:
                data=src.read_bytes();self.assertLessEqual(len(data),16384);target=P/'actual-fixtures'/src.name;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
            cases.append({'name':name,'source':str(path),'records':len(rows),'kinds':kinds,'footerFailure':footer[12:15],'cleanupInvariant':footer[31],'flags':footer[9],'stored':footer[2],'semanticParity':True,'fullReplayAccepted':False})
        observations['actualPrefixes']=cases

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls);result=unittest.TextTestRunner(verbosity=2).run(suite)
    dump('independent-controls-'+ATTEMPT+'.json',{'passed':result.testsRun-len(result.failures)-len(result.errors),'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'observations':observations,'scope':'bounded actual-prefix and custody assertions; no full replay acceptance'})
    sys.exit(0 if result.wasSuccessful() else 1)
