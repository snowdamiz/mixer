# Production-mode constructor checks using the locked Jason source, without an app or database.
[jason_lib] = System.argv()
root = Path.expand("../..", __DIR__)
Mix.start()
Mix.env(:prod)
{:ok, _} = Application.ensure_all_started(:public_key)
jason_sources = Path.wildcard(Path.join(jason_lib, "**/*.ex"))
true = jason_sources != []

{_, []} =
  Code.with_diagnostics(fn ->
    {:ok, _, _} = Kernel.ParallelCompiler.compile(jason_sources, return_diagnostics: true)
  end)

false = Code.ensure_loaded?(MixerHosted.Application)
startup_counter = :counters.new(1, [])
:persistent_term.put({MixerHosted.Application, :constructor_calls}, startup_counter)

defmodule MixerHosted.Application do
  def startup do
    :counters.add(:persistent_term.get({__MODULE__, :constructor_calls}), 1, 1)
    raise "Application startup is outside the secret-constructor harness"
  end
end

inputs = [
  "hosted/lib/mixer_hosted/identity/encoding.ex",
  "hosted/lib/mixer_hosted/identity/manifest.ex",
  "hosted/lib/mixer_hosted/identity/bounded_json.ex",
  "hosted/lib/mixer_hosted/identity/startup_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/config.ex",
  "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
  "hosted/lib/mixer_hosted/builds/processor_profile.ex",
  "hosted/lib/mixer_hosted/runtime_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/vault.ex",
  "hosted/lib/mixer_hosted/browser_auth/custody.ex",
  "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/provider_trust_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex"
]

{_, []} =
  Code.with_diagnostics(fn ->
    Enum.each(inputs, &Code.require_file(Path.join(root, &1)))
  end)

ExUnit.start(autorun: false, seed: 0, trace: true)
test = "hosted/test/mixer_hosted/browser_auth/startup_secrets_test.exs"
{_, []} = Code.with_diagnostics(fn -> Code.require_file(Path.join(root, test)) end)
result = ExUnit.run()
0 = :counters.get(startup_counter, 1)

false =
  Enum.any?(Application.started_applications(), fn {name, _, _} ->
    name in [:mixer_hosted, :ecto_sql, :postgrex, :oban, :phoenix]
  end)

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
    compile_diagnostics: [],
    fake_leaves: ["MixerHosted.Application.startup/0"],
    fake_leaf_calls: 0,
    application_or_database_started: false,
    production_activation: false
  })
)

if result.failures != 0 or result.total != 8 or result.skipped != 0, do: System.halt(1)
