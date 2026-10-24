"""Independent, bounded host controls for V8; no native evidence or producer edits."""
import copy
import errno
import json
import os
import stat
import tempfile
import unittest
from unittest import mock
import independent_flow as f
import durable_settings as d

RESULTS=[]


def snapshot(flow):
    return dict(state=flow.state(), summary=flow.bridge.settings.summary(), journals={name:f.t.sha(data) for name,data in flow.journal().items()})


def save(flow,kind,**detail):
    value=dict(kind=kind,syntheticHostOnly=True,nativeExecuted=False,hostEvidence=str(flow.root.relative_to(f.ROOT)),**detail)
    path=flow.root/'independent-control.json';path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    RESULTS.append({**value,'receiptSHA256':f.t.sha(path.read_bytes())})


class TraceIO(d.DiskIO):
    def __init__(self, fault=None):self.operations=[];self.fault=fault;self.fired=[]
    def sync(self,path,role):
        self.operations.append(['sync',role])
        super().sync(path,role)
        if self.fault==('sync-after',role) and not self.fired:
            self.fired.append(role);raise OSError(errno.EIO,'independent after actual '+role+' fsync')
    def unlink(self,path,role):
        self.operations.append(['unlink',role]);super().unlink(path,role)


class IndependentChecks(unittest.TestCase):
    def test_01_complete_initial_off_and_on_baselines(self):
        for initial in ['0','1']:
            flow=f.Flow('complete-baseline-'+initial);flow.complete(initial)
            summary=flow.bridge.settings.summary()
            self.assertTrue(summary['setupObservationSatisfied']);self.assertFalse(summary['persistenceUncertain'])
            self.assertEqual(summary,f.replay.replay(flow.bridge.output))
            self.assertFalse(d.unresolved(flow.bridge.output));self.assertFalse(summary['nativeKeyboardQualification'])
            self.assertEqual(summary['completionMarkers'],['test-case-finished','suite-finished','bundle-finished'])
            save(flow,'complete-synthetic-baseline',initial=initial,summary=summary,replayMatches=True)

    def test_02_prior_postwrite_journal_fault_rejects_and_retries(self):
        flow=f.Flow('publication-directory-error');flow.before();record=flow.action(send=False);before=snapshot(flow)
        io=TraceIO(('sync-after','publication-directory'));flow.bridge.persistence.io=io
        status,body=flow.http(record)
        self.assertEqual(status,400);self.assertIn('independent after actual',body['error'])
        self.assertEqual(snapshot(flow),before);self.assertFalse(d.unresolved(flow.bridge.output))
        self.assertEqual(before['summary'],f.replay.replay(flow.bridge.output))
        flow.bridge.persistence.io=d.DiskIO();retry=flow.http(record)
        self.assertEqual(retry[0],200);self.assertTrue(retry[1]['accepted'])
        self.assertEqual(flow.bridge.settings.summary(),f.replay.replay(flow.bridge.output))
        save(flow,'prior-postwrite-journal-fixed-in-isolation',http=[status,retry[0]],error=body['error'],before=before,after=flow.bridge.settings.summary(),operations=io.operations)

    def test_03_prior_payload_orphan_fault_rejects_and_retries(self):
        flow=f.Flow('final-payload-journal-partial-write');flow.routes();record,payloads=flow.observation('before-switch');flow.send(record)
        record=next(flow.chunks(payloads));before=snapshot(flow);payload=flow.bridge.output/(record['slot']+'.txt')
        class PartialJournalIO(TraceIO):
            def write(self,path,data,role):
                self.operations.append(['write',role])
                if role=='journal' and not self.fired:
                    self.fired.append('journal-partialwrite')
                    real_write=os.write;calls=[]
                    def short_then_error(fd,part):
                        if not calls:
                            count=real_write(fd,part[:max(1,len(part)//2)]);calls.append(count);return count
                        raise OSError(errno.EIO,'independent journal failure after actual partial write')
                    with mock.patch.object(d.os,'write',side_effect=short_then_error):return super().write(path,data,role)
                return super().write(path,data,role)
        io=PartialJournalIO();flow.bridge.persistence.io=io;status,body=flow.http(record)
        self.assertEqual(status,400);self.assertIn('actual partial write',body['error'])
        self.assertEqual(snapshot(flow),before);self.assertFalse(payload.exists());self.assertFalse(d.unresolved(flow.bridge.output))
        self.assertEqual(before['summary'],f.replay.replay(flow.bridge.output))
        flow.bridge.persistence.io=d.DiskIO();retry=flow.http(record)
        self.assertEqual(retry[0],200);self.assertTrue(payload.is_file())
        self.assertEqual(flow.bridge.settings.summary(),f.replay.replay(flow.bridge.output))
        save(flow,'prior-final-payload-orphan-fixed-in-isolation',http=[status,retry[0]],error=body['error'],payloadSHA256=f.t.sha(payload.read_bytes()),before=before,after=flow.bridge.settings.summary(),operations=io.operations)

    def test_04_actual_ancillary_summary_file_fsync_failure_preserves_ack(self):
        flow=f.Flow('ancillary-summary-actual-fsync');flow.before();record=flow.action(send=False)
        real_mkstemp=tempfile.mkstemp;real_fsync=os.fsync;targets=set();fired=[]
        def marked_temp(*args,**kwargs):
            fd,name=real_mkstemp(*args,**kwargs)
            if kwargs.get('prefix')=='.summary-':
                info=os.fstat(fd);targets.add((info.st_dev,info.st_ino))
            return fd,name
        def summary_fsync(fd):
            real_fsync(fd);info=os.fstat(fd)
            if (info.st_dev,info.st_ino) in targets and not fired:
                fired.append('summary-file-fsync-after-actual')
                raise OSError(errno.EIO,'independent ancillary summary fsync failure')
        with mock.patch.object(tempfile,'mkstemp',side_effect=marked_temp),mock.patch.object(os,'fsync',side_effect=summary_fsync):status,body=flow.http(record)
        self.assertTrue(fired);self.assertEqual(status,200);self.assertTrue(body['accepted'])
        self.assertEqual(flow.bridge.settings.sequence,record['sequence'])
        self.assertEqual(flow.bridge.settings.summary(),f.replay.replay(flow.bridge.output))
        self.assertTrue(flow.bridge.ancillary_failures)
        saved=[json.loads(path.read_bytes()) for path in flow.bridge.output.glob('ancillary-*.json')]
        self.assertTrue(any('independent ancillary summary' in row['reason'] for row in saved))
        save(flow,'prior-postcommit-summary-ack-fixed-in-isolation',http=status,body=body,summary=flow.bridge.settings.summary(),ancillary=flow.bridge.ancillary_failures,fired=fired)

    def test_05_precommit_rollback_uncertainty_remains_guarded_terminal(self):
        flow=f.Flow('ordinary-terminal-uncertainty');flow.before();record=flow.action(send=False);before=flow.state()
        class TerminalIO(TraceIO):
            def unlink(self,path,role):
                if role=='rollback-journal':
                    self.operations.append(['unlink-error',role]);raise OSError(errno.EIO,'independent rollback journal failure')
                return super().unlink(path,role)
        io=TerminalIO(('sync-after','publication-directory'));flow.bridge.persistence.io=io;status,body=flow.http(record)
        self.assertEqual(status,400);self.assertIn('PersistenceUncertain',body['error']);self.assertEqual(flow.state(),before)
        self.assertTrue(d.unresolved(flow.bridge.output));self.assertTrue(flow.bridge.settings.summary()['persistenceUncertain'])
        self.assertFalse(flow.bridge.settings.summary()['setupObservationSatisfied'])
        with self.assertRaises(d.PersistenceUncertain):f.replay.replay(flow.bridge.output)
        with self.assertRaises(d.PersistenceUncertain):d.TransactionStore(flow.bridge.output,flow.bridge.identity)
        flow.bridge.persistence.io=d.DiskIO();retry=flow.http(record)
        self.assertEqual(retry[0],400);self.assertIn('PersistenceUncertain',retry[1]['error'])
        save(flow,'ordinary-guarded-terminal-behavior',http=[status,retry[0]],body=body,guardPresent=True,replayRefused=True,startupRefused=True,summary=flow.bridge.settings.summary(),operations=io.operations)

    def test_06_guard_probe_only_enoent_means_absence(self):
        flow=f.Flow('lstat-absence-errors');guard=flow.bridge.persistence.guard
        self.assertFalse(d.unresolved(flow.bridge.output));real_lstat=os.lstat;observed=[]
        for error in [OSError(errno.EIO,'independent EIO'),PermissionError(errno.EACCES,'independent EACCES'),NotADirectoryError(errno.ENOTDIR,'independent ENOTDIR')]:
            def fault(path,*args,**kwargs):
                if os.fspath(path)==os.fspath(guard):raise error
                return real_lstat(path,*args,**kwargs)
            with mock.patch.object(d.os,'lstat',side_effect=fault):
                with self.assertRaises(type(error)):d.unresolved(flow.bridge.output)
            observed.append(dict(type=type(error).__name__,errno=error.errno,absenceNotClaimed=True))
        guard.symlink_to(flow.root/'missing-synthetic-target')
        self.assertTrue(d.unresolved(flow.bridge.output))
        with self.assertRaises(d.PersistenceUncertain):f.replay.replay(flow.bridge.output)
        with self.assertRaises(d.PersistenceUncertain):d.TransactionStore(flow.bridge.output,flow.bridge.identity)
        save(flow,'guard-lstat-exact-absence-and-dangling-link',statErrors=observed,danglingLinkRefused=True)


if __name__=='__main__':
    result=unittest.main(verbosity=2,exit=False).result
    (f.HERE/'independent-controls.json').write_text(json.dumps(dict(schema='mixer.apple-keyboard.v8-independent-host-controls.1',syntheticHostOnly=True,nativeExecuted=False,methodsRun=result.testsRun,passed=result.wasSuccessful(),controls=RESULTS,controlCount=len(RESULTS),doesNotOverrideFailingGuardProbe=True),sort_keys=True,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
