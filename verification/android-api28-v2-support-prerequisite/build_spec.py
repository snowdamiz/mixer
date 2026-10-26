#!/usr/bin/env python3
"""Generate finite proposal metadata only, from already frozen enumerated inputs."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
JAVA = "native/android/app/src/dev/mixer/android/"
SDK = "sdk/Sources/MixerUI/"


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def ref(path, anchor=""):
    return "https://developer.android.com/reference/" + path + ("#" + anchor if anchor else "")


raw_findings = [
    ("high-contrast", 36, "Public read, listener interface, add and remove begin at API36.", [ref("android/view/accessibility/AccessibilityManager", "isHighContrastTextEnabled()"), ref("android/view/accessibility/AccessibilityManager.HighContrastTextStateChangeListener")]),
    ("system-contrast", 34, "Read, listener interface, add and remove begin at API34; finite documented range -1 to 1, neutral 0.", [ref("android/app/UiModeManager", "getContrast()"), ref("android/app/UiModeManager.ContrastChangeListener")]),
    ("font-weight", 31, "fontWeightAdjustment and its undefined sentinel begin at API31; undefined is distinct from a known zero.", [ref("android/content/res/Configuration", "fontWeightAdjustment")]),
    ("typed-insets", 30, "getInsets(int) and WindowInsets.Type begin at API30. Legacy system-window inset definitions can include IME; systemBars excludes IME. Exact pre30 equivalence is not established.", [ref("android/view/WindowInsets", "getInsets(int)"), ref("android/view/WindowInsets.Type", "systemBars()"), ref("android/view/WindowInsets", "getSystemWindowInsetBottom()")]),
    ("cursor-handles", 29, "Drawable cursor and text-select-handle setter overloads begin at API29.", [ref("android/widget/TextView", "setTextCursorDrawable(android.graphics.drawable.Drawable)"), ref("android/widget/TextView", "setTextSelectHandleLeft(android.graphics.drawable.Drawable)")]),
    ("state-description", 30, "Native state-description APIs begin at API30; required pre30 value equivalence needs an explicit implementation.", [ref("android/view/View", "setStateDescription(java.lang.CharSequence)"), ref("android/view/accessibility/AccessibilityNodeInfo", "setStateDescription(java.lang.CharSequence)")]),
    ("ime-consumption", 31, "InputConnection.setImeConsumesInput begins at API31.", [ref("android/view/inputmethod/InputConnection", "setImeConsumesInput(boolean)")]),
    ("text-attribute", 33, "TextAttribute type and commitText/setComposingText/setComposingRegion overloads begin at API33.", [ref("android/view/inputmethod/TextAttribute"), ref("android/view/inputmethod/InputConnectionWrapper")]),
    ("handwriting-replace", 34, "replaceText, performHandwritingGesture and previewHandwritingGesture begin at API34.", [ref("android/view/inputmethod/InputConnectionWrapper"), ref("android/view/inputmethod/InputConnection")]),
    ("collection-of", 30, "List.of and Map.of factories begin at API30 on Android; min-api compilation alone is not a library replacement receipt.", [ref("java/util/List", "of()"), ref("java/util/Map", "of()")]),
    ("collection-copy", 31, "List.copyOf and Map.copyOf begin at API31; they return immutable snapshots rather than live views, and reject null members.", [ref("java/util/List", "copyOf(java.util.Collection)"), ref("java/util/Map", "copyOf(java.util.Map)")]),
    ("typeface-weight", 28, "Weighted Typeface.create(Typeface,int,boolean) is available at API28; it does not establish glyph/weight parity.", [ref("android/graphics/Typeface", "create(android.graphics.Typeface,%20int,%20boolean)")]),
    ("fallback-spacing", 28, "TextView.setFallbackLineSpacing is available at API28.", [ref("android/widget/TextView", "setFallbackLineSpacing(boolean)")]),
    ("dimension-conversion", 1, "TypedValue.applyDimension is API1. Configuration.fontScale is not a direct font equation for nonlinear scaling.", [ref("android/util/TypedValue", "applyDimension(int,%20float,%20android.util.DisplayMetrics)"), ref("android/content/res/Configuration", "fontScale")]),
]
findings = [{"id": ident, "minimum_api": api, "finding": finding, "urls": urls,
             "source_class": "official-android-reference", "observed_via": "web-tool-search-open-find"}
            for ident, api, finding, urls in raw_findings]
write("official-findings.json", {"schema": 1, "checked_date": "2026-10-26", "scope": "Reviewed public reference facts and explicitly labelled inference; not runtime evidence.", "findings": findings})

anchors = [
    (JAVA + "NativeEnvironmentV2.java", "if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();"),
    (JAVA + "NativeRenderer.java", "if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure"),
    (JAVA + "NativeEnvironmentV2.java", "private final UiModeManager.ContrastChangeListener contrast"),
    (JAVA + "NativeEnvironmentV2.java", "private final AccessibilityManager.HighContrastTextStateChangeListener highContrast"),
    (JAVA + "NativeEnvironmentV2.java", "begin(5); modes.addContrastChangeListener"),
    (JAVA + "NativeEnvironmentV2.java", "begin(6); accessibility.addHighContrastTextStateChangeListener"),
    (JAVA + "NativeEnvironmentV2.java", "case 5: modes.removeContrastChangeListener"),
    (JAVA + "NativeEnvironmentV2.java", "case 6: accessibility.removeHighContrastTextStateChangeListener"),
    (JAVA + "NativeEnvironmentV2.java", "Insets insets = captured.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());"),
    (JAVA + "NativeEnvironmentV2.java", "int adjustment = config.fontWeightAdjustment;"),
    (JAVA + "NativeEnvironmentV2.java", "accessibility.isHighContrastTextEnabled() || modes.getContrast() > 0"),
    (JAVA + "NativeEnvironmentV2.java", "Settings.Global.getFloat(resolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1)"),
    (JAVA + "NativeEnvironmentV2.java", "TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 17, metrics)"),
    (JAVA + "NativeEnvironmentV2.java", "boolean equal = value.equals(source.read());"),
    (JAVA + "NativeEnvironmentV2.java", "private final int[] cleanup = new int[8];"),
    (JAVA + "NativeEnvironmentV2.java", "if (retired || !initialized || owner == null) unsupported();"),
    (JAVA + "NativeAppearanceViewsV2.java", "field.setTextCursorDrawable(new Cursor(this))"),
    (JAVA + "NativeAppearanceViewsV2.java", "field.setTextSelectHandleLeft(new Handle(this))"),
    (JAVA + "NativeAppearanceViewsV2.java", "if(android.os.Build.VERSION.SDK_INT>=30)view.setStateDescription"),
    (JAVA + "NativeAppearanceViewsV2.java", "commitText(CharSequence text,int position,android.view.inputmethod.TextAttribute attributes)"),
    (JAVA + "NativeAppearanceViewsV2.java", "setImeConsumesInput(boolean consumes)"),
    (JAVA + "NativeAppearanceViewsV2.java", "performHandwritingGesture(android.view.inputmethod.HandwritingGesture"),
    (JAVA + "NativeAppearanceViewsV2.java", "replaceText(int start,int end,CharSequence text,int position,android.view.inputmethod.TextAttribute attributes)"),
    (JAVA + "NativeAppearanceViewsV2.java", "text.setFallbackLineSpacing(true)"),
    (JAVA + "NativeAppearanceViewsV2.java", 'Typeface.create(Typeface.create("sans-serif",Typeface.NORMAL),text.metrics().weight().value,false)'),
    (JAVA + "NativeAppearanceViewsV2.java", "this.separators=List.copyOf(separators)"),
    (JAVA + "NativeAppearanceViewsV2.java", "records=Map.of()"),
    (JAVA + "AppearanceResolverV2.java", "byID = Map.copyOf(index);"),
    (JAVA + "AppearanceResolverV2.java", "admit(!environment.accessibility().boldText() && !environment.accessibility().increasedContrast(),"),
    (JAVA + "AppearanceDescriptorV2.java", "this.resources = List.copyOf(resources);"),
    (JAVA + "AppearanceGeometryV2.java", "Command { points = List.copyOf(points); }"),
    (JAVA + "AppearanceGeometryV2.java", "List.of()"),
    (JAVA + "OwnerLifecycleV2.java", "return List.copyOf(out);"),
    (JAVA + "OwnerLifecycleV2.java", "if (!accepts(owner)) return List.of();"),
    (JAVA + "InstalledAppearanceV2.java", "if (!descriptor.resources.isEmpty() ||"),
    (JAVA + "InstalledAppearanceV2.java", "!(descriptor.iOS.typography().font() instanceof AppearanceDescriptorV2.SystemSans)"),
    (JAVA + "InstalledAppearanceV2.java", "!(descriptor.android.typography().font() instanceof AppearanceDescriptorV2.SystemSans)"),
    (JAVA + "InstalledAppearanceV2.java", "if (total > 65536)"),
    (JAVA + "NativeCoordinatorV2.java", "int status = NativeBridge.commitV2(session, token);"),
    (JAVA + "NativeCoordinatorV2.java", "renderer.finishV2(candidate, journal);"),
    (JAVA + "NativeCoordinatorV2.java", "void refreshEnvironment()"),
    (JAVA + "NativeOwnerV2.java", "observer = new NativeEnvironmentV2.Observer(activity, root, this);"),
    (JAVA + "MixerActivity.java", "new NativeRenderer(this,this::event)"),
    (SDK + "AppearanceResolutionV2.swift", "guard !environment.accessibility.boldText, !environment.accessibility.increasedContrast else"),
    ("docs/ui-measured-appearance-v2-contract.md", "Unknown/unsupported required visual accessibility"),
    ("docs/android-owner-effect-contract.md", "Neither a host pass, API 37 compilation"),
    ("native/android/build.py", "run([BT/'d8','--min-api','28','--lib',JAR"),
    ("cli/Sources/MixerBuild/Resources/android-build.py", "run([BT / 'd8', '--min-api', '28', '--lib', JAR"),
]
source = json.loads((HERE / "source-map.json").read_text())
index = []
for path, needle in anchors:
    lines = (HERE / "inputs" / path).read_text().splitlines()
    matches = [i for i, line in enumerate(lines) if needle in line]
    if not matches:
        raise ValueError("Missing exact reviewed source anchor: " + path + ": " + needle)
    for match in matches:
        index.append({"path": path, "needle": needle, "start": match + 1, "end": match + 1, "snippet": lines[match]})
write("source-index.json", {"schema": 1, "source_map_sha256": source["source_map_sha256"], "scope": "Exact reviewed source anchors only; snippet matching grants no native or release authority.", "anchors": index})

policies = {
    "resource-catalog": "reject-any-declaration", "bundled-font-either-theme": "reject",
    "font-fallback-none": "no-substitution", "unknown-accessibility": "reject",
    "nonneutral-accessibility": "reject", "api28-fields-and-selection": "reject-until-implemented",
    "pre30-required-accessibility-value": "reject-until-implemented",
    "unsupported-ime-extension": "reject-before-mutation", "v2-rejection": "no-v1-fallback",
    "uncertain-native-effect": "terminal-with-independent-cleanup",
}
gates = ["root-selection", "independent-implementation-review", "native-compiler", "native-runtime-effects", "physical-phones", "TalkBack", "design-parity", "public-v2-routing", "published-separate-repository-FieldLog", "OTA", "signing-store-operations", "accountable-GA"]
rows = [{"sdk": sdk,
         "high_contrast": "available" if sdk >= 36 else "unavailable-api",
         "system_contrast": "available" if sdk >= 34 else "unavailable-api",
         "font_weight": "available-preserve-undefined" if sdk >= 31 else "unavailable-api",
         "exact_typed_insets": "available" if sdk >= 30 else "unavailable-semantics",
         "legacy_insets_equal_typed_union": False,
         "admission": "candidate-existing-checks-only" if sdk >= 36 else "reject",
         "observed_neutral_value_when_api_absent": None} for sdk in range(28, 37)]
write("contract.json", {"schema": 1, "proposal_only": True, "implementation_selected": False,
    "public_v2_enabled": False, "ota_authorized": False, "new_rendering_contexts_admitted": False,
    "recommended_slice": "guarded-observations-closed-pre36-admission", "observer_owner_count": 1,
    "capture_mint_count": 1, "commit_finish_adapter_calls_allowed": 0,
    "sdk_guards_retained": ["NativeEnvironmentV2.Observer", "NativeRenderer.requireV2Live"],
    "native_or_capture_or_process_inventory_started": False, "policies": policies,
    "gates": {gate: "pending" for gate in gates}, "sdk_matrix": rows})
print(json.dumps({"status": "generated-proposal-data-only", "official_findings": len(findings), "source_anchors": len(index), "sdk_rows": len(rows)}, sort_keys=True))
