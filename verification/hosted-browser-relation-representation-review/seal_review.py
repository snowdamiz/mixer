#!/usr/bin/env python3
"""Seal completed independent evidence and exact owned-resource absence checks."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DOC=ROOT/"docs/hosted-browser-relation-representation-review.md"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def tree(m): return hashlib.sha256("".join(k+"\t"+v+"\n" for k,v in sorted(m.items())).encode()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
commands=[]
def command(label,argv,expected=0):
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    (HERE/(label+".stdout")).write_bytes(p.stdout)
    (HERE/(label+".stderr")).write_bytes(p.stderr)
    commands.append(dict(label=label,argv=argv,cwd=str(ROOT),exit_code=p.returncode,timeout_seconds=30))
    assert p.returncode==expected,(label,p.returncode)
    return p.stdout.decode().strip()

main=load(HERE/"run-receipt.json")
assert main["success"] and main["checks_passed"]==427 and all(main["cleanup"].values())
assert all(c["passed"] for c in load(HERE/"checks.json"))
effects=load(HERE/"mutation-effect-checks.json")
frozen=load(HERE/"frozen-oracle-checks.json")
assert len(effects)==96 and len(frozen)==14 and all(c["passed"] for c in effects+frozen)
assert sha(ROOT/"verification/hosted-browser-relation-representation/receipt.json")==main["producer_receipt_sha256"]
changed={k:dict(at_run=h,current=sha(ROOT/k)) for k,h in main["input_sha256"].items() if sha(ROOT/k)!=h}
assert all(k=="PLAN.md" for k in changed),changed
producer=load(ROOT/"verification/hosted-browser-relation-representation/receipt.json")
cleanup=dict(main["cleanup"])
cleanup["review_scratch_still_absent"]=not Path(main["owned_scratch"]).exists()
for major in (16,17):
    r=load(ROOT/producer["final_attempts"][str(major)]["attempt"]/"receipt.json")
    if major==17:
        cleanup["producer_pg17_scratch_absent"]=not Path(r["owned_scratch"]).exists()
    else:
        command("exact-producer-pg16-container-absence",["docker","container","inspect",r["owned_container"]],expected=1)
        cleanup["producer_pg16_container_absent"]=True
cleanup["owned_python_cache_absent"]=not (HERE/"__pycache__").exists()
assert all(cleanup.values())
revision=command("seal-source-revision",["git","rev-parse","HEAD"])
command("seal-python-version",["python3","--version"])
command("seal-git-version",["git","--version"])
command("seal-docker-version",["docker","--version"])
authored=[DOC]+[HERE/name for name in ("review.py","check_mutation_effects.py","check_frozen_oracle.py","seal_review.py","capture_ordinary_source.exs","linkage.sql")]
lint=[]
for p in authored:
    b=p.read_bytes();text=b.decode()
    assert b.endswith(b"\n") and not b.endswith(b"\n\n") and b"\r" not in b
    assert all(line==line.rstrip() for line in text.splitlines())
    lint.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),passed=True))
write(HERE/"authored-text-lint.json",lint)
refs=["AGENTS.md","PLAN.md","docs/hosted-browser-relation-admission-contract.md","docs/hosted-browser-relation-admission-contract-review.md","docs/hosted-browser-relation-representation.md","verification/hosted-browser-relation-representation/receipt.json","verification/hosted-browser-relation-admission-contract-review/receipt.json","verification/hosted-browser-relation-admission-contract-review/independent-derived-baseline.json","verification/hosted-browser-relation-admission-contract-review/capture_ordinary_source.exs","verification/hosted-browser-relation-admission-contract-review/source-capture.stdout"]
reference_hashes={k:sha(ROOT/k) for k in refs}
artifacts={str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.rglob("*")) if p.is_file() and p.name not in ("receipt.json","seal.stdout","seal.stderr")}
artifacts[str(DOC.relative_to(ROOT))]=sha(DOC)
receipt=dict(schema=1,recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope="Independent development review of selected PG16.15/PG17.11 C-libc relation representation packet only; not runtime admission, Store/owner/readiness, provider, customer, FieldLog, release or GA acceptance.",
    accepted=True,blocking_findings=[],producer_receipt_sha256=main["producer_receipt_sha256"],producer_source_tree_sha256=main["producer_source_tree_sha256"],
    source_revision_at_selected_fixture=main["source_revision"],source_revision_at_seal=revision,
    review_input_tree_sha256=main["input_tree_sha256"],review_input_sha256=main["input_sha256"],
    reference_sha256=reference_hashes,reference_tree_sha256=tree(reference_hashes),
    artifact_sha256=artifacts,artifact_tree_sha256=tree(artifacts),tree_digest_format="sha256 of sorted UTF8 path TAB sha256 LF",
    commands=commands,additional_completed_commands=[
        dict(argv=["python3","verification/hosted-browser-relation-representation-review/review.py"],exit_code=0,environment=dict(PYTHONDONTWRITEBYTECODE="1"),stdout="review.stdout",stderr="review.stderr",inner_commands="run-receipt.json"),
        dict(argv=["python3","verification/hosted-browser-relation-representation-review/check_mutation_effects.py"],exit_code=0,environment=dict(PYTHONDONTWRITEBYTECODE="1"),stdout="mutation-effect.stdout",stderr="mutation-effect.stderr"),
        dict(argv=["python3","verification/hosted-browser-relation-representation-review/check_frozen_oracle.py"],exit_code=0,environment=dict(PYTHONDONTWRITEBYTECODE="1"),stdout="frozen-oracle.stdout",stderr="frozen-oracle.stderr")],
    result=dict(main_assertions=427,mutation_effect_assertions=96,frozen_oracle_assertions=14,producer_real_attacks_independently_checked=47,synthetic_normalization_negative_controls=18,fresh_live_policy_attacks=2,fresh_review_pg_major=17,review_pg16_scope="Independent immutable producer-output audit; no new reviewer PG16 server"),
    coordinator_context_drift_at_run=main["coordinator_context_drift"],post_run_context_drift=changed,
    retained_review_failures=["initial-syntax.stderr","history/context-drift/run-receipt.json","history/noop-negative/run-receipt.json"],
    cleanup=cleanup,delivery=dict(committed=False,pushed=False,coordinator="root"),
    limitations=["Producer collectors/comparators are fixture tools only; no production node/deparse/ACL scalar/decoder/query/aggregate bounds or redacted unavailable behavior qualified.","Fixture canonicalizer excludes environment and uses diagnostic names; runtime requires independent environment checks and numeric same-transaction OID joins.","Only selected C/libc UTF8 environment and fresh index health qualified; other locales/providers/Neon/operational health unqualified.","Owner-coherent rewriting and serialized operator-DDL policy remain outside this fixture boundary."],
    pending=["RelationCatalog implementation and bounded decoder/query adversity","Trusted Store/Repo provenance, same checkout, original end-to-end monotonic clock and rollback composition","Lifecycle readiness, operator/provider/HTTP/console/Neon qualification","Immutable published separate-repository FieldLog packages and customer acceptance","Native/UI/capture tests paused and final physical matrix pending","All specified GA gates and accountable reviewers"])
write(HERE/"receipt.json",receipt)
print(json.dumps(dict(accepted=True,receipt_sha256=sha(HERE/"receipt.json"),artifact_tree_sha256=receipt["artifact_tree_sha256"],cleanup=cleanup)))
