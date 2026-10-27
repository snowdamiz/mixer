#!/usr/bin/env python3
"""Bounded source/data audit of frozen preparation. No Rust or native execution.

These source checks support review; they do not prove control-flow semantics or
authorize validation, adoption, export, execution, publication, or a GA gate.
"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import platform
import re
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
PREP = OUT.parent / "swift-guarded-snapshot-export-preparation"
SOURCE = PREP / "inputs/accepted-source/vm"
EXPECTED_SEAL = "7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe"
READS = {}
CONTROLS = []


def read(relative):
    path = PREP / relative
    data = path.read_bytes()
    READS[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return data.decode()


def check(name, condition, observation):
    assert condition, name
    CONTROLS.append({"name": name, "passed": True, "observation": observation})


def struct_fields(text, name):
    body = re.search(r"\bstruct " + re.escape(name) + r"\s*\{(.*?)\n\}", text, re.S).group(1)
    return re.findall(r"(?:^|,)\s*(?:pub\s+)?(\w+)\s*:", body)


manifest = json.loads(read("inputs/source-manifest.json"))
member_rows = []
for member in manifest["members"]:
    path = SOURCE / member["path"]
    data = path.read_bytes()
    assert len(data) == member["bytes"], member["path"]
    assert hashlib.sha256(data).hexdigest() == member["sha256"], member["path"]
    member_rows.append(member)
tree = hashlib.sha256(json.dumps(member_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
seal_sha = hashlib.sha256((PREP / "seal.json").read_bytes()).hexdigest()
check("released seal and accepted original source manifest",
      seal_sha == EXPECTED_SEAL and len(member_rows) == 144 and tree == manifest["tree_sha256"],
      {"producer_seal_sha256": seal_sha, "source_members": 144, "source_tree_sha256": tree})

loader = read("inputs/accepted-source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs")
swift = read("inputs/accepted-source/vm/src/experimental/swift.rs")
descriptor = read("inputs/accepted-source/vm/src/experimental_wasi/descriptor.rs")
control = read("inputs/accepted-source/vm/src/experimental_swift_reactor/control.rs")
wasi = read("inputs/accepted-source/vm/src/experimental_wasi/mod.rs")
guard = read("inputs/accepted-source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs")
bridge = read("prototype/validator_bridge.rs")
runner = read("run_preparation.py")
contract = read("contract.md")
read("format_model.py")

spec = importlib.util.spec_from_file_location("frozen_preparation_format", PREP / "format_model.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

check("actual loader IDs and five-limit validation binding",
      'header(b, b"MIXLBD01", Role::Build, BUILD_CAP)?' in loader
      and 'header(b, b"MIXLSE01", Role::Session, SESSION_CAP)?' in loader
      and 'if s.budget != budget {' in loader,
      {"actual_loader_ids": ["MIXLBD01", "MIXLSE01"], "observation_ids": ["MIXLPR01", "MIXRTB01"],
       "actual_session_budget": "SwiftValidationBudget; not the 17-field SwiftRunBudget"})

identity_array = re.search(r"let identities = \[(.*?)\n    \];", loader, re.S).group(1)
roles = re.findall(r"identity\(.*?Role::(\w+)", identity_array, re.S)
check("actual session first section binds Source identity",
      roles == ["Source", "Build", "Session", "Executable"]
      and 's.sections[0].bytes != identities[0].encode() || s.source_bytes != identities[0].bytes' in loader,
      {"identity_roles": roles, "session_first_section_role": "Source", "finding": "B01"})

check("canonical retained preimages and independent nonce comparison",
      all(token in loader for token in [
          'platform::hash(b.sections[i].bytes, usage)? != b.digests[i]',
          'platform::hash(s.sections[i].bytes, usage)? != s.digests[i]',
          'let build_digest = platform::hash(&build, usage)?;',
          'let session_digest = platform::hash(&session, usage)?;',
          'session_digest != observed.expected_session', 's.nonce != observed.nonce',
          's.build != build_digest', 's.executable != executable_digest',
          's.source != source_digest', '!source_bytes_equal(&proof, &input)',
          'final_metadata_recheck_v1(files, &identities)?;',
          'order is lexicographic key bytes, duplicate keys refuse, no UTF8 conversion.'
      ]),
      {"source": "SHA256 complete retained source and full equality against proof source",
       "manifest": "SHA256 complete manifest bytes, compared with embedded compile identity",
       "build": "SHA256 complete MIXLBD01 artifact", "session": "SHA256 complete MIXLSE01 artifact",
       "executable": "SHA256 complete retained executable bytes",
       "nonce": "32 retained observed bytes; direct equality, not a hash or signature",
       "build_header_digest_order": ["manifest", "command", "compile_environment", "compiler_version", "compiler", "executable"],
       "compiled_identity_order": ["manifest", "command", "compile_environment", "compiler", "compiler_version"],
       "limits": "trusted quiescent local process correlation; no package authentication or File-close proof"})

provenance_fields = struct_fields(loader, "LoaderProvenanceV1")
expected_provenance = ["validation_budget", "source_extent", "source", "manifest", "build", "session", "executable", "nonce", "identities"]
check("MIXLPR01 source-backed retained-field and identity order",
      provenance_fields == expected_provenance
      and all(f"self.{name} as u64" in loader for name in ["mtime", "mtime_ns", "ctime", "ctime_ns"])
      and '[self.source,self.manifest,self.build,self.session,self.executable,self.nonce]' in runner
      and 'self.identities.map(FileIdentityV1::encode)' in runner,
      {"provenance_fields": provenance_fields, "wire_bytes": 576,
       "file_fields": f.FILE_FIELDS, "negative_i64_example_wire_word": (-1) & f.U64,
       "no_added_provenance_field": True})

enum_all = re.search(r"pub const ALL: \[Self; 34\] = \[(.*?)\n    \];", descriptor, re.S).group(1)
names = re.findall(r"Self::(\w+)", enum_all)
proof_fields = struct_fields(swift, "ValidatedSwiftReactor")
check("six private proof fields and exact 34 import wire identities",
      proof_fields == ["source", "metadata", "policy", "imports", "usage", "observations"]
      and len(names) == 34 and len(set(names)) == 34
      and 'if actual != expected {' in swift
      and 'resolved[index] = actual;' in swift
      and 'Implementation must use an exhaustive match on each actual' in contract,
      {"proof_fields": proof_fields, "wire_imports": [{"wire_id": i + 1, "variant": name} for i, name in enumerate(names)],
       "authority_boundary": "Resolved IDs are observations of actual proof.imports; recognized mutated IDs do not issue a proof"})

check("separate validation/runtime/WASI field orders",
      f.VALIDATION_LIMITS == struct_fields(swift, "SwiftValidationBudget")
      and f.RUN_LIMITS == struct_fields(control, "SwiftRunBudget")
      and f.WASI_LIMITS == struct_fields(wasi, "WasiBudget")
      and f.GRANTS == struct_fields(wasi, "WasiGrants"),
      {"validation_limits": f.VALIDATION_LIMITS, "run_limits": f.RUN_LIMITS,
       "WASI_limits": f.WASI_LIMITS, "grant_booleans": f.GRANTS,
       "implemented_runtime_observation_accessor": False,
       "distinction": "Actual validation and later actual runtime grants are separate records; source declarations alone do not establish same-owner binding"})

outcome_text = re.search(r"enum InitialProfileConstructionOutcomeV1 \{(.*?)\n\}", guard, re.S).group(1)
variants = re.findall(r"^\s+(\w+)\s*\{(.*?)\}\s*=(\d+),", outcome_text, re.M)
expected_names = ["SlotOccupied", "SelectionRefused", "PreparationFailed", "ConstructionFailed", "PhaseCompletionFailed", "HeaderRefused", "HeaderOwnerCheckFailed", "HeaderEncoded"]
positions = [guard.index(token) for token in [
    'if let Err(failure)=phase.complete((preparation,original_return))',
    'let scalars=match inspect_initial_v1(cache,control,wasi)',
    'let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };',
    'let header=match encode_profile_header_v1(&initial,claims)',
    'let rows=write_initial_profile_rows_v1(&initial,row_output);'
]]
check("sole original guard and unchanged eight typed outcomes/order",
      [name for name, _, _ in variants] == expected_names
      and [int(n) for _, _, n in variants] == list(range(1, 9))
      and guard.count('let initial=InitialProfileBorrowV1 {') == 1
      and positions == sorted(positions),
      {"outcomes": [{"id": int(n), "variant": name, "inline_payload": payload} for name, payload, n in variants],
       "source_order": ["phase completion", "initial inspection", "sole guard", "header encoding", "row writing"],
       "new_outer_observation": "proposed only; no current constructor body change or export hook"})

check("guard-bounded callback-free private bridge remains preparation-only",
      "initial: &'guard InitialProfileBorrowV1<'_>" in bridge
      and "Result<LogicalSnapshotViewV1<'guard>,PreparationErrorV1>" in bridge
      and "initial.preparation_selected_v1().ok_or(PreparationErrorV1::MissingSelected)?" in bridge
      and "proof:initial.preparation_proof_v1(),provenance" in bridge
      and 'self.cache.adopted.selected_provenance()' in runner
      and 'Err(PreparationErrorV1::PreparationOnly)' in bridge
      and 'FnOnce' not in bridge and 'FnMut' not in bridge and 'unsafe' not in bridge,
      {"entry": "&InitialProfileBorrowV1; no replacement guard, digest/bool, arbitrary proof, provenance or callback argument",
       "references": "bounded by guard borrow; selected provenance derives from same cache's AdoptedProof",
       "current_successful_exporter": False, "current_MIXRTB01_same_owner_join": False,
       "limitation": "source review only; independent main reviewer owns compiler/privacy matrix"})

result = {
    "schema": 1, "scope": "independent frozen binding/encoding source review; no product selection",
    "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": "python3 verification/swift-guarded-snapshot-export-binding-review/review_binding.py",
    "tool": {"python": sys.version, "implementation": platform.python_implementation()},
    "controls": CONTROLS, "read_members": READS,
    "not_run": ["producer wrapper", "Rust program", "compiler privacy matrix", "native/device/simulator/emulator runtime", "UI or capture", "process inventory"],
    "writes": "only this new review directory",
}
(OUT / "audit-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
summary = json.dumps({"controls_passed": len(CONTROLS), "findings": ["B01"], "producer_seal_sha256": seal_sha, "source_tree_sha256": tree}, sort_keys=True) + "\n"
(OUT / "stdout").write_text(summary)
(OUT / "stderr").write_text("")
(OUT / "command-receipt.json").write_text(json.dumps({
    "command": result["command"], "tool": result["tool"], "exit_code": 0,
    "source_tree_sha256": tree, "producer_seal_sha256": seal_sha,
    "stdout": "stdout", "stderr": "stderr", "scope": result["scope"],
}, indent=2, sort_keys=True) + "\n")
print(summary, end="")
