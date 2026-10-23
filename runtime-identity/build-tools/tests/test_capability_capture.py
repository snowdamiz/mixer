"""Original v2 public-CLI/copied-byte/closed-material tests; no adapter execution."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS)); import capability_capture as c; import capture as legacy; sys.path.pop(0)
sys.path.insert(0,str(ROOT/'runtime-identity/tools')); import vectors_v2 as vectors; sys.path.pop(0)
spec = importlib.util.spec_from_file_location('embed_v2',TOOLS/'embed-v2.py')
emitter = importlib.util.module_from_spec(spec);spec.loader.exec_module(emitter)

class CapabilityCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.swift = os.environ.get('MIXER_SWIFT','swift')
        configured = os.environ.get('MIXER_IDENTITY_TOOL')
        binary = subprocess.check_output([cls.swift,'build','--package-path',str(ROOT/'runtime-identity'),'--show-bin-path'],text=True).strip()
        cls.tool = Path(configured).absolute() if configured else Path(binary)/'mixer-identity'
        if not cls.tool.is_file(): raise RuntimeError('Build actual mixer-identity before tests')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-identity2-'); self.root = Path(self.temporary.name)
        self.inputs = self.root/'inputs'; self.inputs.mkdir()
        self.descriptor = vectors.descriptor()
        self.descriptor['capabilities'] = [vectors.capability(x) for x in sorted(vectors.SCHEMAS)]
        self.descriptor['execution']['startup_export'] = '\U0001f680"); fatalError("injection") //'
        self.descriptor_path = self.root/'descriptor.json';self.descriptor_path.write_bytes(c.canonical(self.descriptor))
        self.bindings = {'schema':1,'bindings':[]}
        schema = json.loads((ROOT/'capabilities/schema/v1.json').read_bytes())
        preimages = {
            '/engine/ui_contract_sha256': (ROOT/'contracts/ui-v1.json').read_bytes(),
            '/engine/capability_contract_sha256': c.canonical(schema)[:-1],
            '/capability_execution/contract_sha256': (ROOT/'contracts/capability-execution-v1.json').read_bytes(),
            '/capability_execution/transport_sha256': (ROOT/'contracts/guest-capability-transport-v1.json').read_bytes(),
            '/capability_execution/native_header_sha256': (ROOT/'vm/include/mixer_vm_capability.h').read_bytes(),
            '/capability_execution/bridge_policy_sha256': c.canonical({'schema':1,'burst':8,'starts_per_second':32}),
        }
        for index,cap in enumerate(self.descriptor['capabilities']):
            prefix=f'/capabilities/{index}/';http=cap['id']=='network.http.v1'
            item=next(x for x in schema['capabilities'] if x['id']==cap['id'])
            preimages[prefix+'schema_sha256']=c.canonical({'wire':{k:v for k,v in schema.items() if k not in ['capabilities','types']},'capability':item,'types':schema['types']})[:-1]
            preimages[prefix+'native_sha256']=b'Original synthetic native build input for '+cap['id'].encode()
            config={'schema':1,'implementation':'urlsession-normal-tls-v1','maximum_concurrent_requests':8} if http else {'schema':1,'implementation':'app-private-kv-v1','container':'application-private','directory_component':'fieldlog','maximum_total_bytes':4194304,'maximum_entries':1024}
            preimages[prefix+'configuration_sha256']=c.canonical(config)
            preimages[prefix+'grants_sha256']=c.canonical({'capability_id':cap['id'],'schema_sha256':cap['schema_sha256'],'permissions':['network.https' if http else 'storage.appPrivate'],'origins':['https://example.test'] if http else [],'methods':['GET'] if http else [],'namespaces':[] if http else ['notes']})
        self.paths={}
        for index,pointer in enumerate(sorted(c.digest_paths(self.descriptor))):
            name=f'input-{index}.bin';self.paths[pointer]=self.inputs/name
            self.paths[pointer].write_bytes(preimages.get(pointer,b'Original synthetic identity input\x00\xff'))
            self.bindings['bindings'].append({'pointer':pointer,'kind':'file','files':[{'name':name,'path':name}]})
        self.bindings_path=self.root/'bindings.json'

    def tearDown(self): self.temporary.cleanup()
    def create(self,name='snapshot'):
        self.bindings_path.write_bytes(c.canonical(self.bindings))
        return c.capture(self.descriptor_path,self.bindings_path,self.inputs,self.root/name,self.tool)
    def verify(self,result,name='snapshot'): return c.verify(self.root/name,result['fingerprint'],self.tool)
    def change(self,pointer,value): self.paths[pointer].write_bytes(c.canonical(value))

    def test_raw_preimages_roles_relocation_and_mutation(self):
        a=self.create();self.assertEqual(self.verify(a)['fingerprint'],a['fingerprint'])
        b=self.create('two');self.assertEqual(a,b)
        descriptor=json.loads((self.root/'snapshot/descriptor.json').read_bytes())
        for index in range(2):
            raw=self.paths[f'/capabilities/{index}/native_sha256'].read_bytes()
            self.assertEqual(descriptor['capabilities'][index]['native_sha256'],c.sha(raw))
            self.assertNotEqual(raw.decode(),descriptor['capabilities'][index]['native_sha256'])
        self.paths['/engine/artifact_sha256'].write_bytes(b'changed')
        self.verify(a);self.assertNotEqual(self.create('three')['fingerprint'],a['fingerprint'])
        report=json.loads((self.root/'snapshot/inputs.json').read_bytes())
        self.assertEqual((report['schema'],report['identity_schema']),(2,2))
        self.assertFalse(report['build_attested']);self.assertFalse(report['complete_graph_proven'])

    def test_old_and_new_public_modes_reject_each_other(self):
        result=self.create()
        with self.assertRaises(legacy.CaptureError): legacy.verify(self.root/'snapshot',result['fingerprint'],self.tool)
        old=ROOT/'activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json'
        for mode,path in [('inspect',self.root/'snapshot/descriptor.json'),('inspect-v2',old)]:
            run=subprocess.run([str(self.tool),mode,str(path)],capture_output=True,timeout=30)
            self.assertEqual(run.returncode,1);self.assertEqual(run.stdout,b'')
        with self.assertRaises(c.CaptureError): c.capture(old,self.bindings_path,self.inputs,self.root/'wrong',self.tool)
        self.assertFalse((self.root/'wrong').exists())

    def test_fixed_contract_header_schema_preimages_fail_closed(self):
        for index,pointer in enumerate(['/capability_execution/native_header_sha256','/capability_execution/contract_sha256','/engine/capability_contract_sha256','/capabilities/0/schema_sha256']):
            original=self.paths[pointer].read_bytes();self.paths[pointer].write_bytes(original+b'\n')
            with self.subTest(pointer=pointer),self.assertRaises(c.CaptureError):self.create('bad'+str(index))
            self.assertFalse((self.root/('bad'+str(index))).exists());self.paths[pointer].write_bytes(original)

    def test_raw_roles_reject_collections_and_empty_native(self):
        for index,pointer in enumerate(['/capability_execution/native_header_sha256','/capabilities/0/native_sha256','/capabilities/1/configuration_sha256','/capability_execution/bridge_policy_sha256']):
            binding=next(x for x in self.bindings['bindings'] if x['pointer']==pointer);binding['kind']='collection'
            with self.subTest(pointer=pointer),self.assertRaises(c.CaptureError): self.create('bad'+str(index))
            binding['kind']='file'
        self.paths['/capabilities/0/native_sha256'].write_bytes(b'')
        with self.assertRaises(c.CaptureError):self.create('empty')

    def test_material_canonical_closed_and_family_rules(self):
        pointer='/capability_execution/bridge_policy_sha256';original=self.paths[pointer].read_bytes()
        variants=[b' '+original,original+b'\n',b'{"schema":1,"burst":8,"burst":8,"starts_per_second":32}\n',b'{"burst":8,"schema":true,"starts_per_second":32}\n',c.canonical({'schema':1,'burst':9,'starts_per_second':32}),c.canonical({'schema':1,'burst':8,'starts_per_second':0}),c.canonical({'schema':1,'burst':8,'starts_per_second':32,'extra':0}), b'{"burst":8,"schema":1,"starts_per_second":'+b'1'*5000+b'}\n']
        for index,raw in enumerate(variants):
            self.paths[pointer].write_bytes(raw)
            with self.subTest(index=index),self.assertRaises(c.CaptureError):self.create('bad'+str(index))
            self.assertFalse((self.root/('bad'+str(index))).exists())
        self.paths[pointer].write_bytes(original)
        hp='/capabilities/0/configuration_sha256';config=json.loads(self.paths[hp].read_bytes());config['maximum_concurrent_requests']=7;self.change(hp,config)
        with self.assertRaises(c.CaptureError):self.create('concurrency')
        config['maximum_concurrent_requests']=8;self.change(hp,config)
        gp='/capabilities/0/grants_sha256';grant=json.loads(self.paths[gp].read_bytes())
        for index,changed in enumerate([dict(grant,capability_id='storage.keyValue.v1'),dict(grant,origins=['https://EXAMPLE.test']),dict(grant,origins=['https://example.test:443']),dict(grant,namespaces=['no']),dict(grant,methods=['GET','GET'])]):
            self.change(gp,changed)
            with self.subTest(index=index),self.assertRaises(c.CaptureError):self.create('grant'+str(index))
        self.change(gp,grant)
        sp='/capabilities/1/configuration_sha256';storage=json.loads(self.paths[sp].read_bytes());storage['directory_component']='../escape';self.change(sp,storage)
        with self.assertRaises(c.CaptureError):self.create('path')

    def test_material_exact_bounds_structure_and_empty_denials(self):
        raw=self.paths['/capability_execution/bridge_policy_sha256'].read_bytes()
        with patch.object(c,'MAX_MATERIAL_FILE',len(raw)):self.assertEqual(c.material(raw)['schema'],1)
        with patch.object(c,'MAX_MATERIAL_FILE',len(raw)-1),self.assertRaises(c.CaptureError):c.material(raw)
        for value in [dict(x=None),dict(x=-1),dict(x=1.0),dict(x=[[[[[[[[[]]]]]]]]]),dict(x=list(range(8192)))]:
            with self.assertRaises(c.CaptureError):c.material(c.canonical(value))
        gp='/capabilities/1/grants_sha256';grant=json.loads(self.paths[gp].read_bytes());grant.update(permissions=[],namespaces=[]);self.change(gp,grant)
        self.verify(self.create()) # Empty installed namespace denies; no adapter constructed.
        count=sum(len(self.paths[p].read_bytes()) for p in self.paths if p.endswith(('configuration_sha256','grants_sha256','bridge_policy_sha256')))
        with patch.object(c,'MAX_MATERIAL_TOTAL',count):self.create('exact')
        with patch.object(c,'MAX_MATERIAL_TOTAL',count-1),self.assertRaises(c.CaptureError):self.create('large')

    def test_partial_sync_and_existing_outputs_are_atomic(self):
        with patch.object(c,'sync_directory',side_effect=OSError('original injected sync failure')):
            with self.assertRaises(OSError):self.create('partial')
        self.assertFalse((self.root/'partial').exists())
        self.create();(self.root/'snapshot/keep').write_bytes(b'keep')
        with self.assertRaises(FileExistsError):self.create()
        self.assertEqual((self.root/'snapshot/keep').read_bytes(),b'keep')

    def test_source_swap_symlinks_and_snapshot_corruption(self):
        p=self.paths['/capability_execution/bridge_policy_sha256'];original=p.read_bytes();p.unlink();p.symlink_to(self.inputs/'missing')
        with self.assertRaises(OSError):self.create('symlink')
        p.unlink();p.write_bytes(original);result=self.create()
        descriptor=json.loads((self.root/'snapshot/descriptor.json').read_bytes());digest=descriptor['capability_execution']['bridge_policy_sha256'];obj=self.root/'snapshot/objects'/digest
        obj.chmod(0o600);obj.write_bytes(b'corrupt')
        with self.assertRaises(c.CaptureError):self.verify(result)

    def test_mutating_open_input_fails_atomically_and_external_file_stays_safe(self):
        target=self.paths['/capability_execution/bridge_policy_sha256'];inode=target.stat().st_ino;original=legacy.os.read;changed=False
        def mutate(fd,amount):
            nonlocal changed
            data=original(fd,amount)
            if os.fstat(fd).st_ino==inode and not changed:
                changed=True;target.write_bytes(target.read_bytes()+b'changed during pinned read')
            return data
        with patch.object(legacy.os,'read',side_effect=mutate):
            with self.assertRaises(c.CaptureError):self.create('mutating')
        self.assertTrue(changed);self.assertFalse((self.root/'mutating').exists())
        outside=self.root/'outside';outside.write_bytes(b'external must survive');target.unlink();target.symlink_to(outside)
        with self.assertRaises(OSError):self.create('outside-link')
        self.assertEqual(outside.read_bytes(),b'external must survive')

    def test_role_coverage_and_completed_snapshot_metadata_tamper(self):
        original=copy.deepcopy(self.bindings)
        for index,changed in enumerate([{'schema':1,'bindings':original['bindings'][:-1]}, {'schema':1,'bindings':original['bindings']+[original['bindings'][0]]}]):
            self.bindings=changed
            with self.assertRaises(c.CaptureError):self.create('coverage'+str(index))
            self.assertFalse((self.root/('coverage'+str(index))).exists())
        self.bindings=original;result=self.create();path=self.root/'snapshot/inputs.json';report=json.loads(path.read_bytes());report['identity_schema']=1;path.chmod(0o600);path.write_bytes(c.canonical(report))
        with self.assertRaises(c.CaptureError):self.verify(result)

    def test_v2_cli_and_optimized_rejection(self):
        self.bindings_path.write_bytes(c.canonical(self.bindings))
        command=[sys.executable,str(TOOLS/'capture-v2.py'),'capture-v2','--descriptor',str(self.descriptor_path),'--bindings',str(self.bindings_path),'--input-root',str(self.inputs),'--identity-tool',str(self.tool),'--output',str(self.root/'cli')]
        run=subprocess.run(command,capture_output=True,timeout=60);self.assertEqual(run.returncode,0,run.stderr)
        run=subprocess.run([sys.executable,'-O',*command[1:]],capture_output=True,timeout=60);self.assertEqual(run.returncode,1);self.assertNotIn(b'Traceback',run.stderr)
        self.paths['/capability_execution/native_header_sha256'].write_bytes(b'wrong header')
        command[-1]=str(self.root/'wrong-header')
        run=subprocess.run([sys.executable,'-O',*command[1:]],capture_output=True,timeout=60);self.assertEqual(run.returncode,1);self.assertNotIn(b'Traceback',run.stderr);self.assertFalse((self.root/'wrong-header').exists())

    def test_v2_emitter_uses_verified_bytes_and_distinct_type(self):
        result=self.create();snapshot=self.root/'snapshot';output=self.root/'generated'
        before=(snapshot/'descriptor.json').read_bytes();original=c.verified_descriptor
        def swap(*args):
            checked=original(*args);path=snapshot/'descriptor.json';path.unlink();path.write_bytes(b'replaced after verification');return checked
        with patch.object(c,'verified_descriptor',swap):receipt=emitter.emit(snapshot,result['fingerprint'],self.tool,output)
        source=(output/'MixerInstalledCapabilityRuntime.swift').read_bytes()
        self.assertIn(b'CapabilityRuntimeIdentity(json:',source);self.assertNotIn(b'fatalError("injection")',source)
        self.assertEqual(receipt['descriptor_sha256'],c.sha(before));self.assertEqual(receipt['identity_schema'],2)
        self.assertFalse(receipt['compiled']);self.assertFalse(receipt['signed'])
        self.assertNotIn(str(self.root).encode(),source)

    def test_compiled_v2_consumer_without_snapshot_and_fingerprint_mismatch(self):
        result=self.create();output=self.root/'generated';emitter.emit(self.root/'snapshot',result['fingerprint'],self.tool,output)
        import shutil
        package=self.root/'consumer';sources=package/'Sources/Consumer';sources.mkdir(parents=True)
        (package/'Package.swift').write_text('// swift-tools-version: 6.2\nimport PackageDescription\nlet package = Package(name:"Identity2Consumer", platforms:[.macOS(.v14)], dependencies:[.package(path:'+json.dumps(str(ROOT/'runtime-identity'))+')], targets:[.executableTarget(name:"Consumer",dependencies:[.product(name:"MixerRuntimeIdentity",package:"runtime-identity")])])\n')
        source=sources/'MixerInstalledCapabilityRuntime.swift';shutil.copyfile(output/source.name,source)
        (sources/'main.swift').write_text('import Foundation\nimport MixerRuntimeIdentity\ndo { let value = try MixerInstalledCapabilityRuntime.load(); print(value.fingerprint); print(value.installedRuntime.protocolVersion); print(value.installedRuntime.guestABI); print(value.capabilityExecution.route); print(value.capabilities.count) } catch { FileHandle.standardError.write(Data(String(describing:error).utf8)); exit(3) }\n')
        shutil.rmtree(self.root/'snapshot');shutil.rmtree(self.inputs);self.descriptor_path.unlink()
        command=[self.swift,'run','--package-path',str(package),'Consumer']
        run=subprocess.run(command,capture_output=True,text=True,timeout=240);self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(run.stdout.splitlines(),[result['fingerprint'],'3','2','capability-guest-v1','2'])
        evidence={'command':command,'valid_stdout':run.stdout,'valid_stderr':run.stderr,'valid_exit':run.returncode,'valid_source_sha256':c.sha(source.read_bytes()),'package_sha256':c.sha((package/'Package.swift').read_bytes())}
        evidence_root=os.environ.get('MIXER_IDENTITY_V2_EVIDENCE')
        if evidence_root:
            directory=Path(evidence_root);directory.mkdir(parents=True,exist_ok=False)
            shutil.copyfile(source,directory/source.name);shutil.copyfile(sources/'main.swift',directory/'main.swift');shutil.copyfile(package/'Package.swift',directory/'Package.swift')
        source.chmod(0o600);source.write_text(source.read_text().replace('fingerprint = "'+result['fingerprint']+'"','fingerprint = "'+'0'*64+'"'))
        run=subprocess.run(command,capture_output=True,text=True,timeout=240);self.assertEqual(run.returncode,3);self.assertIn('fingerprintMismatch',run.stderr);self.assertEqual(run.stdout,'')
        if evidence_root:
            evidence.update(rejected_exit=run.returncode,rejected_stdout=run.stdout,rejected_stderr=run.stderr,rejected_source_sha256=c.sha(source.read_bytes()))
            shutil.copyfile(source,directory/'FingerprintMismatch.swift');(directory/'receipt.json').write_bytes(c.canonical(evidence))

if __name__=='__main__':unittest.main()
