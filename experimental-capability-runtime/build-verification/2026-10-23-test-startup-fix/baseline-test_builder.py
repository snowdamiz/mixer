#!/usr/bin/env python3
"""Original host boundary probes. Fixture Git trees are not VM qualification."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest

BUILDER=Path(__file__).resolve().parents[1]/'build-vm.py'
spec=importlib.util.spec_from_file_location('experimental_builder',BUILDER)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
PIN='b25e3b7de2391a80d12e7fd75e60903495bec120'
REPO=BUILDER.parents[1]

class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_root=b.ROOT
        # Header/contract bytes are pinned production inputs, never invented ABI fixtures.
        cls.pinned={p:subprocess.check_output(['git','show',PIN+':'+p],cwd=REPO) for p in b.REQUIRED if p not in ('vm/Cargo.toml','vm/Cargo.lock','vm/src/lib.rs')}
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='mixer-builder-test-')
        # macOS /var is a platform symlink; choose its canonical private parent.
        self.base=Path(self.tmp.name).resolve();self.repo=self.base/'repo';self.repo.mkdir()
        self.write('vm/Cargo.toml',b'''[package]\nname="mixer-vm"\nversion="0.1.0"\nedition="2021"\n[lib]\nname="mixer_vm"\ncrate-type=["staticlib"]\n[features]\ndefault=[]\nexperimental-capability-mailbox=[]\nexperimental-capability-guest=["experimental-capability-mailbox"]\nexperimental-capability-native=["experimental-capability-guest"]\n''')
        self.write('vm/Cargo.lock',b'version = 4\n[[package]]\nname = "mixer-vm"\nversion = "0.1.0"\n')
        self.write('vm/src/lib.rs',b'// Original empty source for input-policy probes, never compiled.\n')
        for p,raw in self.pinned.items():self.write(p,raw)
        self.write('experimental-capability-runtime/build-vm.py',BUILDER.read_bytes())
        self.git('init','-q');self.revision=self.commit();b.ROOT=self.repo
    def tearDown(self):b.ROOT=self.original_root;self.tmp.cleanup()
    def write(self,path,raw):
        target=self.repo/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    def git(self,*args):
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',*args],cwd=self.repo,stderr=subprocess.PIPE)
    def commit(self):
        self.git('add','-A');self.git('-c','user.name=Boundary Probe','-c','user.email=probe@example.invalid','commit','-qm','original fixture')
        return self.git('rev-parse','HEAD').decode().strip()
    def cli(self,revision,output,optimized=False,extra=()):
        command=[sys.executable]+(['-O'] if optimized else [])+[str(self.repo/'experimental-capability-runtime/build-vm.py'),'--revision',revision,'--target','host','--output',str(output),'--rustc',sys.executable,*extra]
        return subprocess.run(command,cwd='/',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
    def rejected(self,revision,fragment,optimized=False):
        output=self.base/'never-created';result=self.cli(revision,output,optimized)
        self.assertEqual(result.returncode,1,result.stdout);self.assertIn(fragment.encode(),result.stdout)
        self.assertFalse(output.exists());self.assertNotIn(b'Traceback',result.stdout)
    def test_frozen_blobs_ignore_dirty_working_tree(self):
        self.write('vm/src/lib.rs',b'changed after commit')
        files=b.frozen_inputs(self.revision)
        self.assertTrue(files['vm/src/lib.rs']['bytes'].startswith(b'// Original empty'))
        self.assertEqual(len(files),len(b.REQUIRED))
    def test_full_commit_only_normal_and_optimized(self):
        for optimized in (False,True):
            for value in ('HEAD',self.revision[:12],self.revision.upper(),'0'*40):
                with self.subTest(optimized=optimized,value=value):self.rejected(value,'rejected',optimized)
        tree=self.git('rev-parse','HEAD^{tree}').decode().strip()
        self.rejected(tree,'not a commit')
    def test_missing_feature_rejected_before_output_even_optimized(self):
        path=self.repo/'vm/Cargo.toml';path.write_bytes(path.read_bytes().replace(b'experimental-capability-native=["experimental-capability-guest"]',b'experimental-capability-native=[]'))
        revision=self.commit()
        for optimized in (False,True):self.rejected(revision,'feature chain',optimized)
    def test_header_drift_rejected_before_output_even_optimized(self):
        self.write('vm/include/mixer_vm_capability.h',b'wrong ABI')
        revision=self.commit()
        for optimized in (False,True):self.rejected(revision,'header mismatch',optimized)
    def test_legacy_header_copy_drift(self):
        self.write('runtime/Sources/CMixerVM/include/mixer_vm.h',b'wrong copy')
        self.rejected(self.commit(),'copies differ',True)
    def test_missing_source_input(self):
        (self.repo/'capabilities/schema/v1.json').unlink()
        self.rejected(self.commit(),'input is missing')
    def test_build_script_is_selected_and_rejected(self):
        self.write('vm/build.rs',b'fn main() {}\n')
        self.rejected(self.commit(),'build scripts',True)
    def test_external_lib_path_and_dependencies_rejected(self):
        manifest=self.repo/'vm/Cargo.toml';original=manifest.read_bytes()
        for addition in (b'\n[dependencies]\nexternal={path="../../outside"}\n',b'\n[build-dependencies]\nexternal="1"\n',b'\n[target.unix.dependencies]\nexternal="1"\n'):
            manifest.write_bytes(original+addition);self.rejected(self.commit(),'outside' if b'target.' in addition else 'self-contained')
        manifest.write_bytes(original.replace(b'name="mixer_vm"',b'name="mixer_vm"\npath="../../outside.rs"'))
        self.rejected(self.commit(),'library source',True)
    def test_git_symlink_rejected(self):
        target=self.repo/'vm/src/lib.rs';target.unlink();target.symlink_to(self.base/'outside')
        self.rejected(self.commit(),'not a regular file',True)
    def test_output_existing_and_parent_aliases_preserve_external_files(self):
        outside=self.base/'outside';outside.mkdir();marker=outside/'keep';marker.write_bytes(b'unchanged')
        existing=self.base/'existing';existing.mkdir()
        link=self.base/'linked';link.symlink_to(outside,target_is_directory=True)
        final=self.base/'final';final.symlink_to(outside,target_is_directory=True)
        for path in (existing,link/'child',final,self.base/'a/../escape'):
            with self.subTest(path=path):
                result=self.cli(self.revision,path,True);self.assertEqual(result.returncode,1,result.stdout)
                self.assertEqual(marker.read_bytes(),b'unchanged');self.assertEqual(list(outside.iterdir()),[marker])
        self.assertEqual(list(existing.iterdir()),[])
    def test_output_exclusive_leaf_refuses_hardlink_or_symlink(self):
        outside=self.base/'outside';outside.write_bytes(b'unchanged')
        output=b.Output(self.base/'new')
        try:
            os.link(outside,output.path/'hard');(output.path/'sym').symlink_to(outside)
            for path in ('hard','sym'):
                with self.assertRaises(FileExistsError):output.write(path,b'replaced')
            self.assertEqual(outside.read_bytes(),b'unchanged')
        finally:output.close()
    def test_output_directory_identity_change_detected(self):
        output=b.Output(self.base/'new')
        try:
            output.path.rename(self.base/'retained');output.path.mkdir()
            with self.assertRaisesRegex(b.BuildError,'identity'):output.check()
            self.assertEqual(list(output.path.iterdir()),[])
        finally:output.close()
    def test_cache_rejects_external_links_symlinks_and_special_files(self):
        outside=self.base/'outside';outside.write_bytes(b'unchanged')
        for kind in ('hard','sym','fifo'):
            cache=self.base/kind;cache.mkdir(mode=0o700)
            if kind=='hard':os.link(outside,cache/'entry')
            elif kind=='sym':(cache/'entry').symlink_to(outside)
            else:os.mkfifo(cache/'entry')
            with self.assertRaises(b.BuildError):
                with b.cache_owner(cache):self.fail('unsafe cache admitted')
            self.assertEqual(outside.read_bytes(),b'unchanged')
    def test_cache_internal_hardlinks_and_exclusive_lock(self):
        cache=self.base/'cache';cache.mkdir(mode=0o700);(cache/'a').write_bytes(b'internal');os.link(cache/'a',cache/'b')
        with b.cache_owner(cache) as fd:
            self.assertTrue(b.audit_cache(fd)['internal_hardlinks_permitted'])
            with self.assertRaisesRegex(b.BuildError,'already used'):
                with b.cache_owner(cache):self.fail('concurrent cache owner')
    def test_cache_external_lock_and_writable_directory_rejected(self):
        cache=self.base/'cache';cache.mkdir(mode=0o700);outside=self.base/'outside';outside.write_bytes(b'keep')
        os.link(outside,cache/'.mixer-capability-builder.lock')
        with self.assertRaises(b.BuildError):
            with b.cache_owner(cache):self.fail('external lock admitted')
        writable=self.base/'writable';writable.mkdir();writable.chmod(0o777)
        with self.assertRaisesRegex(b.BuildError,'mode'):
            with b.cache_owner(writable):self.fail('writable cache admitted')
    def test_cache_quarantine_is_sticky(self):
        cache=self.base/'cache'
        with self.assertRaises(b.ProcessGroupError):
            with b.cache_owner(cache):raise b.ProcessGroupError('original cleanup failure')
        with self.assertRaisesRegex(b.BuildError,'quarantined'):
            with b.cache_owner(cache):self.fail('quarantined cache admitted')
    def test_cache_output_overlap_rejected_before_output(self):
        for cache in (self.base,self.base/'output',self.base/'output/target'):
            result=self.cli(self.revision,self.base/'output',True,('--cache',str(cache)))
            self.assertEqual(result.returncode,1,result.stdout);self.assertIn(b'overlap',result.stdout);self.assertFalse((self.base/'output').exists())
    def test_source_tar_regular_exact_and_frozen(self):
        files=b.frozen_inputs(self.revision);output=b.Output(self.base/'export')
        try:
            b.source_archive(output,files)
            with tarfile.open(fileobj=io.BytesIO(output.read('source.tar'))) as tar:
                self.assertEqual(len(tar.getmembers()),len(files))
                for member in tar.getmembers():
                    self.assertTrue(member.isreg());self.assertEqual(member.mtime,0)
                    self.assertEqual(tar.extractfile(member).read(),files[member.name]['bytes'])
        finally:output.close()
    def test_archive_copy_refuses_link_and_wrong_format(self):
        cache=self.base/'cache';cache.mkdir();outside=self.base/'outside';outside.write_bytes(b'!<arch>\n')
        os.link(outside,cache/'bad.a');(cache/'wrong.a').write_bytes(b'not ar')
        fd=b.opened_directory(cache)
        try:
            for name in ('bad.a','wrong.a'):
                output=b.Output(self.base/('export-'+name))
                try:
                    with self.assertRaises(b.BuildError):b.copy_library(output,fd,[name])
                    self.assertFalse((output.path/'receipt.json').exists())
                finally:output.close()
        finally:os.close(fd)
    def test_rust_selector_discovery_and_absolute_rule(self):
        self.assertEqual(b.rust_selector(Path(sys.executable)),Path(sys.executable))
        with self.assertRaisesRegex(b.BuildError,'absolute'):b.rust_selector(Path('rustc'))
        old=os.environ['PATH'];os.environ['PATH']=''
        try:
            with self.assertRaisesRegex(b.BuildError,'not on PATH'):b.rust_selector(None)
        finally:os.environ['PATH']=old
    def test_interrupt_kills_descendant_and_quarantines_held_cache(self):
        cache=self.base/'interrupted-cache';marker=self.base/'interrupt-writer'
        writer='import time\nf=open('+repr(str(marker))+',"ab",buffering=0)\nwhile True:\n f.write(b"x");time.sleep(0.005)\n'
        parent='import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c",'+repr(writer)+'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(10)'
        probe="""import importlib.util,os,signal,sys,threading,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('b',sys.argv[1]);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def interrupt():
 deadline=time.monotonic()+4
 while not Path(sys.argv[3]).exists():
  if time.monotonic()>deadline:os._exit(8)
  time.sleep(.005)
 os.kill(os.getpid(),signal.SIGINT)
try:
 with b.cache_owner(Path(sys.argv[2])):
  threading.Thread(target=interrupt,daemon=True).start()
  b.capture([sys.executable,'-c',sys.argv[4]],cwd='/',timeout=10)
except (KeyboardInterrupt,b.ProcessGroupError):pass
else:sys.exit(9)
if not (Path(sys.argv[2])/'.mixer-capability-builder-quarantine').is_file():sys.exit(10)
"""
        result=subprocess.run([sys.executable,'-c',probe,str(BUILDER),str(cache),str(marker),parent],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout);length=marker.stat().st_size
        time.sleep(.08);self.assertEqual(marker.stat().st_size,length)
        with self.assertRaisesRegex(b.BuildError,'quarantined'):
            with b.cache_owner(cache):self.fail('interrupted cache reused')
    def test_failed_command_kills_descendant_writer(self):
        for reason in ('timeout','output','nonzero','orphan'):
            marker=self.base/('writer-'+reason)
            writer='import time\nf=open('+repr(str(marker))+',"ab",buffering=0)\nwhile True:\n f.write(b"x");time.sleep(0.005)\n'
            parent='import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c",'+repr(writer)+'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(0.08)\n'
            parent+= {'timeout':'time.sleep(10)','output':'print("x"*10000,flush=True);time.sleep(10)','nonzero':'sys.exit(7)','orphan':'sys.exit(0)'}[reason]
            code,raw,problem=b.capture([sys.executable,'-c',parent],cwd='/',maximum=1000,timeout=0.25)
            if reason=='orphan':self.assertEqual(code,0);self.assertIn('left running descendants',problem)
            else:self.assertNotEqual(code,0)
            self.assertTrue(marker.exists())
            if reason in ('timeout','output'):self.assertIn('command '+('timeout' if reason=='timeout' else 'output limit'),problem)
            length=marker.stat().st_size;time.sleep(0.08);self.assertEqual(marker.stat().st_size,length,reason)
            # An OS denial probing an adopted process group cannot establish
            # disappearance; conservative quarantine is allowed, never reuse.
            if 'still present' in (problem or ''):self.assertIn('command',problem)

if __name__=='__main__':unittest.main(verbosity=2)
