#!/usr/bin/env python3
"""Seal this bounded review once; never modify an upstream packet."""
from verify import *

assert not (BASE/'handoff.json').exists(),'Preserve sealed review'
result=audit()
members=inventory()
handoff={'schema':1,'audit':result,'members':members,'memberTreeSHA256':sha(canonical(members)),
         'runtimeSelected':False,'nativeExecuted':False,'gaAccepted':False}
(BASE/'handoff.json').write_bytes(canonical(handoff))
digest=sha((BASE/'handoff.json').read_bytes())
(BASE/'handoff.sha256').write_text(digest+'  handoff.json\n')
print(json.dumps({'reviewHandoffSHA256':digest,'reviewMembers':len(members),**result},indent=2,sort_keys=True))
