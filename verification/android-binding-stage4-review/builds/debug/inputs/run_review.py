#!/usr/bin/env python3
"""Independent original probes rebuilt from the read-only producer snapshot."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['debug','release','tsan'],default='release');args=parser.parse_args()
SOURCE=HERE/'candidate-1/source'; OUT=HERE/'builds'/args.mode; OUT.mkdir(parents=True,exist_ok=False)
FROZEN=json.loads((HERE/'candidate-1/producer-receipt.json').read_text())
OLD=ROOT/'verification/android-binding-stage4/.build/release-candidate-1'
sha=lambda path:hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
receipt={'scope':'Independent host-only copied-source review. Exact production Swift/C transport rebuilt. Retained producer dependency objects not rebuilt or sanitizer-instrumented. No JNI, Android Looper, physical device, signed-core integration or GA authority.','mode':args.mode,'source_tree_sha256':FROZEN['source_tree_sha256'],'source_files':FROZEN['source_files'],'dependency_receipt':FROZEN['dependency_receipt'],'dependency_receipt_sha256':FROZEN['dependency_receipt_sha256'],'dependency_artifacts':FROZEN['dependency_artifacts'],'review_probe_sha256':sha(HERE/'ReviewProbes.swift'),'review_runner_sha256':sha(__file__),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],'artifacts':{},'cases_executed':[]}
def verify():
 for rel,digest in FROZEN['source_files'].items(): assert sha(SOURCE/rel)==digest,rel
def run(name,argv):
 verify(); start=time.monotonic(); env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
 try:
  process=subprocess.run([str(x) for x in argv],cwd=SOURCE,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);data=process.stdout;status=process.returncode
 except subprocess.TimeoutExpired as error:data=(error.stdout or b'')+b'\nTIMEOUT\n';status=124
 log=OUT/(name+'.log');log.write_bytes(data)
 receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(SOURCE),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit':status,'seconds':time.monotonic()-start,'output':str(log.relative_to(ROOT)),'output_sha256':sha(log)})
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(name,status,flush=True); verify()
 if status or b'WARNING: ThreadSanitizer' in data: print(data.decode(errors='replace')); raise RuntimeError(name)
 return data
def transform(argv):
 result=[]
 for argument in argv:
  argument=argument.replace(str(OLD/'source'),str(SOURCE)).replace(str(OLD),str(OUT))
  if 'swift-cache' in argument: argument=str(OUT/'swift-cache')
  result.append(argument)
 return result
try:
 run('swift-version',['xcrun','swiftc','--version']);run('clang-version',['xcrun','clang','--version']);run('platform',['uname','-a'])
 for name in ['transport-compile','host_bridge-compile']:
  argv=transform(next(x['argv'] for x in FROZEN['commands'] if x['name']==name))
  if args.mode!='release':
   argv=[x for x in argv if x!='-O2']; argv[2:2]=['-O0'] if args.mode=='debug' else ['-O1','-fsanitize=thread']
  run(name,argv)
 argv=transform(next(x['argv'] for x in FROZEN['commands'] if x['name']=='full-module-link'))
 if args.mode!='release':
  argv=[x for x in argv if x!='-O'];argv[2:2]=['-Onone'] if args.mode=='debug' else ['-sanitize=thread']
 run('full-module-link',argv)
 argv=transform(next(x['argv'] for x in FROZEN['commands'] if x['name']=='harness-link'))
 argv=[x for x in argv if not x.endswith('/HostTests.swift') and not x.endswith('/HoldingExecutor.swift')]
 argv.insert(argv.index('-L'),str(HERE/'ReviewProbes.swift'))
 if args.mode!='release':
  argv=[x for x in argv if x!='-O'];argv[2:2]=['-Onone'] if args.mode=='debug' else ['-sanitize=thread']
 run('probe-link',argv)
 for scenario in ['drop-failed-retire','drop-transferred','destructor-contention']:
  data=run(scenario,[OUT/'Stage4HostTests',scenario]);assert b'REVIEW_PROBE_PASS' in data
  receipt['cases_executed'].append(scenario)
 for name in ['libMixerAndroidStage4.dylib','Stage4HostTests']:receipt['artifacts'][str((OUT/name).relative_to(ROOT))]=sha(OUT/name)
 receipt['result']='independent retention/destructor probes passed; transferred abandonment gap reproduced'
except BaseException as error:receipt['result']='failed review retained';receipt['error']=str(error);raise
finally:
 receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
