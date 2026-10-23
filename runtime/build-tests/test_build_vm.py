"""Native-header identity must reject before any build, including Python -O."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class BuildIdentityTests(unittest.TestCase):
    def test_mismatched_header_rejects_even_when_assertions_are_disabled(self):
        with tempfile.TemporaryDirectory(prefix='mixer-header-review-') as directory:
            root = Path(directory)
            (root/'runtime/Sources/CMixerVM/include').mkdir(parents=True)
            (root/'vm/include').mkdir(parents=True)
            (root/'contracts').mkdir()
            (root/'vm/include/mixer_vm.h').write_text('/* immutable header */\n')
            (root/'contracts/vm-session-v1.json').write_text('{}\n')
            shutil.copyfile(Path(__file__).resolve().parents[1]/'build-vm.py',root/'runtime/build-vm.py')
            (root/'runtime/Sources/CMixerVM/include/mixer_vm.h').write_text('/* mismatched wrapper */\n')
            def git(*args):
                subprocess.run(['git',*args],cwd=root,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            git('init','-q'); git('add','vm','contracts')
            git('-c','user.name=Mixer test','-c','user.email=test@example.invalid','commit','-qm','Frozen ABI fixture')
            for name, flags, optimize in [('normal',[],None),('flag',['-O'],None),('environment',[],'1')]:
                with self.subTest(mode=name):
                    output = root/name
                    env = dict(os.environ)
                    env.pop('PYTHONOPTIMIZE',None)
                    if optimize: env['PYTHONOPTIMIZE']=optimize
                    result = subprocess.run([sys.executable,*flags,str(root/'runtime/build-vm.py'),
                        '--revision','HEAD','--target','host','--output',str(output)],cwd=root,env=env,
                        text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('Swift wrapper header differs from frozen VM',result.stderr)
                    self.assertFalse((output/'build.log').exists(),'Mismatch must reject before invoking Cargo')
                    self.assertFalse((output/'lib/libmixer_vm.a').exists())


if __name__ == '__main__': unittest.main()
