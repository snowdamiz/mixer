#!/usr/bin/env python3
"""Fresh synthetic host probes. No producer fixtures/test helpers or native execution."""
import base64, copy, hashlib, http.client, importlib.util, json, math, pathlib, shutil, struct, sys, tempfile, threading, unittest, zlib
from unittest import mock
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/apple-toggle-keyboard-focus-v6-preparation'
sys.path.insert(0,str(P))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
run=load('fresh_v6_run',P/'run.py'); t=run.settings_telemetry
replay=load('fresh_v6_replay',P/'replay.py')
SCRATCH=HERE/'.scratch';SCRATCH.mkdir(exist_ok=True)
REASON='Route opened capture precedes same-route tap completion'
PROBES=[]
def png():
 def c(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+c(b'IDAT',zlib.compress(b'\x00\x00\x00\x00\xff'))+c(b'IEND',b'')
class Emitter:
 def __init__(self):
  self.tmp=tempfile.TemporaryDirectory(dir=SCRATCH,prefix='fresh-');self.root=pathlib.Path(self.tmp.name)
  docs=self.root/'documents';docs.mkdir()
  self.bridge=run.h.Bridge({'diagnostic':docs,'comparator':docs},self.root/'journal','fresh-review-capability',{'syntheticHostOnly':True},allowed_cases=run.keyboard_oracle.CASES)
  self.host=200.;self.uptime=20.;self.search={};self.taps={}
  self.bridge.settings.now=lambda:self.host;self.bridge.settings.deadline=800.
  self.send({'kind':'start','case':t.CASE,'uptime':self.uptime})
 def close(self):self.tmp.cleanup()
 def send(self,r):return self.bridge.request('evaluate',{'settingsDiagnostic':r})
 def record(self,kind,**extra):
  self.host+=.001;self.uptime+=.02
  return dict(kind=kind,case=t.CASE,generation=self.bridge.settings.token,sequence=self.bridge.settings.sequence+1,uptime=self.uptime,**extra)
 def mark(self,stage,detail=None):
  r=self.record('mark',stage=stage,detail={} if detail is None else detail);self.send(r);return r
 def snap(self,stamp,**extra):
  return dict(bundle='com.apple.Preferences',foreground=True,appState=4,observedUptime=stamp,identifier='FKAEnabledSwitch',label='Full Keyboard Access',elementType=40,exists=True,hittable=True,enabled=True,valueKind='string',value='0',frame=dict(x=5,y=50,width=350,height=60),**extra)
 def observation(self,stage,index=3,initial='0',start=None,send=True):
  start=self.uptime+.001 if start is None else start
  raw=self.snap(start+.0002);raw['value']=initial
  payload={} if stage=='poll' else {'ax':b'Fresh independent synthetic hierarchy; no native capture\n'}
  witness=None
  if stage=='route-search':
   raw.update(identifier='',label=t.ROUTE[index],elementType=75,valueKind='unsupported',value='')
   target=copy.deepcopy(raw);target.update(identifier='',label=t.ROUTE[index],elementType=48,frame=dict(x=10,y=60,width=300,height=30))
   witness={'relation':'descendant','target':target}
  if stage=='route-opened':
   raw.update(identifier='',label='',elementType=0,exists=False,hittable=False,enabled=False,valueKind='absent',value='',frame=dict(x=0,y=0,width=0,height=0))
   dest=copy.deepcopy(raw);dest.update(identifier=t.ROUTE[index],elementType=21,exists=True,enabled=True,frame=dict(x=0,y=0,width=400,height=44))
   witness={'destination':dest}
  if stage in ['before-switch','after-switch','terminal']:payload['png']=png()
  r=self.record('observe',stage=stage,routeIndex=index,attempt=0,captureStartedUptime=start,captureFinishedUptime=start+.0004,snapshot=raw,files={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in payload.items()})
  if witness:r['routeWitness']=witness
  if send:self.send(r);self.upload(payload)
  if stage=='route-search' and send:self.search[index]=r
  return r,payload
 def upload(self,payload):
  for slot in list(self.bridge.settings.pending):
   fmt=slot.rsplit('-',1)[1];data=payload[fmt];desc=self.bridge.settings.uploads[slot]
   for n in range(desc['count']):self.send(self.record('chunk',slot=slot,index=n,count=desc['count'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),data=base64.b64encode(data[n*t.CHUNK:(n+1)*t.CHUNK]).decode()))
 def tap_record(self,index):
  target=copy.deepcopy(self.search[index]['routeWitness']['target']);target['observedUptime']=self.uptime+.001
  return self.record('mark',stage='route-tap',detail=dict(routeIndex=index,searchSequence=self.search[index]['sequence'],target=target,startedUptime=self.uptime+.002,finishedUptime=self.uptime+.010))
 def tap(self,index):
  r=self.tap_record(index);self.send(r);self.taps[index]=r;return r
 def ready(self,index=0):
  self.mark('settings-launched')
  for i in range(index):self.observation('route-search',i);self.tap(i);self.observation('route-opened',i)
  self.observation('route-search',index);self.tap(index)
 def finish(self,initial='0'):
  self.mark('settings-launched')
  for i in range(3):self.observation('route-search',i);self.tap(i);self.observation('route-opened',i)
  self.observation('before-switch',initial=initial)
  anchor=self.uptime+.001 if initial=='0' else self.bridge.settings.before['snapshot']['observedUptime']
  self.mark('switch-action',dict(action='tap' if initial=='0' else 'no-tap',anchorUptime=anchor,deadlineUptime=anchor+3.))
  self.observation('after-switch',initial='1');self.observation('terminal',initial='1')
  for stage in ['terminate-before','terminate-after','test-case-finished','suite-finished','bundle-finished']:self.mark(stage)
 def state(self):return copy.deepcopy({k:v for k,v in self.bridge.settings.__dict__.items() if k not in ['persist','persist_file','now']})
 def journal(self):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.bridge.output.iterdir() if p.name.startswith('0000-settings-') or p.name.startswith('settings-')}
class FreshTests(unittest.TestCase):
 def flow(self):
  f=Emitter();self.addCleanup(f.close);return f
 def rejection(self,f,r,reason=REASON,replay_equal=True):
  state=f.state();journal=f.journal();failures=len(f.bridge.failures)
  with self.assertRaisesRegex(ValueError,reason):f.send(r)
  self.assertEqual(f.state(),state);self.assertEqual(f.journal(),journal)
  self.assertEqual(len(f.bridge.failures),failures+1)
  self.assertIn(reason,f.bridge.failures[-1]['reason'])
  if replay_equal:self.assertEqual(f.bridge.settings.summary(),replay.replay(f.bridge.output))
  self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])
 def test_01_boundary_matrix_real_bridge_and_offline_replay(self):
  for index in range(3):
   for boundary in ['before-start','during','just-before-finish','equal-finish','just-after-finish']:
    with self.subTest(route=index,boundary=boundary):
     f=self.flow();f.ready(index);tap=f.taps[index];d=tap['detail']
     stamp={'before-start':math.nextafter(d['startedUptime'],-math.inf),'during':(d['startedUptime']+d['finishedUptime'])/2,'just-before-finish':math.nextafter(d['finishedUptime'],-math.inf),'equal-finish':d['finishedUptime'],'just-after-finish':math.nextafter(d['finishedUptime'],math.inf)}[boundary]
     r,p=f.observation('route-opened',index,start=stamp,send=False)
     self.assertGreater(stamp,f.search[index]['captureFinishedUptime'])
     if stamp<d['finishedUptime']:self.rejection(f,r);accepted=False
     else:
      f.send(r);f.upload(p);b=f.bridge.settings.route_opened_bindings[index]
      self.assertEqual((b['routeIndex'],b['tapSequence'],b['tapFinishedUptime'],b['captureStartedUptime']),(index,tap['sequence'],d['finishedUptime'],stamp))
      self.assertTrue(b['destinationMatched']);self.assertEqual(f.bridge.settings.summary(),replay.replay(f.bridge.output));accepted=True
     PROBES.append(dict(route=index,boundary=boundary,accepted=accepted,tapSequence=tap['sequence'],tapFinishedUptime=d['finishedUptime'],captureStartedUptime=stamp))
 def test_02_wire_route_and_search_sequence_binding(self):
  for index in range(3):
   for mutation in ['route','search-sequence','tap-time']:
    f=self.flow();f.mark('settings-launched')
    for i in range(index):f.observation('route-search',i);f.tap(i);f.observation('route-opened',i)
    f.observation('route-search',index);r=f.tap_record(index)
    if mutation=='route':r['detail']['routeIndex']=(index+1)%3;reason='Route tap order'
    elif mutation=='search-sequence':r['detail']['searchSequence']-=1;reason='Tap search sequence binding'
    else:r['detail']['finishedUptime']=r['detail']['startedUptime']-.001;reason='Tap target timing'
    self.rejection(f,r,reason)
 def test_03_current_route_completion_required_after_previous_route(self):
  for index in range(3):
   f=self.flow();f.ready(index);s=f.bridge.settings;binding=s.route_bindings[index]
   self.assertEqual(binding['finishedUptime'],f.taps[index]['detail']['finishedUptime'])
   self.assertEqual(binding['searchSequence'],f.search[index]['sequence'])
   stamp=f.search[index]['captureFinishedUptime']+.0001
   earlier=f.taps[index-1]['detail']['finishedUptime'] if index else s.start_runner
   self.assertLess(earlier,stamp);self.assertLess(stamp,binding['finishedUptime'])
   r,_=f.observation('route-opened',index,start=stamp,send=False);self.rejection(f,r)
 def test_04_internal_wrong_route_or_nonpreceding_sequence_fails_closed(self):
  for index in range(3):
   for key in ['routeIndex','tapSequence']:
    f=self.flow();f.ready(index);r,_=f.observation('route-opened',index,start=f.taps[index]['detail']['finishedUptime'],send=False)
    b=f.bridge.settings.route_bindings[index];original=copy.deepcopy(b);b[key]=(index+1)%3 if key=='routeIndex' else r['sequence']
    self.rejection(f,r,'Route opened same-route tap sequence',replay_equal=False)
    b.clear();b.update(original)
    self.assertEqual(f.bridge.settings.summary(),replay.replay(f.bridge.output))
 def test_05_http_stale_each_route_keeps_cursor_and_rejection_reason(self):
  for index in range(3):
   f=self.flow();f.ready(index);r,_=f.observation('route-opened',index,start=math.nextafter(f.taps[index]['detail']['finishedUptime'],-math.inf),send=False)
   state=f.state();journal=f.journal();server=run.h.server_for(f.bridge);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
   try:
    client.request('POST','/evaluate',json.dumps({'settingsDiagnostic':r}),headers={'X-Mixer-Capability':'fresh-review-capability','Content-Type':'application/json'})
    response=client.getresponse();payload=response.read();self.assertEqual(response.status,400);self.assertLessEqual(len(payload),8192);self.assertIn(REASON,payload.decode())
   finally:client.close();server.shutdown();server.server_close();thread.join(3)
   self.assertFalse(thread.is_alive());self.assertEqual(f.state(),state);self.assertEqual(f.journal(),journal);self.assertEqual(f.bridge.settings.summary(),replay.replay(f.bridge.output))
 def test_06_persist_rejection_preserves_route_clock_uploads_and_cursor(self):
  for index in range(3):
   f=self.flow();f.ready(index);r,p=f.observation('route-opened',index,start=f.taps[index]['detail']['finishedUptime'],send=False);state=f.state();journal=f.journal()
   original=f.bridge.save
   def fail_selected(suffix,value):
    if suffix=='settings-'+format(r['sequence'],'04d'):raise OSError('fresh selected journal failure')
    return original(suffix,value)
   with mock.patch.object(f.bridge,'save',side_effect=fail_selected):
    with self.assertRaisesRegex(OSError,'fresh selected journal failure'):f.send(r)
   self.assertEqual(f.state(),state);self.assertEqual(f.journal(),journal)
   f.send(r);f.upload(p);self.assertEqual(f.bridge.settings.summary(),replay.replay(f.bridge.output))
 def test_07_mutated_durable_opened_each_route_rejects(self):
  for index in range(3):
   f=self.flow();f.finish();paths=sorted(f.bridge.output.glob('0000-settings-*.json'))
   path=next(p for p in paths if (lambda r:r.get('stage')=='route-opened' and r['routeIndex']==index)(json.loads(p.read_bytes())['record']))
   saved=json.loads(path.read_bytes());r=saved['record'];start=math.nextafter(f.taps[index]['detail']['finishedUptime'],-math.inf)
   r.update(captureStartedUptime=start,captureFinishedUptime=start+.0004);r['snapshot']['observedUptime']=start+.0002;r['routeWitness']['destination']['observedUptime']=start+.0002
   path.write_text(json.dumps(saved))
   with self.assertRaisesRegex(ValueError,REASON):replay.replay(f.bridge.output)
 def test_08_valid_initial_off_and_on_keep_diagnostic_only_authority(self):
  for initial in ['0','1']:
   f=self.flow();f.finish(initial);s=f.bridge.settings.summary();self.assertTrue(s['setupObservationSatisfied']);self.assertEqual(s,replay.replay(f.bridge.output))
   r=run.summary('interaction',f.bridge,0,{'type':'ValueError','message':'Strict XCTest result failed; preserved evidence is authoritative'},[])
   self.assertTrue(r['expectedDiagnosticQualificationBoundary']);self.assertEqual(r['applicationCasesExecuted'],0);self.assertEqual(len(r['dependentCasesUnrun']),6)
   self.assertEqual(s['observationDeadlineUptime'],s['anchorUptime']+3.)
   for k in ['runPassed','nativeKeyboardQualification','carrierAccepted','gaAccepted','strictNativeVerdictsPassed']:self.assertIs(r[k],False)
 def test_09_bounds_and_anchor_rejection_remain_fixed(self):
  self.assertEqual((t.CHUNK,t.MAX_TOTAL,t.MAX_REQUESTS,t.MAX_EVENTS,t.MAX_UPLOADS,t.MAX_DURATION),(3072,7000000,2500,100,32,29.))
  f=self.flow();f.finish();r=f.record('mark',stage='switch-action',detail=dict(action='tap',anchorUptime=f.uptime,deadlineUptime=f.uptime+3.))
  state=f.state();journal=f.journal()
  with self.assertRaisesRegex(ValueError,'Action after terminal'):f.send(r)
  self.assertEqual(f.state(),state);self.assertEqual(f.journal(),journal)
 def test_10_exact_frozen_v5_stale_journal_v6_rejects_unchanged(self):
  cap=ROOT/'verification/apple-toggle-keyboard-focus-v5-independent-review/witnesses/pre-tap-destination/captures'
  before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cap.iterdir() if p.is_file()}
  self.assertEqual(len(before),45)
  with self.assertRaisesRegex(ValueError,REASON):replay.replay(cap)
  self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cap.iterdir() if p.is_file()})
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FreshTests))
 (HERE/'fresh-boundary-matrix.json').write_text(json.dumps({'syntheticHostOnly':True,'nativeExecuted':False,'probes':PROBES},indent=2,sort_keys=True)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
