#!/usr/bin/env python3
"""Derive host preparation utilities from the accepted V6 packet without execution."""
from pathlib import Path
import hashlib

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
OLD=ROOT/'verification/apple-settings-instrumented-runtime-preparation'

def one(raw,before,after):
    if raw.count(before)!=1:raise ValueError('Expected one bootstrap edit: '+before[:100])
    return raw.replace(before,after,1)

raw=(OLD/'prepare.py').read_text()
raw=one(raw,"PRIOR = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'","PRIOR = ROOT / 'verification/apple-settings-instrumented-runtime-preparation'")
raw=one(raw,"BUILD = ROOT / 'verification/apple-settings-instrumented-native-build'","BUILD = ROOT / 'verification/apple-settings-fixed-chunk-native-build'")
raw=one(raw,"BUILD_HANDOFF = '246f5e9486f804d2ab784ba474696bcf7905873aa5a1200117b570bd66933e91'","BUILD_HANDOFF = '3e6dc04dd9d2f314f3ccf5a9dc363e88c327936f2e9719b9365000f81859cc21'")
raw=one(raw,"PRIOR_PACKET = '6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc'","PRIOR_PACKET = 'f7ef1ed54b65a71e666646d1e4b54cef1cea5b7afdfee804810ffaf2c65eaeb6'")
acceptance=hashlib.sha256((ROOT/'verification/apple-settings-fixed-chunk-build-root-review/acceptance.json').read_bytes()).hexdigest()
raw=one(raw,"ACCEPTANCE = '9956f0384828da9cdd8082ca387716c439131f6a2f0c4fcde4065cc5c96995ff'",f"ACCEPTANCE = '{acceptance}'")
for before,after in [('c3e696b102d0a5daefa928e2941437739c5c418eb876dc31a65f0acef8e6e924','cca8472579ed6ce7c3c00babadb44d37ba34dc1a400ec00fc7802536342d7a2c'),('2b44b02dbd702becefa8b609435928890ad7c1a5f7cb11b3cc0fd1f5000ca101','0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb'),('696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a','2b44b02dbd702becefa8b609435928890ad7c1a5f7cb11b3cc0fd1f5000ca101'),('0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8','c3e696b102d0a5daefa928e2941437739c5c418eb876dc31a65f0acef8e6e924')]:
    raw=one(raw,before,after)
raw=one(raw,"OUTPUT_PREFIX = 'native-run-v6-'","OUTPUT_PREFIX = 'native-run-v7-'")
raw=one(raw,"SOURCES = ['prepare.py', 'run_controls.py', 'record_command.py', 'seal.py', 'local_first_failure.py']","SOURCES = ['prepare.py', 'run_controls.py', 'record_command.py', 'seal.py', 'local_first_failure.py', 'bootstrap.py']\nENDPOINT = ROOT / 'verification/apple-settings-fixed-chunk-implementation'\nRECEIVER = 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'\nREVIEW_ARCHIVE = '585f44532cb67ca626ae7c2c95bfa7030408bf2b4dc57f5bac0fdbd84cea66af'\nCOMPILE_ARCHIVE = '96cf2e6d4356035e004564a2a4d4e01122fb570835e4089c6c83788ab53465f8'\nPRODUCT_TREE = '58835bb84bfdf801a395a237c6ea6dfdd746ca005c9533736ec2ee5cf80fa4b8'")
start=raw.index('def references():')
end=raw.index('\ndef prior_payload():',start)
raw=raw[:start]+'''def references():
    """Bind accepted V6 composition, reviewed receiver and exact fresh build only."""
    bindings = {}
    def bind(path, expected=None):
        actual = row(path)
        require(expected is None or actual['sha256'] == expected, 'Accepted input identity differs: ' + str(path))
        bindings[str(path.relative_to(ROOT))] = actual
        return actual
    def sealed(path, digest, required_count=None):
        bind(path, digest)
        value = json.loads(path.read_bytes())
        if required_count is not None:
            require(len(value['members']) == required_count, 'Accepted sealed inventory differs')
        for name, expected in value['members'].items():
            safe_name(name)
            # Do not traverse a named but unselected lane through a handoff.
            require(not any(word in name.lower() for word in ('catalog-inspector', 'authority-driver', 'worker-transport')),
                    'Excluded handoff lane refused')
            actual = row(ROOT / name)
            require(set(expected) <= {'kind', 'mode', 'bytes', 'sha256'}
                    and all(actual[key] == item for key, item in expected.items()), 'Accepted sealed member changed: ' + name)
            bindings[name] = actual
        return value
    prior_seal = sealed(PRIOR / 'handoff.json', 'ca361bde1632c4ad4bbaf517817b9d8a5a9426a25d462738a9e03eeeb1786a3c', 61)
    require(prior_seal['packetSHA256'] == PRIOR_PACKET and prior_seal['nativeExecuted'] is False,
            'Accepted V6 preparation scope differs')
    bind(PRIOR / 'packet.json', PRIOR_PACKET)
    prior = json.loads((PRIOR / 'packet.json').read_bytes())
    require(prior['selectedFiles'] == 32, 'Accepted V6 runtime file count differs')
    for name in ['runtime-source-manifest.json', 'runtime-sources.tar.gz', 'adapter.py', 'importer.py', 'selection-template.json']:
        require(row(PRIOR / name) == prior['files'][name], 'Accepted V6 artifact differs: ' + name)
    review_root = ROOT / 'verification/apple-settings-instrumented-runtime-review'
    bind(review_root / 'handoff.json', 'dbfcd7c074acbe63b27bd26a94d77f72c494fa4fdc8b0f9b6792aa2d83da049f')
    accepted_review = json.loads((review_root / 'handoff.json').read_bytes())
    for name in ['verification/apple-settings-instrumented-runtime-review/review.json',
                 'docs/apple-settings-instrumented-runtime-review.md']:
        expected = accepted_review['members'][name]
        require(row(ROOT / name) == expected, 'Accepted V6 independent review differs')
        bindings[name] = expected
    decision = json.loads((review_root / 'review.json').read_bytes())
    require(decision['status'] == 'source-and-host-packaging-accepted' and decision['blockingFindings'] == []
            and decision['packetSHA256'] == PRIOR_PACKET and decision['nativeSelected'] is False,
            'Accepted V6 independent decision differs')
    bind(BUILD / 'handoff.json', BUILD_HANDOFF)
    build = sealed(BUILD / 'handoff.json', BUILD_HANDOFF, 42)
    require(build['nativeExecuted'] is False and build['nativeExecutionSelected'] is False
            and build['sourceFiles'] == 40 and build['products'] == 55
            and build['runnerProductFilesFresh'] == 42 and build['originalApplicationFilesUnchanged'] == 13
            and build['sourceTreeSHA256'] == SOURCE and build['productTreeSHA256'] == PRODUCT_TREE
            and build['sourceArchiveSHA256'] == COMPILE_ARCHIVE and build['productArchiveSHA256'] == PRODUCT
            and build['warningLines'] == 15 and build['allWarningMessagesMatchOriginalAndPrior'] is True,
            'Accepted fresh build scope differs')
    accept_path = ROOT / 'verification/apple-settings-fixed-chunk-build-root-review/acceptance.json'
    bind(accept_path, ACCEPTANCE)
    acceptance = json.loads(accept_path.read_bytes())
    require(acceptance['buildAccepted'] is True and acceptance['hostRuntimePreparationSelected'] is True
            and acceptance['nativeExecutionSelected'] is False and acceptance['handoffSHA256'] == BUILD_HANDOFF
            and acceptance['sourceRevision'] == 'be472ce6424a691de5673e3438d2768264827d23', 'Root build acceptance differs')
    bind(ENDPOINT / 'handoff.json', '2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748')
    endpoint_seal = json.loads((ENDPOINT / 'handoff.json').read_bytes())
    for name in ['source-package-manifest.json', 'source-bindings.json', 'review-source-package.tar.gz']:
        path = ENDPOINT / name
        expected = endpoint_seal['members'][str(path.relative_to(ROOT))]
        actual = bind(path)
        require(all(actual[key] == item for key, item in expected.items()), 'Reviewed source artifact differs')
    require(bind(ENDPOINT / 'review-source-package.tar.gz')['sha256'] == REVIEW_ARCHIVE, 'Reviewed endpoint archive differs')
    endpoint_review = ROOT / 'verification/apple-settings-fixed-chunk-review'
    bind(endpoint_review / 'handoff.json', '43f2ee87e461d28a8d05d113adf7a9581ea34c6d16e0dfe5caee26773febc092')
    endpoint_review_seal = json.loads((endpoint_review / 'handoff.json').read_bytes())
    for name in ['verification/apple-settings-fixed-chunk-review/review.json', 'docs/apple-settings-fixed-chunk-review.md']:
        actual = bind(ROOT / name)
        require(all(actual[key] == item for key, item in endpoint_review_seal['members'][name].items()),
                'Accepted fixed4992 independent review differs')
    endpoint_decision = json.loads((endpoint_review / 'review.json').read_bytes())
    require(endpoint_decision['status'] == 'ACCEPTED_SCOPED' and endpoint_decision['findings'] == []
            and endpoint_decision['producerSourceArchiveSHA256'] == REVIEW_ARCHIVE, 'Receiver review decision differs')
    source = json.loads((BUILD_ATTEMPT / 'source-manifest.json').read_bytes())
    require(len(source['sources']) == 40 and sha(stable(source['sources'])) == SOURCE
            and source['archive']['sha256'] == COMPILE_ARCHIVE, 'Exact fresh compile closure differs')
    accepted = archive_payload(BUILD_ATTEMPT / 'accepted-sources.tar.gz', source['sources'], COMPILE_ARCHIVE)
    reviewed = reviewed_payload()
    for name, raw in accepted.items():
        require(raw == reviewed['sources/' + name], 'Fresh compile source differs from reviewed endpoint package: ' + name)
    products = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    require(len(products['products']) == 55 and products['archive']['sha256'] == PRODUCT
            and products['originalApplicationFilesUnchanged'] == 13 and products['runnerProductsFresh'] is True
            and products['runnerProductFiles'] == 42 and products['sourceTreeSHA256'] == SOURCE,
            'Exact fresh product closure differs')
    require(sha(stable(products['products'])) == products['productTreeSHA256'] == PRODUCT_TREE,
            'Fresh product tree identity differs')
    archive_payload(BUILD_ATTEMPT / 'products.tar.gz', products['products'], PRODUCT)
    return bindings


def reviewed_payload():
    rows = json.loads((ENDPOINT / 'source-package-manifest.json').read_bytes())
    require(len(rows) == 97 and row(ENDPOINT / 'review-source-package.tar.gz')['sha256'] == REVIEW_ARCHIVE,
            'Exact reviewed package required')
    payload = {}
    with tarfile.open(ENDPOINT / 'review-source-package.tar.gz', 'r:gz') as archive:
        for member in archive.getmembers():
            safe_name(member.name)
            require(member.isfile() and member.name.startswith('package/'), 'Reviewed package regular file required')
            name = member.name[len('package/'):]
            require(name in rows and name not in payload, 'Unlisted/duplicate reviewed member')
            raw = archive.extractfile(member).read()
            require({'kind': 'file', 'mode': member.mode, 'bytes': len(raw), 'sha256': sha(raw)} == rows[name],
                    'Reviewed package member differs: ' + name)
            payload[name] = raw
    require(set(payload) == set(rows), 'Reviewed package inventory differs')
    return payload

''' +raw[end:]
start=raw.index('def derived_payload():')
end=raw.index('\ndef selection_template(',start)
raw=raw[:start]+'''def derived_payload():
    original = prior_payload()
    require(len(original) == 32, 'Exact approved V6 composition required')
    selected = dict(original)
    reviewed = reviewed_payload()
    # Prove the reviewed endpoint package preserved the other 31 V6 runtime files.
    for name, raw in original.items():
        require(name == RECEIVER or reviewed['sources/selected/' + name] == raw,
                'Unexpected reviewed runtime change: ' + name)
    selected[RECEIVER] = reviewed['sources/selected/' + RECEIVER]
    require(selected[RECEIVER] != original[RECEIVER], 'Fresh reviewed fixed4992 receiver required')
    substitutions = [(OLD_SOURCE, SOURCE), (OLD_PRODUCT, PRODUCT),
                     ('mixer.apple-focus-reference-root-selection.6', 'mixer.apple-focus-reference-root-selection.7'),
                     ('MixerFocusReferenceV6-', 'MixerFocusReferenceV7-'),
                     ('mixer.apple-focus-reference-runtime-import.6', 'mixer.apple-focus-reference-runtime-import.7')]
    for before, after in substitutions:
        selected['importer.py'] = replace_once(selected['importer.py'], before.encode(), after.encode())
    restored = selected['importer.py']
    for before, after in reversed(substitutions):
        restored = replace_once(restored, after.encode(), before.encode())
    require(restored == original['importer.py'], 'Importer changes beyond exact identity/namespace substitutions')
    adapter = (PRIOR / 'adapter.py').read_bytes()
    adapter = replace_once(adapter, b"'native-run-v6-'", b"'native-run-v7-'")
    adapter = replace_once(adapter, b"'mixer.apple-focus-reference-runtime.6'", b"'mixer.apple-focus-reference-runtime.7'")
    require(original['join_support.py'].endswith((PRIOR / 'adapter.py').read_bytes()), 'Approved V6 adapter suffix differs')
    selected['join_support.py'] = original['join_support.py'][:-len((PRIOR / 'adapter.py').read_bytes())] + adapter
    require(sorted(name for name in selected if selected[name] != original[name]) == sorted([RECEIVER, 'importer.py', 'join_support.py']),
            'Only reviewed receiver, importer identities and adapter namespace may change')
    return selected, adapter

''' +raw[end:]
raw=raw.replace('Instrumented Settings runtime selected source closure','Fixed4992 Settings V7 runtime selected source closure')
raw=raw.replace("fromfile='accepted-v5/'", "fromfile='accepted-v6/'").replace("tofile='instrumented-v6/'", "tofile='fixed4992-v7/'")
raw=raw.replace("'mixer.apple-settings-instrumented-runtime-packet.1'", "'mixer.apple-settings-fixed-chunk-runtime-packet.1'")
raw=raw.replace("'8b9b4950d23fd4595018deb751395e6bcc27d3e4'", "'be472ce6424a691de5673e3438d2768264827d23'")
raw=raw.replace("'mixer.apple-focus-reference-root-selection.6'", "'mixer.apple-focus-reference-root-selection.7'", 0) if False else raw
# Packet literals occur after the closed derivation and must not alter its before/after pairs.
raw=one(raw,"'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.6'", "'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.7'")
raw=one(raw,"'simulatorNamePrefix': 'MixerFocusReferenceV6-'", "'simulatorNamePrefix': 'MixerFocusReferenceV7-'")
raw=raw.replace('PASS: instrumented Settings runtime packet prepared; no native execution','PASS: fixed4992 V7 Settings runtime packet prepared; no native execution')
(BASE/'prepare.py').write_text(raw)
for name in ['local_first_failure.py','record_command.py','seal.py','run_controls.py']:
    (BASE/name).write_bytes((OLD/name).read_bytes())
raw=(BASE/'run_controls.py').read_text()
raw=raw.replace('root-selection.6','root-selection.7').replace('MixerFocusReferenceV6-','MixerFocusReferenceV7-').replace('native-run-v6-','native-run-v7-')
raw=one(raw,"['composition.py', 'importer.py', 'join_support.py', 'local_first_failure.py']","sorted([p.RECEIVER, 'importer.py', 'join_support.py'])")
raw=one(raw,"('mixer.apple-focus-reference-root-selection.7', 'mixer.apple-focus-reference-root-selection.5')", "('mixer.apple-focus-reference-root-selection.7', 'mixer.apple-focus-reference-root-selection.6')")
raw=one(raw,"('MixerFocusReferenceV7-', 'MixerFocusReferenceV5-')", "('MixerFocusReferenceV7-', 'MixerFocusReferenceV6-')")
raw=one(raw,"('mixer.apple-focus-reference-runtime-import.6', 'mixer.apple-focus-reference-runtime-import.5')", "('mixer.apple-focus-reference-runtime-import.7', 'mixer.apple-focus-reference-runtime-import.6')")
raw=one(raw,'for version in [6, 5, 4, 7]:','for version in [7, 6, 5, 8]:')
raw=one(raw,'accepted = version == 6 and not wrong_argv','accepted = version == 7 and not wrong_argv')
raw=raw.replace("root-selection.5'", "root-selection.6'").replace("MixerFocusReferenceV5-rejected", "MixerFocusReferenceV6-rejected")
raw=one(raw,"    if event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'socket.bind',\n                 'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo'}:","    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'pty.spawn'}:")
(BASE/'run_controls.py').write_text(raw)
raw=(BASE/'seal.py').read_text().replace('apple-settings-instrumented-runtime-preparation.md','apple-settings-fixed-chunk-runtime-preparation.md')
raw=one(raw,"if path.is_file() and path.name not in {'handoff.json', 'handoff.sha256'}:","if path.is_file() and path not in {p.BASE / 'handoff.json', p.BASE / 'handoff.sha256'}:")
raw=one(raw,"if path.is_relative_to(p.BASE / 'commands/seal'):","if any(path.is_relative_to(p.BASE / name) for name in ['commands/seal', 'commands/verify']):")
(BASE/'seal.py').write_text(raw)
raw=(BASE/'record_command.py').read_text()
raw=one(raw,"'sourceSHA256': sha((BASE / script).read_bytes()),", "'sourceSHA256': sha((BASE / script).read_bytes()),\n               'sourceRevisionContext': 'be472ce6424a691de5673e3438d2768264827d23',\n               'compileSourceTreeSHA256': '0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb',\n               'commandSourceFiles': {item.name: {'bytes': item.stat().st_size, 'sha256': sha(item.read_bytes())}\n                                      for item in sorted(BASE.glob('*.py'))},")
(BASE/'record_command.py').write_text(raw)
print('Prepared exact-source host utility derivation; no selected/native module imported')
