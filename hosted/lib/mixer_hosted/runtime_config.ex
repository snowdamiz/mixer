defmodule MixerHosted.RuntimeConfig do
  @moduledoc """
  Validated per-process configuration for the hosted control plane.

  Production database connections are direct and verify both certificate trust
  and hostname. Queue limits are per process; they are not organization quotas.
  """
  @derive {Inspect, only: [:role, :database_connection_bound]}
  @enforce_keys [:role, :repo, :oban, :endpoint, :database_connection_bound, :identity_startup]
  defstruct @enforce_keys ++ [create_repo: nil, processor_profile: nil]

  @queues [:builds, :signing, :submissions, :releases, :telemetry, :billing]

  def load!(env) when is_map(env) do
    role = role!(required!(env, "MIXER_HOSTED_ROLE"))

    processor_profile =
      case Map.get(env, "MIXER_PROCESSOR_PROFILE") do
        "builds_v1" -> :builds_v1
        nil when role == :api -> nil
        _ -> invalid!("MIXER_PROCESSOR_PROFILE")
      end

    if role == :processor and required!(env, "MIXER_DATABASE_USER") != "mixer_build_processor",
      do: invalid!("MIXER_DATABASE_USER")

    if role == :processor do
      for q <- @queues -- [:builds] do
        key = "MIXER_QUEUE_" <> String.upcase(Atom.to_string(q)) <> "_CONCURRENCY"
        if Map.has_key?(env, key), do: invalid!(key)
      end
    end

    hostname = hostname!(required!(env, "MIXER_DATABASE_HOST"))
    pool_size = integer!(env, "MIXER_DATABASE_POOL_SIZE", 8, 2..20)

    ca_roots = :public_key.cacerts_get()

    identity_roots =
      Enum.map(ca_roots, fn
        {:cert, der, _decoded} -> der
        der -> der
      end)

    identity_startup = MixerHosted.Identity.StartupConfig.load!(env, role, identity_roots)

    repo = [
      hostname: hostname,
      port: 5432,
      database: required!(env, "MIXER_DATABASE_NAME"),
      username: required!(env, "MIXER_DATABASE_USER"),
      password: required!(env, "MIXER_DATABASE_PASSWORD"),
      pool_size: pool_size,
      pool_count: 1,
      timeout: 5_000,
      connect_timeout: 5_000,
      queue_target: 50,
      queue_interval: 1_000,
      show_sensitive_data_on_connection_error: false,
      ssl: [
        verify: :verify_peer,
        cacerts: ca_roots,
        server_name_indication: String.to_charlist(hostname),
        customize_hostname_check: [match_fun: :public_key.pkix_verify_hostname_match_fun(:https)]
      ]
    ]

    repo =
      if role == :processor,
        do:
          Keyword.put(
            repo,
            :after_connect,
            {MixerHosted.Builds.ProcessorAdmission, :after_connect, []}
          ),
        else: repo

    create_repo =
      if Map.get(env, "MIXER_BUILD_CREATE_ENABLED", "false") == "true" and role == :api do
        repo
        |> Keyword.put(:username, "mixer_build_create")
        |> Keyword.put(:password, required!(env, "MIXER_BUILD_CREATE_PASSWORD"))
        |> Keyword.put(:pool_size, 2)
      else
        nil
      end

    queues =
      if role == :processor do
        for queue <- [:builds] do
          key = "MIXER_QUEUE_" <> String.upcase(Atom.to_string(queue)) <> "_CONCURRENCY"
          {queue, integer!(env, key, 1, 1..8)}
        end
      else
        []
      end

    %__MODULE__{
      role: role,
      processor_profile: processor_profile,
      create_repo: create_repo,
      identity_startup: identity_startup,
      repo: repo,
      oban:
        if(role == :processor,
          do: MixerHosted.Builds.ProcessorProfile.oban(Keyword.fetch!(queues, :builds)),
          else: [
            repo: MixerHosted.Repo,
            name: Oban,
            engine: Oban.Engines.Basic,
            insert_trigger: role != :api,
            notifier: Oban.Notifiers.Postgres,
            queues: queues,
            plugins: if(role == :api, do: false, else: []),
            peer: if(role == :api, do: false, else: Oban.Peers.Database),
            stager: [interval: if(role == :api, do: :infinity, else: 1_000)],
            shutdown_grace_period: 15_000
          ]
        ),
      endpoint: endpoint!(env, role),
      # Oban's Postgres notifier holds one additional direct connection.
      database_connection_bound: pool_size + 1 + if(is_nil(create_repo), do: 0, else: 2)
    }
  end

  @doc false
  def installed_processor_profile do
    case MixerHosted.Application.startup() do
      {:ok, {%__MODULE__{processor_profile: profile}, _}} when profile in [nil, :builds_v1] ->
        profile

      _ ->
        nil
    end
  end

  defp role!("api"), do: :api
  defp role!("processor"), do: :processor
  defp role!(_), do: invalid!("MIXER_HOSTED_ROLE")

  defp hostname!(value) do
    labels = String.split(value, ".")

    valid =
      byte_size(value) <= 253 and length(labels) >= 2 and
        Enum.all?(labels, fn label ->
          byte_size(label) in 1..63 and
            Regex.match?(~r/\A[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\z/, label)
        end) and not Enum.any?(labels, &String.contains?(&1, "-pooler"))

    if valid, do: value, else: invalid!("MIXER_DATABASE_HOST")
  end

  defp endpoint!(_env, :processor), do: [server: false]

  defp endpoint!(env, :api) do
    secret = required!(env, "MIXER_SECRET_KEY_BASE")
    if byte_size(secret) < 64, do: invalid!("MIXER_SECRET_KEY_BASE")

    ip =
      case Map.get(env, "MIXER_HTTP_BIND", "127.0.0.1") do
        "127.0.0.1" -> {127, 0, 0, 1}
        "0.0.0.0" -> {0, 0, 0, 0}
        _ -> invalid!("MIXER_HTTP_BIND")
      end

    [
      server: true,
      http: [ip: ip, port: integer!(env, "MIXER_HTTP_PORT", 4000, 1..65_535)],
      secret_key_base: secret
    ]
  end

  defp required!(env, key) do
    case Map.get(env, key) do
      value when is_binary(value) and byte_size(value) in 1..4096 -> value
      _ -> invalid!(key)
    end
  end

  defp integer!(env, key, default, range) do
    case Integer.parse(Map.get(env, key, Integer.to_string(default))) do
      {value, ""} -> if value in range, do: value, else: invalid!(key)
      _ -> invalid!(key)
    end
  end

  defp invalid!(key), do: raise(ArgumentError, "invalid or missing hosted setting: " <> key)
end
