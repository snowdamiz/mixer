Code.ensure_loaded!(MixerHosted.Identity.KeyOwner); Code.ensure_loaded!(MixerHosted.Identity.KeyOwnerSupervisor); Code.ensure_loaded!(MixerHosted.Identity.JWKSTransport); values = %{fixture_owner: function_exported?(MixerHosted.Identity.KeyOwner, :start_fixture, 1), fixture_supervisor: function_exported?(MixerHosted.Identity.KeyOwnerSupervisor, :start_fixture, 1), fixture_transport: function_exported?(MixerHosted.Identity.JWKSTransport, :fetch_fixture, 6), startup_fixture: Code.ensure_loaded?(MixerHosted.Identity.StartupFixture), startup_dns_fixture: Code.ensure_loaded?(MixerHosted.Identity.StartupDNSFixture)}; IO.inspect(values, label: "production_test_export_exclusion"); true = Enum.all?(Map.values(values), &(&1 == false)); 
probe_name = MixerHosted.Identity.ProductionSupervisorFixtureProbe
probe_workers = Module.concat(probe_name, "FetchSupervisor")
probe_pointer = {MixerHosted.Identity.Admission, probe_name}
nil = Process.whereis(probe_name)
nil = Process.whereis(probe_workers)
:absent = :persistent_term.get(probe_pointer, :absent)
fixture_init_rejected =
  try do
    MixerHosted.Identity.KeyOwnerSupervisor.init({:fixture, [name: probe_name]})
    false
  rescue
    FunctionClauseError -> true
  end
true = fixture_init_rejected
nil = Process.whereis(probe_name)
nil = Process.whereis(probe_workers)
:absent = :persistent_term.get(probe_pointer, :absent)
IO.inspect(%{fixture_init_rejected: fixture_init_rejected, owner_absent: true,
             workers_absent: true, admission_absent: true},
           label: "production_key_owner_supervisor_fixture_init_exclusion")

