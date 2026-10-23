from pathlib import Path
import subprocess,json,hashlib,datetime
ROOT=Path(__file__).resolve().parent;repo=ROOT.parents[1]
(ROOT/'build').mkdir(exist_ok=True)
commands=[['swift','--version'],['python3','--version'],['swiftc','-O',str(ROOT/'DecodePNG.swift'),'-o',str(ROOT/'build/decode')],[str(ROOT/'build/decode'),str(repo)],['python3','-B',str(repo/'verification/apple-appearance-measurement/scripts/verify.py')],['python3','-B',str(repo/'verification/apple-appearance-measurement/scripts/verify-seal.py')]]
rows=[]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log=f'{i:02d}.log';(ROOT/log).write_bytes(p.stdout)
 rows.append({'command':cmd,'exit_code':p.returncode,'log':log,'sha256':hashlib.sha256(p.stdout).hexdigest()}); print(i,p.returncode,p.stdout.decode()[:550],flush=True)
 if p.returncode:break
(ROOT/'commands.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':rows},indent=2)+'\n')
