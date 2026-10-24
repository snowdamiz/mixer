"""Real temporary-file race controls; no native instances or UI APIs."""
import errno
import hashlib
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock
import observation_reader as r
import run

PAYLOAD={'state':{'identity':'host-only','isOn':False,'retainedOn':False,'enabled':True,'allowed':True},'events':[{'sequence':0}]}

class ReaderControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name).resolve();self.docs=self.root/'Documents';self.docs.mkdir();self.path=self.docs/'observations.json'
        self.replace(PAYLOAD);self.opened=[];self.closed=[]
        self.real_open=os.open;self.real_close=os.close;self.real_fstat=os.fstat
        def opened(*args,**kwargs):
            fd=self.real_open(*args,**kwargs);self.opened.append(fd);return fd
        def closed(fd):self.closed.append(fd);return self.real_close(fd)
        self.opener=mock.patch.object(r.os,'open',side_effect=opened);self.closer=mock.patch.object(r.os,'close',side_effect=closed)
        self.opener.start();self.closer.start();self.addCleanup(self.opener.stop);self.addCleanup(self.closer.stop)
    def tearDown(self):self.assertEqual(self.opened,self.closed,'Every opened descriptor must close exactly once')
    def replace(self,value):
        temporary=self.docs/'replacement.json';temporary.write_text(json.dumps(value));temporary.replace(self.path)
    def read(self,**kwargs):return r.read_observation(self.docs,deadline=r.time.monotonic()+1,**kwargs)
    def reject(self):
        prior=len(self.opened)
        with self.assertRaises((ValueError,OSError,UnicodeError)):self.read()
        self.assertLessEqual(len(self.opened)-prior,1)
        self.assertEqual(self.opened,self.closed)

    def test_stable_regular_payload_signature(self):
        value,signature=self.read();self.assertEqual(value,PAYLOAD)
        self.assertEqual(signature,[self.path.stat().st_ino,self.path.stat().st_mtime_ns,len(self.path.read_bytes()),hashlib.sha256(self.path.read_bytes()).hexdigest()])
        self.assertEqual(len(self.opened),1)

    def test_atomic_replace_before_first_fstat_reopens_unlinked_inode(self):
        fired=False
        def fstat(fd):
            nonlocal fired
            if not fired:fired=True;self.replace({**PAYLOAD,'version':2});self.assertEqual(self.real_fstat(fd).st_nlink,0)
            return self.real_fstat(fd)
        with mock.patch.object(r.os,'fstat',side_effect=fstat):value,_=self.read()
        self.assertEqual(value['version'],2);self.assertEqual(len(self.opened),2)

    def test_atomic_replace_during_read_rejects_old_bytes(self):
        original=r.read_payload;fired=False
        def payload(fd):
            nonlocal fired
            value=original(fd)
            if not fired:fired=True;self.replace({**PAYLOAD,'version':2});self.assertEqual(self.real_fstat(fd).st_nlink,0)
            return value
        with mock.patch.object(r,'read_payload',side_effect=payload):value,_=self.read()
        self.assertEqual(value['version'],2);self.assertEqual(len(self.opened),2)

    def test_repeated_replace_never_accepts_links_zero_and_stops_at_four(self):
        def fstat(fd):self.replace(PAYLOAD);return self.real_fstat(fd)
        with mock.patch.object(r.os,'fstat',side_effect=fstat),self.assertRaises(FileNotFoundError):self.read()
        self.assertEqual(len(self.opened),4)

    def test_missing_file_retries_only_fixed_attempt_count(self):
        self.path.unlink();calls=[]
        def opening(*args,**kwargs):calls.append(args);return self.real_open(*args,**kwargs)
        with mock.patch.object(r.os,'open',side_effect=opening),self.assertRaises(FileNotFoundError):self.read()
        self.assertEqual(len(calls),4);self.assertEqual(self.opened,[])

    def test_unlinked_inode_with_missing_canonical_name_is_never_accepted(self):
        fired=False
        def fstat(fd):
            nonlocal fired
            if not fired:fired=True;self.path.unlink()
            return self.real_fstat(fd)
        with mock.patch.object(r.os,'fstat',side_effect=fstat),self.assertRaises(FileNotFoundError):self.read()
        self.assertEqual(len(self.opened),1)

    def test_symlink_leaf_and_documents_fail_closed(self):
        target=self.docs/'target.json';self.path.rename(target);self.path.symlink_to(target)
        self.reject();self.assertEqual(self.opened,[])
        self.path.unlink();target.rename(self.path)
        link=self.root/'linked-documents';link.symlink_to(self.docs,target_is_directory=True)
        with self.assertRaises(ValueError):r.read_observation(link,deadline=r.time.monotonic()+1)

    def test_nofollow_blocks_symlink_inserted_between_path_check_and_open(self):
        target=self.docs/'target.json';target.write_text(json.dumps(PAYLOAD))
        def opening(path,flags):
            self.assertTrue(flags & os.O_NOFOLLOW);self.path.unlink();self.path.symlink_to(target)
            return self.real_open(path,flags)
        with mock.patch.object(r.os,'open',side_effect=opening):self.reject()
        self.assertEqual(self.opened,[])

    def test_hardlinked_payload_fails_closed(self):
        os.link(self.path,self.docs/'alias.json');self.reject();self.assertEqual(len(self.opened),1)

    def test_replacement_with_symlink_is_not_retryable(self):
        original=r.read_payload;target=self.docs/'target.json';target.write_text(json.dumps(PAYLOAD))
        def payload(fd):
            value=original(fd);self.path.unlink();self.path.symlink_to(target);return value
        with mock.patch.object(r,'read_payload',side_effect=payload):self.reject()

    def test_parent_redirect_during_read_is_not_accepted(self):
        original=r.read_payload;foreign=self.root/'foreign';foreign.mkdir();(foreign/'observations.json').write_text(json.dumps(PAYLOAD))
        def payload(fd):
            value=original(fd);self.docs.rename(self.root/'prior-documents');self.docs.symlink_to(foreign,target_is_directory=True);return value
        with mock.patch.object(r,'read_payload',side_effect=payload):self.reject()

    def test_replacement_with_hardlink_is_not_retryable(self):
        original=r.read_payload;target=self.docs/'target.json';target.write_text(json.dumps(PAYLOAD))
        def payload(fd):
            value=original(fd);self.path.unlink();os.link(target,self.path);return value
        with mock.patch.object(r,'read_payload',side_effect=payload):self.reject()

    def test_zero_oversize_directory_and_fifo_are_rejected(self):
        self.path.write_bytes(b'');self.reject()
        self.path.write_bytes(b'x'*(r.MAX_OBSERVATION+1));self.reject()
        self.path.unlink();self.path.mkdir();self.reject()
        self.path.rmdir();os.mkfifo(self.path)
        self.reject()

    def test_malformed_schema_json_duplicates_utf8_and_nonfinite_fail_closed(self):
        for payload in [b'{',b'\xff',b'{"state":{},"state":{}}',b'{"state":NaN,"events":[1]}',b'[]',b'{}',b'{"state":{"identity":"x","isOn":0},"events":[1]}']:
            with self.subTest(payload=payload):
                self.opened.clear();self.closed.clear();self.path.write_bytes(payload);self.reject()
        for value in [{**PAYLOAD,'events':[]},{**PAYLOAD,'state':{**PAYLOAD['state'],'identity':''}},{**PAYLOAD,'state':{**PAYLOAD['state'],'enabled':1}}]:
            self.opened.clear();self.closed.clear();self.replace(value);self.reject()

    def test_in_place_mutation_is_not_atomic_retry(self):
        original=r.read_payload
        def payload(fd):
            value=original(fd);self.path.write_text(json.dumps({**PAYLOAD,'new':1}));return value
        with mock.patch.object(r,'read_payload',side_effect=payload):self.reject()

    def test_metadata_is_rechecked_after_json_parse(self):
        original=r.json.loads
        def loads(*args,**kwargs):
            value=original(*args,**kwargs);self.path.chmod(0o600);return value
        with mock.patch.object(r.json,'loads',side_effect=loads):self.reject()

    def test_payload_bounds_and_read_failures_close_descriptor(self):
        with mock.patch.object(r,'read_payload',return_value=b'x'*(r.MAX_OBSERVATION+1)):self.reject()
        self.opened.clear();self.closed.clear()
        with mock.patch.object(r,'read_payload',side_effect=OSError(errno.EIO,'host-injected-read-failure')):self.reject()

    def test_expired_deadline_never_opens_or_accepts_late_result(self):
        with mock.patch.object(r,'read_once') as once,self.assertRaises(FileNotFoundError):r.read_observation(self.docs,deadline=10,clock=lambda:10)
        once.assert_not_called()
        with self.assertRaises(FileNotFoundError):r.read_observation(self.docs,deadline=10,clock=iter([9,10]).__next__)
        self.assertEqual(len(self.opened),1)

    def test_retry_uses_one_absolute_deadline_without_refresh(self):
        with mock.patch.object(r,'read_once',side_effect=FileNotFoundError('host-only-race')) as once,self.assertRaises(FileNotFoundError):
            r.read_observation(self.docs,deadline=1.15,clock=iter([1,1.1,1.2]).__next__)
        self.assertEqual(once.call_count,2)

    def test_deadline_and_attempt_parameters_have_strict_types(self):
        for deadline in [True,float('inf'),float('nan'),'100']:
            with self.assertRaises(ValueError):r.read_observation(self.docs,deadline=deadline)
        for attempts in [0,5,True,1.0]:
            with self.assertRaises(ValueError):self.read(max_attempts=attempts)
        self.assertEqual(self.opened,[])

class DeadlineAdapterControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name).resolve()
        self.base=run.inherited_bridge.Bridge;self.cls=r.deadline_bridge(self.base)
        self.bridge=self.cls({'diagnostic':self.root,'comparator':self.root},self.root/'out','host-only-capability',{'scope':'host-only'},allowed_cases={'commit-rebind-off'})
        self.bridge.current={'candidate':'diagnostic','case':'commit-rebind-off'}
    def test_wait_propagates_same_earlier_deadline_across_retries(self):
        now=[100.0];deadlines=[]
        def reading(documents,*,deadline,max_attempts):
            deadlines.append((deadline,max_attempts))
            if len(deadlines)<4:raise FileNotFoundError('host-only-atomic-race')
            return PAYLOAD,[1,2,3,'host-only']
        self.bridge.deadline=700
        with mock.patch.object(r.time,'monotonic',side_effect=lambda:now[0]),mock.patch.object(r.time,'sleep',side_effect=lambda n:now.__setitem__(0,now[0]+n)),mock.patch.object(r,'read_observation',side_effect=reading):
            self.assertEqual(self.bridge.wait(lambda *_:True)[0],PAYLOAD)
        self.assertEqual(deadlines,[(106.0,4)]*4);self.assertFalse(hasattr(self.bridge,'_observation_read_deadline'))
    def test_wait_clamps_to_existing_session_and_restores_prior_deadline(self):
        self.bridge.deadline=102;self.bridge._observation_read_deadline=101
        with mock.patch.object(r.time,'monotonic',return_value=100),mock.patch.object(r,'read_observation',return_value=(PAYLOAD,[1])) as reading:
            self.bridge.wait(lambda *_:True)
        self.assertEqual(reading.call_args.kwargs,{'deadline':101,'max_attempts':4});self.assertEqual(self.bridge._observation_read_deadline,101)
    def test_direct_reads_are_clamped_to_session_or_fifty_ms(self):
        for session,expected in [(700,100.05),(100.01,100.01)]:
            self.bridge.deadline=session
            with mock.patch.object(r.time,'monotonic',return_value=100),mock.patch.object(r,'read_observation',return_value=(PAYLOAD,[1])) as reading:self.bridge.observe()
            self.assertEqual(reading.call_args.kwargs,{'deadline':expected,'max_attempts':4})
    def test_wait_exception_restores_context_and_inherits_authority(self):
        self.bridge.deadline=700
        with mock.patch.object(r.time,'monotonic',return_value=100),mock.patch.object(r,'read_observation',side_effect=ValueError('host-only-malformed')),self.assertRaises(ValueError):self.bridge.wait(lambda *_:True)
        self.assertFalse(hasattr(self.bridge,'_observation_read_deadline'))
        for name in ['request','_request','write_command','save','persist_summary','record_failure']:
            self.assertIs(getattr(self.cls,name),getattr(self.base,name))
        self.assertIs(run.inherited.Bridge.__base__,self.base)

if __name__=='__main__':unittest.main()
