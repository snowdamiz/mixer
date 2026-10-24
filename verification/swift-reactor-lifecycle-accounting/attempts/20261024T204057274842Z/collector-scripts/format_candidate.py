"""Format only the two new owned Rust modules; record exact source delta."""
import collect as c
from pathlib import Path
import subprocess,datetime
p=c.HERE/'candidate';before=c.manifest(p)
tool=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustfmt')
paths=['src/experimental_swift_reactor/lifecycle.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
argv=[str(tool),'--edition','2021',*paths];started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=subprocess.run(argv,cwd=p,capture_output=True);after=c.manifest(p)
changed=[name for name in before if before[name]!=after[name]];assert set(changed)<=set(paths)
c.save(c.HERE/'formatting.json',{'argv':argv,'cwd':str(p),'startedUTC':started,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'toolSHA256':c.sha(tool.read_bytes()),'exitCode':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode(),'before':before,'after':after,'changedFiles':changed})
assert result.returncode==0
print(c.sha(c.enc(after)))
