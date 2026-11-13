# Run with elixir and the lib directory of the locked Jason 1.4.5 source:
# elixir hosted/scripts/check-provider-trust-config.exs /path/to/jason/lib
[jason_lib] = System.argv()
root = Path.expand("../..", __DIR__)
Mix.start()
Mix.env(:prod)
{:ok, _} = Application.ensure_all_started(:public_key)
jason_sources = Path.wildcard(Path.join(jason_lib, "**/*.ex"))
true = jason_sources != []
{:ok, _, []} = Kernel.ParallelCompiler.compile(jason_sources)

inputs = [
  "hosted/lib/mixer_hosted/identity/encoding.ex",
  "hosted/lib/mixer_hosted/identity/manifest.ex",
  "hosted/lib/mixer_hosted/identity/bounded_json.ex",
  "hosted/lib/mixer_hosted/identity/startup_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/config.ex",
  "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
  "hosted/lib/mixer_hosted/runtime_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/vault.ex",
  "hosted/lib/mixer_hosted/browser_auth/custody.ex",
  "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/provider_trust_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex",
  "hosted/lib/mixer_hosted/browser_auth/installation.ex"
]

Enum.each(inputs, &Code.require_file(Path.join(root, &1)))
ExUnit.start(autorun: false, seed: 0, trace: true)
test = "hosted/test/mixer_hosted/browser_auth/provider_trust_config_test.exs"
Code.require_file(Path.join(root, test))
result = ExUnit.run()

identities =
  Map.new(inputs ++ [test], fn path ->
    bytes = File.read!(Path.join(root, path))

    {path,
     %{bytes: byte_size(bytes), sha256: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)}}
  end)

IO.puts(
  Jason.encode!(%{
    result: result,
    source: identities,
    elixir: System.version(),
    otp: List.to_string(:erlang.system_info(:otp_release)),
    mix_env: Mix.env(),
    jason_sources: length(jason_sources),
    production_activation: false
  })
)

if result.failures != 0 or result.total != 12 or result.skipped != 0, do: System.halt(1)
