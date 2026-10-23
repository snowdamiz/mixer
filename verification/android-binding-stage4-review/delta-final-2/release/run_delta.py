#!/usr/bin/env python3
"""Link original delta probes to a separately rebuilt exact frozen module."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,shutil
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['debug','release','tsan'],required=True);a=p.parse_args()
build=HERE/'builds'/('final2-'+a.mode);base_path=build/'receipt.json';base=json.load(open(base_path));out=HERE/'delta-final-2'/a.mode;out.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
result={'source_tree_sha256':base['source_tree_sha256'],'full_rebuild_receipt':str(base_path.relative_to(ROOT)),'full_rebuild_receipt_sha256':sha(base_path),'mode':a.mode,'scope':'Original independent derived host probes against previously rebuilt copied final-2 production module. Duplicate-waiter test uses real register invariant failure and real C callback; it does not prove counter MAX origin. No fabricated fence/success/receipt, no JNI/Looper/device/GA evidence.','commands':[]}
def run(name,argv):
 r=subprocess.run(argv,cwd=ROOT,env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90);log=out/(name+'.log');log.write_bytes(r.stdout);result['commands'].append({'name':name,'argv':argv,'cwd':str(ROOT),'exit':r.returncode,'output':str(log.relative_to(ROOT)),'output_sha256':sha(log)});print(name,r.returncode,flush=True)
 if r.returncode or b'WARNING: ThreadSanitizer' in r.stdout:raise RuntimeError(r.stdout.decode(errors='replace'))
try:
 for rel,h in base['artifacts'].items():assert sha(ROOT/rel)==h,rel
 shutil.copy2(HERE/'DeltaProbes.swift',out/'DeltaProbes.swift');shutil.copy2(__file__,out/'run_delta.py')
 argv=next(x['argv'] for x in base['commands'] if x['name']=='probe-link');argv=[str(out/'DeltaProbes.swift') if x==str(HERE/'ReviewProbes.swift') else str(out/'DeltaProbes') if x==str(build/'Stage4HostTests') else x for x in argv]
 run('delta-link',argv)
 for scenario in ['leased-race','fallback-ids','duplicate-progress-fanout']:run(scenario,[str(out/'DeltaProbes'),scenario])
 result['result']='all three original delta probes passed';result['artifacts']={str((out/'DeltaProbes').relative_to(ROOT)):sha(out/'DeltaProbes')};result['probe_sha256']=sha(out/'DeltaProbes.swift')
except BaseException as e:result['result']='failure retained';result['error']=str(e);raise
finally:result['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
