#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,datetime
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SSL=pathlib.Path('/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang/lib/ssl-11.7.7/src')
DOC=pathlib.Path('/opt/homebrew/Cellar/erlang/29.1.1_2/share/doc/erlang')
sections={
 SSL/'ssl.erl':[(258,283)],SSL/'ssl_config.erl':[(136,149)],SSL/'ssl_internal.hrl':[(50,60)],
 SSL/'tls_socket.erl':[(150,159),(196,199),(246,279),(286,289)],
 SSL/'tls_gen_connection.erl':[(274,308),(612,642),(655,790),(850,880)],
 SSL/'ssl_record.hrl':[(140,146)],SSL/'tls_dyn_connection_sup.erl':[(62,91)],
 DOC/'lib/kernel-11.0.4/doc/html/inet.md':[(1239,1252),(1593,1596)],
 DOC/'lib/ssl-11.7.7/doc/html/ssl.md':[(1042,1047),(2035,2068)],
 DOC/'erts-17.1/doc/html/erlang.md':[(6957,7015)]}
evidence=[]
for p,ranges in sections.items():
 lines=p.read_text().splitlines()
 evidence.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'excerpts':[{'startLine':a,'endLine':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
(OUT/'otp-source-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
deps={}
for name in ['mint','hpax','jason']:
 base=ROOT/'hosted/deps'/name
 entries={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.rglob('*')) if p.is_file() and '_build' not in p.parts and '.git' not in p.parts}
 deps[name]={'files':entries,'treeDigest':hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(OUT/'dependency-source-manifest.json').write_text(json.dumps(deps,indent=2)+'\n')
results=json.loads((OUT/'results.json').read_text())
assert results['assertions']=='passed'
assert results['ordinary_fixture_protocols']==['tlsv1.3']
assert 'hostname_check_failed' in results['wrong_hostname']
assert results['wrong_hostname_resources']['alive_raw_ports']==0
assert results['wrong_hostname_resources']['alive_ssl_processes']==0
paths=[p for p in OUT.rglob('*') if p.is_file() and p.name not in ['receipt.json']]
paths.append(ROOT/'docs/hosted-tls-buffer-preflight.md')
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
receipt={'status':'prototype-preflight-passed-production-acceptance-pending','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'command':'PREFLIGHT_REUSE_INPUTS=1 python3 verification/hosted-tls-buffer-preflight/run.py',
 'baseRevisionAtFinalProbe':(OUT/'revision.log').read_text().strip(),'inputAuthority':'source-manifest.json plus inputs/ snapshots; source files include uncommitted producer work',
 'observedEnvironment':results['versions'],'scopes':['supported OTP TLS callback seam','ordered per-socket active1 and driver16KiB buffering','loopback verified TLS1.2/TLS1.3','fastflood comparison','absolute timeout','pre-handshake raw socket cancellation lifecycle'],
 'notVerified':['production callback integration','complete key owner component suite','Linux deployment memory envelope','all hostile TLS inputs','hard RSS or kernel receive queue bound','provider or publication','physical phones','operational acceptance','GA gates'],
 'cleanup':json.loads((OUT/'cleanup.json').read_text()),'files':manifest,'treeDigest':hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'treeDigest':receipt['treeDigest'],'files':len(manifest)},indent=2))
