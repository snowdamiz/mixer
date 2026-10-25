"""Adversarial actual Session + Bridge + real loopback HTTP + retained replay.

Faults wrap real filesystem calls, including genuine short/partial writes and
errors before/after fsync, hardlink publication and unlink. No protocol model.
"""
import base64
import copy
import errno
import http.client
import json
import os
import pathlib
import threading
import unittest
from unittest import mock
import fixtures as f
import replay
import durable_settings as d

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = []


def send_http(flow, record):
    server = f.producer.h.server_for(flow.bridge)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    client = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
    try:
        client.request('POST','/evaluate',body=json.dumps({'settingsDiagnostic':record}).encode(),headers={'Content-Type':'application/json','X-Mixer-Capability':flow.bridge.capability})
        response = client.getresponse()
        return response.status, json.loads(response.read())
    finally:
        client.close(); thread.join(timeout=3); server.server_close()
        if thread.is_alive():
            raise AssertionError('Owned synthetic HTTP thread did not terminate')


class FaultIO(d.DiskIO):
    def __init__(self, role, mode, extra=None):
        self.role, self.mode, self.extra = role, mode, extra
        self.fired = []
        self.operations = []

    def fault(self, role, mode):
        choices = [(self.role,self.mode)] + ([] if self.extra is None else [self.extra])
        key=(role,mode)
        if key in choices and key not in self.fired:
            self.fired.append(key)
            return True
        return False

    def write(self, path, payload, role):
        self.operations.append(('write',role))
        if self.fault(role,'prewrite'):
            raise OSError('injected '+role+' prewrite')
        if self.fault(role,'partialwrite'):
            real=os.write; calls=[0]
            def partial(fd,data):
                calls[0]+=1
                if calls[0]==1:
                    return real(fd,data[:max(1,len(data)//2)])
                raise OSError('injected '+role+' partialwrite after real short write')
            with mock.patch.object(d.os,'write',side_effect=partial):
                return super().write(path,payload,role)
        if self.fault(role,'filefsync-before'):
            with mock.patch.object(d.os,'fsync',side_effect=OSError('injected '+role+' before file fsync')):
                return super().write(path,payload,role)
        if self.fault(role,'filefsync'):
            real=os.fsync
            def sync(fd):
                real(fd)
                raise OSError('injected '+role+' filefsync after actual fsync')
            with mock.patch.object(d.os,'fsync',side_effect=sync):
                return super().write(path,payload,role)
        super().write(path,payload,role)
        if self.fault(role,'postwrite'):
            raise OSError('injected '+role+' postwrite')

    def sync(self, path, role):
        self.operations.append(('sync',role))
        if self.fault(role,'before'):
            raise OSError('injected '+role+' before directory fsync')
        super().sync(path,role)
        if self.fault(role,'after'):
            raise OSError('injected '+role+' after actual directory fsync')

    def publish(self, staged, final, role):
        self.operations.append(('publish',role))
        if self.fault(role,'before-publish'):
            raise OSError('injected '+role+' before publication')
        super().publish(staged,final,role)
        if self.fault(role,'after-publish'):
            raise OSError('injected '+role+' after actual publication')

    def unlink(self,path,role):
        self.operations.append(('unlink',role))
        if self.fault(role,'before-unlink'):
            raise OSError('injected '+role+' before unlink')
        super().unlink(path,role)
        if self.fault(role,'after-unlink'):
            raise OSError('injected '+role+' after actual unlink')


class PersistenceTests(unittest.TestCase):
    def flow(self, upload=False):
        flow=f.Flow(); self.addCleanup(flow.close)
        if upload:
            flow.routes()
            record,payloads=flow.observe('before-switch',upload=False)
            flow.send(record)
            slot=flow.bridge.settings.pending[0]
            data=payloads['ax'];item=flow.bridge.settings.uploads[slot]
            record=flow.record('chunk',slot=slot,index=0,count=item['count'],bytes=len(data),sha256=f.t.sha(data),data=base64.b64encode(data).decode())
            return flow,record,slot+'.txt'
        flow.before()
        return flow,flow.action_record(),None

    def snapshot(self, flow):
        return copy.deepcopy({key:value for key,value in flow.bridge.settings.__dict__.items() if key not in ['persist','persist_file','transaction','now']})

    def journals(self,flow):
        return {p.name:f.t.sha(p.read_bytes()) for p in flow.bridge.output.glob('0000-settings-*.json')}

    def committed(self,flow,record,io,before=None):
        self.assertEqual(flow.bridge.settings.sequence,record['sequence'])
        journals=self.journals(flow)
        self.assertEqual(len(journals),record['sequence']+1)
        journal=flow.bridge.output/f"0000-settings-{record['sequence']:04d}.json"
        self.assertEqual(json.loads(journal.read_bytes())['record'],record)
        if before is not None:
            self.assertEqual({k:v for k,v in journals.items() if k in before},before)
        self.assertFalse(any('rollback' in role for operation,role in io.operations))
        # Retirement is live metadata; compare every protocol/evidence field.
        replayed=replay.replay(flow.bridge.output) if not d.unresolved(flow.bridge.output) else None
        if replayed is not None:
            protocol=lambda value:{k:v for k,v in value.items() if k not in ['persistenceUncertain','persistenceRetirementPending']}
            self.assertEqual(protocol(flow.bridge.settings.summary()),protocol(replayed))

    def blocked_new_work(self,flow):
        if flow.bridge.settings.pending:
            slot=flow.bridge.settings.pending[0];item=flow.bridge.settings.uploads[slot]
            data=f.image() if item['format']=='png' else b'Independent synthetic AX text; not a native hierarchy\n'
            record=flow.record('chunk',slot=slot,index=len(item['parts']),count=item['count'],bytes=len(data),sha256=f.t.sha(data),data=base64.b64encode(data).decode())
        else:
            record,_=flow.observe('after-switch',value='1',upload=False)
        before=self.snapshot(flow);journals=self.journals(flow)
        status,body=send_http(flow,record)
        self.assertEqual(status,400);self.assertIn('PersistenceUncertain',body['error'])
        self.assertEqual(before,self.snapshot(flow));self.assertEqual(journals,self.journals(flow))
        return status,body

    def receipt(self, flow, detail):
        path=flow.root/'persistence-control.json'
        detail={**detail,'journals':self.journals(flow),'guardPresentAtReceipt':d.unresolved(flow.bridge.output),'acceptedCursorAtReceipt':flow.bridge.settings.sequence,'requestsAtReceipt':flow.bridge.settings.requests}
        path.write_text(json.dumps(dict(syntheticHostOnly=True,nativeExecuted=False,**detail,settingsDiagnostic=flow.bridge.settings.summary()),indent=2,sort_keys=True)+'\n')
        RESULTS.append({'path':str(path.relative_to(HERE)),'sha256':f.t.sha(path.read_bytes()),**detail})

    def recoverable(self, role, mode, upload=False):
        flow,record,payload=self.flow(upload)
        before=self.snapshot(flow);journals=self.journals(flow)
        io=FaultIO(role,mode);flow.bridge.persistence.io=io
        status,body=send_http(flow,record)
        self.assertEqual(status,400);self.assertIn('injected',body['error'])
        self.assertEqual(before,self.snapshot(flow));self.assertEqual(journals,self.journals(flow))
        self.assertFalse(d.unresolved(flow.bridge.output))
        if payload:self.assertFalse((flow.bridge.output/payload).exists())
        self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
        flow.bridge.persistence.io=d.DiskIO()
        retry_status,retry_body=send_http(flow,record)
        self.assertEqual(retry_status,200);self.assertTrue(retry_body['accepted'])
        self.assertEqual(flow.bridge.settings.sequence,record['sequence'])
        self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
        self.assertTrue(io.fired)
        self.receipt(flow,dict(kind='recoverable-rejection-same-sequence-retry',fault=[role,mode],http=[status,retry_status],error=body['error'],acceptedSequence=record['sequence'],operations=io.operations,fired=io.fired,payload=payload))

    def test_action_journal_all_write_publish_directory_faults_reject_and_retry(self):
        for role,mode in [('guard','prewrite'),('guard','partialwrite'),('guard','filefsync'),('guard','postwrite'),('guard-directory','before'),('guard-directory','after'),('journal','prewrite'),('journal','partialwrite'),('journal','filefsync-before'),('journal','filefsync'),('journal','postwrite'),('staging-directory','before'),('staging-directory','after'),('journal','before-publish'),('journal','after-publish'),('publication-directory','before'),('publication-directory','after')]:
            with self.subTest(role=role,mode=mode):self.recoverable(role,mode)

    def test_final_chunk_payload_and_journal_transaction_order_faults_reject_and_retry(self):
        for role,mode in [('payload','prewrite'),('payload','partialwrite'),('payload','filefsync-before'),('payload','filefsync'),('payload','postwrite'),('payload','before-publish'),('payload','after-publish'),('journal','prewrite'),('journal','partialwrite'),('journal','filefsync'),('journal','before-publish'),('journal','after-publish'),('publication-directory','before'),('publication-directory','after')]:
            with self.subTest(role=role,mode=mode):self.recoverable(role,mode,True)

    def test_actual_short_writes_complete_until_all_bytes_are_saved(self):
        flow,record,payload=self.flow(True)
        real=os.write;counts=[]
        def short(fd,data):
            count=real(fd,data[:max(1,min(7,len(data)))]);counts.append(count);return count
        with mock.patch.object(d.os,'write',side_effect=short):status,body=send_http(flow,record)
        self.assertEqual(status,200);self.assertTrue(body['accepted']);self.assertGreater(len(counts),10)
        self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
        self.receipt(flow,dict(kind='real-short-writes-success',http=status,writeCalls=len(counts)))

    def test_rollback_uncertainty_keeps_guard_http_terminal_and_replay_never_credits(self):
        for extra in [('rollback-journal','before-unlink'),('rollback-journal','after-unlink'),('rollback-directory','before'),('rollback-directory','after')]:
            flow,record,_=self.flow();before=self.snapshot(flow)
            io=FaultIO('publication-directory','after',extra);flow.bridge.persistence.io=io
            status,body=send_http(flow,record)
            self.assertEqual(status,400);self.assertIn('PersistenceUncertain',body['error'])
            self.assertEqual(before,self.snapshot(flow));self.assertTrue(d.unresolved(flow.bridge.output))
            self.assertTrue(flow.bridge.settings.summary()['persistenceUncertain'])
            self.assertFalse(flow.bridge.settings.summary()['setupObservationSatisfied'])
            with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
            flow.bridge.persistence.io=d.DiskIO()
            retry_status,retry_body=send_http(flow,record)
            self.assertEqual(retry_status,400);self.assertIn('PersistenceUncertain',retry_body['error'])
            with self.assertRaises(d.PersistenceUncertain):d.TransactionStore(flow.bridge.output,flow.bridge.identity)
            self.receipt(flow,dict(kind='terminal-uncertainty',fault=['publication-directory','after'],rollbackFault=extra,http=[status,retry_status],guardPresent=True,journalComplete=(flow.bridge.output/f"0000-settings-{record['sequence']:04d}.json").exists(),error=body['error'],operations=io.operations,fired=io.fired))

    def test_payload_rollback_uncertainty_keeps_guard_and_pending_upload(self):
        flow,record,payload=self.flow(True);before=self.snapshot(flow)
        io=FaultIO('journal','before-publish',('rollback-payload','before-unlink'));flow.bridge.persistence.io=io
        status,body=send_http(flow,record)
        self.assertEqual(status,400);self.assertIn('PersistenceUncertain',body['error']);self.assertEqual(before,self.snapshot(flow))
        self.assertTrue((flow.bridge.output/payload).exists());self.assertTrue(d.unresolved(flow.bridge.output))
        with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
        self.receipt(flow,dict(kind='payload-terminal-uncertainty',http=status,error=body['error'],guardPresent=True,payloadPresent=True,operations=io.operations))

    def test_guard_error_after_actual_unlink_is_committed_ack_and_replay(self):
        flow,record,_=self.flow();io=FaultIO('guard-clear','after-unlink');flow.bridge.persistence.io=io
        status,body=send_http(flow,record)
        self.assertEqual(status,200);self.assertTrue(body['accepted']);self.assertEqual(flow.bridge.settings.sequence,record['sequence'])
        self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output));self.assertFalse(d.unresolved(flow.bridge.output))
        self.assertTrue(any(row['operation']=='guard-clear' for row in flow.bridge.persistence.ancillary))
        self.receipt(flow,dict(kind='committed-guard-unlink-reported-error-after-removal',http=status,body=body,ancillary=flow.bridge.persistence.ancillary))

    def test_postcommit_guard_directory_failure_keeps_ack_and_resurrected_guard_fails_closed(self):
        flow,record,_=self.flow();io=FaultIO('postcommit-guard-directory','after');flow.bridge.persistence.io=io
        status,body=send_http(flow,record);self.assertEqual(status,200);self.assertTrue(body['accepted'])
        self.committed(flow,record,io)
        self.assertTrue(flow.bridge.persistence.retirement_pending);self.assertTrue(flow.bridge.persistence.ancillary)
        self.assertFalse(flow.bridge.settings.summary()['setupObservationSatisfied'])
        # The guard is actually absent. Offline replay can accept this ACKed
        # journal even though this live store conservatively blocks new work.
        self.assertEqual(replay.replay(flow.bridge.output)['sequence'],record['sequence'])
        # Simulate only conservative guard resurrection; no power-loss claim.
        d.DiskIO().write(flow.bridge.persistence.guard,d.encoded({'simulatedResurrectedGuard':True}),'fixture')
        with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
        self.receipt(flow,dict(kind='committed-postcommit-directory-error-conservative-resurrection-control',http=status,body=body,ancillary=flow.bridge.persistence.ancillary,simulatedGuardResurrection=True))

    def test_ancillary_summary_and_its_receipt_errors_never_replace_committed_http_ack(self):
        for receipt_error in [False,True]:
            flow,record,_=self.flow()
            with mock.patch.object(flow.bridge,'persist_summary',side_effect=OSError('injected ancillary summary failure')):
                if receipt_error:
                    with mock.patch.object(flow.bridge.persistence,'record_ancillary',side_effect=OSError('injected ancillary receipt failure')):status,body=send_http(flow,record)
                else:status,body=send_http(flow,record)
            self.assertEqual(status,200);self.assertTrue(body['accepted']);self.assertEqual(flow.bridge.settings.sequence,record['sequence'])
            self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output));self.assertTrue(flow.bridge.ancillary_failures)
            if not receipt_error:
                saved=[json.loads(p.read_bytes()) for p in flow.bridge.output.glob('ancillary-*.json')]
                self.assertTrue(any('injected ancillary summary failure' in row['reason'] for row in saved))
            self.receipt(flow,dict(kind='committed-ancillary-summary-error',http=status,body=body,ancillary=flow.bridge.ancillary_failures,ancillaryReceiptAlsoFailed=receipt_error))

    def test_ancillary_summary_receipt_actual_io_errors_preserve_ack_and_live_warning(self):
        for role,mode in [('ancillary','prewrite'),('ancillary','partialwrite'),('ancillary','filefsync-before'),('ancillary','filefsync'),('ancillary-directory','before'),('ancillary-directory','after')]:
            flow,record,_=self.flow();io=FaultIO(role,mode);flow.bridge.persistence.io=io
            with mock.patch.object(flow.bridge,'persist_summary',side_effect=OSError('injected ancillary summary failure')):status,body=send_http(flow,record)
            self.assertEqual(status,200);self.assertTrue(body['accepted']);self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
            self.assertTrue(any(row['operation']=='ancillary-receipt-unavailable' for row in flow.bridge.persistence.ancillary));self.assertTrue(io.fired)
            self.receipt(flow,dict(kind='committed-ancillary-summary-and-actual-receipt-io-error',fault=[role,mode],http=status,body=body,ancillary=flow.bridge.persistence.ancillary))

    def test_replay_rejects_partial_symlink_and_complete_unresolved_guards(self):
        for content in [b'',b'{',d.encoded({'complete':True})]:
            flow,record,_=self.flow()
            flow.bridge.persistence.guard.write_bytes(content)
            with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
        flow,record,_=self.flow();flow.bridge.persistence.guard.symlink_to(flow.bridge.output/'absent')
        with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)

    def test_v8_actual_guard_unlink_lstat_eio_rollback_eio_is_now_ack200_without_rollback(self):
        flow,record,_=self.flow();before=self.journals(flow);real_lstat=os.lstat
        class ReproduceV8(FaultIO):
            armed=False
            def unlink(self,path,role):
                if role=='rollback-journal':
                    self.operations.append(('unlink',role));self.fired.append(('rollback-journal','EIO'))
                    raise OSError(errno.EIO,'V8 rollback journal unlink EIO')
                super().unlink(path,role)
                if role=='guard-clear':self.armed=True
        io=ReproduceV8('unused','unused');flow.bridge.persistence.io=io
        def fail_stat(path,*args,**kwargs):
            if io.armed and os.fspath(path)==os.fspath(flow.bridge.persistence.guard):
                io.armed=False;io.fired.append(('guard-lstat','EIO-after-real-unlink'))
                raise OSError(errno.EIO,'V8 lstat EIO after actual guard unlink')
            return real_lstat(path,*args,**kwargs)
        with mock.patch.object(d.os,'lstat',side_effect=fail_stat):status,body=send_http(flow,record)
        self.assertEqual(status,200);self.assertTrue(body['accepted']);self.assertEqual(record['sequence'],20)
        self.committed(flow,record,io,before)
        self.assertTrue(flow.bridge.persistence.retirement_pending);self.assertTrue(flow.bridge.settings.summary()['persistenceUncertain'])
        self.assertFalse(d.unresolved(flow.bridge.output));self.assertEqual(replay.replay(flow.bridge.output)['sequence'],20)
        reopened=d.TransactionStore(flow.bridge.output,flow.bridge.identity);self.assertFalse(reopened.uncertain)
        blocked=self.blocked_new_work(flow)
        self.assertNotIn(('rollback-journal','EIO'),io.fired)
        self.receipt(flow,dict(kind='exact-V8-regression-ACK200-live20-replay20-no-rollback',http=[status,blocked[0]],body=body,beforeJournals=before,freshStoreAllowed=True,liveRetirementPending=True,operations=io.operations,fired=io.fired))

    def test_guard_unlink_before_removal_commits_action_and_payload_then_blocks_until_resolved(self):
        # These two expectations deliberately replace V8's rejected/retry cases:
        # guard-clear now occurs after the selected irrevocable commit point.
        for upload in [False,True]:
            flow,record,payload=self.flow(upload);before=self.journals(flow)
            io=FaultIO('guard-clear','before-unlink');flow.bridge.persistence.io=io
            status,body=send_http(flow,record);self.assertEqual(status,200);self.assertTrue(body['accepted'])
            self.committed(flow,record,io,before);self.assertTrue(d.unresolved(flow.bridge.output))
            if payload:self.assertTrue((flow.bridge.output/payload).is_file());self.assertTrue(flow.bridge.settings.uploads[record['slot']]['complete'])
            self.assertTrue(flow.bridge.settings.summary()['persistenceRetirementPending'])
            with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
            with self.assertRaises(d.PersistenceUncertain):d.TransactionStore(flow.bridge.output,flow.bridge.identity)
            blocked=self.blocked_new_work(flow)
            self.assertEqual(flow.bridge.settings.sequence,record['sequence'])
            flow.bridge.persistence.io=d.DiskIO();self.assertTrue(flow.bridge.persistence.resolve_retirement())
            self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
            duplicate=send_http(flow,record);self.assertEqual(duplicate[0],400);self.assertIn('Diagnostic sequence',duplicate[1]['error'])
            self.receipt(flow,dict(kind='postcommit-guard-removal-error-ACK200-guard-present-replay-refusal-positive-resolution',http=[status,blocked[0],duplicate[0]],payload=payload,operations=io.operations,guardPresentBeforeResolution=True,startupRefusedBeforeResolution=True))

    def test_postcommit_stat_eio_present_and_absent_guard_never_rejects_committed_request(self):
        for guard_present,unlink_reported_error in [(False,False),(False,True),(True,True)]:
            flow,record,_=self.flow();before=self.journals(flow);real_lstat=os.lstat
            class StatFaultIO(FaultIO):
                armed=False
                def unlink(self,path,role):
                    if role=='guard-clear':
                        self.armed=True;self.operations.append(('unlink',role))
                        if not guard_present:d.DiskIO.unlink(self,path,role)
                        if unlink_reported_error:raise OSError(errno.EIO,'guard unlink reported EIO')
                    else:super().unlink(path,role)
            io=StatFaultIO('unused','unused');flow.bridge.persistence.io=io
            def stat_fault(path,*args,**kwargs):
                if io.armed and os.fspath(path)==os.fspath(flow.bridge.persistence.guard):
                    io.armed=False;io.fired.append(('guard-lstat','EIO'))
                    raise OSError(errno.EIO,'postcommit guard stat EIO')
                return real_lstat(path,*args,**kwargs)
            with mock.patch.object(d.os,'lstat',side_effect=stat_fault):status,body=send_http(flow,record)
            self.assertEqual(status,200);self.assertTrue(body['accepted']);self.committed(flow,record,io,before)
            self.assertTrue(flow.bridge.persistence.retirement_pending);self.assertTrue(flow.bridge.persistence.ancillary)
            if guard_present:
                with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
                with self.assertRaises(d.PersistenceUncertain):d.TransactionStore(flow.bridge.output,flow.bridge.identity)
            else:
                self.assertEqual(replay.replay(flow.bridge.output)['sequence'],record['sequence'])
                self.assertFalse(d.TransactionStore(flow.bridge.output,flow.bridge.identity).uncertain)
            self.blocked_new_work(flow)
            self.receipt(flow,dict(kind='postcommit-stat-EIO-ACK200',http=status,body=body,guardPresent=guard_present,unlinkReportedError=unlink_reported_error,liveRetirementPending=True,operations=io.operations,fired=io.fired))

    def test_postcommit_directory_before_after_faults_block_live_work_but_offline_replay_accepts_ack(self):
        for mode in ['before','after']:
            flow,record,_=self.flow();io=FaultIO('postcommit-guard-directory',mode);flow.bridge.persistence.io=io
            status,body=send_http(flow,record);self.assertEqual(status,200);self.assertTrue(body['accepted']);self.committed(flow,record,io)
            self.assertTrue(flow.bridge.persistence.retirement_pending);self.assertFalse(d.unresolved(flow.bridge.output))
            self.assertFalse(d.TransactionStore(flow.bridge.output,flow.bridge.identity).uncertain)
            self.blocked_new_work(flow)
            flow.bridge.persistence.io=d.DiskIO();self.assertTrue(flow.bridge.persistence.resolve_retirement())
            self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
            self.receipt(flow,dict(kind='postcommit-directory-error-ACK200-positive-resolution',fault=mode,http=status,operations=io.operations,offlineReplayAllowed=True))

    def test_completed_setup_loses_credit_on_retirement_failure_until_positive_resolution(self):
        flow=f.Flow();self.addCleanup(flow.close);flow.before();flow.action();flow.observe('after-switch',value='1');flow.observe('terminal',value='1')
        for stage in ['terminate-before','terminate-after','test-case-finished','suite-finished']:flow.mark(stage)
        self.assertTrue(flow.bridge.settings.summary()['setupObservationSatisfied'])
        record=flow.record('mark',stage='bundle-finished',detail={});io=FaultIO('guard-clear','before-unlink');flow.bridge.persistence.io=io
        status,body=send_http(flow,record);self.assertEqual(status,200);self.assertTrue(body['accepted']);self.committed(flow,record,io)
        self.assertTrue(flow.bridge.settings.summary()['settingsEvidenceComplete']);self.assertFalse(flow.bridge.settings.summary()['setupObservationSatisfied'])
        summary=f.producer.summary('interaction',flow.bridge,0,None,[])
        self.assertFalse(summary['setupEvidenceComplete']);self.assertFalse(summary['diagnosticCompleted']);self.assertEqual(summary['persistenceRetirement']['state'],'unresolved')
        flow.bridge.persistence.io=d.DiskIO();self.assertTrue(flow.bridge.persistence.resolve_retirement())
        self.assertTrue(flow.bridge.settings.summary()['setupObservationSatisfied']);self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
        self.receipt(flow,dict(kind='complete-evidence-ACK200-setup-credit-blocked-until-positive-retirement',http=status,operations=io.operations,setupCreditBeforeResolution=False,setupCreditAfterResolution=True))

    def test_precommit_guard_stat_eio_rejects_without_cursor_or_journal_advance_then_retries(self):
        flow,record,_=self.flow();before=self.snapshot(flow);journals=self.journals(flow);real_lstat=os.lstat;fired=[]
        def stat_fault(path,*args,**kwargs):
            if not fired and os.fspath(path)==os.fspath(flow.bridge.persistence.guard):
                fired.append('precommit-guard-lstat-EIO');raise OSError(errno.EIO,'precommit guard stat EIO')
            return real_lstat(path,*args,**kwargs)
        with mock.patch.object(d.os,'lstat',side_effect=stat_fault):status,body=send_http(flow,record)
        self.assertEqual(status,400);self.assertEqual(before,self.snapshot(flow));self.assertEqual(journals,self.journals(flow))
        self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output));self.assertFalse(d.unresolved(flow.bridge.output))
        retry=send_http(flow,record);self.assertEqual(retry[0],200);self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
        self.receipt(flow,dict(kind='precommit-stat-EIO-reject-then-retry',http=[status,retry[0]],error=body['error'],fired=fired))

    def test_precommit_exact_publication_checks_fail_before_commit_and_remain_recoverable(self):
        for check in ['samefile','bytes']:
            flow,record,_=self.flow();before=self.snapshot(flow);journals=self.journals(flow);fired=[]
            real_same=os.path.samefile;real_read=pathlib.Path.read_bytes
            def samefile(a,b):
                if not fired:fired.append('publication-samefile-false');return False
                return real_same(a,b)
            def read_bytes(path):
                data=real_read(path)
                if not fired and path==flow.bridge.output/f"0000-settings-{record['sequence']:04d}.json":fired.append('publication-byte-mismatch');return data+b'x'
                return data
            with mock.patch.object(d.os.path,'samefile',side_effect=samefile) if check=='samefile' else mock.patch.object(pathlib.Path,'read_bytes',read_bytes):status,body=send_http(flow,record)
            self.assertEqual(status,400);self.assertIn('Published evidence identity differs',body['error']);self.assertTrue(fired)
            self.assertEqual(before,self.snapshot(flow));self.assertEqual(journals,self.journals(flow));self.assertFalse(d.unresolved(flow.bridge.output))
            self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output));retry=send_http(flow,record);self.assertEqual(retry[0],200)
            self.receipt(flow,dict(kind='precommit-exact-publication-rejection-retry',check=check,http=[status,retry[0]],fired=fired))

    def test_attempt_receipt_and_directory_actual_faults_preserve_commit_and_exact_replay(self):
        for role,mode in [('attempt-outcome','prewrite'),('attempt-outcome','partialwrite'),('attempt-outcome','filefsync-before'),('attempt-outcome','filefsync'),('attempt-outcome-directory','before'),('attempt-outcome-directory','after')]:
            flow,record,_=self.flow();io=FaultIO(role,mode);flow.bridge.persistence.io=io
            status,body=send_http(flow,record);self.assertEqual(status,200);self.assertTrue(body['accepted']);self.committed(flow,record,io)
            self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output));self.assertFalse(flow.bridge.persistence.retirement_pending)
            self.assertTrue(any(item['operation']=='attempt-outcome' for item in flow.bridge.persistence.ancillary));self.assertTrue(io.fired)
            self.receipt(flow,dict(kind='postcommit-attempt-receipt-error-ACK200',fault=[role,mode],http=status,operations=io.operations,fired=io.fired))

    def test_postcommit_retirement_and_receipt_reporting_wrappers_cannot_escape_commit(self):
        for method in ['resolve_retirement','_attempt_receipt']:
            flow,record,_=self.flow();io=FaultIO('unused','unused');flow.bridge.persistence.io=io
            with mock.patch.object(flow.bridge.persistence,method,side_effect=OSError('wrapper failure after irrevocable commit')):status,body=send_http(flow,record)
            self.assertEqual(status,200);self.assertTrue(body['accepted']);self.committed(flow,record,io);self.assertTrue(flow.bridge.persistence.ancillary)
            self.receipt(flow,dict(kind='postcommit-wrapper-error-ACK200',method=method,http=status,guardPresent=d.unresolved(flow.bridge.output),operations=io.operations))

    def test_terminal_precommit_guard_cannot_be_cleared_by_postcommit_retirement_api(self):
        flow,record,_=self.flow();before=self.snapshot(flow);io=FaultIO('publication-directory','before',('rollback-journal','before-unlink'));flow.bridge.persistence.io=io
        status,body=send_http(flow,record);self.assertEqual(status,400);self.assertEqual(before,self.snapshot(flow));self.assertTrue(d.unresolved(flow.bridge.output))
        flow.bridge.persistence.io=d.DiskIO();self.assertFalse(flow.bridge.persistence.resolve_retirement());self.assertTrue(d.unresolved(flow.bridge.output))
        with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
        self.receipt(flow,dict(kind='precommit-terminal-poison-not-resolvable-by-retirement-api',http=status,error=body['error'],operations=io.operations))


if __name__=='__main__':
    result=unittest.main(verbosity=2,exit=False).result
    (HERE/'persistence-controls.json').write_text(json.dumps(dict(schema='mixer.apple-keyboard.v9-persistence-controls.1',syntheticHostOnly=True,nativeExecuted=False,methodsRun=result.testsRun,passed=result.wasSuccessful(),controlCount=len(RESULTS),controls=RESULTS),indent=2,sort_keys=True)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
