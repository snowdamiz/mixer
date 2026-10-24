from pathlib import Path
import ast,importlib.util,shutil,json,os,subprocess,datetime,hashlib,gzip
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];CAND=ROOT/'verification/swift-control-accounting-candidate-2';SCRATCH=Path('/tmp/mixer-swift-control-behavior-20261024');SOURCE=SCRATCH/'vm';META=SCRATCH/'metadata-vm';OUT=HERE/'metadata-results'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');OUT.mkdir(parents=True)
spec=importlib.util.spec_from_file_location('builder',CAND/'build_overlay.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
# Reuse the frozen metadata instrumentation source, without running its producer.
module=ast.parse((CAND/'collect.py').read_text());defs=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['metadata_source','parse_layout']]
ns=dict(ROOT=ROOT,HERE=CAND,json=json,Path=Path);exec(compile(ast.Module(body=defs,type_ignores=[]),str(CAND/'collect.py'),'exec'),ns)
if META.exists():shutil.rmtree(META)
shutil.copytree(SOURCE,META);ns['metadata_source'](META,'candidate')
# Exact new unit class/field offsets; original containing inventories unchanged.
rows=json.loads((HERE/'unit-hook-inventory.json').read_text());code=['pub(super) fn control_hook_metadata(){']
for envelope,cls in [('permanent','ControlHookPermanentPositions'),('active','ControlHookActivePositions')]:
 code.append(f'println!("CPI_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
 for row in rows:
  if row['envelope']==envelope:code.append(f'println!("CPI_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({cls},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
code+=['println!("CPI_TYPE Hooks {} {}",size_of::<Hooks>(),std::mem::align_of::<Hooks>());','}']
p=META/'src/experimental_swift_reactor/frame_operations_tests.rs';p.write_text(p.read_text()+'\n'+'\n'.join(code)+'\n')
p=META/'src/experimental_swift_reactor/frame_operations.rs';p.write_text(p.read_text().replace('pub(crate) fn accounting_preflight_metadata(){','pub(crate) fn accounting_preflight_metadata(){\n#[cfg(test)] tests::control_hook_metadata();',1))
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(SCRATCH/'metadata-target'));env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
manifest=builder.files(META);(OUT/'instrumented-manifest.json').write_bytes(builder.enc(manifest));commands=[];layouts=[]
for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  for unit in [False,True]:
   name=config+('-release' if release else '-debug')+('-unit' if unit else '-production');args=['cargo','test','--lib',*flags,*(['--release'] if release else []),'control_accounting_preflight_metadata_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--bin','control_accounting_layout',*flags,*(['--release'] if release else [])]
   start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=META,env=env,capture_output=True)
   for stream in ['stdout','stderr']:
    data=getattr(p,stream)
    with gzip.open(OUT/(name+'.'+stream+'.gz'),'wb') as f:f.write(data)
   commands.append(dict(name=name,argv=args,cwd=str(META),sourceTreeSHA256=hashlib.sha256(builder.enc(manifest)).hexdigest(),startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,stdout=name+'.stdout.gz',stderr=name+'.stderr.gz'))
   (OUT/'commands.json').write_bytes(builder.enc(commands));print(name,p.returncode,flush=True)
   assert p.returncode==0,p.stderr.decode()[-6000:]
   layout=ns['parse_layout'](p.stdout.decode());layout.update(config=config,profile='release' if release else 'debug',unit=unit);layouts.append(layout)
   (OUT/'layouts.json').write_bytes(builder.enc(layouts))
   if not unit:assert (layout['totals']['new_permanent'],layout['totals']['new_active'],layout['totals']['header'],layout['totals']['frame_bound'])==(105280,1162520,1514504,2211968)
   else:
    perm=layout['classes']['ControlHookPermanentPositions']['bytes'];active=layout['classes']['ControlHookActivePositions']['bytes'];assert layout['totals']['new_permanent']==105312+perm;assert layout['totals']['new_active']==2325032+active;assert layout['totals']['header']==2392040+perm;assert layout['totals']['frame_bound']==3949904+active
    for cls in ['ControlHookPermanentPositions','ControlHookActivePositions']:
     selected=[r for r in rows if (r['envelope']=='permanent')==(cls=='ControlHookPermanentPositions')];last=0
     for row in sorted(selected,key=lambda r:(layout['fields'][r['field']]['offset'],layout['fields'][r['field']]['bytes'])):
      field=layout['fields'][row['field']];assert field['offset']%field['alignment']==0;assert field['offset']>=last;last=field['offset']+field['bytes'];assert last<=layout['classes'][cls]['bytes']
print('metadata complete',flush=True)
