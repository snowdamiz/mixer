from pathlib import Path
import json,os,subprocess,time,signal
p=Path(__file__).parent;c=json.loads((p/'selection.json').read_text());started=time.monotonic()
with (p/'stdout.log').open('wb') as out,(p/'stderr.log').open('wb') as err:
 child=subprocess.Popen(c['argv'],cwd=c['cwd'],stdout=out,stderr=err,start_new_session=True)
 row={'pid':child.pid,'pgid':child.pid,'argv':c['argv']};(p/'command.json').write_text(json.dumps(row,indent=2)+'\n')
 try:code=child.wait(timeout=c['seconds'])
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=10);row['timeout']=True
try:os.killpg(child.pid,0);absent=False
except ProcessLookupError:absent=True
row.update(exitCode=code,groupAbsent=absent,seconds=time.monotonic()-started)
(p/('result.json' if absent else 'HOLD.json')).write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row))
