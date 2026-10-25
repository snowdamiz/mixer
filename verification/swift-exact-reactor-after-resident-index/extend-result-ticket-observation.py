#!/usr/bin/env python3
"""Seal a requested observation from existing evidence; preserve predecessor bytes."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-exact-reactor-after-cache'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

assert not (HERE / 'result-seal-initial.json').exists(), 'one extension; preserve predecessor'
initial = read(HERE / 'result-seal.json')
assert sha(HERE / 'result-seal.json') == '6a42a4329fe1a0d6a3590e51fa7e4a4969d9becd1e5dc4a6f559334a1d5e3d57'
for name, digest in initial['files'].items():
    assert sha(HERE / name) == digest, name
for name, digest in initial['externalFiles'].items():
    assert sha(ROOT / name) == digest, name
(HERE / 'result-seal-initial.json').write_bytes((HERE / 'result-seal.json').read_bytes())
before = read(OLD / 'target-once-events.json')
after = read(HERE / 'target-once-events.json')
rows = []
for name in ['constructed','initialize','runtime_failure']:
    row = {'event':name}
    for key, events in [('before',before),('after',after)]:
        p = next(e['payload'] for e in events if e['event'] == name)
        u = p['at_failure'] if name == 'runtime_failure' else p['usage']
        row[key] = {'liveTickets':u['reservations']['live_tickets'], 'peakTickets':u['reservations']['peak_tickets'],
                    'cacheEntries':u['live']['cache_entries']['current'], 'activePins':u['live']['active_pins']['current'],
                    'frames':u['live']['frames']['current'], 'instructions':u['instructions'],
                    'cacheWork':u['cache_work'], 'unusedTicketCapacity':86-u['reservations']['live_tickets']}
    rows.append(row)
source_evidence = []
for path, ranges in [
    (OLD / 'baseline/src/experimental_swift_reactor/cache.rs',[(129,134),(1641,1680)]),
    (HERE / 'baseline/src/experimental_swift_reactor/cache.rs',[(242,248),(1816,1833)]),
    (HERE / 'baseline/src/experimental_swift_reactor/control.rs',[(15,15),(986,1010)])]:
    lines = path.read_text().splitlines()
    source_evidence.append({'path':str(path.relative_to(ROOT)), 'sha256':sha(path),
        'excerpts':[{'start':a,'end':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
assert 'buffers: [Option<ReservationTicket>; 3]' in (OLD / 'baseline/src/experimental_swift_reactor/cache.rs').read_text()
assert 'buffers: [Option<ReservationTicket>; 4]' in (HERE / 'baseline/src/experimental_swift_reactor/cache.rs').read_text()
assert 'partial.buffers[3] = Some(self.control.admit(RESIDENT_INDEX_BYTES)?);' in (HERE / 'baseline/src/experimental_swift_reactor/cache.rs').read_text()
assert (OLD / 'baseline/src/experimental_swift_reactor/control.rs').read_bytes() == (HERE / 'baseline/src/experimental_swift_reactor/control.rs').read_bytes()
save('ticket-headroom-observation.json', {
    'schema':1, 'status':'source-bound-observation-only-no-new-execution',
    'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'beforeEvents':{'path':str((OLD / 'target-once-events.json').relative_to(ROOT)), 'sha256':sha(OLD / 'target-once-events.json')},
    'afterEvents':{'path':str((HERE / 'target-once-events.json').relative_to(ROOT)), 'sha256':sha(HERE / 'target-once-events.json')},
    'sourceEvidence':source_evidence, 'snapshots':rows, 'ticketLimit':86,
    'persistentBufferTicketDelta':1, 'sourceSupportedDelta':'resident-index Vec<u8> has one additional persistent admitted buffer ticket',
    'requesting87thTicketOwnerObserved':False,
    'failureOwnerScope':'Invocation cursor function79548 offset15881589 is observed; the requesting reservation owner/category/bytes are not emitted by the unchanged observer',
    'unequalFailurePrefixesComparableForPerformance':False,
    'repairSelected':False, 'resourceLimitExpansionSelected':False, 'newTargetExecution':False,
    'instrumentationChanged':False, 'targetAttempts':1})
(HERE / 'ticket-headroom-observation.md').write_text('''# Existing ticket headroom observations

This supplement compares immutable snapshots already collected by the unchanged
original harness. No target, compiler, oracle or instrumentation is rerun. The
first result report, receipt and seal retain their bytes; the final seal binds
this supplement and the preserved predecessor `result-seal-initial.json`.

| Existing phase snapshot | Before resident index: live / peak tickets | After resident index: live / peak tickets | Resident cache entries before / after | Unused ticket capacity before / after |
| --- | ---: | ---: | ---: | ---: |
| Constructed | 21 / 21 | 22 / 22 | 0 / 0 | 65 / 64 |
| Initialize complete | 85 / 85 | 86 / 86 | 64 / 64 | 1 / 0 |
| First typed failure | 85 / 86 | 86 / 86 | 64 / 64 | 1 / 0 |

The source-backed persistent accounting delta is one buffer ticket. The frozen
before cache has three buffer-ticket slots; the integrated cache has four. Its
new `buffers[3]` admits the 192-byte resident-index vector before reserving and
initializing that vector. The original shared ticket admission implementation and
`MAX_RESERVATION_TICKETS = 86` are byte-identical before and after integration.
The constructor and completed Initialize observations each increase by one live
ticket. At the new completed Initialize snapshot the entire 86-ticket inventory
is occupied. These are observed snapshot counts and a source-supported allocation
delta; they do not identify the actual next requesting ticket owner.

The earlier failure is CacheWork exhaustion at 12,971,689 guest instructions,
64,000,000 cache work, seven frames and eight active pins. The new failure is
TicketInventory exhaustion at 6,555,490 guest instructions, 31,475,443 cache work,
12 frames and 12 active pins. These are different execution prefixes. The failure
snapshots cannot establish a performance improvement or equal-prefix ticket
behavior. The current failure cursor is Invocation, function 79,548, source offset
15,881,589; the unchanged observer emits no requesting reservation category,
owner identity or requested bytes. Its 87th ticket request therefore remains
unattributed. The failed admission does not create the refused ticket.

The existing new run's final consuming snapshot still has all current reservation
and live categories/tickets at zero, with no cleanup invariant. This supplement
does not select a repair, expand the ticket limit, alter accounting or qualify a
new full-target run. Any fixed-storage or ticket-headroom diagnosis is separate.

`ticket-headroom-observation.json` binds exact old/new event hashes, snapshot
values and frozen source excerpts. Check this observation read-only with:

```sh
python3 -B verification/swift-exact-reactor-after-resident-index/verify-ticket-headroom.py
```
''')
files = {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name != 'result-seal.json'}
for name, digest in initial['files'].items():
    assert files[name] == digest, name
save('result-seal.json', {**initial, 'files':files, 'priorResultSealSHA256':sha(HERE / 'result-seal-initial.json'),
    'supplement':'ticket-headroom-observation.json', 'supplementScope':'existing snapshots plus source-supported persistent ticket delta; no actual requesting-owner attribution or rerun'})
print(json.dumps({'resultSealSHA256':sha(HERE / 'result-seal.json'), 'sealedMembers':len(files),
    'predecessorResultSealPreserved':True,'targetAttempts':1,'requesting87thTicketOwnerObserved':False}))
