"""Run pinned official compiler with independent exact-type metadata callback."""
import collect as c
from pathlib import Path
import json,sys,gzip,datetime
s=json.loads((c.HERE/'layout-tool-session.json').read_text());tool=json.loads((c.HERE/'layout-driver-build.json').read_text());assert c.sha(Path(tool['binary']).read_bytes())==tool['sha256']
def run(features,profile,unit):
 name=features+'-'+profile+'-'+('unit'if unit else'production');output=Path(s['scratch'])/('layout-'+name+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S%f')+'.jsonl')
 flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])+(['--release']if profile=='release'else[])
 code,attempt,out,err=c.run(['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']+(['--test']if unit else[]),env_extra={'RUSTC_BOOTSTRAP':'1','RUSTC_WRAPPER':tool['binary'],'MIXER_LAYOUT_SYSROOT':s['sysroot'],'MIXER_LAYOUT_OUTPUT':str(output)},label='exact-query-'+name)
 if output.exists():
  raw=output.read_bytes();c.save(attempt/'exact-layouts.jsonl.gz',gzip.compress(raw,mtime=0));output.unlink()
  rows=[json.loads(line)for line in raw.decode().splitlines()];c.save(c.HERE/('exact-query-'+name+'.json'),{'attempt':str(attempt.relative_to(c.HERE)),'exitCode':code,'records':len(rows),'bytes':len(raw),'sha256':c.sha(raw),'toolSHA256':tool['sha256'],'sourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate')))})
 else:c.save(c.HERE/('exact-query-'+name+'.json'),{'attempt':str(attempt.relative_to(c.HERE)),'exitCode':code,'outputMissing':True})
 return code
if __name__=='__main__':raise SystemExit(run(sys.argv[1],sys.argv[2],sys.argv[3]=='unit'))
