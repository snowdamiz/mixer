#!/usr/bin/env python3
"""Freeze observed correction evidence; preflight runs no PostgreSQL or native work."""
import datetime,hashlib,json,pathlib,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def js(p):return json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    ar=js(HERE/'attempt-1/receipt.json');assert ar['success'];delta=js(HERE/'delta-manifest.json')
    receipt={'schema':1,'status':'correction-ready-for-independent-review','findings':['ACSR01','ACSR02'],'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_source_digest':delta['candidate_source_digest'],'upstream_candidate_source_digest':delta['upstream_source_digest'],'producer_receipt_sha256':sha((HERE/'inputs/producer/receipt.json').read_bytes()),'review_receipt_sha256':sha((HERE/'inputs/review/receipt.json').read_bytes()),'root_direction_sha256':sha((HERE/'inputs/docs/hosted-catalog-wildcard-direction.md').read_bytes()),'expected_manifest_sha256':sha((HERE/'selected-expected.json').read_bytes()),'runtime_attempt':'attempt-1','attempt_receipt_sha256':sha((HERE/'attempt-1/receipt.json').read_bytes()),'fresh_models':{'original126':{'rejected':108,'portable_admitted':18,'historical_malformed_rejected':21},'added_shape':1083,'added_shape_invalid_raw_rejections':1036,'added_shape_valid_unselected_raw_controls':47,'transport':8,'selected_portability':3,'independent_extra':136,'focused':24,'frozen_uniqueness_required_rejections':2,'frozen_uniqueness_portable_control':1,'all_passed':True},'fresh_actual_postgresql':{'clusters':1,'databases':2,'postgres_version':'17.11','oid_padding_tables':107,'targeted_cases':5,'safe_comparisons':11,'selected_drift_rejections':7,'actual_duplicate_trigger_name_SQLSTATE42710_rejections':3,'actual_trigger_name_portability_controls':2,'all_passed':True},'reused_not_freshly_rerun':{'original_schema_cases':128,'prior_controls':43,'historical_findings_not_security_passes':5,'catalog_correction_cases':67,'ordinary_runtime_cases':19,'ordinary_safe_comparisons':23,'ordinary_drift_rejections':15},'source_delta':'Only raw_validation.py: zero OID implies wildcard sentinel; all raw trigger (relation_oid,name) pairs must be unique before normalization. No new resolved-name identifier length rule.','source_SQL_selected_manifest_normalization_and_comparator_unchanged':True,'command_failures_or_discarded_attempts':0,'intentional_SQL_error_observations':3,'cleanup':ar['cleanup'],'independent_correction_review_accepted':False,'root_acceptance':False,'product_startup_inspector':False,'ga_acceptance':False,'limits':['Isolated point-in-time prerequisite; no live hosted/SQL mutation or startup integration.','No malformed actual PostgreSQL catalog or ordinary-runtime authorization bypass demonstrated by either finding.','Original broad schema/runtime counts are reused byte-bound evidence, not newly executed tests.','No concurrent privileged DDL protection or concurrent-drop index-liveness runtime receipt.','Existing nullable_text validation retained; no new identifier-byte bound for resolved startup association names.','No combined domain schema, provider/HTTP, production operation, signing, publication, customer, native or physical-phone qualification.','Physical phones remain disconnected and final acceptance pending.','Independent correction review and accountable root/GA acceptance remain pending.']}
    receipt['command_failures_or_discarded_attempts']=1
    receipt['retained_checker_preflight_failures']=1
    receipt['discarded_attempts']=0
    receipt['runtime_or_model_execution_failures']=0
    save(HERE/'receipt.json',receipt)
    document="""# Catalog wildcard and trigger-name raw-domain correction

The isolated candidate corrects **ACSR01 and ACSR02** in `raw_validation.py`.
A zero startup-association OID requires the `*` sentinel. A positive OID still
requires non-null, nonempty, NUL-free UTF8 resolved text and now permits a literal
`*` name. This preserves the existing text domain without adding an identifier
length rule. Every raw trigger `(relation_oid, name)` pair must be unique before
internal names disappear during normalization. Distinct names on one relation
and the same name on different relations remain portable.

The [exact delta](../verification/hosted-catalog-wildcard-correction/implementation.diff)
changes only that validator. All original SQL, schema, roles, functions, types,
capture queries, assertions, normalization and selected comparison bytes remain
unchanged. Selected manifest SHA-256 remains
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
Candidate source digest is
`3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8`.
The predecessor candidate, receipt and final 115-binding independent review are
preserved and verified; the correction does not rewrite their finding oracles.

Fresh model replay passes all **126 original cases** (108 rejections, including
the prior 21 malformed admissions, and 18 portable OID admissions), **1,083 shape
cases**, **8 transport cases**, **3 selected portability controls**, and **136
independent cases**. The only original expected-oracle changes are two legal
positive-OID `*` startup rows and the cloned same-relation trigger-name row in
each shape matrix. Original scripts and explicit adaptation diffs are retained.
The 1,083 matrix now has 1,036 invalid raw rejections and 47 valid unselected raw
controls. Another **24 focused models** cover both startup association fields,
the frozen two ACSR02 observations and portability. The original review's
separate three-case uniqueness probe also freshly replays with **two required
raw/selected rejections and one selected portability admission**.

One fresh socket-only PostgreSQL **17.11** cluster, with **107 padding tables**
and two owned databases, passed **5 targeted cases** containing **11 safe selected
comparisons and 7 selected drift rejections**. Actual quoted role `"*"` has OID
17024 and quoted database `"*"` has OID 17023. Captured startup rows cover zero
database/role sentinels, positive `*` names, and both positive names together.
Raw validation accepts all legal observations; exact comparison still rejects
the additional reachable role/defaults and ordinary trigger/default drift.
PostgreSQL rejects internal/internal, internal/external and external/external
duplicate trigger names with **SQLSTATE 42710**. Both actual name portability
controls remain selected-safe. The fresh baseline has different OIDs and generated
internal trigger names while normalizing to the identical selected manifest.

The original **128 schema cases**, **43 prior controls**, **5 historical finding
observations**, **67 catalog-correction cases**, and **19 ordinary-runtime cases**
(23 safe comparisons / 15 drift rejections) are **reused byte-bound evidence**;
they were not rerun here. The producer's 277-binding and final review's 115-binding
checkers both pass against their unchanged packets. Historical findings remain
observations, not security passes. Neither finding demonstrates an actual malformed
PostgreSQL catalog or ordinary-runtime authorization bypass.

The [frozen receipt](../verification/hosted-catalog-wildcard-correction/receipt.json),
[command and SQL bindings](../verification/hosted-catalog-wildcard-correction/attempt-1/compression.json),
[runtime observations](../verification/hosted-catalog-wildcard-correction/attempt-1/runtime/tests.json)
and [read-only checker](../verification/hosted-catalog-wildcard-correction/check.py)
retain tool versions/executable hashes, source revision/tree digest, original and
adapted input bytes, full compressed output, SQL and cleanup. The observed HEAD is
`e337ddd14236cc94ede4def750a9fde4c461ad3e`, tree
`09a2ecb36e08d49497f9da82c746789be8f47ea5`, on macOS 27.0.1 arm64 with Python
3.14.8 and libpq 170011. The single runtime attempt and all model executions
succeeded. One checker preflight failed because it compared insertion-order
diagnostic strings after sorted JSON serialization; its source, command, output
and diagnosis are preserved under `checker-preflight-attempt-1/`. The checker now
compares the unchanged rejection group sets. No candidate/runtime byte or outcome
changed, and no attempt was discarded. Three expected SQL errors are assertion evidence.
The owned cluster stopped and unique scratch directory was removed. No TCP
listener, other project's process or data, simulator, emulator or phone was touched.

Run the frozen checker without starting a server:

```sh
python3 -B verification/hosted-catalog-wildcard-correction/check.py
```

Independent correction review and root acceptance remain pending. This isolated
point-in-time prerequisite creates no live hosted/SQL mutation or product startup
authority. Concurrent privileged DDL protection, combined domain schema,
HTTP/provider behavior, production operations, signing/publication, native and
physical-phone qualification and GA acceptance remain pending. Phones remain
disconnected. No dependency, tracker, other active lane, commit or push was changed.
"""
    (ROOT/'docs/hosted-catalog-wildcard-correction.md').write_text(document)
    command={'argv':['python3','-B',str(HERE/'check.py'),'--preflight'],'cwd':str(ROOT),'script_sha256':sha((HERE/'check.py').read_bytes()),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};t=time.monotonic()
    p=subprocess.run(command['argv'],cwd=ROOT,capture_output=True,text=True,timeout=60);command.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,stdout_sha256=sha(p.stdout.encode()),stderr_sha256=sha(p.stderr.encode()),seconds=time.monotonic()-t)
    # A failed preflight is never overwritten or hidden by a later repair.
    path=HERE/'checker-preflight-command.json';assert not path.exists();save(path,command)
    if p.returncode:print(json.dumps(command,indent=2));return p.returncode
    files=[p for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json']+[ROOT/'docs/hosted-catalog-wildcard-correction.md']
    save(HERE/'artifact-manifest.json',{'schema':1,'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(files)]})
    print(json.dumps({'sealed':True,'bindings':len(files),'receipt_sha256':sha((HERE/'receipt.json').read_bytes()),'candidate_source_digest':delta['candidate_source_digest']},indent=2));return 0
if __name__=='__main__':sys.exit(main())
