"""Successor controls: 36 scenarios with an explicit changed fixture contract."""
import contextlib, hashlib, importlib.util, json, sys, types, unittest
from unittest import mock
import adopt_fixture as selected

KIND = 'cache-successor-runner-controls-v2'
CHANGED_METHODS = {
 'test_mocked_primary_and_stop_exceptions_retain_terminal_receipt': 'primary',
 'test_mocked_cleanup_only_exception_is_reported_and_held': 'cleanup',
 'test_mocked_cpu_custody_hold_withholds_delta': 'accounting',
}
class SyntheticUnknown(BaseException): pass

class MemoryPath:
    """Fixture storage only; no file descriptor, real path or PID is acquired."""
    def __init__(self, state, name='synthetic'): self.state,self.name=state,name
    def __truediv__(self, name): return MemoryPath(self.state,self.name+'/'+str(name))
    def __str__(self): return self.name
    @property
    def suffix(self): return '.'+self.name.rsplit('.',1)[-1]
    @property
    def parent(self): return MemoryPath(self.state,self.name.rsplit('/',1)[0])
    def touch(self, operation):
        if self.state['frozen']: raise AssertionError('Scratch inspection after UNKNOWN: '+operation)
        self.state['events'].append(operation)
    def mkdir(self,*a,**k): self.touch('mkdir')
    def exists(self): self.touch('exists'); return self.name in self.state['files']
    def write_bytes(self, value): self.touch('write'); self.state['files'][self.name]=value
    def read_bytes(self): self.touch('read'); return self.state['files'][self.name]
    def read_text(self): return self.read_bytes().decode()
    def write_text(self, value): self.write_bytes(value.encode())
    def open(self,*a,**k):
        self.write_bytes(b''); return MemoryStream(self.state,self.name)
class MemoryStream:
    def __init__(self,state,name): self.state,self.name=state,name
    def fileno(self): return 987654
    def write(self,value): self.state['files'][self.name]+=value
    def close(self): self.state['events'].append('close-'+self.name)

def attach_fixture(module):
    """Adapt fixtures, never production custody transitions or positive tests."""
    r=module.r; cls=module.RunnerControls; inert=r.InertPopen
    module.successor_fixture_records=[]
    class FixtureProcess(inert):
        def __init__(self,*args,**kwargs): self._fixture_state['events'].append('constructor')
    def mocked_command(case):
        state={'frozen':False,'files':{},'events':[],'metadata':None,'authority':None}
        # Each retained synthetic authority owns permanent isolated globals.
        namespace=dict(r.__dict__)
        for name,fn in r.__dict__.items():
            if isinstance(fn,types.FunctionType) and fn.__globals__ is r.__dict__:
                namespace[name]=types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
        methods={name:types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
                 for name,fn in vars(r.Commands).items() if isinstance(fn,types.FunctionType)}
        command_type=type('FixtureCommands',(r.Commands,),methods)
        c=command_type(MemoryPath(state),{'commands':[]},module.time.monotonic()+20)
        c.child_environment=lambda env:{}
        process=object.__new__(FixtureProcess)
        process._fixture_state=state
        process.pid=987654;process.stdout=MemoryStream(state,'stdout');process.stderr=MemoryStream(state,'stderr')
        process.returncode=0;process.poll=mock.Mock(return_value=0);process.wait=mock.Mock(return_value=0)
        keys={}
        def register(pipe,event,data):keys[pipe]=types.SimpleNamespace(fileobj=pipe,data=data)
        selector=types.SimpleNamespace(register=register,get_map=lambda:keys,
            select=mock.Mock(side_effect=lambda seconds:[(key,None)for key in list(keys.values())]),
            unregister=lambda pipe:keys.pop(pipe),close=mock.Mock())
        def forbidden(*a,**k):
            state['events'].append('blocked-kernel-operation')
            raise AssertionError('Unintercepted synthetic kernel operation')
        for name in ['_internal_poll','_wait','send_signal','terminate','kill','communicate']:
            setattr(process,name,forbidden)
        real_run=c.run
        def run(*a,**kw):
            def admission(argv,cwd,env):
                if argv!=['synthetic-command'] or not isinstance(r.subprocess.Popen,mock.Mock):
                    raise AssertionError('Exact synthetic executable fixture required')
            def save(path,value):path.write_text(json.dumps(value))
            def freeze(authority,metadata,path):
                state.update(frozen=True,metadata=metadata,authority=authority)
                raise SyntheticUnknown()
            # Capture only already mocked operations. No fake PID can reach os.
            fakeos=types.SimpleNamespace(path=r.os.path,environ=r.os.environ,
                read=r.os.read if isinstance(r.os.read,mock.Mock) else forbidden,
                killpg=r.os.killpg if isinstance(r.os.killpg,mock.Mock) else forbidden,
                kill=forbidden,waitpid=forbidden,waitid=forbidden,close=forbidden,_exit=forbidden)
            constructor=r.subprocess.Popen
            class RetainedPopen(inert):
                def __new__(kind):
                    if not isinstance(constructor,mock.Mock):
                        raise AssertionError('Synthetic constructor injection was not armed')
                    return constructor()
            # Never restore a real kernel, constructor, selector or exit API into
            # the globals of a retained synthetic authority, even after teardown.
            namespace.update(time=r.time,CHILD_SECONDS=r.CHILD_SECONDS,
                InertPopen=RetainedPopen,admit_executable=admission,
                os=fakeos,subprocess=types.SimpleNamespace(Popen=constructor,PIPE=r.subprocess.PIPE),
                selectors=types.SimpleNamespace(DefaultSelector=r.selectors.DefaultSelector,EVENT_READ=r.selectors.EVENT_READ),
                resource=types.SimpleNamespace(getrusage=r.resource.getrusage,RUSAGE_CHILDREN=r.resource.RUSAGE_CHILDREN),
                save=save,sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(),freeze_unknown=freeze)
            return real_run(*a,**kw)
        c.run=run;c.synthetic_state=state
        module.successor_fixture_records.append(state)
        return c,process,selector
    cls.mocked_command=mocked_command
    def unknown(case,scenario):
        c,process,selector=case.mocked_command();state=c.synthetic_state
        primary=OSError(5,'injected active read failure')
        cleanup=OSError(5,'synthetic child reap failure' if scenario=='accounting' else 'injected final stop failure')
        before=types.SimpleNamespace(ru_utime=1.0,ru_stime=2.0,ru_minflt=3,ru_majflt=4)
        real_stop=c.stop
        if scenario=='primary':selector.select.side_effect=primary;process.wait.side_effect=OSError(1,'injected wait failure')
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(r.subprocess,'Popen',return_value=process))
            stack.enter_context(mock.patch.object(r.selectors,'DefaultSelector',return_value=selector))
            killpg=stack.enter_context(mock.patch.object(r.os,'killpg',side_effect=ProcessLookupError))
            stack.enter_context(mock.patch.object(r.os,'read',return_value=b''))
            snapshots=stack.enter_context(mock.patch.object(r.resource,'getrusage',return_value=before))
            if scenario!='primary':stack.enter_context(mock.patch.object(c,'stop',side_effect=cleanup))
            with case.assertRaises(SyntheticUnknown):c.run('mock-'+scenario,['synthetic-command'],case.base)
            row=state['metadata']['row']
            case.assertTrue(c.unknown_custody);case.assertTrue(row['custody_hold']);case.assertIs(c.active,process)
            case.assertFalse(row['owned_group_gone']);case.assertFalse(row.get('stop_complete',False))
            case.assertTrue(state['metadata']['noFurtherOperations'])
            case.assertNotIn('child_resource_usage',row);case.assertNotIn('finished_utc',row)
            case.assertEqual(snapshots.call_count,1)
            if scenario=='primary':
                case.assertEqual(row['errors'],[{'phase':'active',**r.exception_details(primary)}])
                case.assertEqual(process.wait.call_count,0);case.assertEqual(killpg.call_count,0)
                case.assertEqual(selector.close.call_count,0)
            else:
                case.assertTrue(row['child_returned']);case.assertEqual(row['errors'][0]['phase'],'stop-owned-group')
                case.assertEqual(row['errors'][0]['message'],str(cleanup))
            counts=(len(state['events']),process.poll.call_count,process.wait.call_count,killpg.call_count,selector.close.call_count,snapshots.call_count)
            with process:pass
            process.__del__()
            for operation in [lambda:c.run('again',['synthetic-command'],case.base),lambda:c.observe(process.poll),lambda:c.gone(process.pid)]:
                try:
                    operation()
                except (RuntimeError,OSError):pass
            # Call the unchanged stop method while every interceptor remains armed.
            with case.assertRaises(RuntimeError):real_stop(process,row)
            case.assertEqual(counts,(len(state['events']),process.poll.call_count,process.wait.call_count,killpg.call_count,selector.close.call_count,snapshots.call_count))
        state['checkedSticky']=True;state['scenario']=scenario
    def primary(case):return unknown(case,'primary')
    def cleanup(case):return unknown(case,'cleanup')
    def accounting(case):return unknown(case,'accounting')
    for name,implementation in zip(CHANGED_METHODS,[primary,cleanup,accounting]):
        setattr(cls,name,implementation)
    return module

def load_original():
    # R3806's reviewed loader identity and exceptional restoration are retained.
    sys.path.insert(0,str(selected.PREVIOUS))
    spec=importlib.util.spec_from_file_location('cache_r8_original_controls',selected.PREVIOUS/'test_original.py')
    old=importlib.util.module_from_spec(spec)
    selected_module=sys.modules['adopt_fixture']
    sys.modules['adopt_fixture']=selected.previous()
    try:spec.loader.exec_module(old)
    finally:sys.modules['adopt_fixture']=selected_module
    old.HERE=selected.HERE;old.install=selected.install;old.verify=selected.verify
    return old

def main():
    selected.verify();old=load_original()
    old.previous()
    import local_support
    original_save=local_support.save
    original_loader=unittest.defaultTestLoader.loadTestsFromModule
    def load(module,*a,**kw):return original_loader(attach_fixture(module),*a,**kw)
    def save(path,value):
        if path.name=='result.json':
            value=dict(value);value.pop('complete_original_suite',None)
            value.update(kind=KIND,complete_successor_suite=value['tests']==36,
                unchanged_original36_pass=False,changed_methods=CHANGED_METHODS,
                scope='Successor controls with changed method map; cooperative positive processes remain real. No compiler or native qualification.')
            path=path.with_name('successor-controls-result.json')
        return original_save(path,value)
    try:
        unittest.defaultTestLoader.loadTestsFromModule=load;local_support.save=save
        return old.main()
    finally:
        unittest.defaultTestLoader.loadTestsFromModule=original_loader;local_support.save=original_save
if __name__=='__main__':sys.exit(main())
