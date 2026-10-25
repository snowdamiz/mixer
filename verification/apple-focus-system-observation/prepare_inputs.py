#!/usr/bin/env python3
"""Copy only hash-accepted inputs; no runtime, Git or native dispatch."""
import hashlib, json, pathlib, tarfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REVIEW=ROOT/'verification/apple-settings-fixed-chunk-native-result-review'
ARCHIVE=ROOT/'verification/apple-settings-fixed-chunk-native-build/attempt-1/accepted-sources.tar.gz'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
manifest={}
def copy(origin,dest,expected=None):
 data=origin.read_bytes()
 if expected: assert sha(data)==expected['sha256'] and len(data)==expected['bytes'],str(origin)
 write(HERE/dest,data);manifest[dest]={'origin':str(origin.relative_to(ROOT)),'bytes':len(data),'sha256':sha(data)}
raw=(REVIEW/'handoff.json').read_bytes();assert sha(raw)=='4c51a382173b38962cf031db0f19c82b076756fc51195092b29674e9f7a5ee48'
handoff=json.loads(raw)
for name,expected in handoff['members'].items():
 data=(ROOT/name).read_bytes();assert sha(data)==expected['sha256'] and len(data)==expected['bytes'],name
copy(REVIEW/'handoff.json','inputs/result-review-handoff.json')
copy(ROOT/'verification/apple-settings-fixed-chunk-native-result-root-review/acceptance.json','inputs/root-acceptance.json')
copy(REVIEW/'commands/final-validation/stdout.json','inputs/result-review-validation.json',handoff['members']['verification/apple-settings-fixed-chunk-native-result-review/commands/final-validation/stdout.json'])
assert sha(ARCHIVE.read_bytes())=='96cf2e6d4356035e004564a2a4d4e01122fb570835e4089c6c83788ab53465f8'
copy(ARCHIVE,'inputs/accepted-sources.tar.gz')
copy(ARCHIVE.parent/'source-manifest.json','inputs/accepted-source-manifest.json')
accepted=json.loads((ARCHIVE.parent/'source-manifest.json').read_bytes())['sources']
with tarfile.open(ARCHIVE) as t:
 members=[m for m in t.getmembers() if m.isfile()];assert len(members)==40
 for member in members:
  assert member.name in accepted and not member.issym() and not member.islnk()
  data=t.extractfile(member).read();expected=accepted[member.name]
  assert sha(data)==expected['sha256'] and len(data)==expected['bytes']
  write(HERE/'inputs'/member.name,data);write(HERE/'candidate'/member.name,data)
  manifest['inputs/'+member.name]={'origin':'archive:'+member.name,'bytes':len(data),'sha256':sha(data)}
for name,expected in handoff['members'].items():
 prefix='verification/apple-settings-fixed-chunk-native-result-review/inputs/runtime/inputs/runtime/verification/'
 if name.startswith(prefix): copy(ROOT/name,'inputs/oracle/'+name[len(prefix):],expected)
review=json.loads((REVIEW/'commands/final-validation/stdout.json').read_bytes())
for name,expected in review['inputs'].items():
 if name.endswith(('captures/0001-before-1.json','captures/0001-after-1.json','captures/0001-keyboard-witness-1.json')):
  copy(ROOT/name,'inputs/v7/'+pathlib.Path(name).name,expected)
write(HERE/'input-bindings.json',(json.dumps({'schema':1,'verifiedReviewMembers':42,'archiveMembers':40,'files':manifest},indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'copiedInputs':len(manifest),'acceptedArchiveMembers':40,'reviewMembersVerified':42},sort_keys=True))
