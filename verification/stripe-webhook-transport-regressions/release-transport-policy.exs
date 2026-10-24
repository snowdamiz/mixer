modules = [
  MixerHosted.Billing.WebhookTransport,
  MixerHosted.Billing.WebhookTransport.Sinks,
  MixerHosted.Billing.WebhookTransport.Guard,
  MixerHosted.Billing.WebhookTransport.Owner
]

helpers = [
  MixerRawCapture.TestClock,
  MixerRawCapture.FakeAdapter,
  MixerRawCapture.ProductionProbeAdapter,
  MixerRawCapture.CountingAdapter,
  MixerRawCapture.ComponentTest,
  MixerRawCapture.WireState,
  MixerRawCapture.LoggerHandler,
  MixerRawCapture.PrivatePlug,
  MixerRawCapture.WireHelpers,
  MixerRawCapture.WireTest,
  MixerPrivateNegative,
  PrivateTransportEvidence,
  PrivateTransportLogSink,
  PrivateTransportPlug,
  PrivateTransportHelpers,
  PrivateTransportTest,
  ReviewEvidence,
  ReviewSink,
  ReviewPlug,
  ReviewHelpers,
  ReviewIndependentTest,
  MixerHosted.Billing.RawWebhookCaptureTest.Adapter,
  MixerHosted.Billing.WebhookTransportTest,
  MixerHosted.Billing.WebhookTransportTest.ForbiddenAdapter
]

rows = Enum.map(modules, fn module ->
  Code.ensure_loaded!(module)
  path = :code.which(module)
  {:ok, {^module, [atoms: atoms, exports: exports]}} = :beam_lib.chunks(path, [:atoms, :exports])
  names = Enum.map(atoms, fn {_, atom} -> Atom.to_string(atom) end)
  false = Enum.any?(names, fn name ->
    String.starts_with?(name, ["Elixir.MixerRawCapture.", "Elixir.PrivateTransport", "Elixir.Review"])
  end)

  %{
    module: Atom.to_string(module),
    path: List.to_string(path),
    exports: Enum.map(exports, fn {name, arity} -> %{name: Atom.to_string(name), arity: arity} end),
    atoms: names,
    test_helper_atom_absent: true
  }
end)

false = Enum.any?(helpers, &Code.ensure_loaded?/1)
false = function_exported?(MixerHosted.Billing.WebhookTransport, :capture, 2)
false = function_exported?(MixerHosted.Billing.WebhookTransport, :dispose, 1)
true = Enum.sort(MixerHosted.Billing.WebhookTransport.__info__(:functions)) ==
  Enum.sort(capture: 1, child_spec: 1, dispose: 0, init: 1, start_link: 1, start_link: 2)

# This process only loads production modules. The candidate role is intentionally
# absent: the ordinary application has no transport child or activated listener.
nil = Process.whereis(MixerHosted.Billing.WebhookTransport.Owner)
nil = Process.whereis(MixerHosted.Billing.WebhookTransport.Sinks)
nil = Process.whereis(MixerHosted.Billing.WebhookTransport.Guards)

result = %{
  status: "passed",
  candidate_modules: rows,
  absent_helper_modules: Enum.map(helpers, &Atom.to_string/1),
  test_helpers_loaded: false,
  transport_capture_clock_or_adapter_argument: false,
  role_started: false,
  listener_started: false,
  scope: "Production release BEAM inspection; no transport role startup or public admission"
}

IO.inspect(result, label: "production_transport_policy", limit: :infinity)
IO.puts("production_transport_policy: passed; 4 production modules; test helpers absent; role inactive")
