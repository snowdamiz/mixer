"""New independent adversarial guard-absence probe; actual loopback HTTP."""
import errno
import json
import os
from unittest import mock
import independent_flow as f
import durable_settings as d


def capture(flow):
    return dict(sequence=flow.bridge.settings.sequence, state=flow.state(), summary=flow.bridge.settings.summary(), journals={name:f.t.sha(data) for name,data in flow.journal().items()})


def run():
    flow=f.Flow('guard-cleared-stat-eio-rollback-journal-failure')
    flow.before(); record=flow.action(send=False); before=capture(flow)
    real_lstat=os.lstat
    class GuardThenRollbackFault(d.DiskIO):
        def __init__(self):self.arm=False;self.fired=[];self.operations=[]
        def unlink(self,path,role):
            self.operations.append(['unlink',role])
            if role=='rollback-journal':
                self.fired.append('rollback-journal-unlink-EIO')
                raise OSError(errno.EIO,'independent rollback journal unlink failure')
            super().unlink(path,role)
            if role=='guard-clear':
                self.arm=True
                self.fired.append('actual-guard-unlinked')
    io=GuardThenRollbackFault();flow.bridge.persistence.io=io
    def stat_fault(path,*args,**kwargs):
        if io.arm and os.fspath(path)==os.fspath(flow.bridge.persistence.guard):
            io.arm=False
            io.fired.append('guard-lstat-EIO-after-actual-unlink')
            raise OSError(errno.EIO,'independent lstat EIO after actual guard unlink')
        return real_lstat(path,*args,**kwargs)
    with mock.patch.object(d.os,'lstat',side_effect=stat_fault):
        status,body=flow.http(record)
    after=capture(flow)
    guard_present=d.unresolved(flow.bridge.output)
    replayed=f.replay.replay(flow.bridge.output)
    flow.bridge.persistence.io=d.DiskIO()
    retry=flow.http(record)
    restart=d.TransactionStore(flow.bridge.output,flow.bridge.identity)
    assert status==400 and 'PersistenceUncertain' in body['error']
    assert before['state']==after['state'] and before['sequence']==19 and after['sequence']==19
    assert not guard_present and after['summary']['persistenceUncertain']
    assert replayed['sequence']==20 and replayed['switchAction']=='tap' and not replayed['persistenceUncertain']
    result=dict(schema='mixer.apple-keyboard.v8-independent-guard-absence-probe.1', finding='PERSIST-GUARD-ABSENCE-ROLLBACK', reproduced=True, syntheticHostOnly=True, nativeExecuted=False,
                record=record,httpStatus=status,httpBody=body,before=before,after=after,guardPresent=guard_present,replayAfterRejection=replayed,
                liveRetry=dict(status=retry[0],body=retry[1]),freshTransactionStoreAllowed=not restart.uncertain,faults=io.fired,operations=io.operations,
                uncertainty=flow.bridge.persistence.uncertainty,hostEvidence=str(flow.root.relative_to(f.ROOT)))
    (f.HERE/'guard-absence-probe.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(reproduced=True,httpStatus=status,liveSequence=after['sequence'],replaySequence=replayed['sequence'],guardPresent=guard_present,freshTransactionStoreAllowed=not restart.uncertain)))

if __name__=='__main__':run()
