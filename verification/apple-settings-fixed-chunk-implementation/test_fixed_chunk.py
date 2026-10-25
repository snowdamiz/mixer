"""Actual selected receiver controls. All Settings records/files are synthetic."""
import base64,copy,hashlib,importlib.util,json,math,pathlib,struct,types,unittest,zlib
import fixtures as f
import settings_telemetry as t
import replay
B=pathlib.Path(__file__).resolve().parent
RESULTS=[]

def state(s):return copy.deepcopy({k:v for k,v in vars(s).items() if k not in ['persist','persist_file','transaction','now']})
def memory():
 journals=[];files=[];clock=[100.0]
 s=t.Session(lambda a,b:journals.append((a,b)),lambda a,b,c:files.append((a,b,c)),129.0,now=lambda:clock[0],token='ffffffff-ffff-ffff-ffff-ffffffffffff')
 return s,journals,files,clock

def started():
 s,j,p,c=memory();r={'kind':'start','case':t.CASE,'uptime':10.0,'chunkBytes':4992};s.request(r);return s,j,p,c

def seeded(data,form='ax'):
 s,j,p,c=started();slot='settings-0001-'+form
 s.pending=[slot];s.uploads[slot]={'format':form,'bytes':len(data),'sha256':t.sha(data),'count':(len(data)+4991)//4992,'parts':[],'complete':False}
 return s,j,p,c,slot

def chunk(s,slot,data,index=0):
 item=s.uploads[slot]
 return dict(kind='chunk',case=t.CASE,generation=s.token,sequence=s.sequence+1,uptime=10.1,slot=slot,index=index,count=item['count'],bytes=len(data),sha256=t.sha(data),data=base64.b64encode(data[index*4992:(index+1)*4992]).decode())

def png_bytes(size):
 def block(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
 basic=f.image();assert size>=len(basic)+12
 return basic[:-12]+block(b'tEXt',(bytes(range(256))*((size-len(basic)-12+255)//256))[:size-len(basic)-12])+basic[-12:]

class FixedChunkTests(unittest.TestCase):
 def reject(self,s,j,p,r):
  before=state(s);journals=copy.deepcopy(j);files=copy.deepcopy(p)
  with self.assertRaises((ValueError,UnicodeError,TypeError,OverflowError)):s.request(r)
  self.assertEqual(before,state(s));self.assertEqual(journals,j);self.assertEqual(files,p)
 def test_exact_format_start_and_old_new_incompatibility(self):
  for bad in ['missing',None,True,False,4992.0,'4992',3072,4096,4993,0,-1,[],{}]:
   s,j,p,c=memory();r={'kind':'start','case':t.CASE,'uptime':10.0,'chunkBytes':bad}
   if bad=='missing':del r['chunkBytes']
   self.reject(s,j,p,r);self.assertIsNone(s.start_host);self.assertEqual(s.requests,0)
  s,j,p,c=memory();reply=s.request({'kind':'start','case':t.CASE,'uptime':10.0,'chunkBytes':4992})
  self.assertIs(type(reply['chunkBytes']),int);self.assertEqual(reply['chunkBytes'],4992)
  original=B/'original-host.py'
  with __import__('tarfile').open(B/'inputs/selected-sources.tar.gz') as a:raw=a.extractfile('selected/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py').read()
  ns={'__name__':'original_frozen_settings'};exec(compile(raw,str(original),'exec'),ns)
  old=ns['Session'](lambda *a:None,lambda *a:None,129,now=lambda:100)
  with self.assertRaisesRegex(ValueError,'Setup start'):old.request({'kind':'start','case':t.CASE,'uptime':10.0,'chunkBytes':4992})
  self.assertEqual(old.requests,0);self.assertIsNone(old.start_host)
 def test_actual_admission_boundaries_reassembly_bytes_hash_and_exact_last(self):
  for form,sizes in [('ax',[1,4991,4992,4993,9984,14976,200000]),('png',[4991,4992,4993,9984,2000000])]:
   for size in sizes:
    flow=f.Flow();data=(b'X'*size) if form=='ax' else png_bytes(size)
    if form=='png':flow.routes();r,payloads=flow.observe('before-switch',upload=False);payloads['png']=data
    else:r,payloads=flow.observe('route-search',index=0,upload=False);payloads['ax']=data
    r['files']={k:dict(bytes=len(v),sha256=t.sha(v)) for k,v in payloads.items()}
    flow.send(r);slot=f"settings-{r['sequence']:04d}-{form}"
    self.assertEqual(flow.bridge.settings.uploads[slot]['count'],(size+4991)//4992)
    flow.upload(payloads)
    dest=flow.bridge.output/(slot+('.png' if form=='png' else '.txt'))
    self.assertEqual(dest.read_bytes(),data);self.assertEqual(t.sha(dest.read_bytes()),t.sha(data));self.assertFalse(flow.bridge.settings.pending)
    self.assertEqual(flow.bridge.settings.summary(),replay.replay(flow.bridge.output))
    rows=[json.loads(p.read_bytes())['record'] for p in sorted(flow.bridge.output.glob('0000-settings-*.json'))]
    parts=[r for r in rows if r['kind']=='chunk' and r['slot']==slot]
    self.assertEqual([r['index'] for r in parts],list(range(len(parts))))
    self.assertEqual(len(base64.b64decode(parts[-1]['data'],validate=True)),size-4992*(len(parts)-1))
    self.assertTrue(all(len(r['data'])<=6656 for r in parts));self.assertLessEqual(len(parts),401 if form=='png' else 41)
    RESULTS.append(dict(control='actual-admission-boundary',format=form,bytes=size,chunks=len(parts),lastBytes=len(base64.b64decode(parts[-1]['data'])),sha256=t.sha(data)))
 def test_malformed_fragments_and_no_state_advance(self):
  data=b'A'*4993
  mutations={
   'wrong-slot':lambda r:r.update(slot='settings-0002-ax'),
   'wrong-index':lambda r:r.update(index=1),'boolean-index':lambda r:r.update(index=False),'oversized-index':lambda r:r.update(index=401),
   'wrong-count':lambda r:r.update(count=3),'boolean-count':lambda r:r.update(count=True),'float-count':lambda r:r.update(count=2.0),
   'wrong-bytes':lambda r:r.update(bytes=4992),'float-bytes':lambda r:r.update(bytes=4993.0),'wrong-hash':lambda r:r.update(sha256='f'*64),
   'missing-data':lambda r:r.pop('data'),'extra-field':lambda r:r.update(chunkBytes=4992),
   'old-size':lambda r:r.update(data=base64.b64encode(data[:3072]).decode()),'mixed-short':lambda r:r.update(data=base64.b64encode(data[:4096]).decode()),
   'oversized':lambda r:r.update(data=base64.b64encode(data).decode()),'garbage':lambda r:r.update(data='!'),
   'whitespace':lambda r:r.update(data=r['data']+'\n'),'extra-padding':lambda r:r.update(data=r['data']+'='),
   'wrong-type':lambda r:r.update(data=1),'empty':lambda r:r.update(data=''),
  }
  for name,mutate in mutations.items():
   s,j,p,c,slot=seeded(data);r=chunk(s,slot,data);mutate(r);self.reject(s,j,p,r);RESULTS.append(dict(control='reject-no-advance',case=name))
  s,j,p,c,slot=seeded(data);first=chunk(s,slot,data);s.request(first)
  duplicate=copy.deepcopy(first);duplicate['sequence']=s.sequence+1;self.reject(s,j,p,duplicate)
  last=chunk(s,slot,data,1);last['data']='QR==' # noncanonical pad bits for b'A'
  self.reject(s,j,p,last)
  last=chunk(s,slot,data,1);last['data']='QQ' # missing canonical padding
  self.reject(s,j,p,last)
  self.assertFalse(s.summary()['settingsEvidenceComplete'])
  # Correct canonical final fragment must still accept at the same cursor.
  s.request(chunk(s,slot,data,1));self.assertEqual(p[0][2],data)
 def test_corrupted_complete_payload_png_utf8_and_hash_do_not_publish(self):
  for data,form in [(b'bad png','png'),(b'\xff','ax'),(b'\x00','ax'),(f.image()[:-1]+b'X','png')]:
   s,j,p,c,slot=seeded(data,form);self.reject(s,j,p,chunk(s,slot,data))
  data=b'A';s,j,p,c,slot=seeded(data);s.uploads[slot]['sha256']='f'*64;r=chunk(s,slot,data);r['sha256']='f'*64;self.reject(s,j,p,r)
 def test_limits_request_total_upload_event_poll_and_both_deadlines(self):
  for cap in ['requests','total','uploads','events']:
   flow=f.Flow()
   if cap=='requests':flow.bridge.settings.requests=2500;r=flow.record('mark',stage='settings-launched',detail={})
   else:
    r,_=flow.observe('route-search',index=0,upload=False)
    if cap=='total':flow.bridge.settings.total=7000000
    if cap=='uploads':flow.bridge.settings.uploads={str(i):{} for i in range(32)}
    if cap=='events':flow.bridge.settings.events=[{}]*100
   before=state(flow.bridge.settings)
   with self.assertRaises(ValueError):flow.send(r)
   self.assertEqual(before,state(flow.bridge.settings))
  flow=f.Flow();flow.before();flow.action();flow.observe('after-switch',value='1')
  for _ in range(40):flow.observe('poll',value='1')
  r,_=flow.observe('poll',value='1',upload=False)
  with self.assertRaisesRegex(ValueError,'Poll stage/count'):flow.send(r)
  for form,limit in [('ax',200000),('png',2000000)]:
   flow=f.Flow();flow.routes();r,_=flow.observe('before-switch',upload=False);r['files'][form]['bytes']=limit+1
   with self.assertRaisesRegex(ValueError,'File descriptor'):flow.send(r)
  for boundary in [129.0,math.nextafter(129.0,math.inf)]:
   s,j,p,c=started();c[0]=boundary;self.reject(s,j,p,dict(kind='mark',case=t.CASE,generation=s.token,sequence=1,uptime=11.0,stage='settings-launched',detail={}))
  for bad in [math.nextafter(39.0,math.inf),math.inf,math.nan,-1.0]:
   s,j,p,c=started();self.reject(s,j,p,dict(kind='mark',case=t.CASE,generation=s.token,sequence=1,uptime=bad,stage='settings-launched',detail={}))
 def test_valid_full_proof_retry_and_each_required_field_omitted(self):
  flow=f.Flow();flow.mark('settings-launched')
  for i in range(3):
   if i==0:flow.observe('route-search',index=i,attempt=0)
   flow.observe('route-search',index=i,attempt=1 if i==0 else 0);flow.tap(i);flow.observe('route-opened',index=i)
  flow.observe('before-switch');flow.action();flow.observe('after-switch',value='1');flow.observe('terminal',value='1');flow.completion()
  self.assertTrue(f.strict_summary('host',flow.bridge)['diagnosticCompleted'])
  records=[json.loads(p.read_bytes()) for p in sorted(flow.bridge.output.glob('0000-settings-*.json'))]
  def replay_records(values):
   clock=[records[0]['receivedUptime']];s=t.Session(lambda *a:None,lambda *a:None,500,now=lambda:clock[0],token=flow.bridge.settings.token)
   for row in values:clock[0]=row['receivedUptime'];s.request(row['record'])
   summary=s.summary();return summary['setupObservationSatisfied'] and summary['terminationMarkers']==['terminate-before','terminate-after'] and summary['completionMarkers']==['test-case-finished','suite-finished','bundle-finished']
  self.assertTrue(replay_records(records));omitted=0;invalidated=0;stale=0
  def paths(value,prefix=()):
   if type(value) is dict:
    for key,nested in value.items():
     yield prefix+(key,)
     yield from paths(nested,prefix+(key,))
  def altered(values,index,path,remove=False):
   target=values[index]['record']
   for key in path[:-1]:target=target[key]
   if remove:del target[path[-1]]
   else:target[path[-1]]=None
  def fail_closed(values,label):
   try:accepted=replay_records(values)
   except (ValueError,KeyError,TypeError,UnicodeError,AttributeError):accepted=False
   self.assertFalse(accepted,label)
  for index,row in enumerate(records):
   if row['record']['kind']=='chunk':continue
   for path in paths(row['record']):
    for remove in [True,False]:
     values=copy.deepcopy(records);altered(values,index,path,remove)
     fail_closed(values,(index,path,remove))
     if remove:omitted+=1
     else:invalidated+=1
   # Explicit stale times for every capture and nested route/switch snapshot.
   for path in paths(row['record']):
    if path[-1] not in ['observedUptime','captureStartedUptime','captureFinishedUptime','startedUptime','finishedUptime','anchorUptime','deadlineUptime']:continue
    values=copy.deepcopy(records);target=values[index]['record']
    for key in path[:-1]:target=target[key]
    target[path[-1]]=0.0
    fail_closed(values,('stale',index,path));stale+=1
   values=copy.deepcopy(records);del values[index]
   try:accepted=replay_records(values)
   except (ValueError,KeyError,TypeError,UnicodeError):accepted=False
   self.assertFalse(accepted,index)
  flow.witness('valid-full-proof-with-retry',dict(requiredFieldsOmittedControls=omitted,requiredFieldsInvalidControls=invalidated,staleTimingControls=stale,routeAXCaptures=7,syntheticHostOnly=True))
  RESULTS.append(dict(control='strict-full-proof',requiredFieldsOmitted=omitted,requiredFieldsInvalid=invalidated,staleTiming=stale,routeAXCaptures=7,nativePassed=False))
 def test_runtime_binding_guards_exact_source_and_spoofed_code(self):
  path=B/'sources/selected/runtime_bindings.py';spec=importlib.util.spec_from_file_location('fixed_guard',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  base=B/'sources';files={name:row['sha256'] for name,row in json.loads((B/'source-bindings.json').read_bytes())['derivativeFiles'].items()}
  guard=m.RuntimeBindings(base,dict(files=files,moduleAliases={'settings_telemetry':'selected/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py','durable_settings':'selected/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py'}))
  guard.check();guard.module(t);guard.check([t])
  forged=types.ModuleType('forged');forged.__file__=t.__file__;forged.__spec__=t.__spec__
  exec(compile('def impostor():pass','/outside/selected-origin.py','exec'),forged.__dict__)
  with self.assertRaisesRegex(ValueError,'outside selected origin'):guard.module(forged)

if __name__=='__main__':unittest.main(verbosity=2)
