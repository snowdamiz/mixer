#!/usr/bin/env python3
"""Bind the independently reviewed C3 bytes without rewriting historical C2."""
import datetime
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/swift-function-cache/candidate-3'
REVIEW = ROOT / 'verification/swift-function-cache-review'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


producer = json.loads((PRODUCER / 'producer-receipt.json').read_text())
review = json.loads((REVIEW / 'candidate-3-review-receipt.json').read_text())
freeze = json.loads((PRODUCER / 'source-freeze.json').read_text())
measure = json.loads((REVIEW / 'candidate3-final-map/measurement-receipt.json').read_text())
require(review['required_missing_assertions'] == [], 'mandatory assertions')
require(review['decision'] == 'pass_bounded_private_cache_required_synthetic_assertions_and_selected_named_object_accounting', 'independent decision')
require(review['producer_receipt_sha256'] == sha((PRODUCER / 'producer-receipt.json').read_bytes()), 'producer decision seal')
require(review['source_manifest_sha256'] == producer['source_manifest_sha256'] == freeze['source_manifest_sha256'], 'source union')
require(sha(json.dumps(freeze['source_manifest'], sort_keys=True).encode()) == freeze['source_manifest_sha256'], 'source digest')
require(review['bounds'] == {'construction': 57224, 'operation': 80566, 'cleanup': 62096, 'header': 62424, 'foundation': 16504}, 'measured bounds')
require(review['construction_delta'] == 96 and review['preflight_and_final_whole_slot_assignments_unchanged_and_independently_verified'], 'accounting delta')
bindings = {}
count = 0


def bind(path, expected):
    global count
    require(sha((ROOT / path).read_bytes()) == expected, path)
    bindings[path] = expected
    count += 1


for mapping in [producer['bindings'], review['bound_review_artifacts']]:
    for path, digest in mapping.items():
        bind(path, digest)
# The measurement intentionally appends two private test probes. Reconstruct
# those exact derived bytes independently; never call their hashes live source.
measurement_dir = REVIEW / 'candidate3-final-map'
probe_tails = {
    'vm/src/experimental_swift_reactor/cache.rs': ('\n#[cfg(test)]\ninclude!(' + json.dumps(str(measurement_dir / 'measure.rs')) + ');\n').encode(),
    'vm/src/experimental_swift_reactor/cache_tests.rs': b'\n#[test]\nfn review_only_candidate3_map_measurement(){let bytes=fixture(0,&[0,0x0b],100);let(mut c,a)=adopt(&bytes,SwiftRunBudget::default());super::cache::review_rootleaf_measure(&mut c);c.drop_proof(a).unwrap();let _=c.finish_owned_cleanup(None); }\n'.replace(b'; }', b';}'),
}
require(set(measure['derived_sources']) == set(probe_tails), 'derived source inventory')
for path, digest in measure['full_vm_input_manifest'].items():
    if path in probe_tails:
        require(sha((ROOT / path).read_bytes()) == measure['source_before_test_overlay'][path], 'measurement base ' + path)
        require(sha((ROOT / path).read_bytes() + probe_tails[path]) == digest == measure['derived_sources'][path], 'derived measurement ' + path)
        count += 1
    else:
        bind(path, digest)
with tarfile.open(PRODUCER / 'frozen-source.tar.gz', 'r:gz') as archive:
    require(len(archive.getmembers()) == len(freeze['source_manifest']) == 118, 'archive inventory')
    for path, digest in freeze['source_manifest'].items():
        member = archive.getmember(path)
        require(member.isfile(), 'archive regular source ' + path)
        require(sha(archive.extractfile(member).read()) == digest, 'archive ' + path)
        count += 1
        bind(path, digest)
for path in [Path(__file__), PRODUCER / 'producer-receipt.json', PRODUCER / 'seal-audit.json',
             REVIEW / 'candidate-3-review-receipt.json', REVIEW / 'candidate-3-review.md',
             ROOT / 'docs/swift-cache-candidate3-acceptance.md',
             ROOT / 'docs/swift-cache-foundation-phase-addendum.md',
             ROOT / 'verification/swift-cache-foundation-phase-review/acceptance.json']:
    bind(str(path.relative_to(ROOT)), sha(path.read_bytes()))
result = {
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'integrator': 'root', 'independent_reviewer': 'swift_function_cache_review',
    'decision': 'accepted_bounded_private_cache_and_candidate3_named_object_accounting',
    'source_manifest_sha256': freeze['source_manifest_sha256'], 'binding_checks': count, 'bindings': bindings,
    'derived_measurement_inputs': measure['derived_sources'], 'bounds': review['bounds'], 'construction_delta': 96, 'required_missing_assertions': [],
    'evidence': {'exact_named_commands': 36, 'terminal_latches_per_mode': 21, 'repeated_routes_per_mode': 315,
        'actual_constructor_exhaustions_per_mode': 3, 'independent_concurrent_owner_isolation': True,
        'independent_legacy_replays': 4, 'independent_supplementary_probes_per_mode': 8,
        'private_compile_outcomes': 12, 'independent_layout_rows': 138, 'inventory_fields': 584,
        'attributed_producer_tests_per_mode': {'all_features': 340, 'minimal_swift': 226, 'references': 9}},
    'next_permitted_assignment': 'Compiling private executor type/lifetime/layout prerequisite under frozen executor contract, separately owned; no full execution accepted.',
    'limits': 'Authored named-value accounting only; no physical stack/RSS. Explicit terminal latches are not natural executor failure origins. No full Swift target instantiation/initialization/invocation, public execution, physical devices, release, dogfood or GA acceptance. Historical C2 exact-source acceptance remains historical.',
}
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'decision': result['decision'], 'binding_checks': count}))
