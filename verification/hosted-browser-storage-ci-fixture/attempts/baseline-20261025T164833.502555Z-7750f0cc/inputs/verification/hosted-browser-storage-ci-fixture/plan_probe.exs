Code.require_file("../../hosted/test/mixer_hosted/browser_auth/storage_fixture.exs", __DIR__)

defmodule StorageDirectoryPlanProbe do
  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  def run do
    Application.ensure_all_started(:ecto_sql)
    Application.ensure_all_started(:postgrex)
    Application.ensure_all_started(:jason)
    settings = [hostname: "127.0.0.1", port: F.port(), database: "browser_storage", pool_size: 4, log: false]
    {:ok, _} = Admin.start_link(settings ++ [username: "browser_admin"])
    {:ok, _} = Migration.start_link(settings ++ [username: "browser_admin", after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end])
    F.install!()
    F.q!(Admin, "GRANT USAGE ON SCHEMA public TO browser_ordinary")
    F.q!(Admin, "GRANT SELECT ON ALL TABLES IN SCHEMA public TO browser_ordinary")
    for helper <- ~w(profiles principals families credentials organization_heads project_heads),
      do: F.q!(Admin, "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO browser_ordinary")
    for t <- ~w(sessions session_vault oidc_attempts session_events),
      do: F.q!(Admin, "REVOKE SELECT ON public.mixer_browser_#{t} FROM browser_ordinary")
    for sql <- [
      "INSERT INTO public.mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)",
      "INSERT INTO public.mixer_authz_principals VALUES('person-1','human',true,0,1)",
      "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)",
      "INSERT INTO public.mixer_authz_families VALUES('ordinary-family','humans',1,'person-1',true,0,NULL,1)",
      "INSERT INTO public.mixer_authz_credentials VALUES('humans',1,'ordinary-jti','person-1','ordinary-family',true,0,NULL,1)",
      "INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES('org',true,'Organization')",
      "INSERT INTO public.mixer_authz_projects(organization_id,id,active,display_name) VALUES('org','project',true,'Project')",
      "INSERT INTO public.mixer_authz_memberships VALUES('membership','person-1','org',NULL,'all_projects','viewer',true,0,NULL,1)"
    ], do: F.q!(Admin, sql)
    c = F.connection!("browser_ordinary")
    before = settings(c)
    # Preserve default server cost thresholds; compare only the runtime's local policy.
    results = Enum.map([:inherited, :local_off], fn policy -> collect(c, policy, before) end)
    GenServer.stop(c)
    File.write!(Path.join(System.fetch_env!("MIXER_STORAGE_PLAN_OUTPUT"), "plan-summary.json"), Jason.encode!(%{inherited: before, results: results}, pretty: true))
  end

  defp settings(c) do
    Postgrex.query!(c, "SELECT current_user,session_user,pg_backend_pid(),current_setting('jit'),current_setting('jit_above_cost'),current_setting('jit_inline_above_cost'),current_setting('jit_optimize_above_cost'),current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout')", []).rows |> hd()
  end

  defp configure(c) do
    values = %{
      "profile_id" => "humans", "profile_version" => "1", "issuer" => "https://issuer.fixture",
      "client_id" => "console", "identity_class" => "human", "principal_id" => "person-1",
      "subject" => "subject-1", "family_id" => "ordinary-family", "credential_ref" => "ordinary-jti",
      "directory_mode" => "organizations", "action" => "workspace.read", "required_scope" => "mixer.workspace.read",
      "phase" => "directory", "project_id" => "", "application_id" => "", "environment_id" => "", "organization_id" => "",
      "token_issued_at" => Integer.to_string(F.now() - 5), "token_expires_at" => Integer.to_string(F.now() + 300)
    }
    Enum.each(values, fn {key, value} -> Postgrex.query!(c, "SELECT pg_catalog.set_config($1,$2,true)", ["mixer.authz." <> key, value]) end)
  end

  defp collect(c, policy, original) do
    Postgrex.query!(c, "BEGIN", [])
    if policy == :local_off, do: Postgrex.query!(c, "SET LOCAL jit = off", [])
    configure(c)
    inside = settings(c)
    sql = "SELECT id FROM public.mixer_authz_organizations ORDER BY id"
    [[plan]] = Postgrex.query!(c, "EXPLAIN (SETTINGS, FORMAT JSON) " <> sql, []).rows
    File.write!(Path.join(System.fetch_env!("MIXER_STORAGE_PLAN_OUTPUT"), "#{policy}-plan.json"), Jason.encode!(plan, pretty: true))
    started = System.monotonic_time(:microsecond)
    execution = Postgrex.query(c, "EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON) " <> sql, [], timeout: 5_000, queue: false)
    elapsed = System.monotonic_time(:microsecond) - started
    {result, outcome} = case execution do
      {:ok, %{rows: [[actual]]}} ->
        File.write!(Path.join(System.fetch_env!("MIXER_STORAGE_PLAN_OUTPUT"), "#{policy}-actual.json"), Jason.encode!(actual, pretty: true))
        Postgrex.query!(c, "COMMIT", [])
        {%{status: "ok", actual: hd(actual)}, "commit"}
      {:error, error} ->
        Postgrex.query!(c, "ROLLBACK", [])
        {%{status: "error", code: error.postgres.code, message: error.postgres.message}, "rollback"}
    end
    restored = settings(c)
    if restored != original, do: raise("transaction changed inherited settings")
    %{policy: policy, effective: inside, elapsed_microseconds: elapsed, outcome: outcome, restored: restored, result: result}
  end
end

StorageDirectoryPlanProbe.run()
