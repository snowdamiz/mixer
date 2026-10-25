#!/usr/bin/env python3
"""Seal exact standalone component evidence and explicit contract coverage."""
import datetime as dt,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((R/p).read_text())
def write(p,data):p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def tree(m):return hashlib.sha256(''.join(p+'\t'+h+'\n' for p,h in sorted(m.items())).encode()).hexdigest()
selected={16:'20261025T190443.947254Z-pg16-df9dcb',17:'20261025T190528.301940Z-pg17-a1a1de'}
checks={major:read(f'verification/hosted-browser-relation-catalog/attempts/{name}/checks.json')['checks'] for major,name in selected.items()}
mapping={
'T01':(['no transaction rejects','role shape:','actual session identity mismatch denies'],'partial_pending_owner','No trusted Store provenance, foreign/nested owner context or request-selected Repo admission is implemented.'),
'T02':(['original expired deadline','future budget','original remaining deadline checked after every query'],'partial_pending_owner','Entry/each-query expiry passes; separately timed decoding/final-return expiry and checkout-through-commit rollback remain pending.'),
'T03':(['all query timeouts monotonically','driver failure redacted','cancellation redacted'],'partial_pending_owner','Wire seam asserts positive remaining timeouts, queue:false, log:false and no retry. Real pool exhaustion/server cancellation and owner checkout remain pending.'),
'T04':(['actual session identity mismatch','transaction policy:','actual mutation: writer LOGIN flag'],'component_controls_passed','Current same-backend session, role flags and transaction policy are checked; complete function/owner conjunction is separate.'),
'R01':(['actual mutation: relation owner','actual mutation: extra browser view any schema','wire family 2:'],'component_controls_passed','Actual owner/extra-namespace controls and typed relation-family controls; no exhaustive DDL variant claim.'),
'R02':(['actual mutation: inheritance edge','actual mutation: rewrite rule','actual mutation: unlogged relation','actual mutation: external foreign table'],'component_controls_passed','These actual variants pass; partition/typed/temp replacement variants are structurally rejected but not all individually recreated.'),
'R03':(['actual mutation: disabled FORCE RLS','actual lifecycle-login baseline'],'component_controls_passed','ENABLE/FORCE fields are both exact; the live negative explicitly disables FORCE.'),
'R04':([],'pending_operator_policy','Serialized operator-DDL policy and coherent owner rewriting are external operational responsibilities.'),
'C01':(['actual mutation: extra column','actual mutation: dropped column slot','wire family 3:'],'component_controls_passed','Ordered exact columns/contiguous ordinals and typed count/shape controls; no exhaustive reorder DDL claim.'),
'C02':(['actual mutation: changed collation','wire family 3:'],'component_controls_passed','Exact builtin type/OID joins, typmod/dimensions/collation comparison implemented; not every domain/type DDL variant is separately executed.'),
'C03':(['actual mutation: changed NOT NULL','actual mutation: changed default','actual mutation: missing default'],'component_controls_passed','NOT NULL/default variants run live; identity/generation remain exact structural comparisons.'),
'C04':(['actual mutation: changed default','actual mutation: missing default','actual lifecycle-login baseline'],'component_controls_passed','All three default expressions are source-bound; actual removal/change controls pass.'),
'C05':(['actual mutation: corrupt bigint fast default','actual rewrite clears admitted bigint fast defaults'],'component_controls_passed','Both original {1} and actual absent-after-rewrite forms pass; bigint {2} fails on each major.'),
'K01':(['actual mutation: extra check','actual mutation: weakened check','wire family 4:'],'component_controls_passed','Complete 80-CHECK multiset and 109-boundary cardinality are exact.'),
'K02':(['actual mutation: weakened check','actual mutation: oversized deparse output','actual mutation: oversized source node'],'component_controls_passed','All 80 literal expressions compare exactly; selected live semantic weakening and expression bounds are exercised.'),
'K03':(['actual mutation: same-named custom equality','actual mutation: unvalidated FK','actual mutation: deferred FK','actual mutation: CHECK dependency keys','actual mutation: constraint key vector 33 entries'],'component_controls_passed','Exact target/key/action/operator vectors are compared; selected actual operator/enforcement/vector mutations pass.'),
'K04':(['actual mutation: wrong FK referenced index','automatic constraint and backing-index rename equivalence'],'component_controls_passed','Numeric PK/UNIQUE/FK index backlinks and ordered keys are checked; automatic diagnostic names remain equivalent.'),
'K05':(['actual lifecycle-login baseline','wire family 4:','wire family 6:'],'component_controls_passed','Four user constraint rows link one-to-one to their four deferred triggers; no separate live removal-only control.'),
'K06':(['actual mutation: disabled child RI','actual mutation: disabled parent RI','actual mutation: wrong RI opposite endpoint'],'component_controls_passed','All twelve FK groups/48 RI triggers and both endpoints are checked on each major.'),
'I01':(['actual mutation: extra index','actual mutation: missing partial index','actual mutation: partial index explicit name','automatic constraint and backing-index rename equivalence'],'component_controls_passed','Complete fourteen indexes; explicit partial name exact, generated names ignored.'),
'I02':(['actual mutation: weakened partial predicate'],'component_controls_passed','Removing claimed from the exact predicate is independently observed and denied.'),
'I03':(['actual mutation: invalid index','actual mutation: index checkxmin','wire family 5:'],'component_controls_passed','All health flags are decoded/exact; selected invalid/xmin states run live. No operational transition is qualified.'),
'I04':(['actual mutation: wrong opclass family','actual mutation: changed collation','wire family 5:'],'component_controls_passed','Key/opclass/family/input/collation numeric identity/options/linkage exact; not every index DDL variant is recreated.'),
'G01':(['actual mutation: disabled user trigger','actual mutation: user trigger explicit name','wire family 6:'],'component_controls_passed','All trigger enablement must be O; selected actual user-trigger controls pass.'),
'G02':(['actual mutation: wrong RI opposite endpoint','wire family 6:'],'component_controls_passed','Event/argument/filter/WHEN/transition/clone fields are exact; every user-trigger variant is not separately recreated.'),
'G03':(['actual lifecycle-login baseline','wire family 6:'],'component_controls_passed','Four user triggers are deferred with exact constraint linkage; separate live deferral-only corruption remains unrun.'),
'G04':(['actual mutation: changed trigger body','actual mutation: changed trigger configuration','actual mutation: trigger PUBLIC execution'],'partial_pending_function_owner_join','Relation checker resolves exact four function OIDs/source/config/owner/ACL. Complete eighteen-function/type prerequisite and same-owner conjunction remain separate.'),
'P01':(['actual mutation: extra permissive policy','actual mutation: extra restrictive policy','wire family 7:'],'component_controls_passed','Complete32-policy multiset, commands/permissiveness/roles/NULL/expression fields compare exactly.'),
'P02':(['actual mutation: extra permissive policy','actual mutation: writer policy to PUBLIC'],'component_controls_passed','PUBLIC-target OR widening is denied with the original policies present.'),
'P03':(['actual mutation: writer policy to PUBLIC','wire scalar: policy role vector overrun'],'component_controls_passed','Exact singleton numeric role vectors and source policy fields are checked.'),
'P04':(['actual mutation: policy false to true','actual mutation: policy false to NULL'],'component_controls_passed','All ordinary source-compiled predicates compare byte-for-byte, preserving NULL/false/true.'),
'P05':(['actual mutation: extra permissive policy','actual mutation: extra restrictive policy'],'component_controls_passed','Every unexpected name is rejected; directory_read itself is not separately created by this suite.'),
'P06':(['actual mutation: writer policy to PUBLIC','actual mutation: policy false to true','actual mutation: policy false to NULL'],'component_controls_passed','Writer singleton targets and USING/CHECK states are source-bound.'),
'A01':(['actual mutation: lifecycle direct SELECT','actual mutation: PUBLIC relation SELECT','wire family 9:','wire family 10:'],'component_controls_passed','Raw and effective all-token table/column denial; selected actual grants pass.'),
'A02':(['actual mutation: writer extra table UPDATE','actual mutation: writer immutable column UPDATE','actual mutation: writer grant option','actual mutation: PG17 application MAINTAIN'],'component_controls_passed','PG17-specific MAINTAIN mutation runs only on PG17; all other listed controls run on both.'),
'A03':(['actual mutation: missing writer INSERT','actual lifecycle-login baseline','wire family 8:','wire family 10:'],'component_controls_passed','Exact SELECT/INSERT/mutable-column raw and effective matrices checked.'),
'A04':(['actual mutation: ordinary browser SELECT','wire family 9:','wire family 10:'],'component_controls_passed','Ordinary browser denial and five authz SELECT rights exact; not each authz mutation grant is independently applied.'),
'A05':(['actual mutation: PUBLIC relation SELECT','actual mutation: third-party role SELECT','actual mutation: raw ACL grantor','actual mutation: writer grant option'],'component_controls_passed','Raw grantor/grantee/token/grant-option tuples and owner/application separation are exact.'),
'A06':(['actual mutation: external membership SELECT','actual mutation: external membership column UPDATE','actual mutation: external writable view','actual mutation: external foreign table','actual mutation: external sequence USAGE','actual mutation: schema CREATE escape','actual mutation: role membership escape'],'partial_pending_function_owner_join','Relation/schema/column/sequence escapes close here. Full SECURITY DEFINER/type/role-topology composition remains the separate prerequisite and trusted owner responsibility.'),
'V01':(['actual lifecycle-login baseline','automatic constraint and backing-index rename equivalence','actual rewrite clears admitted bigint fast defaults'],'component_controls_passed','Both selected major fixtures independently install the same explicit nine source migrations and match fixed reviewed expressions; no runtime oracle learning.'),
'V02':(['actual mutation: oversized deparse output','actual mutation: changed trigger body'],'component_controls_passed','Whitespace literal survives into separate output-bound control; expressions and function source use exact equality without normalization.'),
'V03':(['wire scalar: unsupported major','actual mutation: PG17 application MAINTAIN'],'component_controls_passed','PG16 executes no MAINTAIN probe; unknown raw tokens differ from its exact source matrix. Real unsupported server is not started.'),
'V04':(['actual mutation: same-named custom equality','actual mutation: wrong opclass family','actual mutation: wrong RI opposite endpoint','all four configured role names are parameterized'],'component_controls_passed','Numeric OID joins resolve qualified builtin identities; configured names are not frozen fixture identities.'),
'V05':(['wire family','wire scalar:','actual mutation: ACL 65 entry scalar cap','actual mutation: ACL 16KiB scalar cap','actual mutation: constraint key vector 33 entries','actual mutation: oversized source node','actual mutation: oversized deparse output','aggregate decoded wire over 2MiB'],'component_controls_passed','All twelve result families have cap+one/NULL/shape/kind/backend/message/fault controls, plus actual scalar/node/output bounds. Not all exhaustive combinations are claimed.'),
'J01':([],'pending_trusted_owner','No trusted Store/readiness/route composition exists in this slice; neither prerequisite atom independently authorizes it.'),
'J02':(['actual lifecycle-login baseline','actual mutation: changed trigger body'],'pending_trusted_owner','Same-backend numeric trigger joins are implemented locally; future Store must compose the complete function prerequisite on its checkout.'),
'J03':([],'pending_function_version_selection','No v2 function/type selection is made by this original-nine relation checker. Root owns the separate additive selection.'),
'J04':(['driver failure redacted','cancellation redacted','actual lifecycle-login baseline'],'partial_pending_owner_rollback','Production performs only bounded catalog SELECTs and returns redacted failures. Live mutation rollback is fixture isolation, not trusted Store rollback/readiness qualification.')
}
matrix=read('verification/hosted-browser-relation-admission-contract/runtime-adversity-matrix.json')
assert set(mapping)=={c['id'] for c in matrix} and len(matrix)==48
coverage=[]
for case in matrix:
 patterns,status,note=mapping[case['id']]
 evidence={}
 for major,methods in checks.items():
  names=[c['name'] for c in methods if any(p in c['name'] for p in patterns)]
  if patterns and not names:raise AssertionError(case['id'])
  evidence[str(major)]=names
 coverage.append(dict(case,original_status=case['status'],status=status,component_methods=evidence,limitations=note,independent_review='pending'))
write(B/'coverage.json',{'schema':1,'scope':'48 exact original cases mapped; component coverage is not full owner/runtime acceptance','cases':coverage,'full_contract_cases_claimed_passed':0})
selected_receipts=[]
for major,name in selected.items():
 path=B/'attempts'/name/'receipt.json';data=json.loads(path.read_text())
 assert data['success'] and not data['source_changes'] and not data['dependency_changes'] and all(data['cleanup'].values())
 assert all(sha(R/p)==h for p,h in data['source_sha256'].items()),'selected runtime source drift'
 assert all(sha(R/p)==h for p,h in data['dependency_sha256'].items()),'selected dependency drift'
 assert all(sha(path.parent/p)==h for p,h in data['output_sha256'].items()),'selected output drift'
 effects=json.loads((path.parent/'mutation-effects.json').read_text())
 assert len(effects)==(65 if major==16 else 66) and all(e['observed'] is True for e in effects)
 selected_receipts.append({'major':major,'path':str(path.relative_to(R)),'sha256':sha(path),'source_tree_sha256':data['source_tree_sha256'],'dependency_tree_sha256':data['dependency_tree_sha256'],'methods':len(checks[major]),'actual_mutations':len(effects),'cleanup':data['cleanup']})
assert selected_receipts[0]['source_tree_sha256']==selected_receipts[1]['source_tree_sha256']
assert selected_receipts[0]['dependency_tree_sha256']==selected_receipts[1]['dependency_tree_sha256']
retained=[]
cleanup={}
for path in sorted((B/'attempts').glob('*/receipt.json')):
 data=json.loads(path.read_text())
 assert all(data['cleanup'].values())
 if 'owned_scratch' in data:assert not Path(data['owned_scratch']).exists()
 cleanup[path.parent.name]=data['cleanup']
 if path.parent.name not in selected.values():
  retained.append({'path':str(path.relative_to(R)),'sha256':sha(path),'success':data['success'],'failure':data.get('failure'),'cleanup':data['cleanup']})
for name in ['initial-warning-compile.json','check-key-edit-format-failure.json','format-compile.json']:
 data=json.loads((B/name).read_text())
 assert all(data['cleanup'].values())
 for command in data['commands']:
  cwd=Path(command['cwd'])
  if 'mixer-relation-catalog-format-' in cwd.name:assert not cwd.exists()
cleanup['formatter_compiler_scratch_absent']=True
# Exact known container absence only; no process or fleet discovery.
pg16=json.loads((R/selected_receipts[0]['path']).read_text())
cmd=['docker','container','inspect',pg16['owned_container']]
probe=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
(B/'seal-container-absence.stdout').write_text(probe.stdout)
(B/'seal-container-absence.stderr').write_text(probe.stderr)
assert probe.returncode!=0
cleanup['selected_pg16_container_still_absent']=True
# Source-oracle derivation audit without running its generator or changing products.
accept=read('verification/hosted-browser-relation-representation-review/root-acceptance.json')
review_path='verification/hosted-browser-relation-representation-review/receipt.json'
review=read(review_path)
assert sha(R/review_path)==accept['review_receipt_sha256']
capture='verification/hosted-browser-relation-representation-review/ordinary-source-capture.stdout'
assert sha(R/capture)==review['artifact_sha256'][capture]
for packet in accept['producer_packets']:
 data=read(packet['receipt']);base=Path(packet['receipt']).parent
 assert sha(R/packet['receipt'])==packet['receipt_sha256']
 for name in ['source-compiled-oracle.json','clean-baseline.json']:
  assert sha(R/base/name)==data['outputs_sha256'][name]
static_files=['hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex','hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex',
'hosted/priv/browser_auth/relation_surface_v1_pg16.json','hosted/priv/browser_auth/relation_surface_v1_pg17.json',
'docs/hosted-browser-relation-catalog.md']
static_files += [str(p.relative_to(R)) for p in sorted(B.iterdir()) if p.is_file() and p.name!='receipt.json']
bindings={p:sha(R/p) for p in static_files}
receipt={'schema':1,'recorded_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'component-candidate-awaiting-independent-review','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'scope':'Bounded RelationCatalog original-nine prerequisite only; no function/Store/readiness/GA admission',
'selected':selected_receipts,'artifact_sha256':bindings,'artifact_tree_sha256':tree(bindings),'retained_nonselected_attempts':retained,
'retained_tooling_attempts':['initial-warning-compile.json','check-key-edit-format-failure.json'],
'format_compile':{'path':'verification/hosted-browser-relation-catalog/format-compile.json','sha256':sha(B/'format-compile.json'),'actual_mix_formatter':True,'selected_elixirc_warnings_as_errors':True},
'cleanup':cleanup,'cleanup_command':{'command':cmd,'exit':probe.returncode},
'coverage':{'cases':48,'fully_accepted_runtime_cases':0,'file':'verification/hosted-browser-relation-catalog/coverage.json'},
'pending':['Independent review','Complete function/type prerequisite conjunction through trusted Store and exact Repo/checkout/role provenance','Original checkout-through-commit deadline, nested/foreign Store rejection and actual Store rollback','Actual pool-pressure/server cancellation; separately timed decoding/final-return expiry controls','Serialized operator DDL, non-C locale/provider/index health and Neon qualification','Lifecycle/provider/HTTP/console readiness, immutable published external FieldLog packages, customer and GA acceptance','Native/UI/capture and final physical checks remain paused/pending'],
'limitations':['Method counts overlap; source/fixture/wire seam coverage is not 48 completed contract cases.','Fixture superuser mutations are transaction-local with independent named effects; unchanged identical context and genuine lifecycle baseline pass. This is not Store ownership proof.','Wire seam injects driver errors/cancellations and malformed actual result copies; it does not simulate real pool exhaustion/server cancellation.','Pinned Oban source files are required at compilation. Production never reads verification files or filesystem state.','All product and test files match both selected final receipts. No commits or pushes by this lane.']}
write(B/'receipt.json',receipt)
print(json.dumps({'status':receipt['status'],'selected':selected_receipts,'artifact_tree_sha256':receipt['artifact_tree_sha256'],'retained_nonselected':len(retained),'cleanup':cleanup},indent=2))
