"""Bind two frozen editor audits and select only the cleanup design work."""
import datetime, hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, why):
    if not ok: raise ValueError(why)
target = HERE / "design-selection.json"
require(not target.exists(), "Immutable receipt already exists")
packets = []
for folder, index_name, expected, count in [
    ("android-editor-api-boundary-proposal", "manifest.json", "4ad1b8edebf913308484c4600282c5d8af0af00efbc67fa4f75962967b4cc08e", 95),
    ("android-inputconnection-authority-audit", "seal.json", "c7fa78e51d301418479c0d2eab214211ac653800a9c747126e89a0b3b7756e82", 108),
]:
    base = ROOT / "verification" / folder
    index = base / index_name
    require(sha(index) == expected, "Index identity")
    data = json.loads(index.read_text())
    rows = data.get("members") or [dict(path=k, **v) for k, v in data["files"].items()]
    require(len(rows) == count, "Count")
    seen = set()
    for row in rows:
        p = base / row["path"]
        require(p.resolve().is_relative_to(base.resolve()) and not p.is_symlink() and row["path"] not in seen, "Member path")
        seen.add(row["path"])
        require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], row["path"])
    source_map = base / ("source-map.json" if index_name == "manifest.json" else "collection.json")
    source_data = json.loads(source_map.read_text())
    sources = source_data.get("sources") or [dict(path=k, **v) for k, v in source_data["files"].items()]
    for row in sources:
        p = ROOT / row["path"]
        require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], "Current input drift: " + row["path"])
    packets.append({"path": str(index.relative_to(ROOT)), "sha256": expected, "members_verified": count, "bytes": sum(x["bytes"] for x in rows), "current_inputs_verified": len(sources)})
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": sys.argv, "python": sys.version, "selector_sha256": sha(pathlib.Path(__file__)), "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "packets": packets, "third_party_registry_sha256": sha(ROOT / "THIRD_PARTY.yml"), "decision": "Accept source findings and select bounded cleanup/creation/continuation contract design; no adapter implementation selected", "findings": ["38 interface descriptors; current 24 explicit and 14 inherited routes", "Inherited reads/platform subscriptions lack current Mixer entry/return fences", "Widget fences menu action but native batch prefix/suffix remain outside", "No field-local connection incarnation; native close is not universal revocation", "Current immutable setTarget is protected; getHandler target is constant null", "Close old target before successor or quarantine; skipping close does not prove batch cleanup", "Current EditorInfo advertises some refused operations"], "design_scope": ["Exact target and Editable, CLOSING guard, no successor during close", "Serialized CREATING: nested creator refuses before platform super; replaces proposal newest-nested-native-wins rule", "Immediate scalar retirement during native edit; exact captured suffix only and synchronous outermost unwind cleanup", "Narrow Record/renderer continuation and no-event cleanup contract; owner/core/coordinator bytes unchanged", "Preserve ordinary accepted keystrokes, compatible Binding echoes, Editable/selection/composition and healthy connection through temporary seals", "Quarantine plus existing owner retirement/first-fatal precedence on uncertain close", "Resolve getHandler bootstrap calling-thread contract using official caller source"], "ancillary_policy_candidate": "Private extraction nonmonitor only, cursor disable-only, explicit spellcheck false, immutable textbounds unsupported; new restrictions need explicit implementation selection and native qualification", "metadata_policy_candidate": "Clear advertisements for already-refused handwriting gestures/previews; generic stylus input and writing-tools policy require specific review", "native_or_product_implementation_or_GA_accepted": False, "API28_to_35_admission_selected": False, "both_SDK36_guards_preserved": True, "next": "Complete and independently review exact cleanup/creation/continuation contract before isolated actual-source implementation"}
target.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"path": str(target.relative_to(ROOT)), "sha256": sha(target), "members_verified": 203, "packets": packets}))
