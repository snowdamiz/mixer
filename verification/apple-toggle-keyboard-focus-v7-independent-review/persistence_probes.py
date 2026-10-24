#!/usr/bin/env python3
"""Reproduce post-write persistence boundaries in actual V7 code; retain evidence."""
import copy
import json
import os
import pathlib
import stat
import threading
import http.client
from unittest import mock
import host_checks as h


def error(call):
    try:
        call()
        return None
    except (ValueError, OSError) as e:
        return {'type':type(e).__name__, 'message':str(e)}


def capture(f):
    return dict(sequence=f.bridge.settings.sequence, requests=f.bridge.settings.requests, anchor=f.bridge.settings.anchor, action=f.bridge.settings.action,
                journalFiles={name:h.t.sha(data) for name,data in f.journal().items()}, summary=f.bridge.settings.summary())


def main():
    findings=[]
    # The real save writes/fsyncs the request record before the containing
    # persist closure fsyncs the output directory. Simulate that directory fsync
    # failing while the actual regular-file write has completed.
    f=h.Flow('postwrite-journal'); f.before(); r=f.action(send=False); before=capture(f); real_fsync=os.fsync; injected=[]
    expected_journal=f.bridge.output/(f"0000-settings-{r['sequence']:04d}.json")
    def fsync_then_fail(fd):
        if not injected and stat.S_ISDIR(os.fstat(fd).st_mode):
            assert expected_journal.is_file() and json.loads(expected_journal.read_bytes())['record']==r
            injected.append(dict(descriptorType='directory',afterJournalFileWrite=True,journalSHA256=h.t.sha(expected_journal.read_bytes())))
            raise OSError('independent directory fsync failure after real journal write')
        return real_fsync(fd)
    with mock.patch.object(h.t.os,'fsync',side_effect=fsync_then_fail):
        failure=error(lambda:f.send(r))
    after=capture(f); replayed=h.replay.replay(f.bridge.output); retry=error(lambda:f.send(r))
    assert failure is not None and before['sequence']==after['sequence'] and len(after['journalFiles'])==len(before['journalFiles'])+1
    assert replayed['sequence']==r['sequence'] and replayed['switchAction']=='tap'
    assert retry is not None and 'Evidence file already exists' in retry['message']
    findings.append(dict(id='PERSIST-POSTWRITE-JOURNAL',status='reproduced',failure=failure,faultInjection=injected,retryFailure=retry,before=before,after=after,replayAfterFailure=replayed,
                         consequence='Rejected request leaves a new durable journal record and replays as accepted; same-sequence retry fails on the existing journal filename. No setup pass follows this partial flow.'))

    # Final-chunk payload is persisted before its journal record. A selected
    # prewrite journal failure leaves an orphan final file and prevents retry.
    f=h.Flow('payload-before-journal'); f.routes(); record,payloads=f.observation('before-switch'); f.send(record)
    first=next(f.chunks(payloads)); before=capture(f)
    with mock.patch.object(f.bridge,'save',side_effect=OSError('independent journal failure after final payload write')):
        failure=error(lambda:f.send(first))
    after=capture(f); artifact=f.bridge.output/(first['slot']+'.txt'); assert artifact.is_file()
    replayed=h.replay.replay(f.bridge.output); retry=error(lambda:f.send(first))
    assert failure is not None and before==after and retry is not None and 'Fixed fresh telemetry artifact' in retry['message']
    findings.append(dict(id='PERSIST-PAYLOAD-ORPHAN',status='reproduced',failure=failure,retryFailure=retry,before=before,after=after,replayAfterFailure=replayed,
                         orphanArtifact=str(artifact.relative_to(h.ROOT)),orphanSHA256=h.t.sha(artifact.read_bytes()),
                         consequence='In-memory state and journal prefix roll back, but a final payload survives rejection; retry of that pending chunk cannot complete.'))

    # Bridge.request persists its outer summary after Session.request commits.
    # A summary fsync failure reports rejection with an already-advanced cursor.
    f=h.Flow('ack-summary'); f.before(); r=f.action(send=False); before=capture(f)
    server=h.p.h.server_for(f.bridge);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
    try:
        with mock.patch.object(f.bridge,'persist_summary',side_effect=OSError('independent postcommit summary failure')):
            client.request('POST','/evaluate',body=json.dumps({'settingsDiagnostic':r}).encode(),headers={'Content-Type':'application/json','X-Mixer-Capability':'independent-synthetic-capability'})
            response=client.getresponse();status=response.status;body=response.read().decode()
        failure=json.loads(body)
    finally:client.close();server.shutdown();server.server_close();thread.join(3);assert not thread.is_alive()
    after=capture(f); replayed=h.replay.replay(f.bridge.output)
    assert status==400 and 'independent postcommit summary failure' in failure['error'] and after['sequence']==r['sequence'] and after['sequence']>before['sequence']
    assert after['summary']==replayed
    findings.append(dict(id='PERSIST-ACK-SUMMARY',status='reproduced',httpStatus=status,httpBody=failure,before=before,after=after,replayAfterFailure=replayed,
                         consequence='Protocol journal and Session commit succeeded and replay agree, but ancillary Bridge summary persistence failure replaces the success ACK with HTTP 400. This is a postcommit ACK failure, distinct from journal rollback.'))
    result=dict(schema='mixer.apple-toggle.keyboard-v7-independent-persistence-probes.1',syntheticHostOnly=True,nativeExecuted=False,findings=findings,
                strictRollbackContractSatisfied=False,scope='Actual sealed Bridge and Session; isolated synthetic folders; no production or native writes')
    (h.HERE/'persistence-probes.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(reproduced=[f['id'] for f in findings],strictRollbackContractSatisfied=False)))


if __name__=='__main__':main()
