from pathlib import Path
import subprocess,sys,json
H=Path(__file__).resolve().parent
rows=json.loads((H/'inherited-controls.json').read_text());results=[]
with (H/'sealed-control-dispatch.stdout').open('w') as out:
 for i,row in enumerate(rows):
  name=row['name'];label=f'sealed-inherited-{i+1:02}'
  p=subprocess.run([sys.executable,'-B',str(H/'record.py'),'source',label,'test','--offline','--lib','--all-features','experimental_swift_reactor::cache_tests::'+name,'--','--exact','--nocapture','--test-threads=1'],stdout=out,stderr=subprocess.STDOUT)
  results.append({'name':name,'command':label,'exitCode':p.returncode})
(H/'sealed-inherited-controls.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'controls':len(results),'passed':sum(x['exitCode']==0 for x in results),'failures':[x for x in results if x['exitCode']]}))
