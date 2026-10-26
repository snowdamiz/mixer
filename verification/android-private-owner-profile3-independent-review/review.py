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
PACKET = ROOT / 'verification/android-private-owner-profile3-integration/candidate4-qualification'
CANDIDATE = ROOT / 'verification/android-private-owner-integration-implementation/candidate-4'
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
                        'scope': 'independent exact candidate4 profile3 CLI host admission and copied app semantics only',
                        'native_runtime_UI_capture_process_inventory': False, 'GA_qualified': False,
                        'native_owner_accepted': False, 'pid': os.getpid(), 'pgid': os.getpgrp(),
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
            p = subprocess.Popen(argv, cwd=cwd, env=env or self.env, stdout=out, stderr=err, start_new_session=True)
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
        check(not timed_out and not oversized and p.returncode == expected, label + ' command failed')
        return stdout, stderr

    def audit(self):
        pins = {'manifest.json': 'ff947ccf16b055e10e3458bd9b8161b597b7744131c5eb8d7f67377736c134a6',
                'seal-receipt.json': 'a86a971a8be3d62b5c5ae8a03cc0aee6192941d6c138d26b39d1f390dc417251'}
        for name, sha in pins.items():
            check(ident((PACKET/name).read_bytes())['sha256'] == sha, 'producer seal pin ' + name)
        manifest = load(PACKET/'manifest.json')
        for name, value in manifest['files'].items():
            check(ident((PACKET/name).read_bytes()) == value, 'producer member ' + name)
        check(len(manifest['files']) == 1011 and sum(x['bytes'] for x in manifest['files'].values()) == 6659386, 'producer totals')
        actual = set(files(PACKET)); declared = set(manifest['files'])
        check(actual == declared | {'manifest.json', 'seal-receipt.json'}, 'producer closed inventory')
        check(ident((CANDIDATE/'profile-proposal.json').read_bytes())['sha256'] == 'fa20572d64d0cec8e2bbfd959df6a2993b4e231cca6f3f8009761bd0b2678d62', 'selected profile')
        self.profile = load(CANDIDATE/'profile-proposal.json')
        swift = (PACKET/'source/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
        literal = swift.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0]
        check(json.loads(literal) == self.profile, 'Swift profile exact equality')
        for kind in ('adapter', 'sdk'):
            check(len(self.profile[kind+'_files']) == 22, 'profile inventory')
            check(project(self.profile[kind+'_files']) == self.profile[kind+'_compatibility_sha256'], 'projection')
        source = load(PACKET/'source-binding.json')
        check(len(source['files']) == 356 and project(source['files']) == source['projection_sha256'], 'producer source binding')
        for name, value in source['files'].items():
            check(ident((PACKET/'source'/name).read_bytes()) == value, 'sealed source ' + name)
        canonical = load(CANDIDATE/'source-map.json')
        check(len(canonical) == 309, 'canonical count')
        for name, value in canonical.items():
            check(ident((ROOT/name).read_bytes()) == value, 'canonical drift ' + name)
        self.canonical = canonical
        self.original_source = source['files']
        producer_commands = load(PACKET/'commands.json')
        binding_hash = ident((PACKET/'source-binding.json').read_bytes())['sha256']
        unbound = []; all_bound = []; consumer_bound = []; missing_exe = []
        products = load(PACKET/'compiled-products-before-cleanup.json')
        disposition = load(PACKET/'binary-identity-disposition.json')
        for command in producer_commands:
            label = command['label']; cp = PACKET/'commands'/label
            check(load(cp/'result.json') == command, 'aggregate command binding ' + label)
            check(ident((cp/'stdout').read_bytes()) == command['stdout'] and ident((cp/'stderr').read_bytes()) == command['stderr'], 'producer output binding ' + label)
            check(command['exit'] == command['expected_exit'] and not command['timed_out'], 'producer command disposition ' + label)
            if command.get('source_binding_sha256') == binding_hash:
                all_bound.append(label)
            else:
                unbound.append(label)
            if command['argv'][0].endswith('/mixer'):
                group = 'cli-debug' if 'build-cli-debug/' in command['argv'][0] else 'cli-release'
                key = str(Path(command['argv'][0]).relative_to(PACKET))
                observed = {k: command['executable'][k] for k in ('bytes', 'sha256')}
                if label in disposition['dispositions'][group]['actual_consumer_and_refusal_commands']:
                    check(observed == products[key] == disposition['dispositions'][group]['final_after_Swift_test'], 'actual producer binary ' + label)
                    consumer_bound.append(label)
                else:
                    missing_exe.append({'label': label, 'scope': 'pre-test version command bound to initial identity, not final relinked product'})
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
        save(BASE/'producer-audit.json', {'pins': pins, 'packet_members_verified': 1011, 'packet_bytes_verified': 6659386,
            'producer_source_members_verified': 356, 'canonical_members_verified': 309, 'exact_profile': ident((CANDIDATE/'profile-proposal.json').read_bytes()),
            'commands_verified': len(producer_commands), 'source_bound_commands': all_bound, 'source_unbound_commands': unbound,
            'actual_consumer_refusal_binary_bound_commands': consumer_bound, 'other_CLI_identity_dispositions': missing_exe,
            'Swift_methods_not_parameterized_cases': method_counts, 'Python_methods_not_inner_cases': counts,
            'first_seal_failure': load(PACKET/'seal-attempt-1-disposition.json'), 'release_relink': disposition['dispositions']['cli-release'],
            'scope_limit': 'source hash fields bind source snapshot, not compiler dependency traces; command receipts do not claim immutable sandbox attestation'})
        self.receipt['producer_audit'] = {'members': 1011, 'bytes': 6659386, 'commands': len(producer_commands),
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
        cases=[('profile2',None,None),('missing-lock',None,None)]
        cases += [(file[:-5]+'-'+action,file,action) for file in ('NativeOwnerV2.java','OwnerLifecycleV2.java') for action in ('same-size','remove','rename')]
        for label,filename,action in cases:
            lock=json.loads(json.dumps(old));source=fixture/'Generated/MixerAndroid/app/src/dev/mixer/android'/filename if filename else None
            before=source.read_bytes() if source else None; renamed=source.with_suffix('.review-renamed') if source else None
            if label=='profile2': lock['android']['profile']['id']='mixer.android-source-pair.2';code='android.sdk-profile-mismatch';text='profile-mismatch'
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
                check(not marker.exists() and not (fixture/'.mixer').exists(),'unexpected tools/output')
                report.append({'case':label,'generic_adapter_hash_recomputed':filename is not None,'expected_code':code,
                               'actual_commands':6,'direct_preaccess_trap':True,'tool_output_absent':True})
            finally:
                if source:
                    renamed.unlink(missing_ok=True);source.write_bytes(before)
                save(fixture/'mixer.lock',old)
        save(BASE/'mutation-results.json',{'fixtures':report,'actual_refusal_commands':48,
            'configuration_platform_scope':'Debug Android and iOS; Release host and export; direct Python normal and optimized',
            'not_exhaustive':'does not repeat every platform in both CLI configurations'})
        self.receipt.update(independent_refusal_commands=48,independent_mutation_fixtures=8,independent_preaccess_traps=8)

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
            self.receipt.update(status='passed-independent-profile3-host-review-awaiting-root',
                                independent_Swift_methods=3,producer_and_canonical_sources_unchanged=True)
        except BaseException as error:
            self.receipt['failure']={'type':type(error).__name__,'message':str(error)}
            raise
        finally:self.finish()

if __name__=='__main__':Review().main()
