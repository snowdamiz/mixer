#!/usr/bin/env python3
"""Seal only this independent host review and its report; never product/native state."""
import datetime,hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
packet=ROOT/'verification/apple-toggle-keyboard-focus-v6-preparation/packet-seal.json'
selection=ROOT/'verification/apple-toggle-keyboard-focus-v5-root-review/v6-repair-selection.json'
assert sha(packet)=='5b2743fd61dbabc95abc6e50468347efe406953fb1314785b17013922b6438fd'
assert sha(selection)=='a687f64d09bc04df73842b3a45a4014551497a452cdf5092cd24ee60cbb9a3d7'
assert all((ROOT/n).is_file() and not (ROOT/n).is_symlink() and sha(ROOT/n)==d for n,d in json.loads(packet.read_bytes())['files'].items())
old=ROOT/'verification/apple-toggle-keyboard-focus-v5-independent-review/review-seal.json'
assert sha(old)=='dbe9f176e1f32d418fb70592b976dcb3ff84789d10104d50816b720c54d7af6d'
assert all(sha(ROOT/n)==d for n,d in json.loads(old.read_bytes())['files'].items())
assert not (HERE/'.scratch').exists()
report=ROOT/'docs/apple-toggle-keyboard-focus-v6-independent-review.md'
seal=HERE/'review-seal.json'
paths=[p for p in HERE.rglob('*') if p.is_file() and p!=seal]+[report]
assert all(not p.is_symlink() for p in paths)
files={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
if '--check' in sys.argv:
 value=json.loads(seal.read_bytes());assert value['files']==files,'Review evidence changed'
else:
 assert not seal.exists(),'Existing review seal is immutable'
 value={'schema':'mixer.apple-toggle.keyboard-v6-independent-review-seal.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producerPacketSHA256':sha(packet),'rootSelectionSHA256':sha(selection),'disposition':'no-actionable-findings-in-selected-host-ordering-repair','nativeExecutionSelected':False,'nativeExecuted':False,'keyboardAccepted':False,'carrierAccepted':False,'gaAccepted':False,'fileCount':len(files),'files':files}
 seal.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps({'reviewSealSHA256':sha(seal),'files':len(files),'producerFilesVerified':184,'scratchAbsent':True,'nativeExecuted':False}))
