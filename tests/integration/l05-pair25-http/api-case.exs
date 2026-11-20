# Included in the pinned LocalStarterHTTPSQLTest module by run.py. Reuse its private HTTP helpers.
@tag :pair25_http
@tag timeout: 1_300_000
test "serve one ordinary Android build for the Pair25 fixture", c do
  owner = login(c)
  org = create(c, owner, "/console-api/v1/orgs", %{display_name: "Pair25 owner"})
  scope = register_app(c, owner, org, "Pair25 project")
  outsider = pair25_outsider(c)
  other_org = create(c, outsider, "/console-api/v1/orgs", %{display_name: "Pair25 outsider"})
  assert org != other_org
  register_app(c, outsider, other_org, "Other project")

  pins =
    Path.join(System.fetch_env!("PAIR25_RUN"), "inputs.json") |> File.read!() |> Jason.decode!()

  source = pins["source_tree_sha256"]
  lock = pins["linux_lock_sha256"]
  recipe = pins["recipe_sha256"]
  input = "pair25-" <> source
  reference = "starter-" <> source

  # Stock verified-input relation. The Linux layout is operator-registered.
  assert %{num_rows: 1} =
           DB.q!(
             Migration,
             """
             INSERT INTO public.mixer_customer_build_inputs
               (organization_id,project_id,application_id,platform,input_id,source_kind,
                source_reference,source_sha256,toolchain_lock_sha256,build_definition_sha256,
                max_attempts,timeout_ms,retry_backoff_ms)
             VALUES($1,$2,$3,'android',$4,'revision',$5,$6,$7,$8,1,1200000,0)
             """,
             [
               scope.organization_id,
               scope.project_id,
               scope.application_id,
               input,
               reference,
               source,
               lock,
               recipe
             ]
           )

  build =
    Map.merge(scope, %{
      platform: "android",
      source_input_id: input,
      source_sha256: source,
      toolchain_lock_sha256: lock,
      build_definition_sha256: recipe
    })

  {cookie, csrf} = login(c)

  pair25_publish!("api.ready", %{
    port: c.http_port,
    issuer: c.provider_port,
    jwks: GenServer.call(c.fixture, :authority).port,
    origin: c.config.public_origin,
    build: build,
    source_reference: reference,
    cookie: cookie,
    csrf: csrf
  })

  pair25_wait!(c, false, System.monotonic_time(:millisecond) + 1_240_000)
end

defp pair25_outsider(c) do
  :ok = GenServer.call(c.provider, {:pair25_subject, "subject-2"})

  try do
    login(c)
  after
    :ok = GenServer.call(c.provider, {:pair25_subject, "subject-1"})
  end
end

defp pair25_wait!(c, renewed, deadline) do
  assert System.monotonic_time(:millisecond) < deadline

  cond do
    File.regular?(pair25_path("api.done")) ->
      :ok

    not renewed and File.regular?(pair25_path("api.refresh")) ->
      {owner, _} = login(c)
      {outsider, _} = pair25_outsider(c)
      pair25_publish!("api.sessions", %{owner: owner, outsider: outsider})
      pair25_wait!(c, true, deadline)

    true ->
      Process.sleep(50)
      pair25_wait!(c, renewed, deadline)
  end
end

defp pair25_publish!(name, data) do
  File.write!(pair25_path(name <> ".tmp"), Jason.encode!(data), [:exclusive])
  File.rename!(pair25_path(name <> ".tmp"), pair25_path(name))
end

defp pair25_path(name), do: Path.join(System.fetch_env!("PAIR25_RUN"), name)

defp pair25_processor!(c) do
  alias MixerHosted.Builds.ProcessorProfile

  for version <- [20_261_110_000_498, 20_261_110_000_499, 20_261_110_000_500] do
    [path] = Path.wildcard("priv/unselected_operation_admission/#{version}_*.exs")
    [{module, _}] = Code.require_file(path)
    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
  end

  for sql <- ProcessorProfile.statements(:builds_v1) do
    DB.q!(
      Admin,
      String.replace(sql, ~s(:"processor_database"), "browser_ordinary_installation_r1422")
    )
  end

  for sql <- ProcessorProfile.operation_intent_statements(:durable_intent_v1),
      do: DB.q!(Admin, sql)

  for sql <- SelfServiceSchema.processor_policy_statements(), do: DB.q!(Migration, sql)

  DB.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES('person-2','human',true,0,1)")

  DB.q!(
    Admin,
    "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-2','human','person-2',true,1)"
  )

  DB.q!(
    Admin,
    ~s(UPDATE mixer_build_fleet_capacity SET configured=true,"limit"=1,revision=1 WHERE id='fleet')
  )

  DB.q!(
    Admin,
    ~s(UPDATE mixer_build_fleet_platform_capacities SET configured=true,"limit"=1,revision=1 WHERE platform='android')
  )

  c
  |> put_in([:hosted, Access.key(:processor_profile)], :builds_v1)
  |> put_in([:hosted, Access.key(:native)], %{retained_root: pair25_path("worker")})
end
