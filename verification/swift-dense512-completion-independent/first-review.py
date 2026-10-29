#!/usr/bin/env python3
"""Independent offline review. No compiler, product runtime, process probe or child."""
import ast, contextlib, copy, datetime, hashlib, importlib.util, io, json, os
from pathlib import Path
import platform, signal, socket, subprocess, sys, tempfile, time, unittest, zipfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
CAND=HERE.parent/'swift-dense512-completion-experiment'
RAW=HERE.parent/'github-delivery-capacity-window/ci-review'
READS=set(); DENIED=[]; FDS={}; START=time.monotonic()
sys.dont_write_bytecode=True

def forbidden(*args, **kwargs):
    DENIED.append('blocked API')
    raise AssertionError('independent offline guard denied process/network/custody API')

def owned(p, fd=None):
    p=Path(os.fsdecode(p))
    if not p.is_absolute() and fd is not None and fd >= 0:
        if fd not in FDS: raise AssertionError('unowned directory descriptor')
        p=FDS[fd]/p
    if not p.resolve().is_relative_to(HERE):
        raise AssertionError('write outside independent review lane')

raw_open, raw_close=os.open, os.close

def tracked_open(p, flags, mode=0o777, *, dir_fd=None):
    if dir_fd is not None:
        owned(p,dir_fd)
        p=FDS[dir_fd]/p
    fd=raw_open(p,flags,mode)
    FDS[fd]=Path(p).resolve()
    return fd

def tracked_close(fd):
    FDS.pop(fd,None)
    return raw_close(fd)

os.open,os.close=tracked_open,tracked_close

def audit(event,args):
    if event.startswith(('subprocess.','socket.','pty.','ctypes.')) or event in {
        'os.system','os.fork','os.forkpty','os.posix_spawn','os.exec','os.kill','os.killpg','os.chdir'}:
        forbidden()
    if event=='open':
        name,mode,flags=args
        writing=isinstance(mode,str) and any(x in mode for x in 'wax+')
        writing |= isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if isinstance(name,(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(name)).resolve()
            if writing: owned(p)
            elif p.is_relative_to(ROOT) and not p.is_relative_to(HERE): READS.add(p)
        elif writing: raise AssertionError('untracked writable file descriptor')
    if event in {'os.remove','os.rmdir','os.mkdir','os.chmod','os.utime'}:
        index={'os.remove':1,'os.rmdir':1,'os.mkdir':2,'os.chmod':2,'os.utime':3}[event]
        owned(args[0],args[index] if len(args)>index and isinstance(args[index],int) else None)
    if event=='os.rename':
        owned(args[0],args[2]); owned(args[1],args[3])
    if event in {'os.link','os.symlink','os.chown','os.truncate'}:
        raise AssertionError('unneeded filesystem mutation denied')

sys.addaudithook(audit)
BANNED=[]
for module,names in [
    (os,'system fork forkpty posix_spawn posix_spawnp kill killpg wait waitpid wait3 wait4 waitid popen execv execve execl execle execlp execlpe execvp execvpe setsid getsid setpgid getpgid setpgrp getpgrp getpid getppid'),
    (signal,'signal pthread_sigmask pthread_kill sigwait sigwaitinfo sigtimedwait alarm setitimer raise_signal pause'),
    (subprocess,'Popen run call check_call check_output'),
    (socket,'socket socketpair create_connection create_server getaddrinfo gethostbyname gethostbyname_ex gethostbyaddr getnameinfo')]:
    for name in names.split():
        if hasattr(module,name):
            setattr(module,name,forbidden); BANNED.append((module,name))

def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def rec(b): return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(name,obj): (HERE/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def bound():
    if time.monotonic()-START>60: raise AssertionError('60-second independent offline deadline')

def verify_seal(directory, expected):
    data=(directory/'seal.json').read_bytes()
    assert rec(data)['sha256']==expected
    seal=json.loads(data)
    assert len(seal['files'])==seal['filesCount']
    for name,row in seal['files'].items():
        bound(); assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert rec((directory/name).read_bytes())==row, name
    return seal

CAND_SEAL='9fafabda83d0a64c1d609afa61c845d0f9d0a93e5cb44580f3f2a8a5ca62ee08'
RAW_SEAL='c272c735a0a959a9c27e1072503bceb3df7624c9bdf1a8515a54d4baa05ea072'
verify_seal(CAND,CAND_SEAL); verify_seal(RAW,RAW_SEAL)
suite=load('independent_candidate_controls',CAND/'test_campaign.py')
c=suite.campaign
original,artifact,bindings=c.inputs()
candidate=c.candidate_module()
prior=candidate.prior.parameterize(original,True)
source=c.prepare_source(original,True)
prior_record,_=c.base.source_record(original,prior)
source_record,_=c.base.source_record(original,source)

class IndependentControls(unittest.TestCase):
    def setUp(self): bound()

    def test_guard_denies_each_exposed_process_session_group_socket_api(self):
        for module,name in BANNED:
            with self.subTest(api=module.__name__+'.'+name),self.assertRaisesRegex(AssertionError,'offline guard'):
                getattr(module,name)()
        self.assertEqual(len(DENIED),len(BANNED))

    def test_both_packets_and_all_frozen_source_members_are_bound(self):
        self.assertEqual(verify_seal(CAND,CAND_SEAL)['filesCount'],27)
        self.assertEqual(verify_seal(RAW,RAW_SEAL)['filesCount'],19)
        self.assertEqual(prior_record['sha256'],'09ac825f108574f626838e0fc54628adb5ed70fa8d8871b527bc1bba4922c0ee')
        self.assertEqual(source_record['sha256'],'066789f44a39300a33e7583ab039086589576e3c8701ecfdd19dc4717ebab567')
        self.assertEqual(source_record,json.loads((CAND/'source-check/dense512-completion/source.json').read_bytes()))

    def test_exact_four_file_delta_restores_every_byte_of_executed_source(self):
        delta={n for n in source if source[n]!=prior.get(n)}
        self.assertEqual(set(source),set(prior))
        self.assertEqual(delta,{'src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/cache_tests.rs',
            'src/experimental_swift_reactor/control_tests.rs','src/experimental_wasi/mod.rs'})
        restored=dict(source)
        for name,old,new,count in [
            ('src/experimental_swift_reactor/control.rs','instruction_fuel: 4_000_000_000,','instruction_fuel: 2_000_000_000,',1),
            ('src/experimental_swift_reactor/control.rs','deadline_ms: 1_200_000,','deadline_ms: 600_000,',1),
            ('src/experimental_wasi/mod.rs','deadline_ms: 1_200_000,','deadline_ms: 600_000,',1),
            ('src/experimental_swift_reactor/cache_tests.rs','4_000_000_000, 16_000_000_000, 1_200_000','2_000_000_000, 16_000_000_000, 600_000',2),
            ('src/experimental_swift_reactor/control_tests.rs',(CAND/'scalar-guards.rs').read_text(),(candidate.PRIOR/'scalar-guards.rs').read_text(),1)]:
            self.assertEqual(restored[name].decode().count(old),count)
            restored[name]=restored[name].decode().replace(old,new).encode()
        self.assertEqual(restored,prior)

    def test_actual_archive_phase_source_and_geometry_join(self):
        evidence=json.loads((CAND/'phase-evidence.json').read_bytes())
        with zipfile.ZipFile(RAW/'artifact.zip') as z:
            self.assertEqual(len(z.namelist()),len(set(z.namelist())))
            raw=z.read(evidence['member'])
            self.assertEqual(rec(raw)['sha256'],evidence['memberSHA256'])
            self.assertEqual(json.loads(z.read('dense-512-window/source.json')),prior_record)
            events=[json.loads(line.split(b'MIXER_EXACT ',1)[1]) for line in raw.splitlines() if b'MIXER_EXACT ' in line]
            for event,key in [('initialize','initialize'),('corpus_1','corpus1Cumulative')]:
                values=[x['payload']['usage'] for x in events if x['event']==event]
                self.assertEqual(len(values),1)
                self.assertEqual({k:values[0][k] for k in evidence[key]},evidence[key])
            self.assertEqual(json.loads(z.read('dense-512-window/geometry.json')),evidence['actualGeometry'])
            self.assertEqual([x['payload'] for x in events if x['event']=='guest_output_native_equal'],['corpus_1'])
            self.assertEqual([x['payload'] for x in events if x['event']=='phase_begin'],['validation','initialize','corpus_1','corpus_2'])
            self.assertFalse(any(x['event']=='diagnostic_execution_complete' and x['payload'] is True for x in events))
        self.assertEqual(evidence['twoCorpusHypothesis'],{k:2*evidence['corpus1Cumulative'][k]-v for k,v in evidence['initialize'].items()})
        self.assertEqual(evidence['twoCorpusHypothesis']['elapsed_micros'],839370504)

    def test_all_twelve_selected_finite_functions_are_unique_and_deadline_control_is_real(self):
        methods=[]
        for name,data in source.items():
            for line in data.decode().splitlines():
                if line.startswith('fn framepin_campaign_'): methods.append((name,line))
        self.assertEqual(len(methods),12)
        self.assertEqual(len(set(line for _,line in methods)),12)
        tests=source['src/experimental_swift_reactor/control_tests.rs'].decode()
        start=tests.index('fn deadlines_are_carried_as_earliest_absolute_time_and_real_expiry_is_sticky()')
        body=tests[start:tests.index('\n#[test]',start)]
        self.assertIn('std::thread::sleep(Duration::from_millis(12))',body)
        self.assertIn('sticky',body)
        self.assertIn('assert_empty(clean(',body)
        self.assertEqual(body,prior['src/experimental_swift_reactor/control_tests.rs'].decode()[start:prior['src/experimental_swift_reactor/control_tests.rs'].decode().index('\n#[test]',start)])

    def test_budget_or_persistence_failure_never_admits_a_full_spawn(self):
        for failed in ('budget','save'):
            with tempfile.TemporaryDirectory() as tmp:
                record={'fullAttempts':0}; output=Path(tmp)
                with patch.object(c.base,'ensure_command_budget',side_effect=RuntimeError('budget') if failed=='budget' else None),\
                     patch.object(c,'save',side_effect=RuntimeError('save') if failed=='save' else None),\
                     patch.object(c,'guarded_command',side_effect=AssertionError('must not spawn')) as command:
                    with self.assertRaises(RuntimeError): c.reserve_full_attempt(record,output)
                    command.assert_not_called()
                    self.assertEqual(record['fullAttempts'],0 if failed=='budget' else 1)

    def test_pending_command_is_durable_before_helper_and_receipt_failure_blocks_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); custody={'recordPath':str(out/'custody.json'),'pendingCommand':None,'provenClosedCommands':5}
            def helper(*args):
                saved=json.loads((out/'custody.json').read_text())
                self.assertEqual(saved['pendingCommand']['argv'],['synthetic-only'])
                self.assertEqual(saved['provenClosedCommands'],5)
                raise RuntimeError('synthetic helper failure')
            with patch.object(c.base,'command',side_effect=helper) as command:
                with self.assertRaisesRegex(RuntimeError,'helper failure'):
                    c.guarded_command(custody,['synthetic-only'],out,{},out/'cmd',1350)
                with self.assertRaisesRegex(RuntimeError,'custody unresolved'):
                    c.guarded_command(custody,['never'],out,{},out/'next',1)
                self.assertEqual(command.call_count,1)
                self.assertIsNotNone(custody['pendingCommand'])
                self.assertEqual(custody['provenClosedCommands'],5)

    def test_full_failure_preserves_reserved_attempt_without_hidden_second_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp); phase=output/'dense512-completion'; phase.mkdir()
            prepared={'name':'dense512-completion','capacity512':True,'source':{},'record':{},'phase':phase,
                'crate':output,'childEnv':{},'binary':output/'not-an-executable','executable':{}}
            record={'fullAttempts':0,'preparationGate':{'singleArmPrepared':True,'fullAttemptsAtAdmission':0,'closedPreparationCommands':5},
                'preparedProfiles':[{'name':'dense512-completion'}]}
            custody={'recordPath':str(output/'custody.json'),'pendingCommand':None,'provenClosedCommands':5}
            with patch.object(c,'verify_prepared'),patch.object(c.base,'ensure_command_budget'),\
                 patch.object(c.base,'command',side_effect=RuntimeError('synthetic spawn failure')) as command:
                with self.assertRaisesRegex(RuntimeError,'spawn failure'):
                    c.execute_profile(prepared,None,output,output,record,custody)
                self.assertEqual(json.loads((output/'campaign.json').read_text())['fullAttempts'],1)
                self.assertEqual(command.call_count,1)
                self.assertIsNotNone(custody['pendingCommand'])
                with self.assertRaisesRegex(RuntimeError,'full attempt cap'): c.reserve_full_attempt(record,output)
                self.assertEqual(command.call_count,1)

    def test_conservative_geometry_rejects_envelope_overflow_bad_formula_and_tickets(self):
        case=suite.CompletionTests()
        text=case.geometry_fixture(True).replace('4000000000,2000000000,16000000000','4000000000,4000000000,16000000000')
        text+='COMPLETION deadline_ms=1200000 wasi_deadline_ms=1200000 earliest_absolute=true sticky_expiry=true cleanup_zero=true\n'
        good=case.parse_geometry(text,True)
        for old,new in [
            ('combined_limit=268435456','combined_limit=268435457'),
            ('frame_operation=3000','frame_operation=999999999'),
            ('tickets=533/534','tickets=533/535'),
            ('pin_bitmap_bytes=16','pin_bitmap_bytes=32'),
            ('guest_instructions=0','guest_instructions=1'),
            ('earliest_absolute=true','earliest_absolute=false')]:
            with self.subTest(old=old),self.assertRaises(RuntimeError): case.parse_geometry(text.replace(old,new),True)
        self.assertLess(good['recomputedConservativeCombined'],good['combinedLimit'])

    def test_no_false_eof_or_resource_success_claim_and_original_count_mismatch_retained(self):
        decision=(CAND/'DECISION.md').read_text()
        self.assertIn('no explicit pipe-EOF flag',decision)
        self.assertIn('Resource exhaustion remains diagnostic failure',decision)
        first=json.loads((CAND/'first-pure-attempt.json').read_bytes())
        self.assertTrue(first)
        self.assertIn('Ran 35 tests',(CAND/'first-pure-attempt.stderr').read_text())
        self.assertIn('Ran 36 tests',(CAND/'pure-check.stderr').read_text())

start=datetime.datetime.now(datetime.timezone.utc).isoformat()
scratch=HERE/'scratch'
scratch.mkdir(exist_ok=False)
tempfile.tempdir=str(scratch)
try:
    combined=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(suite),unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)])
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(combined)
    (HERE/'tests.log').write_text(stream.getvalue())
finally:
    tempfile.tempdir=None
    scratch.rmdir()
bound()
verify_seal(CAND,CAND_SEAL);verify_seal(RAW,RAW_SEAL)
save('readset.json',{'scope':'audited repository files read by independent offline verifier','files':{str(p.relative_to(ROOT)):rec(p.read_bytes()) for p in sorted(READS)}})
save('receipt.json',{'schema':1,'startedAtUTC':start,'completedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command':'python3 -B verification/swift-dense512-completion-independent/review.py','python':sys.version,'pythonExecutable':sys.executable,
    'candidateSealSHA256':CAND_SEAL,'sourceSHA256':source_record['sha256'],'actualSourceSHA256':prior_record['sha256'],
    'testsRun':result.testsRun,'testsPassed':result.wasSuccessful(),'inheritedMethods':36,'independentMethods':10,
    'failures':len(result.failures),'errors':len(result.errors),'guardedAPIs':len(BANNED),'blockedGuardSelfTests':len(DENIED),
    'unexpectedForbiddenAPIAttempts':len(DENIED)-len(BANNED),'realChildSocketSignalWaitSessionGroupCalls':0,
    'compilerProductRuntimeNativeUICaptureRuns':0,'ownedScratchRemoved':not scratch.exists(),
    'internalDeadlineSeconds':60,'elapsedSeconds':time.monotonic()-START,
    'sourceTreeDigest':rec((HERE/'readset.json').read_bytes())['sha256'],
    'sourceTreeDigestScope':'audited offline read closure; no Git/process inventory or mutable HEAD query',
    'actualBaseline':{'run':40788458735,'head':'e5670519a0d02b74a95c00d35dbf5f837fca9850','tree':'89a9344ecf974105b7ad7df30394485bade6e284'},
    'scope':'independent source/data and synthetic fault controls only; actual compiler, finite/harness and full CI attempt pending'})
print(json.dumps({'passed':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'guardedAPIs':len(BANNED),'elapsedSeconds':time.monotonic()-START}))
if not result.wasSuccessful():
    print(stream.getvalue())
    raise SystemExit(1)
