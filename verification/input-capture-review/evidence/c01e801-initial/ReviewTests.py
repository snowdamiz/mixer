"""Original bounded probes; production capture implementation is imported read-only."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
MODULE = Path(os.environ['CAPTURE_REVIEW_MODULE'])
TOOL = Path(os.environ['CAPTURE_REVIEW_TOOL'])
FIXTURE = Path(os.environ['CAPTURE_REVIEW_DESCRIPTOR'])
SPEC = importlib.util.spec_from_file_location('reviewed_capture', MODULE)
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)

def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()+b'\n'
def sha(value):
    return hashlib.sha256(value).hexdigest()
def digest_pointers(value, prefix=''):
    result=[]
    if type(value) is dict:
        for k,v in value.items():
            if k.endswith('_sha256'): result.append(prefix+'/'+k)
            else: result.extend(digest_pointers(v,prefix+'/'+k))
    elif type(value) is list:
        for i,v in enumerate(value): result.extend(digest_pointers(v,prefix+'/'+str(i)))
    return sorted(result)

def set_pointer(value,pointer,replacement):
    parts=pointer.split('/')[1:]
    for part in parts[:-1]: value=value[int(part)] if type(value) is list else value[part]
    value[parts[-1]]=replacement

class IndependentInputCapture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='mixer-independent-capture-')
        self.base=Path(self.tmp.name);self.inputs=self.base/'input';self.inputs.mkdir(mode=0o700)
        self.payload=b'original review payload\0\xff\x80\n';(self.inputs/'unit.bin').write_bytes(self.payload)
        self.outside=self.base/'outside';self.outside.mkdir();self.secret=b'EXTERNAL SAFETY WITNESS\0\xff'
        (self.outside/'payload').write_bytes(self.secret)
        self.descriptor=json.loads(FIXTURE.read_bytes());self.pointers=digest_pointers(self.descriptor)
        self.descriptor_path=self.base/'descriptor.json';self.descriptor_path.write_bytes(encoded(self.descriptor))
        self.bindings={'schema':1,'bindings':[{'pointer':p,'kind':'file','files':[{'name':'unit.bin','path':'unit.bin'}]} for p in self.pointers]}
        self.bindings_path=self.base/'bindings.json';self.bindings_path.write_bytes(encoded(self.bindings))
    def tearDown(self):
        self.assertEqual((self.outside/'payload').read_bytes(),self.secret,'external witness changed')
        self.tmp.cleanup()
    def create(self,name='snapshot',raw_bindings=None):
        self.bindings_path.write_bytes(raw_bindings if raw_bindings is not None else encoded(self.bindings))
        return capture.capture(self.descriptor_path,self.bindings_path,self.inputs,self.base/name,TOOL)
    def verify(self,result,name='snapshot'):
        return capture.verify(self.base/name,result['fingerprint'],TOOL)
    def report(self,name='snapshot'):
        return json.loads((self.base/name/'inputs.json').read_bytes())
    def rewrite(self,path,data):
        path.chmod(0o600);path.write_bytes(data);path.chmod(0o400)
    def no_completion(self,name='snapshot'):
        self.assertFalse((self.base/name).exists())
    def reject_capture(self,**kwargs):
        with self.assertRaises((capture.CaptureError,OSError)):self.create(**kwargs)
        self.no_completion(kwargs.get('name','snapshot'))
    def cli(self,*args):
        return subprocess.run([sys.executable,'-B',str(MODULE),*map(str,args)],capture_output=True,text=True,timeout=30)
    def capture_args(self):
        return ['capture','--descriptor',self.descriptor_path,'--bindings',self.bindings_path,'--input-root',self.inputs,'--output',self.base/'snapshot','--identity-tool',TOOL]

    def test_raw_and_empty_and_collection_digests_are_independently_computed(self):
        self.bindings['bindings'][0].update(kind='collection',files=[])
        self.bindings['bindings'][1].update(kind='collection',files=[{'name':'a-name','path':'unit.bin'},{'name':'z-name','path':'unit.bin'}])
        result=self.create();self.verify(result);report=self.report();desc=json.loads((self.base/'snapshot/descriptor.json').read_bytes())
        empty=sha(b'{"files":[],"schema":1}\n')
        collection=sha(encoded({'schema':1,'files':[{'name':'a-name','sha256':sha(self.payload),'bytes':len(self.payload)},{'name':'z-name','sha256':sha(self.payload),'bytes':len(self.payload)}]}))
        by_pointer={b['pointer']:b['sha256'] for b in report['bindings']}
        self.assertEqual(by_pointer[self.pointers[0]],empty);self.assertEqual(by_pointer[self.pointers[1]],collection)
        self.assertEqual(set(by_pointer.values()),{empty,collection,sha(self.payload)})
        for pointer,digest in by_pointer.items():set_pointer(self.descriptor,pointer,digest)
        self.assertEqual(desc,self.descriptor,'only digest fields may change')
        self.assertEqual(result['sourceBytes'],len(self.payload),'same source path captured once')
        self.assertEqual(report['objects'][empty],len(b'{"files":[],"schema":1}\n'))
        self.assertFalse(result['buildAttested']);self.assertFalse(result['completeGraphProven'])

    def test_stale_original_paths_do_not_retarget_snapshot_or_repeat_capture(self):
        original=capture.stream_file;reads=0
        def after(root,name,limit,sink=None):
            nonlocal reads
            info=original(root,name,limit,sink)
            if name=='unit.bin':reads+=1;(self.inputs/'unit.bin').write_bytes(b'later bytes')
            return info
        with patch.object(capture,'stream_file',after):result=self.create()
        self.assertEqual(reads,1);self.assertEqual(set(self.report()['objects']),{sha(self.payload)})
        (self.inputs/'unit.bin').unlink();self.verify(result)
        self.assertEqual((self.base/'snapshot/objects'/sha(self.payload)).read_bytes(),self.payload)
        (self.inputs/'unit.bin').write_bytes(b'later bytes');fresh=self.create('fresh');self.assertNotEqual(fresh['fingerprint'],result['fingerprint'])

    def test_source_swap_after_parent_open_keeps_pinned_internal_directory(self):
        branch=self.inputs/'branch';branch.mkdir();(branch/'payload').write_bytes(self.payload)
        self.bindings['bindings'][0]['files'][0]['path']='branch/payload'
        real_open=os.open;trigger=threading.Event();swapped=threading.Event();fail=[]
        def swap():
            if not trigger.wait(5):fail.append('gate never reached');return
            try:branch.rename(self.inputs/'retired');branch.symlink_to(self.outside,target_is_directory=True)
            except BaseException as e:fail.append(str(e))
            finally:swapped.set()
        worker=threading.Thread(target=swap);worker.start()
        def opening(path,flags,*args,**kwargs):
            fd=real_open(path,flags,*args,**kwargs)
            if path=='branch' and kwargs.get('dir_fd') is not None:
                trigger.set()
                if not swapped.wait(5):os.close(fd);raise RuntimeError('swap timed out')
            return fd
        try:
            with patch.object(capture.os,'open',opening):result=self.create()
        finally:trigger.set();worker.join(6)
        self.assertFalse(worker.is_alive());self.assertFalse(fail);self.verify(result)
        self.assertEqual(self.report()['bindings'][0]['files'][0]['sha256'],sha(self.payload))
        self.assertNotIn(sha(self.secret),self.report()['objects'])

    def test_leaf_swap_after_open_captures_original_fd_not_external_target(self):
        target=self.inputs/'payload';target.write_bytes(self.payload);self.bindings['bindings'][0]['files'][0]['path']='payload'
        real_open=os.open;swapped=False
        def opening(path,flags,*args,**kwargs):
            nonlocal swapped
            fd=real_open(path,flags,*args,**kwargs)
            if path=='payload' and kwargs.get('dir_fd') is not None and not swapped:
                swapped=True;target.rename(self.inputs/'retired');target.symlink_to(self.outside/'payload')
            return fd
        with patch.object(capture.os,'open',opening):result=self.create()
        self.assertTrue(swapped);self.verify(result);self.assertNotIn(sha(self.secret),self.report()['objects'])

    def test_symlink_before_leaf_open_and_intermediate_symlink_never_follow(self):
        real_open=os.open;target=self.inputs/'payload';target.write_bytes(self.payload);self.bindings['bindings'][0]['files'][0]['path']='payload';swapped=False
        def opening(path,flags,*args,**kwargs):
            nonlocal swapped
            if path=='payload' and kwargs.get('dir_fd') is not None and not swapped:
                swapped=True;target.rename(self.inputs/'retired');target.symlink_to(self.outside/'payload')
            return real_open(path,flags,*args,**kwargs)
        with patch.object(capture.os,'open',opening):self.reject_capture()
        (self.inputs/'link').symlink_to(self.outside,target_is_directory=True);self.bindings['bindings'][0]['files'][0]['path']='link/payload';self.reject_capture()
        self.assertTrue(swapped)

    def test_overwrite_during_read_and_restored_mtime_still_rejects(self):
        data=b'GATED INPUT'+b'x'*(3*capture.CHUNK);target=self.inputs/'unit.bin';target.write_bytes(data);before=target.stat();real_read=os.read;changed=False
        def reading(fd,size):
            nonlocal changed
            block=real_read(fd,size)
            if block.startswith(b'GATED INPUT') and not changed:
                changed=True
                with target.open('r+b') as stream:stream.seek(capture.CHUNK+7);stream.write(b'changed')
                os.utime(target,ns=(before.st_atime_ns,before.st_mtime_ns))
            return block
        with patch.object(capture.os,'read',reading):self.reject_capture()
        self.assertTrue(changed)

    def test_fifo_socket_directory_and_symlink_input_fail_without_blocking(self):
        os.mkfifo(self.inputs/'fifo');(self.inputs/'dir').mkdir();(self.inputs/'symlink').symlink_to(self.outside/'payload')
        sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.bind(str(self.inputs/'socket'))
        try:
            for path in ['fifo','socket','dir','symlink']:
                with self.subTest(path=path):
                    self.bindings['bindings'][0]['files'][0]['path']=path;self.bindings_path.write_bytes(encoded(self.bindings))
                    result=self.cli(*self.capture_args());self.assertEqual(result.returncode,1);self.no_completion()
        finally:sock.close()

    def test_output_existing_file_directory_and_symlink_preserve_external_content(self):
        target=self.base/'snapshot'
        for kind in ['file','directory','symlink']:
            with self.subTest(kind=kind):
                if kind=='file':target.write_bytes(b'keep')
                elif kind=='directory':target.mkdir();(target/'keep').write_bytes(b'keep')
                else:target.symlink_to(self.outside,target_is_directory=True)
                with self.assertRaises(FileExistsError):self.create()
                if kind=='directory':self.assertEqual((target/'keep').read_bytes(),b'keep');(target/'keep').unlink();target.rmdir()
                else:
                    if kind=='file':self.assertEqual(target.read_bytes(),b'keep')
                    target.unlink()

    def test_actual_manifest_descriptor_and_file_size_guard_boundaries(self):
        for exact,field in [(capture.MAX_MANIFEST,'bindings'),(capture.MAX_DESCRIPTOR,'descriptor')]:
            raw=encoded(self.bindings if field=='bindings' else self.descriptor);padded=raw+b' '*(exact-len(raw))
            if field=='bindings':self.create('exact-bindings',raw_bindings=padded)
            else:self.descriptor_path.write_bytes(padded);self.create('exact-descriptor')
            if field=='bindings':self.reject_capture(raw_bindings=padded+b' ')
            else:self.descriptor_path.write_bytes(padded+b' ');self.reject_capture()
            self.descriptor_path.write_bytes(encoded(self.descriptor))
        # Actual 1GiB+1 stat boundary; sparse file, not a 1GiB read/heap test.
        with (self.inputs/'huge').open('wb') as stream:stream.truncate(capture.MAX_FILE_BYTES+1)
        self.bindings['bindings'][0]['files'][0]['path']='huge';self.reject_capture()

    def test_4096_entries_exact_and_plus_one_and_generated_manifest_bound(self):
        for b in self.bindings['bindings']:b.update(kind='collection',files=[])
        self.bindings['bindings'][0]['files']=[{'name':f'n-{i:04}','path':'unit.bin'} for i in range(4096)]
        result=self.create('count-exact');self.verify(result,'count-exact');self.assertEqual(result['sourceBytes'],len(self.payload))
        self.bindings['bindings'][0]['files'].append({'name':'n-4096','path':'unit.bin'});self.reject_capture()
        self.bindings['bindings'][0]['files']=[{'name':f'{i:04}-'+('a'*200),'path':'unit.bin'} for i in range(4096)]
        self.assertLess(len(encoded(self.bindings)),capture.MAX_MANIFEST);self.reject_capture()

    def test_reduced_byte_caps_exact_plus_one_and_empty_file_real_digest(self):
        size=len(self.payload)
        with patch.object(capture,'MAX_FILE_BYTES',size),patch.object(capture,'MAX_TOTAL_BYTES',size):self.create('exact-bytes')
        with patch.object(capture,'MAX_FILE_BYTES',size-1):self.reject_capture()
        (self.inputs/'other').write_bytes(b'Z');self.bindings['bindings'][0]['files'][0]['path']='other'
        with patch.object(capture,'MAX_TOTAL_BYTES',size+1):self.create('exact-total')
        with patch.object(capture,'MAX_TOTAL_BYTES',size):self.reject_capture()
        (self.inputs/'other').write_bytes(b'');(self.inputs/'unit.bin').write_bytes(b'')
        with patch.object(capture,'MAX_FILE_BYTES',0),patch.object(capture,'MAX_TOTAL_BYTES',0):result=self.create('empty')
        self.verify(result,'empty');self.assertEqual(set(self.report('empty')['objects']),{sha(b'')});self.assertEqual(result['sourceBytes'],0)

    def test_path_and_closed_shape_boundaries(self):
        invalid=['','/absolute','..','x/../y','./x','x//y','x/','a\\b','\0','\n','é','x'*256,'x/'+'a'*1024]
        original=copy.deepcopy(self.bindings)
        for path in invalid:
            with self.subTest(path=repr(path)):
                self.bindings=copy.deepcopy(original);self.bindings['bindings'][0]['files'][0]['path']=path;self.reject_capture()
        for value in [None,True,1,[],{},'unknown']:
            with self.subTest(kind=value):
                self.bindings=copy.deepcopy(original);self.bindings['bindings'][0]['kind']=value;self.reject_capture()
        self.bindings=copy.deepcopy(original);name='/'.join(['a'*255,'b'*255,'c'*255,'d'*254,'z']);self.assertEqual(len(name),1024);self.bindings['bindings'][0]['files'][0]['name']=name;self.create('exact-name')
        self.bindings['bindings'][0]['files'][0]['name']+='z';self.reject_capture()

    def test_report_corruption_matrix_and_external_object_paths_fail_closed(self):
        self.bindings['bindings'][0].update(kind='collection',files=[{'name':'unit','path':'unit.bin'}]);result=self.create();original=self.report();report_path=self.base/'snapshot/inputs.json'
        variants=[]
        for field,value in [('schema',True),('build_attested',True),('complete_graph_proven',True),('fingerprint','0'*64),('descriptor_sha256','0'*64),('bindings',None),('objects',[])]:
            v=copy.deepcopy(original);v[field]=value;variants.append(v)
        for size in [True,-1,1.5,capture.MAX_FILE_BYTES+1]:v=copy.deepcopy(original);k=next(iter(v['objects']));v['objects'][k]=size;variants.append(v)
        for key in ['../payload','/'+'a'*64,'A'*64,'a'*63]:v=copy.deepcopy(original);k=next(iter(v['objects']));v['objects'][key]=v['objects'].pop(k);variants.append(v)
        v=copy.deepcopy(original);v['bindings'].pop();variants.append(v)
        v=copy.deepcopy(original);v['bindings'][0]['files'][0]['name']='changed';variants.append(v)
        v=copy.deepcopy(original);v['bindings'][0]['files'][0]['bytes']=True;variants.append(v)
        v=copy.deepcopy(original);v['bindings'][0]['pointer']='/execution/fuel';variants.append(v)
        v=copy.deepcopy(original);v['bindings'][0]['kind']='passive';variants.append(v)
        for i,v in enumerate(variants):
            with self.subTest(case=i):self.rewrite(report_path,encoded(v));self.assertRaises((capture.CaptureError,OSError),self.verify,result)
        self.rewrite(report_path,encoded(original));self.verify(result)
        for name in ['descriptor.json','inputs.json']:
            path=self.base/'snapshot'/name;saved=path.read_bytes();path.unlink();path.symlink_to(self.outside/'payload');self.assertRaises((capture.CaptureError,OSError),self.verify,result);path.unlink();path.write_bytes(saved)
        obj=self.base/'snapshot/objects'/sha(self.payload);obj.unlink();obj.symlink_to(self.outside/'payload');self.assertRaises(OSError,self.verify,result)

    def test_expected_fingerprint_rejects_consistently_rehashed_policy_change(self):
        result=self.create();report=self.report();path=self.base/'snapshot/descriptor.json';desc=json.loads(path.read_bytes());desc['execution']['fuel']=999_999;data=encoded(desc);self.rewrite(path,data)
        report['descriptor_sha256']=sha(data);self.rewrite(self.base/'snapshot/inputs.json',encoded(report))
        self.assertRaises(capture.CaptureError,self.verify,result)
        for expected in ['',None,'A'*64,'0'*64]:self.assertRaises(capture.CaptureError,capture.verify,self.base/'snapshot',expected,TOOL)

    def test_completion_last_interruption_is_unverifiable_and_sync_failure_cleans(self):
        self.bindings_path.write_bytes(encoded(self.bindings))
        code="import importlib.util,os,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('c',sys.argv[1]);c=importlib.util.module_from_spec(s);s.loader.exec_module(c);w=c.write_new\ndef f(p,d):\n if Path(p).name=='inputs.json':os._exit(72)\n w(p,d)\nc.write_new=f;c.capture(*sys.argv[2:])"
        child=subprocess.run([sys.executable,'-B','-c',code,str(MODULE),str(self.descriptor_path),str(self.bindings_path),str(self.inputs),str(self.base/'partial'),str(TOOL)],capture_output=True,timeout=30)
        self.assertEqual(child.returncode,72);self.assertTrue((self.base/'partial/descriptor.json').is_file());self.assertFalse((self.base/'partial/inputs.json').exists())
        self.assertRaises(FileNotFoundError,capture.verify,self.base/'partial','0'*64,TOOL)
        with patch.object(capture,'sync_directory',side_effect=OSError('original injected sync failure')):self.reject_capture()

    def test_real_validator_rejects_non_digest_policy_or_unsupported_descriptor(self):
        for mutate in [lambda x:x['execution'].update(fuel=True),lambda x:x['execution'].update(fuel=1.5),lambda x:x['execution'].update(protocol=99),lambda x:x['engine'].update(profile='unknown'),lambda x:x.update(undeclared={})]:
            self.descriptor=json.loads(FIXTURE.read_bytes());mutate(self.descriptor);self.descriptor_path.write_bytes(encoded(self.descriptor));self.reject_capture()
        for raw in [b'{"schema":1,"schema":1,"bindings":[]}',b'{"schema":1,"\\u0073chema":1,"bindings":[]}',b'\xff',b'{"schema":NaN,"bindings":[]}',b'['*18+b'0'+b']'*18]:self.reject_capture(raw_bindings=raw)

    def test_oversized_integer_is_rejected_and_characterizes_cli_diagnostic(self):
        # Python's configured integer conversion limit is a different parser error
        # from JSONDecodeError; record whether the public CLI handles it cleanly.
        raw=b'{"schema":'+b'9'*5000+b',"bindings":[]}'
        self.bindings_path.write_bytes(raw);result=self.cli(*self.capture_args());self.assertNotEqual(result.returncode,0);self.no_completion()
        print(json.dumps({'case':'5000-digit-invalid-schema','exit_code':result.returncode,'traceback':'Traceback' in result.stderr,'stderr_bytes':len(result.stderr)},sort_keys=True))

if __name__=='__main__':unittest.main(verbosity=2)
