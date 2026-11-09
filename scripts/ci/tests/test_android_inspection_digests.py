"""Owned filesystem regression controls for operation-scoped Android digests."""
import hashlib, importlib.util, io, json, os, pathlib, shutil, stat, sys, tempfile, types, unittest
from unittest import mock
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXTURES = HERE / 'android_inspection_digests'

def load(name, path):
    data = path.read_bytes()
    if name == 'baseline' and (len(data) != 30638 or hashlib.sha256(data).hexdigest() != 'df87f377dee8a167f559eb43ea22d15e692f299dc715aff74454ea5747573cf2'):
        raise RuntimeError('Android inspection baseline fixture differs')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module

Meter = load('android_inspection_read_meter', FIXTURES / 'read_meter.py').Meter
b = load('baseline', FIXTURES / 'preimage-android-build.py')
c = load('candidate', ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py')
class Equivalence(unittest.TestCase):
    def setUp(self):
        self.root=pathlib.Path(tempfile.mkdtemp(prefix='android-inspection-'))
        self.dist=self.root/'dist'; self.dist.mkdir()
    def tearDown(self): shutil.rmtree(self.root)
    def file(self,name,data=b'content'):
        p=self.dist/name; p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);return p
    def same(self): self.assertEqual(b.tree(self.dist),c.tree(self.dist,c.InspectionDigests()))
    def projection(self,rows):
        return hashlib.sha256(''.join(name+'\0'+value+'\n' for name,value in rows).encode()).hexdigest()
    def test_01_empty(self): self.same()
    def test_02_ordinary_nested_sorted(self):
        self.file('z',b'z');self.file('a/b',b'ab');self.file('a/a',b'aa');self.same()
    def test_03_known_bytes(self):
        self.file('a',b'abc')
        self.assertEqual(c.tree(self.dist,c.InspectionDigests()),self.projection([('a',hashlib.sha256(b'abc').hexdigest())]))
    def test_04_symlink_file_same_hash(self):
        self.file('z');(self.dist/'a').symlink_to('z');self.same()
    def test_05_symlink_file_text_contributes(self):
        self.file('z');a=self.dist/'a';a.symlink_to('z');first=c.tree(self.dist,c.InspectionDigests());a.unlink();a.symlink_to('./z')
        self.same();self.assertNotEqual(first,c.tree(self.dist,c.InspectionDigests()))
    def test_06_symlink_directory_no_recursion(self):
        self.file('z/b',b'b');(self.dist/'a').symlink_to('z',target_is_directory=True);self.same()
        self.assertEqual(c.tree(self.dist,c.InspectionDigests()),self.projection([('a','symlink:z'),('z/b',hashlib.sha256(b'b').hexdigest())]))
    def test_07_symlink_directory_text_contributes(self):
        self.file('z/b');p=self.dist/'a';p.symlink_to('z',target_is_directory=True);old=c.tree(self.dist,c.InspectionDigests());p.unlink();p.symlink_to('./z',target_is_directory=True)
        self.same();self.assertNotEqual(old,c.tree(self.dist,c.InspectionDigests()))
    def test_08_directory_escape_refused(self):
        outside=self.root/'outside';outside.mkdir();(self.dist/'a').symlink_to(outside,target_is_directory=True)
        for mod,kwargs in [(b,{}),(c,{'digest_file':c.InspectionDigests()})]:
            with self.assertRaisesRegex(RuntimeError,'escapes hashed root'): mod.tree(self.dist,**kwargs)
    def test_09_baseline_external_file_symlink_preserved(self):
        outside=self.root/'outside';outside.write_bytes(b'external');(self.dist/'a').symlink_to(outside);self.same()
    def test_10_broken_symlink_refused(self):
        (self.dist/'a').symlink_to('missing')
        for mod in [b,c]:
            with self.assertRaises(FileNotFoundError):mod.tree(self.dist)
        with self.assertRaises(FileNotFoundError):c.tree(self.dist,c.InspectionDigests())
    def test_11_special_fifo_refused(self):
        os.mkfifo(self.dist/'fifo')
        for fn in [lambda:b.tree(self.dist),lambda:c.tree(self.dist,c.InspectionDigests()),lambda:c.InspectionDigests()(self.dist/'fifo')]:
            with self.assertRaisesRegex(RuntimeError,'Unsupported installed tool file'):fn()
    def test_12_hardlink_equivalence_and_read_once(self):
        p=self.file('a',b'hard');os.link(p,self.dist/'b')
        with Meter() as bm:expected=b.tree(self.dist)
        with Meter() as cm:actual=c.tree(self.dist,c.InspectionDigests())
        self.assertEqual(actual,expected);self.assertEqual(bm.bytes_read,8);self.assertEqual(cm.bytes_read,4);self.assertEqual(cm.opens,2)
    def test_13_symlink_read_once(self):
        self.file('a',b'alias');(self.dist/'b').symlink_to('a');(self.dist/'c').symlink_to('a')
        with Meter() as m:actual=c.tree(self.dist,c.InspectionDigests())
        self.assertEqual(actual,b.tree(self.dist));self.assertEqual(m.bytes_read,5);self.assertEqual(m.opens,3)
    def test_14_identical_bytes_distinct_inodes_both_read(self):
        self.file('a',b'copy');self.file('b',b'copy')
        with Meter() as m:c.tree(self.dist,c.InspectionDigests())
        self.assertEqual(m.bytes_read,8);self.assertEqual(len(m.identities_read),2)
    def test_15_operation_does_not_reuse_prior_inventory(self):
        self.file('a',b'new')
        for _ in range(2):
            with Meter() as m:c.tree(self.dist,c.InspectionDigests())
            self.assertEqual(m.bytes_read,3)
    def test_16_content_changes_between_alias_calls_refused(self):
        p=self.file('a',b'old');d=c.InspectionDigests();d(p);p.write_bytes(b'new')
        with self.assertRaisesRegex(RuntimeError,'changed during inspection'):d(p)
    def test_17_restored_mtime_still_refused(self):
        p=self.file('a',b'old');d=c.InspectionDigests();before=p.stat();d(p);p.write_bytes(b'new');os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError,'changed during inspection'):d(p)
    def test_18_permission_metadata_mutation_refused(self):
        p=self.file('a');d=c.InspectionDigests();d(p);p.chmod(0o700)
        with self.assertRaisesRegex(RuntimeError,'changed during inspection'):d(p)
    def test_19_nlink_metadata_mutation_refused(self):
        p=self.file('a');d=c.InspectionDigests();d(p);os.link(p,self.dist/'b')
        with self.assertRaisesRegex(RuntimeError,'changed during inspection'):d(p)
    def test_20_replaced_inode_is_freshly_hashed(self):
        p=self.file('a',b'old');new=self.file('new',b'new');d=c.InspectionDigests();d(p);os.replace(new,p)
        with Meter() as m:actual=d(p)
        self.assertEqual(actual,hashlib.sha256(b'new').hexdigest());self.assertEqual(m.bytes_read,3)
    def test_21_retargeted_symlink_is_freshly_hashed(self):
        self.file('a',b'old');self.file('b',b'new');p=self.dist/'link';p.symlink_to('a');d=c.InspectionDigests();d(p);p.unlink();p.symlink_to('b')
        with Meter() as m:actual=d(p)
        self.assertEqual(actual,hashlib.sha256(b'new').hexdigest());self.assertEqual(m.bytes_read,3)
    def test_22_mutation_during_content_read_refused(self):
        p=self.file('a',b'old');changed=[]
        def change(stream,value):
            if value and not changed:changed.append(True);p.write_bytes(b'new')
        with Meter(after_read=change):
            with self.assertRaisesRegex(RuntimeError,'changed during inspection'):c.InspectionDigests()(p)
    def test_23_replacement_between_stat_and_open_refused(self):
        p=self.file('a',b'old');new=self.file('b',b'new');opener=os.open
        def replace_open(*args,**kwargs):os.replace(new,p);return opener(*args,**kwargs)
        with mock.patch.object(c.os,'open',replace_open):
            with self.assertRaisesRegex(RuntimeError,'changed during inspection'):c.InspectionDigests()(p)
    def test_24_mutation_after_open_on_cache_hit_refused(self):
        p=self.file('a',b'old');d=c.InspectionDigests();d(p);fdopen=os.fdopen
        def changed(*args,**kwargs):
            stream=fdopen(*args,**kwargs);p.write_bytes(b'new');return stream
        with mock.patch.object(c.os,'fdopen',changed):
            with self.assertRaisesRegex(RuntimeError,'changed during inspection'):d(p)
    def test_25_mutation_after_cache_lookup_refused(self):
        p=self.file('a',b'old');d=c.InspectionDigests();d(p)
        class Changing(dict):
            def get(cache,key):
                value=super().get(key);p.write_bytes(b'new');return value
        d._files=Changing(d._files)
        with self.assertRaisesRegex(RuntimeError,'changed during inspection'):d(p)
    def test_26_symlink_loop_refused(self):
        (self.dist/'a').symlink_to('a')
        for fn in [lambda:b.tree(self.dist),lambda:c.tree(self.dist,c.InspectionDigests())]:
            with self.assertRaises((OSError,RuntimeError)):fn()
    def test_27_source_tree_behavior_unchanged(self):
        self.file('a',b'bytes');self.assertEqual(b.source_tree(self.dist),c.source_tree(self.dist))
    def test_28_default_tree_behavior_unchanged(self):
        self.file('a');(self.dist/'b').symlink_to('a');self.assertEqual(b.tree(self.dist),c.tree(self.dist))
    def test_29_empty_file_still_opens_each_path(self):
        p=self.file('a',b'');os.link(p,self.dist/'b')
        with Meter() as m:actual=c.tree(self.dist,c.InspectionDigests())
        self.assertEqual(actual,b.tree(self.dist));self.assertEqual(m.bytes_read,0);self.assertEqual(m.opens,2);self.assertEqual(m.read_calls,1)
    def fake_inspect(self):
        swift=self.root/'swift';art=self.root/'bundle/swift-android';jdk=self.root/'jdk';sdk=self.root/'sdk';bt=sdk/'build-tools/37.0.0';jar=sdk/'platforms/android-37.0/android.jar';ndk=art/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64';python=self.root/'python'
        tools=[swift/'usr/bin/swift',ndk/'bin/aarch64-linux-android28-clang',ndk/'bin/llvm-readelf',ndk/'bin/llvm-nm',jdk/'bin/java',jdk/'bin/javac',bt/'d8',bt/'aapt2',bt/'zipalign',bt/'dexdump',python]
        for p in tools:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'executable');p.chmod(0o755)
        (swift/'usr/bin/swift-alias').symlink_to('swift')
        metadata={art/'android-ndk-r27d/source.properties':'Pkg.Revision=27.3.13750724',jar.parent/'source.properties':'AndroidVersion.ApiLevel=37.0',bt/'source.properties':'Pkg.Revision=37.0.0',jdk/'release':'JAVA_VERSION="25.0.4.1"',art/'swift-sdk.json':'{}',art/'swift-toolset.json':'{}',jar:'fake jar'}
        for p,text in metadata.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        return {'SWIFT':swift/'usr/bin/swift','ART':art,'JDK':jdk,'SDK':sdk,'BT':bt,'JAR':jar,'NDK':ndk,'SWIFT_SDKS':self.root,'sys':types.SimpleNamespace(executable=str(python),version='test-python'),'probe':lambda argv:'Apple Swift version 6.3.3 test' if argv[0]==swift/'usr/bin/swift' else 'fake java 25'}
    def test_30_complete_fake_inspect_matches_and_shares_one_operation(self):
        env=self.fake_inspect()
        with mock.patch.multiple(b,**env),mock.patch.multiple(c,**env):
            with Meter() as bm:baseline=b.inspect()
            with Meter() as cm:candidate=c.inspect()
        self.assertEqual(baseline,candidate);self.assertLess(cm.bytes_read,bm.bytes_read);self.assertEqual(cm.opens,bm.opens)
    def test_31_each_fake_inspect_gets_new_cache(self):
        env=self.fake_inspect()
        with mock.patch.multiple(c,**env):
            with Meter() as one:a=c.inspect()
            with Meter() as two:z=c.inspect()
        self.assertEqual(a,z);self.assertEqual(one.bytes_read,two.bytes_read);self.assertGreater(one.bytes_read,0)
    def test_32_non_regular_descriptor_swap_refused(self):
        p=self.file('a');original=os.open
        def redirect(*args,**kwargs):return original(self.dist,os.O_RDONLY)
        with mock.patch.object(c.os,'open',redirect):
            with self.assertRaises((OSError,RuntimeError)):c.InspectionDigests()(p)


if __name__ == '__main__':
    unittest.main()
