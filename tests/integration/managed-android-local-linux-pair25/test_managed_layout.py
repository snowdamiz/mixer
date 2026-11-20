import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hosted/priv/development"))
import linux_android_pair25_layout as pair25
import managed_worker as worker


DRIVER = Path(__file__).resolve().parents[3] / "cli/Sources/MixerBuild/Resources/android-build.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ManagedLayoutTest(unittest.TestCase):
    def test_managed_driver_reports_output_byte_counts(self):
        def build(project, *, retained_output):
            self.assertEqual((worker.PROJECT, worker.RETAINED), (project, retained_output))
            print("Swift ✓", flush=True)
            print("warning", file=sys.stderr)

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            log = worker.build_driver_log(SimpleNamespace(build=build))
        self.assertEqual("Swift ✓\n", stdout.getvalue())
        self.assertEqual("warning\n", stderr.getvalue())
        self.assertEqual({
            "exitCode": 0, "stdoutBytes": len(stdout.getvalue().encode()),
            "stderrBytes": len(stderr.getvalue().encode()), "outputTruncated": False,
        }, log)

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="managed-pair25-"))).resolve()
        self.project = "readonly/Export/"
        self.name = "mixer-l05-" + "a" * 64
        (self.root / "outputs" / self.name).mkdir(parents=True)
        (self.root / "outputs").chmod(0o700)
        self.toolchain = {
            "distributions": {"swift_toolchain": {"path": "/", "sha256": pair25.MANIFEST[7:]}},
            "tools": {
                "python": {"path": "/python/bin/python3.12", "sha256": sha(b"python tool")},
                "d8": {"path": "/android-sdk/build-tools/37.0.0/d8", "sha256": sha(b"d8 tool")},
            },
            "metadata": {},
        }
        self.write("python/bin/python3.12", b"python tool")
        self.write("android-sdk/build-tools/37.0.0/d8", b"d8 tool")
        for tool in ("python/bin/python3.12", "android-sdk/build-tools/37.0.0/d8"):
            (self.root / tool).chmod(0o755)
        self.write("glibc/libc.so.6", b"compat libc")
        self.write("glibc/ld-linux-x86-64.so.2", b"compat loader")
        (self.root / "lib64").mkdir()
        (self.root / "lib64/ld-linux-x86-64.so.2").symlink_to("/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2")
        for package in ("swift-asn1", "swift-crypto"):
            mirror = f"mirrors/{package}.git/"
            (self.root / mirror / "objects").mkdir(parents=True)
            self.write(mirror + "HEAD", b"ref: refs/heads/main\n")
            self.write(mirror + "config", b"[core]\n\tbare = true\n")
        self.mac = {"schema": 1, "android": {"adapterDigest": "fixed", "toolchain": {"os": "mac"}}}
        self.linux = {"schema": 1, "android": {"adapterDigest": "fixed", "toolchain": self.toolchain}}
        self.receipt = {
            "toolSources": {"swiftArm64Image": pair25.IMAGE},
            "toolchain": self.toolchain,
        }
        self.pin = self.write_json("recipe/receipt.json", self.receipt)
        self.products = {
            "priorPackagingReceipt": {"sha256": self.pin},
            "build": {"source_tree_sha256": "1" * 64, "source_tree_after_sha256": "1" * 64},
            "fixtureSHA256": {"worker.py": self.write("recipe/worker.py", b"recorded worker")},
            "inputHashes": {
                "macMixerLockSHA256BeforeAndAfter": self.write_json(self.project + "mixer.lock", self.mac),
                "localLinuxLockSHA256": self.write_json("lock/linux-mixer.lock", self.linux),
                "platformLockSHA256BeforeAndAfter": self.write(
                    self.project + "Platforms/Android/Package.resolved", b"two package pins"),
                "renderedBuildDriverSHA256": self.write(
                    self.project + "Generated/MixerAndroid/android-build.py", b"locked build driver"),
            },
        }
        self.write(self.project + "Generated/MixerSDK/Package.resolved", b"two package pins")
        self.products_pin = self.write_json("recipe/retained-products.json", self.products)

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return sha(data)

    def write_json(self, relative, data):
        return self.write(relative, json.dumps(data).encode())

    def read(self):
        # Substitute the legacy fixture receipt hashes.
        with patch.multiple(pair25, RECEIPT_SHA256=self.pin, PRODUCTS_RECEIPT_SHA256=self.products_pin):
            return pair25.Pair25Layout.read(self.root)

    def project_lock(self):
        project = self.root / self.project
        shutil.copyfile(DRIVER, project / worker.DRIVER)
        shutil.copyfile(worker.__file__, self.root / "recipe/worker.py")
        (self.root / "recipe/receipt.json").unlink()
        (self.root / "recipe/retained-products.json").unlink()
        (self.root / "lock/linux-mixer.lock").unlink()
        self.toolchain["distributions"]["swift_toolchain"]["sha256"] = pair25.NOBLE_MANIFEST[7:]
        spec = importlib.util.spec_from_file_location("test_pair25_android_driver", project / worker.DRIVER)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        with patch.multiple(worker, PROJECT=project, DELIVERY=self.root / "lock"), \
                patch.object(driver, "inspect", return_value=self.toolchain):
            worker.project_lock(driver)
        return driver

    def approve_projection(self):
        approval = self.root / pair25.PROJECTION
        approval.write_bytes((self.root / "lock" / pair25.PROJECTION).read_bytes())
        approval.chmod(0o600)
        return approval

    def read_projection(self):
        with patch.object(pair25, "NOBLE_PYTHON_SHA256", self.toolchain["tools"]["python"]["sha256"]):
            return pair25.Pair25Layout.read(self.root)

    def volume(self, layout):
        return {
            "Name": layout.volume_name, "Driver": "local", "Scope": "local", "Options": None,
            "Labels": layout.volume_labels, "CreatedAt": "2026-11-20T05:22:00Z",
            "Mountpoint": f"/var/lib/docker/volumes/{layout.volume_name}/_data",
        }

    def test_generated_command_matches_fixed_pair25_build(self):
        layout = self.read()
        layout.recheck_stage()
        args = layout.create_arguments(self.name)
        mounts = [args[i + 1] for i, arg in enumerate(args) if arg == "--mount"]
        expected_binds = {
            "/lib/x86_64-linux-gnu": "glibc", "/lib64": "lib64", "/recipe": "recipe",
            "/project": "readonly/Export", "/android-sdk": "android-sdk", "/mirrors": "mirrors",
            "/python": "python", "/project/mixer.lock": "lock/linux-mixer.lock",
        }
        self.assertCountEqual(mounts, [
            f"type=bind,source={self.root / source},target={target},bind-recursive=disabled,readonly"
            for target, source in expected_binds.items()
        ] + [
            f"type=volume,source={layout.volume_name},target=/toolchain,readonly,volume-nocopy",
            f"type=bind,source={self.root / 'outputs' / self.name},target=/deliver,bind-recursive=disabled",
        ])
        self.assertLess(next(i for i, value in enumerate(mounts) if ",target=/project," in value),
                        next(i for i, value in enumerate(mounts) if ",target=/project/mixer.lock," in value))
        self.assertEqual(args[:6], (
            "--tmpfs", "/tmp:rw,nosuid,nodev,exec,size=512m", "--tmpfs",
            "/work:rw,nodev,nosuid,exec,size=3g,mode=0700,uid=65534,gid=65534", "--user", "65534:65534",
        ))
        env = [args[i + 1] for i, arg in enumerate(args) if arg == "--env"]
        self.assertCountEqual(env, [
            f"PAIR25_VERIFIED_SWIFT_MANIFEST={pair25.MANIFEST}", "HOME=/work/home", "PYTHONHOME=/python",
            "PYTHONDONTWRITEBYTECODE=1", "GIT_CONFIG_GLOBAL=/dev/null", "GIT_CONFIG_NOSYSTEM=1",
            "GIT_ALLOW_PROTOCOL=file", "GIT_CONFIG_COUNT=2",
            "GIT_CONFIG_KEY_0=url.file:///mirrors/swift-asn1.git.insteadOf",
            "GIT_CONFIG_VALUE_0=https://github.com/apple/swift-asn1.git",
            "GIT_CONFIG_KEY_1=url.file:///mirrors/swift-crypto.git.insteadOf",
            "GIT_CONFIG_VALUE_1=https://github.com/apple/swift-crypto.git",
            "JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=4 -Xmx1024m",
        ])
        self.assertEqual(args[-7:-3], ("--entrypoint", "/bin/sh", pair25.IMAGE, "-euc"))
        self.assertEqual(args[-2:], ("pair25-worker", "build"))
        self.assertEqual(layout.verified_inputs, {
            "source_tree_sha256": "1" * 64,
            "linux_lock_sha256": self.products["inputHashes"]["localLinuxLockSHA256"],
            "rendered_driver_sha256": self.products["inputHashes"]["renderedBuildDriverSHA256"],
        })

    def test_generated_shell_projects_linux_lock_into_delivery(self):
        args = self.read().create_arguments(self.name)
        shell, _, flags, script, label, phase = args[-6:]
        subprocess.run([shell, "-n", "-c", script], check=True, timeout=3)
        self.assertEqual(flags, "-euc")
        self.write("stub.py", b"""from pathlib import Path
import sys
assert sys.argv[1:] == ['build']
out = Path(__file__).parent / 'deliver'
assert (out / 'linux-mixer.lock').is_file()
for name in ('UpgradeStarter-unsigned.apk', 'debug-symbols.zip', 'resource-inventory.json', 'readback.json'):
    (out / name).write_text(name)
""")
        for directory in ("work", "deliver"):
            (self.root / directory).mkdir()
        for guest, host in {
            "/work/home": self.root / "work/home",
            "/project/mixer.lock": self.root / "lock/linux-mixer.lock",
            "/deliver/linux-mixer.lock": self.root / "deliver/linux-mixer.lock",
            "/python/bin/python3.12": Path(sys.executable), "/recipe/worker.py": self.root / "stub.py",
        }.items():
            script = script.replace(guest, shlex.quote(str(host)))
        command = [shell, flags, script, label, phase]
        subprocess.run(command, check=True, timeout=3)
        out = self.root / "deliver"
        self.assertCountEqual((p.name for p in out.iterdir()), (
            "UpgradeStarter-unsigned.apk", "debug-symbols.zip", "resource-inventory.json", "readback.json",
            "linux-mixer.lock",
        ))
        lock = out / "linux-mixer.lock"
        self.assertEqual(lock.read_bytes(), (self.root / "lock/linux-mixer.lock").read_bytes())
        self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
        (self.root / "work/home").rmdir()
        lock.write_bytes(b"preexisting output")
        (out / "readback.json").unlink()
        blocked = subprocess.run(command, capture_output=True, timeout=3)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertEqual(lock.read_bytes(), b"preexisting output")
        self.assertFalse((out / "readback.json").exists())

    def test_missing_or_mismatched_stage_refuses(self):
        for relative in ("lock/linux-mixer.lock", "recipe/worker.py", "recipe/retained-products.json",
                         "android-sdk/build-tools/37.0.0/d8",
                         "python/bin/python3.12", self.project + "Generated/MixerSDK/Package.resolved"):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                mode = path.stat().st_mode & 0o777
                path.unlink()
                with self.assertRaises(pair25.LayoutError):
                    self.read()
                path.write_bytes(b"different bytes")
                path.chmod(mode)
                with self.assertRaisesRegex(pair25.LayoutError, "SHA-256 mismatch"):
                    self.read()
                path.write_bytes(original)
        with self.assertRaisesRegex(pair25.LayoutError, "SHA-256 mismatch"):
            pair25.Pair25Layout.read(self.root)
        (self.root / "python/bin/python3.12").chmod(0o644)
        with self.assertRaisesRegex(pair25.LayoutError, "is not executable"):
            self.read()

    def test_matching_digest_still_requires_only_toolchain_projection(self):
        self.linux["schema"] = 2
        self.products["inputHashes"]["localLinuxLockSHA256"] = self.write_json("lock/linux-mixer.lock", self.linux)
        self.products_pin = self.write_json("recipe/retained-products.json", self.products)
        with self.assertRaisesRegex(pair25.LayoutError, "changes fields beyond"):
            self.read()
        self.linux["schema"] = 1
        self.linux["android"]["toolchain"] = {"wrong": "toolchain"}
        self.products["inputHashes"]["localLinuxLockSHA256"] = self.write_json("lock/linux-mixer.lock", self.linux)
        self.products_pin = self.write_json("recipe/retained-products.json", self.products)
        with self.assertRaisesRegex(pair25.LayoutError, "Unexpected Linux lock toolchain"):
            self.read()

    def test_output_and_stage_cannot_escape_operator_root(self):
        layout = self.read()
        output = layout.output(self.name)
        output.rmdir()
        output.symlink_to(self.root / "recipe", target_is_directory=True)
        for name in (self.name, "../recipe", "/tmp", "mixer-l05-x,readonly"):
            with self.subTest(name=name), self.assertRaises(pair25.LayoutError):
                layout.create_arguments(name)
        with self.assertRaises(pair25.LayoutError):
            pair25.Pair25Layout.read(self.root / "outputs/..")
        with self.assertRaises(pair25.LayoutError):
            pair25.Pair25Layout.read(self.root / "bad,field")
        with TemporaryDirectory() as outside:
            external_file = Path(outside) / "linux-mixer.lock"
            lock = self.root / "lock/linux-mixer.lock"
            external_file.write_bytes(lock.read_bytes())
            lock.unlink()
            lock.symlink_to(external_file)
            with self.assertRaisesRegex(pair25.LayoutError, "Invalid staged path"):
                self.read()
        mirrors = self.root / "mirrors"
        mirrors.rename(self.root / "old-mirrors")
        mirrors.symlink_to(self.root / "old-mirrors", target_is_directory=True)
        with self.assertRaisesRegex(pair25.LayoutError, "Invalid staged path"):
            layout.recheck_stage()

    def test_prestart_detects_mutation_after_stage_admission(self):
        layout = self.read()
        self.write("lock/linux-mixer.lock", b"changed lock")
        with self.assertRaisesRegex(pair25.LayoutError, "Staged file changed"):
            layout.recheck_stage()
        self.write_json("lock/linux-mixer.lock", self.linux)
        layout = self.read()
        link = self.root / "lib64/ld-linux-x86-64.so.2"
        link.unlink()
        link.symlink_to("/lib/another-loader")
        with self.assertRaisesRegex(pair25.LayoutError, "loader link changed"):
            layout.recheck_stage()

    def test_recipe_and_volume_are_bound(self):
        layout = self.read()
        recipe = SimpleNamespace(image=pair25.IMAGE, image_id=pair25.MANIFEST, platform="linux/arm64",
                                 entrypoint="/bin/sh", arguments=pair25.ARGUMENTS)
        layout.verify_recipe(recipe)
        recipe.arguments = (*recipe.arguments[:-1], "lock")
        with self.assertRaises(pair25.LayoutError):
            layout.verify_recipe(recipe)
        volume = self.volume(layout)
        self.assertEqual(layout.volume_identity(volume), (volume["Mountpoint"], volume["CreatedAt"]))
        for field, value in {"Name": "unbound", "Driver": "other", "Options": {"o": "bind"}, "Labels": {},
                             "Mountpoint": "/foreign/_data", "CreatedAt": ""}.items():
            with self.subTest(field=field), self.assertRaises(pair25.LayoutError):
                layout.volume_identity(volume | {field: value})
        changed = volume | {"CreatedAt": "2026-11-20T05:22:01Z"}
        self.assertNotEqual(layout.volume_identity(volume), layout.volume_identity(changed))

    def test_offline_projection_admits_first_build_after_explicit_approval(self):
        driver = self.project_lock()
        project = self.root / self.project
        mac_lock = project / "mixer.lock"
        self.assertEqual(json.loads(mac_lock.read_bytes()), self.mac)
        with self.assertRaises(pair25.LayoutError):
            self.read_projection()
        approval = self.approve_projection()
        layout = self.read_projection()
        layout.recheck_stage()
        overlaid = self.root / "overlaid"
        shutil.copytree(project, overlaid)
        linux_lock = self.root / "lock/linux-mixer.lock"
        shutil.copyfile(linux_lock, overlaid / "mixer.lock")
        self.assertEqual(layout.verified_inputs, {
            "source_tree_sha256": driver.source_tree(overlaid),
            "linux_lock_sha256": sha(linux_lock.read_bytes()),
            "rendered_driver_sha256": sha((project / worker.DRIVER).read_bytes()),
        })
        self.assertEqual(layout.volume_labels, {
            "mixer.pair25.stage": str(self.root), "mixer.pair25.lock": layout.linux_lock_sha256,
            "mixer.pair25.projection": sha(approval.read_bytes()),
        })
        self.assertEqual(layout.image, f"docker.io/library/swift@{worker.SWIFT_MANIFEST}")
        for image_id in pair25.NOBLE_IMAGE_IDS:
            recipe = SimpleNamespace(image=layout.image, image_id=image_id, platform="linux/arm64",
                                     entrypoint="/bin/sh", arguments=pair25.ARGUMENTS)
            layout.verify_recipe(recipe)
        for field, value in {"image_id": pair25.IMAGE_IDS[1], "image": pair25.IMAGE,
                             "platform": "linux/amd64", "entrypoint": "/bin/bash",
                             "arguments": (*pair25.ARGUMENTS[:-1], "lock")}.items():
            with self.subTest(field=field), self.assertRaises(pair25.LayoutError):
                layout.verify_recipe(SimpleNamespace(**(vars(recipe) | {field: value})))
        self.assertIn("PAIR25_VERIFIED_SWIFT_MANIFEST=" + worker.SWIFT_MANIFEST,
                      layout.create_arguments(self.name))
        with approval.open("ab") as handle:
            handle.write(b"\n")
        with self.assertRaisesRegex(pair25.LayoutError, "Staged file changed at projection.json"):
            layout.recheck_stage()

    def test_projection_validation_refuses_bad_approval_or_stage(self):
        self.project_lock()
        approval = self.approve_projection()
        approval.chmod(0o644)
        with self.assertRaisesRegex(pair25.LayoutError, "operator-owned 0600 approval"):
            self.read_projection()
        approval.unlink()
        approval.symlink_to(self.root / "lock" / pair25.PROJECTION)
        with self.assertRaisesRegex(pair25.LayoutError, "Invalid staged path"):
            self.read_projection()
        approval.unlink()
        self.approve_projection()
        pins = json.loads(approval.read_bytes())
        for fields in ({"image": pair25.IMAGE}, {"schema": True}, {"source_tree_sha256": "x" * 64}):
            with self.subTest(fields=fields):
                self.write_json(pair25.PROJECTION, pins | fields)
                with self.assertRaisesRegex(pair25.LayoutError, "Invalid Pair25 projection approval"):
                    self.read_projection()
        approval.write_text('{"schema": 1, "schema": 1}')
        with self.assertRaisesRegex(pair25.LayoutError, "Duplicate JSON key"):
            self.read_projection()
        self.approve_projection()
        for relative in ("recipe/worker.py", "lock/linux-mixer.lock", self.project + worker.DRIVER):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(b"changed")
                with self.assertRaisesRegex(pair25.LayoutError, "SHA-256 mismatch"):
                    self.read_projection()
                path.write_bytes(original)
        for change, message in (
            ({"schema": 2}, "changes fields beyond android.toolchain"),
            ({"android": self.mac["android"] | {"toolchain": self.toolchain | {
                "distributions": {"swift_toolchain": {"path": "/", "sha256": pair25.MANIFEST[7:]}}}}},
             "not bound to the pinned Swift image"),
            ({"android": self.mac["android"] | {"toolchain": self.toolchain | {"tools": {
                "python": self.toolchain["tools"]["python"] | {"sha256": "f" * 64}}}}},
             "Unexpected Pair25 Noble Python tool"),
        ):
            with self.subTest(message=message):
                lock_sha = self.write_json("lock/linux-mixer.lock", self.linux | change)
                self.write_json(pair25.PROJECTION, pins | {"linux_lock_sha256": lock_sha})
                with self.assertRaisesRegex(pair25.LayoutError, message):
                    self.read_projection()

    def test_inspect_matches_generated_args_and_rejects_extra_or_writable_mounts(self):
        self.check_inspect(self.read())
        self.project_lock()
        self.approve_projection()
        self.check_inspect(self.read_projection())

    def check_inspect(self, layout):
        volume = layout.volume_identity(self.volume(layout))
        argv = layout.create_arguments(self.name)
        inherited = ["PATH=/usr/bin:/bin", "HOME=/root", "SWIFT_VERSION=6.3.3"]
        env = dict(row.split("=", 1) for row in inherited)
        mounts, requests, tmpfs = [], [], {}
        for i, argument in enumerate(argv):
            if argument == "--env":
                key, value = argv[i + 1].split("=", 1)
                env[key] = value
            if argument == "--tmpfs":
                target, options = argv[i + 1].split(":", 1)
                tmpfs[target] = options
            if argument == "--mount":
                fields = dict(piece.partition("=")[::2] for piece in argv[i + 1].split(","))
                kind, source, target = (fields[key] for key in ("type", "source", "target"))
                readonly = "readonly" in fields
                mount = {"Type": kind, "Source": source, "Destination": target, "RW": not readonly}
                request = {"Type": kind, "Source": source, "Target": target, "ReadOnly": readonly}
                if kind == "volume":
                    mount.update(Source=volume[0], Name=source, Driver="local")
                    request["VolumeOptions"] = {"NoCopy": "volume-nocopy" in fields}
                else:
                    request["BindOptions"] = {"NonRecursive": fields.get("bind-recursive") == "disabled"}
                mounts.append(mount)
                requests.append(request)
        config = {"Env": [f"{key}={value}" for key, value in env.items()], "Cmd": list(argv[-4:]),
                  "Entrypoint": [argv[-6]], "User": argv[argv.index("--user") + 1]}
        inspect = {"Config": config, "HostConfig": {"Tmpfs": tmpfs, "Mounts": requests}, "Mounts": mounts}
        layout.verify_container(inspect, self.name, volume, inherited)
        desktop = copy.deepcopy(inspect)
        desktop["Mounts"][-1]["Source"] = "/host_mnt" + mounts[-1]["Source"]
        desktop["HostConfig"]["Mounts"][-1]["Source"] = "/host_mnt" + requests[-1]["Source"]
        with patch.object(pair25.sys, "platform", "darwin"):
            layout.verify_container(desktop, self.name, volume, inherited)
            disagreement = copy.deepcopy(desktop)
            disagreement["HostConfig"]["Mounts"][-1]["Source"] = requests[-1]["Source"]
            with self.assertRaises(pair25.LayoutError):
                layout.verify_container(disagreement, self.name, volume, inherited)
        with patch.object(pair25.sys, "platform", "linux"), self.assertRaises(pair25.LayoutError):
            layout.verify_container(desktop, self.name, volume, inherited)
        for name, change in {
            "extra mount": lambda data: data["Mounts"].append(mounts[-1] | {"Destination": "/escape"}),
            "writable glibc": lambda data: data["Mounts"][0].update(RW=True),
            "wrong volume source": lambda data: data["Mounts"][-2].update(Source="/alias"),
            "wrong operation": lambda data: data["Mounts"][-1].update(Source=str(self.root / "outputs/sibling")),
            "altered env": lambda data: data["Config"]["Env"].append("LD_PRELOAD=/evil.so"),
            "duplicate env": lambda data: data["Config"]["Env"].append("HOME=/work/home"),
            "unbounded work": lambda data: data["HostConfig"]["Tmpfs"].update({"/work": "rw,exec"}),
            "recursive bind": lambda data: data["HostConfig"]["Mounts"][0]["BindOptions"].update(NonRecursive=False),
            "volume copy": lambda data: data["HostConfig"]["Mounts"][-2]["VolumeOptions"].update(NoCopy=False),
            "lock phase": lambda data: data["Config"]["Cmd"].__setitem__(-1, "lock"),
        }.items():
            wrong = copy.deepcopy(inspect)
            change(wrong)
            with self.subTest(name=name), self.assertRaises(pair25.LayoutError):
                layout.verify_container(wrong, self.name, volume, inherited)


if __name__ == "__main__":
    unittest.main()
