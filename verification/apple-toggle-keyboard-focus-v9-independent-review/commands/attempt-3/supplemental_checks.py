"""Focused added controls after the passing matrix; does not repeat it."""
import json
import os
import pathlib
import stat
import traceback
from unittest import mock

import host_checks as h
import independent_flow as f
import durable_settings as d


def publication(check):
    flow,record=h.candidate('action','publication-exact-'+check)
    before=h.capture(flow)
    io=h.BoundaryIO();flow.bridge.persistence.io=io
    target=flow.bridge.output/f"0000-settings-{record['sequence']:04d}.json"
    fired=[]
    real_read=pathlib.Path.read_bytes;real_samefile=os.path.samefile
    def read(path):
        value=real_read(path)
        if path==target and not fired:
            fired.append('published-byte-comparison')
            return value+b'\x00'
        return value
    def samefile(left,right):
        if pathlib.Path(right)==target and not fired:
            fired.append('published-hardlink-comparison')
            return False
        return real_samefile(left,right)
    with mock.patch.object(pathlib.Path,'read_bytes',read) if check=='bytes' else mock.patch.object(d.os.path,'samefile',side_effect=samefile):
        status,body=flow.http(record)
    assert fired and status==400 and 'Published evidence identity differs' in body['error']
    rejected=h.capture(flow)
    assert before['state']==rejected['state'] and before['journals']==rejected['journals']
    assert not io.committed and not d.unresolved(flow.bridge.output)
    assert flow.bridge.settings.summary()==f.replay.replay(flow.bridge.output)
    flow.bridge.persistence.io=d.DiskIO()
    status2,body2=flow.http(record)
    assert status2==200 and body2['accepted']
    assert flow.bridge.settings.summary()==f.replay.replay(flow.bridge.output)
    h.persist_result(flow,dict(name='publication-exact-'+check,kind='exact-publication-check',
                     status=status,body=body,retryStatus=status2,fired=fired,
                     before=before,rejected=rejected,operations=io.operations))


def guard_fixture(kind):
    flow,record=h.candidate('action','guard-presence-'+kind)
    before=h.capture(flow)
    guard=flow.bridge.persistence.guard
    if kind=='dangling-symlink':
        guard.symlink_to(flow.bridge.output/'missing-guard-target')
    else:
        guard.write_bytes({'empty':b'','partial':b'{','complete':d.encoded({'independentFixture':True})}[kind])
    h.guarded_refusal(flow)
    status,body=flow.http(record)
    assert status==400 and 'PersistenceUncertain' in body['error']
    assert before['state']==h.state(flow) and before['journals']==h.capture(flow)['journals']
    assert flow.bridge.settings.summary()['persistenceUncertain']
    assert not flow.bridge.persistence.resolve_retirement()
    h.persist_result(flow,dict(name='guard-presence-'+kind,kind='guard-refusal',status=status,body=body,
                     before=before,fixture=kind,replayAndStartupRefused=True))


def actual_summary_io(mode):
    flow,record=h.candidate('action','actual-summary-'+mode)
    before=h.capture(flow)
    io=h.BoundaryIO();flow.bridge.persistence.io=io
    original_summary=flow.bridge.persist_summary
    real_fsync=os.fsync;real_replace=os.replace
    active=[False];fired=[];operations=[]
    def summary():
        active[0]=True
        try:return original_summary()
        finally:active[0]=False
    def fsync(fd):
        role='directory-fsync' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file-fsync'
        if active[0]:operations.append(role)
        if active[0] and mode==role+'-before' and not fired:
            fired.append(mode)
            raise OSError('independent actual summary '+mode)
        result=real_fsync(fd)
        if active[0] and mode==role+'-after' and not fired:
            fired.append(mode)
            raise OSError('independent actual summary '+mode)
        return result
    def replace(source,destination):
        targeted=active[0] and pathlib.Path(destination)==flow.bridge.output/'bridge-summary.json'
        if targeted:operations.append('replace')
        if targeted and mode=='replace-before' and not fired:
            fired.append(mode)
            raise OSError('independent actual summary '+mode)
        result=real_replace(source,destination)
        if targeted and mode=='replace-after' and not fired:
            fired.append(mode)
            raise OSError('independent actual summary '+mode)
        return result
    with mock.patch.object(flow.bridge,'persist_summary',side_effect=summary),mock.patch.object(os,'fsync',side_effect=fsync),mock.patch.object(os,'replace',side_effect=replace):
        status,body=flow.http(record)
    assert fired and status==200 and body['accepted'],(status,body,fired)
    committed=h.capture(flow)
    assert committed['sequence']==record['sequence'] and io.committed
    assert committed['ancillaryFailures'] and committed['warnings']
    assert not committed['summary']['persistenceUncertain']
    assert flow.bridge.settings.summary()==f.replay.replay(flow.bridge.output)
    assert not any('rollback' in role for _,role in io.operations)
    assert all(committed['journals'][k]==v for k,v in before['journals'].items())
    h.persist_result(flow,dict(name='actual-summary-'+mode,kind='actual-summary-filesystem-error',
                     status=status,body=body,before=before,committed=committed,
                     committedSequence=record['sequence'],fired=fired,
                     summaryOperations=operations,persistenceOperations=io.operations))


def run():
    publication('bytes');publication('hardlink')
    for kind in ['empty','partial','complete','dangling-symlink']:
        guard_fixture(kind)
    for mode in ['file-fsync-before','file-fsync-after','replace-before','replace-after','directory-fsync-before','directory-fsync-after']:
        actual_summary_io(mode)


if __name__=='__main__':
    failure=None
    try:run()
    except BaseException:
        failure=traceback.format_exc();print(failure)
    result=dict(schema='mixer.apple-keyboard.v9-independent-supplemental-controls.1',passed=failure is None,
                controlCount=len(h.RESULTS),controls=h.RESULTS,failure=failure,
                syntheticHostOnly=True,nativeExecuted=False,nativeInstancesQueried=False)
    (f.HERE/'supplemental-controls.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(passed=failure is None,controlCount=len(h.RESULTS),actualHTTPRequests=sum(x['requestCount'] for x in h.RESULTS))))
    raise SystemExit(1 if failure else 0)
