#!/usr/bin/env python3
"""One local correction handoff; upstream packets remain untouched."""
from verify import *

assert not (BASE/'handoff.json').exists(), 'Preserve the existing seal'
result=audit()
members=inventory()
handoff={'schema':1,'members':members,'memberTreeSHA256':sha(canonical(members)),'audit':result,
         'independentReviewAccepted':False,'runtimeSelected':False,'nativeExecuted':False,'gaAccepted':False}
(BASE/'handoff.json').write_bytes(canonical(handoff))
digest=sha((BASE/'handoff.json').read_bytes())
(BASE/'handoff.sha256').write_text(digest+'  handoff.json\n')
print(json.dumps({'handoffSHA256':digest,'sealedMembers':len(members),**result},indent=2,sort_keys=True))
