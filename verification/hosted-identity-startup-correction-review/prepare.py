#!/usr/bin/env python3
"""Independent reconstruction and content verification; own output/scratch only."""
import datetime,hashlib,io,json,shutil,subprocess,tarfile,tempfile
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(d): return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,d): (O/p).write_text(json.dumps(d,indent=2)+'\n')
C=R/'verification/hosted-identity-startup-correction';F=R/'verification/hosted-identity-startup-implementation';V=R/'verification/hosted-identity-startup-review'
c=json.loads((C/'receipt.json').read_text());f=json.loads((F/'receipt.json').read_text());v=json.loads((V/'receipt.json').read_text())
assert sha(C/'receipt.json')=='e90dc6714ecf1b9fd34786384cce3db0e8ed61af780ee1ebb2a82370e7db25ed'
checks={}
for p,x in [(C,c),(F,f),(V,v)]:
 assert all(sha(p/n)==h for n,h in x['bindings'].items()),p
 checks[p.name]={'receiptSHA256':sha(p/'receipt.json'),'boundFilesVerified':len(x['bindings'])}
assert sha(R/c['contract']['path'])==c['contract']['sha256']
assert sha(R/c['documentation']['path'])==c['documentation']['sha256']
assert sha(R/'docs/hosted-identity-startup-implementation.md')==f['documentationSHA256']
assert sha(R/v['documentation'])==v['documentationSHA256']
S=Path(tempfile.mkdtemp(prefix='mixer-identity-startup-correction-review-')).resolve()
base='b0629cf554a1798b2d22ce3e1d349cd1f9504c3a'
raw=subprocess.check_output(['git','archive',base,'hosted','services/protocol/testdata'],cwd=R)
with tarfile.open(fileobj=io.BytesIO(raw)) as t:t.extractall(S,filter='data')
commands=[]
for label,patch in [('cumulative',C/'implementation.patch')]:
 p=subprocess.run(['git','apply',str(patch)],cwd=S,capture_output=True);(O/(label+'-apply.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
 commands.append({'argv':['git','apply',str(patch)],'cwd':str(S),'exitCode':p.returncode,'output':label+'-apply.log','outputSHA256':sha(O/(label+'-apply.log'))})
cm=json.loads((C/'tested-source-manifest.json').read_text());fm=json.loads((F/'tested-source-manifest.json').read_text())
assert digest(cm['files'])==cm['digest']==c['testedSourceDigest']=='bfa2dcc1467f524a68fec298bdd098625f450b68ab2bd68b99f2a73d435772c3'
assert digest(fm['files'])==fm['digest']==f['testedSourceDigest']
for p,receipt,manifest in [(C,c,cm),(F,f,fm)]:
 assert sha(p/'tested-source.tar.gz')==receipt['sourceArchiveSHA256']
 with tarfile.open(p/'tested-source.tar.gz') as t:
  assert len(t.getmembers())==len(manifest['files'])
  archive={m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}
 assert archive==manifest['files']
actual={str(p.relative_to(S)):sha(p) for p in (S/'hosted').rglob('*') if p.is_file()}
actual.update({str(p.relative_to(S)):sha(p) for p in (S/'services/protocol/testdata').rglob('*') if p.is_file()})
assert actual==cm['files'],(set(actual)^set(cm['files']))
assert sha(C/'implementation.patch')==c['patchSHA256']=='b8e19489a86e4bfe621dc478070f48c4aebad58dc98d950599020eecad0add49'
assert sha(C/'correction-vs-frozen.patch')==c['correctionDeltaSHA256']=='1b5fee53a73ddcafb3122c2bad874985a191a67c472b12210cd12b217b1439d1'
assert len(c['overlayFiles'])==12 and len(f['overlayFiles'])==10
assert all(c['overlayFiles'][p]==h==sha(F/'overlay'/p)==sha(C/'overlay'/p)==sha(S/p) for p,h in f['overlayFiles'].items())
diff={p:{'original':fm['files'].get(p),'corrected':h} for p,h in cm['files'].items() if fm['files'].get(p)!=h}
assert set(diff)=={'hosted/lib/mixer_hosted/identity/manifest.ex','hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs'}
with tarfile.open(F/'tested-source.tar.gz') as t: old=t.extractfile('hosted/lib/mixer_hosted/identity/manifest.ex').read()
new=(S/'hosted/lib/mixer_hosted/identity/manifest.ex').read_bytes()
assert new==old.replace(b'~r/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/',b'~r/\\A[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\z/').replace(b'~r/^[A-Za-z0-9_~.\\/-]+$/',b'~r/\\A[A-Za-z0-9_~.\\/-]+\\z/')
# Independently apply frozen patch to a second owned subdirectory, then delta.
B=S/'lineage';B.mkdir()
with tarfile.open(fileobj=io.BytesIO(raw)) as t:t.extractall(B,filter='data')
for patch in [F/'implementation.patch',C/'correction-vs-frozen.patch']:
 p=subprocess.run(['git','apply',str(patch)],cwd=B,capture_output=True);assert p.returncode==0,p.stderr
assert all(sha(B/p)==h for p,h in actual.items());shutil.rmtree(B)
shutil.copytree(R/'hosted/deps',S/'hosted/deps',ignore=shutil.ignore_patterns('_build'))
deps={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted/deps').rglob('*')) if p.is_file() and '_build' not in p.relative_to(S).parts}
assert digest(deps)==c['dependencyDigest']==f['dependencyDigest']==v['dependencyDigest']
live={str(p.relative_to(R)):sha(p) for p in (R/'hosted').rglob('*') if p.is_file() and not {'deps','_build','__pycache__','cover'}.intersection(p.relative_to(R).parts) and p.name!='erl_crash.dump'}
assert digest(live)==c['liveHostedDigest']
for n in ['review_startup_adversarial_test.exs','endpoint_regression_test.exs']:
 shutil.copy2(V/n,O/n);shutil.copy2(O/n,S/'hosted/test/mixer_hosted/identity'/n)
save('source-verification.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'hostedBase':base,'packets':checks,'contractAndDocumentationHashesVerified':True,'sourceFiles':len(actual),'correctedSource':actual,'correctedSourceDigest':digest(actual),'archiveEntriesVerified':{'original':len(fm['files']),'corrected':len(cm['files'])},'delta':diff,'productionDeltaExactlyTwoAnchors':True,'tenOriginalOverlayHashesUnchanged':True,'cumulativeOverlayCount':12,'dependencies':deps,'dependencyFiles':len(deps),'dependencyDigest':digest(deps),'liveHosted':live,'liveHostedDigest':digest(live),'cumulativeAndFrozenPlusDeltaReconstructIdentically':True,'commands':commands})
save('state.json',{'scratch':str(S),'commands':[]});print(json.dumps({'scratch':str(S),'verifiedBindings':checks,'sourceFiles':len(actual),'dependencyFiles':len(deps),'sourceDigest':digest(actual)}))
