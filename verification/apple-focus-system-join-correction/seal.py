#!/usr/bin/env python3
"""Seal only this owned correction lane and its document; no parent writes."""
import datetime
import hashlib
import json
import pathlib
import stat
import sys

sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
assert not (H/'handoff.json').exists(),'Never replace a sealed handoff'
paths=sorted([path for path in H.rglob('*') if path.is_file()]+[ROOT/'docs/apple-focus-system-join-correction.md'])
assert not list(H.rglob('__pycache__'))
members={}
for path in paths:
 assert not path.is_symlink()
 path.chmod(0o444);raw=path.read_bytes()
 members[str(path.relative_to(ROOT))]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':stat.S_IMODE(path.stat().st_mode)}
packet={'schema':1,'status':'pending-independent-host-review','scope':'Isolated host-adapter-only frozen V7 replay correction for F1/F2','sourceRevision':'9102ad3ee1247187c01ea5f55c42caaac882961b','producerHandoffSHA256':'5d88cd0069f7e83e73b95903ecf0e9e6b721a73328193653e8e1da8903c81427','reviewHandoffSHA256':'e66d1f5710d5614fc668bec3fc6759fb6080a91002516f13d43994dca2ab35a4','candidateArchiveSHA256':'d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda','candidateSourceMembers':40,'changedSwiftMembers':[],'hostTestMethodsPassed':38,'focusedResultControls':36,'originalVerdictUnchanged':True,'originalOraclePassed':False,'nativePass':False,'sourceHostAccepted':False,'nativeAccepted':False,'gaAccepted':False,'compilerInvocations':0,'nativeQueries':0,'nativeAttempts':0,'appProducts':0,'physicalPhones':'disconnected-deferred','members':members}
handoff=H/'handoff.json';handoff.write_text(json.dumps(packet,sort_keys=True,indent=2)+'\n');handoff.chmod(0o444)
from verify_seal import verify
print(json.dumps(verify(),sort_keys=True))
