"""Source-only JSON preparation. Never imports or invokes a certificate verifier."""
import hashlib
import json
from pathlib import Path
import time

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/swift-retained-partial-certificate-v1'
START = time.monotonic()
LIMIT = 8 * 1024 * 1024
inputs = {}
read_bytes = 0


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(relative):
    global read_bytes
    path = ROOT / relative
    before = path.stat()
    if not path.is_file() or path.is_symlink() or before.st_size > LIMIT:
        raise RuntimeError('bounded regular metadata source required: ' + relative)
    raw = path.read_bytes()
    read_bytes += len(raw)
    if read_bytes > LIMIT or time.monotonic() - START > 55:
        raise RuntimeError('source-only preparation bound')
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after):
        raise RuntimeError('input changed while reading: ' + relative)
    inputs[relative] = {'path': relative, 'bytes': len(raw), 'sha256': sha(raw)}
    return raw


def load(relative):
    return json.loads(read(relative))


def put(name, value):
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    if len(raw) > LIMIT:
        raise RuntimeError('derived member bound')
    (OUT / name).write_bytes(raw)


P = 'verification/'
source_path = P + 'swift-root-bound-dispatch-retained-verifier-v1/source/region_certificate.py'
verifier_text = read(source_path).decode()
plan = load(P + 'swift-root-bound-dispatch-retained-capture-v1/plan.json')
observation_path = P + 'swift-root-bound-dispatch-retained-capture-v1/runtime/capture-observation.json'
observation = load(observation_path)
policy_path = P + 'swift-root-bound-dispatch-retained-capture-v1/diagnostic-policy.json'
policy = load(policy_path)
manifest = load(plan['source_manifest']['path'])
frontier = load(plan['frontier']['path'])
identity = load(P + 'swift-semantic-adapter-root-review/dispatch-retained-physical-identity-acceptance.json')
local_acceptance = load(P + 'swift-semantic-adapter-root-review/dispatch-retained-local-geometry-acceptance.json')
verifier_acceptance = load(P + 'swift-semantic-adapter-root-review/dispatch-retained-verifier-source-acceptance.json')
geometry_seal_path = P + 'swift-retained-geometry-independent/seal.json'
verifier_seal_path = P + 'swift-root-bound-dispatch-retained-verifier-independent/seal.json'
read(geometry_seal_path)
read(verifier_seal_path)
if inputs[geometry_seal_path]['sha256'] != 'e840f9929d49e1abeea6f9c454a60cf589e6fb2a72b211eda857fd64a5a6ef50':
    raise RuntimeError('selected geometry review seal changed')
if inputs[verifier_seal_path]['sha256'] != '57f374b75c686fbc62024fd31b2a7ea37e80e33c57016a15b2db99dd3f3b739f':
    raise RuntimeError('selected verifier review seal changed')
facts_review = load(P + 'swift-retained-geometry-independent/local-facts-review.json')
caller = load(P + 'swift-retained-geometry-caller-closure/facts.json')
caller_bindings = load(P + 'swift-retained-geometry-caller-closure/whole-function-bindings.json')
caller_anchors = load(P + 'swift-retained-geometry-caller-closure/instruction-anchors.json')
caller_calls = load(P + 'swift-retained-geometry-caller-closure/caller-call-sites.json')
closure_calls = load(P + 'swift-retained-geometry-caller-closure/closure-call-sites.json')
dispatch = load(P + 'swift-retained-geometry-dispatch-body/dispatch-facts.json')
body = load(P + 'swift-retained-geometry-dispatch-body/body-facts.json')
edges = load(P + 'swift-retained-geometry-dispatch-body/edges-and-exits.json')
readiness = load(P + 'swift-retained-geometry-dispatch-body/verifier-readiness.json')
cross = load(P + 'swift-retained-geometry-dispatch-body/cross-lane-candidate-join.json')
targets = load(P + 'swift-retained-capture-terminal-mapping/target-map.json')

scope = {'link_dead_code': True, 'alternate_diagnostic_configuration_only': True,
         'original_capture_qualified': False, 'runtime_admission_accepted': False}
if observation['binding'] != plan['verifier_binding']:
    raise RuntimeError('retained immutable observation binding changed')
if any(observation[key] is not value for key, value in scope.items() if key != 'link_dead_code'):
    raise RuntimeError('immutable observation scope levels changed')
binding = observation['binding']
binding_sha = sha(canonical(binding))
source_pin = inputs[plan['source_manifest']['path']]
if source_pin['sha256'] != observation['source_manifest_sha256'] or source_pin['sha256'] != plan['source_manifest']['sha256']:
    raise RuntimeError('source manifest metadata join changed')

required_inputs = []
generated_root = P + 'swift-root-bound-dispatch-retained-capture-v1/runtime/'
path_for_output = {'ir': generated_root + 'generated/dispatch.ll',
                   'asm': generated_root + 'generated/dispatch.s',
                   'stdout': generated_root + 'compile.stdout', 'stderr': generated_root + 'compile.stderr'}
# The compiler stdout/stderr saved names come from the immutable observations,
# rather than an invented replacement. Resolve their selected published pins.
runtime_observations = load(generated_root + 'observations.json')
runtime_receipt = load(generated_root + 'receipt.json')
for pin in observation['outputs']:
    required_inputs.append({**pin, 'path': path_for_output[pin['name']],
                            'freshly_read_or_hashed': False,
                            'pin_provenance': observation_path + '#outputs[name=' + pin['name'] + ']'})
for name, path in [('source_manifest', plan['source_manifest']['path']),
                   ('frontier', plan['frontier']['path']),
                   ('mir', frontier['targets'][0]['retained_MIR']['file']['path']),
                   ('capture_observation', observation_path), ('diagnostic_policy', policy_path)]:
    pin = inputs.get(path) or frontier['targets'][0]['retained_MIR']['file']
    required_inputs.append({'name': name, 'path': path, 'bytes': pin['bytes'], 'sha256': pin['sha256'],
                            'freshly_read_or_hashed': path in inputs})
for member in manifest['members']:
    required_inputs.append({'name': 'source/' + member['path'],
                            'path': P + 'swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/' + member['path'],
                            'bytes': member['bytes'], 'sha256': member['sha256'],
                            'freshly_read_or_hashed': False,
                            'pin_provenance': plan['source_manifest']['path'] + '#members'})

capture_acceptance_proposal = {'schema': 1, 'status': 'accepted-capture-custody-only',
    'observation_sha256': inputs[observation_path]['sha256'],
    'diagnostic_policy_sha256': inputs[policy_path]['sha256'],
    'source_manifest_sha256': source_pin['sha256'], 'binding_sha256': binding_sha,
    'outputs': observation['outputs'], 'local_geometry_only': True,
    'complete_capacity_accepted': False, **scope}
put('proposed-capture-acceptance-envelope.json', capture_acceptance_proposal)
put('proposed-input-bindings.json', {
    'schema': 1, 'status': 'UNAPPROVED_INPUT_BINDING_PROPOSAL_NOT_AN_INVOCATION', **scope,
    'binding': binding,
    'binding_sha256_canonical_JSON': binding_sha,
    'certificate': None, 'semantic_review': None, 'independent_seal': None,
    'trusted_root_approval': None, 'expected_external_approval_sha256': None,
    'synthetic': False, 'invocation_selected': False,
    'immutable_observation_field_levels': {
        'binding': 'exact plan.verifier_binding; link_dead_code is nested here',
        'scope': 'alternate_diagnostic_configuration_only, original_capture_qualified and runtime_admission_accepted are top-level',
        'outputs': 'ordered exact ir/asm/stdout/stderr name-byte-sha pins',
        'source_manifest_sha256': 'top-level, matched to retained-plan manifest pin',
        'successful_custody_booleans': {key: observation[key] for key in ['owned_groups_closed', 'cleanup_complete', 'bounds_met', 'truncated', 'capture_complete']},
        'compiler_exit': observation['compiler_exit']},
    'existing_inputs': required_inputs,
    'raw_pair_bytes_from_immutable_observation': sum(x['bytes'] for x in observation['outputs'] if x['name'] in ('ir', 'asm')),
    'raw_pair_read_this_preparation': False,
    'source_member_pins_are_inherited_not_fresh_content_hashes': True,
    'capture_acceptance_translation_requires_root_selection': True,
    'capture_custody_authority': identity,
    'blocked_missing_inputs': ['truthful structured complete-or-explicitly-incomplete certificate stage mapping', 'independent semantic-map review', 'independent semantic-map seal', 'trusted root approval only if subsequently selected']})

put('proposed-partial-semantic-map.json', {
    'schema': 'PROPOSAL_ONLY_NOT_VERIFIER_V1_SCHEMA',
    'status': 'UNAPPROVED_PARTIAL_SOURCE_FACTS_WITH_UNREPRESENTABLE_COPY_STAGES', **scope,
    'binding': binding, 'trusted_root_approval': None, 'independent_semantic_review': None,
    'numeric_union': None, 'local_peak_bytes': None, 'whole_capacity': None,
    'complete_capacity_accepted': False, 'whole_map_complete': False,
    'accepted_scope': local_acceptance,
    'known_local_reservations_bytes': facts_review['accepted_reservations_bytes'],
    'whole_native_function_spans': targets['targets'],
    'known_instruction_coordinate_relations_only': facts_review['emitted_success_chain_signed_coordinates_only'],
    'physical_base_congruences': None,
    'outer_O': caller['Caller']['outer_O'],
    'Caller_slots': caller['Caller']['slots'],
    'Closure_slots': caller['Closure']['slots'],
    'Dispatch_slots': dispatch['frame']['native_slots'],
    'Dispatch_spills': dispatch['frame']['native_spills'],
    'Body_slots': body['frame']['native_slots'],
    'Body_spills': body['frame']['native_spills'],
    'Body_padding_intervals_final_sp': body['frame']['unassigned_native_padding_intervals_final_sp'],
    'Body_exception_record_internal_padding_final_sp': body['frame']['exception_record_internal_padding_final_sp'],
    'caller_to_dispatch_capture': caller['Caller']['closure_record'],
    'closure_capture_forwarding': caller['Closure']['loads'],
    'dispatch_all_copy_stages': dispatch['return_storage'],
    'body_all_copy_stages': body['admitted_return'],
    'body_cleanup_and_termination': body['cleanup_state_machine'],
    'Body_normal_SP_path_only': body['frame']['normal_signed_sp_path_candidate'],
    'Body_nonlocal_SP_path_without_fabricated_restoration': body['frame']['cleanup_and_terminate_signed_sp_path_candidate'],
    'complete_all_exit_unwind_restoration_accepted': False,
    'all_native_and_IR_edges': {'Caller': caller_calls, 'Closure': closure_calls, 'Dispatch_and_Body': edges},
    'retained_partitions': readiness['retained_partitions'],
    'backings': readiness['backing_obligations'],
    'backing_transfer_rule': readiness['backing_transfer_rule'],
    'remaining': ['all physical base congruences', 'O concrete arena/rebase/relation/lifetime',
        'copy micro-stage value lifetimes and complete stage representation',
        'Body external unwind/resume/terminate continuation and callee peaks',
        'all actual backing capacities and healthy final destruction',
        'work prices, every retained quote term and durable root funding',
        'original configuration qualification, runtime admission, FieldLog immutable package use, OTA and GA'],
    'runtime_admission_source_state': 'WholeQuotePending',
    'stage_identity_rule': 'Every distinct physical source/destination copy slot remains distinct; source moves never shorten native reservations or mint new backing identities.',
    'stage_lifetime_rule': 'Frozen native reservation intervals remain known; no copy micro-stage initialized/value lifetime is inferred from only the five abstract phases.'})

def lines(first, last):
    selected = verifier_text.splitlines(keepends=True)
    raw = ''.join(selected[first-1:last]).encode()
    return {'path': source_path, 'line_begin': first, 'line_end_inclusive': last,
            'sha256_of_selected_lines': sha(raw)}

put('schema-assessment.json', {
    'schema': 1, 'status': 'SCHEMA_MISMATCH_NO_COMPLETE_CERTIFICATE_OR_ACTUAL_INVOCATION', **scope,
    'verifier_source': inputs[source_path],
    'root_accepted_verifier_source': verifier_acceptance,
    'selected_geometry_independent_seal': inputs[geometry_seal_path],
    'selected_verifier_independent_seal': inputs[verifier_seal_path],
    'findings': [
        {'id': 'S1', 'source': lines(47, 57),
         'finding': 'ROLES is the closed set R,C,O,FCaller,FClosure,FDispatch,FBody. The intermediate Dispatch13624 and Body13616 physical copy slots have no distinct role identities.'},
        {'id': 'S2', 'source': lines(288, 293),
         'finding': 'semantic_map is a closed object without a storage-stage or copy-edge table. Adding structured stages to the input is rejected as closed object fields.'},
        {'id': 'S3', 'source': lines(336, 342),
         'finding': 'Region roles must be in ROLES and unique. Reusing R/C or a frame role for additional copy stages is rejected, and changing a role target changes its required meaning.'},
        {'id': 'S4', 'source': lines(406, 414),
         'finding': 'return_chain permits exactly Body->Closure R, Closure->Dispatch R and Dispatch->Caller C; only a free-text argument can describe intermediate stages. This does not retain structured stage identities, intervals or lifetimes, and cannot substantiate a complete map.'},
        {'id': 'S5', 'source': lines(358, 379),
         'finding': 'Body normal paths can be recorded while frame.complete=false and nonlocal cleanup/terminate exits stay unresolved. No +63920 restoration step is supported for __Unwind_Resume or panic_in_cleanup.'},
        {'id': 'S6', 'source': lines(406, 414),
         'finding': 'A future explicitly incomplete projection may set affected return_chain.state=unknown; the verifier then records local unresolved sret/PHI/cast/copy. That projection would leave the unsupported copy-stage representation incomplete, and must say so.'},
        {'id': 'S7', 'source': lines(510, 511),
         'finding': 'Any missing scope=local suppresses all closed_local_phase_bytes; current unknown alignment and unknown O also remain blockers. No parser-accepted projection has been produced or executed by this packet.'}],
    'required_distinct_stage_examples': {
        'Dispatch': ['R=%owned at E_D-40968,13624', '%_7 at E_D-13672,13624', '%_6 at E_D-27296,13624', 'C incoming destination at E_C-13840,13640'],
        'Body_loaded': ['%complete at finalSP+21248,13616', '%_58 at finalSP+50192,13616', '%_57 at finalSP+36576,13616', 'incoming R payload13616 then root8'],
        'Body_setup': ['%_13 at finalSP+256,40', '%refused at finalSP+296,40', '%_29 at finalSP+13952,40', '%_28 at finalSP+336,13616', 'incoming R payload13616 then root8']},
    'parent_frame_coverage_does_not_complete_copy_stage_representation': True,
    'scope_of_mismatch': 'Representational completeness of actual physical copy stages, not retained capture identity or proof that existing partial/fail-closed branches are unsafe.',
    'minimal_additive_proposal': 'Add one closed storage_stages object containing expected stage inventory hash, stages with distinct ids, symbolic arenas/offsets/capacities, native reservation and initialized/value lifetime status, copy edges with bounded representation extent and preserved semantic backing ids, and reviewed_complete. reviewed_complete=false or any missing stage/copy/lifetime must emit local missing and suppress all affected numeric claims. Root independently reviews the exact source inventory; input labels cannot self-declare completeness.',
    'changes_to_verifier_made': False, 'certificate_emitted': False,
    'trusted_root_approval_emitted': False, 'independent_semantic_review_claimed': False,
    'actual_input_invocation_selected': False, 'verifier_import_or_invocation_count': 0})

# Recheck only metadata already read; no generated pair, source distribution,
# MIR, interpreter version, verifier import, or fact evaluation is introduced.
for relative, expected in list(inputs.items()):
    raw = (ROOT / relative).read_bytes()
    read_bytes += len(raw)
    if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
        raise RuntimeError('metadata input changed before finalization: ' + relative)
    if read_bytes > LIMIT or time.monotonic()-START > 55:
        raise RuntimeError('metadata posthash bound')

put('preparation-receipt.json', {
    'schema': 1, 'status': 'SOURCE_ONLY_SCHEMA_ASSESSMENT_AND_UNAPPROVED_PROPOSAL', **scope,
    'command': '/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -B verification/swift-retained-partial-certificate-v1/prepare_proposal.py',
    'tool_version_provenance': {'version': plan['python_version_from_this_preparation'], 'source': P + 'swift-root-bound-dispatch-retained-capture-v1/plan.json#python_version_from_this_preparation', 'new_version_probe': False},
    'source146_tree_sha256': binding['source_tree'],
    'inputs': [inputs[key] for key in sorted(inputs)],
    'metadata_read_bytes': read_bytes, 'raw_pair_bytes_read': 0,
    'input_metadata_posthash_unchanged': True,
    'bounds': {'readhash_wall_seconds': 55, 'derived_bytes': LIMIT, 'raw_pair_bytes_if_needed': 128*1024*1024},
    'elapsed_seconds_before_finalization': time.monotonic()-START,
    'outputs': ['schema-assessment.json', 'proposed-input-bindings.json', 'proposed-partial-semantic-map.json', 'proposed-capture-acceptance-envelope.json'],
    'verifier_import_or_invocation_count': 0, 'actual_fact_verification_count': 0,
    'compiler_native_test_process_UI_capture_or_network': False,
    'device_runtime_checks': 'Paused/unrun, pending; no native instance started, cleanup not owed.',
    'product_metadata_existing_packet_edits_commit_or_push': False,
    'root_selection_required_before_any_actual_input_invocation': True,
    'outcome': 'Current closed grammar cannot truthfully encode every required structured copy stage. No complete certificate, semantic signature, approval, or execution was produced.'})

members = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'seal.json':
        raw = path.read_bytes()
        members.append({'path': path.name, 'bytes': len(raw), 'sha256': sha(raw)})
total = sum(m['bytes'] for m in members)
if total > LIMIT or time.monotonic()-START > 55:
    raise RuntimeError('preparation finalization bound')
put('seal.json', {'schema': 1, 'status': 'FROZEN_SOURCE_ONLY_UNAPPROVED_SCHEMA_PROPOSAL',
    'members': members, 'tree_sha256': sha(canonical(members)), 'derived_bytes_without_seal': total,
    'independent_semantic_approval': False, 'root_approval': None, **scope})
print(json.dumps({'status': 'prepared-unapproved-schema-mismatch-packet',
                  'metadata_read_bytes': read_bytes, 'raw_pair_bytes_read': 0,
                  'derived_bytes_without_seal': total,
                  'elapsed_seconds': time.monotonic()-START,
                  'seal_sha256': sha((OUT/'seal.json').read_bytes()),
                  'verifier_invocations': 0}, sort_keys=True))
