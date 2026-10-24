#!/usr/bin/env python3
"""Read-only exact packet membership/hash check. No native commands."""
import json
from pathlib import Path
import common
import seal


def check():
    expected=json.loads((common.HERE/'packet-seal.json').read_text())['files'];actual=seal.files()
    if expected!=actual:raise ValueError('exact root packet membership/hash/size drift')
    packet=json.loads((common.HERE/'packet.json').read_text());external=packet['externalAPK']
    if common.sha(external['path'])!=external['sha256'] or Path(external['path']).stat().st_size!=external['bytes']:raise ValueError('retained outside-Git APK drift')
    if packet['nativeRuntime']!='NOT RUN' or packet['nativeAcceptance'] or packet['nativeInstancesStarted'] or packet['physicalTargetsQueried']:raise ValueError('host packet made native claim')
    return {'status':'passed-exact-recursive-pointer-packet-seal','files':len(actual),'packetSealSHA256':common.sha(common.HERE/'packet-seal.json'),'concreteRunnerSHA256':packet['concreteRunnerSHA256'],'nativeRuntime':'NOT RUN'}

if __name__=='__main__':print(json.dumps(check(),indent=2,sort_keys=True))
