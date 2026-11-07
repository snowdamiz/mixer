#!/usr/bin/env python3
"""Bounded exact-roster compiler sanity. Main behavior fixture belongs to parent lane."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import selectors
import time
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=Path(__file__).resolve().parent
ROSTER=ROOT/'verification/android-private-owner-effect-roster-amendment/required-host-roster.json'
JAVAC=Path('/opt/homebrew/opt/openjdk/bin/javac')
registry=json.loads(ROSTER.read_text())['closures']['B-concrete-renderer-views']
paths=registry['actual_production_sources']+[item['source'] for item in registry['substitutes']]+registry['test_support_sources']
actual=sorted(str(path.relative_to(ROOT)) for path in (ROOT/'native/android/tests/NativeOwnerV2ConcreteHostLeaves').rglob('*.java'))
expected=sorted([item['source'] for item in registry['substitutes']]+registry['test_support_sources'])
if actual!=expected:raise SystemExit('leaf roster mismatch')
if len(registry['substitutes'])!=73 or len(registry['actual_production_sources'])!=14:raise SystemExit('wrong contract closure')
name=sys.argv[1] if len(sys.argv)>1 else datetime.datetime.now(datetime.timezone.utc).strftime('attempt-%Y%m%dT%H%M%SZ')
if '/' in name or name in ('','.','..'):raise SystemExit('attempt must be one new basename')
out=EVIDENCE/name
out.mkdir(exist_ok=False)
scratch=out/'owned-scratch';classes=scratch/'classes';empty=scratch/'empty';classes.mkdir(parents=True);empty.mkdir()
env={key:value for key,value in os.environ.items() if key not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVAC_OPTS'}}
def hashes():return {path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in paths}
def run(argv,timeout):
 process=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ,'stdout');selector.register(process.stderr,selectors.EVENT_READ,'stderr')
 buffers={'stdout':bytearray(),'stderr':bytearray()};deadline=time.monotonic()+timeout;failure=None
 try:
  while selector.get_map():
   if time.monotonic()>deadline:
    failure='timeout';process.kill();break
   for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:selector.unregister(key.fileobj);continue
    budget=1048576-sum(len(value) for value in buffers.values())
    buffers[key.data].extend(chunk[:budget])
    if len(chunk)>budget:
     failure='output-bound';process.kill();break
   if failure:break
  process.wait(timeout=5)
 finally:
  selector.close();process.stdout.close();process.stderr.close()
 result=subprocess.CompletedProcess(argv,process.returncode,bytes(buffers['stdout']).decode('utf-8','replace'),bytes(buffers['stderr']).decode('utf-8','replace'))
 result.bound_failure=failure
 return result
before=hashes();argv=[str(JAVAC),'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',str(empty),'-sourcepath',str(empty),'-d',str(classes)]+paths
(out/'argv.json').write_text(json.dumps(argv,indent=2)+'\n')
(out/'sources-before.json').write_text(json.dumps(before,indent=2)+'\n')
revision=run(['git','rev-parse','HEAD'],10).stdout.strip()
version=run([str(JAVAC),'-version'],10)
(out/'tool.txt').write_text(version.stdout+version.stderr)
result={'revision':revision,'scope':'14 actual complete production sources + exact 73 mechanical Android/JNI substitutes + one probe; compiler signature sanity only','native_runtime':'not run; paused','process_discovery':'not run; paused','network':'not used','substitutes':73,'production_subjects':14,'argv':'argv.json','output_bound_bytes':1048576,'timeout_seconds':45,'javac_path':str(JAVAC.resolve()),'javac_sha256':hashlib.sha256(JAVAC.resolve().read_bytes()).hexdigest()}
try:
 p=run(argv,45)
 stdout=p.stdout[:1048576];stderr=p.stderr[:1048576]
 (out/'stdout.txt').write_text(stdout);(out/'stderr.txt').write_text(stderr)
 after=hashes();(out/'sources-after.json').write_text(json.dumps(after,indent=2)+'\n')
 result.update(returncode=p.returncode,source_stable=before==after,output_truncated=p.bound_failure=='output-bound',bounded_failure=p.bound_failure)
 result['pass']=p.returncode==0 and before==after and p.bound_failure is None
except subprocess.TimeoutExpired as exc:
 result.update(timeout=True,**{'pass':False});(out/'stderr.txt').write_text(str(exc))
finally:
 shutil.rmtree(scratch)
 result['cleanup']={'owned_scratch':str(scratch.relative_to(ROOT)),'removed':not scratch.exists(),'native_or_capture_instances_started':0,'other_projects_processes_queried_or_changed':False}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
print((out/'stderr.txt').read_text())
raise SystemExit(0 if result['pass'] else 1)
