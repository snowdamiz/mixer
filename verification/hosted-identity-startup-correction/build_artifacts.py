#!/usr/bin/env python3
"""Bind cumulative overlay and the exact correction against immutable inputs."""
import difflib,hashlib,json,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];S=Path(json.loads((O/'state.json').read_text())['scratch']);I=json.loads((O/'inputs.json').read_text());F=R/I['frozenPacket']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(files):return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
overlay={str(p.relative_to(O/'overlay')):sha(p) for p in sorted((O/'overlay').rglob('*')) if p.is_file()}
assert len(overlay)==12
assert all(overlay[p]==h for p,h in I['frozenOverlay'].items()),'frozen overlay drift'
assert all(sha(S/p)==h for p,h in overlay.items())
patch=[];delta=[];changes={};delta_changes={}
with tarfile.open(F/'tested-source.tar.gz') as t:
 for p,h in overlay.items():
  live=R/p;old=live.read_text() if live.exists() else '';new=(S/p).read_text()
  assert (sha(live) if live.exists() else None)==I['liveHosted'].get(p),p+' live source drift'
  patch+=difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+p if live.exists() else '/dev/null',tofile='b/'+p)
  changes[p]={'baseSHA256':sha(live) if live.exists() else None,'resultSHA256':h}
  original=t.extractfile(p).read().decode() if p in I['frozenSource'] else ''
  if original!=new:
   delta+=difflib.unified_diff(original.splitlines(True),new.splitlines(True),fromfile='a/'+p if p in I['frozenSource'] else '/dev/null',tofile='b/'+p)
   delta_changes[p]={'baseSHA256':I['frozenSource'].get(p),'resultSHA256':h}
assert set(delta_changes)=={'hosted/lib/mixer_hosted/identity/manifest.ex','hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs'}
(O/'implementation.patch').write_text(''.join(patch));(O/'correction-vs-frozen.patch').write_text(''.join(delta))
check=subprocess.run(['git','apply','--check',str(O/'implementation.patch')],cwd=R,capture_output=True)
(O/'patch-apply-check.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0
save('overlay-manifest.json',{'files':overlay,'changes':changes,'patchSHA256':sha(O/'implementation.patch'),'correctionDelta':delta_changes,'correctionDeltaSHA256':sha(O/'correction-vs-frozen.patch'),'allTenFrozenOverlayFilesUnchanged':True,'patchApplyCheck':{'argv':['git','apply','--check',str(O/'implementation.patch')],'cwd':str(R),'exitCode':check.returncode,'output':'patch-apply-check.log','outputSHA256':sha(O/'patch-apply-check.log')}})
source={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted').rglob('*')) if p.is_file() and not {'deps','_build','__pycache__','cover'}.intersection(p.relative_to(S).parts) and p.name!='erl_crash.dump'}
for p in sorted((S/'services/protocol/testdata').rglob('*')):
 if p.is_file():source[str(p.relative_to(S))]=sha(p)
assert set(source)==set(I['frozenSource'])|{'hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs'}
assert all(h==I['frozenSource'][p] for p,h in source.items() if p not in delta_changes)
deps={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted/deps').rglob('*')) if p.is_file() and '_build' not in p.relative_to(S).parts}
assert deps==I['dependencies']
save('tested-source-manifest.json',{'files':source,'digest':digest(source),'dependencyDigest':digest(deps)})
with tarfile.open(O/'tested-source.tar.gz','w:gz') as t:
 for p in source:t.add(S/p,arcname=p,recursive=False)
print(json.dumps({'overlayFiles':len(overlay),'testedSourceDigest':digest(source),'patchSHA256':sha(O/'implementation.patch'),'correctionDeltaSHA256':sha(O/'correction-vs-frozen.patch'),'sourceArchiveSHA256':sha(O/'tested-source.tar.gz')}))
