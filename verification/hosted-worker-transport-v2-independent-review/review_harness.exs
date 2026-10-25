{:ok, _} = Mix.State.start_link([])
Mix.env(:test)
{:ok, _} = Application.ensure_all_started(:ssl)
{:ok, _} = Application.ensure_all_started(:mint)
{:ok, _} = Application.ensure_all_started(:jason)
review = Path.dirname(__ENV__.file)
root = Path.join(review, "scratch/verification/hosted-worker-transport-v2")
build = Path.join(review, "build/test")
File.mkdir_p!(build)
relative = [
 "candidate/context/builds/dispatch.ex", "candidate/context/builds/lifecycle.ex",
 "candidate/context/identity/bounded_json.ex", "candidate/context/identity/bounded_tcp.ex",
 "candidate/context/identity/dns_resolver.ex", "candidate/context/identity/global_address.ex",
 "candidate/lib/mixer_hosted/builds/worker_config.ex", "candidate/lib/mixer_hosted/builds/worker_http_adapter.ex",
 "candidate/lib/mixer_hosted/builds/worker_transport.ex", "candidate/lib/mixer_hosted/builds/worker_wire.ex"
]
{:ok, compiled, %{compile_warnings: [], runtime_warnings: []}} =
 Kernel.ParallelCompiler.compile_to_path(Enum.map(relative, &Path.join(root,&1)), build, return_diagnostics: true)
allowed_prefixes = ["Elixir.MixerHosted.Builds.Dispatch", "Elixir.MixerHosted.Builds.Lifecycle", "Elixir.MixerHosted.Builds.Worker", "Elixir.Inspect.MixerHosted.Builds.Worker", "Elixir.MixerHosted.Identity.BoundedJSON", "Elixir.MixerHosted.Identity.BoundedTCP", "Elixir.MixerHosted.Identity.DNSResolver", "Elixir.MixerHosted.Identity.GlobalAddress"]
true = Enum.all?(compiled, fn m -> Enum.any?(allowed_prefixes,&String.starts_with?(Atom.to_string(m),&1)) end)
Code.prepend_path(build)
Code.require_file(Path.join(root,"candidate/test/support/worker_tls_fixture.ex"))
ExUnit.start(autorun: false, seed: 0, capture_log: true)
case System.argv() do
 ["baseline"] -> Enum.each(["worker_config", "worker_transport", "worker_wire"], &Code.require_file(Path.join(root,"candidate/test/mixer_hosted/builds/" <> &1 <> "_test.exs")))
 ["fault", name] ->
   Code.require_file(Path.join(root,"candidate/test/support/worker_v2_case.exs"))
   Code.require_file(Path.join(root,"candidate/test/fault_cases/" <> name <> "_test.exs"))
 ["independent", name] ->
   Code.require_file(Path.join(root,"candidate/test/support/worker_v2_case.exs"))
   Code.require_file(Path.join(review,"cases/" <> name <> "_test.exs"))
 _ -> System.halt(2)
end
r=ExUnit.run()
frozen=Enum.filter(:code.all_loaded(),fn {m,_} -> n=Atom.to_string(m);String.contains?(n,"Authority") or String.contains?(n,"Catalog") end)
[] = frozen
IO.puts(Jason.encode!(%{tests: r.total,failures: r.failures,skipped: r.skipped,excluded: r.excluded,frozen_modules_loaded: [],compiled_allowlist_verified: true,compiled_modules: Enum.map(compiled,&Atom.to_string/1)}))
System.halt(if r.failures==0,do: 0,else: 1)
