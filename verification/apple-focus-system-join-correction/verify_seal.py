#!/usr/bin/env python3
"""Read-only exact-member, mode and digest verification of this sealed lane."""
import hashlib
import json
import pathlib
import stat

H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def verify():
 handoff=H/'handoff.json';raw=handoff.read_bytes();packet=json.loads(raw)
 expected=set(packet['members'])
 actual={str(path.relative_to(ROOT)) for path in H.rglob('*') if path.is_file() and path!=handoff}
 actual.add('docs/apple-focus-system-join-correction.md')
 assert actual==expected,{'missing':sorted(expected-actual),'extra':sorted(actual-expected)}
 for relative,binding in packet['members'].items():
  path=ROOT/relative;data=path.read_bytes()
  assert len(data)==binding['bytes'] and sha(data)==binding['sha256'] and stat.S_IMODE(path.stat().st_mode)==binding['mode'],relative
 assert stat.S_IMODE(handoff.stat().st_mode)==0o444
 return {'schema':1,'passed':True,'members':len(expected),'handoffSHA256':sha(raw),'nativePass':False,'sourceHostAccepted':False,'scope':'Read-only sealed host correction verification; independent acceptance pending'}
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
