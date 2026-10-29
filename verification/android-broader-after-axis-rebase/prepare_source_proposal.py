"""Prepare a bounded source-only pair.7 proposal; never import product code."""
import sys

OWNED = "/Users/andreyyurlov/Documents/dev/mixer/verification/android-broader-after-axis-rebase"


def deny_active_apis(event, args):
    if event.startswith(("subprocess.", "socket.", "ctypes.")) or event in {
        "os.system", "os.posix_spawn", "os.fork", "os.forkpty", "os.kill",
        "os.killpg", "os.exec", "pty.spawn",
    }:
        raise RuntimeError("source-data-only active API denied: " + event)
    if event == "import" and args[0].split(".")[0] not in sys.stdlib_module_names:
        raise RuntimeError("subject import denied: " + args[0])
    if event == "open":
        path, mode, flags = args
        writing = (isinstance(mode, str) and any(x in mode for x in "wax+")) or (isinstance(flags, int) and flags & 3)
        if writing and not str(path).startswith(OWNED + "/"):
            raise RuntimeError("write outside owned proposal denied")
    if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename"}:
        if str(args[0]) != OWNED and not str(args[0]).startswith(OWNED + "/"):
            raise RuntimeError("mutation outside owned proposal denied")


sys.addaudithook(deny_active_apis)

import ast
import datetime
import difflib
import hashlib
import json
import pathlib

ROOT = pathlib.Path(OWNED).parents[1]
OUT = pathlib.Path(OWNED)
OLD = "verification/android-editor-source-pair5-cli-integration/source/"
RECON = "verification/android-view-api-source-pair-reconciliation/manifest.json"
POLICY = "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift"
DRIVER = "cli/Sources/MixerBuild/Resources/android-build.py"
SWIFT_TEST = "cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift"
PY_TEST = "cli/build-tests/test_android_sdk_compatibility.py"
PROJECT_TEST = "cli/Tests/MixerBuildTests/AndroidProjectTests.swift"
SDK = "bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0"
AXIS = "7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885"
BROADER = "ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e"
inputs = {}
staged = {}
checks = []


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(name):
    path = ROOT / name
    data = path.read_bytes()
    assert len(data) <= 1_048_576, name
    observed = identity(data)
    if name in inputs:
        assert inputs[name] == observed, ("input drift", name)
    inputs[name] = observed
    return data


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, ("duplicate JSON key", key)
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=unique)


def profile(source):
    return decode(source.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0])


def projection(files):
    return hashlib.sha256("".join(path + "\0" + files[path]["sha256"] + "\n" for path in sorted(files)).encode()).hexdigest()


def write(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode()
    path.write_bytes(data)
    return identity(data)


def write_json(name, value):
    return write(name, json.dumps(value, sort_keys=True, indent=2) + "\n")


def stage(target, data, origin):
    staged[target] = {**write("proposed-source/" + target, data), "origin": origin}


def check(label, condition):
    assert condition, label
    checks.append(label)


current_text = read(POLICY).decode()
current = profile(current_text)
check("canonical base bare pair.6", current["id"] == "mixer.android-source-pair.6")
check("canonical SDK22 projection", current["sdk_compatibility_sha256"] == SDK and len(current["sdk_files"]) == 22)
check("canonical axis adapter23 projection", current["adapter_compatibility_sha256"] == AXIS and len(current["adapter_files"]) == 23)
check("canonical SDK22 map digest recomputes", projection(current["sdk_files"]) == SDK)
check("canonical adapter23 map digest recomputes", projection(current["adapter_files"]) == AXIS)
reconciliation = decode(read(RECON))
old_proposal = reconciliation["proposed_policy_object"]
check("historical broader SDK22 equals canonical", old_proposal["sdk_files"] == current["sdk_files"])
proposed = decode(json.dumps(current))
proposed["id"] = "mixer.android-source-pair.7"
proposed["adapter_files"] = old_proposal["adapter_files"]
doc = "Sources/MixerAndroidRuntime/DocumentSession.swift"
proposed["adapter_files"][doc] = current["adapter_files"][doc]
proposed["adapter_compatibility_sha256"] = projection(proposed["adapter_files"])
check("rebased broader adapter24 projection", proposed["adapter_compatibility_sha256"] == BROADER and len(proposed["adapter_files"]) == 24)
check("wire and descriptor unchanged", proposed["wire"] == old_proposal["wire"] == current["wire"] and proposed["default_descriptor"] == old_proposal["default_descriptor"] == current["default_descriptor"])
assembly = {row["exported_path"]: row for row in reconciliation["adapter_assembly"]}
source_rows = []
for kind in ("sdk", "adapter"):
    for exported, expected in sorted(proposed[kind + "_files"].items()):
        if kind == "sdk":
            origin = target = "sdk/" + exported
        else:
            target = "native/android/" + ("engine/" if exported.startswith("Sources/") else "") + exported
            origin = target if exported == doc else assembly[exported]["source_path"]
        data = read(origin)
        check("source identity " + kind + "/" + exported, identity(data) == expected)
        stage(target, data, origin)
        source_rows.append({"kind": kind, "exported_path": exported, "canonical_path": target, "origin": origin, **expected})

check("all SDK22 bytes unchanged", all(current["sdk_files"][p] == i for p, i in proposed["sdk_files"].items()))
changed_adapter = [p for p, i in proposed["adapter_files"].items() if p in current["adapter_files"] and current["adapter_files"][p] != i]
added_adapter = sorted(set(proposed["adapter_files"]) - set(current["adapter_files"]))
check("only expected three Java replacements", sorted(changed_adapter) == ["app/src/dev/mixer/android/NativeAppearanceViewsV2.java", "app/src/dev/mixer/android/NativeCoordinatorV2.java", "app/src/dev/mixer/android/NativeRenderer.java"])
check("only direct editor added", added_adapter == ["app/src/dev/mixer/android/NativeEditorConnectionV2.java"])
check("axis DocumentSession exact canonical6", proposed["adapter_files"][doc] == {"bytes": 4328, "sha256": "cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7"})

# Rebase the accepted canonical-input/export/driver safeguards; replace its old
# policy object wholesale with the current-SDK / axis-preserving broader tuple.
accepted_text = read(OLD + POLICY).decode()
prefix, remainder = accepted_text.split('Data(#"""\n', 1)
_, suffix = remainder.split('\n        """#.utf8)', 1)
policy_json = json.dumps(proposed, sort_keys=True, indent=2)
policy_text = prefix + 'Data(#"""\n' + "\n".join("        " + line for line in policy_json.splitlines()) + '\n        """#.utf8)' + suffix
check("compiled proposed profile exact data", profile(policy_text) == proposed)
stage(POLICY, policy_text, OLD + POLICY + " plus fresh proposed pair.7 literal")
driver_text = read(OLD + DRIVER).decode().replace("value['id'] != 'mixer.android-source-pair.5'", "value['id'] != 'mixer.android-source-pair.7'")
check("driver only admitted ID is pair.7", driver_text.count("value['id'] != 'mixer.android-source-pair.7'") == 1)
check("driver expects SDK22 adapter24", "(('sdk', 22), ('adapter', 24))" in driver_text)
check("accepted explicit javac input flags retained", "'-proc:none', '-sourcepath', ''" in driver_text)
previous_driver = driver_text.replace("value['id'] != 'mixer.android-source-pair.7'", "value['id'] != 'mixer.android-source-pair.6'").replace("('adapter', 24)", "('adapter', 23)").replace("'-proc:none', '-sourcepath', '', ", "")
check("future stale canonical6 driver fixture reconstructs exact current bytes", previous_driver.encode() == read(DRIVER))
ast.parse(driver_text)
stage(DRIVER, driver_text, OLD + DRIVER + " with fresh proposed ID only")


def swift_block(source, function):
    signature = "func " + function + "("
    start = source.rfind("@Test", 0, source.index(signature))
    end = source.find("\n@Test", source.index(signature))
    return source[start:end if end >= 0 else len(source)].rstrip() + "\n"


current_tests = read(SWIFT_TEST).decode()
swift_tests = read(OLD + SWIFT_TEST).decode()
name = "androidCompatibilityLinkedSDKAndTypedDefaultMatchCompiledPolicy"
linked = swift_block(current_tests, name).replace("mixer.android-source-pair.6", "mixer.android-source-pair.7").replace(AXIS, BROADER).replace("p.adapter_files.count == 23", "p.adapter_files.count == 24")
swift_tests = swift_tests.replace(swift_block(swift_tests, name), linked)
name = "androidCompatibilityRequiredContextRejectsMissingLegacyOrMismatchedProfile"
locks = swift_block(current_tests, name)
locks = locks.replace('"broader-6-axis", "mixed-sdk"', '"broader-6-axis", "profile-6-current", "proposal-6-suffixed", "mixed-axis-only", "mixed-sdk"')
extra_cases = '''    case "profile-6-current":
        lock.android?.profile?.id = "mixer.android-source-pair.6"
        lock.android?.profile?.adapter_compatibility_sha256 = "''' + AXIS + '''"
    case "proposal-6-suffixed":
        lock.android?.profile?.id = "mixer.android-source-pair.6-editor-view-api29-30-bc03288599ec-8cd611a5b07f"
        lock.android?.profile?.adapter_compatibility_sha256 = "8cd611a5b07fbf96adb270fa30042577789d4b87b252108697003809f00599b4"
    case "mixed-axis-only": lock.android?.profile?.adapter_compatibility_sha256 = "''' + AXIS + '''"
'''
locks = locks.replace('    case "mixed-sdk":', extra_cases + '    case "mixed-sdk":')
swift_tests = swift_tests.replace(swift_block(swift_tests, name), locks)
name = "androidCompatibilityOrdinaryRelocationCommonLockAndCopiedExportPass"
swift_tests = swift_tests.replace(swift_block(swift_tests, name), swift_block(current_tests, name))
swift_tests += "\n" + swift_block(current_tests, "androidCompatibilityAxisSessionDriftRefusesRecomputedLocksBeforeGenericSourcesAndTools")
check("Swift tests retain axis drift and exact session controls", "baseline.count == 4128" in swift_tests and "p.adapter_files.count == 24" in swift_tests and BROADER in swift_tests)
stage(SWIFT_TEST, swift_tests, OLD + SWIFT_TEST + " merged with canonical6 axis/lock/export controls and new identity refusals")
stage(PROJECT_TEST, read(OLD + PROJECT_TEST), OLD + PROJECT_TEST)


def python_method(source, method):
    tree = ast.parse(source)
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == method]
    assert len(matches) == 1, method
    node = matches[0]
    return "".join(source.splitlines(True)[node.lineno - 1:node.end_lineno])


current_py = read(PY_TEST).decode()
py_tests = read(OLD + PY_TEST).decode()
name = "test_profile_missing_unknown_mismatched_and_configuration_missing_android_lock"
locks = python_method(current_py, name)
locks = locks.replace("'broader-6-axis', 'mixed-sdk'", "'broader-6-axis', 'profile-6-current', 'proposal-6-suffixed', 'mixed-axis-only', 'mixed-sdk'")
extra_cases = (
    "                elif change == 'profile-6-current':\n"
    "                    value['android']['profile'].update(id='mixer.android-source-pair.6', adapter_compatibility_sha256=" + repr(AXIS) + ")\n"
    "                elif change == 'proposal-6-suffixed':\n"
    "                    value['android']['profile'].update(id='mixer.android-source-pair.6-editor-view-api29-30-bc03288599ec-8cd611a5b07f',\n"
    "                        adapter_compatibility_sha256='8cd611a5b07fbf96adb270fa30042577789d4b87b252108697003809f00599b4')\n"
    "                elif change == 'mixed-axis-only': value['android']['profile']['adapter_compatibility_sha256'] = " + repr(AXIS) + "\n"
)
# repr is used for code source data, never interpolated into a shell command.
locks = locks.replace("                elif change == 'mixed-sdk':", extra_cases + "                elif change == 'mixed-sdk':")
py_tests = py_tests.replace(python_method(py_tests, name), locks)
exact = python_method(current_py, "test_axis_only_profile_and_exported_session_are_exact")
exact = exact.replace("test_axis_only_profile_and_exported_session_are_exact", "test_broader_pair7_profile_preserves_exact_axis_session")
exact = exact.replace("'mixer.android-source-pair.6'", "'mixer.android-source-pair.7'").replace("len(PROFILE['adapter_files']), 23", "len(PROFILE['adapter_files']), 24").replace(AXIS, BROADER)
axis_drift = python_method(current_py, "test_axis_session_baseline_and_drift_refuse_recomputed_generic_locks")
previous = '''    def test_previous_pair6_rendered_driver_refuses_broader_sources_before_output(self):
        # Reconstruct exact canonical6 template/map as data, then reach its stale-map admission.
        previous_raw = RAW.replace("value['id'] != 'mixer.android-source-pair.7'", "value['id'] != 'mixer.android-source-pair.6'")
        previous_raw = previous_raw.replace("('adapter', 24)", "('adapter', 23)")
        previous_raw = previous_raw.replace("'-proc:none', '-sourcepath', '', ", "")
        self.assertEqual(hashlib.sha256(previous_raw.encode()).hexdigest(), 'e1e1c57e56d71fe2cadcf9e0b43d8760a5745587f76a8326068a7b8363493a13')
        previous = json.loads(json.dumps(PROFILE))
        previous['id'] = 'mixer.android-source-pair.6'
        previous['adapter_compatibility_sha256'] = ''' + repr(AXIS) + '''
        previous['adapter_files'].pop('app/src/dev/mixer/android/NativeEditorConnectionV2.java')
'''
for exported in changed_adapter:
    previous += "        previous['adapter_files'][" + repr(exported) + "] = " + repr(current["adapter_files"][exported]) + "\n"
previous += '''        self.rendered.write_text(previous_raw.replace(MARKER, json.dumps(previous).encode().hex()))
        self.module = load_driver(self.rendered, 'stale_pair6_' + self.root.name.replace('-', '_'))
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(previous)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()
'''
insertion = "\n\n" + exact + "\n\n" + axis_drift + "\n\n" + previous + "\n"
py_tests = py_tests.replace("\nclass EditorSourcePairTests", insertion + "\nclass EditorSourcePairTests")
ast.parse(py_tests)
py_tree = ast.parse(py_tests)
for cls in (node for node in py_tree.body if isinstance(node, ast.ClassDef)):
    methods = [node.name for node in cls.body if isinstance(node, ast.FunctionDef)]
    check("unique Python method source names " + cls.name, len(methods) == len(set(methods)))
check("Python refusal source retains both .6 tuples", "'profile-6-current'" in py_tests and "'broader-6-axis'" in py_tests)
check("Python source retains accepted editor negative matrix", "test_direct_editor_views_renderer_coordinator_full_negative_matrix" in py_tests)
stage(PY_TEST, py_tests, OLD + PY_TEST + " merged with canonical6 axis/lock tests and exact previous canonical6 driver control")

# Preserve separate unchanged test witnesses and optional input identities. They
# are deliberately not additional product-profile/export/compiler members.
axis_test = "native/android/engine/Tests/MixerAndroidRuntimeTests/AndroidTextFieldAxisRefusalTests.swift"
stage(axis_test, read(axis_test), axis_test)
for optional, expected in reconciliation["canonical_only_optional3_excluded_from_product"].items():
    data = read(optional)
    check("canonical optional identity " + optional, identity(data) == expected)
    stage(optional, data, optional)
for name in ("cli/build-tests/test_android_appearance.py", "cli/build-tests/test_android_staging.py", "verification/android-default-appearance-packaging/run-2/created-descriptor.json"):
    stage(name, read(name), name)

# Read only bounded named evidence, without invoking any historical helper.
evidence = [
    "AGENTS.md", "PLAN.md", "mixer-product-plan.md",
    "verification/android-axis-canonical-source-integration/application-receipt.json",
    "verification/android-axis-canonical-integration-refresh/independent-review/seal.json",
    "verification/android-view-api-boundary-root-source-review/REVIEW.md",
    "verification/android-view-api-package-runtime-actual-review/ACTUAL-REVIEW.md",
    "verification/android-view-api-package-runtime-binary-review/REVIEW.md",
    "verification/android-api28-collections-root-review/acceptance.json",
    "verification/android-api28-collections-prerequisite/consumer-build-contract.json",
    "verification/android-api28-v2-support-prerequisite/contract.json",
    "verification/android-api28-v2-support-prerequisite-independent/receipt.json",
]
for name in evidence:
    read(name)

changes = []
patches = []
for target, item in sorted(staged.items()):
    before_path = ROOT / target
    before = read(target) if before_path.is_file() else b""
    after = (OUT / "proposed-source" / target).read_bytes()
    if before != after:
        changes.append({"canonical_target": target, "before": identity(before) if before_path.is_file() else None, "proposed": identity(after)})
        patches.append("".join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True), fromfile="a/" + target if before else "/dev/null", tofile="b/" + target)))
check("nine canonical overlay changes only", len(changes) == 9)
write("minimal.patch", "".join(patches))
write_json("proposed-profile.json", proposed)
write_json("canonical-pair6-profile.json", current)
write_json("source-manifest.json", {"schema": 1, "status": "source-only-proposed-not-selected", "id": proposed["id"], "projection_algorithm": "SHA256 sorted path + NUL + lowercase file SHA256 + LF; sizes checked separately", "sdk_projection": SDK, "adapter_projection": BROADER, "product_members": len(source_rows), "product_bytes": sum(r["bytes"] for r in source_rows), "product_source_rows": source_rows, "staged_source_count": len(staged), "staged_source_projection": projection(staged), "staged_sources": staged, "canonical_overlay_changes": changes, "descriptor": proposed["default_descriptor"], "wire": proposed["wire"]})
write_json("named-inputs.json", {"schema": 1, "named_count": len(inputs), "projection": projection(inputs), "files": inputs})

# Postflight rereads only the exact named input set; no repository inventory,
# Git/process inspection, product import, compiler, or runtime is performed.
for name, expected in inputs.items():
    check("named input unchanged " + name, identity((ROOT / name).read_bytes()) == expected)
write_json("source-data-receipt.json", {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "source-only-proposal-data-checks-passed-product-and-compiler-tests-unrun",
    "command": "python3 -B verification/android-broader-after-axis-rebase/prepare_source_proposal.py",
    "python": sys.version, "python_executable": sys.executable,
    "source_revision": "3da0d01bd05565a6aad905997beddf6805826241",
    "source_tree": "89297f81773cad23c94ebba1560deccda99c551f",
    "source_revision_provenance": "root supplied; no Git command in this lane",
    "ordinary_ci": {"run": 40960463690, "attempt": 1, "state": "reported-running-by-root; not inspected in this lane"},
    "proposed_id": proposed["id"], "selected_or_activated": False,
    "active_api_denyguard_installed_before_subject_imports": True,
    "subject_imports": 0, "subject_methods_executed": 0, "compiler_invocations": 0,
    "source_data_checks": len(checks), "checks": checks,
    "AST_parse_only": [DRIVER, PY_TEST],
    "named_inputs_unchanged": len(inputs), "staged_sources": len(staged), "overlay_changes": len(changes),
    "prior_preparation_failures": [
        {"kind": "source-data inspection script ValueError before any writes", "detail": "looked for static func required instead of actual static func require; no product or compiler ran"},
        {"kind": "first preparation attempt AST SyntaxError in assembled Python test source", "detail": "source-string quoting emitted literal concatenation text; only owned partial proposal sources were written; no product import/compiler/test ran"},
        {"kind": "second preparation attempt owned-root mkdir guard refusal", "detail": "write guard allowed descendants but rejected mkdir(exist_ok=True) on owned packet root; allowed exact owned root without broadening other writes; no product import/compiler/test ran"},
    ],
    "pending": ["independent source review and root exact-source selection", "actual CLI Debug/Release and Python tests", "canonical installation and ordinary host CI", "fresh generated Debug/Release, relocated and exported consumer evidence", "fresh emitted SDK37 javac/D8 closure with selected JDK/D8 identity", "full owner/default matrix semantic obligations", "ART/class loading and native effects", "API28-35 environment/accessibility/insets/IME compatibility", "TalkBack and physical final acceptance", "immutable separately published SDK consumption by FieldLog", "OTA/release/store/operations/accountable GA"],
    "all_existing_holds_preserved": True,
    "native_UI_capture_emulator_phone_or_process_probes": 0,
    "cleanup": "No native/capture/runtime instance or helper was started; no process probe or signal; other-project processes untouched.",
})
print(json.dumps({"status": "source-only-proposed-not-selected", "id": proposed["id"], "sdk": SDK, "adapter": BROADER, "product_members": len(source_rows), "product_bytes": sum(r["bytes"] for r in source_rows), "staged_sources": len(staged), "overlay_changes": len(changes), "source_data_checks": len(checks), "product_tests_run": 0}, sort_keys=True))
