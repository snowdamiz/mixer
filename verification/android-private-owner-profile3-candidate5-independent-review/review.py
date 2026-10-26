#!/usr/bin/env python3
"""Independent host-only review. Never starts native runtimes or inventories processes."""
import ast
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from unittest import mock

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / 'verification/android-private-owner-profile3-integration/candidate5-qualification'
CANDIDATE = ROOT / 'verification/android-private-owner-integration-implementation/candidate-5'
SWIFT = Path('/usr/bin/swift')
ANDROID_SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
STRIP = ('CLASSPATH', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS',
         'JDK_JAVAC_OPTIONS', 'JAVA_OPTS', 'SWIFT_EXEC', 'SWIFT_DRIVER_SWIFT_FRONTEND_EXEC',
         'DYLD_INSERT_LIBRARIES', 'LD_PRELOAD', 'SDKROOT', 'TOOLCHAINS')

def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def load(path):
    return json.loads(path.read_text())

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def check(value, message):
    if not value:
        raise RuntimeError(message)

def files(root):
    result = {}
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in {'.build', '.swiftpm', '__pycache__'})
        for name in sorted(names):
            path = Path(directory) / name
            check(not path.is_symlink(), 'unexpected symlink ' + str(path))
            result[path.relative_to(root).as_posix()] = ident(path.read_bytes())
    return result

def project(files):
    return hashlib.sha256(''.join(p + '\0' + files[p]['sha256'] + '\n' for p in sorted(files)).encode()).hexdigest()

def imported(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Review:
    def __init__(self):
        self.env = {k: v for k, v in os.environ.items() if k not in STRIP}
        self.env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
                        MIXER_SWIFT=str(ANDROID_SWIFT), PYTHONDONTWRITEBYTECODE='1')
        self.commands = []
        self.scratch = []
        self.receipt = {'schema': 1, 'status': 'failed', 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        'scope': 'independent exact candidate5 profile3 CLI host admission and copied app semantics only',
                        'native_runtime_UI_capture_process_inventory': False, 'GA_qualified': False,
                        'native_owner_accepted': False, 'pid': os.getpid(), 'pgid': os.getpgrp(), 'argv':[sys.executable,*sys.argv],
                        'python': {'path': str(Path(sys.executable).resolve()), **ident(Path(sys.executable).resolve().read_bytes())},
                        'python_version': sys.version, 'runner': ident(Path(__file__).read_bytes())}

    def run(self, label, argv, cwd=ROOT, env=None, timeout=120, expected=0, binding=None):
        path = BASE / 'commands' / label
        path.mkdir(parents=True)
        argv = list(map(str, argv))
        resolved = Path(argv[0]).resolve()
        record = {'label': label, 'argv': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
                  'expected_exit': expected, 'start': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'executable': {'path': str(resolved), **ident(resolved.read_bytes())},
                  'source_binding_sha256': self.receipt.get('source_binding_sha256'), 'input_binding': binding,
                  'environment': {'PATH': (env or self.env)['PATH'], 'MIXER_SWIFT': (env or self.env)['MIXER_SWIFT'],
                                  'removed_injection_variable_names': list(STRIP)},
                  'output_limit_bytes_per_stream': 2_097_152}
        start = time.monotonic()
        with (path / 'stdout').open('wb') as out, (path / 'stderr').open('wb') as err:
            p = subprocess.Popen(argv, cwd=cwd, env=env or self.env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            record.update(pid=p.pid, pgid=p.pid)
            save(path / 'command.json', record)
            timed_out = oversized = False
            while p.poll() is None:
                timed_out = time.monotonic() - start > timeout
                oversized = max((path / 'stdout').stat().st_size, (path / 'stderr').stat().st_size) > 2_097_152
                if timed_out or oversized:
                    os.killpg(p.pid, signal.SIGKILL)
                    break
                time.sleep(.05)
            p.wait()
        stdout = (path / 'stdout').read_bytes(); stderr = (path / 'stderr').read_bytes()
        record.update(exit=p.returncode, timed_out=timed_out, output_limit_exceeded=oversized,
                      elapsed_seconds=time.monotonic()-start, stdout=ident(stdout), stderr=ident(stderr),
                      child_reaped=True, own_group_signaled=timed_out or oversized)
        save(path / 'result.json', record); self.commands.append(record)
        save(BASE / 'commands.json', self.commands)
        print(label, p.returncode, flush=True)
        check(not timed_out and not oversized and p.returncode == expected, label + ' command failed')
        return stdout, stderr

    def audit(self):
        pins = {'manifest.json': '31e034832247144f6f042006f4725dbf0242408ec33d61b9d1cedaa688b90ec4',
                'seal-receipt.json': '8ffb4ec37ff4189a330dfb0c32b427d7399365fdbf3c94a5a64ea6b70cf92db0'}
        for name, sha in pins.items():
            check(ident((PACKET/name).read_bytes())['sha256'] == sha, 'producer seal pin ' + name)
        self.external_pins = {
            'verification/android-private-owner-effect-integration-root-review/candidate-5-admission.json': '8f125495bc3ad3f31d41408f0cbae97487016152ec123c1fab79416628daa48d',
            'verification/android-private-owner-effect-integration-root-review/candidate-5-profile-selection.json': '990f8dff5a27f30892aa5671394f072f5a093658a8b71eb6bbe1848c34bcbe2d',
            'verification/android-private-owner-integration-implementation/candidate-5/manifest.json': '59a820bd3cd7e01ead02114293028985f64a42eebc36094cef9d76f516eee1f1',
            'verification/android-private-owner-integration-implementation/candidate-5/source-map.json': 'da250cd1e7560f8d702753769a132b70f60ea05477d133c32afd0c7372c542a1',
            'verification/android-private-owner-integration-implementation/candidate-5/profile-proposal.json': '6bcf2c6b0b0936522e3a6f5297765b6e4f795203b55721aabe7a82c4ba216a8f',
            'verification/android-private-owner-profile3-independent-review/manifest.json': '685a1d1f905540c023d3ffebd5eed392cde08fd8e07ee15e6d9d246dcbd8b7ac',
        }
        for name, sha in self.external_pins.items():
            check(ident((ROOT/name).read_bytes())['sha256'] == sha, 'external admission pin '+name)
        selection=load(ROOT/'verification/android-private-owner-effect-integration-root-review/candidate-5-profile-selection.json')
        check(selection['CLI_validation_authorized'] is True and selection['profile_id']=='mixer.android-source-pair.3', 'explicit selection')
        manifest = load(PACKET/'manifest.json')
        for name, value in manifest['files'].items():
            check(ident((PACKET/name).read_bytes()) == value, 'producer member ' + name)
        check(len(manifest['files']) == manifest['members'] == 1008 and sum(x['bytes'] for x in manifest['files'].values()) == manifest['bytes'] == 7073964, 'producer totals')
        check(set(files(PACKET)) == set(manifest['files']) | {'manifest.json', 'seal-receipt.json'}, 'producer closed inventory')
        self.profile = load(CANDIDATE/'profile-proposal.json')
        swift = (PACKET/'source/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
        literal = swift.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0]
        check(json.loads(literal) == self.profile, 'Swift profile exact equality')
        for kind in ('adapter', 'sdk'):
            check(len(self.profile[kind+'_files']) == 22, 'profile inventory')
            check(project(self.profile[kind+'_files']) == self.profile[kind+'_compatibility_sha256'], 'projection')
        check(self.profile['adapter_compatibility_sha256']=='c5df444d5be8f7d422dedde7786b0232f24db1b295288da3cc3fce31a27f5b59', 'adapter selection')
        check(self.profile['sdk_compatibility_sha256']=='4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7', 'SDK selection')
        source = load(PACKET/'source-binding.json')
        check(len(source['files']) == 356 and project(source['files']) == source['projection_sha256']=='f57c7145ff5465b2ad40accf12bb4852f17d7de270963ec3b7b2cd73e2577502', 'producer source binding')
        for name, value in source['files'].items():
            check(ident((PACKET/'source'/name).read_bytes()) == value, 'sealed source ' + name)
            check(ident((ROOT/name).read_bytes()) == value, 'live source ' + name)
        canonical = load(CANDIDATE/'source-map.json')
        check(len(canonical) == 311, 'canonical count')
        for name, value in canonical.items():
            check(ident((ROOT/name).read_bytes()) == value, 'canonical drift ' + name)
        previous=load(ROOT/'verification/android-private-owner-integration-implementation/candidate-4/profile-proposal.json')
        check(previous['id']==self.profile['id'] and previous['sdk_files']==self.profile['sdk_files'] and previous['wire']==self.profile['wire'] and previous['default_descriptor']==self.profile['default_descriptor'], 'profile preserved contracts')
        changed=[name for name in self.profile['adapter_files'] if self.profile['adapter_files'][name]!=previous['adapter_files'][name]]
        check(changed==['app/src/dev/mixer/android/NativeOwnerV2.java'], 'only owner identity changes')
        save(BASE/'profile-delta-review.json', {'changed_adapter_files':changed,'profile_id_unchanged':True,'SDK_default_wire_unchanged':True,'current_profile':self.profile,'previous_profile_sha256':ident((ROOT/'verification/android-private-owner-integration-implementation/candidate-4/profile-proposal.json').read_bytes())['sha256'],'scope':'compiled literal exact identity and map; not native implementation acceptance'})
        self.canonical = canonical
        self.original_source = source['files']
        producer_commands = load(PACKET/'commands.json')
        binding_hash = ident((PACKET/'source-binding.json').read_bytes())['sha256']
        unbound = []; all_bound = []; consumer_bound = []; version_bound=[]
        products = load(PACKET/'compiled-products-before-cleanup.json')
        disposition = load(PACKET/'binary-identity-disposition.json')
        successes=refusals=0
        for command in producer_commands:
            label = command['label']; cp = PACKET/'commands'/label
            check(load(cp/'result.json') == command, 'aggregate command binding ' + label)
            before=load(cp/'command.json')
            check(all(before[k]==command[k] for k in before), 'raw literal argv/provenance '+label)
            check(ident((cp/'stdout').read_bytes()) == command['stdout'] and ident((cp/'stderr').read_bytes()) == command['stderr'], 'producer output binding ' + label)
            check(command['exit'] == command['expected_exit'] and not command['timed_out'] and command['child_reaped'], 'producer command disposition ' + label)
            check(command['expected_exit'] in (0,1), 'unexpected producer expectation')
            successes += command['expected_exit']==0; refusals += command['expected_exit']==1
            (all_bound if command.get('source_binding_sha256') == binding_hash else unbound).append(label)
            if command['argv'][0].endswith('/mixer'):
                group = 'debug' if 'build-cli-debug/' in command['argv'][0] else 'release'
                key = str(Path(command['argv'][0]).relative_to(PACKET))
                observed = {k: command['executable'][k] for k in ('bytes', 'sha256')}
                if command['argv'][1]=='version':
                    check(observed==disposition[group]['initial_version_binary'], 'pre-test version identity '+label)
                    version_bound.append(label)
                else:
                    check(observed == products[key] == disposition[group]['actual_consumer_and_refusal_binary'], 'actual producer binary ' + label)
                    consumer_bound.append(label)
            if command['executable']['path'] and not command['argv'][0].endswith('/mixer'):
                exe=Path(command['executable']['path'])
                check(ident(exe.read_bytes())=={k:command['executable'][k] for k in ('bytes','sha256')}, 'current producer direct executable '+label)
        check(len(producer_commands)==101 and successes==29 and refusals==72, 'producer command totals')
        check(unbound==['tracked-input-list'], 'producer source binding coverage')
        check(len(consumer_bound)==66 and len(products)==39, 'producer product command counts')
        check(disposition['release']['identity_changed_during_swift_test'] is True and disposition['debug']['identity_changed_during_swift_test'] is False, 'recorded relink')
        method_counts = {}
        for mode in ('debug', 'release'):
            folder = PACKET/'commands'/(mode+'-swift-tests')
            text = (folder/'stdout').read_text() + (folder/'stderr').read_text()
            check('Test run with 13 tests in 0 suites passed' in text, 'Swift method count ' + mode)
            method_counts[mode] = 13
        counts = {}
        for mode in ('normal', 'optimized'):
            for suite, count in [('test_android_sdk_compatibility',10), ('test_android_staging',9), ('test_android_appearance',11)]:
                text = (PACKET/'commands'/('python-'+mode+'-'+suite)/'stderr').read_text()
                check('Ran '+str(count)+' tests' in text and 'OK' in text, 'Python method count')
                counts[mode+'-'+suite] = count
        producer_receipt=load(PACKET/'receipt.json')
        for name in producer_receipt['cleanup']['owned_scratch_removed']:check(not (PACKET/name).exists(), 'producer scratch remains')
        save(BASE/'producer-audit.json', {'pins': pins, 'external_pins':self.external_pins,
            'packet_members_verified': 1008, 'packet_bytes_verified': 7073964,
            'producer_source_members_verified': 356, 'canonical_members_verified': 311, 'exact_profile': ident((CANDIDATE/'profile-proposal.json').read_bytes()),
            'commands_verified': len(producer_commands), 'successful_commands':successes, 'expected_refusals':refusals,
            'source_bound_commands': all_bound, 'source_unbound_commands': unbound,
            'actual_consumer_refusal_binary_bound_commands': consumer_bound, 'pretest_version_bound_commands': version_bound,
            'Swift_methods_not_parameterized_cases': method_counts, 'Python_methods_not_inner_cases': counts,
            'no_producer_seal_failure': not (PACKET/'seal-attempt-1-disposition.json').exists(),
            'binary_identity_dispositions': disposition,'compiled_products_hashed_removed':len(products),
            'owned_scratch_removed': producer_receipt['cleanup']['owned_scratch_removed'],
            'scope_limit': 'source hash fields bind source snapshot, not compiler dependency traces; command receipts do not claim immutable sandbox attestation'})
        self.receipt['producer_audit'] = {'members': 1008, 'bytes': 7073964, 'commands': len(producer_commands),
                                         'source_unbound_command_labels': unbound, 'source356': source['projection_sha256']}

    def snapshot(self):
        selected = {k:v for k,v in self.original_source.items() if k.startswith(('cli/', 'sdk/', 'updates/'))}
        for relative in self.profile['adapter_files']:
            path = 'native/android/' + ('engine/'+relative if relative.startswith('Sources/') else relative)
            selected[path] = self.original_source[path]
        self.source = BASE/'source'
        for name, identity in selected.items():
            target = self.source/name; target.parent.mkdir(parents=True, exist_ok=True)
            data = (PACKET/'source'/name).read_bytes(); check(ident(data) == identity, 'copy source')
            target.write_bytes(data)
        save(BASE/'source-binding.json', {'files': selected, 'projection_sha256': project(selected),
                                         'scope': 'exact selected host CLI dependency closure and 22 adapter inputs; native test harness omitted'})
        self.selected = selected
        self.receipt.update(source_members=len(selected), source_projection_sha256=project(selected),
                            source_binding_sha256=ident((BASE/'source-binding.json').read_bytes())['sha256'])

    def build(self):
        versions = {}
        for label, argv in [('host-swift', [SWIFT,'--version']), ('python',[sys.executable,'--version']),('git',['/usr/bin/git','--version']),
                            ('resolved-swift', ['/usr/bin/xcrun','--find','swift']),('resolved-swiftc',['/usr/bin/xcrun','--find','swiftc'])]:
            out, err = self.run(label+'-version', argv); versions[label]=(out+err).decode().strip()
        versions['actual_compiler_files'] = {k:{'path':str(Path(versions[k]).resolve()), **ident(Path(versions[k]).resolve().read_bytes())}
                                            for k in ('resolved-swift','resolved-swiftc')}
        out,_=self.run('revision-context',['/usr/bin/git','rev-parse','HEAD'])
        self.receipt.update(versions=versions, revision_context_only=out.decode().strip())
        self.clis={}
        for config in ('debug','release'):
            scratch=BASE/('build-cli-'+config); self.scratch.append(scratch)
            common=['--package-path',self.source/'cli','--scratch-path',scratch,'--disable-automatic-resolution','--jobs','2','-c',config]
            self.run(config+'-cli-build',[SWIFT,'build',*common,'--product','mixer'],timeout=600)
            out,_=self.run(config+'-cli-bin-path',[SWIFT,'build',*common,'--show-bin-path'])
            self.clis[config]=Path(out.decode().strip())/'mixer'

    def consumers(self):
        self.app=BASE/'ReviewConsumer'; self.copy=BASE/'CopiedReviewConsumer'
        self.run('independent-create',[self.clis['debug'],'create','ReviewConsumer','--directory',self.app,
                 '--application','dev.mixer.independentreview','--platform','android','--sdk-path',self.source/'sdk',
                 '--android-adapter-path',self.source/'native/android'],timeout=300)
        self.run('independent-export',[self.clis['release'],'export',self.copy,'--directory',self.app])
        for app in (self.app,self.copy):
            driver=imported(app/'Generated/MixerAndroid/android-build.py','independent_'+app.name)
            check(driver.source_profile()==self.profile,'rendered Python exact profile')
            check(ident(driver.admit_source_pair(app,self.profile))==self.profile['default_descriptor'],'copied canonical descriptor')
            check(load(app/'mixer.lock')['android']['profile']==driver.profile_lock(self.profile),'copied lock')
            for kind, folder in [('sdk','MixerSDK'),('adapter','MixerAndroid')]:
                for name,value in self.profile[kind+'_files'].items():
                    check(ident((app/'Generated'/folder/name).read_bytes())==value,'exported byte path binding')
        self.driver=imported(self.copy/'Generated/MixerAndroid/android-build.py','independent_driver')
        self.run('python-positive-admission',[sys.executable,'-B',BASE/'python-probes.py',self.copy])
        self.run('python-optimized-positive-admission',[sys.executable,'-B','-O',BASE/'python-probes.py',self.copy])
        entry=self.copy/'Platforms/Android/Sources/AppAndroid/NativeEntry.swift'
        reducer=self.copy/'Sources/AppFeatures/ProjectFeature.swift'
        entry.write_text(entry.read_text().replace('ProjectFeatureState()', 'ProjectFeatureState(draft: "Independent factory seed")'))
        reducer.write_text(reducer.read_text().replace('state.draft = value','state.draft = "review:" + value'))
        custom=self.copy/'Platforms/Android/Tests/AppAndroidTests/IndependentReviewTests.swift'
        shutil.copyfile(BASE/'IndependentReviewTests.swift', custom)
        save(BASE/'consumer-binding.json',{'created':files(self.app),'exported_customized':files(self.copy),
                                           'customization_scope':'only app-owned factory, reducer, independent host tests'})
        scratch=BASE/'build-copied-host';self.scratch.append(scratch)
        self.run('independent-copied-host-tests',[SWIFT,'test','--package-path',self.copy/'Platforms/Android',
                 '--scratch-path',scratch,'--disable-automatic-resolution','--jobs','2','--filter','IndependentReviewTests'],timeout=600,
                 binding=ident((BASE/'consumer-binding.json').read_bytes()))

    def mutations(self):
        fixture=BASE/'mutation-fixture';shutil.copytree(self.app,fixture);self.scratch.append(fixture)
        trap=BASE/'trap-tools';trap.mkdir();marker=trap/'invoked'
        for name in ('swift','python3'):
            tool=trap/name;tool.write_text('#!/bin/sh\n/usr/bin/touch "'+str(marker)+'"\nexit 97\n');tool.chmod(0o755)
        env=dict(self.env,PATH=str(trap)+':'+self.env['PATH'],MIXER_SWIFT=str(trap/'swift'))
        old=load(fixture/'mixer.lock'); report=[]
        cases=[('profile2',None,None),('missing-lock',None,None),('stale-candidate4-profile',None,None)]
        cases += [(file[:-5]+'-'+action,file,action) for file in ('NativeOwnerV2.java','OwnerLifecycleV2.java') for action in ('same-size','remove','rename')]
        for label,filename,action in cases:
            lock=json.loads(json.dumps(old));source=fixture/'Generated/MixerAndroid/app/src/dev/mixer/android'/filename if filename else None
            before=source.read_bytes() if source else None; renamed=source.with_suffix('.review-renamed') if source else None
            if label=='profile2': lock['android']['profile']['id']='mixer.android-source-pair.2';code='android.sdk-profile-mismatch';text='profile-mismatch'
            elif label=='stale-candidate4-profile':
                previous=load(ROOT/'verification/android-private-owner-integration-implementation/candidate-4/profile-proposal.json')
                lock['android']['profile']=self.driver.profile_lock(previous);code='android.sdk-profile-mismatch';text='profile-mismatch'
            elif label=='missing-lock': del lock['android'];code='android.sdk-profile-required';text='profile-required'
            else:
                if action=='same-size': source.write_bytes(bytes([before[0]^1])+before[1:])
                elif action=='remove':source.unlink()
                else:source.rename(renamed)
                lock['android']['adapterDigest']=self.driver.source_tree(fixture/'Generated/MixerAndroid')
                code='android.sdk-compatibility';text='source compatibility rejected'
            save(fixture/'mixer.lock',lock)
            binding=files(fixture);save(BASE/'mutation-bindings'/(label+'.json'),binding)
            try:
                # Guard against a refusal accidentally emitted after generic hashing/tools/output.
                with mock.patch.object(self.driver,'source_tree',side_effect=RuntimeError('GENERIC-HASH-TOO-EARLY')), \
                     mock.patch.object(self.driver,'inspect',side_effect=RuntimeError('TOOLS-TOO-EARLY')), \
                     mock.patch.object(self.driver,'checked_output',side_effect=RuntimeError('OUTPUT-TOO-EARLY')):
                    try:self.driver.build(fixture)
                    except RuntimeError as error:check(text in str(error),'preaccess refusal '+label)
                    else:raise RuntimeError('unrefused direct build')
                for config,platform in [('debug','android'),('release','host'),('debug','ios')]:
                    out,_=self.run(label+'-'+config+'-'+platform,[self.clis[config],'build','--directory',fixture,'--platform',platform],env=env,expected=1,timeout=20,binding=ident((BASE/'mutation-bindings'/(label+'.json')).read_bytes()))
                    check(json.loads(out)['code']==code,'CLI exact refusal '+label)
                forbidden=BASE/('forbidden-'+label)
                out,_=self.run(label+'-release-export',[self.clis['release'],'export',forbidden,'--directory',fixture],env=env,expected=1,timeout=20)
                check(json.loads(out)['code']==code and not forbidden.exists(),'pre-output export refusal')
                for mode,flags in [('normal',[]),('optimized',['-O'])]:
                    _,err=self.run(label+'-python-'+mode,[sys.executable,'-B',*flags,fixture/'Generated/MixerAndroid/android-build.py','build',fixture],env=env,expected=1,timeout=20)
                    check(text in err.decode(),'actual driver refusal')
                check(files(fixture)==binding,'refusal changed fixture or silently upgraded lock')
                check(not marker.exists() and not (fixture/'.mixer').exists(),'unexpected tools/output')
                report.append({'case':label,'generic_adapter_hash_recomputed':filename is not None,'expected_code':code,
                               'actual_commands':6,'direct_preaccess_trap':True,'tool_output_absent':True})
            finally:
                if source:
                    renamed.unlink(missing_ok=True);source.write_bytes(before)
                save(fixture/'mixer.lock',old)
        save(BASE/'mutation-results.json',{'fixtures':report,'actual_refusal_commands':54,
            'configuration_platform_scope':'Debug Android and iOS; Release host and export; direct Python normal and optimized',
            'not_exhaustive':'does not repeat every platform in both CLI configurations'})
        self.receipt.update(independent_refusal_commands=54,independent_mutation_fixtures=9,independent_preaccess_traps=9)

    def finish(self):
        products={};removed=[]
        for folder in self.scratch:
            if folder.exists():
                for path in folder.rglob('*'):
                    if path.is_file() and not path.is_symlink() and (path.name=='mixer' or path.suffix in ('.dylib','.so','.xctest') or any(p.endswith('.xctest') for p in path.parts)):
                        products[str(path.relative_to(BASE))]=ident(path.read_bytes())
                shutil.rmtree(folder);removed.append(str(folder.relative_to(BASE)))
        save(BASE/'products-before-cleanup.json',products)
        for label,cli in getattr(self,'clis',{}).items():
            key=str(cli.relative_to(BASE))
            executed=[c for c in self.commands if c['argv'][0]==str(cli)]
            for command in executed:
                check({k:command['executable'][k] for k in ('bytes','sha256')}==products[key],'review product command identity')
        self.receipt['cleanup']={'removed_owned_scratch':removed,'compiled_products_hashed':len(products),
                                  'children_reaped':all(c['child_reaped'] for c in self.commands),
                                  'signaled_groups':[c['pgid'] for c in self.commands if c['own_group_signaled']],
                                  'native_instances_started':False,'process_inventory_performed':False}
        self.receipt['commands']=len(self.commands)
        self.receipt['pending']=['Native owner/source/barrier/legacy acceptance belongs to other reviewer and root',
            'Native Android runtime, physical phone matrix, capture and UI tests paused',
            'No native compilation or APK claimed by this independent review',
            'Public V2 routing, immutable published FieldLog consumption, signing/store/operations/GA remain open']
        save(BASE/'receipt.json',self.receipt)

    def main(self):
        try:
            self.audit();self.snapshot();self.build();self.consumers();self.mutations()
            for name,value in self.selected.items():check(ident((self.source/name).read_bytes())==value,'isolated source drift')
            for name,value in self.original_source.items():check(ident((PACKET/'source'/name).read_bytes())==value,'producer source drift')
            for name,value in self.canonical.items():check(ident((ROOT/name).read_bytes())==value,'canonical final drift')
            for name,sha in self.external_pins.items():check(ident((ROOT/name).read_bytes())['sha256']==sha,'external pin final drift')
            self.receipt.update(status='passed-independent-profile3-host-review-awaiting-root',
                                independent_Swift_methods=3,producer_and_canonical_sources_unchanged=True)
        except BaseException as error:
            self.receipt['failure']={'type':type(error).__name__,'message':str(error)}
            raise
        finally:self.finish()

if __name__=='__main__':Review().main()
