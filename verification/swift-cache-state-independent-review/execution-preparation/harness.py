"""Bounded owned-command execution and independent caller-protocol checks."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def bounded(argv,cwd,output,name,seconds=60,cap=1048576):
 if not 0<seconds<=60 or not 0<cap<=1048576: raise ValueError('command bound')
 if not isinstance(argv,list) or not argv or any(type(a)!=str for a in argv): raise ValueError('argv list required')
 output=Path(output); output.mkdir(parents=True,exist_ok=True)
 start=time.monotonic(); at=datetime.now(timezone.utc).isoformat()
 paths={key:output/(name+'.'+key) for key in ('stdout','stderr')}
 streams={key:p.open('wb') for key,p in paths.items()}; counts={key:0 for key in paths}
 timed=truncated=False; failure=None; process=None; code=None
 try:
  process=subprocess.Popen(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  selector=selectors.DefaultSelector()
  selector.register(process.stdout,selectors.EVENT_READ,'stdout'); selector.register(process.stderr,selectors.EVENT_READ,'stderr')
  while selector.get_map():
   if time.monotonic()-start>seconds:
    timed=True
    try: os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError: pass
   for key,_ in selector.select(timeout=0.1):
    block=os.read(key.fileobj.fileno(),65536)
    if not block:
     selector.unregister(key.fileobj); key.fileobj.close(); continue
    kind=key.data; remaining=cap-counts[kind]
    streams[kind].write(block[:remaining]); counts[kind]+=min(len(block),remaining)
    if len(block)>remaining:
     truncated=True
     try: os.killpg(process.pid,signal.SIGKILL)
     except ProcessLookupError: pass
   if timed and time.monotonic()-start>seconds+5: raise RuntimeError('owned group did not close pipes')
  selector.close(); code=process.wait(timeout=5)
 except OSError as e:
  code=None; failure={'type':type(e).__name__,'errno':e.errno}
 except Exception as e:
  code=None; failure={'type':type(e).__name__,'message':str(e)[:512]}
 finally:
  if process is not None and process.poll() is None:
   os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=5)
  for stream in streams.values(): stream.close()
 receipt={'argv':argv,'cwd':str(cwd),'at':at,'duration_seconds':time.monotonic()-start,
  'timeout_seconds':seconds,'output_byte_cap_per_stream':cap,'exit_code':code,
  'timed_out':timed,'output_truncated':truncated,'spawn_failure':failure,
  'stdout':str(paths['stdout']),'stderr':str(paths['stderr']),
  'stdout_sha256':sha(paths['stdout'].read_bytes()),'stderr_sha256':sha(paths['stderr'].read_bytes()),
  'cleanup':'sole owned process group returned; no process discovery or unrelated process access'}
 write_json(output/(name+'.json'),receipt)
 return receipt

def protocol(raw):
 if len(raw)>16384: raise ValueError('driver diagnostic exceeds fixed protocol bound')
 d=json.loads(raw)
 keys={'protocol','api_result','cache_state_words','framing_words','envelope_words','aggregate_authority',
  'envelope_metrics','error','input_before','input_after','input_positions_after','output_after','output_position','layouts'}
 if set(d)!=keys or type(d['protocol'])!=int or d['protocol']!=1: raise ValueError('closed driver protocol')
 def integers(value,count):
  return isinstance(value,list) and len(value)==count and all(type(x)==int and 0<=x<(1<<64) for x in value)
 if not isinstance(d['input_before'],list) or len(d['input_before'])!=3 or not all(integers(v,8) for v in d['input_before']): raise ValueError('before stamps')
 if not isinstance(d['input_after'],list) or len(d['input_after'])!=3 or not all(v is None or integers(v,8) for v in d['input_after']): raise ValueError('after stamps')
 if not isinstance(d['input_positions_after'],list) or len(d['input_positions_after'])!=3 or not all(v is None or type(v)==int and 0<=v<(1<<64) for v in d['input_positions_after']): raise ValueError('input positions')
 if d['output_after'] is not None and not integers(d['output_after'],8): raise ValueError('output stamp')
 if d['output_position'] is not None and not (type(d['output_position'])==int and 0<=d['output_position']<(1<<64)): raise ValueError('output position')
 if d['api_result']=='Err':
  if not integers(d['error'],5) or any(d[k] is not None for k in ['cache_state_words','framing_words','envelope_words','aggregate_authority','envelope_metrics']): raise ValueError('Err must have no aggregate/observation')
 elif d['api_result']=='Ok':
  for key,size in [('cache_state_words',32),('framing_words',16),('envelope_words',16),('aggregate_authority',4)]:
   if not integers(d[key],size): raise ValueError('getter projection '+key)
  if d['error'] is not None or type(d['envelope_metrics'])!=int: raise ValueError('Ok error/metrics partition')
  if not (0<=d['cache_state_words'][0]<=6 and 0<=d['cache_state_words'][1]<=17 and
    d['framing_words'][0] in (3,4,5) and 0<=d['envelope_words'][0]<=5 and 0<=d['envelope_words'][1]<=21): raise ValueError('typed enum protocol')
 else: raise ValueError('unknown Result tag')
 if not integers(d['layouts'],6): raise ValueError('layout diagnostics')
 return d

def attributed_probe(receipt,probe,source):
 if receipt['timed_out'] or receipt['output_truncated'] or receipt['spawn_failure']: return False
 if probe['compile_success_expected']: return receipt['exit_code']==0
 if receipt['exit_code']==0: return False
 primary=[]
 for line in Path(receipt['stderr']).read_text().splitlines():
  d=json.loads(line)
  if d.get('level')=='error' and d.get('spans'): primary.append(d)
 if not primary: return False
 for d in primary:
  code=d['code']['code'] if d.get('code') else None
  if code not in probe['expected_primary_error_codes']: return False
  if not any(s.get('is_primary') and Path(s['file_name'])==source for s in d['spans']): return False
  if probe.get('required_error_text') and probe['required_error_text'] not in d['message']: return False
 return True

def compare_public(d,expected_words,report,context,stream=None):
 """Public observable assertions only; never reads private seeded state."""
 failures=[]
 if d['api_result']!='Ok': return ['unexpected outer Err; exact error retained']
 if d['cache_state_words']!=expected_words:
  failures += [f'word{i}: expected {a} observed {b}' for i,(a,b) in enumerate(zip(expected_words,d['cache_state_words'])) if a!=b]
 if d['aggregate_authority']!=[0]*4 or d['cache_state_words'][26:30]!=[0]*4: failures.append('authority getter became true')
 if d['cache_state_words'][30:]!=[0,0]: failures.append('cache reserved words')
 if d['cache_state_words'][1] in (15,17): failures.append('non-emitting semantic reason')
 f,e=d['framing_words'],d['envelope_words']
 if f[14:]!=[0,0] or e[14:]!=[0,0] or d['envelope_metrics']!=0: failures.append('old false authority getter')
 if d['input_before']!=d['input_after']: failures.append('input metadata changed or unavailable')
 if len(report)!=49152 or d['output_position']!=49152 or d['output_after'] is None or d['output_after'][3]!=49152:
  failures.append('fixed report length/position'); return failures
 import struct
 h=list(struct.unpack('<64Q',report[:512])); echoes=list(struct.unpack('<32Q',context[128:384]))
 expected={0:int.from_bytes(b'MIXANL01','little'),1:1,2:49152,3:f[0],4:0,5:0,6:f[2],9:f[4],
  10:(9 if f[8]==13 else 8) if f[0]==3 else 1 if f[0]==4 else 7,
  15:f[13],22:(1<<64)-1,29:f[8] if 6<=f[8]<=9 else 0,30:f[11]}
 if stream is not None:
  footer=list(struct.unpack('<64Q',stream[-512:]))
  footer_read=bool(f[13]) or f[9]==7
  expected[7]=footer[2] if footer_read else 0
  expected[14]=footer[9] if footer_read else 0
 for index,value in expected.items():
  if h[index]!=value: failures.append(f'report word{index} differs from exact inherited diagnostic projection')
 if h[32:64]!=echoes: failures.append('synthetic report echoes')
 allowed=set(expected)|{7,14}|set(range(32,64))
 if any(h[i] for i in range(64) if i not in allowed) or any(report[512:]): failures.append('report reserved/semantic byte changed')
 if d['layouts'][:5]!=[104,128,232,256,488] or not 488<=d['layouts'][5]<=512: failures.append('fresh layout outside selected bounds')
 return failures
