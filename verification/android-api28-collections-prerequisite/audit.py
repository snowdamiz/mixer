#!/usr/bin/env python3
"""Recheck frozen emitted evidence and exact library contracts; source-only, never Android execution."""
from pathlib import Path
import datetime, hashlib, json, re, sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
import run as producer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def check(value,message):
    if not value: raise AssertionError(message)
def validate(audit,types):
    check(bool(audit),'empty member audit')
    check(all(row['official_sdk'] is not None and row['official_sdk']['api'] <= 28 for row in audit),'post28 or unknown Java member')
    check(not any(x.startswith('java/util/stream/') for x in types),'unexpected streams')
    check('java/lang/Record' not in types,'unlowered Record superclass')

def main():
    source_map = json.loads((HERE/'source-map.json').read_text())
    profile = json.loads((HERE/'inputs'/producer.PROFILE).read_text())
    check(len(profile['adapter_files']) == 23,'adapter23 projection')
    index = []
    for path,row in source_map.items():
        snapshot = ROOT/row['snapshot']
        check(producer.identity(snapshot) == {k:row[k] for k in ('bytes','sha256')},'snapshot changed '+path)
        if not path.endswith('.java'): continue
        check(producer.identity(ROOT/path) == {k:row[k] for k in ('bytes','sha256')},'current Java changed '+path)
        for line,text in enumerate(snapshot.read_text().splitlines(),1):
            for match in re.finditer(r'\b(List|Set|Map)\.(of|copyOf|ofEntries|entry)\s*\(',text):
                index.append({'path':path,'line':line,'symbol':match.group(1)+'.'+match.group(2),'snippet':text.strip()})
    write('source-factory-index.json',index)
    audits = json.loads((HERE/'attempt-1/dex-java-api-audit.json').read_text())
    refs = producer.dex_refs(HERE/'attempt-1/actual20.classes.dex')
    validate(audits,refs['types'])
    # Recompute independently of cached summary; resolve real DEX IDs against frozen official metadata.
    excerpt=ET.parse(HERE/'official-sdk-api-excerpt.xml').getroot()
    # The first producer excerpt omitted some inherited declaration owners. Retain that failed
    # audit diagnosis separately, then complete the finite metadata ancestry from the exact SDK.
    provenance=json.loads((HERE/'tool-provenance.json').read_text())
    check(producer.identity(producer.APIS)==provenance[str(producer.APIS.resolve())],'official API database changed')
    full={c.get('name'):c for c in ET.parse(producer.APIS).getroot().findall('class')}
    retained={c.get('name'):c for c in excerpt.findall('class')}
    def ancestors(name):
        node=full.get(name)
        if node is None: return
        for tag in ('extends','implements'):
            for parent in node.findall(tag):
                value=parent.get('name')
                if value not in retained and value in full: retained[value]=full[value]; ancestors(value)
    for name in list(retained): ancestors(name)
    completed=ET.Element('api-excerpt',excerpt.attrib)
    for name in sorted(retained): completed.append(retained[name])
    ET.indent(completed)
    (HERE/'official-sdk-api-excerpt.xml').write_text(ET.tostring(completed,encoding='unicode')+'\n')
    api_classes=retained
    for row in audits:
        check(producer.api_lookup(api_classes,row['owner'],row['name'],row['kind']) == row['official_sdk'],'official floor mismatch')
    controls = []
    for name,bad_rows,bad_types in [
        ('post28 Java method',audits+[{'official_sdk':{'api':31}}],refs['types']),
        ('unknown Java member',audits+[{'official_sdk':None}],refs['types']),
        ('stream dependency',audits,refs['types']+['java/util/stream/Stream']),
        ('unlowered record type',audits,refs['types']+['java/lang/Record'])]:
        try: validate(bad_rows,bad_types)
        except AssertionError: controls.append({'name':name,'rejected':True})
        else: raise AssertionError('control accepted: '+name)
    # dexdump preserves DEX modified-UTF8 literals, including surrogate encodings.
    # Instruction/member names are ASCII; preserve original bytes and replace only for text indexing.
    lines = (HERE/'attempt-1/dexdump.stdout').read_text(errors='replace').splitlines()
    methods = {}
    current = None
    for number,line in enumerate(lines,1):
        match = re.search(r'\|\[[0-9a-f]+\] (.+:\(.*)$',line)
        if match:
            current=match.group(1); methods[current]={'line':number,'code':[],'invokes':[],'fields':[]}
        elif current and re.match(r'^[0-9a-f]+:.*\|[0-9a-f]+:',line):
            methods[current]['code'].append(line)
            invoke=re.search(r'invoke-\S+.*?, L([^;]+);\.([^:]+):(\S+)',line)
            if invoke: methods[current]['invokes'].append({'owner':invoke.group(1),'name':invoke.group(2),'descriptor':invoke.group(3),'line':number})
            field=re.search(r'(?:sget|iget)\S*.*?, L([^;]+);\.([^:]+):(\S+)',line)
            if field: methods[current]['fields'].append({'owner':field.group(1),'name':field.group(2),'type':field.group(3),'line':number})
    helper_names = [
        'dev.mixer.android.AppearanceDescriptorV2$0.m:(Ljava/util/Collection;)Ljava/util/List;',
        'dev.mixer.android.AppearanceDescriptorV2$1.m:([Ljava/lang/Object;)Ljava/util/List;',
        'dev.mixer.android.AppearanceDescriptorV2$2.m:(Ljava/lang/Object;Ljava/lang/Object;Ljava/lang/Object;)Ljava/util/List;',
        'dev.mixer.android.AppearanceDescriptorV2$3.m:(Ljava/lang/Object;Ljava/lang/Object;)Ljava/util/List;',
        'dev.mixer.android.AppearanceGeometryV2$0.m:(Ljava/lang/Object;)Ljava/util/List;',
        'dev.mixer.android.AppearanceResolverV2$Plan$0.m:(Ljava/util/Map;)Ljava/util/Map;',
        'dev.mixer.android.OwnerLifecycleV2.batch:(Ljava/util/List;)Ljava/util/List;',
        'dev.mixer.android.NativeAppearanceViewsV2$Group.<init>:(Landroid/content/Context;Ldev/mixer/android/NativeAppearanceViewsV2$Record;)V']
    selected = {key:methods[key] for key in helper_names}
    check('Collection;.iterator:' in '\n'.join(selected[helper_names[0]]['code']),'copy traversal')
    check('Collections;.unmodifiableList:' in '\n'.join(selected[helper_names[0]]['code']),'owned list wrapper')
    check('Objects;.requireNonNull:' in '\n'.join(selected[helper_names[0]]['code']),'copy null refusal')
    check('Collections;.unmodifiableMap:' in '\n'.join(selected[helper_names[5]]['code']),'owned map wrapper')
    check('Collections;.EMPTY_MAP:' in '\n'.join(selected[helper_names[7]]['code']),'empty map lowering')
    calls = []
    for owner,body in methods.items():
        for call in body['invokes']:
            target=call['owner'].replace('/','.')+'.'+call['name']+':'+call['descriptor']
            if target in selected: calls.append({'caller':owner,'target':target,'line':call['line']})
        for field in body['fields']:
            if field['owner']=='java/util/Collections' and field['name'] in ('EMPTY_LIST','EMPTY_MAP'):
                calls.append({'caller':owner,'target':'java/util/Collections.'+field['name'],'line':field['line']})
    check(any(row['caller'].startswith('dev.mixer.android.OwnerLifecycleV2.batch:') and row['target']==helper_names[0] for row in calls),'core snapshot routing')
    write('attempt-1/collection-lowering.json',{'helpers_and_boundary_bodies':selected,'call_edges':calls,
        'warning':'DEX disassembly/source evidence only. Synthetic bodies are official compiler output, not product-authored source or Android execution.'})
    floors = []
    for name in refs['types']:
        c=api_classes.get(name); check(c is not None,'unresolved Java type '+name)
        since=int(c.get('since','1'));check(since<=28,'new Java type '+name)
        floors.append({'type':name,'api':since})
    write('attempt-1/java-type-api-audit.json',floors)
    jar=producer.SDK/'build-tools/37.0.0/lib/d8.jar'
    write('attempt-1/d8-implementation-identity.json',{'path':str(jar),'identity':producer.identity(jar),
        'source':'official installed Android build-tools37.0.0; frozen driver tree() hashes every distribution file, including this jar',
        'not_a_global_toolchain_allowlist':True})
    # Copy only the already sealed producer driver, never a live CLI source, and verify exact data identity.
    frozen_driver=ROOT/'verification/android-environment-platform-profile4/source/cli/Sources/MixerBuild/Resources/android-build.py'
    driver_map=json.loads((ROOT/'verification/android-environment-platform-profile4/source-map.json').read_text())
    check(producer.identity(frozen_driver)==driver_map['cli/Sources/MixerBuild/Resources/android-build.py'],'frozen driver custody')
    copied=HERE/'inputs/frozen-profile4-android-build.py'; copied.write_bytes(frozen_driver.read_bytes())
    driver=copied.read_text()
    check("run([BT / 'd8', '--min-api', '28', '--lib', JAR, '--output', dex" in driver,'consumer D8 flags')
    check("'android_build_tools': {'path': str(BT), 'sha256': tree(BT)}" in driver,'distribution jar covered')
    check("if identity != android['toolchain']:" in driver,'exact local lock equality')
    write('consumer-build-contract.json',{'frozen_driver':str(copied.relative_to(ROOT)),'identity':producer.identity(copied),
        'same_D8_flags':True,'build_tools37_path':True,'distribution_tree_includes_d8_jar':True,
        'exact_toolchain_compared_to_lock_before_compilation':True,
        'remaining_limits':['Generated builder does not audit emitted library member API floors.',
            'Source profile identity alone does not identify D8; local toolchain lock supplies the distribution identity.',
            'Version metadata alone is not a globally approved D8 binary allowlist.',
            'This finite test clears implicit JVM option variables; frozen builder inherits them. Reproduction assumes no JVM injection/options changing compilation.',
            'Additional generated/application Java source, changed compilers or D8 flags require a fresh emitted closure audit.'],
        'live_CLI_read_or_executed':False})
    oracle=(HERE/'attempt-1/host-oracle.stdout').read_text().strip()
    oracle_count=re.fullmatch(r'PASS (\d+) host assertions; UNSELECTED prototype; no Android execution',oracle)
    check(oracle_count is not None,'host oracle output')
    write('audit-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,
        'python':sys.version,'source_factory_calls':len(index),'audited_Java_members':len(audits),'audited_Java_types':len(floors),
        'post28_or_unknown_java_members':0,'source_Java_files_unchanged':20,'adapter_Java_members':17,'adapter_total_members':23,
        'controls':controls,'D8_helper_call_edges':len(calls),'host_oracle_assertions':int(oracle_count.group(1)),
        'scope':'source/compiler proof only; no native runtime, no product/profile selection','owned_scratch_or_children':False})
    print(json.dumps({'status':'passed-finite-audit','factory_calls':len(index),'members':len(audits),'types':len(floors),'edges':len(calls)}))

if __name__=='__main__': main()
