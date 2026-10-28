from pathlib import Path
p=Path('hosted/scripts/test_identity_network_collector.py');s=p.read_text()
needle='class BudgetAndCommandControls(unittest.TestCase):'
insert='''    def _amendment_preflight_subject(self, directory, metadata):
        repository = COLLECTOR_PATH.resolve().parents[2]
        subject = self.make_collector(directory, lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("real command forbidden")))
        controls = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "docs/hosted-identity-production-network-ci-contract.md", ".github/workflows/identity-network.yml"]
        for path in controls:
            target = subject.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repository / path).read_bytes())
        def blobs(paths):
            return {path: metadata[path] if path.startswith("verification/") else (repository / path).read_bytes() for path in paths}
        subject.git_blobs = blobs
        calls = []
        def command(argv, *args, **kwargs):
            calls.append(argv)
            if argv == ["git", "--no-replace-objects", "rev-parse", "HEAD"]:
                return (subject.sha.encode(), b"", 0)
            if argv == ["git", "--version"] or argv[:2] == ["docker", "version"] or argv[:2] == ["docker", "pull"]:
                return (b"{}", b"", 0)
            if argv[:3] == ["docker", "image", "inspect"]:
                return (json.dumps([exact_image("pg" if argv[-1] == POSTGRES_REF else "test")]).encode(), b"", 0)
            raise AssertionError("unexpected command in pure collector preflight: " + repr(argv))
        subject.command = command
        return subject, calls

    def test_collect_refuses_missing_amendment_before_any_image_or_create_operation(self):
        metadata = exact_metadata()
        metadata.pop("verification/identity-network-image-amendment-v1/metadata/packet-manifest.json")
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, metadata)
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \\
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \\
                    mock.patch.object(subject, "create", side_effect=AssertionError("create before metadata admission")) as create:
                with self.assertRaises((collector.CollectorError, KeyError)):
                    subject.collect()
            self.assertFalse(create.called)
            self.assertFalse(any(argv[0] == "docker" for argv in calls))

    def test_collect_requires_actual_prepare_result_before_bootstrap(self):
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, exact_metadata())
            prepared = owned("prepare")
            inspected = {"Config": {"Env": [key + "=" + value for key, value in collector.BASE_ENV.items()]}}
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \\
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \\
                    mock.patch.object(collector.os, "readlink", return_value="net:[100]"), \\
                    mock.patch.object(subject, "create", return_value=prepared) as create, \\
                    mock.patch.object(subject, "inspect", return_value=inspected), \\
                    mock.patch.object(subject, "docker"), mock.patch.object(subject, "copy_in"), \\
                    mock.patch.object(subject, "execute", return_value=(b"IDENTITY_JSON={}\\n", b"", 0)) as execute:
                with self.assertRaisesRegex(collector.CollectorError, "prerequisite result incomplete"):
                    subject.collect()
            self.assertEqual([mock.call("prepare")], create.call_args_list)
            self.assertEqual([mock.call(prepared, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])], execute.call_args_list)
            self.assertFalse((subject.output / "bootstrap-plan.json").exists())


'''
assert needle in s;s=s.replace(needle,insert+needle);p.write_text(s)
