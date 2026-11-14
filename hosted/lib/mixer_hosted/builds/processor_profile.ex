defmodule MixerHosted.Builds.ProcessorProfile do
  @moduledoc "Fixed builds-only operator and runtime authority. Never installed by startup."
  @role "mixer_build_processor"
  @locker "mixer_build_capacity_locker_v1"
  @function "public.mixer_build_capacity_lock_v1(text,text)"
  @body "BEGIN\n IF current_setting('transaction_isolation') <> 'read committed' THEN RAISE EXCEPTION 'read committed required'; END IF;\n IF org IS NOT NULL AND (octet_length(org) NOT BETWEEN 1 AND 128) THEN RAISE EXCEPTION 'invalid organization'; END IF;\n IF plat IS NOT NULL AND plat NOT IN ('ios','android') THEN RAISE EXCEPTION 'invalid platform'; END IF;\n PERFORM pg_catalog.pg_advisory_xact_lock(1296648258,1);\n PERFORM id FROM public.mixer_build_fleet_capacity WHERE id='fleet' FOR UPDATE;\n IF plat IS NOT NULL THEN PERFORM platform FROM public.mixer_build_fleet_platform_capacities WHERE platform=plat FOR UPDATE; END IF;\n IF org IS NOT NULL THEN PERFORM organization_id FROM public.mixer_build_organization_capacities WHERE organization_id=org FOR UPDATE; END IF;\n IF org IS NOT NULL AND plat IS NOT NULL THEN PERFORM organization_id FROM public.mixer_build_capacities WHERE organization_id=org AND platform=plat FOR UPDATE; END IF;\nEND"
  @capacity [
    {"mixer_build_fleet_capacity", "id"},
    {"mixer_build_fleet_platform_capacities", "platform"},
    {"mixer_build_organization_capacities", "organization_id"},
    {"mixer_build_capacities", "organization_id"}
  ]
  @job_columns ~w(state attempt attempted_at attempted_by scheduled_at completed_at discarded_at cancelled_at errors meta)
  @queue "((queue = 'builds'::text) AND (worker = 'MixerHosted.Builds.Coordinator'::text))"
  @insert """
  (queue = 'builds' AND worker = 'MixerHosted.Builds.Coordinator' AND state = 'available' AND attempt = 0
    AND jsonb_typeof(args) = 'object'
    AND args ?& ARRAY['organization_id','project_id','application_id','build_id','platform','build_record_id','revision','attempt','fence','kind']
    AND args - ARRAY['organization_id','project_id','application_id','build_id','platform','build_record_id','revision','attempt','fence','kind'] = '{}'::jsonb
    AND args->>'kind' IN ('created','start','completed','cancel','retry','expire','stopped')
    AND EXISTS(SELECT 1 FROM public.mixer_builds b WHERE b.id::text = args->>'build_record_id'
      AND b.organization_id = args->>'organization_id' AND b.project_id = args->>'project_id'
      AND b.application_id = args->>'application_id' AND b.build_id = args->>'build_id'
      AND b.platform = args->>'platform' AND b.revision::text = args->>'revision'
      AND COALESCE(b.journal->'events'->-1->'event'->>'type','created') = args->>'kind'
      AND (SELECT (1+count(*))::text FROM jsonb_array_elements(b.journal->'events') e WHERE e->'event'->>'type'='retry') = args->>'attempt'
      AND (SELECT (1+count(*))::text FROM jsonb_array_elements(b.journal->'events') e WHERE e->'event'->>'type'<>'start') = args->>'fence'))
  """

  def oban(concurrency) when is_integer(concurrency) and concurrency in 1..8 do
    [
      name: Oban,
      repo: MixerHosted.Repo,
      engine: Oban.Engines.Basic,
      insert_trigger: true,
      notifier: MixerHosted.Builds.ProcessorNotifier,
      queues: [builds: concurrency],
      plugins: [],
      peer: Oban.Peers.Database,
      stager: [interval: 1_000],
      shutdown_grace_period: 15_000
    ]
  end

  def role, do: @role
  def locker, do: @locker
  def function, do: @function
  def body, do: @body
  def capacities, do: @capacity
  def profile!(:builds_v1), do: :builds_v1
  def profile!(_), do: raise(ArgumentError, "unsupported processor profile")

  def table_rights(role) when role in [@role, @locker] do
    capacity =
      Map.new(@capacity, fn {t, key} ->
        {t,
         %{table: ["SELECT"], columns: if(role == @locker, do: %{"UPDATE" => [key]}, else: %{})}}
      end)

    if role == @locker do
      capacity
    else
      Map.merge(capacity, %{
        "mixer_builds" => %{
          table: ["SELECT"],
          columns: %{"UPDATE" => ~w(journal revision updated_at)}
        },
        "mixer_build_reservations" => %{
          table: ["SELECT"],
          columns: %{
            "INSERT" =>
              ~w(build_record_id organization_id platform attempt worker_fence held terminal_event_id),
            "UPDATE" => ~w(organization_id platform attempt worker_fence held terminal_event_id)
          }
        },
        "mixer_build_coordinator_leases" => %{
          table: ["SELECT"],
          columns: %{
            "INSERT" => ~w(build_record_id owner_id epoch expires_at),
            "UPDATE" => ~w(owner_id epoch expires_at)
          }
        },
        "oban_jobs" => %{table: ["SELECT", "INSERT"], columns: %{"UPDATE" => @job_columns}},
        "oban_peers" => %{
          table: ["SELECT", "INSERT", "DELETE"],
          columns: %{"UPDATE" => ["expires_at"]}
        }
      })
    end
  end

  def create_policies do
    [
      ["mixer_builds", "processor_build_read", "r", true, [@role], "true", nil],
      ["mixer_builds", "processor_build_update", "w", true, [@role], "true", "true"],
      ["oban_jobs", "processor_job_read", "r", true, [@role], @queue, nil],
      ["oban_jobs", "processor_job_update", "w", true, [@role], @queue, @queue],
      ["oban_jobs", "processor_job_insert", "a", true, [@role], nil, insert_deparsed()]
    ]
  end

  # Exact expected catalog rendering; requires actual full-schema qualification.
  # A mismatch refuses admission; installation text is not runtime authority.
  defp insert_deparsed do
    "((queue = 'builds'::text) AND (worker = 'MixerHosted.Builds.Coordinator'::text) AND (state = 'available'::public.oban_job_state) AND (attempt = 0) AND (jsonb_typeof(args) = 'object'::text) AND (args ?& ARRAY['organization_id'::text, 'project_id'::text, 'application_id'::text, 'build_id'::text, 'platform'::text, 'build_record_id'::text, 'revision'::text, 'attempt'::text, 'fence'::text, 'kind'::text]) AND ((args - ARRAY['organization_id'::text, 'project_id'::text, 'application_id'::text, 'build_id'::text, 'platform'::text, 'build_record_id'::text, 'revision'::text, 'attempt'::text, 'fence'::text, 'kind'::text]) = '{}'::jsonb) AND ((args ->> 'kind'::text) = ANY (ARRAY['created'::text, 'start'::text, 'completed'::text, 'cancel'::text, 'retry'::text, 'expire'::text, 'stopped'::text])) AND (EXISTS ( SELECT 1\n   FROM public.mixer_builds b\n  WHERE (((b.id)::text = (oban_jobs.args ->> 'build_record_id'::text)) AND (b.organization_id = (oban_jobs.args ->> 'organization_id'::text)) AND (b.project_id = (oban_jobs.args ->> 'project_id'::text)) AND (b.application_id = (oban_jobs.args ->> 'application_id'::text)) AND (b.build_id = (oban_jobs.args ->> 'build_id'::text)) AND (b.platform = (oban_jobs.args ->> 'platform'::text)) AND ((b.revision)::text = (oban_jobs.args ->> 'revision'::text)) AND (COALESCE(((((b.journal -> 'events'::text) -> '-1'::integer) -> 'event'::text) ->> 'type'::text), 'created'::text) = (oban_jobs.args ->> 'kind'::text)) AND (( SELECT ((1 + count(*)))::text AS text\n           FROM jsonb_array_elements((b.journal -> 'events'::text)) e(value)\n          WHERE (((e.value -> 'event'::text) ->> 'type'::text) = 'retry'::text)) = (oban_jobs.args ->> 'attempt'::text)) AND (( SELECT ((1 + count(*)))::text AS text\n           FROM jsonb_array_elements((b.journal -> 'events'::text)) e(value)\n          WHERE (((e.value -> 'event'::text) ->> 'type'::text) <> 'start'::text)) = (oban_jobs.args ->> 'fence'::text))))))"
  end

  def auxiliary_policies do
    caps =
      Enum.flat_map(@capacity, fn {t, _} ->
        [
          policy(t, "processor_read", "r", @role, "true", nil),
          policy(t, "locker_read", "r", @locker, "true", nil),
          policy(t, "locker_lock", "w", @locker, "true", "false"),
          policy(t, "processor_maintenance", "*", "browser_schema_owner", "true", "true")
        ]
      end)

    domain =
      Enum.flat_map(~w(mixer_build_reservations mixer_build_coordinator_leases), fn t ->
        [
          policy(t, "processor_read", "r", @role, "true", nil),
          policy(t, "processor_insert", "a", @role, nil, "true"),
          policy(t, "processor_update", "w", @role, "true", "true"),
          policy(t, "processor_maintenance", "*", "browser_schema_owner", "true", "true")
        ]
      end)

    peer = "(name = 'Oban'::text)"

    caps ++
      domain ++
      [
        policy("oban_peers", "processor_read", "r", @role, peer, nil),
        policy("oban_peers", "processor_insert", "a", @role, nil, peer),
        policy("oban_peers", "processor_update", "w", @role, peer, peer),
        policy("oban_peers", "processor_delete", "d", @role, peer, nil),
        policy("oban_peers", "processor_maintenance", "*", "browser_schema_owner", "true", "true")
      ]
  end

  defp policy(t, n, c, r, u, w), do: [t, n, c, true, [r], u, w]

  def statements(:builds_v1) do
    roles = [
      "CREATE ROLE #{@role} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT",
      "CREATE ROLE #{@locker} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT",
      "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
      "REVOKE CREATE,TEMPORARY ON DATABASE " <> quote_ident_database() <> " FROM PUBLIC",
      "GRANT USAGE ON SCHEMA public TO #{@role},#{@locker}",
      "GRANT CONNECT ON DATABASE " <> quote_ident_database() <> " TO #{@role}"
    ]

    grants =
      for role <- [@role, @locker],
          {table, rights} <- table_rights(role),
          right <- rights.table,
          do: "GRANT #{right} ON public.#{table} TO #{role}"

    columns =
      for role <- [@role, @locker],
          {table, rights} <- table_rights(role),
          {right, cols} <- rights.columns,
          do: "GRANT #{right}(#{Enum.join(cols, ",")}) ON public.#{table} TO #{role}"

    rls =
      for table <- Map.keys(table_rights(@role)),
          sql <- [
            "ALTER TABLE public.#{table} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE public.#{table} FORCE ROW LEVEL SECURITY"
          ],
          do: sql

    policies =
      Enum.map(create_policies() ++ auxiliary_policies(), fn [t, n, c, _, [r], u, w] ->
        command =
          %{"r" => "SELECT", "w" => "UPDATE", "a" => "INSERT", "d" => "DELETE", "*" => "ALL"}[c]

        check = if n == "processor_job_insert", do: @insert, else: w

        "CREATE POLICY #{n} ON public.#{t} FOR #{command} TO #{r}" <>
          if(u, do: " USING(#{u})", else: "") <> if(check, do: " WITH CHECK(#{check})", else: "")
      end)

    roles ++
      grants ++
      columns ++
      rls ++
      policies ++
      [
        "GRANT USAGE ON SEQUENCE public.oban_jobs_id_seq TO #{@role}",
        "CREATE FUNCTION public.mixer_build_capacity_lock_v1(org text,plat text) RETURNS void LANGUAGE plpgsql VOLATILE CALLED ON NULL INPUT SECURITY DEFINER SET search_path=pg_catalog AS $body$#{@body}$body$",
        "ALTER FUNCTION #{@function} OWNER TO #{@locker}",
        "REVOKE ALL ON FUNCTION #{@function} FROM PUBLIC",
        "GRANT EXECUTE ON FUNCTION #{@function} TO #{@role},browser_schema_owner"
      ]
  end

  # Operator replaces this one documented psql variable before execution.
  defp quote_ident_database, do: ~s(:"processor_database")
end
