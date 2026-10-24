"""Bounded read-only Docker platform identity observation; starts no container."""
from pathlib import Path
import hashlib, json, subprocess, selectors, os, time, sys, datetime
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PREP=ROOT/'verification/stripe-resource-linux-compiler-qualification-preparation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proposal=PREP/'image-identity-correction-proposal/proposal.json'
assert sha(proposal)=='74ab57508eec0a6393c122c7d8675dfd21734754148ff5540343a5d725002798'
d=json.loads(proposal.read_text());command=d['exactNextReadOnlyCommand']
assert command[:4]==['docker','image','inspect','--platform=linux/arm64']
assert command[4]=='hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde'
out={s:bytearray() for s in ['stdout','stderr']};start=time.monotonic();failure=None
p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
s=selectors.DefaultSelector();s.register(p.stdout,selectors.EVENT_READ,'stdout');s.register(p.stderr,selectors.EVENT_READ,'stderr')
try:
 while s.get_map():
  if time.monotonic()-start>=10:raise TimeoutError('10 second read-only inspection bound')
  for key,_ in s.select(.05):
   block=os.read(key.fd,65536)
   if not block:s.unregister(key.fileobj);continue
   if len(out[key.data])+len(block)>65536:raise ValueError('64 KiB per-stream bound')
   out[key.data].extend(block)
 p.wait(timeout=max(.01,10-(time.monotonic()-start)))
except Exception as e:
 failure={'type':type(e).__name__,'message':str(e)};p.kill();p.wait(timeout=2)
finally:s.close()
for stream,raw in out.items():
 with (HERE/('explicit-platform.'+stream)).open('xb') as f:f.write(raw)
matched=False
if failure is None and p.returncode==0:
 try:
  values=json.loads(out['stdout']);assert len(values)==1
  sys.path.insert(0,str(PREP));import run_qualification
  run_qualification.checked_image(values[0]);matched=True
 except Exception as e:failure={'type':type(e).__name__,'message':str(e)}
r={'schema':1,'accountableReviewer':'/root','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'exitCode':p.returncode,'elapsedSeconds':time.monotonic()-start,'sourceSHA256':sha(Path(__file__)),'proposalSHA256':sha(proposal),'outputs':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in out.items()},'failure':failure,'originalStrictImageValidatorPassed':matched,'containerActions':0,'compilerInvocations':0,'C6Retries':0}
with (HERE/'explicit-platform-receipt.json').open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(r))
