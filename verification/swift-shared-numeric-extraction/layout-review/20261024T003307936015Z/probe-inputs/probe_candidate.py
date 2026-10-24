#!/usr/bin/env python3
"""Fresh source overlay for the reviewed numeric-only extraction; no product edits."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'build' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
RUN.mkdir(parents=True, exist_ok=False)
OUT = RUN / 'results'
OUT.mkdir()
revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
jsonbytes = lambda v: (json.dumps(v, sort_keys=True, indent=2)+'\n').encode()
files = [ROOT/'vm/Cargo.toml', ROOT/'vm/Cargo.lock'] + sorted((ROOT/'vm/src').rglob('*')) + sorted((ROOT/'vm/tests').rglob('*')) + sorted((ROOT/'vm/include').rglob('*'))
files = [p for p in files if p.is_file()]
source = {str(p.relative_to(ROOT/'vm')): sha(p) for p in files}
(OUT/'source-manifest.json').write_bytes(jsonbytes(source))
archive = OUT/'source.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for p in files: tf.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
inputs = {p.name:sha(p) for p in (HERE/'numeric_candidate.rs', HERE/'layout_probe.rs', HERE/'probe_candidate.py')}
(OUT/'probe-inputs').mkdir()
for name in inputs: shutil.copy2(HERE/name,OUT/'probe-inputs'/name)
commands=[]; variants=[]
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
def command(name, argv, cwd, target=None, manifest=None):
    def unchanged():
        assert {str(p.relative_to(cwd)):sha(p) for p in cwd.rglob('*') if p.is_file()} == manifest
    if manifest: unchanged()
    penv=dict(env)
    if target: penv['CARGO_TARGET_DIR']=str(target)
    p=subprocess.run(argv,cwd=cwd,env=penv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
    (OUT/(name+'.log')).write_bytes(p.stdout)
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,exit=p.returncode,log=name+'.log',sourceBeforeAfterVerified=manifest is not None))
    print(name,p.returncode,flush=True)
    if manifest: unchanged()
    if p.returncode: raise RuntimeError(p.stdout.decode(errors='replace')[-6000:])
try:
    command('rustc-version',['rustc','-vV'],ROOT)
    command('cargo-version',['cargo','-V'],ROOT)
    for variant in ['base','candidate']:
        with tarfile.open(archive) as tf: tf.extractall(RUN/variant,filter='data')
        dest=RUN/variant/'vm'
        mod=dest/'src/experimental/execution/mod.rs'
        borrowed=dest/'src/experimental/execution/borrowed.rs'
        if variant=='candidate':
            text=mod.read_text()
            start=text.index('        let result = if saturating {',text.index('    fn numeric(&mut self, opcode: u8, saturating: bool)'))
            end=text.index('        self.observe();',start)
            text=text[:start]+'        let result = borrowed::numeric::<borrowed::FrozenMode>(self, opcode, saturating);\n'+text[end:]
            text=text.replace('#[cfg(feature = "experimental-swift-reactor")]\npub(crate) mod borrowed;', '#[cfg(any(feature = "experimental-span-execution", feature = "experimental-swift-reactor"))]\npub(crate) mod borrowed;')
            mod.write_text(text)
            borrowed.write_text(borrowed.read_text()+(HERE/'numeric_candidate.rs').read_text())
        borrowed.write_text(borrowed.read_text()+'\n#[cfg(test)]\n#[path = "numeric_layout_probe.rs"]\nmod numeric_layout_probe;\n')
        probe=dest/'src/experimental/execution/numeric_layout_probe.rs'
        probe.write_text('use super::*;\n'+(HERE/'layout_probe.rs').read_text())
        manifest={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()}
        (OUT/(variant+'-manifest.json')).write_bytes(jsonbytes(manifest))
        variants.append(dict(name=variant,manifest=variant+'-manifest.json',treeSHA256=hashlib.sha256(jsonbytes(manifest)).hexdigest()))
        command(variant+'-layout',['cargo','test','--locked','--offline','--all-features','--lib','shared_numeric_actual_layout','--','--nocapture'],dest,RUN/variant/'target',manifest)
        command(variant+'-layout-list',['cargo','test','--locked','--offline','--all-features','--lib','shared_numeric_actual_layout','--','--list'],dest,RUN/variant/'target',manifest)
    status='derived-candidate-layout-executed-only'
except Exception:
    status='failed'
    raise
finally:
    (OUT/'receipt.json').write_bytes(jsonbytes(dict(schema=1,status=status,revision=revision,finalRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sourceManifest=source,archiveSHA256=sha(archive),inputs=inputs,commands=commands,variants=variants,productVMUnchanged=all(sha(ROOT/'vm'/p)==h for p,h in source.items()))))
    print(str(OUT),flush=True)
