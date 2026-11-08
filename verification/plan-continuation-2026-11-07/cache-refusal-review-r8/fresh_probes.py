"""Independent probes: fake descriptor matrix, cleanup faults, actual child-free setup."""
class FreshR8(unittest.TestCase):
    def fake_case(self,label,handles,cached,fault=None):
        expected=sorted({fd for fd in handles+[cached] if type(fd) is int and fd>=0})
        calls=[];closed=set();invalid=[];io_calls=[]
        class Fake:
            def _get_handles(self,*args):
                self._devnull=cached
                return tuple(handles)
        def valid(op,fd):
            if type(fd) is not int or fd<0:
                invalid.append(op);raise AssertionError('invalid FD operation')
        def close(fd):
            valid('close',fd);calls.append(fd)
            if fd in closed:raise AssertionError('duplicate close')
            if fd==expected[0] and fault=='before':raise KeyboardInterrupt('injected before close')
            if fd==expected[0] and fault=='no-close':return
            closed.add(fd)
            if fd==expected[0] and fault=='after':raise SystemExit('injected after close')
        def stat(fd):
            valid('fstat',fd)
            if fd in closed:
                if fd==expected[0] and fault=='confirmation':raise OSError(errno.EIO,'injected confirmation')
                raise OSError(errno.EBADF,'closed fake FD')
            if fault=='no-close' and fd==expected[0]:return object()
            raise AssertionError('refused layout reached pre-I/O stat')
        def no_io(*args):io_calls.append(args[0]);raise AssertionError('refused layout reached I/O')
        os_proxy=types.SimpleNamespace(**vars(os));os_proxy.close=close;os_proxy.fstat=stat
        os_proxy.read=no_io;os_proxy.write=no_io
        sp=types.SimpleNamespace(Popen=Fake,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,__file__=subprocess.__file__)
        output=io.StringIO()
        with mock.patch.object(preflight,'os',os_proxy),mock.patch.object(preflight,'subprocess',sp),contextlib.redirect_stdout(output):code=preflight.main()
        data=json.loads(output.getvalue());raw=json.loads(Path(data['descriptor_preflight']).read_bytes())
        record={'case':label,'fake_fds_only':True,'actual_python_malformed_layout_claimed':False,'returncode':code,'report':data,'expected_close_calls':expected,'close_calls':calls,'invalid_operations':invalid,'io_calls':io_calls,'fault':fault}
        (EVIDENCE/('fresh-'+label+'.json')).write_text(json.dumps(record,indent=2)+'\n')
        self.assertEqual(code,1);self.assertFalse(data['passed']);self.assertTrue(data['timer_disarmed'])
        self.assertIsNone(guard._stdin_scope.get());self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        self.assertEqual(raw,{k:v for k,v in data.items() if k!='descriptor_preflight'})
        self.assertEqual(calls,expected);self.assertEqual(invalid,[]);self.assertEqual(io_calls,[])
        self.assertIn('error',data)
        if fault:
            self.assertIn('Five distinct nonnegative descriptors required',data['error'])
            self.assertEqual(len(data['cleanup_errors']),1)
            self.assertEqual(data['closed_descriptors'],expected[1:])
        else:
            self.assertNotIn('cleanup_errors',data);self.assertEqual(data['closed_descriptors'],expected)
        return data

    def test_every_endpoint_and_cache_rejects_bad_cleanup_values(self):
        class UnusableInt(int):
            def __hash__(self):raise AssertionError('int subclass hashed')
            def __lt__(self,other):raise AssertionError('int subclass sorted')
            def __ge__(self,other):raise AssertionError('int subclass compared')
        values=[('none',None),('string','bad'),('list',[]),('dict',{}),('set',set()),('true',True),('false',False),('int-subclass',UnusableInt(777))]
        for label,value in values:
            for slot in [0,2,3,4,5]:
                with self.subTest(value=label,slot=slot):
                    handles=[10,-1,11,12,13,14];handles[slot]=value
                    data=self.fake_case('endpoint-'+str(slot)+'-'+label,handles,10)
                    self.assertIn('Five distinct nonnegative descriptors required',data['error'])
            with self.subTest(cache=label):
                data=self.fake_case('cache-'+label,[10,-1,11,12,13,14],value)
                self.assertIn('Stdin must be the cached DEVNULL descriptor',data['error'])

    def test_zero_alias_and_cached_only_inventory(self):
        self.fake_case('zero-alias-cache-only',[0,-1,0,1,2,[]],3)

    def test_baseexception_and_confirmation_failures_preserve_refusal(self):
        for fault in ['before','after','confirmation','no-close']:
            with self.subTest(fault=fault):self.fake_case('cleanup-'+fault,[10,-1,11,12,13,None],10,fault)

    def test_actual_five_live_before_io_and_revoked_after_exit(self):
        allocated=[];closed=[];stats=[];io_calls=[];contexts=[];live=[];reviewer_closed=[]
        class Observed(subprocess.Popen):
            def _get_handles(self,*args):
                h=super()._get_handles(*args);allocated.extend([h[0],*h[2:]])
                contexts.append(contextvars.copy_context());return h
        def stat(fd):stats.append(fd);return os.fstat(fd)
        def close(fd):closed.append(fd);return os.close(fd)
        def observe_io(operation,*args):
            io_calls.append({'operation':operation,'prior_stats':list(stats)})
            return getattr(os,operation)(*args)
        os_proxy=types.SimpleNamespace(**vars(os));os_proxy.fstat=stat;os_proxy.close=close
        os_proxy.read=lambda *a:observe_io('read',*a);os_proxy.write=lambda *a:observe_io('write',*a)
        sp=types.SimpleNamespace(Popen=Observed,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,__file__=subprocess.__file__)
        captured=io.StringIO();code=None;data=None
        try:
            with mock.patch.object(preflight,'os',os_proxy),mock.patch.object(preflight,'subprocess',sp),contextlib.redirect_stdout(captured):code=preflight.main()
            data=json.loads(captured.getvalue())
            for fd in allocated:
                try:os.fstat(fd);live.append(fd)
                except OSError as error:self.assertEqual(error.errno,errno.EBADF)
        finally:
            for fd in allocated:
                try:os.fstat(fd)
                except OSError as error:
                    if error.errno!=errno.EBADF:raise
                else:os.close(fd);reviewer_closed.append(fd)
        revoked=all(not ctx.get(guard._stdin_scope).active for ctx in contexts)
        (EVIDENCE/'fresh-actual-five-live.json').write_text(json.dumps({'returncode':code,'report':data,'actual_stdlib_get_handles':True,'instrumentation':'subclass delegates unchanged inherited method; module-local os observer','allocated':allocated,'close_calls':closed,'io_calls':io_calls,'live_after_candidate':live,'reviewer_closed':reviewer_closed,'copied_capabilities_revoked':revoked,'real_inner_children':0},indent=2)+'\n')
        self.assertEqual(code,0);self.assertTrue(data['passed']);self.assertEqual(len(set(allocated)),5)
        self.assertEqual(io_calls[0]['prior_stats'],allocated);self.assertEqual(closed,sorted(allocated))
        self.assertEqual(live,[]);self.assertEqual(reviewer_closed,[]);self.assertTrue(revoked)
        self.assertTrue(data['stdin_matches_cached_devnull']);self.assertIsNone(guard._stdin_scope.get())
        for ctx in contexts:Independent().denied(ctx)

fresh_suite=unittest.defaultTestLoader.loadTestsFromTestCase(FreshR8)
fresh_result=unittest.TextTestRunner(verbosity=2).run(fresh_suite)
(EVIDENCE/'fresh-result.json').write_text(json.dumps({'tests':fresh_result.testsRun,'successful':fresh_result.wasSuccessful(),'failures':[(str(t),e)for t,e in fresh_result.failures],'errors':[(str(t),e)for t,e in fresh_result.errors],'cases':54,'real_inner_children':0,'actual_original36_run':False},indent=2)+'\n')
