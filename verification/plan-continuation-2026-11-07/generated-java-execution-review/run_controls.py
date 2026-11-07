import importlib.util
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('runner',ROOT/'scripts/ci/check-android-generated-java.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
commands_dir=HERE/'commands';commands_dir.mkdir()
tmp=HERE/'temporary';tmp.mkdir()
env=os.environ.copy();env.update(TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
commands=M.Commands(commands_dir,env,seconds=180,command_seconds=40)
errors=[]
for name,path in [('supplied',ROOT/'scripts/ci/tests/test_android_generated_java_runner.py'),('independent',HERE/'independent_controls.py')]:
 for optimized in (False,True):
  label=name+('-optimized' if optimized else '-normal')
  try:
   commands.run(label,[sys.executable,'-B',*(['-O'] if optimized else []),path,'-v'])
   print(label,'PASS',flush=True)
  except Exception as e:
   errors.append({'label':label,'error':str(e)});print(label,'FAIL',e,flush=True)
M.save(HERE/'tests.json',{'python':sys.version,'records':commands.records,'errors':errors,'temporary_entries':[p.name for p in tmp.iterdir()]})
if not list(tmp.iterdir()):tmp.rmdir()
sys.exit(bool(errors))
