#!/usr/bin/env python3
"""Reproduce post-write persistence boundaries in actual V7 code; retain evidence."""
import copy
import json
import pathlib
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
    f=h.Flow('postwrite-journal'); f.before(); r=f.action(send=False); before=capture(f); save=f.bridge.save
    def write_then_fail(*args):
        save(*args)
        if args[0].startswith('settings-'): raise OSError('independent directory fsync failure after real journal write')
    with mock.patch.object(f.bridge,'save',side_effect=write_then_fail):
        failure=error(lambda:f.send(r))
    after=capture(f); replayed=h.replay.replay(f.bridge.output); retry=error(lambda:f.send(r))
    assert failure is not None and before['sequence']==after['sequence'] and len(after['journalFiles'])==len(before['journalFiles'])+1
    assert replayed['sequence']==r['sequence'] and replayed['switchAction']=='tap'
    assert retry is not None and 'Evidence file already exists' in retry['message']
    findings.append(dict(id='PERSIST-POSTWRITE-JOURNAL',status='reproduced',failure=failure,retryFailure=retry,before=before,after=after,replayAfterFailure=replayed,
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
    with mock.patch.object(f.bridge,'persist_summary',side_effect=OSError('independent postcommit summary failure')):
        failure=error(lambda:f.send(r))
    after=capture(f); replayed=h.replay.replay(f.bridge.output)
    assert failure is not None and after['sequence']==r['sequence'] and after['sequence']>before['sequence']
    assert after['summary']==replayed
    findings.append(dict(id='PERSIST-ACK-SUMMARY',status='reproduced',failure=failure,before=before,after=after,replayAfterFailure=replayed,
                         consequence='Actual Bridge request raises a persistence error after Session cursor/action commit; rejection does not retain the prior accepted cursor.'))
    result=dict(schema='mixer.apple-toggle.keyboard-v7-independent-persistence-probes.1',syntheticHostOnly=True,nativeExecuted=False,findings=findings,
                strictRollbackContractSatisfied=False,scope='Actual sealed Bridge and Session; isolated synthetic folders; no production or native writes')
    (h.HERE/'persistence-probes.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(reproduced=[f['id'] for f in findings],strictRollbackContractSatisfied=False)))


if __name__=='__main__':main()
