"""Focused behavioral controls added to the unchanged 64 retained methods."""
class RefusalCleanup(unittest.TestCase):
    def case(self,label,mutate,fault=None):
        allocated=[]; fixture_closed=[]; closes=[]; invalid_ops=[]; io_calls=[]; stats=[]
        contexts=[]; actually_closed=[]; live=[]; reviewer_closed=[]; target=[]
        class Changed(subprocess.Popen):
            def _get_handles(self,*args):
                h=list(super()._get_handles(*args))
                allocated.extend([h[0],*h[2:]])
                contexts.append(contextvars.copy_context())
                mutate(self,h,fixture_closed)
                return h
        def valid(operation,fd):
            if type(fd) is not int or fd<0:
                invalid_ops.append(operation)
                raise AssertionError('Invalid descriptor operation: '+operation)
        def close(fd):
            valid('close',fd);closes.append(fd)
            if not target:target.append(fd)
            if fault=='before-close' and fd==target[0]:raise OSError(errno.EIO,'injected close failure')
            os.close(fd);actually_closed.append(fd)
            if fault=='after-close' and fd==target[0]:raise OSError(errno.EIO,'injected close failure')
        def stat(fd):
            valid('fstat',fd);stats.append(fd)
            if fault=='confirmation' and fd in actually_closed and fd==target[0]:
                raise OSError(errno.EIO,'injected confirmation failure')
            return os.fstat(fd)
        def probe(operation,*args):
            valid(operation,args[0]);io_calls.append(operation)
            return getattr(os,operation)(*args)
        proxy=types.SimpleNamespace(Popen=Changed,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,__file__=subprocess.__file__)
        os_proxy=types.SimpleNamespace(**vars(os))
        os_proxy.close=close;os_proxy.fstat=stat
        os_proxy.read=lambda *a:probe('read',*a)
        os_proxy.write=lambda *a:probe('write',*a)
        captured=io.StringIO();code=None;escaped=None;data=None
        try:
            with mock.patch.object(preflight,'subprocess',proxy),mock.patch.object(preflight,'os',os_proxy),contextlib.redirect_stdout(captured):
                try:code=preflight.main()
                except BaseException as error:escaped=repr(error)
            if captured.getvalue():data=json.loads(captured.getvalue())
            for fd in allocated:
                try:os.fstat(fd);live.append(fd)
                except OSError as error:
                    if error.errno!=errno.EBADF:raise
        finally:
            for fd in allocated:
                try:os.fstat(fd)
                except OSError as error:
                    if error.errno!=errno.EBADF:raise
                else:os.close(fd);reviewer_closed.append(fd)
        receipt={'label':label,'injected':True,'actual_python_invalid_layout_claimed':False,
                 'returncode':code,'escaped':escaped,'report':data,'allocated':allocated,
                 'fixture_closed':fixture_closed,'close_calls':closes,'invalid_operations':invalid_ops,
                 'io_calls':io_calls,'fstats':stats,'live_after_candidate':live,
                 'reviewer_closed':reviewer_closed,'cleanup_fault':fault,
                 'timer_disarmed':signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),
                 'capabilities_revoked':all(not c.get(guard._stdin_scope).active for c in contexts)}
        (EVIDENCE/('focused-'+label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        self.assertIsNone(escaped)
        self.assertEqual(code,1)
        self.assertFalse(data['passed'])
        self.assertTrue(data['timer_disarmed'] and receipt['timer_disarmed'])
        self.assertTrue(receipt['capabilities_revoked'])
        self.assertIsNone(guard._stdin_scope.get())
        self.assertEqual(invalid_ops,[])
        self.assertEqual(len(closes),len(set(closes)))
        self.assertEqual(set(closes),set(allocated)-set(fixture_closed))
        raw=json.loads(Path(data['descriptor_preflight']).read_bytes())
        self.assertEqual(raw,{k:v for k,v in data.items() if k!='descriptor_preflight'})
        for fd in allocated:
            with self.assertRaises(OSError) as caught:os.fstat(fd)
            self.assertEqual(caught.exception.errno,errno.EBADF)
        return receipt

    def replace_endpoint(self,value):
        def mutate(obj,h,closed):
            os.close(h[5]);closed.append(h[5]);h[5]=value
        return mutate

    def test_malformed_unhashable_and_bool_endpoints(self):
        class IntSubclass(int):
            def __hash__(self):raise AssertionError('invalid value hashed')
        for label,value in [('none',None),('string','invalid-descriptor'),('list',[]),('dict',{}),('set',set()),('true',True),('false',False),('int-subclass',IntSubclass(0))]:
            with self.subTest(label=label):
                r=self.case('endpoint-'+label,self.replace_endpoint(value))
                self.assertIn('Five distinct nonnegative descriptors required',r['report']['error'])
                self.assertEqual(r['live_after_candidate'],[])
                self.assertEqual(r['io_calls'],[])
                self.assertEqual(len(r['report']['closed_descriptors']),4)
                self.assertNotIn('cleanup_errors',r['report'])

    def test_malformed_cached_devnull_never_operated_on(self):
        for label,value in [('none',None),('string','invalid-cache'),('list',[]),('dict',{}),('bool',True)]:
            with self.subTest(label=label):
                def mutate(obj,h,closed):obj._devnull=value
                r=self.case('cached-'+label,mutate)
                self.assertIn('Stdin must be the cached DEVNULL descriptor',r['report']['error'])
                self.assertEqual(r['io_calls'],[])
                self.assertEqual(r['live_after_candidate'],[])
                self.assertEqual(len(r['report']['closed_descriptors']),5)

    def test_cached_devnull_closed_when_returned_stdin_invalid(self):
        def mutate(obj,h,closed):h[0]=[]
        r=self.case('cached-only-live-stdin',mutate)
        self.assertEqual(len(r['report']['closed_descriptors']),5)
        self.assertEqual(r['io_calls'],[])
        self.assertEqual(r['live_after_candidate'],[])
        self.assertIn('Five distinct nonnegative descriptors required',r['report']['error'])

    def test_cleanup_errors_keep_primary_refusal_and_finish_inventory(self):
        for fault in ['before-close','after-close','confirmation']:
            with self.subTest(fault=fault):
                r=self.case('refusal-'+fault,self.replace_endpoint([]),fault)
                self.assertIn('Five distinct nonnegative descriptors required',r['report']['error'])
                self.assertEqual(len(r['report']['cleanup_errors']),1)
                self.assertIn('Descriptor close not confirmed' if fault=='confirmation' else 'injected',r['report']['cleanup_errors'][0])
                self.assertEqual(len(r['close_calls']),4)
                self.assertEqual(len(r['report']['closed_descriptors']),3)
                self.assertEqual(r['io_calls'],[])
                self.assertEqual(r['live_after_candidate'],r['close_calls'][:1] if fault=='before-close' else [])
                self.assertEqual(r['reviewer_closed'],r['live_after_candidate'])

    def test_cleanup_error_turns_successful_setup_into_failed_receipt(self):
        r=self.case('positive-setup-cleanup-error',lambda *a:None,'after-close')
        self.assertNotIn('error',r['report'])
        self.assertEqual(len(r['report']['cleanup_errors']),1)
        self.assertEqual(len(r['report']['validated_descriptors']),5)
        self.assertTrue(r['io_calls'])
        self.assertEqual(len(r['close_calls']),5)
        self.assertEqual(r['live_after_candidate'],[])

    def test_fake_zero_and_alias_inventory_is_deduplicated(self):
        calls=[];closed=set()
        class Fake:
            def _get_handles(self,*args):
                self._devnull=3
                return [0,-1,0,1,2,[]]
        def close(fd):
            calls.append(fd)
            if type(fd) is not int or fd<0:raise AssertionError('invalid FD')
            if fd in closed:raise AssertionError('duplicate close')
            closed.add(fd)
        def stat(fd):
            if fd in closed:raise OSError(errno.EBADF,'closed fake descriptor')
            raise AssertionError('refusal must precede liveness probes')
        def io_forbidden(*args):raise AssertionError('refusal must precede I/O')
        os_proxy=types.SimpleNamespace(**vars(os));os_proxy.close=close;os_proxy.fstat=stat
        os_proxy.read=io_forbidden;os_proxy.write=io_forbidden
        proxy=types.SimpleNamespace(Popen=Fake,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,__file__=subprocess.__file__)
        captured=io.StringIO()
        with mock.patch.object(preflight,'subprocess',proxy),mock.patch.object(preflight,'os',os_proxy),contextlib.redirect_stdout(captured):code=preflight.main()
        data=json.loads(captured.getvalue())
        (EVIDENCE/'focused-fake-zero.json').write_text(json.dumps({'fake_fds_only':True,'returncode':code,'close_calls':calls,'report':data},indent=2)+'\n')
        self.assertEqual(code,1)
        self.assertEqual(calls,[0,1,2,3])
        self.assertEqual(data['closed_descriptors'],calls)
        self.assertNotIn('cleanup_errors',data)
        self.assertIn('Five distinct nonnegative descriptors required',data['error'])
        self.assertTrue(data['timer_disarmed'])
        self.assertIsNone(guard._stdin_scope.get())
