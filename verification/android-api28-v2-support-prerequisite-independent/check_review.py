#!/usr/bin/env python3
"""Independent finite source/contract review. Does not run product or native code."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/android-api28-v2-support-prerequisite"
SDK_METADATA = Path("/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/data/api-versions.xml")
EXPECTED_MANIFEST = "7a006a00ed71e014efb9e854fe36b7fcacc09dd5bccae101a193d042407323ad"
DOC = "docs/android-api28-v2-support-prerequisite.md"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": digest(raw)}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_reject(name, action, rejected):
    try:
        action()
    except (AssertionError, ValueError):
        rejected.append(name)
    else:
        raise AssertionError("Negative control admitted: " + name)


def sealed_packet():
    manifest = json.loads((PACKET / "manifest.json").read_bytes())
    require(identity(PACKET / "manifest.json")["sha256"] == EXPECTED_MANIFEST, "different candidate manifest")
    members = manifest["files"]
    actual = {str(p.relative_to(ROOT)) for p in PACKET.rglob("*") if p.is_file() and p.name != "manifest.json"}
    actual.add(DOC)
    require(set(members) == actual and len(members) == 46, "sealed member closure")
    for relative, expected in members.items():
        path = Path(relative)
        require(not path.is_absolute() and ".." not in path.parts, "unsafe member path")
        require(relative == DOC or relative.startswith("verification/android-api28-v2-support-prerequisite/"), "unowned sealed member")
        require(identity(ROOT / relative) == expected, "sealed byte drift: " + relative)
    source_map = json.loads((PACKET / "source-map.json").read_bytes())
    sources = source_map["files"]
    require(len(sources) == 28, "frozen source count")
    require(digest(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) == source_map["source_map_sha256"], "source-map identity")
    for relative, expected in sources.items():
        require(identity(PACKET / "inputs" / relative) == expected, "frozen source drift: " + relative)
    return source_map


def official_sdk_facts():
    api = ET.fromstring(SDK_METADATA.read_bytes())
    facts = []

    def symbol(class_name, member, floor):
        cls = api.find("./class[@name='%s']" % class_name)
        require(cls is not None, "missing official SDK class: " + class_name)
        entry = cls if member is None else next((e for e in cls if e.get("name") == member), None)
        require(entry is not None, "missing official SDK symbol: " + str(member))
        actual_floor = max(int(cls.get("since", "1")), int(entry.get("since", cls.get("since", "1"))))
        require(actual_floor == floor, "wrong official API floor: " + str(member))
        facts.append({"class": class_name, "member": member, "api": actual_floor, "sdk_attributes": dict(entry.attrib)})

    accessibility = "android/view/accessibility/AccessibilityManager"
    listener = accessibility + "$HighContrastTextStateChangeListener"
    symbol(listener, None, 36)
    symbol(accessibility, "isHighContrastTextEnabled()Z", 36)
    symbol(accessibility, "addHighContrastTextStateChangeListener(Ljava/util/concurrent/Executor;L" + listener + ";)V", 36)
    symbol(accessibility, "removeHighContrastTextStateChangeListener(L" + listener + ";)V", 36)
    modes = "android/app/UiModeManager"
    contrast = modes + "$ContrastChangeListener"
    symbol(contrast, None, 34)
    symbol(modes, "getContrast()F", 34)
    symbol(modes, "addContrastChangeListener(Ljava/util/concurrent/Executor;L" + contrast + ";)V", 34)
    symbol(modes, "removeContrastChangeListener(L" + contrast + ";)V", 34)
    for member in ("fontWeightAdjustment", "FONT_WEIGHT_ADJUSTMENT_UNDEFINED"):
        symbol("android/content/res/Configuration", member, 31)
    symbol("android/view/WindowInsets", "getInsets(I)Landroid/graphics/Insets;", 30)
    symbol("android/view/WindowInsets$Type", None, 30)
    for member in ("systemBars()I", "displayCutout()I"):
        symbol("android/view/WindowInsets$Type", member, 30)
    for name in ("setTextCursorDrawable", "setTextSelectHandle", "setTextSelectHandleLeft", "setTextSelectHandleRight"):
        symbol("android/widget/TextView", name + "(Landroid/graphics/drawable/Drawable;)V", 29)
    symbol("android/view/View", "setStateDescription(Ljava/lang/CharSequence;)V", 30)
    symbol("android/view/inputmethod/InputConnection", "setImeConsumesInput(Z)Z", 31)
    symbol("android/view/inputmethod/TextAttribute", None, 33)
    for name, signature in (("commitText", "Ljava/lang/CharSequence;I"), ("setComposingText", "Ljava/lang/CharSequence;I"), ("setComposingRegion", "II")):
        symbol("android/view/inputmethod/InputConnection", name + "(" + signature + "Landroid/view/inputmethod/TextAttribute;)Z", 33)
    symbol("android/view/inputmethod/InputConnection", "replaceText(IILjava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z", 34)
    symbol("android/view/inputmethod/InputConnection", "performHandwritingGesture(Landroid/view/inputmethod/HandwritingGesture;Ljava/util/concurrent/Executor;Ljava/util/function/IntConsumer;)V", 34)
    symbol("android/view/inputmethod/InputConnection", "previewHandwritingGesture(Landroid/view/inputmethod/PreviewableHandwritingGesture;Landroid/os/CancellationSignal;)Z", 34)
    for cls, collection in (("List", "Collection"), ("Map", "Map")):
        symbol("java/util/" + cls, "of()Ljava/util/" + cls + ";", 30)
        symbol("java/util/" + cls, "copyOf(Ljava/util/" + collection + ";)Ljava/util/" + cls + ";", 31)
    symbol("android/graphics/Typeface", "create(Landroid/graphics/Typeface;IZ)Landroid/graphics/Typeface;", 28)
    symbol("android/widget/TextView", "setFallbackLineSpacing(Z)V", 28)
    symbol("android/util/TypedValue", "applyDimension(IFLandroid/util/DisplayMetrics;)F", 1)
    return facts


def matrix_check():
    contract = json.loads((PACKET / "contract.json").read_bytes())
    rows = contract["sdk_matrix"]
    require(len(rows) == 9 and [r["sdk"] for r in rows] == list(range(28, 37)), "nine exact SDK rows")
    for r in rows:
        sdk = r["sdk"]
        expected = {
            "sdk": sdk,
            "high_contrast": "available" if sdk == 36 else "unavailable-api",
            "system_contrast": "available" if sdk >= 34 else "unavailable-api",
            "font_weight": "available-preserve-undefined" if sdk >= 31 else "unavailable-api",
            "exact_typed_insets": "available" if sdk >= 30 else "unavailable-semantics",
            "legacy_insets_equal_typed_union": False,
            "observed_neutral_value_when_api_absent": None,
            "admission": "candidate-existing-checks-only" if sdk == 36 else "reject",
        }
        require(r == expected, "inconsistent SDK availability/admission: " + str(sdk))
    require(contract["sdk_guards_retained"] == ["NativeEnvironmentV2.Observer", "NativeRenderer.requireV2Live"], "retained guards")
    for key in ("public_v2_enabled", "ota_authorized", "new_rendering_contexts_admitted", "implementation_selected", "native_or_capture_or_process_inventory_started"):
        require(contract[key] is False, "unexpected authority: " + key)
    require(all(value == "pending" for value in contract["gates"].values()), "gate promotion")
    return rows


@dataclass(frozen=True)
class Observation:
    status: str
    value: object = None
    reason: str = ""

    def __post_init__(self):
        require(self.status in {"KNOWN", "UNAVAILABLE_API", "UNAVAILABLE_SEMANTICS", "UNDEFINED", "READ_FAILED"}, "closed status set")
        require((self.value is not None) == (self.status == "KNOWN"), "only KNOWN carries a value")
        require(self.status == "KNOWN" or bool(self.reason), "unknown needs a reason")


def selected_neutral_policy(sdk, weight, contrast, high, motion):
    # Proposed contract model only; not Environment/capture creation or product execution.
    if sdk < 36 or any(o.status != "KNOWN" for o in (weight, contrast, high, motion)):
        return False
    return (type(weight.value) is int and weight.value == 0
            and type(contrast.value) in (int, float) and math.isfinite(contrast.value)
            and -1 <= contrast.value <= 1 and contrast.value == 0
            and type(high.value) is bool and high.value is False
            and type(motion.value) in (int, float) and math.isfinite(motion.value) and motion.value >= 0)


def finite_policy_controls():
    rejected = []
    positives = 0
    for status in ("UNAVAILABLE_API", "UNAVAILABLE_SEMANTICS", "UNDEFINED", "READ_FAILED"):
        for value in (False, 0, 1):
            expect_reject(status + "-with-" + str(value), lambda s=status, v=value: Observation(s, v, "reason"), rejected)
    expect_reject("known-without-value", lambda: Observation("KNOWN"), rejected)
    expect_reject("invented-status", lambda: Observation("DEFAULT", False), rejected)
    known = lambda v: Observation("KNOWN", v)
    neutral = (known(0), known(0.0), known(False), known(1.0))
    for sdk in range(28, 36):
        require(not selected_neutral_policy(sdk, *neutral), "model enabled older SDK")
        rejected.append("sdk" + str(sdk) + "-forged-known-neutral")
    for motion in (0, 0.01, 1.0, 20.0):
        require(selected_neutral_policy(36, *neutral[:3], known(motion)), "known supported motion rejected")
        positives += 1
    variants = {
        "weight": [-1, 1, 2147483647],
        "contrast": [-2.0, -1.0, -0.001, 0.001, 1.0, 2.0, math.nan, math.inf, -math.inf],
        "high": [True],
        "motion": [-1.0, math.nan, math.inf, -math.inf],
    }
    for index, (name, values) in enumerate(variants.items()):
        for value in values:
            candidate = list(neutral)
            candidate[index] = known(value)
            require(not selected_neutral_policy(36, *candidate), "model accepted unsupported " + name)
            rejected.append(name + "-" + str(value))
    for index in range(4):
        for status in ("UNAVAILABLE_API", "UNAVAILABLE_SEMANTICS", "UNDEFINED", "READ_FAILED"):
            candidate = list(neutral)
            candidate[index] = Observation(status, reason="finite case")
            require(not selected_neutral_policy(36, *candidate), "unknown became supported")
            rejected.append("unknown-" + str(index) + "-" + status)
    return {"supported_neutral_motion_cases": positives, "rejected_controls": rejected,
            "scope": "Independent proposed observation/admission model only; no native Environment, readiness or capture exists in this model."}


def source_review_anchors():
    inputs = PACKET / "inputs"
    base = "native/android/app/src/dev/mixer/android/"
    anchors = [
        (base + "NativeEnvironmentV2.java", "private final UiModeManager.ContrastChangeListener contrast"),
        (base + "NativeEnvironmentV2.java", "private final AccessibilityManager.HighContrastTextStateChangeListener highContrast"),
        (base + "NativeEnvironmentV2.java", "if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();"),
        (base + "NativeEnvironmentV2.java", "begin(5); modes.addContrastChangeListener"),
        (base + "NativeEnvironmentV2.java", "begin(6); accessibility.addHighContrastTextStateChangeListener"),
        (base + "NativeEnvironmentV2.java", "case 5: modes.removeContrastChangeListener(contrast); break;"),
        (base + "NativeEnvironmentV2.java", "case 6: accessibility.removeHighContrastTextStateChangeListener(highContrast); break;"),
        (base + "NativeEnvironmentV2.java", "boolean equal = value.equals(source.read());"),
        (base + "NativeEnvironmentV2.java", "Settings.Global.ANIMATOR_DURATION_SCALE, 1"),
        (base + "NativeRenderer.java", "if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure"),
        (base + "NativeAppearanceViewsV2.java", "if(android.os.Build.VERSION.SDK_INT>=30)view.setStateDescription"),
        (base + "NativeAppearanceViewsV2.java", "field.setTextCursorDrawable(new Cursor(this))"),
        (base + "NativeAppearanceViewsV2.java", "performHandwritingGesture(android.view.inputmethod.HandwritingGesture"),
        (base + "InstalledAppearanceV2.java", "if (!descriptor.resources.isEmpty() ||"),
        (base + "AppearanceResolverV2.java", "admit(!environment.accessibility().boldText() && !environment.accessibility().increasedContrast(),"),
    ]
    result = []
    for relative, needle in anchors:
        lines = (inputs / relative).read_text().splitlines()
        hits = [(i + 1, line) for i, line in enumerate(lines) if needle in line]
        require(len(hits) == 1, "ambiguous/missing independently inspected source anchor: " + needle)
        result.append({"path": relative, "line": hits[0][0], "source": hits[0][1]})
    return result


def run():
    source_map = sealed_packet()
    sdk_facts = official_sdk_facts()
    rows = matrix_check()
    result = {
        "schema": 1,
        "status": "passed-independent-source-contract-review-only",
        "candidate_manifest_sha256": EXPECTED_MANIFEST,
        "source_map_sha256": source_map["source_map_sha256"],
        "accepted_context_revision": source_map["accepted_context_revision"],
        "live_HEAD_or_live_metadata_identity_asserted": False,
        "sealed_members": 46,
        "frozen_sources": 28,
        "official_sdk_metadata": {"path": str(SDK_METADATA), **identity(SDK_METADATA)},
        "official_sdk_facts": sdk_facts,
        "nine_sdk_rows": rows,
        "reviewed_source_anchors": source_review_anchors(),
        "finite_controls": finite_policy_controls(),
        "python": sys.version,
        "native_product_execution_or_qualification": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, ValueError, OSError, KeyError) as failure:
        print("FAIL independent source contract review: " + str(failure), file=sys.stderr)
        raise SystemExit(1)
