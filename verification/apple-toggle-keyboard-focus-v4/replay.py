#!/usr/bin/env python3
"""Offline replay of the fixed owned runtime journal; never native execution."""
import json
import pathlib
import settings_telemetry as t
BASE = pathlib.Path(__file__).resolve().parent


def replay(folder):
    paths = sorted(folder.glob('0000-settings-*.json'))
    t.require(paths and paths[0].name == '0000-settings-0000.json', 'Durable setup start missing')
    first = json.loads(paths[0].read_bytes())
    clock = [first['receivedUptime']]
    identity = first['ownedSimulatorIdentity']
    generated = []
    def persist(suffix, value):
        generated.append({**value, 'ownedSimulatorIdentity': identity})
    def file(slot, form, payload):
        p = folder / (slot + ('.png' if form == 'png' else '.txt'))
        t.require(p.is_file() and not p.is_symlink() and p.read_bytes() == payload, 'Durable AX/PNG differs from journal')
    session = t.Session(persist, file, first['sessionDeadlineUptime'], now=lambda: clock[0], token=first['generation'])
    for path in paths:
        saved = json.loads(path.read_bytes())
        t.require(saved['ownedSimulatorIdentity'] == identity and not path.is_symlink(), 'Journal identity/path changed')
        clock[0] = saved['receivedUptime']
        session.request(saved['record'])
        t.require(generated[-1] == saved, 'Replayed durable record differs')
    return session.summary()


if __name__ == '__main__':
    result = replay(BASE / 'runtime/captures')
    p = BASE / 'runtime/runtime-verdict.json'
    if p.is_file():
        t.require(result == json.loads(p.read_bytes())['settingsDiagnostic'], 'Replayed summary differs')
    print(json.dumps({'schema': 'mixer.apple-toggle.keyboard-v4-diagnostic-replay.1', 'status': 'DIAGNOSTIC_ONLY', 'settingsDiagnostic': result, 'nativeKeyboardQualification': False, 'gaAccepted': False}, sort_keys=True))
