#!/usr/bin/env python3
"""Independent frozen-data cross-checks; no Java/product/native/build execution."""
import copy
import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / "android-editor-integration-protocol"
EXPECTED_SEAL = "2338ce170833c7a33d797d46a6d51d50e3b24398ed05b2b8b2129dafb35eb89f"
STATES = {"current", "successor", "terminal", "dirty", "stale", "fatal"}
FAMILIES = {
    "beginBatchEdit": ("beginBatchEdit", False),
    "endBatchEdit": ("endBatchEdit", False),
    "clearMetaKeyStates": ("clearMetaKeyStates", False),
    "commitText": ("commitText", True),
    "commitTextWithAttributes": ("commitTextWithAttributes", True),
    "setComposingText": ("setComposingText", True),
    "setComposingTextWithAttributes": ("setComposingTextWithAttributes", True),
    "setComposingRegion": ("setComposingRegion", False),
    "setComposingRegionWithAttributes": ("setComposingRegion", False),
    "finishComposingText": ("finishComposingText", False),
    "deleteSurroundingText": ("deleteSurroundingText", True),
    "deleteSurroundingTextInCodePoints": ("deleteSurroundingTextInCodePoints", True),
    "setSelection": ("setSelection", False),
    "performEditorAction": ("performEditorAction", True),
    "setImeConsumesInput": ("setImeConsumesInput", False),
    "commitCompletion": ("commitCompletion", True),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": digest(data)}


def load(name):
    return json.loads((INPUT / name).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def projection(files):
    return digest("".join(path + "\0" + files[path]["sha256"] + "\n"
                          for path in sorted(files)).encode())


def validate_family_data(design):
    rows = design["families"]
    names = [row["family"] for row in rows]
    require(len(names) == len(set(names)) == 16 and set(names) == set(FAMILIES), "exact family set")
    require(design["designed_state_rows"] == 96, "design row count")
    for row in rows:
        leaf, natural = FAMILIES[row["family"]]
        require(row["counted_leaf"] == "BaseInputConnection." + leaf, "exact counted leaf")
        require(set(row["cases"]) == STATES, "six distinct states")
        require(row["ordinary_can_publish_successor"] is natural, "natural callback classification")
        require(row["successor_is_injected_feature_event"] is (not natural), "injection classification")
        require(row["watchers_suppressed"] is False and row["listener_removed"] is False,
                "callbacks must remain enabled")
        require(row["new_transport_leaf_mode"] is None, "no suppression leaf mode")
    require(design["append_contract"]["initial_selection"] == [0, 0], "default selection")
    require(design["separate_invalid_entry"]["changing"] is True, "changing-only invalid-entry control")
    require(design["sendKeyEvent"]["accepted"] is False and
            set(design["sendKeyEvent"]["all_states"]) == STATES, "sendKey direct refusal")


def main():
    groups = []
    require(identity(INPUT / "seal.json")["sha256"] == EXPECTED_SEAL, "assigned seal")
    seal = load("seal.json")
    members = {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in seal["members"]}
    require(len(members) == len(seal["members"]) == 657, "member count/uniqueness")
    actual = {str(path.relative_to(INPUT)) for path in INPUT.rglob("*") if path.is_file()}
    require(actual == set(members) | {"seal.json"}, "frozen file closure")
    require(not any(path.is_symlink() for path in INPUT.rglob("*")), "frozen symlink")
    for name, expected in members.items():
        require(identity(INPUT / name) == expected, "member " + name)
    require(sum(row["bytes"] for row in members.values()) == 7_527_003, "member bytes")
    custody_path = HERE.parent / "android-editor-boundary-root-review/integration-protocol-custody.json"
    require(identity(custody_path)["sha256"] == "84e7d7b5538d7894459fef493f157d19685bb8cfb010790612f641d983c8f8b3", "root custody identity")
    custody = json.loads(custody_path.read_text())
    require((custody["seal_sha256"], custody["members_verified"], custody["bytes_verified"]) ==
            (EXPECTED_SEAL, 657, 7_527_003), "root custody agreement")
    focus = HERE.parent / "android-editor-focus-history-independent/actual-review"
    require(identity(focus / "review-seal.json")["sha256"] == "69e1f6a02702e5a4181cbb6ff76263301d499e8853115c7059bb39e0c393dcb8", "focus review seal")
    focus_seal = json.loads((focus / "review-seal.json").read_text())
    focus_row = next(row for row in focus_seal["members"] if row["path"] == "review.md")
    require(identity(focus / "review.md") == {key: focus_row[key] for key in ("bytes", "sha256")}, "focus review text identity only")
    groups.append("657-member exact closure and 7527003-byte custody")

    manifest = load("input-manifest.json")
    require(len(manifest) == 602, "copied input count")
    for name, expected in manifest.items():
        require(identity(INPUT / "inputs" / name) == {key: expected[key] for key in ("bytes", "sha256")},
                "copied identity " + name)
    groups.append("602 copied input identities")

    current = load("current-profile4.json")
    proposed = load("proposed-profile5.json")
    require(current["id"] == "mixer.android-source-pair.4" and proposed["id"] == "mixer.android-source-pair.5", "profile IDs")
    require(proposed["root_acceptance"] is None and proposed["candidate_binding"]["acceptance"].startswith("pending"), "unselected binding")
    for kind, old_count, new_count in (("sdk", 22, 22), ("adapter", 23, 24)):
        for profile, count in ((current, old_count), (proposed, new_count)):
            files = profile[kind + "_files"]
            require(len(files) == count and projection(files) == profile[kind + "_compatibility_sha256"], "profile projection " + kind)
        for relative, expected in current[kind + "_files"].items():
            prefix = "sdk/" if kind == "sdk" else "native/android/" + ("engine/" if relative.startswith("Sources/") else "")
            require(identity(INPUT / "inputs/repo" / (prefix + relative)) == expected, "current source " + relative)
    require(proposed["sdk_files"] == current["sdk_files"] and proposed["wire"] == current["wire"], "SDK and wire invariance")
    require(proposed["default_descriptor"] == current["default_descriptor"] == identity(INPUT / "inputs/repo/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json"), "9587-byte descriptor")
    groups.append("22 SDK and 24 adapter projections, unchanged wire/default descriptor")

    prefix = "app/src/dev/mixer/android/"
    require(set(proposed["adapter_files"]) - set(current["adapter_files"]) == {prefix + "NativeEditorConnectionV2.java"}, "one new direct adapter")
    require(not set(current["adapter_files"]) - set(proposed["adapter_files"]), "no dropped subject")
    changed = {name for name in current["adapter_files"] if current["adapter_files"][name] != proposed["adapter_files"][name]}
    require(changed == {prefix + name + ".java" for name in ("NativeAppearanceViewsV2", "NativeRenderer", "NativeCoordinatorV2")}, "exact current-byte changes")
    for name in set(current["adapter_files"]) - changed:
        require(current["adapter_files"][name] == proposed["adapter_files"][name], "unchanged adapter identity")
    released = {path.name: identity(path) for path in (INPUT / "inputs/released-correction/source").glob("*.java")}
    require(len(released) == 16, "released source count")
    for name, expected in released.items():
        require(proposed["adapter_files"][prefix + name] == expected, "released binding " + name)
    binding = load("released-correction-binding.json")
    tree = digest(json.dumps(released, sort_keys=True, separators=(",", ":")).encode())
    require(tree == binding["source_tree_sha256"] == proposed["candidate_binding"]["source_tree_sha256"], "candidate tree")
    groups.append("16 released source identities, 3 changed and 1 new adapter, 20 unchanged")

    java = {Path(path).name for path in proposed["adapter_files"] if path.endswith(".java")}
    require(len(java) == 18 and "NativeEditorConnectionV2.java" in java and "AdapterInstrumentation.java" not in java, "18 exact exports")
    require({Path(path).name for path in current["adapter_files"] if path.endswith(".java")} | {"NativeEditorConnectionV2.java"} == java, "exact Java export delta")
    groups.append("18 Java exports exclude checklist instrumentation")

    design = load("family-migration.json")
    validate_family_data(design)
    groups.append("16 families and 96 six-state design rows without callback suppression")
    text = [row["family"] for row in design["families"] if row["category"] in {"text", "text-composition"}]
    submit = [row["family"] for row in design["families"] if row["category"] == "submit"]
    injected = [row["family"] for row in design["families"] if row["successor_is_injected_feature_event"]]
    require(len(text) == 7 and submit == ["performEditorAction"] and len(injected) == 8, "7 text / 1 submit / 8 injected")
    groups.append("seven real text-event families, one installed-listener submit, eight injected non-text successor families")

    lists = load("source-lists.json")
    for label, count in (("A-orchestration", 11), ("B-concrete-renderer-views", 16)):
        sources = lists["closures"][label]["proposed_explicit_product_sources"]
        require(len(sources) == len(set(sources)) == count, "unique host closure " + label)
        require(any(Path(path).name == "NativeEditorConnectionV2.java" for path in sources) is label.startswith("B-"), "B-only direct subject")
    cross = lists["crosscompile"]
    require(len(cross["current_java"]) == 23 and len(cross["proposed_java"]) == len(set(cross["proposed_java"])) == 24, "cross Java count")
    require(set(cross["proposed_java"]) - set(cross["current_java"]) == {"native/android/" + prefix + "NativeEditorConnectionV2.java"}, "cross direct delta")
    require(len(cross["current_swift_c_h"]) == len(set(cross["current_swift_c_h"])) == 76 and cross["new_swift_c_h"] == [], "cross Swift/C/header/package set")
    require(all("repo/" + path in manifest for path in cross["current_swift_c_h"] + cross["current_java"]), "cross inputs manifest bound")
    groups.append("A11/B16 and cross24 Java plus 76 Swift/C/header/package identities")

    for name in ("jni.c", "mixer_android.h", "mixer_android_v2.h"):
        relative = "bridge/" + name
        require(current["adapter_files"][relative] == proposed["adapter_files"][relative] == identity(INPUT / "inputs/repo/native/android" / relative), "bridge invariance")
    groups.append("three byte-identical C/JNI bridge identities")

    guards = {
        "NativeEnvironmentV2.java": "if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();",
        "NativeRenderer.java": "if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);",
    }
    for name, guard in guards.items():
        require(guard in (INPUT / "inputs/released-correction/source" / name).read_text(), "guard retained " + name)
    groups.append("both SDK36 guard source expressions retained; no runtime credit")

    old = load("inputs/historical-preparation/barrier-map-migration-inventory.json")
    require((old["original_records"], old["unchanged_text_suggestions"], old["changed_or_removed"]) == (189, 171, 18), "historical hint counts")
    require(old["runtime_matrix_accepted"] is False and old["new_direct_editor_boundaries_covered"] is False, "historical hints not qualification")
    groups.append("189 historical records / 171 unchanged hints / 18 changed hints remain unqualified")

    mutations = {
        "missing-family": lambda d: d["families"].pop(),
        "duplicate-family": lambda d: d["families"][1].update(family=d["families"][0]["family"]),
        "suppressed-watcher": lambda d: d["families"][0].update(watchers_suppressed=True),
        "removed-listener": lambda d: d["families"][0].update(listener_removed=True),
        "invented-transport-mode": lambda d: d["families"][0].update(new_transport_leaf_mode="suppressed"),
        "wrong-native-leaf": lambda d: d["families"][0].update(counted_leaf="InputConnectionWrapper.beginBatchEdit"),
        "injected-event-as-native": lambda d: d["families"][0].update(ordinary_can_publish_successor=True),
        "natural-event-as-injected": lambda d: d["families"][3].update(successor_is_injected_feature_event=True),
        "missing-fatal-row": lambda d: d["families"][0]["cases"].pop("fatal"),
        "sendKey-positive": lambda d: d["sendKeyEvent"].update(accepted=True),
    }
    for name, mutation in mutations.items():
        value = copy.deepcopy(design)
        mutation(value)
        try:
            validate_family_data(value)
        except ValueError:
            continue
        raise ValueError("design corruption not rejected: " + name)

    result = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "passed-frozen-data-review-controls-only", "python": platform.python_version(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "reviewer_script": identity(Path(__file__)), "input_seal_sha256": EXPECTED_SEAL,
        "positive_groups": groups, "positive_group_count": len(groups),
        "design_corruption_refusals": list(mutations), "design_corruption_refusal_count": len(mutations),
        "text_event_families": text, "submit_event_families": submit, "explicit_injected_successor_families": injected,
        "candidate_source_tree_sha256": tree, "proposed_adapter_projection_sha256": proposed["adapter_compatibility_sha256"],
        "limitations": ["No Java behavior or native/runtime equivalence tested", "Guard checks are source/data only", "96 rows are design, not observed passing cases", "Bound candidate remains changes-required; corrected accepted bytes must be rebound and qualified", "Input-Java extra-sibling policy requires explicit distinction from closed export inventory"],
        "acceptance_or_release_authorized": False,
    }
    (HERE / "design-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS independent data audit:", len(groups), "positive groups;", len(mutations), "design-corruption refusals; no implementation acceptance")


if __name__ == "__main__":
    main()
