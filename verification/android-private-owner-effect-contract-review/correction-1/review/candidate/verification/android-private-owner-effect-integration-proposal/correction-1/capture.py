#!/usr/bin/env python3
"""Capture correction design inputs and mandatory roster; no product execution."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
ORIGINAL = BASE.parent
REVIEW = ROOT / "verification/android-private-owner-effect-contract-review"
DOC = "docs/android-private-owner-effect-integration-correction.md"
APP = "native/android/app/src/dev/mixer/android/"
CORE = "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java"
ACTUAL_NAMES = ["NativeCoordinatorV2", "NativeRenderer", "NativeEnvironmentV2",
                "NativeAppearanceViewsV2", "InstalledAppearanceV2", "UiPacket", "Json",
                "AppearanceDescriptorV2", "AppearanceGeometryV2", "AppearanceResolverV2",
                "AppearanceNativePathsV2", "AuthoredToggleInputV2"]
SOURCES = ["AGENTS.md", "PLAN.md", "mixer-product-plan.md", CORE,
           *[APP + name + ".java" for name in ACTUAL_NAMES], APP + "NativeBridge.java",
           APP + "MixerActivity.java", "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift",
           "cli/Sources/MixerBuild/AndroidProject.swift",
           "docs/android-private-owner-effect-contract-review.md",
           "verification/android-environment-observer-root-review/implementation-acceptance.json",
           "verification/android-public-owner-core-root-review/implementation-acceptance.json"]
ANDROID = """
android.R
android.app.Activity android.app.UiModeManager
android.content.Context android.content.ComponentCallbacks android.content.ContentResolver
android.content.ClipboardManager android.content.ClipData
android.content.res.Configuration android.content.res.Resources android.content.res.ColorStateList android.content.res.AssetManager
android.database.ContentObserver
android.graphics.Canvas android.graphics.Color android.graphics.ColorFilter android.graphics.Insets
android.graphics.Paint android.graphics.Path android.graphics.PixelFormat android.graphics.Rect android.graphics.RectF android.graphics.Typeface
android.graphics.drawable.Drawable
android.net.Uri
android.os.Build android.os.Bundle android.os.CancellationSignal android.os.Handler android.os.LocaleList android.os.Looper
android.provider.Settings
android.text.Annotation android.text.Editable android.text.InputFilter android.text.InputType android.text.Layout
android.text.Spanned android.text.TextUtils android.text.TextWatcher android.text.style.UnderlineSpan
android.util.DisplayMetrics android.util.TypedValue
android.view.Gravity android.view.KeyEvent android.view.MotionEvent android.view.View android.view.ViewGroup
android.view.ViewParent android.view.ViewConfiguration android.view.Window android.view.WindowInsets android.view.ViewTreeObserver
android.view.accessibility.AccessibilityManager android.view.accessibility.AccessibilityNodeInfo
android.view.inputmethod.BaseInputConnection android.view.inputmethod.CompletionInfo android.view.inputmethod.CorrectionInfo
android.view.inputmethod.EditorInfo android.view.inputmethod.HandwritingGesture android.view.inputmethod.InputConnection
android.view.inputmethod.InputConnectionWrapper android.view.inputmethod.InputContentInfo
android.view.inputmethod.PreviewableHandwritingGesture android.view.inputmethod.TextAttribute
android.widget.Button android.widget.EditText android.widget.FrameLayout android.widget.LinearLayout
android.widget.ScrollView android.widget.Switch android.widget.TextView
""".split()


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_manifest(path):
    manifest = json.loads(path.read_text())
    for name, expected in manifest["files"].items():
        actual = ROOT / name
        assert not actual.is_symlink() and ident(actual.read_bytes()) == expected, name
    return {"path": str(path.relative_to(ROOT)), **ident(path.read_bytes()),
            "members": len(manifest["files"]),
            "bytes_in_members": sum(v["bytes"] for v in manifest["files"].values())}


def inventory():
    result = []
    calls = re.compile(r"(?P<receiver>\b[\w.]+)\.(?P<method>set[A-Z]\w*|addView|removeView|removeViewAt|measure|layout|requestFocus|scrollTo|invalidate|requestDisallowInterceptTouchEvent|performClick|performAccessibilityAction|dispatchKeyEvent|dispatchTouchEvent|dispatchDraw|drawChild|onDraw|onCreateInputConnection|onLayout|onScrollChanged|onDetachedFromWindow|onAttachedToWindow|onVisibilityChanged|onWindowVisibilityChanged|onWindowFocusChanged|onFocusChanged|onRtlPropertiesChanged|onSelectionChanged|onKeyDown|onTextContextMenuItem|drawableStateChanged)\s*\(")
    constructors = re.compile(r"new\s+(?P<constructor>TextView|NativeButton|NativeField|NativeSwitch|NativeScroll|Group|NativeAppearanceViewsV2.Record|NativeAppearanceViewsV2.Gate)\s*\(")
    for name, minimum in [("NativeRenderer", 60), ("NativeAppearanceViewsV2", 1)]:
        path = APP + name + ".java"
        for number, line in enumerate((ROOT / path).read_text().splitlines(), 1):
            if number < minimum:
                continue
            matches = [(m.start(), m.group(0).strip()) for m in calls.finditer(line)]
            matches += [(m.start(), m.group(0).strip()) for m in constructors.finditer(line)]
            for ordinal, (column, expression) in enumerate(sorted(matches), 1):
                result.append({"id": f"{name}:L{number}:C{column + 1}:{ordinal}",
                               "source": path, "line": number, "column": column + 1,
                               "expression": expression, "source_line": line.strip(),
                               "required_cases": ["clean", "terminal-at-entry", "terminal-before-return",
                                                  "dirty-at-entry", "dirty-before-return",
                                                  "ordinary-throw-after-callback", "fatal-throw-after-callback"]})
    return result


def roster():
    actual_b = [APP + "NativeOwnerV2.java", APP + "OwnerLifecycleV2.java"] + [APP + n + ".java" for n in ACTUAL_NAMES]
    actual_a = [p for p in actual_b if p.rsplit("/", 1)[-1] not in
                {"NativeRenderer.java", "NativeAppearanceViewsV2.java", "AppearanceNativePathsV2.java", "AuthoredToggleInputV2.java"}]
    closures = {}
    for key, directory, test, subjects, extras, probe in [
        ("A-orchestration", "NativeOwnerV2HostLeaves", "NativeOwnerV2HostTests.java", actual_a,
         ["dev.mixer.android.NativeRenderer"], "dev.mixer.android.OwnerHostProbe"),
        ("B-concrete-renderer-views", "NativeOwnerV2ConcreteHostLeaves", "NativeOwnerV2ConcreteHostTests.java", actual_b,
         [], "dev.mixer.android.ConcreteHostProbe"),
    ]:
        fqcn = sorted(ANDROID + ["dev.mixer.android.NativeBridge"] + extras)
        closures[key] = {
            "mandatory": True, "actual_production_sources": subjects,
            "test_source": "native/android/tests/" + test,
            "substitutes": [{"fqcn": n, "source": "native/android/tests/" + directory + "/" + n.replace(".", "/") + ".java"} for n in fqcn],
            "test_support_sources": ["native/android/tests/" + directory + "/" + probe.replace(".", "/") + ".java"],
            "compiled_source_roster_is_exact": True, "implicit_sourcepath_or_classpath": False,
            "native_framework_or_JNI_qualification": False,
        }
    return {"schema": 1, "status": "mandatory-contract-for-later-implementation-not-executed",
            "closures": closures,
            "new_or_moved_production_sources": [APP + "NativeOwnerV2.java", APP + "OwnerLifecycleV2.java"],
            "accepted_core_must_move_without_byte_change": CORE,
            "nested_types_share_enumerated_owning_source": True,
            "source_inventory_is_supplemental_not_behavior_proof": True,
            "baseline_callback_barriers": inventory(),
            "mandatory_constructor_entries": {
                "NativeButton": "android.widget.Button", "NativeField": "android.widget.EditText",
                "NativeSwitch": "android.widget.Switch", "NativeScroll": "android.widget.ScrollView",
                "Group": "android.view.ViewGroup", "Gate": "android.widget.FrameLayout",
                "plain text/header/compact": "android.widget.TextView"},
            "early_virtual_constructor_entries": ["setEnabled", "setFrame", "drawableStateChanged",
                "onSelectionChanged", "onAttachedToWindow", "onDetachedFromWindow", "onFocusChanged",
                "onWindowFocusChanged", "onVisibilityChanged", "onWindowVisibilityChanged", "onRtlPropertiesChanged"],
            "new_calls_in_same_regions_require_additional_mandatory_barrier_ids": True,
            "mandatory_callback_regions": [
                "Record and native View superclass/subclass construction before v2Pending publication",
                "Record.defaults/bind/text/bindTitle and nested constructor hierarchy adds",
                "measure/title/measureList/installChildren/layoutRoot/layout/Group.onLayout/titleLayout",
                "renderer attach/restoreParent/restoreV2 and Gate construction",
                "NativeSwitch setEnabled/setFrame cancellation before superclass mutation",
                "NativeSwitch attach/detach/visibility/windowVisibility/windowFocus/focus/RTL cancellation overrides",
                "NativeSwitch clearTouch setPressed/invalidate/parent release independent attempts",
                "NativeSwitch performClick finally/reconcile and input gestures",
                "NativeScroll.onScrollChanged live presentation with null operation token",
                "Gate onDraw/dispatchDraw/dispatchTouchEvent/dispatchKeyEvent and renderer Input/current",
                "NativeField onCreateInputConnection before superclass acquisition and every retained wrapper mutation",
                "NativeField selection/key/accessibility/context-menu/text-change input callbacks",
                "actual active-safe cancellation, serial exhaustion, duplicate and recursive record claims",
                "actual interaction exhaustion/capture/rollback/fatal current exact-bound terminal reports",
                "commit/finish direct scalar failure and deferred reporting outside critical interval",
                "root focus/core.focusChanged and resume/pause/stop plus one owned drain/terminal tail",
            ],
            "mandatory_nonbarrier_controls": [
                "first/middle/last cancellation ordinary and fatal errors, all remaining slots attempted",
                "foreign/stale/repeated/wrong-thread terminal reports",
                "late acquired coordinator; active/cancel/report deferred disposition; never-returned pending",
                "no new input/drain authority after terminal and no callback inside successful commit-to-finish",
                "positive ordinary native scrolling/navigation/input with operation null",
                "actual retained packet identity, zero engine calls on refresh, synchronous ordinary input",
            ]}


def main():
    assert not (BASE / "receipt.json").exists(), "do not replace captured boundary"
    original = verify_manifest(ORIGINAL / "manifest.json")
    assert original["sha256"] == "7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7"
    review = verify_manifest(REVIEW / "manifest.json")
    assert review["sha256"] == "8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58"
    preaccess_path = REVIEW / "correction-1/preaccess/manifest.json"
    preaccess = json.loads(preaccess_path.read_text())
    assert ident(preaccess_path.read_bytes())["sha256"] == "638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c"
    for name, expected in preaccess["files"].items():
        assert ident((preaccess_path.parent / name).read_bytes()) == expected, name
    commands = []
    for argv in [["git", "rev-parse", "HEAD"], ["git", "rev-parse", "HEAD^{tree}"], ["git", "--version"]]:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=10)
        command = {"argv": argv, "cwd": str(ROOT), "timeout_seconds": 10,
                   "exit_code": result.returncode, "stdout": result.stdout.decode(), "stderr": result.stderr.decode()}
        commands.append(command)
        assert result.returncode == 0, command
    inputs = {}
    for name in SOURCES:
        path = ROOT / name
        assert path.is_file() and not path.is_symlink(), name
        data = path.read_bytes()
        target = BASE / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs[name] = ident(data)
    for label, path in [("original-manifest.json", ORIGINAL / "manifest.json"),
                        ("review-manifest.json", REVIEW / "manifest.json"),
                        ("review-result.json", REVIEW / "review-result.json")]:
        (BASE / label).write_bytes(path.read_bytes())
    for name in ("plan.json", "manifest.json"):
        (BASE / ("preaccess-" + name)).write_bytes((preaccess_path.parent / name).read_bytes())
    (BASE / "preaccess-admission.json").write_bytes((ROOT / "verification/android-private-owner-effect-integration-root-review/correction-preaccess-admission.json").read_bytes())
    write(BASE / "required-host-roster.json", roster())
    tools = {}
    for name, location in [("python", sys.executable), ("git", shutil.which("git"))]:
        path = Path(location).resolve(strict=True)
        tools[name] = {"path": str(path), **ident(path.read_bytes())}
    tools["python"]["version"] = sys.version
    tools["git"]["version"] = commands[2]["stdout"].strip()
    projection = "".join(n + "\0" + inputs[n]["sha256"] + "\n" for n in sorted(inputs)).encode()
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "status": "source-only-correction-1-awaiting-independent-review-and-root-selection",
               "context_revision": commands[0]["stdout"].strip(), "context_tree": commands[1]["stdout"].strip(),
               "design_read_revision": "b45963c03816112972499bd60073039f36916272",
               "revision_drift_is_context_only_when_selected_product_bindings_match": True,
               "command": [sys.executable, "-B", str(Path(__file__).resolve())], "commands": commands,
               "tools": tools, "inputs": inputs, "selected_input_projection_sha256": hashlib.sha256(projection).hexdigest(),
               "projection_is_complete_repository_tree": False,
               "original_manifest": original, "independent_review_manifest": review,
               "preaccess_plan_manifest_sha256": ident(preaccess_path.read_bytes())["sha256"],
               "preaccess_obligations": 28,
               "original_files_preserved": True,
               "only_authorized_original_directory_extension": "verification/android-private-owner-effect-integration-proposal/correction-1/",
               "old_verifier_exact_directory_limitation": "Original seal.py includes all descendants; adding correction-1 makes its historical exact-directory closure fail. New verifier excludes only correction-1 while preserving every old member and original manifest/verifier bytes.",
               "correction": {"path": DOC, **ident((ROOT / DOC).read_bytes())},
               "roster": ident((BASE / "required-host-roster.json").read_bytes()),
               "product_tests_run": False, "mandatory_host_closures_executed": False,
               "implementation_selected": False, "implementation_accepted": False,
               "cross_compilation_run": False, "native_runtime_or_capture_started": False,
               "process_discovery": False, "network_install_signing_credentials_publication": False,
               "product_profile_root_metadata_or_original_member_edits": False,
               "new_dependencies": [], "actual_reclamation_proven": False, "GA_qualified": False,
               "retained_tool_failure": {"tool": "apply_patch", "scope": "correction documentation only; no mutation occurred",
                   "result": "apply_patch verification failed: Failed to find expected lines in /Users/andreyyurlov/Documents/dev/mixer/docs/android-private-owner-effect-integration-correction.md:\ncandidate publication must not expose a map without its roster. Do not",
                   "resolution": "Read exact lines and applied corrected contexts successfully before the first seal."},
               "limitations": ["Source custody/roster/contract checks only; no product behavior was run.",
                               "Both executable host closures and all native/SDK/JNI cross-compilation remain required after selection.",
                               "Native UI/capture/runtime paused, physical phones disconnected, final product and GA gates pending."]}
    write(BASE / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "inputs": len(inputs),
                      "original_members_preserved": original["members"], "review_members_verified": review["members"],
                      "mandatory_concrete_subjects": len(roster()["closures"]["B-concrete-renderer-views"]["actual_production_sources"]),
                      "baseline_callback_barriers": len(roster()["baseline_callback_barriers"])}, sort_keys=True))


if __name__ == "__main__":
    main()
