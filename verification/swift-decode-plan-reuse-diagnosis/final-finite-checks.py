from pathlib import Path
import subprocess,sys,json
H=Path(__file__).resolve().parent
commands=[('source','qualified-finite-debug','plan_reuse_'),('source','qualified-frozen','experimental::cache::tests::frozen_'),('baseline','qualified-baseline-observation','plan_reuse_observation'),('baseline','qualified-baseline-frozen','experimental::cache::tests::frozen_')]
results=[]
with (H/'qualified-dispatch.stdout').open('w') as out:
 for lane,label,filter_ in commands:
  p=subprocess.run([sys.executable,'-B',str(H/'record.py'),lane,label,'test','--offline','--lib','--all-features',filter_,'--','--nocapture','--test-threads=1'],stdout=out,stderr=subprocess.STDOUT)
  results.append({'command':label,'exitCode':p.returncode})
(H/'qualified-checks.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
