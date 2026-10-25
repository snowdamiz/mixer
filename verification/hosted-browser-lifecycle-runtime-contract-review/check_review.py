#!/usr/bin/env python3
"""Bounded documentation/source review controls; no application or database starts."""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
OUT = BASE / "attempts" / STAMP
OUT.mkdir(parents=True)
PATHS = [
    "AGENTS.md", "PLAN.md", "mixer-product-plan.md",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
    "docs/hosted-browser-session-storage-contract.md",
    "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
    "hosted/lib/mixer_hosted/browser_auth/protocol.ex",
    "hosted/lib/mixer_hosted/identity/configured_verifier.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
    "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
    "hosted/lib/mixer_hosted/identity/admission.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/runtime_config.ex",
    "hosted/lib/mixer_hosted/application.ex",
    "hosted/config/runtime.exs",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
    "hosted/test/mixer_hosted/browser_auth/storage_fixture.exs",
    "hosted/test/mixer_hosted/browser_auth/storage_spec.exs",
    "hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py",
    str((BASE / "probe.exs").relative_to(ROOT)),
    str(pathlib.Path(__file__).resolve().relative_to(ROOT)),
]

def text(path):
    return (ROOT / path).read_text()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def manifest():
    return {path: sha((ROOT / path).read_bytes()) for path in PATHS}

before = manifest()
commands = []

def command(name, argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
    (OUT / (name + ".stdout")).write_text(result.stdout)
    (OUT / (name + ".stderr")).write_text(result.stderr)
    commands.append({"argv": argv, "cwd": str(ROOT), "timeout_seconds": 30,
                     "exit_code": result.returncode, "stdout": name + ".stdout",
                     "stderr": name + ".stderr"})
    if result.returncode:
        raise RuntimeError(name + " failed")
    return result.stdout

head = command("head", ["git", "rev-parse", "HEAD"]).strip()
git = command("git-version", ["git", "--version"]).strip()
elixir = command("elixir-version", ["elixir", "--version"]).strip()
inventory = command("independent-inventory", ["elixir", str(BASE / "probe.exs")])
DOC = text("docs/hosted-browser-lifecycle-runtime-contract.md")
SQL = text("hosted/lib/mixer_hosted/browser_auth/storage_schema.ex")

class ReviewControls(unittest.TestCase):
    def test_existing_public_signatures_are_exact(self):
        expected = {}
        for line in inventory.splitlines():
            if line.startswith("signature|"):
                _, name, args, result = line.split("|")
                expected[name] = (args, result)
        actual = {}
        for name, args, result in re.findall(r"^public\.(mixer_browser_\w+)\(([^\n]*)\) -> (jsonb-or-NULL|jsonb|boolean)$", DOC, re.M):
            actual[name] = (args, result.replace("jsonb-or-NULL", "jsonb"))
        self.assertEqual(actual, expected)
        self.assertEqual(len(expected), 9)

    def test_manifest_is_eighteen_and_nine_not_proposed_nineteen(self):
        self.assertIn("functions=18\npublic=9\n", inventory)
        self.assertEqual(sum(line.startswith("manifest|") for line in inventory.splitlines()), 18)
        self.assertIn("There will be 19 admitted functions and 10 public EXECUTEs", DOC)
        self.assertNotIn('"mixer_browser_prepare_activation" =>', SQL)

    def test_preparation_has_six_exact_keys_and_existing_snapshot_shape(self):
        block = re.search(r'Return exactly:\s*```text\n(.*?)\n```', DOC, re.S).group(1)
        keys = re.findall(r'^  "([a-z_]+)":', block, re.M)
        self.assertEqual(keys, ["version", "snapshot", "principal_id", "profile_revision", "binding_revision", "principal_revision"])
        self.assertIn("all six top-level keys/types", DOC)
        snapshot = text("hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex")
        self.assertIn('exact!(input, ~w(browser vault attempt))', snapshot)
        self.assertIn('Enum.all?(@cipher_fields, &is_nil(a[&1]))', snapshot)

    def test_default_verifier_source_and_database_revision_absence(self):
        verifier = text("hosted/lib/mixer_hosted/identity/configured_verifier.ex")
        identity = text("hosted/lib/mixer_hosted/identity/verified_identity.ex")
        self.assertIn('def authenticate(token, now), do: authenticate(KeyOwner, :configured, token, now)', verifier)
        self.assertIn('case KeyOwner.finish(owner, lease)', verifier)
        self.assertNotIn(':profile_revision', identity)
        self.assertNotIn(':principal_id', identity)
        self.assertIn('No injected verifier, `authenticate/4`', DOC)

    def test_runtime_configuration_uses_actual_shared_startup_shape(self):
        runtime = text("hosted/lib/mixer_hosted/runtime_config.ex")
        startup = text("hosted/config/runtime.exs")
        self.assertIn(':identity_startup]', runtime)
        self.assertIn('settings = MixerHosted.RuntimeConfig.load!(System.get_env())', startup)
        self.assertIn('Config.load(browser_env, hosted_config.role, hosted_config.identity_startup)', DOC)
        self.assertIn('Struct shape alone proves no provenance', DOC)
        self.assertIn('actually supervised', DOC)

    def test_public_baseline_policies_are_explicitly_retained(self):
        authz = text("hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs")
        directory = text("hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs")
        self.assertIn('FOR SELECT USING (#{predicate})', authz)
        self.assertIn('FOR UPDATE USING (#{predicate}) WITH CHECK (false)', authz)
        self.assertIn('mixer_authz_memberships FOR SELECT USING (', directory)
        self.assertIn('baseline PUBLIC targets/predicates', DOC)
        self.assertIn('Reject additional/widened PUBLIC', DOC)

    def test_same_pid_manifest_change_is_not_claimed_observed(self):
        owner = text("hosted/lib/mixer_hosted/identity/key_owner.ex")
        self.assertIn('def replace_manifest(owner, expected, candidate)', owner)
        self.assertIn('generation: s.generation + 1', owner)
        self.assertIn('a process\nmonitor does not observe that change', DOC)
        self.assertIn('no current-generation read/notification\nAPI is assumed here', DOC)

    def test_aead_owner_boundaries_and_4089_byte_limit(self):
        vault = text("hosted/lib/mixer_hosted/browser_auth/vault.ex")
        self.assertIn('byte_size(value) in 1..4089', vault)
        self.assertIn('Vault.open/3', DOC)
        self.assertIn('Vault.seal/3', DOC)
        self.assertIn('4,089 bytes', DOC)
        self.assertIn('before the mutating transaction', DOC)

    def test_activation_lock_order_and_no_browser_prelock(self):
        activation = SQL.split('defp activation do', 1)[1].split('defp termination do', 1)[0]
        markers = ['PERFORM 1 FROM public.mixer_authz_profiles', 'PERFORM 1 FROM public.mixer_authz_principals',
                   'SELECT * INTO STRICT old_family', 'SELECT * INTO STRICT o FROM public.mixer_browser_sessions',
                   'SELECT * INTO a FROM public.mixer_browser_oidc_attempts', 'SELECT * INTO STRICT v']
        offsets = [activation.index(marker) for marker in markers]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn('without an earlier browser\n  SHARE lock', DOC)
        self.assertIn('one MVCC statement snapshot', DOC)

    def test_claim_is_caller_owned_one_use_and_not_durable_resume(self):
        for fragment in ['actual\nGenServer caller PID', '`exchange_started`', 'zero provider exchange',
                         'another replica cannot reconstruct the\nsecret or resume', 'no waiting queue']:
            self.assertIn(fragment, DOC)

    def test_first_slice_is_useful_and_authentication_remains_unavailable(self):
        self.assertIn('real preauth Vault/StoredSnapshot roundtrip', DOC)
        self.assertIn('explicitly rejected for facade authentication/workspace use', DOC)
        self.assertIn('`storage_ready` cannot enable a route', DOC)
        self.assertIn('pending runtime implementation', DOC)

    def test_operator_upgrade_and_uncertain_commit_fail_closed(self):
        for fragment in ['accepted initial provisioning plan must not be', 'silently replayed',
                         'Version-1 admission must reject the added surface', 'unknown commit outcome returns unavailable',
                         'never repair by resurrecting linkage', 'No error authorizes automatic retry']:
            self.assertIn(fragment, DOC)

with (OUT / "checks.txt").open("w") as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReviewControls))
after = manifest()
receipt = {
    "schema": 1, "kind": "independent-documentation-source-review", "head": head,
    "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Bounded ordinary browser/identity/authorization source review plus independent standalone StorageSchema inventory and twelve structural controls; no product runtime acceptance.",
    "status": "passed_documentation_review" if result.wasSuccessful() and before == after else "failed",
    "source_manifest": before, "source_unchanged": before == after,
    "source_tree_digest": sha(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()),
    "commands": commands, "review_command": [sys.executable, str(pathlib.Path(__file__).resolve())],
    "tools": {"python": sys.version, "git": git, "elixir": elixir},
    "checks": {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)},
    "cleanup": "Only terminated ordinary Elixir inventory subprocess; no PostgreSQL, native, capture or provider process started.",
    "pending": ["Catalog matrix and admission implementation", "Restricted-pool PostgreSQL/AEAD end-to-end runtime evidence", "Activation preparation migration/decoder and all runtime adversity cases", "Provider/OIDC/Neon/operator/custody qualification", "Browser/native/physical-device checks paused", "Customer/FieldLog and GA acceptance"],
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(BASE / "receipt.json").write_text(json.dumps(receipt | {"attempt": str(OUT.relative_to(BASE))}, indent=2) + "\n")
print(json.dumps({"attempt": str(OUT.relative_to(ROOT)), "status": receipt["status"], "checks": receipt["checks"]}))
sys.exit(0 if result.wasSuccessful() and before == after else 1)
