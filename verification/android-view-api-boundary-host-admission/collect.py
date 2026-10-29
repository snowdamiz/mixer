"""Focused hosted collector candidate. Import is inert; execution needs root selection.

Exactly three version commands, two javac commands, one narrow test main and D8.
No old runner, matrix, Unit A, native runtime, installer or automatic dispatch.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import resource
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = "verification/android-view-api-boundary-candidate"
INSPECTOR = "verification/android-view-api-boundary-bytecode-inspection"


class Refusal(RuntimeError):
    pass


def save(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def identity(path):
    h = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(part)
            if size > 536870912:
                raise Refusal("single input larger than reviewed bound")
            h.update(part)
    return {"bytes": size, "sha256": h.hexdigest()}


def regular(path, root):
    path, root = Path(path), Path(root)
    if not path.is_relative_to(root):
        raise Refusal("input escapes root")
    for component in (path, *path.parents):
        if component == root.parent:
            break
        if stat.S_ISLNK(component.lstat().st_mode):
            raise Refusal("source symlink refused: " + str(component))
    if not stat.S_ISREG(path.lstat().st_mode):
        raise Refusal("ordinary input required: " + str(path))
    return path


def verify_rows(root, rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 512:
        raise Refusal("bounded input manifest required")
    seen = set()
    for entry in rows:
        name = entry["path"]
        if name in seen or not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts:
            raise Refusal("duplicate or escaping input")
        seen.add(name)
        actual = identity(regular(Path(root) / name, root))
        if actual != {"bytes": entry["bytes"], "sha256": entry["sha256"]}:
            raise Refusal("source identity changed: " + name)
    return {"members": len(rows), "map_sha256": hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def bounded_files(root, maximum_nodes, prune_local=False, excluded_files=()):
    """Bound dirs and files during discovery; never descend ignored local history."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise Refusal("ordinary directory required")
    nodes, files = 1, []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        nodes += len(dirs) + len(names)
        if nodes > maximum_nodes:
            raise Refusal("filesystem node discovery bound")
        retained = []
        for name in dirs:
            path = Path(base) / name
            if prune_local and "local" in path.relative_to(root).parts:
                continue
            if path.is_symlink() or not stat.S_ISDIR(path.lstat().st_mode):
                raise Refusal("directory symlink/nonordinary node refused")
            retained.append(name)
        dirs[:] = retained
        for name in sorted(names):
            path = Path(base) / name
            if path.relative_to(root).as_posix() in excluded_files:
                continue
            if prune_local and "local" in path.relative_to(root).parts:
                continue
            regular(path, root)
            files.append(path)
    return sorted(files)


def verify_frozen_inputs(root=ROOT, packet=HERE):
    root, packet = Path(root), Path(packet)
    manifest = json.loads((packet / "input-manifest.json").read_bytes())
    result = verify_rows(root, manifest["members"])
    producer = json.loads((root / CANDIDATE / "manifest.json").read_bytes())
    expected = {entry["path"] for entry in producer["members"]}
    observed = set()
    for path in bounded_files(root / CANDIDATE, 1024, prune_local=True):
        relative = path.relative_to(root / CANDIDATE)
        if relative.as_posix() not in ("manifest.json", "freeze.json"):
            observed.add(relative.as_posix())
    if observed != expected or len(expected) != 115:
        raise Refusal("producer closed membership changed")
    source_map = {Path(e["path"]).name: {"bytes": e["bytes"], "sha256": e["sha256"]}
                  for e in producer["members"] if e["path"].startswith("source/")}
    product = hashlib.sha256(json.dumps(source_map, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if len(source_map) != 16 or product != manifest["product_tree"]:
        raise Refusal("product16 identity changed")
    host, sdk = manifest["host_sources"], manifest["sdk_sources"]
    product_paths = sorted("source/" + name for name in source_map)
    leaves = sorted(e["path"] for e in producer["members"]
                    if e["path"].startswith("tests/host-leaves/") and e["path"].endswith(".java"))
    if len(leaves) != 86 or host != sorted(product_paths + leaves + ["tests/ViewApiBoundaryTests.java"]):
        raise Refusal("host closure must be product16 + mechanical86 + focused1")
    if sdk != sorted(product_paths + ["tests/cross-leaf/NativeBridge.java"]):
        raise Refusal("SDK closure must be product16 + signature leaf only")
    if manifest["copied_input_paths"] != sorted(set(host + sdk + ["tests/descriptor.json"])):
        raise Refusal("copy closure expanded")
    result.update(product_tree=product, host_inputs=len(host), sdk_inputs=len(sdk))
    return result


def distribution_tree(path):
    """Independent implementation of the accepted installed-distribution digest."""
    root = Path(path).resolve(strict=True)
    if not root.is_dir():
        raise Refusal("tool distribution missing")
    h, count, total, nodes = hashlib.sha256(), 0, 0, 1
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        nodes += len(dirs) + len(names)
        if nodes > 50000:
            raise Refusal("distribution total node bound")
        if len(dirs) + len(names) > 16384:
            raise Refusal("distribution directory bound")
        for name in sorted(names + [n for n in dirs if (Path(base) / n).is_symlink()]):
            path = Path(base) / name
            count += 1
            if count > 50000:
                raise Refusal("distribution member bound")
            if path.is_symlink():
                resolved = path.resolve(strict=True)
                if path.is_dir() and not resolved.is_relative_to(root):
                    raise Refusal("distribution directory symlink escapes hashed root")
                value = "symlink:" + os.readlink(path)
                if path.is_file():
                    info = identity(path)
                    total += info["bytes"]
                    value += ":" + info["sha256"]
            elif stat.S_ISREG(path.lstat().st_mode):
                info = identity(path)
                total += info["bytes"]
                value = info["sha256"]
            else:
                raise Refusal("nonordinary distribution member")
            if total > 3221225472:
                raise Refusal("distribution byte bound")
            h.update((path.relative_to(root).as_posix() + "\0" + value + "\n").encode())
    return {"sha256": h.hexdigest(), "members": count, "nodes": nodes, "bytes": total}


def verify_tools(profile):
    if sys.platform != profile["host_os"] or platform.machine() != profile["host_machine"]:
        raise Refusal("selected OS/architecture tool profile required")
    actual = {}
    mode = profile.get("identity_mode", "historical-distribution-tree")
    if mode == "official-jdk-runtime-files-v1":
        name = profile["jdk_runtime_manifest"]
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise Refusal("runtime manifest path escapes admission")
        if identity(HERE / name)["sha256"] != profile["jdk_runtime_manifest_sha256"]:
            raise Refusal("selected runtime manifest identity changed")
        expected = json.loads((HERE / name).read_bytes())
        rows = expected["members"] if isinstance(expected, dict) else expected
        if not 1 <= len(rows) <= 256:
            raise Refusal("JDK runtime member bound")
        if len(rows) != profile["jdk_runtime_members"] or sum(e["bytes"] for e in rows) != profile["jdk_runtime_bytes"]:
            raise Refusal("JDK runtime manifest totals")
        seen, observed = set(), []
        for entry in rows:
            relative = entry["path"]
            if relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise Refusal("JDK runtime path/duplicate")
            seen.add(relative)
            path = Path(profile["jdk"]) / relative
            regular(path, Path(profile["jdk"]))
            resolved = path.resolve(strict=True)
            if not stat.S_ISREG(resolved.lstat().st_mode):
                raise Refusal("JDK runtime regular file required")
            value = identity(resolved)
            if value != {"bytes": entry["bytes"], "sha256": entry["sha256"]}:
                raise Refusal("official JDK runtime member changed: " + relative)
            observed.append({"path": relative, "resolved": str(resolved),
                             "symlink": os.readlink(path) if path.is_symlink() else None, **value})
        jdk = Path(profile["jdk"])
        scoped = {"bin/java", "bin/javac", "release"}
        for folder, excluded in (("conf", ()), ("lib", ("src.zip", "security/cacerts"))):
            scoped.update(folder + "/" + p.relative_to(jdk / folder).as_posix()
                          for p in bounded_files(jdk / folder, 4096, excluded_files=excluded))
        if scoped != seen:
            raise Refusal("JDK runtime conf/lib closed membership changed")
        actual["jdk_runtime"] = {"members": observed, "scope": profile["packaging_boundary"]}
    elif mode == "historical-distribution-tree":
        for name, entry in profile["distributions"].items():
            value = distribution_tree(entry["path"])
            if value["sha256"] != entry["sha256"]:
                raise Refusal("official tool distribution changed: " + name)
            actual[name] = value
    else:
        raise Refusal("unreviewed tool identity mode")
    actual["tool_files"] = {}
    for path, expected in profile["files"].items():
        value = identity(path)
        if value != expected:
            raise Refusal("official tool file changed: " + path)
        actual["tool_files"][path] = value
    for entry in profile["metadata_sha256"].values():
        if identity(entry["path"])["sha256"] != entry["sha256"]:
            raise Refusal("official tool metadata changed")
    expected_python = profile["collector_python"]
    if expected_python.get("boundary") == "root-admitted-ubuntu-provider-infrastructure":
        if (str(Path(sys.executable).absolute()) != expected_python["path"]
                or tuple(sys.version_info[:3]) != tuple(expected_python["version"])
                or sys.flags.isolated != 1 or not sys.dont_write_bytecode):
            raise Refusal("selected isolated Ubuntu Python provider changed")
        os_release = Path("/etc/os-release").read_text()
        parsed = dict(line.split("=", 1) for line in os_release.splitlines() if "=" in line)
        if parsed.get("ID", "").strip('"') != "ubuntu" or parsed.get("VERSION_ID", "").strip('"') != "24.04":
            raise Refusal("Ubuntu24.04 provider required")
        actual["provider_os_release"] = {"text": os_release, **identity("/etc/os-release")}
    elif str(Path(sys.executable).resolve()) != expected_python["path"] or identity(sys.executable)["sha256"] != expected_python["sha256"]:
        raise Refusal("collector Python identity changed")
    actual["python"] = {"path": str(Path(sys.executable).resolve()), "version": sys.version,
                        "bootstrap_independently_pinned_by_running_collector": False,
                        **identity(sys.executable)}
    return actual


def build_plan(root, output, profile, manifest):
    """Pure argv construction. All sources are explicit, no wildcard/argfile discovery."""
    scratch = Path(output) / "scratch"
    inputs, temp, empty = scratch / "inputs", scratch / "tmp", scratch / "empty"
    host, sdk, dex = scratch / "host-classes", scratch / "sdk-classes", scratch / "dex"
    jdk = Path(profile["jdk"])
    java, javac = str(jdk / "bin/java"), str(jdk / "bin/javac")
    jar = str(Path(profile["android_platform"]) / "android.jar")
    d8jar = str(Path(profile["android_build_tools"]) / "lib/d8.jar")
    java_options = ["-Xmx256m", "-XX:MaxMetaspaceSize=256m", "-XX:ReservedCodeCacheSize=128m",
                    "-XX:CompressedClassSpaceSize=128m", "-Djava.io.tmpdir=" + str(temp),
                    "-Duser.home=" + str(scratch / "home"), "-Dfile.encoding=UTF-8"]
    compiler_options = ["-J" + option for option in java_options]
    compile_flags = ["--release", "17", "-proc:none", "-Xlint:all", "-Werror", "-sourcepath", str(empty)]
    commands = [
        {"name": "java-version", "argv": [java, *java_options, "-version"]},
        {"name": "javac-version", "argv": [javac, *compiler_options, "-version"]},
        {"name": "d8-version", "argv": [java, *java_options, "-cp", d8jar, "com.android.tools.r8.D8", "--version"]},
        {"name": "host-compile", "argv": [javac, *compiler_options, *compile_flags,
             "-classpath", str(empty), "-d", str(host), *[str(inputs / p) for p in manifest["host_sources"]]]},
        {"name": "focused-main", "argv": [java, *java_options, "-ea", "-cp", str(host),
             "dev.mixer.android.ViewApiBoundaryTests", str(inputs / manifest["descriptor"])]},
        {"name": "sdk37-compile", "argv": [javac, *compiler_options, *compile_flags,
             "-classpath", jar, "-d", str(sdk), *[str(inputs / p) for p in manifest["sdk_sources"]]]},
    ]
    # D8 input class filenames must be bound from the inspected emitted SDK map.
    return {"commands": commands, "scratch": str(scratch), "host_classes": str(host),
            "sdk_classes": str(sdk), "dex_dir": str(dex), "platform_jar": jar,
            "d8_prefix": [java, *java_options, "-cp", d8jar, "com.android.tools.r8.D8",
                          "--min-api", "28", "--lib", jar, "--output", str(dex)],
            "command_count": 7, "work_commands": 4, "version_commands": 3}


def verify_self(packet, expected_seal_sha256=None):
    seal_path = packet / "seal.json"
    if expected_seal_sha256 is not None and identity(seal_path)["sha256"] != expected_seal_sha256:
        raise Refusal("selected admission seal mismatch")
    seal = json.loads(seal_path.read_bytes())
    observed = set()
    for p in bounded_files(packet, 1024, prune_local=True):
        if p != seal_path:
            observed.add(p.relative_to(packet).as_posix())
    if observed != {e["path"] for e in seal["members"]}:
        raise Refusal("admission membership changed")
    return verify_rows(packet, seal["members"])


def validate_selection(selection, env, packet=HERE, root=ROOT):
    if selection.get("purpose") != "android-view-api-focused-hosted-only" or selection.get("dispatch_selected") is not True:
        raise Refusal("explicit root hosted selection required")
    if env.get("GITHUB_ACTIONS") != "true" or env.get("GITHUB_REPOSITORY") != "snowdamiz/mixer":
        raise Refusal("selected GitHub hosted execution context required")
    revision = selection.get("github_sha", "")
    if not re.fullmatch("[0-9a-f]{40}", revision) or env.get("GITHUB_SHA") != revision:
        raise Refusal("selected workflow revision mismatch")
    run_id = env.get("GITHUB_RUN_ID", "")
    if not re.fullmatch("[0-9]+", run_id):
        raise Refusal("workflow run identity unavailable")
    nonce = selection.get("dispatch_nonce", "")
    if not re.fullmatch("[0-9a-f]{64}", nonce):
        raise Refusal("explicit root once-only dispatch nonce required")
    if env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise Refusal("no workflow retries admitted")
    workflow = selection.get("workflow_relative_path", "")
    if not re.fullmatch(r"\.github/workflows/[a-z0-9-]+\.yml", workflow):
        raise Refusal("selected installed workflow path required")
    if identity(regular(Path(root) / workflow, root))["sha256"] != selection.get("installed_workflow_sha256"):
        raise Refusal("selected installed workflow identity changed")
    if not env.get("GITHUB_WORKFLOW_REF", "").startswith("snowdamiz/mixer/" + workflow + "@"):
        raise Refusal("workflow context path mismatch")
    verify_self(packet, selection.get("admission_seal_sha256", ""))
    for field, file in (("runner_sha256", "collect.py"), ("custody_sha256", "custody.py"),
                        ("workflow_draft_sha256", "workflow.DRAFT.yml")):
        if identity(packet / file)["sha256"] != selection.get(field):
            raise Refusal("root-selected " + field + " mismatch")
    return {"revision": revision, "run_id": run_id, "run_attempt": 1,
            "root_dispatch_nonce": nonce,
            "selection_sha256": hashlib.sha256(json.dumps(selection, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def emitted_map(directory):
    result = []
    for path in bounded_files(directory, 4096):
        if path.suffix != ".class":
            raise Refusal("unexpected emitted file")
        result.append({"path": path.relative_to(directory).as_posix(), **identity(path)})
        if len(result) > 512:
            raise Refusal("emitted class bound")
    if not result:
        raise Refusal("no emitted classes")
    return result


def scratch_bound(scratch, profile):
    files, total = 0, 0
    for path in bounded_files(scratch, profile["scratch_files"] * 2):
        files += 1
        total += path.stat().st_size
        if files > profile["scratch_files"] or total > profile["scratch_file_bytes"]:
            raise Refusal("scratch output bound")
    return {"files": files, "bytes": total, "disposition": "retained; no deletion"}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def collect(selection_path, output):
    output = Path(output)
    if not output.is_absolute():
        raise Refusal("absolute unique output directory required")
    # Unique attempt directory, never auto-select/reuse a prior failed setup.
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": 1, "status": "failed-setup", "runtime_accepted": False,
               "scratch_disposition": "retained", "commands": [], "errors": [],
               "old_process_access_or_cleanup": False, "native_ui_capture_phones": False}
    before = None
    try:
        selection = json.loads(Path(selection_path).read_bytes())
        save(output / "root-selection.json", selection)
        receipt["selection"] = validate_selection(selection, dict(os.environ))
        # Selected standalone hosted collector only; never applied at import or
        # during preparation. JVM children install their own stricter limits.
        resource.setrlimit(resource.RLIMIT_AS, (2147483648, 8589934592))
        resource.setrlimit(resource.RLIMIT_FSIZE, (268435456, 268435456))
        resource.setrlimit(resource.RLIMIT_CPU, (900, 900))
        profile = json.loads((HERE / "tool-profile.json").read_bytes())
        admission = json.loads((HERE / "admission.json").read_bytes())
        if profile.get("id") != admission.get("tool_profile_id") or profile.get("identity_mode") != "official-jdk-runtime-files-v1":
            raise Refusal("selected focused Linux tool profile mismatch")
        if selection.get("candidate_freeze_sha256") != admission["candidate_freeze_sha256"]:
            raise Refusal("root selection candidate mismatch")
        binding = admission["inspector"]
        if selection.get("inspector_seal_sha256") != binding["seal_sha256"]:
            raise Refusal("root selection inspector mismatch")
        inspector_path = ROOT / INSPECTOR / "inspect_artifacts.py"
        if identity(inspector_path)["sha256"] != binding["file_sha256"] or identity(ROOT / INSPECTOR / "seal.json")["sha256"] != binding["seal_sha256"]:
            raise Refusal("inspector frozen identity mismatch")
        manifest = json.loads((HERE / "input-manifest.json").read_bytes())
        before = verify_frozen_inputs()
        save(output / "source-preflight.json", before)
        receipt["tools_before"] = verify_tools(profile)
        save(output / "tool-preflight.json", receipt["tools_before"])
        plan = build_plan(ROOT, output, profile, manifest)
        save(output / "plan.json", plan)
        scratch = Path(plan["scratch"])
        for name in ("inputs", "tmp", "empty", "home", "host-classes", "sdk-classes", "dex"):
            (scratch / name).mkdir(parents=True, exist_ok=False)
        for name in manifest["copied_input_paths"]:
            destination = scratch / "inputs" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / CANDIDATE / name).read_bytes())
        copied = [{"path": name, **identity(scratch / "inputs" / name)} for name in manifest["copied_input_paths"]]
        frozen_rows = {e["path"].removeprefix(CANDIDATE + "/"): {"bytes": e["bytes"], "sha256": e["sha256"]}
                       for e in manifest["members"] if e["path"].startswith(CANDIDATE + "/")}
        expected_copy = [{"path": name, **frozen_rows[name]} for name in manifest["copied_input_paths"]]
        if copied != expected_copy:
            raise Refusal("copied source differs from frozen manifest")
        save(output / "copied-inputs.json", copied)
        custody = load_module(HERE / "custody.py", "mixer_view_api_custody")
        inspector = load_module(inspector_path, "mixer_view_api_bytecode_inspector")
        env = {"JAVA_HOME": profile["jdk"], "PATH": profile["jdk"] + "/bin:/usr/bin:/bin",
               "HOME": str(scratch / "home"), "TMPDIR": str(scratch / "tmp"),
               "TMP": str(scratch / "tmp"), "TEMP": str(scratch / "tmp"),
               "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
        inspected_maps = {}
        def flight():
            source = verify_frozen_inputs()
            validate_selection(selection, dict(os.environ))
            verify_self(HERE, selection["admission_seal_sha256"])
            if expected_copy != [{"path": name, **identity(regular(scratch / "inputs" / name, scratch))} for name in manifest["copied_input_paths"]]:
                raise Refusal("copied source changed")
            for kind, rows in inspected_maps.items():
                if emitted_map(plan[kind + "_classes"]) != rows:
                    raise Refusal("inspected " + kind + " class bytes changed")
            if identity(inspector_path)["sha256"] != binding["file_sha256"] or identity(ROOT / INSPECTOR / "seal.json")["sha256"] != binding["seal_sha256"]:
                raise Refusal("inspector source changed")
            tools = verify_tools(profile)
            if tools != receipt["tools_before"]:
                raise Refusal("within-run tool/provider observations changed")
            return {"source": source, "tools": tools, "scratch": scratch_bound(scratch, profile)}
        def command(entry):
            receipt.setdefault("attempted_commands", []).append(entry["name"])
            result = custody.run_command(entry["name"], entry["argv"], scratch, env,
                output / "commands" / entry["name"], profile["bounds"], flight, flight)
            receipt["commands"].append({"name": entry["name"], "accepted": result["accepted"]})
        for entry in plan["commands"]:
            command(entry)
            if entry["name"] in ("java-version", "javac-version", "d8-version"):
                expected_key = {"java-version": "java_stderr", "javac-version": "javac_stdout", "d8-version": "d8_stdout"}[entry["name"]]
                stream = expected_key.split("_")[-1]
                if (output / "commands" / entry["name"] / stream).read_text() != profile["versions"][expected_key]:
                    raise Refusal("observed version output mismatch: " + entry["name"])
                other = "stderr" if stream == "stdout" else "stdout"
                if (output / "commands" / entry["name"] / other).read_bytes():
                    raise Refusal("unexpected version stream: " + entry["name"])
            if entry["name"] in ("host-compile", "sdk37-compile"):
                kind = "host" if entry["name"] == "host-compile" else "sdk"
                classes = Path(plan[kind + "_classes"])
                class_rows = emitted_map(classes)
                save(output / (kind + "-classes.json"), class_rows)
                evidence = inspector.inspect_classes(classes, platform_jar=Path(plan["platform_jar"]))
                save(output / (kind + "-class-inspection.json"), evidence)
                if evidence.get("accepted") is not True:
                    raise Refusal("emitted " + kind + " classes refused")
                if emitted_map(classes) != class_rows:
                    raise Refusal("emitted classes changed during inspection")
                inspected_maps[kind] = class_rows
            if entry["name"] == "focused-main":
                lines = (output / "commands/focused-main/stdout").read_text().splitlines()
                groups = json.loads((ROOT / CANDIDATE / "coverage-plan.json").read_bytes())["groups"]
                if len(lines) != 14 or lines[:13] != ["PASS " + e["name"] for e in groups] or not re.fullmatch(r"PASS 13 focused actual-source groups / [1-9][0-9]{0,5} assertions; mechanical host leaves only", lines[13]):
                    raise Refusal("focused main output differs from frozen thirteen groups")
                if (output / "commands/focused-main/stderr").read_bytes():
                    raise Refusal("focused main unexpected stderr")
        sdk_classes = emitted_map(plan["sdk_classes"])
        d8 = {"name": "d8-min28", "argv": plan["d8_prefix"] + [str(Path(plan["sdk_classes"]) / row["path"]) for row in sdk_classes]}
        save(output / "d8-exact-plan.json", d8)
        command(d8)
        dex_files = sorted(Path(plan["dex_dir"]).iterdir())
        if [p.name for p in dex_files] != ["classes.dex"]:
            raise Refusal("exact single DEX required")
        dex_evidence = inspector.inspect_dex(dex_files[0])
        save(output / "dex-inspection.json", dex_evidence)
        if dex_evidence.get("accepted") is not True:
            raise Refusal("DEX reference inspection refused")
        receipt["dex"] = identity(dex_files[0])
        if receipt["dex"] != dex_evidence.get("artifact"):
            raise Refusal("DEX bytes changed during inspection")
        receipt["final_flight"] = flight()
        receipt["tools_after"] = verify_tools(profile)
        if receipt["tools_after"] != receipt["tools_before"]:
            raise Refusal("final tool/provider observations changed")
        receipt.update(status="passed-focused-host-and-sdk37-d8-only", runtime_accepted=True,
                       focused_groups=13, frozen_finite_interruption_invocations=152,
                       limits="mechanical JVM component behavior and emitted SDK37/min28 references only; no ART, startup matrix, native parity, new source pair, canonical, OTA or GA admission")
    except BaseException as error:
        receipt["errors"].append(type(error).__name__ + ": " + str(error)[:2000])
    finally:
        try:
            after = verify_frozen_inputs()
            receipt["source_after"] = after
            receipt["source_unchanged"] = before is not None and after == before
            if before is not None and after != before:
                raise Refusal("final source changed")
        except BaseException as error:
            receipt["errors"].append("final source: " + type(error).__name__ + ": " + str(error)[:1000])
        if receipt["errors"]:
            receipt.update(status="refused-failure-retained", runtime_accepted=False)
        save(output / "receipt.json", receipt)
    if not receipt["runtime_accepted"]:
        raise Refusal("focused admission failed; all evidence retained at " + str(output))
    return receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-selection", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    collect(args.root_selection, args.output)


if __name__ == "__main__":
    main()
