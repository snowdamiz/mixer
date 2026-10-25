Mix.start()
Mix.env(:test)
for {app, expected} <- %{:jason => "1.4.5", :jose => "1.11.12"} do
  :ok = Application.load(app)
  actual = Application.spec(app, :vsn) |> to_string()
  if actual != expected, do: raise("dependency runtime version mismatch: #{app}")
end
Application.put_env(:jose, :json_module, :jose_json_jason)
Application.put_env(:jose, :unsecured_signing, false)
Application.put_env(:jose, :crypto_fallback, false)
{:ok, _} = Application.ensure_all_started(:jose)
{:ok, _, %{compile_warnings: [], runtime_warnings: []}} = Kernel.ParallelCompiler.compile(["/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/lib/mixer_hosted/identity/verified_identity.ex", "/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/lib/mixer_hosted/identity/encoding.ex", "/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/lib/mixer_hosted/identity/bounded_json.ex", "/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/lib/mixer_hosted/identity/manifest.ex", "/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/lib/mixer_hosted/identity/trust_snapshot.ex", "/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/lib/mixer_hosted/identity/access_token_verifier.ex"], return_diagnostics: true)
ExUnit.start(seed: 0)
for path <- ["/Users/andreyyurlov/Documents/dev/mixer/verification/hosted-workspace-token-scope/run-3/inputs/hosted/test/mixer_hosted/identity/access_token_verifier_test.exs"], do: Code.require_file(path)
