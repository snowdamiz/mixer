defmodule MixerHosted.RuntimeConfig do
  @moduledoc """
  Validated per-process configuration for the hosted control plane.

  Production database connections are direct and verify both certificate trust
  and hostname. Queue limits are per process; they are not organization quotas.
  """
  @derive {Inspect, only: [:role, :database_connection_bound]}
  @enforce_keys [:role, :repo, :oban, :endpoint, :database_connection_bound, :identity_startup]
  defstruct @enforce_keys ++
              [
                create_repo: nil,
                processor_profile: nil,
                build_operation_intent: :disabled,
                build_cancel: false,
                native: nil,
                artifact_upload: nil
              ]

  @queues [
    :builds,
    :signing,
    :submissions,
    :releases,
    :telemetry,
    :billing,
    :billing_reconciliation
  ]

  def load!(env) when is_map(env) do
    role = role!(required!(env, "MIXER_HOSTED_ROLE"))

    processor_profile =
      case Map.get(env, "MIXER_PROCESSOR_PROFILE") do
        "builds_v1" -> :builds_v1
        "billing_v1" when role == :processor -> :billing_v1
        nil when role == :api -> nil
        _ -> invalid!("MIXER_PROCESSOR_PROFILE")
      end

    build_operation_intent =
      case Map.fetch(env, "MIXER_BUILD_OPERATION_INTENT") do
        :error ->
          :disabled

        {:ok, "durable_intent_v1"} when role == :processor and processor_profile == :builds_v1 ->
          :durable_intent_v1

        _ ->
          invalid!("MIXER_BUILD_OPERATION_INTENT")
      end

    profile =
      if processor_profile == :billing_v1,
        do: MixerHosted.Billing.ProcessorProfile,
        else: MixerHosted.Builds.ProcessorProfile

    queue = if processor_profile == :billing_v1, do: :billing_reconciliation, else: :builds

    if role == :processor and required!(env, "MIXER_DATABASE_USER") != profile.role(),
      do: invalid!("MIXER_DATABASE_USER")

    if role == :processor do
      for q <- @queues -- [queue] do
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
            processor_admission(processor_profile, build_operation_intent)
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

    endpoint = endpoint!(env, role)

    build_cancel =
      case Map.fetch(env, "MIXER_BUILD_CANCEL_ENABLED") do
        :error ->
          false

        {:ok, "false"} ->
          false

        {:ok, "true"}
        when role == :api and processor_profile == :builds_v1 and is_list(create_repo) ->
          true

        _ ->
          invalid!("MIXER_BUILD_CANCEL_ENABLED")
      end

    native = native!(env, role, processor_profile, build_operation_intent, endpoint)

    queues =
      if role == :processor do
        for queue <- [queue] do
          key = "MIXER_QUEUE_" <> String.upcase(Atom.to_string(queue)) <> "_CONCURRENCY"
          {queue, integer!(env, key, 1, 1..8)}
        end
      else
        []
      end

    %__MODULE__{
      role: role,
      processor_profile: processor_profile,
      build_operation_intent: build_operation_intent,
      create_repo: create_repo,
      identity_startup: identity_startup,
      repo: repo,
      oban:
        if(role == :processor,
          do: profile.oban(Keyword.fetch!(queues, queue)),
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
      endpoint: endpoint,
      build_cancel: build_cancel,
      native: native,
      # Oban's Postgres notifier holds one additional direct connection.
      database_connection_bound: pool_size + 1 + if(is_nil(create_repo), do: 0, else: 2)
    }
  end

  @doc false
  def processor_admission(:builds_v1, :disabled),
    do: {MixerHosted.Builds.ProcessorAdmission, :after_connect, []}

  def processor_admission(:builds_v1, :durable_intent_v1),
    do: {MixerHosted.Builds.ProcessorAdmission, :after_connect, [:durable_intent_v1]}

  def processor_admission(:billing_v1, :disabled),
    do: {MixerHosted.Billing.ProcessorAdmission, :after_connect, []}

  @doc false
  def installed_processor_profile do
    case MixerHosted.Application.startup() do
      {:ok, {%__MODULE__{processor_profile: profile}, _}}
      when profile in [nil, :builds_v1, :billing_v1] ->
        profile

      _ ->
        nil
    end
  end

  @doc false
  def build_cancel_enabled? do
    match?(
      {:ok, {%__MODULE__{role: :api, build_cancel: true}, _}},
      MixerHosted.Application.startup()
    )
  end

  @doc false
  def native_settings do
    case MixerHosted.Application.startup() do
      {:ok, {%__MODULE__{native: native}, _}} ->
        native

      :error ->
        if Process.whereis(MixerHosted.Supervisor) == nil and
             Application.fetch_env(:mixer_hosted, :startup) == :error,
           do: Application.get_env(:mixer_hosted, :native_development_dispatch)
    end
  end

  defp native!(env, role, profile, intent, endpoint) do
    root = Map.get(env, "MIXER_NATIVE_RETAINED_ROOT")
    worker_keys = ~w(MIXER_NATIVE_WORKER_PORT MIXER_NATIVE_WORKER_ID MIXER_NATIVE_WORKER_TOKEN)
    worker_configured? = Enum.any?(worker_keys, &Map.has_key?(env, &1))

    case Map.fetch(env, "MIXER_BUILD_DISPATCH") do
      :error when is_nil(root) and not worker_configured? ->
        nil

      :error when role == :api and profile == :builds_v1 and not worker_configured? ->
        if endpoint[:http][:ip] != {127, 0, 0, 1}, do: invalid!("MIXER_HTTP_BIND")
        %{retained_root: native_root!(root)}

      {:ok, "native_development_v1"}
      when role == :processor and profile == :builds_v1 and intent == :durable_intent_v1 ->
        required!(env, "MIXER_NATIVE_WORKER_PORT")
        id = required!(env, "MIXER_NATIVE_WORKER_ID")
        token = required!(env, "MIXER_NATIVE_WORKER_TOKEN")

        if not Regex.match?(~r/\A[a-zA-Z0-9_.-]{1,128}\z/, id),
          do: invalid!("MIXER_NATIVE_WORKER_ID")

        if byte_size(token) not in 32..256 or not String.printable?(token),
          do: invalid!("MIXER_NATIVE_WORKER_TOKEN")

        %{
          port: integer!(env, "MIXER_NATIVE_WORKER_PORT", 0, 1..65_535),
          worker_id: id,
          token: token,
          retained_root: native_root!(root)
        }

      _ ->
        invalid!("MIXER_BUILD_DISPATCH")
    end
  end

  defp native_root!(root) when is_binary(root) and byte_size(root) in 2..4096 do
    if String.starts_with?(root, "/") and root == Path.expand(root) and String.printable?(root),
      do: root,
      else: invalid!("MIXER_NATIVE_RETAINED_ROOT")
  end

  defp native_root!(_), do: invalid!("MIXER_NATIVE_RETAINED_ROOT")

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
      http: [
        ip: ip,
        port: integer!(env, "MIXER_HTTP_PORT", 4000, 1..65_535),
        http_2_options: [enabled: false]
      ],
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
