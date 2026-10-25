from pathlib import Path
import json,hashlib,shutil,subprocess,datetime
R=Path(__file__).resolve().parents[2]; H=Path(__file__).resolve().parent; P=R/'verification/swift-cache-resident-index'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def manifest(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def write(n,v):(H/n).write_bytes(enc(v))
expected={'seal.json':'fc45e20ca74edc4d435b1d9d82ed8b01bb68a55b42801501901356ab530b39d7','receipt.json':'916b8fdfdc2d78f538bb2fc556a37cce97304850bc4868c8e1685304d2b76267','candidate.patch':'bbf581ceb101f4befbd5d9f837b7fe7648155c36d009b1eb1c46cbc5c3f0401e'}
assert all(sha(P/n)==v for n,v in expected.items())
s=json.loads((P/'seal.json').read_text());bad=[n for n,v in s['members'].items() if sha(P/n)!=v];assert not bad,bad
assert hashlib.sha256(enc(s['members'])).hexdigest()==s['membersSHA256']
c=json.loads((P/'candidate-source-manifest.json').read_text());b=json.loads((P/'baseline-manifest.json').read_text())
assert len(c)==len(b)==132
assert sha(P/'candidate-source-manifest.json')=='02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d'
assert sha(P/'baseline-manifest.json')=='b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
assert all(sha(P/'source'/n)==v for n,v in c.items())
assert all(sha(R/'vm'/n)==v for n,v in b.items())
changes=[n for n in b if b[n]!=c[n]];assert len(changes)==6
S=H/'owned-scratch';assert not S.exists();S.mkdir()
for kind in ('candidate','baseline'):
 for n,v in (c if kind=='candidate' else b).items():
  src=P/'source'/n if kind=='candidate' else (P/'baseline-original-cache-tests.rs' if n=='src/experimental_swift_reactor/cache_tests.rs' else P/'baseline'/n)
  assert sha(src)==v
  dst=S/kind/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 (S/'targets'/kind).mkdir(parents=True)
assert manifest(S/'candidate')==c and manifest(S/'baseline')==b
(S/'tmp').mkdir()
write('packet-audit.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootHEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'expectedPacket':expected,'sealedMembersVerified':len(s['members']),'candidateClosure':sha(P/'candidate-source-manifest.json'),'baselineClosure':sha(P/'baseline-manifest.json'),'candidateMembers':132,'liveBaselineUnchanged':True,'changedFiles':changes,'producerScriptsExecuted':False,'baselineOriginalTestsRestored':True,'freshTargets':True})
print(json.dumps({'packetVerified':True,'sealedMembers':len(s['members']),'changes':changes}))
