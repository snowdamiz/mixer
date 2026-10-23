#!/usr/bin/env python3
"""Prepare original reference fixtures/project; input SDK is a frozen Git archive."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "harness/Fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)


def node(id, kind, properties=None, children=None, actions=None):
    return dict(id=id, kind=kind, properties=properties or {}, children=children or [], actions=actions or [])


def text(id, content, style="body", **extra):
    return node(id, "text", dict(text=content, style=style, selectable=False, **extra))


def button(id, label, role="normal", disabled=False):
    properties = dict(label=label, role=role)
    if disabled:
        properties["disabled"] = True
    return node(id, "button", properties, actions=[dict(id=id + ".activate", event="activate")])


def field(id, label, value, disabled=False):
    properties = dict(label=label, value=value)
    if disabled:
        properties["disabled"] = True
    return node(id, "textField", properties, actions=[dict(id=id + ".changed", event="textChange")])


def toggle(id, label, value, disabled=False):
    properties = dict(label=label, value=value)
    if disabled:
        properties["disabled"] = True
    return node(id, "toggle", properties, actions=[dict(id=id + ".changed", event="valueChange")])


def section(id, title, children):
    return node(id, "section", dict(title=title), children)


def document(id, title, sections):
    return dict(schemaVersion=1, revision=1,
        root=node(id + ".navigation", "navigation", dict(title=title),
            [node(id + ".list", "list", children=sections)]))


fixtures = {
    "typography": document("type", "Typography", [
        section("type.roles", "Semantic text roles", [
            text("type.title", "Title · Mixer reference", "title"),
            text("type.headline", "Headline · Field notes", "headline"),
            text("type.body", "Body · Record a clear observation."),
            text("type.caption", "Caption · Saved locally", "caption"),
        ]),
        section("type.wrapping", "Wrapping and state", [
            text("type.wrap", "Body text wraps naturally across lines so native shaping and the available width remain visible."),
            text("type.disabled", "Disabled body text", disabled=True),
            text("type.maxlines", "Two-line limit · An intentionally long note shows the existing renderer's native wrapping and truncation behavior within the list row.", maxLines=2),
        ]),
    ]),
    "controls": document("controls", "Controls", [
        section("controls.buttons", "Button roles", [
            button("controls.normal", "Save note"),
            button("controls.destructive", "Delete note", "destructive"),
            button("controls.cancel", "Cancel", "cancel"),
            button("controls.disabled", "Save unavailable", disabled=True),
        ]),
        section("controls.fields", "Native text fields", [
            field("controls.empty", "Add a note", ""),
            field("controls.filled", "Note", "Roof access clear"),
        ]),
        section("controls.toggles", "Native toggles", [
            toggle("controls.on", "Complete", True),
            toggle("controls.off", "Notify team", False),
            toggle("controls.toggleDisabled", "Unavailable", True, disabled=True),
        ]),
    ]),
    "layouts": document("layout", "Layout & groups", [
        section("layout.vertical", "VStack · explicit leading / gap 8", [
            node("layout.vstack", "vStack", dict(alignment="leading", spacing=8), [
                text("layout.vheadline", "A vertical group", "headline"),
                text("layout.vbody", "Shared document hierarchy"),
                text("layout.vcaption", "Caption inside the same stack", "caption"),
            ]),
        ]),
        section("layout.horizontal", "HStack · first text baseline / gap 16", [
            node("layout.hstack", "hStack", dict(alignment="firstTextBaseline", spacing=16), [
                text("layout.hbody", "Body"), text("layout.htitle", "Title", "title"),
                text("layout.hcaption", "Caption", "caption"),
            ]),
        ]),
        section("layout.overlay", "ZStack · bottom trailing", [
            node("layout.zstack", "zStack", dict(alignment="bottomTrailing"), [
                node("layout.zbase", "vStack", dict(alignment="leading", spacing=8), [
                    text("layout.ztitle", "Overlay base", "headline"),
                    text("layout.zspacer", " "),
                ]), text("layout.zlabel", "Overlay label", "caption"),
            ]),
        ]),
        section("layout.default", "VStack · absent spacing / alignment", [
            node("layout.implicit", "vStack", children=[
                text("layout.implicit1", "Native default stack spacing"),
                text("layout.implicit2", "No theme applied", "caption"),
            ]),
        ]),
    ]),
    "rtl-large": document("rtl", "مرجع", [
        section("rtl.section", "العربية · نص كبير", [
            text("rtl.headline", "ملاحظات الموقع", "headline"),
            text("rtl.body", "حُفظت الملاحظة محليًا."),
            button("rtl.save", "حفظ"),
            toggle("rtl.complete", "مكتمل", True),
        ]),
    ]),
}
for name, value in fixtures.items():
    (FIXTURES / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
manifest = {name: {"sha256": hashlib.sha256((FIXTURES / (name + ".json")).read_bytes()).hexdigest(),
    "documentPath": "harness/Fixtures/" + name + ".json"} for name in fixtures}
(ROOT / "fixture-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

project = ROOT / "harness/MixerAppearanceReference.xcodeproj"
project.mkdir(exist_ok=True)
(project / "project.pbxproj").write_text('''// !$*UTF8*$!
// Original verification-only app project; frozen package dependency.
{
 archiveVersion = 1; classes = {}; objectVersion = 60;
 objects = {
  A00000000000000000000001 = { isa = PBXProject; attributes = { LastUpgradeCheck = 2700; }; buildConfigurationList = A00000000000000000000002; compatibilityVersion = "Xcode 15.0"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en, ar, Base); mainGroup = A00000000000000000000003; productRefGroup = A00000000000000000000004; projectDirPath = ""; projectRoot = ""; targets = (A00000000000000000000005); packageReferences = (A00000000000000000000020); };
  A00000000000000000000002 = { isa = XCConfigurationList; buildConfigurations = (A00000000000000000000006); defaultConfigurationIsVisible = 0; defaultConfigurationName = Debug; };
  A00000000000000000000003 = { isa = PBXGroup; children = (A00000000000000000000008,A00000000000000000000017,A00000000000000000000004); sourceTree = "<group>"; };
  A00000000000000000000004 = { isa = PBXGroup; name = Products; children = (A00000000000000000000009); sourceTree = "<group>"; };
  A00000000000000000000005 = { isa = PBXNativeTarget; buildConfigurationList = A00000000000000000000010; buildPhases = (A00000000000000000000011,A00000000000000000000012,A00000000000000000000013); buildRules = (); dependencies = (); name = MixerAppearanceReference; productName = MixerAppearanceReference; productReference = A00000000000000000000009; productType = "com.apple.product-type.application"; packageProductDependencies = (A00000000000000000000022); };
  A00000000000000000000006 = { isa = XCBuildConfiguration; buildSettings = { SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = 17.0; SWIFT_VERSION = 6.0; CLANG_ENABLE_MODULES = YES; ONLY_ACTIVE_ARCH = YES; }; name = Debug; };
  A00000000000000000000008 = { isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ReferenceApp.swift; sourceTree = "<group>"; };
  A00000000000000000000009 = { isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = MixerAppearanceReference.app; sourceTree = BUILT_PRODUCTS_DIR; };
  A00000000000000000000010 = { isa = XCConfigurationList; buildConfigurations = (A00000000000000000000014); defaultConfigurationIsVisible = 0; defaultConfigurationName = Debug; };
  A00000000000000000000011 = { isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (A00000000000000000000016); runOnlyForDeploymentPostprocessing = 0; };
  A00000000000000000000012 = { isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (A00000000000000000000024); runOnlyForDeploymentPostprocessing = 0; };
  A00000000000000000000013 = { isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (A00000000000000000000018); runOnlyForDeploymentPostprocessing = 0; };
  A00000000000000000000014 = { isa = XCBuildConfiguration; buildSettings = { PRODUCT_BUNDLE_IDENTIFIER = dev.mixer.appearancereference; PRODUCT_NAME = MixerAppearanceReference; GENERATE_INFOPLIST_FILE = YES; INFOPLIST_KEY_CFBundleDisplayName = "Mixer Apple Reference"; INFOPLIST_KEY_UILaunchScreen_Generation = YES; INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES; TARGETED_DEVICE_FAMILY = "1"; CODE_SIGN_STYLE = Automatic; CURRENT_PROJECT_VERSION = 1; MARKETING_VERSION = 0.1.0; SWIFT_VERSION = 6.0; SWIFT_OPTIMIZATION_LEVEL = "-Onone"; IPHONEOS_DEPLOYMENT_TARGET = 17.0; ENABLE_USER_SCRIPT_SANDBOXING = YES; }; name = Debug; };
  A00000000000000000000016 = { isa = PBXBuildFile; fileRef = A00000000000000000000008; };
  A00000000000000000000017 = { isa = PBXFileReference; lastKnownFileType = folder; path = Fixtures; sourceTree = "<group>"; };
  A00000000000000000000018 = { isa = PBXBuildFile; fileRef = A00000000000000000000017; };
  A00000000000000000000020 = { isa = XCLocalSwiftPackageReference; relativePath = "../frozen/sdk"; };
  A00000000000000000000022 = { isa = XCSwiftPackageProductDependency; package = A00000000000000000000020; productName = MixerApple; };
  A00000000000000000000024 = { isa = PBXBuildFile; productRef = A00000000000000000000022; };
 };
 rootObject = A00000000000000000000001;
}
''')
print("Prepared four unchanged-UIDocument fixtures and one frozen-package app project.")
