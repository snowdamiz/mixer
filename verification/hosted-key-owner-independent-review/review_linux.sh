set -eu
mkdir -p /private/tmp
elixir /workspace/linux_netns_setup.exs
elixir --version
mix --version
openssl version
uname -a
mix test --seed 0 test/mixer_hosted/identity/key_owner_test.exs test/mixer_hosted/identity/access_token_verifier_test.exs test/mixer_hosted/identity/key_owner_linux_network_test.exs test/mixer_hosted/identity/independent_adversarial_test.exs
elixir -e 'IO.inspect(Enum.filter(File.ls!("/private/tmp"), &String.starts_with?(&1,"mixer-key-owner-tls-")), label: "retained_fixture_key_directories")'
MIX_ENV=prod MIX_BUILD_PATH=/workspace/linux-prod-build mix release --path /workspace/linux-release
elixir -pa /workspace/linux-release/lib/mixer_hosted-0.1.0/ebin -e 'Code.ensure_loaded!(MixerHosted.Identity.JWKSTransport); Code.ensure_loaded!(MixerHosted.Identity.KeyOwner); values = %{fixture_transport_exported: function_exported?(MixerHosted.Identity.JWKSTransport,:fetch_fixture,6), fixture_owner_exported: function_exported?(MixerHosted.Identity.KeyOwner,:start_fixture,1), fixture_module_present: Code.ensure_loaded?(MixerHosted.Identity.TLSFixture), independent_fixture_present: Code.ensure_loaded?(MixerHosted.Identity.IndependentAdapterOwner)}; IO.inspect(values,label: "production_fixture_exclusion"); true = Enum.all?(Map.values(values), &(&1 == false))'
