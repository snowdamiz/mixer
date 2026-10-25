#!/usr/bin/env python3
"""Retain a host verification command and exact output without native actions."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent
attempt=H/('host-validation-'+(sys.argv[1] if len(sys.argv)>1 else '1'));attempt.mkdir()
argv=[sys.executable,'-B',str(H/'validate.py')]
sources={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.glob('*.py'))}
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
r=subprocess.run(argv,cwd=H,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55)
(attempt/'stdout.json').write_bytes(r.stdout);(attempt/'stderr.log').write_bytes(r.stderr)
receipt={'schema':1,'argv':argv,'cwd':str(H),'startedUTC':start,'elapsedSeconds':time.monotonic()-t,'exitCode':r.returncode,'python':platform.python_version(),'pythonExecutableSHA256':hashlib.sha256(pathlib.Path(sys.executable).resolve().read_bytes()).hexdigest(),'sourceHashes':sources,'stdoutSHA256':hashlib.sha256(r.stdout).hexdigest(),'stderrSHA256':hashlib.sha256(r.stderr).hexdigest(),'nativeAttempts':0,'nativeQueries':0,'scope':'Read-only host validation only'}
(attempt/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,sort_keys=True));sys.exit(r.returncode)
