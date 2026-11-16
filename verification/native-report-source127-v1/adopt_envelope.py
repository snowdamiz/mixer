#!/usr/bin/env python3
"""Typed source127 registration; exact current126 inverse, development scope only."""
import argparse, hashlib, importlib.util, json, os, stat, sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREVIOUS='verification/native-report-source126-v1'
TYPE='EXACT_SAME_BUILD_PUBLIC_REPORT_SOURCE127_SUCCESSOR'
GATES={'actual_report_evidence','independent_packet_review','explicit_successor_selection'}
PRODUCTS={'cli/Sources/MixerBuild/SameBuildPublicReport.swift','cli/Sources/MixerCLI/main.swift'}
MAX_BYTES=8*1024*1024
def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result

def relative(name):
    need(type(name) is str and len(name) <= 1024 and '\\' not in name and '\0' not in name,
         'Invalid relative path')
    p = Path(name)
    need(p.as_posix() == name and not p.is_absolute() and name not in ('', '.')
         and not any(v in ('.', '..', '.git') for v in p.parts), 'Invalid relative path')
    return p

def regular(path):
    p = Path(path).absolute()
    for ancestor in [*reversed(p.parents), p]:
        need(not ancestor.is_symlink(), 'Symlink forbidden: ' + str(ancestor))
    st = p.stat()
    need(stat.S_ISREG(st.st_mode) and st.st_size <= MAX_BYTES, 'Bounded regular file required')
    return p

def read(path):
    return regular(path).read_bytes()

def row(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def load_json(path):
    return json.loads(read(path), object_pairs_hook=unique)

def digest(rows):
    return hashlib.sha256(''.join(p + '\0' + r['sha256'] + '\n'
                                  for p, r in sorted(rows.items())).encode()).hexdigest()

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, regular(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def source_input_path(name):
    p = relative(name)
    need('__pycache__' not in p.parts and p.suffix.lower() not in {'.pyc', '.pyo'},
         'Derived Python cache is not a source input: ' + name)
    return p

def check_rows(root, rows):
    need(type(rows) is dict and len(rows) <= 2048, 'Bounded rows required')
    paths = {name: source_input_path(name) for name in rows}
    for name, expected in rows.items():
        need(row(read(root / paths[name])) == expected, 'Owning bytes differ: ' + name)

def closed_members(root, members):
    """Exact authority only; excluded scratch directories are never descended."""
    allowed = set(members)
    directories = {p.as_posix() for name in allowed for p in Path(name).parents if p != Path('.')}
    observed, folders = set(), set()
    remaining = len(allowed) + len(directories) + 2
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    def walk(fd, prefix=''):
        nonlocal remaining
        with os.scandir(fd) as entries:
            for entry in entries:
                remaining -= 1
                need(remaining >= 0, 'Authority membership budget exceeded')
                name = prefix + entry.name
                scratch = not prefix and name in {'control-scratch'}
                need(scratch or name in allowed or name in directories,
                     'Unknown authority member: ' + name)
                mode = entry.stat(follow_symlinks=False).st_mode
                if scratch or name in directories:
                    need(stat.S_ISDIR(mode), 'Authority directory required')
                    if not scratch:
                        folders.add(name)
                        child = os.open(entry.name, flags, dir_fd=fd)
                        try:
                            walk(child, name + '/')
                        finally:
                            os.close(child)
                else:
                    need(stat.S_ISREG(mode), 'Authority regular file required')
                    observed.add(name)
    fd = os.open(root, flags)
    try:
        walk(fd)
    finally:
        os.close(fd)
    need(observed == allowed and folders == directories, 'Authority membership differs')
def inverse127(binding, selected):
    t=binding['report_transition']
    need(type(t) is dict and set(t)=={'schema','type','sourceCountBefore','sourceCountAfter',
         'sourceBefore','sourceAfter','changes','qualification','scope'},'Transition fields differ')
    need(type(t['schema']) is int and t['schema']==1 and t['type']==TYPE
         and type(t['sourceCountBefore']) is int and t['sourceCountBefore']==126
         and type(t['sourceCountAfter']) is int and t['sourceCountAfter']==127
         and t['qualification'] is False and t['scope']=='verified_subset; aggregate and GA false',
         'Typed source127 transition differs')
    need(type(selected) is dict and len(selected)==127 and digest(selected)==t['sourceAfter']=='58e548dd97b80f4f023e33efc5a73b857cb7a62018738ac59e1f1b02bcf394f7',
         'Selected source127 differs')
    need(type(t['changes']) is dict and set(t['changes'])==PRODUCTS,'Exact two products required')
    previous=dict(selected)
    for name,c in t['changes'].items():
        need(type(c) is dict and set(c)=={'before','after'} and selected.get(name)==c['after'],
             'Selected product differs')
        if c['before'] is None:
            need(name=='cli/Sources/MixerBuild/SameBuildPublicReport.swift','Wrong null preimage')
            del previous[name]
        else:
            need(name=='cli/Sources/MixerCLI/main.swift','Wrong replacement')
            previous[name]=c['before']
    need(len(previous)==126 and digest(previous)==t['sourceBefore']
         =='b5aaa0ad4822f9f2e4d35fd3e3853ffc3b5be2575c15a8297027de70f2b942a1'
         and previous==load_json(HERE/'predecessor-source-inputs.json')
         ==load_json(ROOT/PREVIOUS/'current-source-inputs.json'),'Exact current126 inverse differs')
    return previous

def admit():
    seal=load_json(HERE/'seal.json')
    need(set(seal)=={'schema','members','tree_sha256'} and type(seal['schema']) is int
         and seal['schema']==1 and digest(seal['members'])==seal['tree_sha256'],'Seal differs')
    closed_members(HERE,{*seal['members'],'seal.json'})
    check_rows(HERE,seal['members'])
    b=load_json(HERE/'binding.json')
    need(set(b)=={'schema','type','source','profile','renderer_pair21_transition','report_transition',
      'predecessor_authority','predecessor_seal','predecessor_bytes','ordinary_test','root_gates',
      'adoption','activation','aggregate','GA','holdsReleased','frozen_composition','root_evidence',
      'limitations'},'Binding fields differ')
    need(type(b['schema']) is int and b['schema']==1 and b['type']==TYPE,'Binding type differs')
    need(set(b['root_gates'])==GATES and all(v is False for v in b['root_gates'].values())
         and all(b[k] is False for k in ('adoption','activation','aggregate','GA','holdsReleased')),
         'Root scope differs')
    selected=load_json(HERE/'current-source-inputs.json')
    # Reject every cache pathname before reading any declared source bytes.
    for rows in (selected,load_json(HERE/'owning-closure.json'),load_json(HERE/'caller-inputs.json')):
        for name in rows: source_input_path(name)
    check_rows(ROOT,selected)
    owner=module('source127_owner',ROOT/'scripts/ci/check-android-generated-java.py')
    need(owner.source_inputs(owner.load_profile(ROOT))==selected,'Owning production roster differs')
    previous=inverse127(b,selected)
    need(b['source']=={'count':127,'sha256':digest(selected),'manifest':'current-source-inputs.json'},
         'Source metadata differs')
    closed_members(ROOT/PREVIOUS,b['predecessor_authority'])
    check_rows(ROOT/PREVIOUS,b['predecessor_authority'])
    need(row(read(ROOT/PREVIOUS/'seal.json'))==b['predecessor_seal'] and b['predecessor_seal']['sha256']=='ad35c4d7a66b955c964ba1f0d6f6321190bf1e96100235adfbfd6de6a681c20a' and digest(b['predecessor_authority'])=='4f5dac1e3a3fb19195ddb5477bb9f159ba0567c621533e4b6fcc13e9e1f52c64','Current126 seal changed')
    old=load_json(ROOT/PREVIOUS/'binding.json')
    need(b['profile']==old['profile'] and b['renderer_pair21_transition']==old['renderer_pair21_transition'],
         'Pair21 changed')
    check_rows(ROOT,load_json(HERE/'owning-closure.json'))
    check_rows(ROOT,load_json(HERE/'caller-inputs.json'))
    need(set(b['predecessor_bytes'])==PRODUCTS|{
         'cli/Tests/MixerBuildTests/NativeOutputAdmissionTests.swift',
         'cli/build-tests/current_android_profile.py','.github/workflows/verify.yml',
         'verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py',
         'verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_sparse_checkout.py'},
         'Exact caller changes required')
    for name,c in b['predecessor_bytes'].items():
        need(row(read(ROOT/source_input_path(name)))==c['after'],'Installed bytes differ')
        if c['before'] is None: need(c['preimage'] is None,'Null preimage required')
        else: need(row(read(HERE/source_input_path(c['preimage'])))==c['before'],'Preimage differs')
    test=b['ordinary_test']
    need(test['path']=='cli/Tests/MixerBuildTests/NativeOutputAdmissionTests.swift'
         and test['original_cases']==24 and test['added_unit_cases']==6 and test['runtime_pass'] is False
         and test['path'] not in selected and row(read(ROOT/test['path']))==test['identity'],
         'Ordinary composition differs')
    need(b['frozen_composition']['private_helper_and_package_excluded'] is True,
         'Private harness forbidden')
    return b,selected,previous

def legacy_view(binding,previous):
    legacy=module('public127_immutable126',ROOT/PREVIOUS/'adopt_envelope.py')
    original_regular,original_module=legacy.regular,legacy.module
    changes=binding['predecessor_bytes']
    def prior_regular(path):
        p=Path(path)
        name=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else None
        if name in changes and changes[name]['preimage']:
            return original_regular(HERE/changes[name]['preimage'])
        return original_regular(path)
    def prior_module(name,path):
        m=original_module(name,path)
        if Path(path)==ROOT/'scripts/ci/check-android-generated-java.py':
            m.source_inputs=lambda profile:dict(previous)
        return m
    legacy.regular,legacy.module=prior_regular,prior_module
    original_view=legacy.legacy_view
    def view126(b126,p121):
        l121=original_view(b126,p121)
        base_regular=l121.regular
        def r121(path):
            p=Path(path);name=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else None
            if name in changes and name not in b126['predecessor_bytes'] and changes[name]['preimage']:
                return base_regular(HERE/changes[name]['preimage'])
            return base_regular(path)
        l121.regular=r121
        original121=l121.legacy_view
        def view121(b121,p119):
            historical,base=original121(b121,p119);base_regular119=base.regular
            def r119(path):
                p=Path(path);name=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else None
                if name in changes and name not in b126['predecessor_bytes'] and name not in b121['predecessor_bytes'] and changes[name]['preimage']:
                    return base_regular119(HERE/changes[name]['preimage'])
                return base_regular119(path)
            base.regular=r119
            return historical,base
        l121.legacy_view=view121
        return l121
    legacy.legacy_view=view126
    return legacy

def verify(installed=False):
    b,s,p=admit()
    historical=legacy_view(b,p).verify(installed)
    return {'schema':1,'type':TYPE,'source_count':127,'source_sha256':digest(s),
      'predecessor_source_count':126,'predecessor_source_sha256':digest(p),
      'historical126':historical,'root_gates':b['root_gates'],'aggregate':False,
      'adoption':False,'activation':False,'GA':False,'holdsReleased':False}

def prepare_predecessor(out):
    b,s,p=admit();out=Path(out).absolute()
    need(not out.exists() and not out.is_symlink(),'Fresh predecessor directory required')
    for a in [*out.parents,out]: need(not a.is_symlink(),'Predecessor symlink')
    files=dict(load_json(HERE/'owning-closure.json'));files.update(load_json(HERE/'caller-inputs.json'))
    files.update(p)
    prepared={}
    for name in files:
        c=b['predecessor_bytes'].get(name)
        if c and c['before'] is None:continue
        prepared[name]=read(HERE/c['preimage']) if c else read(ROOT/name)
    need(len(prepared)<=2048 and sum(map(len,prepared.values()))<=64*1024*1024,'Predecessor budget')
    out.mkdir(parents=True,mode=0o700)
    for name,raw in prepared.items():
        q=out/source_input_path(name);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
    for name in (PREVIOUS,'verification/native-output-source121-v1',
          'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3',
          'verification/envelope-rust-1991-default-ci-adoption',
          'verification/envelope-rust-1991-default-ci-adoption/validation'):
        (out/name/'control-scratch').mkdir(parents=True,exist_ok=True)
    return {'files':len(prepared),'bytes':sum(map(len,prepared.values())),'source126':digest(p),'out':str(out)}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('verify');p.add_argument('--workflow-installed',action='store_true')
    p=sub.add_parser('prepare-predecessor');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--out',type=Path,required=True);p.add_argument('--rustc',required=True)
    a=parser.parse_args()
    if a.command=='verify':print(json.dumps(verify(a.workflow_installed),sort_keys=True))
    elif a.command=='prepare-predecessor':print(json.dumps(prepare_predecessor(a.out),sort_keys=True))
    else:
        b,_,p=admit();l126=legacy_view(b,p);l121=l126.legacy_view(l126.admit()[0],l126.admit()[2])
        old,base=l121.legacy_view(l121.admit()[0],l121.admit()[2])
        prior=base.verify
        def both(installed=False):
            admit();return dict(prior(installed),public_report_source127=digest(load_json(HERE/'current-source-inputs.json')))
        base.verify=both
        return old.run_fixture(base,a.out,a.rustc)
    return 0
if __name__=='__main__':sys.exit(main())
