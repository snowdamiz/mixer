#!/usr/bin/env python3
"""Original schema2 restricted-CBOR/hash vectors; synthetic build inputs only."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from vectors import baseline, cbor, digest

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = '898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97'
TRANSPORT = '052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439'
HEADER = '9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6'
UI = 'e9983da1c8f5b79dcead9fc7c99172be374ddeba319308615108651cb3931ac5'
SEMANTIC = 'ca53c3c2ea1d8f08020468cc5d458d86542e0806d6494840557e591342f1154e'
SCHEMAS = {'network.http.v1': 'fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3',
           'storage.keyValue.v1': '4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd'}

def capability(identifier):
    return dict(id=identifier, schema_sha256=SCHEMAS[identifier],
                native_sha256=digest(identifier+' native input'),
                configuration_sha256=digest(identifier+' config'), grants_sha256=digest(identifier+' grants'))

def descriptor():
    value = baseline()
    value['schema'] = 2
    value['engine'].update(profile='mixer-table-memory-v3', guest_abi=2,
                           ui_contract_sha256=UI, capability_contract_sha256=SEMANTIC)
    value['execution']['protocol'] = 3
    value['capability_execution'] = dict(route='capability-guest-v1', contract_sha256=EXECUTION,
        transport_sha256=TRANSPORT, native_header_sha256=HEADER, maximum_requests=8,
        reservation_bytes=8388608, timeout_milliseconds=30000, turn_milliseconds=50,
        bridge_policy_sha256=digest('bridge policy'))
    return value

def vectors():
    base = descriptor()
    cases = [('ios-device-empty', base)]
    for name, changes in [('ios-simulator', dict(environment='simulator', target='arm64-apple-ios17.0-simulator')),
                          ('android-device', dict(os='android', minimum_os='28', target='aarch64-unknown-linux-android28')),
                          ('android-x86-simulator', dict(os='android', architecture='x86_64', environment='simulator', minimum_os='28', target='x86_64-unknown-linux-android28'))]:
        value = copy.deepcopy(base); value['platform'].update(changes); cases.append((name, value))
    for name, ids in [('http', ['network.http.v1']), ('storage', ['storage.keyValue.v1']), ('both', sorted(SCHEMAS))]:
        value = copy.deepcopy(base); value['capabilities'] = [capability(x) for x in ids]; cases.append((name, value))
    for amount in [1, 65535, 65536]:
        value = copy.deepcopy(base); value['execution']['memory_bytes'] = amount; cases.append(('memory-'+str(amount), value))
    value = copy.deepcopy(base); value['execution'].update(startup_export='e\u0301.start.日志', state_schema=(1<<64)-1)
    cases.append(('unicode-and-uint64', value))
    return [dict(name=name, descriptor=value, canonicalCBOR=cbor(value).hex(),
                 fingerprint=hashlib.sha256(b'mixer.runtime.identity.v2\0'+cbor(value)).hexdigest()) for name,value in cases]

if __name__ == '__main__':
    target = ROOT/'Tests/MixerRuntimeIdentityTests/Fixtures/vectors-v2.json'
    encoded = json.dumps(vectors(), ensure_ascii=True, indent=2)+'\n'
    if sys.argv[1:] == ['--check']:
        if target.read_text() != encoded: raise SystemExit('schema2 vectors differ')
        print('11 original schema2 canonical/hash vectors match')
    elif not sys.argv[1:]: target.write_text(encoded)
    else: raise SystemExit('Usage: vectors_v2.py [--check]')
