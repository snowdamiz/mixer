defmodule MixerHosted.RuntimeConfig do
  @moduledoc """
  Validated per-process configuration for the hosted control plane.

  Production database connections are direct and verify both certificate trust
  and hostname. Queue limits are per process; they are not organization quotas.
  """
  @derive {Inspect, only: [:role, :database_connection_bound]}
  @enforce_keys [:role, :repo, :oban, :endpoint, :database_connection_bound]
  defstruct @enforce_keys

  @queues [:builds, :signing, :submissions, :releases, :telemetry, :billing]

  def load!(env) when is_map(env) do
    role = role!(required!(env, "MIXER_HOSTED_ROLE"))
    hostname = hostname!(required!(env, "MIXER_DATABASE_HOST"))
    pool_size = integer!(env, "MIXER_DATABASE_POOL_SIZE", 8, 2..20)

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
        cacerts: :public_key.cacerts_get(),
        server_name_indication: String.to_charlist(hostname),
        customize_hostname_check: [match_fun: :public_key.pkix_verify_hostname_match_fun(:https)]
      ]
    ]

    queues =
      if role == :processor do
        for queue <- @queues do
          key = "MIXER_QUEUE_" <> String.upcase(Atom.to_string(queue)) <> "_CONCURRENCY"
          {queue, integer!(env, key, 1, 1..8)}
        end
      else
        []
      end

    %__MODULE__{
      role: role,
      repo: repo,
      oban: [
        repo: MixerHosted.Repo,
        notifier: Oban.Notifiers.Postgres,
        queues: queues,
        plugins: if(role == :api, do: false, else: []),
        peer: if(role == :api, do: false, else: Oban.Peers.Database),
        stager: [interval: if(role == :api, do: :infinity, else: 1_000)],
        shutdown_grace_period: 15_000
      ],
      endpoint: endpoint!(env, role),
      # Oban's Postgres notifier holds one additional direct connection.
      database_connection_bound: pool_size + 1
    }
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
