#!/usr/bin/env python3
"""Bounded host-only replay; native observations and their timestamps are immutable.
A replay clock validates retained event order. Real monotonic clocks measure cost.
No host outcome is a fresh Settings or Tab acceptance receipt.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,secrets,shutil,socket,statistics,subprocess,sys,tempfile,threading,time
HERE=pathlib.Path(__file__).resolve().parent
RUNTIME=HERE/'baseline-runtime/inputs/runtime/verification'
sys.path[:0]=[str(RUNTIME/'apple-toggle-pan-origin-correction'),str(RUNTIME/'apple-toggle-keyboard-focus-v9-preparation')]
import bridge,settings_telemetry,durable_settings

def load_candidate():
 spec=importlib.util.spec_from_file_location('candidate_bridge',HERE/'experiments/http11_bridge.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run():
 scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-settings-host-',dir='/tmp')).resolve()
 report={'scope':'host-only exact retained V9 prefix; no simulator, no fresh native evidence','scratch':str(scratch),'runs':[],'commands':[]}
 try:
  actual=HERE.parent/'apple-runtime';result=json.loads((actual/'result.json').read_text()); captures=actual/result['artifacts']['rawCaptures']
  rows=[json.loads(p.read_text()) for p in sorted(captures.glob('0000-settings-*.json'))]
  records=[r['record'] for r in rows]; inp=scratch/'records.json';inp.write_text(json.dumps(records))
  report['inputRows']=len(records);report['inputSHA256']=hashlib.sha256(inp.read_bytes()).hexdigest()
  argv=['/usr/bin/xcrun','swiftc','-swift-version','6',str(HERE/'host_probe.swift'),'-o',str(scratch/'probe')]
  began=time.monotonic();p=subprocess.run(argv,capture_output=True,timeout=90,env={**os.environ,'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer'})
  report['commands'].append({'argv':argv,'exitCode':p.returncode,'elapsedSeconds':time.monotonic()-began,'stderr':p.stderr.decode()});assert p.returncode==0
  for mode in ['baseline-echo','candidate-echo','baseline-durable','candidate-durable']:
   output=scratch/mode;output.mkdir(); index=[0];server_times=[];costs=[]
   store=durable_settings.TransactionStore(output,rows[0]['ownedSimulatorIdentity'])
   session=settings_telemetry.Session(None,None,rows[0]['sessionDeadlineUptime'],now=lambda:rows[index[0]]['receivedUptime'],token=rows[0]['generation'],transaction=store)
   class Receiver:
    capability=secrets.token_urlsafe(32)
    def record_failure(self,*args):raise AssertionError(str(args))
    def request(self,op,body):
     began=time.monotonic()
     if mode.endswith('durable'):
      try:value=session.request(body['settingsDiagnostic'])
      except Exception as e: print(type(e).__name__,str(e),flush=True);raise
     else:value={'accepted':True}
     costs.append(time.monotonic()-began);server_times.append(time.monotonic());index[0]+=1;return value
   recv=Receiver();module=load_candidate() if mode.startswith('candidate') else bridge
   server=module.server_for(recv);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   argv=[str(scratch/'probe'),str(inp),f'http://127.0.0.1:{server.server_port}/evaluate'];began=time.monotonic()
   try:
    proc=subprocess.run(argv,capture_output=True,timeout=40,env={**os.environ,'MIXER_HOST_PROBE_CAPABILITY':recv.capability})
    elapsed=time.monotonic()-began
   finally:
    server.shutdown();server.server_close();thread.join(timeout=3)
   (HERE/(mode+'.stdout.json')).write_bytes(proc.stdout);(HERE/(mode+'.stderr.log')).write_bytes(proc.stderr)
   assert proc.returncode==0,(mode,proc.stderr)
   times=json.loads(proc.stdout)
   report['runs'].append({'mode':mode,'argv':[argv[0],argv[1],'http://127.0.0.1:<ephemeral-port>/evaluate'],'exitCode':proc.returncode,'elapsedSeconds':elapsed,'requests':index[0],
    'serializationSeconds':sum(x['serializationSeconds'] for x in times),'requestSeconds':sum(x['requestSeconds'] for x in times),'medianRequestSeconds':statistics.median(x['requestSeconds'] for x in times),
    'receiverSeconds':sum(costs),'receiverPerRequestSeconds':costs,'serverClosed':True,'threadJoined':not thread.is_alive(),
    'acceptedCursor':session.sequence if mode.endswith('durable') else None,'nativeEvidenceComplete':False})
   (HERE/'host-probe.json').write_text(json.dumps(report,indent=2)+'\n')
 finally:
  shutil.rmtree(scratch);report['scratchRemoved']=not scratch.exists();(HERE/'host-probe.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({**report,'runs':[{k:v for k,v in r.items() if k!='receiverPerRequestSeconds'} for r in report['runs']]},indent=2))
if __name__=='__main__':run()
