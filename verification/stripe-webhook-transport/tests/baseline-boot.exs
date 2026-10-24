root = System.fetch_env!("CAPTURE_SOURCE_DIR")
result = System.fetch_env!("CAPTURE_RESULT_DIR")
phase = System.fetch_env!("CAPTURE_PHASE")

for app <- [:logger, :crypto, :ssl, :plug, :bandit, :mint, :jason] do
  {:ok, _} = Application.ensure_all_started(app)
end

for {app, version} <- [
      plug: ~c"1.20.3",
      bandit: ~c"1.13.1",
      thousand_island: ~c"1.6.0",
      mint: ~c"1.11.0"
    ] do
  if Application.spec(app, :vsn) != version, do: raise("dependency identity mismatch")
end

defmodule MixerRawCapture.ProductionProbeAdapter do
  def get_http_protocol(_), do: :"HTTP/2"
  def read_req_body(state, _), do: {:ok, "a", state}
end

source = Path.join(root, "candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex")
Code.compiler_options(debug_info: true)
Application.put_env(:mixer_raw_capture_candidate, :test_build, false)
[{module, production}] = Code.compile_file(source)
File.mkdir_p!(Path.join(result, "production-beam"))

File.write!(
  Path.join(result, "production-beam/Elixir.MixerHosted.Billing.RawWebhookCapture.beam"),
  production
)

{:ok, {_, [atoms: atoms, exports: exports]}} = :beam_lib.chunks(production, [:atoms, :exports])

if Enum.any?(atoms, fn {_, a} -> a == MixerRawCapture.TestClock end),
  do: raise("production clock seam survived")

if Enum.sort(exports) != Enum.sort(__info__: 1, capture: 1, module_info: 0, module_info: 1),
  do: raise("unexpected public capture exports")

Process.put(:capture_clock_sequence, [0, 5000])

production_conn = %Plug.Conn{
  method: "POST",
  request_path: "/api/v1/webhooks/stripe",
  query_string: "",
  req_headers: [{"content-type", "application/json"}, {"stripe-signature", "x"}],
  adapter: {MixerRawCapture.ProductionProbeAdapter, :original},
  private: %{clock: fn -> 5000 end, raw_webhook_capture: "stale"}
}

{:ok, %{raw_body: "a"}, _} = MixerHosted.Billing.RawWebhookCapture.capture(production_conn)
if Process.get(:capture_clock_sequence) != [0, 5000], do: raise("production consumed test clock")
Process.delete(:capture_clock_sequence)

File.write!(
  Path.join(result, "production-policy.json"),
  Jason.encode!(
    %{
      testClockAtomPresent: false,
      productionClockSpoofIgnored: true,
      exports: Enum.map(exports, fn {n, a} -> [Atom.to_string(n), a] end),
      sha256: Base.encode16(:crypto.hash(:sha256, production), case: :lower)
    },
    pretty: true
  )
)

:code.purge(module)
:code.delete(module)
Code.require_file(Path.join(root, "tests/clock.exs"))
Application.put_env(:mixer_raw_capture_candidate, :test_build, true)
[{^module, test}] = Code.compile_file(source)
File.mkdir_p!(Path.join(result, "test-beam"))

File.write!(
  Path.join(result, "test-beam/Elixir.MixerHosted.Billing.RawWebhookCapture.beam"),
  test
)

Code.require_file(Path.join(root, "inputs/hosted/lib/mixer_hosted/billing/webhook_signature.ex"))
Code.require_file(Path.join(root, "tests/#{phase}.exs"))

