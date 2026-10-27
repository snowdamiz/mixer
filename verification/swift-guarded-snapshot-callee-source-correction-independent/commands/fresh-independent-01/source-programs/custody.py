"""Read-only full frozen membership custody; never import query-named or caches."""
from pathlib import Path
import hashlib, json, stat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-provider-callee-source-correction'
SEAL = 'e80dd24b7cb7e18c97abb1effa705cbc2b7882b36ac8e439a181bc6cf3a6dfb1'
TREE = 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def need(ok, message):
    if not ok:
        raise ValueError(message)

def row(path):
    need(path.is_file() and not path.is_symlink(), 'regular input: ' + str(path))
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}

def load(path):
    return json.loads(path.read_bytes())

def verify_packet(folder, digest, count, total, modes=False):
    seal = row(folder / 'seal.json')
    need(seal['sha256'] == digest, 'frozen seal digest')
    packet = load(folder / 'seal.json')
    members = packet['members']
    need(len(members) == count and sum(x['bytes'] for x in members) == total, 'frozen envelope')
    names = {x['path'] for x in members}
    need(len(names) == count, 'unique frozen membership')
    need(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names), 'safe relative frozen names')
    need(all(not p.is_symlink() for p in folder.rglob('*')), 'no frozen symlinks')
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    need(actual == names | {'seal.json'}, 'complete frozen membership: ' + str(folder))
    observed = [seal]
    for item in members:
        p = folder / item['path']
        observed_row = row(p)
        need((observed_row['bytes'], observed_row['sha256']) == (item['bytes'], item['sha256']), 'frozen member: ' + str(p))
        observed.append(observed_row)
    if modes:
        files = [p for p in folder.rglob('*') if p.is_file()]
        directories = [folder] + [p for p in folder.rglob('*') if p.is_dir()]
        need(len(files) == 220 and len(directories) == 22, 'producer exact mode roster')
        need(all(stat.S_IMODE(p.stat().st_mode) == 0o444 for p in files), 'producer read-only files')
        need(all(stat.S_IMODE(p.stat().st_mode) == 0o555 for p in directories), 'producer read-only directories')
    return observed

def snapshot():
    lock = load(PRODUCER / 'input-lock.json')
    need(lock['source_tree_sha256'] == TREE, 'source146 tree')
    need(lock['inherited_priced_input_count'] == 1245 and lock['inherited_frozen_packet_count'] == 15, 'inherited input scope')
    by = {}
    def keep(item):
        if item['path'] in by:
            need(by[item['path']] == item, 'consistent duplicate input')
        by[item['path']] = item
    for item in lock['files']:
        observed = row(ROOT / item['path'])
        need(observed == item, 'input-lock byte custody: ' + item['path'])
        keep(observed)
    for packet in lock['frozen_packets']:
        for item in verify_packet(ROOT / packet['path'], packet['seal_sha256'], packet['members'], packet['bytes']):
            keep(item)
    for item in verify_packet(PRODUCER, SEAL, 219, 13305313, modes=True):
        keep(item)
    excluded = lock['excluded_inherited_cache_metadata']
    need(len(excluded) == 1 and excluded[0]['path'].endswith('/__pycache__/query-named.cpython-314.pyc'), 'single separately retained cache')
    for item in excluded:
        need(row(ROOT / item['path']) == item, 'excluded cache metadata unchanged')
    anchors = {
        'verification/swift-semantic-adapter-root-review/guarded-snapshot-provider-callee-source-correction-frozen-release.json': 'f848cffc8178d9737d244d253b420f22abf1a7572f633d22f4e2243fcea3536f',
        'verification/swift-guarded-snapshot-owned-provider-callee-independent/correction-contract.json': '85161323e1ea8d101dd71db0f0466d452d964a7b3f25ad80b209891e14fb6320',
        'verification/swift-semantic-adapter-root-review/guarded-snapshot-owned-provider-callee-interfaces-return.json': 'd497b65fed7324ffa52b5a90a2c8b8c2bdd323c59a2a574a5b38d44667f0dc49',
        'verification/swift-semantic-adapter-root-review/provider-callee-source-correction-release-preflight-failure.json': '351f90ac651077a82407d77a353da373e3f8967ac890995d765cb05b215b59ba',
        'verification/swift-semantic-adapter-root-review/release-provider-callee-source-correction.py': 'bcb1361368a51ae5be9878e5efcbff3c02ad5a01fb449f6fd20b41ec720a2dc4',
        'verification/swift-semantic-adapter-root-review/release-provider-callee-source-correction-after-mode-hardening.py': 'd5eac6b0718faca1880d305d4d0924a99be56f51787452b5a8b2e56196c1b991',
    }
    for name, digest in anchors.items():
        item = row(ROOT / name)
        need(item['sha256'] == digest, 'root/original-review anchor')
        keep(item)
    for name in ('AGENTS.md', 'PLAN.md', 'mixer-product-plan.md'):
        # Current guidance is recorded independently, outside all priced source inputs.
        keep(row(ROOT / name))
    return {'schema': 1, 'source146_tree_sha256': TREE, 'producer_seal_sha256': SEAL,
            'producer_members': 219, 'producer_bytes': 13305313,
            'producer_files_0444': 220, 'producer_directories_0555': 22,
            'inherited_priced_inputs': 1245, 'inherited_frozen_packets': 15,
            'complete_frozen_packets_checked': len(lock['frozen_packets']) + 1,
            'files': sorted(by.values(), key=lambda x: x['path']),
            'excluded_cache_metadata_only': excluded, 'cache_imported_executed_or_mutated': False,
            'current_guidance_is_priced': False}
