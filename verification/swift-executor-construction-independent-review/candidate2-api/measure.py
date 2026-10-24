#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,json,hashlib,re,datetime
out=Path(__file__).resolve().parent
logs=out/'logs';logs.mkdir(exist_ok=True)
env=dict(os.environ);env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env['CARGO_TARGET_DIR']=str(out/'target')
records=[]
for features_label,features in [('minimal','experimental-swift-reactor'),('combined','experimental-swift-reactor,experimental-span-execution')]:
 for profile in ['debug','release']:
  for cfg in ['production','unit']:
   args=['cargo','run'if cfg=='production'else'test','--locked','--offline','--features',features]
   if profile=='release':args+=['--release']
   args+=['--example','positive-accounting']if cfg=='production'else['--lib','independent_positive_accounting_probe','--','--nocapture','--test-threads=1']
   started=datetime.datetime.now(datetime.timezone.utc).isoformat();proc=subprocess.run(args,cwd=out/'tree/vm',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   name=f'{features_label}-{profile}-{cfg}';log=logs/(name+'.log');log.write_text(proc.stdout)
   result={'name':name,'argv':args,'started_utc':started,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':proc.returncode,'output':str(log.relative_to(out)),'output_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'totals':{k:{'bytes':int(n),'align':int(a)}for k,n,a in re.findall(r'positivetotal\|([^|]+)\|(\d+)\|(\d+)',proc.stdout)},'classes':[{'scope':s,'field':f,'count':int(c),'offset':int(o),'size':int(n),'align':int(a)}for s,f,c,o,n,a in re.findall(r'positiveclass\|([^|]+)\|([^|]+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)',proc.stdout)],'test_results':re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed;',proc.stdout)}
   records.append(result);(out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')
   print(json.dumps({k:result[k]for k in ['name','exit_code','totals','test_results']}),flush=True)
   if proc.returncode:print(proc.stdout[-5000:]);raise SystemExit(proc.returncode)
