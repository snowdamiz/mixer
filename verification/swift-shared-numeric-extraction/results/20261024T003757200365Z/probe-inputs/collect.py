#!/usr/bin/env python3
"""Frozen baseline/product snapshots, fresh targets, and executable parity receipts."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
RUN = HERE/'build'/('final-'+STAMP)
OUT = HERE/'results'/STAMP
RUN.mkdir(parents=True, exist_ok=False)
OUT.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
jsonbytes = lambda v: (json.dumps(v, sort_keys=True, indent=2)+'\n').encode()
digest = lambda v: hashlib.sha256(jsonbytes(v)).hexdigest()
base = HERE/'layout-review/20261024T003352353904Z/source.tar.gz'
revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
files = [ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']+sorted((ROOT/'vm/src').rglob('*'))+sorted((ROOT/'vm/tests').rglob('*'))+sorted((ROOT/'vm/include').rglob('*'))
files = [p for p in files if p.is_file()]
source = {str(p.relative_to(ROOT/'vm')):sha(p) for p in files}
(OUT/'product-source-manifest.json').write_bytes(jsonbytes(source))
product_archive = OUT/'product-source.tar.gz'
with tarfile.open(product_archive,'w:gz') as archive:
    for p in files: archive.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
shutil.copy2(base,OUT/'baseline-source.tar.gz')
inputs = {p.name:sha(p) for p in [HERE/'collect.py',HERE/'layout_probe.rs',HERE/'public_numeric_probe.rs']}
(OUT/'probe-inputs').mkdir()
for name in inputs: shutil.copy2(HERE/name,OUT/'probe-inputs'/name)
assert (ROOT/'vm/tests/span_numeric_extraction.rs').read_bytes()==(HERE/'public_numeric_probe.rs').read_bytes()
commands=[]; variants=[]; comparisons=[]; logs={}
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
def manifest(path): return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}
def command(name,argv,cwd,target=None,closure=None,allow_failure=False):
    if closure is not None: assert manifest(cwd)==closure,'source changed before '+name
    penv=dict(env)
    if target: penv['CARGO_TARGET_DIR']=str(target)
    p=subprocess.run(argv,cwd=cwd,env=penv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1200)
    log=OUT/(name+'.log');log.write_bytes(p.stdout)
    if closure is not None: assert manifest(cwd)==closure,'source changed after '+name
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,
        exit=p.returncode,log=log.name,logSHA256=sha(log),sourceBeforeAfterVerified=closure is not None))
    print(name,p.returncode,flush=True)
    if p.returncode and not allow_failure: raise RuntimeError(p.stdout.decode(errors='replace')[-6000:])
    text=p.stdout.decode(errors='replace');logs[name]=text
    return text
def filtered(text,prefix):
    return [line[line.index(prefix):] for line in text.splitlines() if prefix in line]
try:
    command('rustc-version',['rustc','-vV'],ROOT)
    command('cargo-version',['cargo','-V'],ROOT)
    command('node-version',['node','--version'],ROOT)
    # Product checks have neither the layout probe nor any source instrumentation.
    with tarfile.open(product_archive) as tf: tf.extractall(RUN/'product',filter='data')
    product=RUN/'product/vm'; product_manifest=manifest(product)
    assert product_manifest==source
    command('product-metadata',['cargo','metadata','--locked','--offline','--no-deps','--format-version=1'],product,RUN/'product-metadata-target',product_manifest)
    command('product-format',['cargo','fmt','--all','--','--check'],product,None,product_manifest)
    command('product-clippy-broad',['cargo','clippy','--locked','--offline','--all-targets','--all-features','--','-D','warnings'],product,RUN/'product-clippy-broad-target',product_manifest,allow_failure=True)
    command('product-clippy-scoped',['cargo','clippy','--locked','--offline','--lib','--test','span_numeric_extraction','--all-features','--','-D','warnings'],product,RUN/'product-clippy-scoped-target',product_manifest)
    configurations=[('default',[]),('span',['--features','experimental-span-execution']),
        ('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]
    for name,flags in configurations:
        command('product-check-'+name,['cargo','check','--locked','--offline','--lib',*flags],product,RUN/('product-check-'+name+'-target'),product_manifest)
    for variant,archive in [('baseline',OUT/'baseline-source.tar.gz'),('candidate',product_archive)]:
        with tarfile.open(archive) as tf: tf.extractall(RUN/variant,filter='data')
        dest=RUN/variant/'vm'
        (dest/'tests/span_numeric_extraction.rs').write_bytes((OUT/'probe-inputs/public_numeric_probe.rs').read_bytes())
        if variant=='baseline':
            uninstrumented=manifest(dest)
            command('baseline-clippy-broad',['cargo','clippy','--locked','--offline','--all-targets','--all-features','--','-D','warnings'],dest,RUN/'baseline-clippy-broad-target',uninstrumented,allow_failure=True)
        execution=dest/'src/experimental/execution/mod.rs'
        execution.write_text(execution.read_text()+'\n#[cfg(all(test, feature = "experimental-span-execution"))]\n#[path = "numeric_layout_probe.rs"]\nmod numeric_layout_probe;\n')
        (dest/'src/experimental/execution/numeric_layout_probe.rs').write_text('use super::*;\n'+(OUT/'probe-inputs/layout_probe.rs').read_text())
        closure=manifest(dest)
        (OUT/(variant+'-probe-manifest.json')).write_bytes(jsonbytes(closure))
        variants.append(dict(name=variant,manifest=variant+'-probe-manifest.json',treeSHA256=digest(closure)))
        for config,flags in configurations:
            for profile in ['debug','release']:
                name=variant+'-'+config+'-'+profile
                target=RUN/(name+'-target')
                argv=['cargo','test','--locked','--offline',*flags]
                if profile=='release': argv+=['--release']
                argv+=['--lib','--test','differential','--test','float_differential','--test','float']
                if config in ['span','all']:
                    argv+=['--test','span_numeric_extraction','--test','span_execution','--test','span_execution_allocations','--test','span_execution_oracle']
                listed=command(name+'-list',argv+['--','--list'],dest,target,closure)
                executed=command(name,argv+['--','--nocapture','--test-threads=1'],dest,target,closure)
                tests=[line for line in listed.splitlines() if line.endswith(': test')]
                assert tests,'no executable tests listed'
                if config in ['span','all']:
                    assert 'shared_numeric_public_parity_trace: test' in listed
                    assert len(filtered(executed,'primitive_window '))==8
                    assert 'scalar=128 saturating=64 corners=10 total=202' in executed
                (OUT/(name+'-executed-tests.json')).write_bytes(jsonbytes(dict(tests=tests,count=len(tests),listCommand=name+'-list',runCommand=name)))
    for config,_ in configurations:
        for profile in ['debug','release']:
            a=logs['baseline-'+config+'-'+profile]
            b=logs['candidate-'+config+'-'+profile]
            item=dict(configuration=config,profile=profile)
            for prefix,key in [('numeric_trace ','publicTrace'),('primitive_window ','typedWindows'),
                ('primitive_position ','typedPositions'),('numeric_offset ','frozenOffsets'),
                ('numeric_owner ','frozenOwners'),('numeric_reservation ','frozenReservation')]:
                left=filtered(a,prefix);right=filtered(b,prefix)
                assert left==right,'baseline/candidate mismatch '+config+'/'+profile+'/'+key
                item[key]=dict(equal=True,records=len(left),sha256=hashlib.sha256(('\n'.join(left)+'\n').encode()).hexdigest())
            if config in ['span','all']: assert item['publicTrace']['records']>300
            comparisons.append(item)
    assert all(sha(ROOT/'vm'/p)==h for p,h in source.items()),'live product source changed'
    assert all(sha(HERE/name)==h for name,h in inputs.items()),'probe inputs changed'
    status='passed-host-primitive-dispatch-parity-only'
except Exception:
    status='failed'
    raise
finally:
    (OUT/'comparisons.json').write_bytes(jsonbytes(comparisons))
    (OUT/'receipt.json').write_bytes(jsonbytes(dict(schema=1,status=status,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        revision=revision,finalRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        scope='Frozen primitive dispatch only; exact independent public SpanInstance traces and typed inventories; no Swift execution or devices.',
        baselineArchiveSHA256=sha(OUT/'baseline-source.tar.gz'),productArchiveSHA256=sha(product_archive),
        productSourceTreeSHA256=digest(source),inputs=inputs,variants=variants,commands=commands,comparisons=comparisons,
        productVMUnchangedDuringVerification=all(sha(ROOT/'vm'/p)==h for p,h in source.items()),
        dirtyStatus=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))))
    print(str(OUT),flush=True)
