from pathlib import Path
p=Path('cli/Sources/MixerBuild/Resources/android-build.py');s=p.read_text()
s=s.replace("APPEARANCE_ASSET = 'assets/MixerAppearanceV2/descriptor.json'", "APPEARANCE_ASSET = 'assets/MixerAppearanceV2/descriptor.json'\nSOURCE_PROFILE_HEX = '__MIXER_ANDROID_SOURCE_PROFILE_HEX__'")
index=s.index('\ndef probe(args):')
s=s[:index]+'''
def source_profile():
    """Build-only decode. Raw import/inspect never evaluates the template marker."""
    message = 'Android SDK source profile is not rendered or supported; recreate with the matching CLI.'
    try:
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError('duplicate profile key')
                value[key] = item
            return value
        value = json.loads(bytes.fromhex(SOURCE_PROFILE_HEX), object_pairs_hook=unique)
        keys = {'schema', 'id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256',
                'default_descriptor', 'sdk_files', 'adapter_files', 'wire'}
        if not isinstance(value, dict) or set(value) != keys or type(value['schema']) is not int or value['schema'] != 1 or value['id'] != 'mixer.android-source-pair.1':
            raise ValueError('unsupported profile shape/id')
        def identity(item):
            return (isinstance(item, dict) and set(item) == {'bytes', 'sha256'} and
                    type(item['bytes']) is int and 0 < item['bytes'] <= 1_048_576 and
                    isinstance(item['sha256'], str) and re.fullmatch('[0-9a-f]{64}', item['sha256']) is not None)
        if not identity(value['default_descriptor']) or value['default_descriptor']['bytes'] > 65_536:
            raise ValueError('unsupported descriptor identity')
        for kind, count in (('sdk', 22), ('adapter', 20)):
            files = value[kind + '_files']
            if not isinstance(files, dict) or len(files) != count:
                raise ValueError('unsupported source map')
            for path, item in files.items():
                if (not isinstance(path, str) or not path.isascii() or
                    any(part in ('', '.', '..') for part in path.split('/')) or path.startswith('/') or not identity(item)):
                    raise ValueError('unsupported source identity')
            projection = hashlib.sha256(''.join(path + '\\0' + files[path]['sha256'] + '\\n' for path in sorted(files)).encode()).hexdigest()
            if projection != value[kind + '_compatibility_sha256']:
                raise ValueError('unsupported projection digest')
        wire = value['wire']
        if (not isinstance(wire, dict) or set(wire) != {'android_profile_id', 'appearance_format', 'appearance_recipe', 'document_schema', 'native_packet_schema', 'staged_C_ABI'} or
            type(wire['document_schema']) is not int or type(wire['native_packet_schema']) is not int or
            wire['document_schema'] != 1 or wire['native_packet_schema'] != 1 or
            not all(isinstance(item, str) and item for key, item in wire.items() if key not in ('document_schema', 'native_packet_schema'))):
            raise ValueError('unsupported wire shape')
        return value
    except (ValueError, TypeError, KeyError, UnicodeError) as error:
        raise RuntimeError(message) from error


def profile_lock(profile):
    return {key: profile[key] for key in ('id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor')}


def profile_required(android, profile):
    if not isinstance(android, dict) or not isinstance(android.get('profile'), dict):
        raise RuntimeError('android.sdk-profile-required: Android project predates source-pair admission; explicitly migrate or recreate with the matching first-party CLI/SDK distribution.')
    if android['profile'] != profile_lock(profile):
        raise RuntimeError('android.sdk-profile-mismatch: recreate with the matching first-party CLI/SDK distribution (' + profile['id'] + ').')


def profile_failure(path):
    return RuntimeError('Android SDK source compatibility rejected (' + str(path) + '); install the matching first-party CLI/SDK distribution. Local locks cannot authorize changed sources.')


def ordinary_directory(path):
    try:
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise profile_failure(path)
    except FileNotFoundError as error:
        raise profile_failure(path) from error


def exact_path(root, relative, directory=False, identity=None):
    current = root
    parts = relative.split('/')
    for index, name in enumerate(parts):
        ordinary_directory(current)
        if name not in [p.name for p in current.iterdir()]:
            raise profile_failure(relative)
        current = current / name
        if index < len(parts) - 1 or directory:
            ordinary_directory(current)
    if identity is not None:
        info = current.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != identity['bytes']:
            raise profile_failure(relative + ': expected ordinary pinned-size file')
    return current


def closed_sources(root, relative, files):
    directory = exact_path(root, relative, directory=True)
    prefix = relative + '/'
    expected = {p[len(prefix):].split('/')[0] for p in files if p.startswith(prefix)}
    if {p.name for p in directory.iterdir()} != expected:
        raise profile_failure(relative + ': exact directory inventory')
    for name in sorted(expected):
        item = relative + '/' + name
        if item in files:
            exact_path(root, item, identity=files[item])
        else:
            closed_sources(root, item, files)


def sdk_layout(root, profile):
    ordinary_directory(root)
    names = [p.name for p in root.iterdir()]
    # This MUST precede transformation/classification and entry lstat/follow/read.
    if not all(name.isascii() for name in names):
        raise profile_failure('non-ASCII SDK-root entry name')
    for name in names:
        if name.lower().startswith('package') and name != 'Package.swift':
            raise profile_failure('reserved SDK manifest namespace: ' + name)
    exact_path(root, 'Package.swift', identity=profile['sdk_files']['Package.swift'])
    for relative in ('Sources/MixerCore', 'Sources/MixerUI'):
        closed_sources(root, relative, profile['sdk_files'])


def adapter_layout(root, profile):
    for relative, identity in profile['adapter_files'].items():
        exact_path(root, relative, identity=identity)
    for relative in ('Sources/MixerAndroidRuntime', 'app/src', 'bridge', 'contracts'):
        closed_sources(root, relative, profile['adapter_files'])


def pinned_read(path, identity):
    with path.open('rb') as stream:
        data = stream.read(identity['bytes'] + 1)
    if len(data) != identity['bytes'] or hashlib.sha256(data).hexdigest() != identity['sha256']:
        raise profile_failure(path)
    return data


def admit_source_pair(root, profile):
    generated = exact_path(root, 'Generated', directory=True)
    adapter = exact_path(generated, 'MixerAndroid', directory=True)
    # Closed appearance topology/type/size before required-source content reads.
    appearance_layout(adapter)
    sdk = exact_path(generated, 'MixerSDK', directory=True)
    sdk_layout(sdk, profile)
    adapter_layout(adapter, profile)
    appearance = pinned_read(adapter / 'app' / APPEARANCE_ASSET, profile['default_descriptor'])
    for directory, key in ((sdk, 'sdk_files'), (adapter, 'adapter_files')):
        for relative, identity in profile[key].items():
            pinned_read(directory / relative, identity)
    return appearance

''' + s[index:]
# preserve public appearance_input helper for packaging tests, split topology from its read.
s=s.replace('def appearance_input(adapter):','def appearance_layout(adapter):',1)
s=s.replace("    assets = adapter / 'app/assets'", "    exact_path(adapter.parent.parent, 'Generated/MixerAndroid/app/assets/MixerAppearanceV2', directory=True)\n    assets = adapter / 'app/assets'",1)
s=s.replace("    with descriptor.open('rb') as stream:\n        data = stream.read(65_537)", "    return descriptor, info.st_size\n\n\ndef appearance_input(adapter):\n    descriptor, size = appearance_layout(adapter)\n    with descriptor.open('rb') as stream:\n        data = stream.read(65_537)",1)
s=s.replace('    if len(data) != info.st_size:', '    if len(data) != size:',1)
s=s.replace("def build(root):\n    lock =", "def build(root):\n    profile = source_profile()\n    lock =",1)
s=s.replace("    if not android:\n        raise RuntimeError('Android host is not generated. Create a new project with --platform android.')", "    profile_required(android, profile)",1)
s=s.replace('    appearance = appearance_input(adapter)', '    appearance = admit_source_pair(root, profile)',1)
s=s.replace("    if appearance_input(adapter) != appearance or source_tree(adapter) != android['adapterDigest']:", "    if admit_source_pair(root, profile) != appearance or source_tree(adapter) != android['adapterDigest']:",1)
s=s.replace('    if appearance_input(adapter) != appearance:', '    if admit_source_pair(root, profile) != appearance:',1)
s=s.replace("        'sdk_digest': lock['sdkDigest'], 'adapter_digest': android['adapterDigest'],", "        'sdk_digest': lock['sdkDigest'], 'adapter_digest': android['adapterDigest'],\n        'source_profile': profile_lock(profile), 'source_profile_observation': 'matched-reviewed-source-pair',",1)
p.write_text(s)
