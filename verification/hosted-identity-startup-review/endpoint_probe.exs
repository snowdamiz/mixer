alias MixerHosted.Identity.{Manifest, StartupConfig, StartupFixture}
[der | _] = StartupFixture.standard_roots()
for {field, value} <- [{"host", "keys.independent.invalid\n"}, {"host", "keys.independent.invalid\r\n"}, {"path", "/keys\n"}, {"path", "/keys\r\n"}, {"host", "keys.independent.invalid"}] do
  raw = StartupFixture.envelope() |> put_in(["profiles", Access.at(0), "jwks_endpoint", field], value) |> Jason.encode!()
  result = try do
    config = StartupConfig.load!(%{"MIXER_IDENTITY_MODE" => "configured", "MIXER_IDENTITY_CONFIG" => raw}, :api, [der])
    {:ok, manifest} = Manifest.validate(config.owner_options[:manifest])
    {:accepted, map_size(manifest)}
  rescue
    exception -> {:rejected, Exception.message(exception)}
  end
  IO.inspect(%{field: field, syntheticValue: value, startupResult: result})
end
