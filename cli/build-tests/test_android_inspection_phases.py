import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
DRIVER=ROOT/'cli/Sources/MixerBuild/Resources/android-build.py'
if not DRIVER.exists():
 DRIVER=Path(__file__).resolve().parent/'candidate/cli/Sources/MixerBuild/Resources/android-build.py'
def module(path):
 spec=importlib.util.spec_from_file_location('inspection_test_'+str(id(path)),path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class InspectionPhaseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.trace=self.root/'trace';self.trace.mkdir(mode=0o700)
  self.m=module(DRIVER);self.calls=[]
  m=self.m;m.SWIFT=self.root/'toolchain/usr/bin/swift';m.ART=self.root/'bundle/swift-android';m.JDK=self.root/'jdk';m.BT=self.root/'build-tools';m.JAR=self.root/'platform/android.jar';m.NDK=m.ART/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64';m.SWIFT_SDKS=self.root/'sdks'
  metadata={m.ART/'android-ndk-r27d/source.properties':'27.3.13750724',m.JAR.parent/'source.properties':'AndroidVersion.ApiLevel=37.0',m.BT/'source.properties':'Pkg.Revision=37.0.0',m.JDK/'release':'JAVA_VERSION="25.0"',m.ART/'swift-sdk.json':'{}',m.ART/'swift-toolset.json':'{}'}
  for p,text in metadata.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  for p in [m.SWIFT,m.NDK/'bin/aarch64-linux-android28-clang',m.NDK/'bin/llvm-readelf',m.NDK/'bin/llvm-nm',m.JDK/'bin/java',m.JDK/'bin/javac']+[m.BT/name for name in ('d8','aapt2','zipalign','dexdump')]:p.parent.mkdir(parents=True,exist_ok=True);p.write_text('inert');p.chmod(0o700)
  def probe(args):
   self.calls.append(('probe',tuple(map(str,args))));return 'Swift version 6.3.3 (official)' if args[0]==m.SWIFT else 'java 25'
  def digest(p):self.calls.append(('digest',str(p)));return 'file-digest'
  def tree(p,digest_file):self.calls.append(('tree',str(p)));return 'tree-digest'
  m.probe=probe;m.InspectionDigests=lambda:digest;m.tree=tree;m.ENV=dict(m.ENV);m.ENV.pop('MIXER_ANDROID_INSPECTION_PHASE_DIR',None)
 def records(self):return [json.loads(line) for p in self.trace.iterdir() for line in p.read_text().splitlines()]
 def test_enabled_disabled_same_result_operation_order_and_clean_streams(self):
  quiet=io.StringIO()
  with contextlib.redirect_stdout(quiet),contextlib.redirect_stderr(quiet):
   expected=self.m.inspect();order=list(self.calls);self.calls.clear();self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR']=str(self.trace);actual=self.m.inspect()
  self.assertEqual(actual,expected);self.assertEqual(self.calls,order);self.assertEqual(quiet.getvalue(),'')
  rows=self.records();self.assertEqual(len(rows),62)
  self.assertEqual([(x['phase'],x['state']) for x in rows[:2]],[('probe.swift','begin'),('probe.swift','end')])
  self.assertEqual(rows[-1]['phase'],'distribution.hash.jdk');self.assertEqual(rows[-1]['state'],'end')
 def test_same_primary_error_identity_with_trace_failure(self):
  error=RuntimeError('original phase failure')
  def fail(args):raise error
  self.m.probe=fail
  for enabled in (False,True):
   if enabled:self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR']=str(self.trace)
   with patch.object(self.m.os,'write',side_effect=OSError('trace failure')):
    with self.assertRaises(RuntimeError) as caught:self.m.inspect()
   self.assertIs(caught.exception,error)
 def test_error_checkpoint_preserves_failure_identity(self):
  self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR']=str(self.trace);error=ValueError('primary')
  def fail(args):raise error
  self.m.probe=fail
  with self.assertRaises(ValueError) as caught:self.m.inspect()
  self.assertIs(caught.exception,error);self.assertEqual([r['state'] for r in self.records()],['begin','error'])
 def test_trace_io_failure_keeps_success_result(self):
  expected=self.m.inspect();self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR']=str(self.trace)
  with patch.object(self.m.os,'write',side_effect=OSError('trace failure')):self.assertEqual(self.m.inspect(),expected)
 def test_disabled_and_distribution_contained_trace_create_nothing(self):
  self.m.inspect();self.assertEqual(list(self.trace.iterdir()),[])
  self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR']=str(self.m.BT);self.m.inspect();self.assertEqual(list(self.m.BT.glob('inspection-*.jsonl')),[])
 def test_trace_is_bounded_and_exclusive(self):
  self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR']=str(self.trace)
  phases=self.m.InspectionPhases()
  for i in range(1000):phases.mark('bounded','begin')
  phases.close();rows=self.records();self.assertEqual(len(rows),64);self.assertLessEqual(sum(p.stat().st_size for p in self.trace.iterdir()),16384)
  phases=self.m.InspectionPhases();phases.mark('huge'*10000,'begin');phases.close();self.assertEqual(len(self.records()),64)

if __name__=='__main__':unittest.main()
