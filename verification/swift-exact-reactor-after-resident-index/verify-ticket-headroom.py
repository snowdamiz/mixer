#!/usr/bin/env python3
"""Read-only check of existing ticket snapshots/source; never reruns the target."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def verify():
    seal = read(HERE / 'result-seal.json')
    predecessor = read(HERE / 'result-seal-initial.json')
    assert seal['priorResultSealSHA256'] == sha(HERE / 'result-seal-initial.json')
    for name, digest in predecessor['files'].items():
        assert seal['files'][name] == digest == sha(HERE / name), name
    observation = read(HERE / 'ticket-headroom-observation.json')
    source = observation['sourceEvidence']
    for record in source:
        path = ROOT / record['path']
        assert sha(path) == record['sha256']
        lines = path.read_text().splitlines()
        for excerpt in record['excerpts']:
            assert '\n'.join(lines[excerpt['start']-1:excerpt['end']]) == excerpt['text']
    assert observation['ticketLimit'] == 86 and observation['persistentBufferTicketDelta'] == 1
    assert observation['requesting87thTicketOwnerObserved'] is False
    before_path = ROOT / observation['beforeEvents']['path']
    after_path = ROOT / observation['afterEvents']['path']
    for record in [observation['beforeEvents'], observation['afterEvents']]:
        assert sha(ROOT / record['path']) == record['sha256']
    before = read(before_path)
    after = read(after_path)
    for row in observation['snapshots']:
        for key, events in [('before', before), ('after', after)]:
            payload = next(e['payload'] for e in events if e['event'] == row['event'])
            usage = payload['at_failure'] if row['event'] == 'runtime_failure' else payload['usage']
            actual = {
                'liveTickets': usage['reservations']['live_tickets'],
                'peakTickets': usage['reservations']['peak_tickets'],
                'cacheEntries': usage['live']['cache_entries']['current'],
                'activePins': usage['live']['active_pins']['current'],
                'frames': usage['live']['frames']['current'],
                'instructions': usage['instructions'], 'cacheWork': usage['cache_work'],
                'unusedTicketCapacity': 86-usage['reservations']['live_tickets']}
            assert row[key] == actual
    assert [(r['before']['liveTickets'],r['after']['liveTickets']) for r in observation['snapshots']] == [(21,22),(85,86),(85,86)]
    assert observation['snapshots'][1]['after']['unusedTicketCapacity'] == 0
    assert observation['snapshots'][2]['before']['instructions'] != observation['snapshots'][2]['after']['instructions']
    assert observation['unequalFailurePrefixesComparableForPerformance'] is False
    return {'ticketHeadroomObservationVerified': True, 'targetAttempts': 1,
        'constructorTicketsBeforeAfter': [21,22], 'initializeTicketsBeforeAfter': [85,86],
        'persistentBufferTicketDelta': 1, 'ticketLimitUnchanged': 86,
        'requesting87thTicketOwnerObserved': False, 'newExecutionOrInstrumentation': False}

if __name__ == '__main__':
    print(json.dumps(verify()))
