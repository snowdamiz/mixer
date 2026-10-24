"""Independent V9 actual HTTP / filesystem boundary controls; no native execution."""
import base64
import copy
import errno
import json
import os
import pathlib
import traceback
from unittest import mock

import independent_flow as f
import durable_settings as d

RESULTS = []


class BoundaryIO(d.DiskIO):
    def __init__(self, fault=None, stat_eio=False, rollback_trap=False):
        self.fault = fault
        self.stat_eio = stat_eio
        self.rollback_trap = rollback_trap
        self.committed = False
        self.operations = []
        self.fired = []

    def hit(self, role, mode):
        key = [role, mode]
        if self.fault == (role, mode) and key not in self.fired:
            self.fired.append(key)
            return True
        return False

    def write(self, path, data, role):
        self.operations.append(['write', role])
        if self.hit(role, 'before'):
            raise OSError(errno.EIO, 'independent before write ' + role)
        if self.hit(role, 'partial'):
            original = os.write
            calls = [0]
            def partial(fd, value):
                calls[0] += 1
                if calls[0] == 1:
                    return original(fd, value[:max(1, len(value)//2)])
                raise OSError(errno.EIO, 'independent failure after actual partial write ' + role)
            with mock.patch.object(d.os, 'write', side_effect=partial):
                return super().write(path, data, role)
        if self.hit(role, 'fsync-before'):
            with mock.patch.object(d.os, 'fsync', side_effect=OSError(errno.EIO, 'independent before file fsync ' + role)):
                return super().write(path, data, role)
        if self.hit(role, 'fsync-after'):
            original = os.fsync
            def synced(fd):
                original(fd)
                raise OSError(errno.EIO, 'independent after real file fsync ' + role)
            with mock.patch.object(d.os, 'fsync', side_effect=synced):
                return super().write(path, data, role)
        super().write(path, data, role)

    def sync(self, path, role):
        self.operations.append(['sync', role])
        if self.hit(role, 'before'):
            raise OSError(errno.EIO, 'independent before directory fsync ' + role)
        super().sync(path, role)
        if self.hit(role, 'after'):
            raise OSError(errno.EIO, 'independent after real directory fsync ' + role)
        if role == 'publication-directory':
            self.committed = True

    def publish(self, staged, final, role):
        self.operations.append(['publish', role])
        if self.hit(role, 'publish-before'):
            raise OSError(errno.EIO, 'independent before publication ' + role)
        super().publish(staged, final, role)
        if self.hit(role, 'publish-after'):
            raise OSError(errno.EIO, 'independent after real publication ' + role)

    def unlink(self, path, role):
        self.operations.append(['unlink', role])
        if role == 'rollback-journal' and self.rollback_trap:
            self.fired.append(['rollback-journal', 'EIO'])
            raise OSError(errno.EIO, 'independent V8 rollback journal unlink failure')
        if self.hit(role, 'before'):
            raise OSError(errno.EIO, 'independent before unlink ' + role)
        if self.hit(role, 'noop'):
            return
        super().unlink(path, role)
        if role == 'guard-clear':
            self.fired.append(['guard-clear', 'actual-unlink'])
        if self.hit(role, 'after'):
            raise OSError(errno.EIO, 'independent after real unlink ' + role)


def state(flow):
    return copy.deepcopy(flow.state())


def capture(flow):
    return dict(sequence=flow.bridge.settings.sequence, state=state(flow),
                summary=flow.bridge.settings.summary(),
                journals={name:f.t.sha(value) for name,value in flow.journal().items()},
                warnings=copy.deepcopy(flow.bridge.persistence.ancillary),
                retirement=copy.deepcopy(flow.bridge.persistence.retirement),
                ancillaryFailures=copy.deepcopy(flow.bridge.ancillary_failures))


def protocol(summary):
    return {k:v for k,v in summary.items() if k not in ['persistenceRetirementPending', 'persistenceUncertain']}


def guarded_refusal(flow):
    for label, call in [('replay', lambda:f.replay.replay(flow.bridge.output)),
                        ('startup', lambda:d.TransactionStore(flow.bridge.output, flow.bridge.identity))]:
        try:
            call()
        except d.PersistenceUncertain:
            continue
        raise AssertionError(label + ' allowed a present transaction guard')


def candidate(kind, name):
    flow = f.Flow(name)
    flow.payloads = None
    if kind == 'upload':
        flow.routes()
        record, payloads = flow.observation('before-switch')
        flow.send(record)
        flow.payloads = payloads
        return flow, next(flow.chunks(payloads))
    flow.before()
    return flow, flow.action(send=False)


def next_valid(flow):
    if flow.bridge.settings.pending:
        return next(flow.chunks(flow.payloads))
    return flow.observation('after-switch', value='1')[0]


def blocked_and_resolved(flow):
    record = next_valid(flow)
    before = capture(flow)
    status, body = flow.http(record)
    assert status == 400 and 'PersistenceUncertain' in body['error'], (status, body)
    assert before['state'] == state(flow) and before['journals'] == capture(flow)['journals']
    flow.bridge.persistence.io = d.DiskIO()
    assert flow.bridge.persistence.resolve_retirement()
    assert not flow.bridge.persistence.retirement_pending and not flow.bridge.persistence.uncertain
    assert flow.bridge.persistence.ancillary, 'Retirement history disappeared'
    assert flow.bridge.settings.summary() == f.replay.replay(flow.bridge.output)
    retry_status, retry_body = flow.http(record)
    assert retry_status == 200 and retry_body['accepted'], (retry_status, retry_body)
    assert flow.bridge.settings.summary() == f.replay.replay(flow.bridge.output)
    return dict(blockedStatus=status, blockedBody=body, resolutionSucceeded=True,
                validNextRetryStatus=retry_status, finalSequence=flow.bridge.settings.sequence)


def persist_result(flow, detail):
    value = dict(detail, syntheticHostOnly=True, nativeExecuted=False,
                 httpRequests=flow.http_requests, final=capture(flow))
    path = flow.root/'independent-control.json'
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
    RESULTS.append(dict(name=detail['name'], passed=True, path=str(path.relative_to(f.HERE)),
                        sha256=f.t.sha(path.read_bytes()), requestCount=len(flow.http_requests),
                        testedHTTPStatus=detail.get('status'), committedSequence=detail.get('committedSequence')))


def postcommit(name, kind='action', fault=None, stat_eio=False, pending=False,
               rollback_trap=False, wrapper=None, summary_failure=False):
    flow, record = candidate(kind, name)
    before = capture(flow)
    io = BoundaryIO(fault, stat_eio, rollback_trap)
    flow.bridge.persistence.io = io
    real_lstat = os.lstat
    def lstat(path, *args, **kwargs):
        if io.committed and io.stat_eio and os.fspath(path) == os.fspath(flow.bridge.persistence.guard):
            io.stat_eio = False
            io.fired.append(['guard-lstat', 'EIO-after-irrevocable-commit'])
            raise OSError(errno.EIO, 'independent guard lstat EIO after commit')
        return real_lstat(path, *args, **kwargs)
    with mock.patch.object(d.os, 'lstat', side_effect=lstat):
        with mock.patch.object(flow.bridge.persistence, wrapper, side_effect=OSError(errno.EIO, 'independent reporting wrapper')) if wrapper else mock.patch.dict({}, {}):
            with mock.patch.object(flow.bridge, 'persist_summary', side_effect=OSError(errno.EIO, 'independent summary failure')) if summary_failure else mock.patch.dict({}, {}):
                status, body = flow.http(record)
    committed = capture(flow)
    assert io.committed and status == 200 and body['accepted'], (status, body)
    assert committed['sequence'] == record['sequence']
    assert len(committed['journals']) == record['sequence']+1
    assert all(committed['journals'][key] == value for key,value in before['journals'].items())
    assert json.loads((flow.bridge.output/f"0000-settings-{record['sequence']:04d}.json").read_bytes())['record'] == record
    assert not any('rollback' in role for _,role in io.operations), io.operations
    assert not any(role == 'rollback-journal' for role,mode in io.fired), io.fired
    assert flow.bridge.persistence.retirement_pending == pending
    assert flow.bridge.persistence.uncertain == pending
    guard = d.unresolved(flow.bridge.output)
    replayed = None
    if guard:
        guarded_refusal(flow)
    else:
        replayed = f.replay.replay(flow.bridge.output)
        assert protocol(replayed) == protocol(committed['summary'])
        assert not d.TransactionStore(flow.bridge.output, flow.bridge.identity).uncertain
    if fault is not None:
        assert list(fault) in io.fired, io.fired
    if stat_eio:
        assert ['guard-lstat', 'EIO-after-irrevocable-commit'] in io.fired
    if fault or stat_eio or wrapper or summary_failure:
        assert committed['warnings'] or committed['ancillaryFailures']
    continuation = blocked_and_resolved(flow) if pending else None
    persist_result(flow, dict(name=name, kind='postcommit', requestKind=kind, fault=fault,
                   status=status, body=body, before=before, committed=committed,
                   committedSequence=record['sequence'], guardPresentAfterACK=guard,
                   offlineReplayAfterACK=replayed, liveRetirementPendingAfterACK=pending,
                   retirementContinuation=continuation, operations=io.operations, fired=io.fired,
                   rollbackFaultArmed=rollback_trap, noRollback=True))


def precommit(name, fault, kind='action', terminal=False):
    flow, record = candidate(kind, name)
    before = capture(flow)
    io = BoundaryIO(fault, rollback_trap=terminal)
    flow.bridge.persistence.io = io
    status, body = flow.http(record)
    rejected = capture(flow)
    assert status == 400 and before['state'] == rejected['state'], (status,body)
    assert not io.committed
    if terminal:
        assert flow.bridge.persistence.uncertain and d.unresolved(flow.bridge.output)
        guarded_refusal(flow)
        flow.bridge.persistence.io = d.DiskIO()
        assert not flow.bridge.persistence.resolve_retirement()
        assert d.unresolved(flow.bridge.output)
        status2, body2 = flow.http(record)
        assert status2 == 400 and 'PersistenceUncertain' in body2['error']
    else:
        assert before['journals'] == rejected['journals'] and not d.unresolved(flow.bridge.output)
        assert flow.bridge.settings.summary() == f.replay.replay(flow.bridge.output)
        flow.bridge.persistence.io = d.DiskIO()
        status2, body2 = flow.http(record)
        assert status2 == 200 and body2['accepted']
        assert flow.bridge.settings.summary() == f.replay.replay(flow.bridge.output)
    assert list(fault) in io.fired
    persist_result(flow, dict(name=name, kind='precommit', requestKind=kind, fault=fault,
                   status=status, body=body, before=before, rejected=rejected,
                   retryStatus=status2, terminal=terminal, operations=io.operations, fired=io.fired))


def full_setup_retirement(name, fault):
    flow = f.Flow(name)
    flow.before(); flow.action(); flow.observe('after-switch', '1'); flow.observe('terminal', '1')
    for stage in ['terminate-before','terminate-after','test-case-finished','suite-finished']:
        flow.mark(stage)
    record = flow.record('mark', stage='bundle-finished', detail={})
    io = BoundaryIO(fault); flow.bridge.persistence.io = io
    status, body = flow.http(record)
    summary = flow.bridge.settings.summary()
    runtime = f.p.summary('interaction', flow.bridge, 0, None, [])
    assert status == 200 and body['accepted'] and summary['settingsEvidenceComplete']
    assert summary['persistenceUncertain'] and summary['persistenceRetirementPending']
    assert not summary['setupObservationSatisfied']
    assert not runtime['setupEvidenceComplete'] and not runtime['diagnosticCompleted']
    guard = d.unresolved(flow.bridge.output)
    if guard:
        guarded_refusal(flow)
    else:
        replayed = f.replay.replay(flow.bridge.output)
        assert protocol(replayed) == protocol(summary) or (replayed['setupObservationSatisfied'] and not summary['setupObservationSatisfied'])
        # The only qualification difference is retirement-induced setup credit.
        assert {k:v for k,v in protocol(replayed).items() if k != 'setupObservationSatisfied'} == {k:v for k,v in protocol(summary).items() if k != 'setupObservationSatisfied'}
        assert replayed['setupObservationSatisfied']
    flow.bridge.persistence.io = d.DiskIO()
    assert flow.bridge.persistence.resolve_retirement()
    assert flow.bridge.settings.summary()['setupObservationSatisfied']
    assert f.p.summary('interaction',flow.bridge,0,None,[])['setupEvidenceComplete']
    persist_result(flow,dict(name=name,kind='complete-setup-disqualification',status=status,body=body,
                   summaryWhilePending=summary,runtimeWhilePending=runtime,guardPresentAfterACK=guard,
                   operations=io.operations,fired=io.fired,committedSequence=record['sequence']))


def run():
    postcommit('baseline-action')
    postcommit('baseline-payload', kind='upload')
    postcommit('exact-v8-real-unlink-lstat-eio-rollback-eio', stat_eio=True, pending=True, rollback_trap=True)
    for kind in ['action','upload']:
        for label,fault,stat_eio,pending in [
            ('unlink-before',('guard-clear','before'),False,True),
            ('unlink-after',('guard-clear','after'),False,False),
            ('unlink-noop',('guard-clear','noop'),False,True),
            ('stat-absent',None,True,True),
            ('stat-present',('guard-clear','before'),True,True),
            ('stat-after-reported-unlink',('guard-clear','after'),True,True),
            ('retirement-fsync-before',('postcommit-guard-directory','before'),False,True),
            ('retirement-fsync-after',('postcommit-guard-directory','after'),False,True)]:
            postcommit(kind+'-'+label,kind,fault,stat_eio,pending)
    for role,modes in [('attempt-outcome',['before','partial','fsync-before','fsync-after']),
                       ('attempt-outcome-directory',['before','after'])]:
        for mode in modes:
            postcommit(role+'-'+mode,fault=(role,mode))
    for method,pending in [('resolve_retirement',True),('_attempt_receipt',False)]:
        postcommit('wrapper-'+method,wrapper=method,pending=pending)
    postcommit('summary-wrapper',summary_failure=True)
    for role,modes in [('ancillary',['before','partial','fsync-before','fsync-after']),('ancillary-directory',['before','after'])]:
        for mode in modes:
            postcommit('summary-and-'+role+'-'+mode,fault=(role,mode),summary_failure=True)
    for kind in ['action','upload']:
        for role,modes in [('guard',['partial','fsync-after']),('journal',['partial','fsync-before','fsync-after','publish-before','publish-after']),('publication-directory',['before','after'])]:
            for mode in modes:
                precommit(kind+'-'+role+'-'+mode,(role,mode),kind)
    for mode in ['partial','fsync-before','fsync-after','publish-before','publish-after']:
        precommit('upload-payload-'+mode,('payload',mode),'upload')
    precommit('terminal-publication-error-rollback-journal-EIO',('publication-directory','after'),terminal=True)
    full_setup_retirement('complete-setup-guard-present',('guard-clear','before'))
    full_setup_retirement('complete-setup-guard-absent-dirsync-failure',('postcommit-guard-directory','after'))


if __name__ == '__main__':
    failure = None
    try:
        run()
    except BaseException:
        failure = traceback.format_exc()
        print(failure)
    result = dict(schema='mixer.apple-keyboard.v9-independent-controls.1',passed=failure is None,
                  controlCount=len(RESULTS),controls=RESULTS,failure=failure,
                  syntheticHostOnly=True,nativeExecuted=False,nativeInstancesQueried=False)
    (f.HERE/'independent-controls.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],controlCount=len(RESULTS),actualHTTPRequests=sum(x['requestCount'] for x in RESULTS))))
    raise SystemExit(1 if failure else 0)
