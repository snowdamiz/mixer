from pathlib import Path
import json,subprocess,datetime
packet=Path(__file__).resolve().parent;root=packet.parents[1]
cmd=['node',str(packet/'candidate/test/snapshot-consistency.mjs')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (packet/'snapshot-consistency.stdout.log').open('w') as stdout,(packet/'snapshot-consistency.stderr.log').open('w') as stderr:
 r=subprocess.run(cmd,cwd=root,stdout=stdout,stderr=stderr,timeout=30)
p=packet/'commands.json';commands=json.loads(p.read_text());commands.append({'name':'snapshot-consistency','command':cmd,'cwd':str(root),'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':r.returncode,'stdout':str((packet/'snapshot-consistency.stdout.log').relative_to(root)),'stderr':str((packet/'snapshot-consistency.stderr.log').relative_to(root)),'stdoutEOF':True,'stderrEOF':True});p.write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps({'exitCode':r.returncode,'expectedUnfixedRegressionExitCode':1}))
