#!/usr/bin/env python3
"""Create a reviewable runtime successor; this command never dispatches native work."""
import difflib,gzip,hashlib,io,json,pathlib,stat,tarfile
HERE=pathlib.Path(__file__).resolve().parent;REPO=HERE.parents[2]
PREP=REPO/'verification/apple-passive-lifecycle-runtime-preparation'
BUILD=REPO/'verification/apple-passive-lifecycle-sendable-correction/build-attempt-1'
REL='inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
def sha(b):return hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def binding(p):
 b=p.read_bytes();return {'path':str(p.relative_to(REPO)),'bytes':len(b),'sha256':sha(b)}
manifest=json.loads((PREP/'runtime-source-manifest.json').read_bytes())
assert sha((PREP/'runtime-sources.tar.gz').read_bytes())==manifest['archive']['sha256']
with tarfile.open(PREP/'runtime-sources.tar.gz') as t:
 baseline={m.name.removeprefix('selected/'):t.extractfile(m).read() for m in t if m.isfile()}
assert set(baseline)==set(manifest['files'])
for n,b in baseline.items():
 assert sha(b)==manifest['files'][n]['sha256']
 assert (HERE/'baseline-runtime'/n).read_bytes()==b
candidate=dict(baseline);candidate[REL]=(HERE/'candidate/settings_telemetry.py').read_bytes()
assert [n for n in baseline if baseline[n]!=candidate[n]]==[REL]
source=json.loads((BUILD/'source-manifest.json').read_bytes())
with tarfile.open(BUILD/'sources.tar.gz') as t:
 compiled={m.name:t.extractfile(m).read() for m in t if m.isfile()}
assert set(compiled)==set(source['sources'])
for n,b in compiled.items():
 assert sha(b)==source['sources'][n]['sha256']
 assert (HERE/'baseline-compile'/n).read_bytes()==b
assert source['sourceTreeSHA256']=='f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb'
assert sha((BUILD/'products.tar.gz').read_bytes())=='495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'
rows={n:{**manifest['files'][n],'bytes':len(b),'sha256':sha(b)} for n,b in candidate.items()}
buffer=io.BytesIO()
with gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0) as gz:
 with tarfile.open(fileobj=gz,mode='w') as t:
  for n,b in sorted(candidate.items()):
   item=tarfile.TarInfo('selected/'+n);item.size=len(b);item.mode=rows[n]['mode'];item.mtime=0;t.addfile(item,io.BytesIO(b))
archive=HERE/'candidate-runtime-sources.tar.gz';archive.write_bytes(buffer.getvalue())
with tarfile.open(archive) as t:assert {m.name.removeprefix('selected/'):t.extractfile(m).read() for m in t if m.isfile()}==candidate
selection=json.loads((PREP/'selection-template.json').read_bytes());selection['files'][REL]=sha(candidate[REL])
(HERE/'candidate-selection-template.json').write_bytes(stable(selection))
packet={'schema':'mixer.apple-settings-terminal-reuse-candidate.1','scope':'unaccepted review candidate; no native dispatch',
 'changedRuntimeFiles':[REL],'byteIdenticalRuntimeFiles':len(candidate)-1,'compileSourceFilesByteIdentical':len(compiled),
 'sourceTreeSHA256':source['sourceTreeSHA256'],'productArchive':binding(BUILD/'products.tar.gz'),
 'runtimeArchive':binding(archive),'runtimeFiles':rows,'candidateSelectionTemplate':binding(HERE/'candidate-selection-template.json'),
 'baselineRuntimeArchive':binding(PREP/'runtime-sources.tar.gz'),'baselineCompileArchive':binding(BUILD/'sources.tar.gz'),
 'baselineNativeResult':binding(HERE.parent/'apple-runtime/result.json'),'baselineNativeHandoff':binding(HERE.parent/'apple-runtime/handoff.json'),
 'settingsBudgetSeconds':29,'observationBudgetSeconds':3,'chunkBytes':4992,'bodyLimitBytes':8192,
 'originalSettingsOracleUnchanged':True,'originalTabOracleUnchanged':True,'appAndUITestRunnerRebuildRequired':False,
 'freshIndependentReviewRequired':True,'nativeSelected':False,'nativeAttempts':0,'gaAccepted':False}
(HERE/'candidate-packet.json').write_bytes(stable(packet))
print(json.dumps({'packetSHA256':sha(stable(packet)),'changedRuntimeFiles':packet['changedRuntimeFiles'],'unchangedRuntimeFiles':len(candidate)-1,'unchangedCompileSourceFiles':len(compiled),'nativeAttempts':0}))
