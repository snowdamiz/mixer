defmodule MixerHosted.Builds.WorkerConfig do
  @moduledoc "Restart-scoped operator worker configuration. Disabled unless explicit."
  alias MixerHosted.Builds.WorkerWire
  alias MixerHosted.Identity.GlobalAddress
  @derive {Inspect, only: [:mode]}
  defstruct mode: :disabled,
            endpoint: nil,
            environment_id: nil,
            pool_id: nil,
            controller_id: nil,
            platforms: [],
            resolvers: [],
            ca_roots: [],
            token: nil

  def load!(env, role, roots) when is_map(env) do
    case Map.get(env, "MIXER_BUILD_WORKER_MODE", "disabled") do
      "disabled" ->
        if Map.has_key?(env, "MIXER_BUILD_WORKER_CONFIG") or
             Map.has_key?(env, "MIXER_BUILD_WORKER_TOKEN"),
           do: invalid!()

        %__MODULE__{}

      "configured" when role == :processor ->
        configured!(env, roots)

      _ ->
        invalid!()
    end
  end

  def load!(_, _, _), do: invalid!()

  @doc false
  def validated?(%__MODULE__{mode: :configured} = c) do
    raw =
      Jason.encode!(%{
        "version" => 1,
        "endpoint" => c.endpoint,
        "environment_id" => c.environment_id,
        "pool_id" => c.pool_id,
        "controller_id" => c.controller_id,
        "platforms" =>
          Enum.map(c.platforms, fn
            :ios -> "ios"
            :android -> "android"
          end),
        "resolvers" =>
          Enum.map(c.resolvers, fn {ip, 53} -> :inet.ntoa(ip) |> List.to_string() end)
      })

    load!(
      %{
        "MIXER_BUILD_WORKER_MODE" => "configured",
        "MIXER_BUILD_WORKER_CONFIG" => raw,
        "MIXER_BUILD_WORKER_TOKEN" => c.token
      },
      :processor,
      c.ca_roots
    ) === c
  rescue
    _ -> false
  catch
    _, _ -> false
  end

  def validated?(_), do: false

  defp configured!(env, roots) do
    with {:ok, v} <- WorkerWire.object(Map.get(env, "MIXER_BUILD_WORKER_CONFIG"), 4_096),
         true <-
           exact?(
             v,
             ~w(version endpoint environment_id pool_id controller_id platforms resolvers)
           ),
         1 <- v["version"],
         true <- Enum.all?(~w(environment_id pool_id controller_id), &id?(v[&1])),
         endpoint = v["endpoint"],
         true <- exact?(endpoint, ~w(host port path)),
         true <- hostname?(endpoint["host"]),
         443 <- endpoint["port"],
         "/internal/mixer-build-worker/v1" <- endpoint["path"],
         platforms when is_list(platforms) and length(platforms) in 1..2 <- v["platforms"],
         true <-
           length(Enum.uniq(platforms)) == length(platforms) and
             Enum.all?(platforms, &(&1 in ["ios", "android"])),
         resolvers when is_list(resolvers) and length(resolvers) in 1..3 <- v["resolvers"],
         true <-
           Enum.all?(resolvers, &resolver?/1) and
             length(Enum.uniq(resolvers)) == length(resolvers),
         token when is_binary(token) and byte_size(token) == 43 <- env["MIXER_BUILD_WORKER_TOKEN"],
         {:ok, bytes} <- Base.url_decode64(token, padding: false),
         true <- byte_size(bytes) == 32,
         ^token <- Base.url_encode64(bytes, padding: false),
         true <- roots?(roots) do
      %__MODULE__{
        mode: :configured,
        endpoint: %{host: endpoint["host"], port: 443, path: endpoint["path"]},
        environment_id: v["environment_id"],
        pool_id: v["pool_id"],
        controller_id: v["controller_id"],
        platforms:
          Enum.map(platforms, fn
            "ios" -> :ios
            "android" -> :android
          end),
        resolvers:
          Enum.map(resolvers, fn address ->
            {:ok, ip} = :inet.parse_address(String.to_charlist(address))
            {ip, 53}
          end),
        ca_roots: roots,
        token: token
      }
    else
      _ -> invalid!()
    end
  rescue
    _ -> invalid!()
  catch
    _, _ -> invalid!()
  end

  defp id?(v),
    do:
      is_binary(v) and byte_size(v) in 1..128 and
        Enum.all?(:binary.bin_to_list(v), &(&1 in 32..126))

  defp exact?(v, keys),
    do: is_map(v) and map_size(v) == length(keys) and Enum.all?(keys, &Map.has_key?(v, &1))

  defp hostname?(v) when is_binary(v) and byte_size(v) in 2..253 do
    labels = String.split(v, ".")

    not match?({:ok, _}, :inet.parse_address(String.to_charlist(v))) and length(labels) >= 2 and
      Enum.all?(
        labels,
        &(byte_size(&1) in 1..63 and Regex.match?(~r/\A[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\z/, &1))
      )
  end

  defp hostname?(_), do: false

  defp resolver?(v) when is_binary(v) and byte_size(v) in 1..45 do
    with {:ok, ip} <- :inet.parse_address(String.to_charlist(v)),
         true <- GlobalAddress.global?(ip),
         ^v <- :inet.ntoa(ip) |> List.to_string(),
         do: true,
         else: (_ -> false)
  end

  defp resolver?(_), do: false

  defp roots?(v) when is_list(v) and length(v) in 1..256 do
    Enum.all?(v, &(is_binary(&1) and byte_size(&1) in 1..65_536)) and
      Enum.sum(Enum.map(v, &byte_size/1)) <= 1_048_576 and
      Enum.all?(v, fn root ->
        try do
          :public_key.pkix_decode_cert(root, :otp)
          true
        rescue
          _ -> false
        end
      end)
  end

  defp roots?(_), do: false
  defp invalid!, do: raise(ArgumentError, "invalid worker configuration")
end
