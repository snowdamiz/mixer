defmodule MixerHosted.BrowserAuth.RuntimeConfig do
  @moduledoc """
  Pure browser lifecycle settings derived from the trusted ordinary startup value.

  No application, environment, database, resolver, or running owner is consulted.
  Struct shape cannot attest startup provenance; later composition must pass the
  same ordinary RuntimeConfig to both supervised graphs. This starts no capability.
  """
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest, Custody, Vault}
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  @enforce_keys [
    :mode,
    :browser_config,
    :configuration_digest,
    :lifecycle_repo,
    :expected_roles,
    :custody
  ]
  defstruct @enforce_keys

  @error {:error, :session_unavailable}
  @hosted_keys ~w(role repo oban endpoint database_connection_bound identity_startup)a
  @repo_keys ~w(hostname port database username password pool_size pool_count timeout
    connect_timeout queue_target queue_interval show_sensitive_data_on_connection_error ssl)a
  @ssl_keys ~w(verify cacerts server_name_indication customize_hostname_check)a
  @lifecycle_keys ~w(username password writer_role relation_owner)a
  @browser_keys ~w(MIXER_BROWSER_AUTH_MODE MIXER_BROWSER_AUTH_CONFIG)

  @doc "Constructs disabled settings or one bounded dedicated lifecycle connection policy."
  def new(browser_env, %HostedConfig{} = hosted, lifecycle, custody) do
    with true <- exact_map?(hosted, [:__struct__ | @hosted_keys]),
         true <- browser_env?(browser_env),
         {:ok, config} <- Config.load(browser_env, hosted.role, hosted.identity_startup) do
      construct(config, hosted, lifecycle, custody)
    else
      _ -> @error
    end
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  def new(_, _, _, _), do: @error

  defp construct(%Config{mode: :disabled}, _hosted, nil, nil) do
    {:ok,
     %__MODULE__{
       mode: :disabled,
       browser_config: nil,
       configuration_digest: nil,
       lifecycle_repo: nil,
       expected_roles: nil,
       custody: nil
     }}
  end

  defp construct(%Config{mode: :configured} = config, hosted, lifecycle, custody) do
    with true <- exact_map?(lifecycle, @lifecycle_keys),
         true <- repo?(hosted.repo, hosted.database_connection_bound),
         true <- bounded_binary?(lifecycle.password),
         roles = %{
           lifecycle_login: lifecycle.username,
           writer: lifecycle.writer_role,
           relation_owner: lifecycle.relation_owner,
           ordinary_runtime_login: hosted.repo[:username]
         },
         true <- roles?(roles),
         {:ok, custody} <- custody(custody, config.session_vault_ref),
         {:ok, digest} <- ConfigurationDigest.digest(config) do
      {:ok,
       %__MODULE__{
         mode: :configured,
         browser_config: config,
         configuration_digest: digest,
         lifecycle_repo: lifecycle_repo(hosted.repo, lifecycle),
         expected_roles: roles,
         custody: custody
       }}
    else
      _ -> @error
    end
  end

  defp construct(_, _, _, _), do: @error

  defp custody(%Custody{reference: reference, key: %Vault.Key{} = key} = custody, reference) do
    with true <- exact_map?(custody, [:__struct__, :reference, :key]),
         true <- exact_map?(key, [:__struct__, :id, :bytes]),
         {:ok, validated} <-
           Custody.new(reference, %{
             reference: reference,
             key_id: key.id,
             key_bytes: key.bytes
           }) do
      {:ok, validated}
    else
      _ -> @error
    end
  end

  defp custody(_, _), do: @error

  defp browser_env?(env) when is_map(env) do
    Enum.all?(Map.keys(env), &(&1 in @browser_keys)) and
      case Map.get(env, "MIXER_BROWSER_AUTH_MODE", "disabled") do
        "disabled" -> not Map.has_key?(env, "MIXER_BROWSER_AUTH_CONFIG")
        "configured" -> exact_map?(env, @browser_keys)
        _ -> false
      end
  end

  defp browser_env?(_), do: false

  defp repo?(repo, connection_bound) do
    exact_keyword?(repo, @repo_keys) and host?(repo[:hostname]) and repo[:port] === 5432 and
      bounded_binary?(repo[:database]) and bounded_binary?(repo[:username]) and
      bounded_binary?(repo[:password]) and is_integer(repo[:pool_size]) and
      repo[:pool_size] in 2..20 and connection_bound === repo[:pool_size] + 1 and
      repo[:pool_count] === 1 and repo[:timeout] === 5_000 and
      repo[:connect_timeout] === 5_000 and repo[:queue_target] === 50 and
      repo[:queue_interval] === 1_000 and
      repo[:show_sensitive_data_on_connection_error] === false and
      tls?(repo[:ssl], repo[:hostname])
  end

  defp tls?(ssl, host) do
    # Compare the OTP policy itself; never evaluate a supplied callback.
    exact_keyword?(ssl, @ssl_keys) and ssl[:verify] === :verify_peer and
      ssl[:server_name_indication] === String.to_charlist(host) and roots?(ssl[:cacerts]) and
      exact_keyword?(ssl[:customize_hostname_check], [:match_fun]) and
      ssl[:customize_hostname_check][:match_fun] ===
        :public_key.pkix_verify_hostname_match_fun(:https)
  end

  defp roots?(roots) when is_list(roots) and roots != [] do
    Enum.all?(roots, fn
      {:cert, der, decoded} when is_binary(der) ->
        :public_key.pkix_decode_cert(der, :otp) === decoded

      der when is_binary(der) ->
        :public_key.pkix_decode_cert(der, :otp)
        true

      _ ->
        false
    end)
  end

  defp roots?(_), do: false

  defp lifecycle_repo(repo, lifecycle) do
    [
      hostname: repo[:hostname],
      port: repo[:port],
      database: repo[:database],
      username: lifecycle.username,
      password: lifecycle.password,
      pool_size: 2,
      pool_count: 1,
      timeout: 5_000,
      connect_timeout: 5_000,
      queue: false,
      show_sensitive_data_on_connection_error: false,
      ssl: repo[:ssl]
    ]
  end

  defp roles?(roles) do
    values = Map.values(roles)
    Enum.all?(values, &role?/1) and length(Enum.uniq(values)) == 4
  end

  # Keep the existing StorageSchema provisioning contract's restricted grammar.
  defp role?(name) when is_binary(name) and byte_size(name) in 1..63 do
    name != "public" and not String.starts_with?(name, "pg_") and
      name
      |> :binary.bin_to_list()
      |> Enum.with_index()
      |> Enum.all?(fn {byte, index} ->
        byte in ?a..?z or byte == ?_ or (index > 0 and byte in ?0..?9)
      end)
  end

  defp role?(_), do: false

  defp host?(host) when is_binary(host) and byte_size(host) in 1..253 do
    labels = :binary.split(host, ".", [:global])

    length(labels) >= 2 and
      match?({:error, _}, :inet.parse_address(String.to_charlist(host))) and
      Enum.all?(labels, fn label ->
        byte_size(label) in 1..63 and not String.contains?(label, "-pooler") and
          not String.starts_with?(label, "-") and not String.ends_with?(label, "-") and
          Enum.all?(:binary.bin_to_list(label), fn byte ->
            byte in ?a..?z or byte in ?0..?9 or byte == ?-
          end)
      end)
  end

  defp host?(_), do: false

  defp exact_map?(map, keys),
    do: is_map(map) and map_size(map) == length(keys) and Enum.all?(keys, &Map.has_key?(map, &1))

  defp exact_keyword?(options, keys),
    do:
      is_list(options) and Keyword.keyword?(options) and length(options) == length(keys) and
        Enum.sort(Keyword.keys(options)) == Enum.sort(keys)

  defp bounded_binary?(value), do: is_binary(value) and byte_size(value) in 1..4096
end

defimpl Inspect, for: MixerHosted.BrowserAuth.RuntimeConfig do
  def inspect(%{mode: :configured}, _options),
    do: "#MixerHosted.BrowserAuth.RuntimeConfig<mode: :configured, lifecycle_connection_bound: 2>"

  def inspect(%{mode: :disabled}, _options),
    do: "#MixerHosted.BrowserAuth.RuntimeConfig<mode: :disabled, lifecycle_connection_bound: 0>"

  def inspect(_, _options), do: "#MixerHosted.BrowserAuth.RuntimeConfig<unavailable>"
end
