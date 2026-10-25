"""Read-only content and bounded archive helpers for this packet only."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/swift-cache-retention-candidate'
CANDIDATE_SEAL = '6507e85f869d0f1a052b9e8e5356ac07910c67813f87b309fa6a5b348e803c13'
CANDIDATE_CLOSURE = 'd840933a706131e64c50b74812af771ead622912d57575336770434387f5b99d'
LIVE_BASELINE_CLOSURE = '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
HARNESS_HASH = 'd72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00'
MAX_MEMBERS = 132
MAX_TOTAL_BYTES = 24 * 1024 * 1024
MAX_MEMBER_BYTES = 16 * 1024 * 1024


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, ('duplicate JSON key', key)
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def closure(manifest):
    return hashlib.sha256((json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    assert name and not path.is_absolute() and str(path) == name
    assert not any(part in ('', '.', '..') for part in path.parts)
    return path


def verify_candidate():
    assert sha(CANDIDATE / 'seal.json') == CANDIDATE_SEAL
    seal = read(CANDIDATE / 'seal.json')
    for name, expected in seal['members'].items():
        safe_name(name)
        path = CANDIDATE / name
        assert not path.is_symlink() and sha(path) == expected, name
    for name, expected in seal['externalMembers'].items():
        safe_name(name)
        assert sha(ROOT / name) == expected, name
    assert sha(CANDIDATE / 'candidate-manifest.json') == CANDIDATE_CLOSURE
    assert sha(CANDIDATE / 'baseline-manifest.json') == LIVE_BASELINE_CLOSURE
    handoff = read(CANDIDATE / 'handoff.json')
    assert handoff['candidateManifestSHA256'] == CANDIDATE_CLOSURE
    assert handoff['baselineClosureSHA256'] == LIVE_BASELINE_CLOSURE
    assert handoff['fullTargetAttempts'] == 0 and not handoff['liveVMModified']
    return seal


def archive_payloads(path, expected):
    """Never extractall: closed names, regular files, finite headers/bytes, hashes first."""
    assert len(expected) == MAX_MEMBERS
    for name in expected:
        safe_name(name)
    path = Path(path)
    assert not path.is_symlink() and path.stat().st_size <= 2 * 1024 * 1024
    payloads = {}
    total = 0
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            safe_name(member.name)
            assert member.name in expected and member.name not in payloads
            assert member.isfile() and not member.issym() and not member.islnk()
            assert not member.pax_headers, 'no extended member metadata'
            assert 0 <= member.size <= MAX_MEMBER_BYTES
            total += member.size
            assert len(payloads) < MAX_MEMBERS and total <= MAX_TOTAL_BYTES
            stream = archive.extractfile(member)
            assert stream is not None
            data = stream.read(member.size + 1)
            assert len(data) == member.size
            assert hashlib.sha256(data).hexdigest() == expected[member.name], member.name
            payloads[member.name] = data
    assert set(payloads) == set(expected)
    return payloads


def candidate_payloads():
    verify_candidate()
    return archive_payloads(CANDIDATE / 'candidate-source.tar.gz',
                            read(CANDIDATE / 'candidate-manifest.json'))


def write_source(payloads, destination):
    destination = Path(destination)
    scratch = HERE / 'owned-scratch'
    assert destination == scratch / 'vm' and not destination.exists()
    assert scratch.exists() and not scratch.is_symlink() and scratch.resolve() == scratch
    for name, data in payloads.items():
        path = destination / safe_name(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)


def verify_prepared_seal():
    seal = read(HERE / 'prepared-seal.json')
    ignored = {'prepared-seal.json', 'root-selection.json', 'bin/exact-tests'}
    files = {str(path.relative_to(HERE)) for path in HERE.rglob('*')
             if path.is_file() and 'owned-scratch' not in path.relative_to(HERE).parts
             and str(path.relative_to(HERE)) not in ignored}
    assert files == set(seal['files']), 'prepared inventory changed'
    for name, expected in seal['files'].items():
        safe_name(name)
        assert sha(HERE / name) == expected, name
    for name, expected in seal['externalFiles'].items():
        safe_name(name)
        assert sha(ROOT / name) == expected, name
    return seal


def accepted_review(selection):
    """Bind the finalized independent acceptance, never an in-progress receipt."""
    review = ROOT / 'verification/swift-cache-retention-review'
    assert selection['reviewSealPath'] == str(review / 'seal.json')
    assert selection['reviewSummaryPath'] == str(review / 'result-summary.json')
    assert sha(review / 'seal.json') == selection['reviewSealSHA256']
    assert sha(review / 'result-summary.json') == selection['reviewSummarySHA256']
    seal = read(review / 'seal.json')
    members = seal.get('members', seal.get('files'))
    assert isinstance(members, dict) and members.get('result-summary.json') == selection['reviewSummarySHA256']
    for name, expected in members.items():
        safe_name(name)
        assert sha(review / name) == expected, name
    for name, expected in seal.get('externalMembers', seal.get('externalFiles', {})).items():
        safe_name(name)
        assert sha(ROOT / name) == expected, name
    summary = read(review / 'result-summary.json')
    assert summary['schema'] == 1
    assert summary['status'] == 'finite-correctness-accounting-prerequisite-accepted'
    assert summary['finitePrerequisiteAccepted'] is True and summary['blockingFindings'] == []
    assert summary['candidateSealSHA256'] == CANDIDATE_SEAL
    assert summary['candidateManifestSHA256'] == CANDIDATE_CLOSURE
    assert summary['baselineClosureSHA256'] == LIVE_BASELINE_CLOSURE
    assert summary['fullDiagnosticSelected'] is False
    assert summary['liveIntegrationAccepted'] is False and summary['gaAccepted'] is False
    return summary
