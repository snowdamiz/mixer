for app <- [:logger, :crypto, :ssl, :plug, :bandit, :mint, :jason] do
  {:ok, _} = Application.ensure_all_started(app)
end

for {app, version} <- [
      plug: ~c"1.20.3",
      bandit: ~c"1.13.1",
      thousand_island: ~c"1.6.0",
      telemetry: ~c"1.4.2",
      mint: ~c"1.11.0"
    ] do
  true = Application.spec(app, :vsn) == version
end

root = System.fetch_env!("TRANSPORT_SOURCE")
result = System.fetch_env!("CAPTURE_RESULT_DIR")
Application.put_env(:mixer_raw_capture_candidate, :test_build, false)

modules =
  Code.compile_file(
    Path.join(root, "inputs/hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex")
  ) ++
    Code.compile_file(
      Path.join(root, "inputs/hosted/lib/mixer_hosted/billing/webhook_signature.ex")
    ) ++
    Code.compile_file(Path.join(root, "candidate/lib/mixer_hosted/billing/webhook_transport.ex"))

File.mkdir_p!(Path.join(result, "compiled"))
for {mod, beam} <- modules, do: File.write!(Path.join(result, "compiled/#{mod}.beam"), beam)
Code.require_file(Path.join(root, "tests/#{System.fetch_env!("TRANSPORT_PHASE")}.exs"))
