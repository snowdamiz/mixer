#!/usr/bin/env python3
"""Read-only exact correction packet replay, preserving every prior packet."""
import json
import support

def check():
    seal = json.loads((support.HERE / 'packet-seal.json').read_text())
    if seal['runtimeSubtreeExcluded'] != 'verification/android-pointer-timing-correction/runtime' or seal['files'] != support.files():
        raise ValueError('exact correction host membership/hash/size drift')
    packet = json.loads((support.HERE / 'packet.json').read_text())
    if packet['nativeRuntime'] != 'NOT RUN' or packet['nativeAcceptance'] or packet['nativeDispatchAuthorizedByThisPacket'] or packet['nativeCommandsExecuted'] or packet['physicalTargetsQueried']:
        raise ValueError('host correction cannot grant native authority')
    if packet['upstream'] != support.upstream(): raise ValueError('immutable upstream proof differs')
    return {'status': 'passed-exact-timing-correction-host-packet', 'hostFiles': len(seal['files']),
            'sealSHA256': support.sha(support.HERE / 'packet-seal.json'), 'upstream': packet['upstream'],
            'nativeRuntime': 'NOT RUN', 'nativeDispatchAuthorizedByThisPacket': False}

if __name__ == '__main__': print(json.dumps(check(), indent=2, sort_keys=True))
